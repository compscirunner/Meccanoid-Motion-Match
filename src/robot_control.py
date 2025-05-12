import asyncio
from bleak import BleakClient, BleakError

# Meccanoid BLE Service and Characteristic UUIDs
# (Vendor specific service for commands)
MECCANOID_SERVICE_UUID = "0000ffe5-0000-1000-8000-00805f9b34fb"
# (Vendor specific characteristic for sending commands)
MECCANOID_CHAR_UUID = "0000ffe9-0000-1000-8000-00805f9b34fb"

# Servo ID mapping and reversal (0-indexed)
# Based on pymecca and protocol document
# Servos that need their position value inverted (0xFF - value) if not center (0x80)
REVERSED_SERVO_INDICES = [1, 3] # Typically RIGHT_ELBOW_SERVO, LEFT_SHOULDER_SERVO

def calculate_checksum(payload_18_bytes):
    """
    Calculates the 2-byte checksum for an 18-byte Meccanoid command payload.
    """
    if len(payload_18_bytes) != 18:
        raise ValueError(f"Payload must be 18 bytes long for checksum calculation, got {len(payload_18_bytes)}")
    
    checksum_val = sum(payload_18_bytes)
    return [(checksum_val >> 8) & 0xFF, checksum_val & 0xFF] # [high_byte, low_byte]

class RobotControl:
    """
    Handles Bluetooth LE connection and command sending to the Meccanoid robot,
    adhering to the 20-byte packet structure (18-byte payload + 2-byte checksum).
    """
    def __init__(self, device_address):
        self.device_address = device_address
        self.client = None

        # Initialize robot state
        # Servos: 8 servos, default to center position (0x80)
        self.servo_positions = [0x80] * 8
        # Servo LED modes: 8 servo LEDs, default mode 0x01 (normal operation) or 0x04 (pymecca default for color)
        self.servo_led_modes = [0x04] * 8 # Using 0x04 as per pymecca for set servo lights
        # Servo LED colors: 8 servo LEDs, default to 0x00 (Off)
        self.servo_led_colors = [0x00] * 8
        # Foot LEDs: Default to 0x01 (pymecca initialization)
        self.foot_leds_byte = 0x01 # This is a single byte in the servo command
        
        # Chest LEDs: 4 LEDs, default to 0x00 (Off)
        self.chest_led_status = [0x00] * 4
        
        # Eye color: R, G, B components (0-7), default to off
        self.eye_r, self.eye_g, self.eye_b = 0, 0, 0

    async def connect(self):
        """
        Connects to the Meccanoid robot.
        Returns True if connection is successful, False otherwise.
        """
        try:
            self.client = BleakClient(self.device_address)
            await self.client.connect()
            print(f"Successfully connected to {self.device_address}")
            return self.client.is_connected
        except BleakError as e:
            print(f"BleakError during connect: {e}")
            self.client = None
            return False
        except Exception as e:
            print(f"An unexpected error occurred during connect: {e}")
            self.client = None
            return False

    async def disconnect(self):
        """
        Disconnects from the Meccanoid robot.
        """
        if self.client and self.client.is_connected:
            try:
                await self.client.disconnect()
                print("Successfully disconnected.")
            except BleakError as e:
                print(f"BleakError during disconnect: {e}")
            except Exception as e:
                print(f"An unexpected error occurred during disconnect: {e}")
        self.client = None

    async def send_command(self, command_payload_18_bytes):
        """
        Sends an 18-byte command payload to the Meccanoid, automatically calculating
        and appending the 2-byte checksum to form a 20-byte packet.

        Args:
            command_payload_18_bytes (list[int]): The 18-byte list of bytes representing the command.

        Returns:
            bool: True if the command was sent successfully, False otherwise.
        """
        if not self.client or not self.client.is_connected:
            print("Not connected to Meccanoid. Cannot send command.")
            return False

        if len(command_payload_18_bytes) != 18:
            print(f"Error: Command payload must be 18 bytes long, got {len(command_payload_18_bytes)} bytes.")
            return False

        try:
            checksum_bytes = calculate_checksum(command_payload_18_bytes)
            full_message_20_bytes = bytes(command_payload_18_bytes + checksum_bytes)
            
            print(f"Sending command ({len(full_message_20_bytes)} bytes): {full_message_20_bytes.hex().upper()}")
            await self.client.write_gatt_char(MECCANOID_CHAR_UUID, full_message_20_bytes, response=False)
            return True
        except BleakError as e:
            print(f"BleakError sending command: {e}")
            return False
        except ValueError as e: # Catch checksum calculation errors
            print(f"ValueError: {e}")
            return False
        except Exception as e:
            print(f"An unexpected error occurred sending command: {e}")
            return False

    async def initialize_robot(self):
        """
        Sends the wake/handshake command to the robot.
        """
        print("Sending Wake/Handshake command...")
        # Payload from docs: [0x0d, 0x00, 0x00, 0x00, 0x00, 0xff, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        handshake_payload = [
            0x0d, 0x00, 0x00, 0x00, 0x00, 0xff, 0xff, 0x00, 
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
            0x00, 0x00
        ]
        return await self.send_command(handshake_payload)

    async def set_servo_position(self, servo_index, position):
        """
        Sets the position of a specific servo. This command updates all servos.
        The Meccanoid protocol for setting servos (0x08) updates all servos and their LED modes at once.

        Args:
            servo_index (int): The index of the servo (0-7).
            position (int): The target position (0-255). 0x80 is typically center.
        """
        if not (0 <= servo_index <= 7):
            print(f"Invalid servo index: {servo_index}. Must be 0-7.")
            return False
        if not (0 <= position <= 255): # Protocol uses 0x00-0xFF for servo positions
            print(f"Invalid servo position: {position}. Must be 0-255.")
            return False

        actual_position = position
        if servo_index in REVERSED_SERVO_INDICES and position != 0x80:
            actual_position = 0xFF - position
            print(f"Servo {servo_index} is reversed. Original pos: {position}, Sent pos: {actual_position}")
        
        self.servo_positions[servo_index] = actual_position
        
        # Construct the full 18-byte payload for command 0x08
        # [0x08, S0_pos...S7_pos, L0_mode...L7_mode, Foot_LEDs]
        payload = [0x08] + self.servo_positions + self.servo_led_modes + [self.foot_leds_byte]
        
        print(f"Setting servo {servo_index} to position {position} (sent as {actual_position}). Full servo payload: {payload}")
        return await self.send_command(payload)

    async def set_all_servos_raw(self, positions_8_bytes, led_modes_8_bytes=None, foot_leds_byte=None):
        """
        Advanced: Sets all servo positions, LED modes, and foot LEDs with raw byte arrays.
        Useful for defining full poses quickly.
        """
        if len(positions_8_bytes) != 8:
            print("Error: positions_8_bytes must be a list of 8 values.")
            return False
        
        self.servo_positions = list(positions_8_bytes) # Ensure it's a list and copy

        if led_modes_8_bytes is not None:
            if len(led_modes_8_bytes) != 8:
                print("Error: led_modes_8_bytes must be a list of 8 values if provided.")
                return False
            self.servo_led_modes = list(led_modes_8_bytes)
        
        if foot_leds_byte is not None:
            self.foot_leds_byte = foot_leds_byte

        payload = [0x08] + self.servo_positions + self.servo_led_modes + [self.foot_leds_byte]
        print(f"Setting all servos raw. Payload: {payload}")
        return await self.send_command(payload)

    async def set_eye_color(self, r, g, b):
        """
        Sets the color of the Meccanoid's eyes.
        Args:
            r, g, b (int): Red, Green, Blue components, each 0-7.
        """
        if not (0 <= r <= 7 and 0 <= g <= 7 and 0 <= b <= 7):
            print("Invalid RGB values for eyes. Must be 0-7 for each component.")
            return False
        
        self.eye_r, self.eye_g, self.eye_b = r, g, b
        
        # Payload: [0x11, 0x00, 0x00, (G << 3) | R, B, 0x00, ..., 0x00] (18 bytes)
        payload = [0x00] * 18
        payload[0] = 0x11
        # payload[1] = 0x00 (already set)
        # payload[2] = 0x00 (already set)
        payload[3] = (g << 3) | r
        payload[4] = b
        # Remaining bytes (5-17) are 0x00

        print(f"Setting eye color to R:{r} G:{g} B:{b}. Payload: {payload}")
        return await self.send_command(payload)

    async def set_servo_led_color(self, servo_index, color_code, mode=None):
        """
        Sets the color and optionally mode of a specific servo's LED.
        This command updates all servo LEDs.

        Args:
            servo_index (int): The index of the servo LED (0-7).
            color_code (int): Color code (0=Off, 1=R, 2=G, 3=Y, 4=B, 5=M, 6=C, 7=W).
            mode (int, optional): Mode for this servo's LED (e.g., 0x04). Defaults to current.
        """
        if not (0 <= servo_index <= 7):
            print(f"Invalid servo LED index: {servo_index}. Must be 0-7.")
            return False
        if not (0 <= color_code <= 7):
            print(f"Invalid servo LED color code: {color_code}. Must be 0-7.")
            return False
        
        self.servo_led_colors[servo_index] = color_code
        if mode is not None:
            if not (0 <= mode <= 255): # Mode is a byte
                 print(f"Invalid servo LED mode: {mode}. Must be 0-255.")
                 return False
            self.servo_led_modes[servo_index] = mode
            
        # Payload: [0x0C, SL0_color...SL7_color, M0_mode...M7_mode, LastByte]
        # LastByte is 0x00 from pymecca example
        payload = [0x0C] + self.servo_led_colors + self.servo_led_modes + [0x00]
        
        print(f"Setting servo {servo_index} LED to color {color_code}, mode {self.servo_led_modes[servo_index]}. Full LED payload: {payload}")
        return await self.send_command(payload)

    async def set_all_servo_leds_raw(self, colors_8_bytes, modes_8_bytes=None, last_byte=0x00):
        """
        Advanced: Sets all servo LED colors, modes, and the last byte directly.
        """
        if len(colors_8_bytes) != 8:
            print("Error: colors_8_bytes must be a list of 8 values.")
            return False
        self.servo_led_colors = list(colors_8_bytes)

        if modes_8_bytes is not None:
            if len(modes_8_bytes) != 8:
                print("Error: modes_8_bytes must be a list of 8 values if provided.")
                return False
            self.servo_led_modes = list(modes_8_bytes)
        
        payload = [0x0C] + self.servo_led_colors + self.servo_led_modes + [last_byte]
        print(f"Setting all servo LEDs raw. Payload: {payload}")
        return await self.send_command(payload)

    async def set_chest_led(self, led_index, status):
        """
        Sets the status of a specific chest LED.
        Args:
            led_index (int): Index of the chest LED (0-3).
            status (int): 0 for Off, 1 for On.
        """
        if not (0 <= led_index <= 3):
            print(f"Invalid chest LED index: {led_index}. Must be 0-3.")
            return False
        if status not in [0, 1]:
            print(f"Invalid chest LED status: {status}. Must be 0 or 1.")
            return False
            
        self.chest_led_status[led_index] = status
        
        # Payload: [0x1C, L0_status, L1_status, L2_status, L3_status, 0x00 ... 0x00] (18 bytes)
        payload = [0x00] * 18
        payload[0] = 0x1C
        for i in range(4):
            payload[i+1] = self.chest_led_status[i]
        # Remaining bytes (5-17) are 0x00
        
        print(f"Setting chest LED {led_index} to status {status}. Full chest LED payload: {payload}")
        return await self.send_command(payload)

async def main():
    """
    Example usage of the RobotControl class.
    Requires the Meccanoid's MAC address.
    """
    MECCANOID_DEVICE_ADDRESS = "5C:F8:21:EF:ED:D1" # Replace if different

    if MECCANOID_DEVICE_ADDRESS == "XX:XX:XX:XX:XX:XX" or not MECCANOID_DEVICE_ADDRESS:
        print("Please update MECCANOID_DEVICE_ADDRESS in the main() function.")
        return

    robot = RobotControl(MECCANOID_DEVICE_ADDRESS)

    try:
        if await robot.connect():
            print("Connected. Initializing robot...")
            if not await robot.initialize_robot():
                print("Failed to send handshake.")
                return # Don't proceed if handshake fails
            await asyncio.sleep(1) # Give time for handshake to be processed

            print("\n--- Testing Eye Color ---")
            await robot.set_eye_color(r=7, g=0, b=0) # Red
            await asyncio.sleep(2)
            await robot.set_eye_color(r=0, g=7, b=0) # Green
            await asyncio.sleep(2)
            await robot.set_eye_color(r=0, g=0, b=7) # Blue
            await asyncio.sleep(2)
            await robot.set_eye_color(r=0, g=0, b=0) # Off
            await asyncio.sleep(1)

            print("\n--- Testing Chest LEDs ---")
            # await robot.set_chest_led(led_index=0, status=1) # LED 0 On
            # await asyncio.sleep(1)
            # await robot.set_chest_led(led_index=1, status=1) # LED 1 On
            # await asyncio.sleep(1)
            # await robot.set_chest_led(led_index=0, status=0) # LED 0 Off
            # await asyncio.sleep(1)
            # await robot.set_chest_led(led_index=1, status=0) # LED 1 Off
            # await asyncio.sleep(1)

            print("\n--- Testing Servo LED Color ---")
            # # Servo LED Colors: 0=Off, 1=R, 2=G, 3=Y, 4=B, 5=M, 6=C, 7=W
            # await robot.set_servo_led_color(servo_index=0, color_code=1) # Servo 0 LED Red
            # await asyncio.sleep(1)
            # await robot.set_servo_led_color(servo_index=2, color_code=4) # Servo 2 LED Blue
            # await asyncio.sleep(1)
            # await robot.set_servo_led_color(servo_index=0, color_code=0) # Servo 0 LED Off
            # await asyncio.sleep(1)
            # await robot.set_servo_led_color(servo_index=2, color_code=0) # Servo 2 LED Off
            # await asyncio.sleep(1)

            print("\n--- Testing Servo Control ---")
            # print("Centering all servos initially (using default state)...")
            # # This will send the default center positions [0x80]*8
            # # and default LED modes [0x04]*8
            # initial_servo_payload = [0x08] + robot.servo_positions + robot.servo_led_modes + [robot.foot_leds_byte]
            # await robot.send_command(initial_servo_payload)
            # await asyncio.sleep(2)

            # print("Moving Servo 0 (e.g., an arm servo) to 90 degrees (approx 0x40) and back to center (0x80)")
            # await robot.set_servo_position(servo_index=0, position=0x40) # Move to 0x40
            # await asyncio.sleep(2)
            # await robot.set_servo_position(servo_index=0, position=0xC0) # Move to 0xC0
            # await asyncio.sleep(2)
            # await robot.set_servo_position(servo_index=0, position=0x80) # Back to center
            # await asyncio.sleep(2)
            
            # print("Moving Servo 1 (e.g., RIGHT_ELBOW, reversed) to 90 degrees (approx 0x40) and back to center (0x80)")
            # # For reversed servo 1, to get to an effective 0x40, we send 0xFF - 0x40 = 0xBF
            # # To get to an effective 0xC0, we send 0xFF - 0xC0 = 0x3F
            # await robot.set_servo_position(servo_index=1, position=0x40) # Effective 0x40 (sends 0xBF)
            # await asyncio.sleep(2)
            # await robot.set_servo_position(servo_index=1, position=0xC0) # Effective 0xC0 (sends 0x3F)
            # await asyncio.sleep(2)
            # await robot.set_servo_position(servo_index=1, position=0x80) # Back to center (sends 0x80)
            # await asyncio.sleep(2)

            print("\n--- Example commands finished ---")
            print("Uncomment the test commands in main() to try them with your robot.")
            print("Ensure servo indices and positions are safe for your robot's build.")

    except Exception as e:
        print(f"An error occurred in main: {e}")
    finally:
        print("Disconnecting...")
        await robot.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
