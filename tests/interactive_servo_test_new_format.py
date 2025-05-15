#!/usr/bin/env python3
import asyncio
import sys
import os

# Add the parent directory to the path so we can import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.robot_control import RobotControl

# Meccanoid's MAC address
MECCANOID_DEVICE_ADDRESS = "5C:F8:21:EF:ED:D1"  # Replace if different

# Map names to servo indices according to the updated protocol:
# Servo 0: Unknown/T-Pose
# Servo 1: Right Elbow
# Servo 2: Right Shoulder
# Servo 3: Left Shoulder
# Servo 4: Left Elbow
SERVO_MAP = {
    "LShoulder": 3,  # Left Shoulder -> Physical Servo 3
    "LElbow": 4,     # Left Elbow -> Physical Servo 4
    "RShoulder": 2,  # Right Shoulder -> Physical Servo 2
    "RElbow": 1,     # Right Elbow -> Physical Servo 1
}

# Standard positions (from protocol):
# 0x40 (64): Minimum position
# 0x80 (128): Center/neutral position
# 0xC0 (192): Maximum position

async def interactive_servo_test():
    """
    Interactive servo test program for the Meccanoid robot.
    Allows moving the 4 main arm servos (LSh, LEl, RSh, REl) with real-time input.
    """
    robot = RobotControl(MECCANOID_DEVICE_ADDRESS)

    try:
        print("Connecting to Meccanoid...")
        if not await robot.connect():
            print("Failed to connect to Meccanoid.")
            return

        print("Connected! Initializing robot...")
        await robot.initialize_robot()
        
        # Set all servos to center position (0x80)
        center_positions = [0x80] * 8
        await robot.set_all_servos_raw(center_positions)
        print("All servos set to center position (0x80).")
        
        print("\n===== INTERACTIVE SERVO TEST =====")
        print("Servo Position Guide:")
        print("  0x40 (64) = Minimum")
        print("  0x80 (128) = Center/Neutral")
        print("  0xC0 (192) = Maximum")
        print("\nDirectional Reference:")
        print("  Left Shoulder (LSh): 0x40=Up, 0x80=Center, 0xC0=Down")
        print("  Left Elbow (LEl): 0x40=In/Bent, 0x80=Center, 0xC0=Out/Extended")
        print("  Right Shoulder (RSh): 0x40=Down, 0x80=Center, 0xC0=Up")
        print("  Right Elbow (REl): 0x40=Out/Extended, 0x80=Center, 0xC0=In/Bent")
        print("\nEnter servo positions (0-255) or press Ctrl+C to exit")
        
        while True:
            try:
                # Get input values for each arm servo
                lsh_input = input("\nLeft Shoulder position (0-255, default=128): ").strip()
                lsh = int(lsh_input) if lsh_input else 0x80

                lel_input = input("Left Elbow position (0-255, default=128): ").strip()
                lel = int(lel_input) if lel_input else 0x80

                rsh_input = input("Right Shoulder position (0-255, default=128): ").strip()
                rsh = int(rsh_input) if rsh_input else 0x80

                rel_input = input("Right Elbow position (0-255, default=128): ").strip()
                rel = int(rel_input) if rel_input else 0x80

                # Validate inputs
                for name, val in [("Left Shoulder", lsh), ("Left Elbow", lel), 
                                 ("Right Shoulder", rsh), ("Right Elbow", rel)]:
                    if not (0 <= val <= 255):
                        print(f"Error: {name} position {val} is out of range (0-255). Using 128 instead.")
                        if name == "Left Shoulder":
                            lsh = 128
                        elif name == "Left Elbow":
                            lel = 128
                        elif name == "Right Shoulder":
                            rsh = 128
                        elif name == "Right Elbow":
                            rel = 128

                # Create servo command with default neutral values
                servo_positions = [0x80] * 8

                # Map the logical arm servo positions to their physical indices
                servo_positions[SERVO_MAP["LShoulder"]] = lsh
                servo_positions[SERVO_MAP["LElbow"]] = lel
                servo_positions[SERVO_MAP["RShoulder"]] = rsh
                servo_positions[SERVO_MAP["RElbow"]] = rel

                print(f"\nSending servo positions: LSh={lsh}, LEl={lel}, RSh={rsh}, REl={rel}")
                print(f"Physical servo indices: LSh->3, LEl->4, RSh->2, REl->1")
                print(f"Full servo array: {servo_positions}")

                # Send the servo command
                await robot.set_all_servos_raw(servo_positions)
                
                # Option to reset to neutral
                reset = input("\nReset to neutral? (y/n, default=n): ").strip().lower()
                if reset == 'y':
                    await robot.set_all_servos_raw([0x80] * 8)
                    print("Reset all servos to neutral position.")
                
            except ValueError:
                print("Invalid input. Please enter numeric values.")
            except KeyboardInterrupt:
                print("\nExiting interactive servo test.")
                break
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        print("Disconnecting from Meccanoid...")
        await robot.disconnect()
        print("Disconnected.")

if __name__ == "__main__":
    asyncio.run(interactive_servo_test())