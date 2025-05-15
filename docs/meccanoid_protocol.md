# Meccanoid G15KS/2.0 Communication Protocol

This document outlines the Bluetooth LE communication protocol for the Meccanoid G15KS/2.0 robot, based on community findings and existing implementations.

## 1. BLE Connection Details

-   **Service UUID:** `0000ffe5-0000-1000-8000-00805f9b34fb`
-   **Characteristic UUID (for commands):** `0000ffe9-0000-1000-8000-00805f9b34fb` (Writeable)

## 2. General Command Format

All commands are sent as a byte array to the command characteristic.
The command packet is typically 20 bytes long:
-   **18 bytes:** Command and data payload.
-   **2 bytes:** Checksum (sum of the previous 18 bytes).

### Checksum Calculation

The checksum is a 16-bit value, calculated by summing all 18 bytes of the command/data payload. This sum is then appended to the payload as two bytes (high byte first, then low byte).

```javascript
// Example Checksum Calculation (JavaScript)
function calculateChecksum(data) { // data is an array of 18 bytes
    const sum = data.reduce((a, b) => a + b, 0);
    return [sum >> 8, sum & 0xFF]; // [highByte, lowByte]
}
```

```python
# Example Checksum Calculation (Python)
def calculate_checksum(data): # data is a list or tuple of 18 bytes
    checksum = 0
    for v in data:
        checksum += v
    return [(checksum >> 8) & 0xff, checksum & 0xff] # [highByte, lowByte]
```

A full command to send would be: `[...18_byte_payload..., checksum_high_byte, checksum_low_byte]`

## 3. Specific Commands (18-byte payloads)

All payloads listed below are 18 bytes long. The 2-byte checksum must be calculated and appended before sending.

### 3.1. Wake / Handshake (Initialize Connection)

This command is often sent upon connection to make the Meccanoid acknowledge the connection. It's effectively a "move wheels with zero speed" command.

-   **Payload:** `[0x0d, 0x00, 0x00, 0x00, 0x00, 0xff, 0xff, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]`

### 3.2. Set Eye Color

Controls the RGB color of the Meccanoid's eyes.

-   **Payload Structure:** `[0x11, 0x00, 0x00, (G << 3) | R, B, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]`
    -   `R`, `G`, `B`: Red, Green, Blue components, each ranging from `0x0` (off) to `0x7` (max intensity).
    -   Byte 3: `(G << 3) | R`
    -   Byte 4: `B`

### 3.3. Play Sound

Plays pre-programmed sounds.

-   **"I'm Awake" / Yawn Sound (Type 0x19):**
    -   **Payload:** `[0x19, 0x1d, 0x1d, 0x1d, 0x1d, 0x1d, 0x1d, 0x1d, 0x1d, 0x1d, 0x1d, 0x1d, 0x1d, 0x1d, 0x1d, 0x1d, 0x1d, 0x1d]`
-   **Other Sounds (e.g., 0x15, 0x16, 0x1c):**
    -   **Payload Structure:** `[sound_type, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]`
        -   `sound_type`: The byte code for the specific sound.

### 3.4. Set Servos (All Servos)

Sets the position of all 8 possible servos.

-   **Payload Structure:** `[0x08, S0_pos, S1_pos, S2_pos, S3_pos, S4_pos, S5_pos, S6_pos, S7_pos, L0_mode, L1_mode, L2_mode, L3_mode, L4_mode, L5_mode, L6_mode, L7_mode, Foot_LEDs]`
    -   Byte 0: `0x08` (Command type for setting servos)
    -   Bytes 1-8 (`S0_pos` to `S7_pos`): Position for servos 0 through 7. Value from `0x00` to `0xFF`. `0x80` is typically center.
        -   **Note on Position Values:** Standard range is:
            -   `0x40` (64): Minimum position
            -   `0x80` (128): Center/neutral position
            -   `0xC0` (192): Maximum position
        -   **Note on Original Documentation:** The original documentation mentioned reversed logic for some servos. Our testing has shown this is NOT necessary with the correct servo mapping.
    -   Bytes 9-16 (`L0_mode` to `L7_mode`): Mode for the LEDs in each servo (0-7). Typically `0x01` for normal operation, but can also control color/pattern. The `pymecca` library initializes these to `0x01`.
    -   Byte 17 (`Foot_LEDs`): Controls LEDs in the feet, if present. `pymecca` initializes this to `0x01`.

    *Initial state from `pymecca` for servo positions (used for arm waggle after "I'm awake")*:
    `[0x08, 0x7f, 0x80, 0x00, 0xff, 0x80, 0x7f, 0x7f, 0x7f, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01]`
    
    *Corrected servo positions for neutral stance (based on our testing)*:
    `[0x08, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01]`

### 3.5. Set Servo Lights (All Servo LEDs)

Controls the color of the LEDs integrated into each of the 8 servo modules.

-   **Payload Structure:** `[0x0C, SL0_color, SL1_color, SL2_color, SL3_color, SL4_color, SL5_color, SL6_color, SL7_color, M1, M2, M3, M4, M5, M6, M7, M8, LastByte]`
    -   Byte 0: `0x0C` (Command type for servo lights)
    -   Bytes 1-8 (`SL0_color` to `SL7_color`): Color for servo LEDs 0 through 7.
        -   `0x00`: Off/Black
        -   `0x01`: Red
        -   `0x02`: Green
        -   `0x03`: Yellow
        -   `0x04`: Blue
        -   `0x05`: Magenta
        -   `0x06`: Cyan
        -   `0x07`: White
    -   Bytes 9-16 (`M1` to `M8`): Mode bytes, `pymecca` sets these to `0x04`.
    -   Byte 17 (`LastByte`): `pymecca` sets this to `0x00`.

    *Initial state from `pymecca` for servo lights*:
    `[0x0c, 0x00, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x00]`


### 3.6. Set Chest Lights

Controls the 4 LEDs on the Meccanoid's chest.

-   **Payload Structure:** `[0x1C, L0_status, L1_status, L2_status, L3_status, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]`
    -   Byte 0: `0x1C` (Command type for chest lights)
    -   Bytes 1-4 (`L0_status` to `L3_status`): Status for chest lights 0 to 3.
        -   `0x00`: Off
        -   `0x01`: On
    -   Remaining bytes are `0x00`.

### 3.7. Move Wheels

Controls the speed and direction of the two drive motors.

-   **Payload Structure:** `[0x0D, left_dir, right_dir, left_speed, right_speed, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]`
    -   Byte 0: `0x0D` (Command type for wheel movement)
    -   `left_dir`, `right_dir`:
        -   `0x00`: Stop (when speed is also 0)
        -   `0x01`: Forward
        -   `0x02`: Backward
    -   `left_speed`, `right_speed`: Speed from `0x00` (stop) to `0xFF` (max speed).
    -   Bytes 5 and 6 are `0xFF`.
    -   Remaining bytes are `0x00`.

## 4. Servo ID Mapping (0-indexed)

Previous mapping from `pymecca` library (which we found to be incorrect):
-   `0`: UNKNOWN0_SERVO
-   `1`: RIGHT_ELBOW_SERVO (Reversed logic: `0xFF - value` if not `0x80`)
-   `2`: RIGHT_SHOULDER_SERVO
-   `3`: LEFT_SHOULDER_SERVO (Reversed logic: `0xFF - value` if not `0x80`)
-   `4`: LEFT_ELBOW_SERVO
-   `5`: UNKNOWN5_SERVO
-   `6`: UNKNOWN6_SERVO
-   `7`: UNKNOWN7_SERVO

### Corrected Servo Mapping (Based on Extensive Testing)

Through rigorous testing with a diagnostic interface, we discovered the actual mapping:
-   `0`: UNKNOWN_SERVO (Appears to briefly move both arms to T position when commanded)
-   `1`: RIGHT_ELBOW_SERVO
-   `2`: RIGHT_SHOULDER_SERVO
-   `3`: LEFT_SHOULDER_SERVO
-   `4`: LEFT_ELBOW_SERVO
-   `5`: UNKNOWN5_SERVO (No observed function)
-   `6`: UNKNOWN6_SERVO (No observed function)
-   `7`: UNKNOWN7_SERVO (No observed function)

### Key Findings:

1. The left elbow is controlled by servo index 4 (NOT index 3 as previously documented)
2. No reverse logic is needed for any of the servos in the standard configuration
3. We implemented an optional inversion toggle for the left elbow in case the physical build requires it
4. Values of 0x40, 0x80, and 0xC0 represent min, center, and max positions respectively

### Directional Reference:

1. **Right Elbow (Servo 1)**:
   - 0x40: Elbow out/extended
   - 0xC0: Elbow in/bent

2. **Right Shoulder (Servo 2)**:
   - 0x40: Shoulder down
   - 0x80: Shoulder center
   - 0xC0: Shoulder up

3. **Left Shoulder (Servo 3)**:
   - 0x40: Shoulder up
   - 0x80: Shoulder center
   - 0xC0: Shoulder down

4. **Left Elbow (Servo 4)**:
   - 0x40: Elbow in/bent
   - 0x80: Elbow center
   - 0xC0: Elbow out/extended

## 5. Working Implementation Examples

Based on our testing, here are working implementations for controlling the Meccanoid robot:

### 5.1 JavaScript Implementation (Web Bluetooth)

```javascript
// Function to move a single servo
async function moveServo(servoNum, position) {
    // Create a command with neutral positions for all servos
    const command = new Uint8Array([
        0x08, // Command code for servo control
        0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, // Default positions (all neutral)
        0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01  // LED modes
    ]);
    
    // Set the position for the target servo
    command[servoNum] = position;
    
    // Calculate checksum
    const sum = command.reduce((a, b) => a + b, 0);
    const checksum = [sum >> 8, sum & 0xFF];
    
    // Construct the full command with checksum
    const fullCommand = new Uint8Array([...command, ...checksum]);
    
    // Send via Bluetooth
    await characteristic.writeValue(fullCommand);
}

// Example: Wave animation using the correct servo mapping
async function waveAnimation() {
    await moveServo(1, 0x80); // Center right elbow
    await moveServo(2, 0xC0); // Raise right shoulder
    
    // Wave the right arm a few times
    for (let i = 0; i < 3; i++) {
        await moveServo(1, 0x40); // Move right elbow out
        await new Promise(resolve => setTimeout(resolve, 300));
        await moveServo(1, 0xC0); // Move right elbow in
        await new Promise(resolve => setTimeout(resolve, 300));
    }
    
    // Return to neutral position
    await moveServo(1, 0x80); // Center right elbow
    await moveServo(2, 0x80); // Center right shoulder
}
```

### 5.2 Python Implementation

```python
import time

# Hypothetical Bluetooth library and connection
# bluetooth_characteristic = ...

def calculate_checksum(data):
    """Calculate the checksum for a Meccanoid command."""
    total = sum(data)
    return [(total >> 8) & 0xFF, total & 0xFF]

def move_servo(servo_num, position):
    """Move a single servo to the specified position."""
    # Create command with neutral positions for all servos
    command = [0x08] + [0x80] * 8 + [0x01] * 9
    
    # Set the position for the target servo
    command[servo_num] = position
    
    # Calculate checksum
    checksum = calculate_checksum(command)
    
    # Construct and send the full command
    full_command = command + checksum
    # bluetooth_characteristic.write_value(bytearray(full_command))
    
    # For debugging
    print(f"Moving servo {servo_num} to position {hex(position)}")
    print(f"Command: {[hex(b) for b in full_command]}")
    
    return full_command

def wave_animation():
    """Execute a wave animation using the correct servo mapping."""
    # Center right elbow, raise right shoulder
    move_servo(1, 0x80)  # Center right elbow
    move_servo(2, 0xC0)  # Raise right shoulder
    time.sleep(0.5)
    
    # Wave the right arm
    for _ in range(3):
        move_servo(1, 0x40)  # Move right elbow out
        time.sleep(0.3)
        move_servo(1, 0xC0)  # Move right elbow in
        time.sleep(0.3)
    
    # Return to neutral position
    move_servo(1, 0x80)  # Center right elbow
    move_servo(2, 0x80)  # Center right shoulder
```

## 6. Common Animation Patterns

Based on our testing, here are some common animation patterns that work well with the Meccanoid:

### 6.1. Wave Hello

```
1. Center right elbow (Servo 1: 0x80)
2. Raise right shoulder (Servo 2: 0xC0)
3. Move right elbow out (Servo 1: 0x40)
4. Move right elbow in (Servo 1: 0xC0)
5. Repeat steps 3-4 a few times
6. Return to neutral position
```

### 6.2. Nod Yes

```
1. Move left shoulder up (Servo 3: 0x40)
2. Move left shoulder down (Servo 3: 0xA0)
3. Repeat steps 1-2 a few times
4. Return left shoulder to center (Servo 3: 0x80)
```

### 6.3. Shake No (Head)

```
1. Move right shoulder right (Servo 2: 0x60)
2. Move right shoulder left (Servo 2: 0xA0)
3. Repeat steps 1-2 a few times
4. Return right shoulder to center (Servo 2: 0x80)
```

### 6.4. Dance Movement

```
1. Set right elbow out (Servo 1: 0x40)
2. Set left elbow out (Servo 4: 0xC0)
3. Set shoulders to center (Servo 2: 0x80, Servo 3: 0x80)
4. Raise arms up (Servo 2: 0xC0, Servo 3: 0x40)
5. Lower arms down (Servo 2: 0x40, Servo 3: 0xC0)
6. Repeat steps 4-5 a few times
7. Return all servos to neutral position
```

