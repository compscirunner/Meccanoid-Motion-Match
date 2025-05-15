import asyncio
import sys
import os
import cv2  # For webcam
import datetime  # For timestamping files and directories
import base64  # For encoding images
import requests  # For making HTTP requests to Ollama API
import webbrowser  # To open the HTML report
import pygame  # For sound playback
import numpy as np  # For sound generation
from tests.utils.home_assistant_control import set_robot_power

# Add project root to Python path to allow importing from 'src'
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

try:
    from src.robot_control import RobotControl
    import src.robot_control as robot_control_module  # Import the module itself
except ImportError:
    print("Error: Could not import RobotControl from src. Ensure src is in PYTHONPATH or script is run from project root.")
    sys.exit(1)

# Configuration
MECCANOID_DEVICE_ADDRESS = "5C:F8:21:EF:ED:D1"  # << IMPORTANT: VERIFY THIS MAC ADDRESS
POSE_CYCLE_DELAY_SECONDS = 3  # Time to hold each pose for visual verification
INITIALIZATION_DELAY_SECONDS = 1
POST_CYCLE_DELAY_SECONDS = 1

# --- New Constants and Configuration ---
TEST_RESULTS_BASE_DIR = os.path.join(PROJECT_ROOT, "test_results", "pose_tests")
IMAGES_SUBDIR = "images"  # Subdirectory within the test run folder for images

OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:12b-it-qat"  # Changed to match test_robot_eyes.py

# Global sound objects
command_ack_beep = None
pre_capture_beep = None

# --- Helper Functions (similar to test_robot_eyes.py) ---


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


def capture_image(cap, filename_prefix, pose_name, images_dir):
    """Captures an image from the webcam and saves it."""
    if not cap or not cap.isOpened():
        print("Error: Webcam not initialized or not open.")
        return None

    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to capture frame from webcam.")
        return None

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    image_filename = f"{filename_prefix}_{pose_name.lower().replace(' ', '_')}_{timestamp}.png"
    image_path = os.path.join(images_dir, image_filename)

    try:
        cv2.imwrite(image_path, frame)
        print(f"Successfully saved image: {image_path}")
        return image_path
    except Exception as e:
        print(f"Error saving image {image_path}: {e}")
        return None


def get_ai_pose_description(image_path, pose_name_expected):
    """Sends an image to Ollama and asks for a pose description."""
    if not image_path:
        return "Error: No image path provided for AI analysis."

    print(f"Requesting AI description for pose: {pose_name_expected} (image: {os.path.basename(image_path)})...")
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

        prompt_text = (
            f"This image contains a Meccanoid robot. "
            f"The robot was instructed to perform the '{pose_name_expected}' pose. "
            f"Describe the robot's actual pose in the image, focusing on its arm and elbow positions. "
            f"Does the robot in the image appear to be performing the '{pose_name_expected}' pose? "
            f"Be concise."
        )

        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt_text,
            "images": [encoded_string],
            "stream": False
        }
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=60)  # 60s timeout
        response.raise_for_status()  # Raise an exception for HTTP errors

        response_json = response.json()
        ai_description = response_json.get("response", "No description provided by AI.").strip()
        print(f"AI (Ollama) says: {ai_description}")
        return ai_description
    except requests.exceptions.RequestException as e:
        error_msg = f"Error communicating with Ollama API: {e}"
        print(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error during AI pose description: {e}"
        print(error_msg)
        return error_msg


def generate_html_report(results, report_dir):
    """Generates an HTML report for the pose test results."""
    report_filename = "pose_test_report.html"
    report_path = os.path.join(report_dir, report_filename)

    html_content = "<html><head><title>Meccanoid Pose Test Report</title>"
    html_content += "<style>"
    html_content += "body { font-family: sans-serif; margin: 20px; } "
    html_content += "h1 { text-align: center; color: #333; } "
    html_content += "table { width: 100%; border-collapse: collapse; margin-top: 20px; } "
    html_content += "th, td { border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: top; } "
    html_content += "th { background-color: #f2f2f2; } "
    html_content += "img { max-width: 320px; max-height: 240px; border: 1px solid #ccc; } "
    html_content += ".result-correct { background-color: #e6ffe6; } "  # Light green
    html_content += ".result-incorrect { background-color: #ffe6e6; } "  # Light red
    html_content += ".result-skipped { background-color: #ffffcc; } "  # Light yellow
    html_content += ".result-unknown { background-color: #f0f0f0; } "  # Light gray
    html_content += "</style></head><body>"
    html_content += f"<h1>Meccanoid Pose Test Report - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</h1>"

    html_content += "<table><tr><th>Expected Pose</th><th>Image</th><th>AI Description</th><th>Human Verification</th></tr>"

    for result in results:
        image_relative_path = os.path.join(IMAGES_SUBDIR, os.path.basename(result.get('image_path', ''))) if result.get('image_path') else ''

        verification_status = result.get('human_verification', 'Unknown').lower()
        row_class = "result-unknown"
        if verification_status == 'correct':
            row_class = "result-correct"
        elif verification_status == 'incorrect':
            row_class = "result-incorrect"
        elif verification_status == 'skipped ai':
            row_class = "result-skipped"

        html_content += f"<tr class='{row_class}'>"
        html_content += f"<td>{result.get('pose_name', 'N/A')}</td>"
        if image_relative_path:
            html_content += f"<td><a href='{image_relative_path}' target='_blank'><img src='{image_relative_path}' alt='Pose: {result.get('pose_name', 'N/A')}'></a></td>"
        else:
            html_content += "<td>No image</td>"
        html_content += f"<td><pre>{result.get('ai_description', 'N/A')}</pre></td>"
        html_content += f"<td>{result.get('human_verification', 'N/A').title()}</td>"
        html_content += "</tr>"

    html_content += "</table></body></html>"

    try:
        with open(report_path, "w") as f:
            f.write(html_content)
        print(f"HTML report generated: {report_path}")
        webbrowser.open(f"file://{os.path.abspath(report_path)}")
    except Exception as e:
        print(f"Error generating HTML report: {e}")


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
        print("Robot power OFF successful. Waiting 5 seconds...")
        await asyncio.sleep(5)
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


async def run_pose_test_cycle():
    """
    Connects to the Meccanoid, initializes it, cycles through all defined poses,
    captures images, verifies poses using AI and human input, and generates an HTML report.
    """
    initialize_sounds()

    if not MECCANOID_DEVICE_ADDRESS or MECCANOID_DEVICE_ADDRESS == "XX:XX:XX:XX:XX:XX":
        print("Error: MECCANOID_DEVICE_ADDRESS is not set. Please edit the script with the correct MAC address.")
        return

    # Create directories for this test run
    test_run_dir, images_dir = create_test_run_directory()
    test_results_data = []  # To store data for the report

    robot = RobotControl(MECCANOID_DEVICE_ADDRESS)
    cap = None  # Webcam capture object

    try:
        # Initialize webcam
        cap = cv2.VideoCapture(0)  # Use 0 for default webcam
        if not cap.isOpened():
            print("Error: Could not open webcam. Pose images will not be captured.")

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
        print(f"Robot initialized. Waiting {INITIALIZATION_DELAY_SECONDS}s for systems to settle.")
        await asyncio.sleep(INITIALIZATION_DELAY_SECONDS)

        pose_names = list(RobotControl.POSES.keys())
        if not pose_names:
            print("No poses found in RobotControl.POSES. Exiting test.")
            return

        print(f"\nStarting pose test cycle. Will execute {len(pose_names)} poses.")
        print(f"Poses to be tested: {', '.join(pose_names)}")
        print(f"Each pose will be held for {POSE_CYCLE_DELAY_SECONDS} seconds.")
        print("Ensure the robot has clear space to move its arms.")

        for i, pose_name in enumerate(pose_names):
            print(f"\n[{i+1}/{len(pose_names)}] Executing pose: '{pose_name}'")
            current_pose_result = {"pose_name": pose_name, "image_path": None, "ai_description": "N/A", "human_verification": "Not Verified"}

            play_sound_if_available(command_ack_beep)
            success = await robot.execute_pose(pose_name)
            if success:
                print(f"Pose '{pose_name}' command sent. Holding for {POSE_CYCLE_DELAY_SECONDS}s for visual verification...")
                await asyncio.sleep(POSE_CYCLE_DELAY_SECONDS / 2)  # Wait half, then capture

                # Play pre-capture beeps
                play_pre_capture_beeps()

                # Capture image
                if cap and cap.isOpened():
                    image_path = capture_image(cap, "pose_test", pose_name, images_dir)
                    current_pose_result["image_path"] = image_path
                    await asyncio.sleep(POSE_CYCLE_DELAY_SECONDS / 2)  # Wait the other half
                else:
                    print("Webcam not available, skipping image capture.")
                    await asyncio.sleep(POSE_CYCLE_DELAY_SECONDS / 2)

                # Get human verification
                while True:
                    user_input = input(f"  Was pose '{pose_name}' correct? (y/n/s skip AI): ").lower()
                    if user_input == 'y':
                        current_pose_result["human_verification"] = "Correct"
                        if image_path:  # Only run AI if image was captured and not skipped
                            current_pose_result["ai_description"] = get_ai_pose_description(image_path, pose_name)
                        break
                    elif user_input == 'n':
                        current_pose_result["human_verification"] = "Incorrect"
                        if image_path:  # Only run AI if image was captured and not skipped
                            current_pose_result["ai_description"] = get_ai_pose_description(image_path, pose_name)
                        break
                    elif user_input == 's':
                        current_pose_result["human_verification"] = "Skipped AI"
                        current_pose_result["ai_description"] = "AI check skipped by user."
                        break
                    else:
                        print("  Invalid input. Please enter 'y', 'n', or 's'.")
            else:
                print(f"Failed to send command for pose '{pose_name}'. Check robot connection and logs.")
                current_pose_result["human_verification"] = "Command Failed"
                await asyncio.sleep(0.5)

            test_results_data.append(current_pose_result)

        print(f"\nPose cycle complete. Returning to 'Neutral' pose for {POST_CYCLE_DELAY_SECONDS}s.")
        await robot.execute_pose("Neutral")
        await asyncio.sleep(POST_CYCLE_DELAY_SECONDS)

    except Exception as e:
        print(f"An unexpected error occurred during the pose test cycle: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if cap and cap.isOpened():
            print("Releasing webcam...")
            cap.release()

        if robot.client and robot.client.is_connected:
            print("Disconnecting from Meccanoid...")
            await robot.disconnect()
        else:
            print("Meccanoid was not connected or already disconnected at the end of the script.")
        print("Pose test script finished.")

        pygame.mixer.quit()

        # Generate HTML report
        if test_results_data:
            generate_html_report(test_results_data, test_run_dir)


if __name__ == "__main__":
    print("============================")
    print(" Meccanoid Pose Test Script ")
    print("============================")
    print(f"Using RobotControl from: {robot_control_module.__file__}")  # Use the module's __file__
    print(f"Defined Poses: {list(RobotControl.POSES.keys())}")
    print(f"Target MAC Address: {MECCANOID_DEVICE_ADDRESS}")
    print(f"Hold time per pose: {POSE_CYCLE_DELAY_SECONDS}s")
    print("----------------------------")

    # Ensure the script is run with Python 3.7+ for asyncio.run
    if sys.version_info < (3, 7):
        print("This script requires Python 3.7 or newer for asyncio.run().")
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(run_pose_test_cycle())
        finally:
            loop.close()
    else:
        asyncio.run(run_pose_test_cycle())
