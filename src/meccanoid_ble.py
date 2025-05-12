import asyncio
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError

# Target Meccanoid details (update if necessary)
MECCANOID_NAME_PREFIX = "MECCANOID"
# If you know your Meccanoid's MAC address, you can specify it here for a faster connection
# MECCANOID_MAC_ADDRESS = "XX:XX:XX:XX:XX:XX" # Replace with actual MAC address
MECCANOID_MAC_ADDRESS = None 

async def scan_and_connect():
    print("Scanning for Bluetooth LE devices...")
    try:
        devices = await BleakScanner.discover(timeout=10.0)
    except BleakError as e:
        print(f"Bluetooth scanning error: {e}")
        print("Please ensure Bluetooth is enabled and the script has the necessary permissions.")
        return

    meccanoid_device = None
    if MECCANOID_MAC_ADDRESS:
        for device in devices:
            if device.address.upper() == MECCANOID_MAC_ADDRESS.upper():
                meccanoid_device = device
                print(f"Found Meccanoid by MAC address: {device.name} ({device.address})")
                break
    else:
        for device in devices:
            if device.name and device.name.startswith(MECCANOID_NAME_PREFIX):
                meccanoid_device = device
                print(f"Found Meccanoid by name: {device.name} ({device.address})")
                break

    if not meccanoid_device:
        print(f"Meccanoid device not found. Discovered devices:")
        for i, device in enumerate(devices):
            print(f"  {i+1}. Name: {device.name}, Address: {device.address}, RSSI: {device.rssi}")
        if not devices:
            print("  No Bluetooth LE devices found.")
        return

    print(f"\nAttempting to connect to {meccanoid_device.name} ({meccanoid_device.address})...")
    try:
        async with BleakClient(meccanoid_device.address, timeout=20.0) as client:
            if client.is_connected:
                print(f"Successfully connected to {meccanoid_device.name}!")

                print("\nServices and Characteristics:")
                for service in client.services:
                    print(f"  Service: {service.uuid} (Description: {service.description})")
                    for char in service.characteristics:
                        print(f"    Characteristic: {char.uuid} (Description: {char.description})")
                        print(f"      Properties: {', '.join(char.properties)}")
                        # You could try reading a characteristic if it's readable
                        # if "read" in char.properties:
                        #     try:
                        #         value = await client.read_gatt_char(char.uuid)
                        #         print(f"        Value: {value}")
                        #     except Exception as e:
                        #         print(f"        Error reading char {char.uuid}: {e}")
            else:
                print(f"Failed to connect to {meccanoid_device.name}.")

    except BleakError as e:
        print(f"Bluetooth connection error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    print("Meccanoid BLE Connection Script")
    print("-------------------------------")
    print("Ensure your Meccanoid robot is powered on and discoverable.")
    if MECCANOID_MAC_ADDRESS:
        print(f"Attempting to connect directly to MAC: {MECCANOID_MAC_ADDRESS}")
    else:
        print(f"Scanning for devices with name starting with: {MECCANOID_NAME_PREFIX}")
    print("Press Ctrl+C to stop scanning if it takes too long.\n")
    
    try:
        asyncio.run(scan_and_connect())
    except KeyboardInterrupt:
        print("\nScanning stopped by user.")
    finally:
        print("\nScript finished.")
