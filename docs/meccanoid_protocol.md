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

-   **Payload Structure:** `[0x11, 0x00, 0x00, (G << 3) | R, B, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]`
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
        -   **Note on Reversal:** Some servos might be mechanically reversed. For `LEFT_SHOULDER_SERVO` (ID 3) and `RIGHT_ELBOW_SERVO` (ID 1), if the desired position is not center (`0x80`), the value sent should be `0xFF - desired_position`.
    -   Bytes 9-16 (`L0_mode` to `L7_mode`): Mode for the LEDs in each servo (0-7). Typically `0x01` for normal operation, but can also control color/pattern. The `pymecca` library initializes these to `0x01`.
    -   Byte 17 (`Foot_LEDs`): Controls LEDs in the feet, if present. `pymecca` initializes this to `0x01`.

    *Initial state from `pymecca` for servo positions (used for arm waggle after "I'm awake")*:
    `[0x08, 0x7f, 0x80, 0x00, 0xff, 0x80, 0x7f, 0x7f, 0x7f, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01]`

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

Based on `pymecca` library:
-   `0`: UNKNOWN0_SERVO
-   `1`: RIGHT_ELBOW_SERVO (Reversed logic: `0xFF - value` if not `0x80`)
-   `2`: RIGHT_SHOULDER_SERVO
-   `3`: LEFT_SHOULDER_SERVO (Reversed logic: `0xFF - value` if not `0x80`)
-   `4`: LEFT_ELBOW_SERVO
-   `5`: UNKNOWN5_SERVO
-   `6`: UNKNOWN6_SERVO
-   `7`: UNKNOWN7_SERVO

