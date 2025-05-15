import asyncio
from bleak import BleakClient, BleakError

# Meccanoid BLE Service and Characteristic UUIDs
# (Vendor specific service for commands)
MECCANOID_SERVICE_UUID = "0000ffe5-0000-1000-8000-00805f9b34fb"
# (Vendor specific characteristic for sending commands)
MECCANOID_CHAR_UUID = "0000ffe9-0000-1000-8000-00805f9b34fb"

# Servo ID mapping for the Meccanoid robot, based on extensive testing:
# According to the Meccanoid Protocol Documentation:
# Physical Servo 0: Unknown/T-Pose
# Physical Servo 1: Right Elbow
# Physical Servo 2: Right Shoulder 
# Physical Servo 3: Left Shoulder
# Physical Servo 4: Left Elbow
# Physical Servos 5-7: No observed function

# Default position for unused servos or center position
DEFAULT_SERVO_POS = 0x80 # 128 - Neutral/center position (standard for all servos)

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
    # Define poses: [L.Shoulder(0), L.Elbow(1), R.Shoulder(2), R.Elbow(3)]
    # Values are 0-255 (0x00-0xFF). DEFAULT_SERVO_POS (0x80/128) is center.
    # Standard range positions:
    # - 0x40 (64): Minimum position
    # - 0x80 (128): Center/neutral position
    # - 0xC0 (192): Maximum position
    #
    # Directional Reference from protocol documentation:
    # - Left Shoulder: 0x40 (Up), 0x80 (Center), 0xC0 (Down)
    # - Left Elbow: 0x40 (In/Bent), 0x80 (Center), 0xC0 (Out/Extended)
    # - Right Shoulder: 0x40 (Down), 0x80 (Center), 0xC0 (Up)
    # - Right Elbow: 0x40 (Out/Extended), 0x80 (Center), 0xC0 (In/Bent)
    POSES = {
        "Neutral":          [0x80, 0x80, 0x80, 0x80], # All servos at neutral/center position
        "T_Pose":           [0x80, 0xC0, 0x80, 0x40], # Arms extended straight out to the sides (T-Pose)
        "Arms_Up":          [0x40, 0x80, 0xC0, 0x80], # Both shoulders raised, elbows straight
        "Arms_Down":        [0xC0, 0x80, 0x40, 0x80], # Both shoulders lowered, elbows straight
        "Right_Wave_High":  [0x80, 0x80, 0xC0, 0xC0], # R.Shoulder up, R.Elbow bent in
        "Right_Wave_Mid":   [0x80, 0x80, 0xC0, 0x80], # R.Shoulder up, R.Elbow straight
        "Left_Wave_High":   [0x40, 0x40, 0x80, 0x80], # L.Shoulder up, L.Elbow bent in
        "Left_Wave_Mid":    [0x40, 0x80, 0x80, 0x80], # L.Shoulder up, L.Elbow straight
        "Surrender":        [0x40, 0x40, 0xC0, 0xC0], # Both arms up, elbows bent in
        "Hug_Open":         [0x60, 0xC0, 0xA0, 0x40], # Arms somewhat forward, ready for hug
        "Hug_Close":        [0x60, 0x40, 0xA0, 0xC0], # Arms forward and bent in (hugging)
    }

    def __init__(self, device_address):
        self.device_address = device_address
        self.client = None

        # Initialize robot state
        # Servos: 8 servos, default to center position (DEFAULT_SERVO_POS)
        self.servo_positions = [DEFAULT_SERVO_POS] * 8
        # Servo LED modes: 8 servo LEDs, default mode 0x01 (normal operation)
        self.servo_led_modes = [0x01] * 8 # Using 0x01 as per protocol for normal operation
        # Servo LED colors: 8 servo LEDs, default to 0x00 (Off)
        self.servo_led_colors = [0x00] * 8
        # Foot LEDs: Default to 0x01 (standard initialization)
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
            print("ERROR: Robot not connected. Cannot send command.")
            return False

        if len(command_payload_18_bytes) != 18:
            print(f"ERROR: Command payload must be 18 bytes long, got {len(command_payload_18_bytes)} bytes. Payload: {command_payload_18_bytes}")
            return False

        try:
            # Ensure all payload elements are integers before checksum and bytes conversion
            for i, val in enumerate(command_payload_18_bytes):
                if not isinstance(val, int):
                    print(f"ERROR: Payload element at index {i} is not an integer: {val} (type: {type(val)})")
                    return False
                if not (0 <= val <= 255):
                    print(f"ERROR: Payload element at index {i} is out of byte range (0-255): {val}")
            
            checksum_bytes = calculate_checksum(command_payload_18_bytes)
            full_message_20_bytes = bytes(command_payload_18_bytes + checksum_bytes)
            
            print(f"DEBUG: Sending command ({len(full_message_20_bytes)} bytes): {full_message_20_bytes.hex().upper()}")
            await self.client.write_gatt_char(MECCANOID_CHAR_UUID, full_message_20_bytes, response=False)
            return True
        except BleakError as e:
            print(f"ERROR: BleakError sending command: {e}")
            import traceback
            traceback.print_exc()
            return False
        except ValueError as e: 
            print(f"ERROR: ValueError sending command (checksum or bytes conversion): {e}")
            import traceback
            traceback.print_exc()
            return False
        except Exception as e:
            print(f"ERROR: Unexpected error in send_command: {type(e).__name__} - {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    async def initialize_robot(self):
        """
        Sends the wake/handshake command to the robot.
        """
        print("Sending Wake/Handshake command (0x0D)...")
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
            position (int): The position value to send (0-255). DEFAULT_SERVO_POS (128) is center.
                            Based on protocol: 0x40 (min), 0x80 (center), 0xC0 (max).
        """
        if not (0 <= servo_index <= 7):
            print(f"Invalid servo index: {servo_index}. Must be 0-7.")
            return False
        if not (0 <= position <= 255): # Protocol uses 0x00-0xFF for servo positions
            print(f"Invalid servo position: {position}. Must be 0-255.")
            return False

        self.servo_positions[servo_index] = position
        
        # Construct the full 18-byte payload for command 0x08
        # [0x08, S0_pos...S7_pos, L0_mode...L7_mode, Foot_LEDs]
        payload = [0x08] + self.servo_positions + self.servo_led_modes + [self.foot_leds_byte]
        
        print(f"Setting servo {servo_index} to position {position}. Full servo payload: {payload}")
        return await self.send_command(payload)

    async def set_all_servos_raw(self, positions_8_bytes_final, led_modes_8_bytes=None, foot_leds_byte=None):
        """
        Advanced: Sets all servo positions, LED modes, and foot LEDs with raw byte arrays.
        The `positions_8_bytes_final` should contain the values exactly as they need to be sent
        to the robot (i.e., already reversed if necessary by the calling function).
        """
        if len(positions_8_bytes_final) != 8:
            print("Error: positions_8_bytes_final must be a list of 8 values.")
            return False
        
        self.servo_positions = list(positions_8_bytes_final)

        if led_modes_8_bytes is not None:
            if len(led_modes_8_bytes) != 8:
                print("Error: led_modes_8_bytes must be a list of 8 values if provided.")
                return False
            self.servo_led_modes = list(led_modes_8_bytes)
        
        if foot_leds_byte is not None:
            self.foot_leds_byte = foot_leds_byte

        payload = [0x08] + self.servo_positions + self.servo_led_modes + [self.foot_leds_byte]
        print(f"Setting all servos raw. Final payload to send: {payload}")
        return await self.send_command(payload)

    async def execute_pose(self, pose_name):
        """
        Executes a predefined pose by name.
        Maps the logical [LSh, LEl, RSh, REl] pose values to their respective
        physical servo indices [3, 4, 2, 1].
        Remaining servos default to DEFAULT_SERVO_POS.
        """
        if pose_name not in self.POSES:
            print(f"Error: Pose '{pose_name}' not defined.")
            return False

        arm_servo_targets = self.POSES[pose_name]
        if len(arm_servo_targets) != 4:
            print(f"Error: Pose definition for '{pose_name}' should have 4 servo values for the arms.")
            return False

        # Initialize all servos to neutral position
        final_positions_to_send = [DEFAULT_SERVO_POS] * 8

        print(f"Executing pose: {pose_name} with arm targets {arm_servo_targets}")

        # Map logical pose array [LSh, LEl, RSh, REl] to physical servo indices [3, 4, 2, 1]
        servo_mapping = {
            0: 3,  # Left Shoulder -> Physical Servo 3
            1: 4,  # Left Elbow -> Physical Servo 4
            2: 2,  # Right Shoulder -> Physical Servo 2
            3: 1,  # Right Elbow -> Physical Servo 1
        }
        
        for logical_idx, target_pos in enumerate(arm_servo_targets):
            if not (0 <= target_pos <= 255):
                print(f"Warning: Servo target {target_pos} for servo {logical_idx} in pose '{pose_name}' is out of 0-255 range. Sending as is.")
            
            physical_idx = servo_mapping[logical_idx]
            final_positions_to_send[physical_idx] = target_pos
            
            print(f"  Setting physical servo {physical_idx} (logical {logical_idx}) to position: {target_pos}")
        
        print(f"  Final 8 servo positions to send: {final_positions_to_send}")
        
        return await self.set_all_servos_raw(final_positions_to_send, self.servo_led_modes, self.foot_leds_byte)

    async def set_eye_color(self, r, g, b):
        """
        Sets the eye color of the Meccanoid using command 0x11.
        Also sets chest LEDs according to their current status, as command 0x11 handles both.

        Args:
            r (int): Red component (0-7).
            g (int): Green component (0-7).
            b (int): Blue component (0-7).
        """
        print(f"DEBUG: set_eye_color called with r={r}, g={g}, b={b}")
        if not all(isinstance(val, int) and 0 <= val <= 7 for val in [r, g, b]):
            print(f"ERROR: Invalid RGB values. r,g,b must be integers between 0 and 7. Got: r={r}({type(r)}), g={g}({type(g)}), b={b}({type(b)})")
            return False

        self.eye_r, self.eye_g, self.eye_b = r, g, b
        print(f"DEBUG: Stored eye_r={self.eye_r}, eye_g={self.eye_g}, eye_b={self.eye_b}")

        # Protocol for command 0x11 (Set LEDs) from docs/meccanoid_protocol.md:
        # Byte 0: 0x11 (Command ID)
        # Byte 1: Chest LED 1 (0=Off, 1=On) - Corresponds to self.chest_led_status[0]
        # Byte 2: Chest LED 2 (0=Off, 1=On) - Corresponds to self.chest_led_status[1]
        # Byte 3: (Eye G << 3) | Eye R       - Eye Green (3 bits) and Red (3 bits)
        # Byte 4: Eye B                       - Eye Blue (3 bits)
        # Byte 5: Chest LED 3 (0=Off, 1=On) - Corresponds to self.chest_led_status[2]
        # Byte 6: Chest LED 4 (0=Off, 1=On) - Corresponds to self.chest_led_status[3]
        # Byte 7-17: 0x00 (Reserved/Padding)

        r_val = self.eye_r & 0x07  # Ensure 0-7
        g_val = self.eye_g & 0x07  # Ensure 0-7
        b_val = self.eye_b & 0x07  # Ensure 0-7

        eye_byte_rg = (g_val << 3) | r_val
        eye_byte_b = b_val
        
        print(f"DEBUG: r_val={r_val}, g_val={g_val}, b_val={b_val}")
        print(f"DEBUG: Calculated eye_byte_rg: {eye_byte_rg} ({bin(eye_byte_rg)}) for payload index 3")
        print(f"DEBUG: Calculated eye_byte_b: {eye_byte_b} ({bin(eye_byte_b)}) for payload index 4")
        
        # Initialize payload with all zeros
        payload = [0x00] * 18
        
        # Set command ID
        payload[0] = 0x11
        
        # Set chest LED statuses (ensure they are 0 or 1)
        # self.chest_led_status should be [LED1_status, LED2_status, LED3_status, LED4_status]
        print(f"DEBUG: Current self.chest_led_status: {self.chest_led_status}")
        payload[1] = self.chest_led_status[0] & 0x01 # Chest LED 1
        payload[2] = self.chest_led_status[1] & 0x01 # Chest LED 2
        payload[5] = self.chest_led_status[2] & 0x01 # Chest LED 3
        payload[6] = self.chest_led_status[3] & 0x01 # Chest LED 4
        
        # Set eye color bytes
        payload[3] = eye_byte_rg
        payload[4] = eye_byte_b
        
        # Bytes 7-17 are already 0x00 from initialization
        
        print(f"INFO: Setting eye color to R:{r} G:{g} B:{b} and updating chest LEDs.")
        print(f"DEBUG: Final payload for command 0x11: {payload}")
        
        success = await self.send_command(payload)
        if not success:
            print(f"ERROR: Failed to set eye color R:{r} G:{g} B:{b} after attempting send_command.")
        return success

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
            if not (0 <= mode <= 255):
                 print(f"Invalid servo LED mode: {mode}. Must be 0-255.")
                 return False
            self.servo_led_modes[servo_index] = mode
            
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
        
        payload = [0x00] * 18
        payload[0] = 0x1C
        for i in range(4):
            payload[i+1] = self.chest_led_status[i]
        
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
                return
            await asyncio.sleep(1)

            print("\n--- Testing Eye Color ---")
            await robot.set_eye_color(r=7, g=0, b=0)
            await asyncio.sleep(2)
            await robot.set_eye_color(r=0, g=7, b=0)
            await asyncio.sleep(2)
            await robot.set_eye_color(r=0, g=0, b=7)
            await asyncio.sleep(2)
            await robot.set_eye_color(r=0, g=0, b=0)
            await asyncio.sleep(1)

            print("\n--- Testing Poses ---")
            await robot.execute_pose("T_Pose")
            await asyncio.sleep(2)
            await robot.execute_pose("Arms_Up")
            await asyncio.sleep(2)
            await robot.execute_pose("Surrender")
            await asyncio.sleep(2)
            await robot.execute_pose("Hug_Open")
            await asyncio.sleep(2)
            await robot.execute_pose("Hug_Close")
            await asyncio.sleep(2)

            print("\n--- Example commands finished ---")

    except Exception as e:
        print(f"An error occurred in main: {e}")
    finally:
        print("Disconnecting...")
        await robot.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
