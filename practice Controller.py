import pygame
import time
import threading
from car import Car
from buzzer import Buzzer
from servo import Servo

class Controller:
    def __init__(self):
        pygame.init()
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            print("No controller is being detected Sir! Please connect a controller.")
            exit()

        self.controller = pygame.joystick.Joystick(0)
        self.controller.init()
        print(f"Connected to: {self.controller.get_name()}")
        print("Waiting for controller input...\n")

        # Initialize components
        self.car = Car()
        self.buzzer = Buzzer()
        self.servo = Servo()

        # Controller settings
        self.deadzone = 0.13  # Deadzone for joystick movement
        self.max_speed = 3000

        # Motor target speeds
        self.target_FL = 0
        self.target_BL = 0
        self.target_FR = 0
        self.target_BR = 0

        # Lock for thread-safe updates of target speeds
        self.speed_lock = threading.Lock()

        # Servo control
        self.servo_x = 90  # X-axis (Servo 0)
        self.servo_y = 90  # Y-axis (Servo 1)
        self.servo_step = 5

        # Button mappings
        self.button_map = {
            0: "X",
            1: "Circle",
            2: "Triangle",
            3: "Square",
            4: "L1",
            5: "R1",
            6: "L2",  # Also has an axis (2)
            7: "R2",  # Also has an axis (5)
            8: "Share",
            9: "Options",
            10: "PS Button",
            11: "Left Stick Press",
            12: "Right Stick Press",
            13: "Touchpad Button",
        }

        # Axis mappings
        self.axis_map = {
            0: "Left Stick X",
            1: "Left Stick Y",  # Inverted
            2: "L2 (Analog)",
            3: "Right Stick X",
            4: "Right Stick Y",  # Inverted
            5: "R2 (Analog)",
        }

        # D-Pad mappings
        self.hat_map = {
            (-1, 0): "D-Pad Left",
            (1, 0): "D-Pad Right",
            (0, -1): "D-Pad Up",
            (0, 1): "D-Pad Down",
        }

        # Running flag to control threads
        self.running = True

        # Camera state
        self.camera_active = False
        self.camera_thread = None

    def scale_joystick(self, value):
        """Scale joystick input (-1 to 1) to motor speed (-3000 to 3000) with deadzone applied."""
        if abs(value) < self.deadzone:
            return 0
        return int(value * self.max_speed)

    def move_servo(self, axis, direction):
        """Adjust servo angles based on D-Pad input."""
        if axis == "X":
            self.servo_x = max(0, min(180, self.servo_x + direction * self.servo_step))
            self.servo.set_servo_pwm("0", self.servo_x)  # Servo 0 (X-axis)
        elif axis == "Y":
            # Invert servo Y to correct flipped behavior
            self.servo_y = max(0, min(180, self.servo_y - direction * self.servo_step))
            self.servo.set_servo_pwm("1", self.servo_y)  # Servo 1 (Y-axis)

    def camera_feed_loop(self):
        """Capture camera frames using Picamera2 and display them in a window."""
        from picamera2 import Picamera2
        import cv2
        picam2 = Picamera2()
        config = picam2.create_preview_configuration()
        picam2.configure(config)
        picam2.start()

        cv2.namedWindow("Camera Feed", cv2.WINDOW_NORMAL)
        while self.camera_active:
            frame = picam2.capture_array()
            if frame is None:
                continue
            cv2.imshow("Camera Feed", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.camera_active = False
                break

        picam2.stop()
        cv2.destroyWindow("Camera Feed")

    def process_event(self):
        """Process all controller events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return False  # Stop program

            # Handle button press/release events
            if event.type in [pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP]:
                button = event.button
                state = "Pressed" if event.type == pygame.JOYBUTTONDOWN else "Released"

                # Toggle camera feed on Share button (button index 8)
                if button == 8 and state == "Pressed":
                    if not self.camera_active:
                        print("Activating camera feed...")
                        self.camera_active = True
                        self.camera_thread = threading.Thread(target=self.camera_feed_loop)
                        self.camera_thread.daemon = True
                        self.camera_thread.start()
                    else:
                        print("Deactivating camera feed...")
                        self.camera_active = False

                # Buzzer controlled by X button (button index 0)
                if button == 0:
                    self.buzzer.set_state(state == "Pressed")

            # Handle analog stick movement for car control
            if event.type == pygame.JOYAXISMOTION:
                if event.axis in [0, 1, 3]:
                    self.handle_movement()

            # Handle D-Pad (Hat) movement for servo control
            if event.type == pygame.JOYHATMOTION:
                hat_value = self.controller.get_hat(0)
                if hat_value in self.hat_map:
                    if hat_value == (-1, 0):
                        self.move_servo("X", -1)
                    elif hat_value == (1, 0):
                        self.move_servo("X", 1)
                    elif hat_value == (0, -1):
                        self.move_servo("Y", 1)
                    elif hat_value == (0, 1):
                        self.move_servo("Y", -1)
        return True

    def handle_movement(self):
        """Update target speeds based on joystick input without smoothing."""
        left_x = self.scale_joystick(self.controller.get_axis(0))
        left_y = self.scale_joystick(-self.controller.get_axis(1))  # Invert Y-axis
        right_x = self.scale_joystick(-self.controller.get_axis(3))

        with self.speed_lock:
            if left_x == 0 and left_y == 0 and right_x == 0:
                self.target_FL = 0
                self.target_BL = 0
                self.target_FR = 0
                self.target_BR = 0
            else:
                self.target_FL = left_y + left_x - right_x
                self.target_BL = left_y - left_x - right_x
                self.target_FR = left_y - left_x + right_x
                self.target_BR = left_y + left_x + right_x

    def motor_control_loop(self):
        """Continuously send motor commands based on the latest target speeds."""
        while self.running:
            with self.speed_lock:
                fl = self.target_FL
                bl = self.target_BL
                fr = self.target_FR
                br = self.target_BR
            self.car.motor.set_motor_model(fl, bl, fr, br)
            time.sleep(0.005)

    def get_input(self):
        """Main loop to continuously listen for input and start the motor control thread."""
        motor_thread = threading.Thread(target=self.motor_control_loop)
        motor_thread.daemon = True
        motor_thread.start()

        while self.running:
            self.process_event()
            time.sleep(0.005)
        pygame.quit()

if __name__ == "__main__":
    controller = Controller()
    controller.get_input()
