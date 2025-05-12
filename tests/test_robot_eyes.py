import sys
import os
import base64 # For encoding images
import requests # For making HTTP requests to Ollama API

# Adjust Python path to find the 'src' module
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT) # Add project root

import asyncio
import cv2
from datetime import datetime
import time
import numpy as np # For sound generation
import pygame # For sound playback

from src.robot_control import RobotControl # Import from src package

# IMPORTANT: Verify this is your Meccanoid's MAC address
MECCANOID_DEVICE_ADDRESS = "5C:F8:21:EF:ED:D1"

# Define colors to test (R, G, B values from 0-7 as per set_eye_color in robot_control.py)
COLORS_TO_TEST = {
    "red": (7, 0, 0),
    "green": (0, 7, 0),
    "blue": (0, 0, 7),
    "yellow": (7, 7, 0), # R+G
    "cyan": (0, 7, 7),   # G+B
    "magenta": (7, 0, 7),# R+B
    "white": (7, 7, 7),
    "off": (0, 0, 0),
}

# Base output directory for images and reports
BASE_OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'test_results', 'eye_tests')

# --- Sound Generation ---
# Initialize pygame mixer with a buffer that's not too large to avoid latency
pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=256) 

# Global sound objects to avoid re-creating them repeatedly
command_ack_beep = None
pre_capture_beep = None

def initialize_sounds():
    global command_ack_beep, pre_capture_beep
    if pygame.mixer.get_init(): # Check if mixer is initialized
        command_ack_beep = make_beep_sound(150, 660)  # 150ms, E5 note
        pre_capture_beep = make_beep_sound(80, 1320) # 80ms, E6 note (higher pitch)
    else:
        print("Pygame mixer not initialized. Cannot create sounds.")

def make_beep_sound(duration_ms, frequency_hz):
    if not pygame.mixer.get_init():
        return None
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
    if sound_object and pygame.mixer.get_init():
        sound_object.play()

def play_command_ack_beep():
    play_sound_if_available(command_ack_beep)

def play_pre_capture_beeps():
    if pre_capture_beep and pygame.mixer.get_init():
        for _ in range(3):
            pre_capture_beep.play()
            pygame.time.wait(int(pre_capture_beep.get_length() * 1000 * 0.7)) # Wait 70% of beep length

# --- AI Model Interaction (Ollama) ---
OLLAMA_API_URL = "http://localhost:11434/api/generate"
AI_MODEL_NAME = "gemma3:12b-it-qat"
AI_PROMPT = "What is the primary color of the robot's eyes in this image? Respond with only the color name (e.g., red, green, blue, yellow, cyan, magenta, white, off/dark)."

async def get_ai_color_prediction(image_path):
    print(f"Sending image to AI model: {image_path}")
    try:
        with open(image_path, "rb") as image_file:
            img_base64 = base64.b64encode(image_file.read()).decode('utf-8')
        
        payload = {
            "model": AI_MODEL_NAME,
            "prompt": AI_PROMPT,
            "images": [img_base64],
            "stream": False # Get the full response at once
        }
        
        # Run the blocking requests call in a separate thread to avoid blocking asyncio event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: requests.post(OLLAMA_API_URL, json=payload, timeout=60))
        response.raise_for_status() # Raise an exception for HTTP errors
        
        response_data = response.json()
        ai_predicted_color = response_data.get("response", "Error: No response field").strip().lower()
        print(f"AI Prediction for {os.path.basename(image_path)}: {ai_predicted_color}")
        return ai_predicted_color
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Ollama or during API request: {e}")
        return "Error: API request failed"
    except Exception as e:
        print(f"Error processing AI prediction for {image_path}: {e}")
        return "Error: Prediction processing failed"

# --- HTML Report Generation ---
def generate_html_report(image_details, output_dir, test_run_timestamp):
    report_filename = "report.html"
    report_filepath = os.path.join(output_dir, report_filename)
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meccanoid Eye Color Test Report - {test_run_timestamp}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f0f2f5; color: #333; }}
        .container {{ background-color: #ffffff; padding: 25px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); max-width: 900px; margin: auto; }}
        h1 {{ color: #1d3557; text-align: center; }}
        h2 {{ color: #457b9d; }}
        .test-case {{ 
            border: 1px solid #d1d1d1; margin-bottom: 25px; padding: 20px; 
            border-radius: 8px; background-color: #fdfdfd; 
            transition: box-shadow 0.3s ease;
        }}
        .test-case:hover {{ box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .test-case img {{ 
            max-width: 100%; height: auto; display: block; margin: 15px auto;
            border: 2px solid #e0e0e0; border-radius: 5px; 
        }}
        .test-case h3 {{ margin-top: 0; font-size: 1.3em; color: #1d3557; }}
        .test-case p {{ margin-bottom: 5px; }}
        .controls label {{ margin-right: 20px; font-weight: 500; cursor: pointer; }}
        .controls input[type="radio"] {{ margin-right: 7px; vertical-align: middle; }}
        button#saveResultsBtn {{
            background-color: #2a9d8f; color: white; padding: 12px 20px;
            border: none; border-radius: 5px; cursor: pointer; font-size: 1.05em; 
            display: block; margin: 30px auto 10px auto; transition: background-color 0.3s ease;
        }}
        button#saveResultsBtn:hover {{ background-color: #21867a; }}
        .filename {{ font-family: "Courier New", Courier, monospace; font-size: 0.95em; color: #588157; background-color: #f0f0f0; padding: 2px 5px; border-radius:3px;}}
        .ai-prediction {{ font-weight: bold; }}
        .ai-pass {{ color: green; }}
        .ai-fail {{ color: red; }}
        .ai-error {{ color: orange; }}
        p {{ line-height: 1.6; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Meccanoid Eye Color Test Report</h1>
        <p><strong>Test Run ID:</strong> {test_run_timestamp}</p>
        <p>Please review each image below. For each test case, select "Pass" if the robot's eye color in the image matches the expected color, or "Fail" otherwise. Once all images are reviewed, click the "Save Results as CSV" button to download a summary of your assessment.</p>

        <div id="test-cases-container">
"""

    for i, detail in enumerate(image_details):
        img_filename_base = os.path.basename(detail["filename"])
        expected_color = detail["color_name"]
        ai_predicted_color = detail.get("ai_prediction", "N/A")
        ai_status_class = ""
        if ai_predicted_color.startswith("Error:"):
            ai_status_class = "ai-error"
        elif ai_predicted_color == expected_color:
            ai_status_class = "ai-pass"
        elif ai_predicted_color != "N/A":
            ai_status_class = "ai-fail"

        html_content += f"""
            <div class="test-case" id="case-{i}">
                <h3>Test Case: {expected_color.capitalize()}</h3>
                <p>Image File: <span class="filename">{img_filename_base}</span></p>
                <p>Expected Color: {expected_color.capitalize()}</p>
                <p>AI Predicted Color: <span class="ai-prediction {ai_status_class}">{ai_predicted_color.capitalize()}</span></p>
                <img src="{img_filename_base}" alt="Test image for {expected_color}">
                <div class="controls">
                    <label><input type="radio" name="status-{i}" value="Pass"> Pass</label>
                    <label><input type="radio" name="status-{i}" value="Fail"> Fail</label>
                    <label><input type="radio" name="status-{i}" value="Not Checked" checked> Not Checked</label>
                </div>
            </div>
"""

    html_content += f"""
        </div>
        <button id="saveResultsBtn" onclick="saveResults()">Save Results as CSV</button>
    </div>

    <script>
        function saveResults() {{
            const results = [];
            const headers = ["ImageFile", "ExpectedColor", "AIPredictedColor", "ManualStatus"];
            results.push(headers.join(','));

            const testCases = document.querySelectorAll('.test-case');
            testCases.forEach((tc, index) => {{
                const imgFilename = tc.querySelector('.filename').textContent;
                const expectedColor = tc.querySelector('h3').textContent.replace('Test Case: ', '').toLowerCase();
                const aiPredictionElement = tc.querySelector('.ai-prediction');
                const aiPredictedColor = aiPredictionElement ? aiPredictionElement.textContent.toLowerCase() : 'N/A';
                const statusInput = tc.querySelector('input[name="status-' + index + '"]:checked');
                const status = statusInput ? statusInput.value : 'Not Checked';
                results.push([imgFilename, expectedColor, aiPredictedColor, status].map(val => `"${{val.replace(/"/g, '""')}}"`).join(','));
            }});

            const csvContent = results.join('\\n');
            const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
            const link = document.createElement("a");
            if (link.download !== undefined) {{
                const url = URL.createObjectURL(blob);
                link.setAttribute("href", url);
                link.setAttribute("download", "test_summary_{test_run_timestamp}.csv");
                link.style.visibility = 'hidden';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(url);
            }} else {{
                alert("Your browser does not support automatic downloads. CSV content will be logged to console.");
                console.log("CSV Content:\\n" + csvContent);
            }}
        }}
    </script>
</body>
</html>
"""
    with open(report_filepath, "w") as f:
        f.write(html_content)
    print(f"\nHTML report generated: {report_filepath}")
    print(f"Open this file in a web browser to review results and save the summary.")

async def run_eye_color_test():
    initialize_sounds() # Create sound objects

    timestamp_run = datetime.now().strftime("%Y%m%d_%H%M%S")
    current_test_run_dir = os.path.join(BASE_OUTPUT_DIR, timestamp_run)
    os.makedirs(current_test_run_dir, exist_ok=True)
    print(f"Saving test images and report to: {current_test_run_dir}")

    robot = RobotControl(MECCANOID_DEVICE_ADDRESS)
    
    print("\nPlease position the Meccanoid's eyes clearly in front of the webcam.")
    print("The test will start in 5 seconds, cycling through colors...")
    time.sleep(5) 

    captured_image_details = []
    cap = None # Initialize cap to None

    try:
        if await robot.connect():
            print("Successfully connected to Meccanoid. Waiting 2 seconds for connection to stabilize...")
            await asyncio.sleep(2) 
            print("Initializing robot...")
            if not await robot.initialize_robot():
                print("Failed to send handshake command to robot. Aborting test.")
            else:
                await asyncio.sleep(0.2) # Short pause after handshake
                play_command_ack_beep()
                await asyncio.sleep(0.8) # Wait for beep and robot to be ready

                for color_name, (r, g, b) in COLORS_TO_TEST.items():
                    print(f"\nAttempting to set eye color to: {color_name} (R:{r}, G:{g}, B:{b})")
                    if not await robot.set_eye_color(r, g, b):
                        print(f"Failed to send command to set eye color to {color_name}.")
                        await asyncio.sleep(1) 
                        continue 
                    
                    play_command_ack_beep()
                    print("Command sent. Waiting 3 seconds for color to change...")
                    await asyncio.sleep(3) 

                    print("Preparing for capture...")
                    play_pre_capture_beeps() 
                    
                    # Initialize webcam for this capture
                    cap = cv2.VideoCapture(0)
                    if not cap.isOpened():
                        print(f"Error: Could not open webcam for color {color_name}. Skipping capture.")
                        if cap: cap.release() # Release if it was partially opened
                        continue

                    # Wait for beeps to finish before capturing
                    if pre_capture_beep: await asyncio.sleep( (pre_capture_beep.get_length() * 3 * 0.7) + 0.2 )

                    ret, frame = cap.read()
                    if ret:
                        image_filename_base = f"eye_test_{color_name}_{timestamp_run}.png"
                        full_image_filepath = os.path.join(current_test_run_dir, image_filename_base)
                        cv2.imwrite(full_image_filepath, frame)
                        print(f"Saved image: {full_image_filepath}")
                        
                        # Get AI prediction
                        ai_prediction = await get_ai_color_prediction(full_image_filepath)
                        captured_image_details.append({
                            "filename": full_image_filepath, 
                            "color_name": color_name,
                            "ai_prediction": ai_prediction
                        })
                    else:
                        print(f"Error: Could not capture image from webcam for color {color_name}.")
                        captured_image_details.append({
                            "filename": "N/A", 
                            "color_name": color_name,
                            "ai_prediction": "Error: Image capture failed"
                        })
                    
                    if cap: cap.release() # Release webcam after capture
                    cap = None # Reset cap variable
                    
                    await asyncio.sleep(0.5) # Small delay before proceeding

                print("\nEye color test sequence finished.")
                await robot.set_eye_color(0,0,0) # Turn eyes off
                play_command_ack_beep()
                await asyncio.sleep(0.5)
        else:
            print("Could not connect to Meccanoid.")

    except Exception as e:
        print(f"An unexpected error occurred during the test: {e}")
    finally:
        print("Releasing any remaining webcam resources and disconnecting from Meccanoid...")
        if cap and cap.isOpened(): # Ensure cap is released if loop was exited prematurely
            cap.release()
        cv2.destroyAllWindows() 
        if robot.client and robot.client.is_connected:
            await robot.disconnect()
        
        if captured_image_details:
            generate_html_report(captured_image_details, current_test_run_dir, timestamp_run)
        else:
            print("No images were captured, so no report will be generated.")

        if pygame.mixer.get_init():
            pygame.mixer.quit()
        print("Test script finished.")

if __name__ == "__main__":
    if MECCANOID_DEVICE_ADDRESS == "XX:XX:XX:XX:XX:XX" or not MECCANOID_DEVICE_ADDRESS:
        print("Error: Please update MECCANOID_DEVICE_ADDRESS in the script.")
    else:
        asyncio.run(run_eye_color_test())
