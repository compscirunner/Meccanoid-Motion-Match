import os
import requests
import warnings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Default Home Assistant configuration
DEFAULT_HA_URL = "http://homeassistant.local:8123"
DEFAULT_ROBOT_SWITCH_ENTITY_ID = "switch.robot_switch"

# Load configuration from environment variables or use defaults
HA_URL = os.environ.get("HA_URL", DEFAULT_HA_URL)
HA_URL = HA_URL.replace('\\x3a', ':')  # Correct any escaped colons
HA_TOKEN = os.environ.get("HA_TOKEN")
ROBOT_SWITCH_ENTITY_ID = os.environ.get("ROBOT_SWITCH_ENTITY_ID", DEFAULT_ROBOT_SWITCH_ENTITY_ID)

HEADERS = {}
if HA_TOKEN:
    HEADERS = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }
else:
    warnings.warn("HA_TOKEN environment variable not set. Home Assistant control will not function.", UserWarning)

def set_robot_power(state: str, timeout: int = 15) -> bool:
    """
    Controls the power state of the Meccanoid robot via a Home Assistant switch.

    Args:
        state (str): The desired power state, must be "on" or "off".
        timeout (int): Timeout for the HTTP request in seconds.

    Returns:
        bool: True if the command was successful, False otherwise.
    """
    if not HA_TOKEN:
        print("Error: HA_TOKEN is not configured. Cannot control robot power.")
        return False

    # Validate HA_URL format
    if not HA_URL or not HA_URL.startswith("http"):
        print(f"Error: Invalid HA_URL '{HA_URL}'. Ensure it is correctly set in the environment.")
        return False

    if state not in ["on", "off"]:
        print(f"Error: Invalid state '{state}'. Must be 'on' or 'off'.")
        return False

    service = f"turn_{state}"
    url = f"{HA_URL}/api/services/switch/{service}"
    data = {"entity_id": ROBOT_SWITCH_ENTITY_ID}

    print(f"Attempting to turn robot power {state.upper()} via Home Assistant: {url} for entity {ROBOT_SWITCH_ENTITY_ID}")

    try:
        response = requests.post(url, headers=HEADERS, json=data, timeout=timeout)
        response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)
        
        # Check if the response content indicates success, if available and structured
        # For Home Assistant, a 200 OK is usually sufficient.
        # Some HA responses might be an empty list [] for successful service calls.
        if 200 <= response.status_code < 300:
            print(f"Robot power successfully turned {state.upper()}. Status: {response.status_code}")
            return True
        else:
            # This case might be redundant due to raise_for_status, but good for clarity
            print(f"Failed to turn robot power {state.upper()}. Status: {response.status_code}, Response: {response.text}")
            return False

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred while trying to turn robot power {state.upper()}: {http_err} - {http_err.response.text}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred while trying to turn robot power {state.upper()}: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred while trying to turn robot power {state.upper()}: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"An unexpected error occurred while trying to turn robot power {state.upper()}: {req_err}")
    
    return False

if __name__ == '__main__':
    # Example usage for direct testing of this module
    # Ensure HA_TOKEN is set as an environment variable before running
    print("Testing Home Assistant Control Module...")
    if not HA_TOKEN:
        print("Please set the HA_TOKEN environment variable to test.")
    else:
        print(f"Using HA_URL: {HA_URL}")
        print(f"Using ROBOT_SWITCH_ENTITY_ID: {ROBOT_SWITCH_ENTITY_ID}")
        
        print("\nAttempting to turn robot OFF...")
        if set_robot_power("off"):
            print("Turn OFF command successful.")
        else:
            print("Turn OFF command failed.")
        
        print("\nWaiting for 5 seconds...")
        import time
        time.sleep(5)
        
        print("\nAttempting to turn robot ON...")
        if set_robot_power("on"):
            print("Turn ON command successful.")
        else:
            print("Turn ON command failed.")
