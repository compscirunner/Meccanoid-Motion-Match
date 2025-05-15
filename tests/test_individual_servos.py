import asyncio
import sys
import os
import cv2  # For webcam
import datetime  # For timestamping files and directories
import base64  # For encoding images
import requests  # For making HTTP requests to Ollama API
import pygame  # For sound playback
import numpy as np  # For sound generation
import argparse # For command-line arguments

# Add project root to Python path to allow importing from 'src'
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

try:
    from src.robot_control import RobotControl, DEFAULT_SERVO_POS
    import src.robot_control as robot_control_module
except ImportError:
    print("Error: Could not import from src.robot_control. Ensure src is in PYTHONPATH or script is run from project root.")
    sys.exit(1)

# Configuration
MECCANOID_DEVICE_ADDRESS = "5C:F8:21:EF:ED:D1"  # << IMPORTANT: VERIFY THIS MAC ADDRESS
INITIALIZATION_DELAY_SECONDS = 1
POST_COMMAND_DELAY_SECONDS = 2.5 # Time to wait after sending command before capture

# --- New Constants and Configuration ---
TEST_RESULTS_BASE_DIR = os.path.join(PROJECT_ROOT, "test_results", "servo_tests")
IMAGES_SUBDIR = "images"  # Subdirectory within the test run folder for images

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llava:latest" # Using a general model that can describe images

# Global sound objects
command_ack_beep = None
pre_capture_beep = None

# --- Helper Functions (adapted from test_robot_poses.py) ---

def initialize_sounds():
    """Initializes sound objects for playback."""
    global command_ack_beep, pre_capture_beep
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=256)
    if pygame.mixer.get_init():
        command_ack_beep = make_beep_sound(150, 660)  # 150ms, E5 note
        pre_capture_beep = make_beep_sound(80, 1320)  # 80ms, E6 note
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

def play_pre_capture_beeps():
    """Plays pre-capture beeps."""
    if pre_capture_beep and pygame.mixer.get_init():
        for _ in range(3):
            pre_capture_beep.play()
            pygame.time.wait(int(pre_capture_beep.get_length() * 1000 * 0.7))

def create_test_run_directory():
    """Creates a timestamped directory for the current test run."""
    current_time_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    test_run_dir = os.path.join(TEST_RESULTS_BASE_DIR, current_time_str)
    images_dir = os.path.join(test_run_dir, IMAGES_SUBDIR)
    os.makedirs(images_dir, exist_ok=True)
    print(f"Created test run directory: {test_run_dir}")
    return test_run_dir, images_dir

async def run_servo_test(s0, s1, s2, s3):
    """
    Connects to the Meccanoid, sets the 4 arm servos to specified effective positions,
    captures an image, and gets an AI description.
    s0: Target effective Left Shoulder
    s1: Target effective Left Elbow
    s2: Target effective Right Shoulder
    s3: Target effective Right Elbow
    """
    initialize_sounds()

    if not MECCANOID_DEVICE_ADDRESS or MECCANOID_DEVICE_ADDRESS == "XX:XX:XX:XX:XX:XX":
        print("Error: MECCANOID_DEVICE_ADDRESS is not set. Please edit the script with the correct MAC address.")
        return

    # Create directories for this test run
    test_run_dir, images_dir = create_test_run_directory()
    
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

        # Prepare servo positions based on updated protocol documentation
        # Script arguments s0, s1, s2, s3 are positions for:
        # s0: Left Shoulder 
        # s1: Left Elbow
        # s2: Right Shoulder
        # s3: Right Elbow

        # Initialize all servos to neutral position
        final_positions_to_send = [DEFAULT_SERVO_POS] * 8

        # Corrected Servo Mapping from protocol:
        # Physical Servo 0: Unknown/T-Pose
        # Physical Servo 1: Right Elbow
        # Physical Servo 2: Right Shoulder
        # Physical Servo 3: Left Shoulder
        # Physical Servo 4: Left Elbow
        # Physical Servos 5-7: No observed function
        
        # Define command array indices for each arm part
        SERVO_MAP = {
            "LShoulder": 3,  # Left Shoulder -> Physical Servo 3
            "LElbow": 4,     # Left Elbow -> Physical Servo 4
            "RShoulder": 2,  # Right Shoulder -> Physical Servo 2
            "RElbow": 1,     # Right Elbow -> Physical Servo 1
        }

        # Store the target positions
        target_lsh = s0  # Left Shoulder position
        target_lel = s1  # Left Elbow position
        target_rsh = s2  # Right Shoulder position
        target_rel = s3  # Right Elbow position

        print(f"Target positions: LSh={target_lsh}, LEl={target_lel}, RSh={target_rsh}, REl={target_rel}")
        print(f"Using DEFAULT_SERVO_POS: {DEFAULT_SERVO_POS}")
        print("Applying servo mapping:")

        # Map the logical arm servo positions to their physical indices
        # Left Shoulder (s0) -> Physical Servo 3
        final_positions_to_send[SERVO_MAP["LShoulder"]] = target_lsh
        print(f"  Physical Servo 3 (Left Shoulder): {target_lsh}")

        # Left Elbow (s1) -> Physical Servo 4
        final_positions_to_send[SERVO_MAP["LElbow"]] = target_lel
        print(f"  Physical Servo 4 (Left Elbow): {target_lel}")

        # Right Shoulder (s2) -> Physical Servo 2
        final_positions_to_send[SERVO_MAP["RShoulder"]] = target_rsh
        print(f"  Physical Servo 2 (Right Shoulder): {target_rsh}")
        
        # Right Elbow (s3) -> Physical Servo 1 
        final_positions_to_send[SERVO_MAP["RElbow"]] = target_rel
        print(f"  Physical Servo 1 (Right Elbow): {target_rel}")
        
        # Ensure other servos are at default
        # final_positions_to_send[0] is already default
        # final_positions_to_send[5] = DEFAULT_SERVO_POS (already default)
        # final_positions_to_send[6] = DEFAULT_SERVO_POS (already default)
        # final_positions_to_send[7] = DEFAULT_SERVO_POS (already default)

        print(f"Final 8 servo positions to send to robot: {final_positions_to_send}")

        play_sound_if_available(command_ack_beep)
        success = await robot.set_all_servos_raw(final_positions_to_send)

        if success:
            print(f"Servo command sent. Waiting {POST_COMMAND_DELAY_SECONDS}s for robot to settle...")
            await asyncio.sleep(POST_COMMAND_DELAY_SECONDS) # Wait full duration for robot to settle

            print("Image capture and AI description are currently commented out.")
        else:
            print(f"Failed to send servo command. Check robot connection and logs.")

        # Optionally, return to a neutral pose
        print(f"\nTest complete. Returning to T_Pose.")
        await robot.execute_pose("T_Pose") # Assumes T_Pose is neutral
        await asyncio.sleep(1)

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if robot.client and robot.client.is_connected:
            print("Disconnecting from Meccanoid...")
            await robot.disconnect()
        else:
            print("Meccanoid was not connected or already disconnected.")
        
        if pygame.mixer.get_init():
            pygame.mixer.quit()
        print("Servo test script finished.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test individual Meccanoid arm servo positions.")
    parser.add_argument("s0", type=int, help="Left Shoulder position (0-255, standard range: 64-128-192).")
    parser.add_argument("s1", type=int, help="Left Elbow position (0-255, standard range: 64-128-192).")
    parser.add_argument("s2", type=int, help="Right Shoulder position (0-255, standard range: 64-128-192).")
    parser.add_argument("s3", type=int, help="Right Elbow position (0-255, standard range: 64-128-192).")
    
    args = parser.parse_args()

    print("===================================")
    print(" Meccanoid Individual Servo Test ")
    print("===================================")
    print(f"Using RobotControl from: {robot_control_module.__file__}")
    print(f"Target MAC Address: {MECCANOID_DEVICE_ADDRESS}")
    print(f"Target Positions: LSh={args.s0}, LEl={args.s1}, RSh={args.s2}, REl={args.s3}")
    print(f"Default Servo Position: {DEFAULT_SERVO_POS} (0x{DEFAULT_SERVO_POS:02X} - Neutral)")
    print(f"Standard Range: 0x40 (64) Min - 0x80 (128) Center - 0xC0 (192) Max")
    print("-----------------------------------")

    if sys.version_info < (3, 7):
        print("This script requires Python 3.7 or newer for asyncio.run().")
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(run_servo_test(args.s0, args.s1, args.s2, args.s3))
        finally:
            loop.close()
    else:
        asyncio.run(run_servo_test(args.s0, args.s1, args.s2, args.s3))
