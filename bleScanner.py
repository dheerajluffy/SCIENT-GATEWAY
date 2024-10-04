from bluepy.btle import Scanner, DefaultDelegate, Peripheral, BTLEException

target_name = "Scient BLE Node"

class ScanDelegate(DefaultDelegate):
    """
    Delegate class required for BLE scanning operations.
    It inherits from DefaultDelegate, allowing for BLE-specific callback handling.
    """
    def __init__(self):
        DefaultDelegate.__init__(self)

def scan_for_device(target_name):
    """
    Scans for a BLE device with a specific target name.

    Parameters:
    target_name (str): The name of the BLE device to scan for.

    Returns:
    tuple: A tuple containing the address and address type of the found BLE device. 
           If no device is found, returns (None, None).
    """
    scanner = Scanner().withDelegate(ScanDelegate())
    devices = scanner.scan(10.0)  # Scan for 10 seconds

    for dev in devices:
        for (adtype, desc, value) in dev.getScanData():
            if desc == 'Complete Local Name' and value == target_name:
                print(f"Found device '{target_name}' with address {dev.addr} and address type {dev.addrType}")
                return dev.addr, dev.addrType
    print(f"Device '{target_name}' not found")
    return None, None

def read_characteristics(target_address, address_type):
    """
    Connects to the BLE device using the given address and reads the characteristics.
    Displays the data received from readable characteristics.

    Parameters:
    target_address (str): The BLE device address.
    address_type (str): The BLE device address type.

    Returns:
    None
    """
    try:
        # Establish a connection to the BLE device
        device = Peripheral(target_address, address_type)
        print(f"Connected to {target_address}")

        try:
            # Retrieve characteristics from the BLE device
            characteristics = device.getCharacteristics()
            if not characteristics:
                print("No characteristics found")
                return
            
            print("Reading data from characteristics:")
            while True:
                for char in characteristics:
                    if char.supportsRead():
                        # Read and display data from each readable characteristic
                        data = char.read()
                        print(f"Data from characteristic {char.uuid}: {data}")
                    else:
                        print(f"Characteristic {char.uuid} does not support reading")
        except BTLEException as e:
            print(f"Error while reading characteristics: {e}")
    except BTLEException as e:
        print(f"Failed to connect to the device: {e}")

if __name__ == "__main__":
    """
    Main script execution. Scans for the target BLE device and reads characteristics if found.
    """
    target_address, address_type = scan_for_device(target_name)
    if target_address:
        read_characteristics(target_address, address_type)
