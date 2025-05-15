import asyncio
import sys
import os
import pygame  # For sound playback
import numpy as np  # For sound generation
import traceback

# Add project root to Python path to allow importing from 'src'
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

try:
    from src.robot_control import RobotControl, DEFAULT_SERVO_POS, REVERSED_SERVO_INDICES
    import src.robot_control as robot_control_module
except ImportError:
    print("Error: Could not import from src.robot_control. Ensure src is in PYTHONPATH or script is run from project root.")
    sys.exit(1)

# Configuration
MECCANOID_DEVICE_ADDRESS = "5C:F8:21:EF:ED:D1"  # << IMPORTANT: VERIFY THIS MAC ADDRESS
INITIALIZATION_DELAY_SECONDS = 1
POST_COMMAND_DELAY_SECONDS = 0.5  # Reduced delay since we don't need to wait for camera

# Global sound objects
command_ack_beep = None

# --- Helper Functions ---

def initialize_sounds():
    """Initializes sound objects for playback."""
    global command_ack_beep
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=256)
    if pygame.mixer.get_init():
        command_ack_beep = make_beep_sound(150, 660)  # 150ms, E5 note
    else:
        print("Pygame mixer not initialized. Cannot create sounds.")

def make_beep_sound(duration_ms, frequency_hz):
    """Generates a beep sound."""
    sample_rate = pygame.mixer.get_init()[0]
    n_samples = int(sample_rate * duration_ms / 1000.0)
    buf = np.zeros((n_samples,), dtype=np.int16)
    max_val = np.iinfo(np.int16).max

    for i in range(n_samples):
        t = float(i) / sample_rate
        buf[i] = int(max_val * np.sin(2 * np.pi * frequency_hz * t))

    sound = pygame.sndarray.make_sound(buf.astype(np.int16))
    return sound

def play_sound_if_available(sound_object):
    """Plays a sound if available."""
    if sound_object and pygame.mixer.get_init():
        sound_object.play()

async def interactive_servo_test():
    """
    Connects to the Meccanoid and allows interactive control of servo positions.
    """
    initialize_sounds()

    if not MECCANOID_DEVICE_ADDRESS or MECCANOID_DEVICE_ADDRESS == "XX:XX:XX:XX:XX:XX":
        print("Error: MECCANOID_DEVICE_ADDRESS is not set. Please edit the script with the correct MAC address.")
        return

    robot = RobotControl(MECCANOID_DEVICE_ADDRESS)

    try:
        print(f"Attempting to connect to Meccanoid at {MECCANOID_DEVICE_ADDRESS}...")
        if not await robot.connect():
            print("Failed to connect to the Meccanoid. Please check Bluetooth and MAC address.")
            return

        print("Connected successfully. Initializing robot...")
        if not await robot.initialize_robot():
            print("Failed to send handshake/initialize command to the robot.")
            if robot.client and robot.client.is_connected:
                await robot.disconnect()
            return
        print(f"Robot initialized. Waiting {INITIALIZATION_DELAY_SECONDS}s.")
        await asyncio.sleep(INITIALIZATION_DELAY_SECONDS)
        
        print("\n===== INTERACTIVE SERVO TEST - EXTENDED =====")
        print("This script allows testing all 8 servo values in the command array")
        print("Enter servo values (0-255) for each servo, separated by spaces.")
        print("- Enter 4 values to control servo indices 0-3 (e.g., '120 90 150 170')")
        print("- Enter 8 values to control all servo indices 0-7")
        print("- Enter 't' for T-pose (all servos to 120)")
        print("- Enter 'q' or 'quit' to exit")
        print("Based on previous tests, servo indices might control:")
        print("  Index 0: Unknown")
        print("  Index 1: Right Elbow")
        print("  Index 2: Right Shoulder")
        print("  Index 3: Left Shoulder")
        print("  Index 4-7: Not known yet (might include Left Elbow)")
        print("============================================")
        
        # Main interactive loop
        while True:
            user_input = input("\nEnter servo positions (4 or 8 values) or command: ")
            
            if user_input.lower() in ['q', 'quit', 'exit']:
                print("Exiting interactive mode...")
                break
                
            if user_input.lower() == 't':
                # T-pose - Set all servos to default position
                final_positions_to_send = [DEFAULT_SERVO_POS] * 8
                print(f"Setting T-pose: {final_positions_to_send}")
            else:
                # Parse the user input - allow either 4 or 8 values
                try:
                    servo_values = list(map(int, user_input.split()))
                    
                    if len(servo_values) != 4 and len(servo_values) != 8:
                        print("Error: Please enter either 4 values (for servos 0-3) or 8 values (for all servos 0-7).")
                        continue
                    
                    # Initialize final positions to default
                    final_positions_to_send = [DEFAULT_SERVO_POS] * 8
                    
                    # Replace with user values
                    for i, val in enumerate(servo_values):
                        if not (0 <= val <= 255):
                            print(f"Warning: Servo {i} value {val} is outside 0-255 range.")
                        final_positions_to_send[i] = val
                            
                except ValueError:
                    print("Error: Please enter valid integer values.")
                    continue
            
            # Apply reversal logic for servos that are in the reversed indices list
            physically_reversed_ids = REVERSED_SERVO_INDICES  # Should be [3] from robot_control
            print(f"Physically reversed servo IDs: {physically_reversed_ids}")
            
            for i in range(len(final_positions_to_send)):
                value = final_positions_to_send[i]
                if i in physically_reversed_ids and value != DEFAULT_SERVO_POS:
                    final_positions_to_send[i] = 0xFF - value
                    print(f"  Servo {i} target={value} is REVERSED. Sending: {final_positions_to_send[i]}")
                else:
                    print(f"  Servo {i} target={value}. Sending: {final_positions_to_send[i]}")
            
            print(f"Command bytes to robot: {final_positions_to_send}")

            play_sound_if_available(command_ack_beep)
            success = await robot.set_all_servos_raw(final_positions_to_send)

            if success:
                print(f"Servo command sent. Waiting {POST_COMMAND_DELAY_SECONDS}s for robot to settle...")
                await asyncio.sleep(POST_COMMAND_DELAY_SECONDS)
                print("Ready for next command.")
            else:
                print(f"Failed to send servo command. Check robot connection and logs.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        traceback.print_exc()
    finally:
        if robot.client and robot.client.is_connected:
            print("Disconnecting from Meccanoid...")
            await robot.disconnect()
        else:
            print("Meccanoid was not connected or already disconnected.")
        
        if pygame.mixer.get_init():
            pygame.mixer.quit()
        print("Interactive servo test finished.")

if __name__ == "__main__":
    print("===================================")
    print(" Meccanoid Interactive Servo Test  ")
    print("===================================")
    print(f"Using RobotControl from: {robot_control_module.__file__}")
    print(f"Target MAC Address: {MECCANOID_DEVICE_ADDRESS}")
    print(f"Default Servo Position: {DEFAULT_SERVO_POS}")
    print(f"Reversed Servo Indices: {REVERSED_SERVO_INDICES}")
    print("-----------------------------------")

    asyncio.run(interactive_servo_test())
