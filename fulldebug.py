import pygame

# Initialize Pygame and the joystick module
pygame.init()
pygame.joystick.init()

# Check if a controller is connected
if pygame.joystick.get_count() == 0:
    print("No controller detected! Please connect a PS5 controller.")
    exit()

# Get the first joystick (controller)
controller = pygame.joystick.Joystick(0)
controller.init()

print(f"Connected to: {controller.get_name()}")
print("Listening for controller input...\n")

# Button and axis mapping
button_map = {
    0: "X",
    1: "Circle",
    2: "Triangle",
    3: "Square",
    4: "L1",
    5: "R1",
    6: "L2 (Button)",
    7: "R2 (Button)",
    8: "Share",
    9: "Options",
    10: "PS Button",
    11: "Left Stick Press",
    12: "Right Stick Press",
    13: "Touchpad Button",
}

axis_map = {
    0: "Left Stick X",
    1: "Left Stick Y",
    2: "L2 (Analog)",
    3: "Right Stick X",
    4: "Right Stick Y",
    5: "R2 (Analog)",
}

hat_map = {
    (-1, 0): "D-Pad Left",
    (1, 0): "D-Pad Right",
    (0, -1): "D-Pad Up",
    (0, 1): "D-Pad Down",
}
deadzone = 0.13
# Main event loop
running = True
while running:
    for event in pygame.event.get():
        # Check if the user wants to quit
        if event.type == pygame.QUIT:
            running = False

        # Detect button press/release
        if event.type == pygame.JOYBUTTONDOWN or event.type == pygame.JOYBUTTONUP:
            button = event.button
            state = "Pressed" if event.type == pygame.JOYBUTTONDOWN else "Released"
            if button in button_map:
                print(f"Button {button_map[button]} {state}")
            else:
                print(f"Unknown Button {button} {state}")

        deadzone = 0.13  # Deadzone threshold (values from -1 to 1)

        # Detect analog stick movement
        
        if event.type == pygame.JOYAXISMOTION:
            axis = event.axis
            value = round(controller.get_axis(axis), 2)  # Get axis value and round to 2 decimal places
            
            if axis in axis_map:
                if abs(value) > deadzone:  # Only print if movement exceeds deadzone
                    print(f"{axis_map[axis]} moved to {value}")

        
        # Detect D-Pad presses
        if event.type == pygame.JOYHATMOTION:
            hat_value = controller.get_hat(0)
            if hat_value in hat_map:
                print(f"{hat_map[hat_value]} Pressed")

pygame.quit()
