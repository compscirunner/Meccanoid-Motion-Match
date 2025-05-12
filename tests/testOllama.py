import sys
import os
import base64
import requests
import asyncio

# Adjust Python path to find the 'src' module (though not strictly needed for this script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# --- AI Model Interaction (Ollama) ---
OLLAMA_API_URL = "http://localhost:11434/api/generate"
# Using a potentially smaller/faster model for this quick test, adjust if needed
AI_MODEL_NAME = "llava:latest" # Or use "gemma3:12b-it-qat" if you have it and prefer it
AI_PROMPT = "What is the primary color of the robot's eyes in this image? Respond with only the color name (e.g., red, green, blue, yellow, cyan, magenta, white, off/dark)."

async def get_ai_color_prediction(image_path):
    """
    Sends an image to the Ollama API and returns the predicted color.
    """
    if not os.path.exists(image_path):
        print(f"Error: Image not found at {image_path}")
        return f"Error: Image not found"

    print(f"Processing image: {os.path.basename(image_path)}")
    try:
        with open(image_path, "rb") as image_file:
            img_base64 = base64.b64encode(image_file.read()).decode('utf-8')
        
        payload = {
            "model": AI_MODEL_NAME,
            "prompt": AI_PROMPT,
            "images": [img_base64],
            "stream": False # Get the full response at once
        }
        
        # Run the blocking requests call in a separate thread
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: requests.post(OLLAMA_API_URL, json=payload, timeout=60))
        response.raise_for_status() # Raise an exception for HTTP errors
        
        response_data = response.json()
        ai_predicted_color = response_data.get("response", "Error: No response field").strip().lower()
        return ai_predicted_color
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Ollama or during API request for {os.path.basename(image_path)}: {e}")
        return "Error: API request failed"
    except Exception as e:
        print(f"Error processing AI prediction for {os.path.basename(image_path)}: {e}")
        return "Error: Prediction processing failed"

async def main():
    """
    Main function to process a list of predefined images.
    """
    # Construct paths to the images relative to this script's location
    # This script is in /tests, images are in /test_results/eye_tests/...
    image_dir = os.path.join(PROJECT_ROOT, "test_results", "eye_tests", "20250511_220939")
    
    images_to_test = [
        os.path.join(image_dir, "eye_test_blue_20250511_220939.png"),
        os.path.join(image_dir, "eye_test_red_20250511_220939.png"),
        os.path.join(image_dir, "eye_test_green_20250511_220939.png"),
        os.path.join(image_dir, "eye_test_yellow_20250511_220939.png"),
        # Add more images if you like
        # os.path.join(image_dir, "eye_test_off_20250511_220939.png"),
    ]
    
    print(f"Using Ollama model: {AI_MODEL_NAME} at {OLLAMA_API_URL}")
    print(f"Prompt: {AI_PROMPT}\n")

    for image_path in images_to_test:
        prediction = await get_ai_color_prediction(image_path)
        print(f"  > AI Prediction for {os.path.basename(image_path)}: {prediction}\n")

if __name__ == "__main__":
    # Check if Ollama is running and accessible
    try:
        requests.get(OLLAMA_API_URL.replace("/api/generate", "/api/tags"), timeout=5) # Check a benign endpoint
        print("Ollama server seems to be accessible.")
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to Ollama at {OLLAMA_API_URL}.")
        print("Please ensure Ollama is running and accessible.")
        sys.exit(1)
    
    asyncio.run(main())
    print("\nProof-of-concept script finished.")
