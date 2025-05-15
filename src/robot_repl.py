import asyncio
import sys
import termios
import tty
from src.robot_control import RobotControl
from tests.utils.home_assistant_control import set_robot_power

def print_help():
    print("\nAvailable commands:")
    print("  pose <pose_name>       - Execute a predefined pose (e.g., Neutral, Arms_Up)")
    print("  eye <r> <g> <b>        - Set eye color (r, g, b values from 0-7)")
    print("  power <on|off>         - Turn the robot power on or off via Home Assistant")
    print("  servo                  - Enter manual servo control mode")
    print("  help                   - Show this help message")
    print("  exit                   - Exit the REPL\n")

async def power_cycle_robot():
    """
    Power cycles the robot using Home Assistant.
    """
    loop = asyncio.get_running_loop()

    print("\n--- Power Cycling Robot ---")

    # Turn off the robot
    print("Turning robot OFF...")
    power_off_successful = await loop.run_in_executor(None, set_robot_power, "off")
    if power_off_successful:
        print("Robot power OFF successful. Waiting 20 seconds...")
        await asyncio.sleep(20)
    else:
        print("Warning: Failed to turn robot OFF. Test may be unreliable.")

    # Turn on the robot
    print("Turning robot ON...")
    power_on_successful = await loop.run_in_executor(None, set_robot_power, "on")
    if power_on_successful:
        print("Robot power ON successful. Waiting 20 seconds for boot...")
        await asyncio.sleep(20)
    else:
        print("Warning: Failed to turn robot ON. Test may be unreliable.")

    print("--- Power Cycle Complete ---\n")

async def manual_servo_control(robot):
    """
    Allows manual control of each servo via the REPL.
    Users can input servo numbers and positions interactively or use arrow keys to adjust.
    """
    def get_key():
        """Reads a single keypress from the user."""
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            key = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return key

    print("\nManual Servo Control Mode")
    print("Enter servo index (0-7) to select a servo. Use arrow keys to adjust position.")
    print("Press 'q' to quit.")

    # Fetch the current servo positions from the robot
    try:
        current_positions = robot.servo_positions[:]
        print("Fetched current servo positions from the robot.")
    except AttributeError:
        print("Warning: Unable to fetch current servo positions. Using default values.")
        current_positions = [120] * 8  # Default positions for all servos

    current_servo = None

    while True:
        if current_servo is None:
            try:
                user_input = input("Select servo index (0-7): ")
                if user_input.lower() == 'q':
                    print("Exiting Manual Servo Control Mode.")
                    break

                current_servo = int(user_input)
                if not (0 <= current_servo <= 7):
                    print("Invalid servo index. Must be between 0 and 7.")
                    current_servo = None
                    continue

                print(f"Servo {current_servo} selected. Use arrow keys to adjust position.")
            except ValueError:
                print("Invalid input. Please enter a servo index (0-7).")
                continue

        print(f"Current position for servo {current_servo}: {current_positions[current_servo]}")
        print("Press arrow keys to adjust, or 'q' to quit.")

        key = get_key()
        if key == 'q':
            print("Exiting Manual Servo Control Mode.")
            break
        elif key == '\x1b':  # Escape sequence for arrow keys
            next_key = get_key()
            if next_key == '[':
                arrow_key = get_key()
                if arrow_key == 'A':  # Up arrow
                    current_positions[current_servo] = min(255, current_positions[current_servo] + 1)
                elif arrow_key == 'B':  # Down arrow
                    current_positions[current_servo] = max(0, current_positions[current_servo] - 1)

                success = await robot.set_all_servos_raw(current_positions)
                if success:
                    print(f"Servo {current_servo} set to position {current_positions[current_servo]}.")
                else:
                    print(f"Failed to set servo {current_servo} to position {current_positions[current_servo]}.")
        else:
            print("Invalid key. Use arrow keys to adjust or 'q' to quit.")

async def main():
    MECCANOID_DEVICE_ADDRESS = "5C:F8:21:EF:ED:D1"  # Replace with your robot's MAC address
    robot = RobotControl(MECCANOID_DEVICE_ADDRESS)

    # await power_cycle_robot()  # Ensure the robot is powered on and ready
    print("INFO: Automatic power cycle at startup is disabled.")

    print("Connecting to the robot...")
    if not await robot.connect():
        print("Failed to connect to the robot. Exiting.")
        return

    print("Initializing robot...")
    if not await robot.initialize_robot():
        print("Failed to send handshake to the robot. Continuing, but some features might not work.")
    # If initialize_robot is crucial and we want to exit on failure:
    # else:
    #     print("Failed to initialize the robot after connection. Exiting.")
    #     await robot.disconnect()
    #     return

    print("Connected and initialized. Type 'help' for available commands.")

    try:
        while True:
            command = input("robot> ").strip()
            if not command:
                continue

            parts = command.split()
            cmd = parts[0].lower()

            if cmd == "pose":
                if len(parts) != 2:
                    print("Usage: pose <pose_name>")
                    continue
                pose_name = parts[1]
                if not await robot.execute_pose(pose_name):
                    print(f"Failed to execute pose: {pose_name}")

            elif cmd == "eye":
                if len(parts) != 4:
                    print("Usage: eye <r> <g> <b>")
                    continue
                try:
                    r, g, b = map(int, parts[1:])
                    if not await robot.set_eye_color(r, g, b):
                        print(f"Failed to set eye color to R:{r} G:{g} B:{b}")
                except ValueError:
                    print("Invalid input. r, g, b must be integers between 0 and 7.")

            elif cmd == "power":
                if len(parts) != 2 or parts[1] not in ["on", "off"]:
                    print("Usage: power <on|off>")
                    continue
                state = parts[1]
                if not set_robot_power(state):
                    print(f"Failed to turn power {state}.")

            elif cmd == "help":
                print_help()

            elif cmd == "exit":
                print("Exiting...")
                break

            elif cmd == "servo":
                await manual_servo_control(robot)

            else:
                print(f"Unknown command: {cmd}. Type 'help' for a list of commands.")

    except KeyboardInterrupt:
        print("\nExiting...")

    finally:
        print("Disconnecting from the robot...")
        await robot.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
