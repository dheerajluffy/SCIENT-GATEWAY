#!usr/bin/python3
import time
import requests
from gpiozero import CPUTemperature, PingServer, DiskUsage
import psutil
import os
import serial
import re
import datetime
from geopy.geocoders import Nominatim
from bluepy.btle import Scanner, DefaultDelegate, Peripheral, BTLEException, BTLEDisconnectError

# The above are all the import statements of the code. Ensure all of the modules are installed, 
# if not, install them using pip.

address = "Hyderabad India" 

"""
The 'address' variable should be in the format of "province country"  
Example: "Newyork USA"
"""

env_api_url = "https://portal.scient-labs.com:8445/insertEnvMetrics"
dev_api_url = "https://portal.scient-labs.com:8445/insertDeviceMetrics"


class ScanDelegate(DefaultDelegate):
    """
    This class defines a delegate for BLE scanning operations. 
    It inherits from DefaultDelegate and is required for BLE scanning callbacks.
    """
    def __init__(self):
        DefaultDelegate.__init__(self)


class TachyonBleDriver():
    """
    This class defines the driver for BLE (Bluetooth Low Energy) operations. 
    It provides methods to scan for BLE devices and read characteristics from the devices.
    """
    
    def scan_for_devices(self, target_name):
        """
        Scans for BLE devices with a specific target name.
        Returns a list of found devices that match the target name.
        
        Parameters:
        target_name (str): The name of the BLE device to scan for.

        Returns:
        list: A list of found devices with their addresses and address types.
        """
        scanner = Scanner().withDelegate(ScanDelegate())
        try:
            devices = scanner.scan(10.0)  # Scan for 10 seconds 
        except BTLEDisconnectError:
            print(f"E 1 | previous connection was force stopped. Please re-run and try again")
            return []
        found_devices = []
        for dev in devices:
            for (adtype, desc, value) in dev.getScanData():
                if desc == 'Complete Local Name' and value == target_name:
                    print(f"Found device '{target_name}' with address {dev.addr} and address type {dev.addrType}")
                    found_devices.append((dev.addr, dev.addrType))
        if not found_devices:
            print(f"No devices found with the name '{target_name}'")
        return found_devices

    def read_characteristics(self, target_address, address_type):
        """
        Connects to a BLE device and reads its characteristics.
        Extracts sensor data from the characteristics.

        Parameters:
        target_address (str): The BLE device address.
        address_type (str): The BLE device address type.

        Returns:
        list: Extracted sensor data in the form [device address, temperature, pressure, humidity, gas].
        """
        try:
            device = Peripheral(target_address, address_type)
            print(f"Connected to {target_address}")

            try:
                characteristics = device.getCharacteristics()
                if not characteristics:
                    print("No characteristics found")
                    return
                if characteristics[6].supportsRead():
                    received_data = characteristics[6].read()
                    if received_data[0] != 0:
                        str_data = f"{characteristics[6].read()}"

                        new_line_index = str_data.find("n")
                        str_data = str_data[2:new_line_index-1]

                        ext_list = extract_values(str_data)

                        ret_data = [target_address, ext_list[0], ext_list[1], ext_list[2], ext_list[3]]
                        return ret_data
                    else:
                        print("E2 | got NULL data")
                device.disconnect()
            except BTLEException as e:
                print(f"Error while reading characteristics: {e}")
            finally:
                device.disconnect()
                print(f"Disconnected from {target_address}")
        except BTLEException as e:
            print(f"Failed to connect to the device: {e}")
        
    def get_data_from_devices(self, found_devices):
        """
        Iterates over a list of BLE devices and reads data from each device.

        Parameters:
        found_devices (list): List of devices with their addresses and address types.

        Returns:
        list: A list of sensor data from each device.
        """
        ret_list = []
        for address, address_type in found_devices:
            ret_list.append(self.read_characteristics(address, address_type))
        return ret_list


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~END OF BLE-DRIVER CLASS~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


def extract_values(data_str):
    """
    Extracts sensor values from the BLE device data string.
    Splits the string by semicolon and space to isolate temperature, pressure, humidity, and gas values.

    Parameters:
    data_str (str): The data string received from the BLE device.

    Returns:
    list: A list of extracted values.
    """
    parts = data_str.replace("T:", "").replace("P:", "").replace("H:", "").replace("G:", "").split(';')
    values = [part.strip() for part in parts if part.strip()]
    return values

def make_post_api_call(api_url, payload, headers=None):
    """
    Sends an HTTP POST request to the specified API endpoint with the provided payload.

    Parameters:
    api_url (str): The URL of the API endpoint.
    payload (dict): The data to send in the request body.
    headers (dict, optional): Additional headers for the request.

    Returns:
    None
    """
    try:
        response = requests.post(api_url, json=payload, headers=headers)

        if response.status_code == 200:
            print("API Response:")
            print(response)
        else:
            print(f"E: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"An error occurred: {e}")

def run():
    """
    Main function to run the BLE scanner and collect data from found devices.
    It also collects CPU, disk, and memory metrics from the system and sends them to APIs.
    """
    print("~~~~~~~~~SCIENT-GATEWAY-V3~~~~~~~~~")
    cpu = CPUTemperature(min_temp=50, max_temp=90)
    disk = DiskUsage()
    print('Current disk usage: {}%'.format(disk.usage))

    # Calling psutil.cpu_precent() for 4 seconds
    print('The CPU usage is: ', psutil.cpu_percent(4))

    # Getting % usage of virtual_memory (3rd field)
    print('RAM memory % used:', psutil.virtual_memory()[2])

    # Geolocation using the address variable
    loc = Nominatim(user_agent="GetLoc")
    getLoc = loc.geocode(address)
    print(getLoc.address)
    print("Latitude = ", getLoc.latitude, "\n")
    print("Longitude = ", getLoc.longitude)

    print("|~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~|")
    print("|Info: make sure the ble server node is powered on and advertising             |")
    print("|Info: make sure ble client node is powered on                                 |")
    print("|Info : if stuck, ensure the above points and rerun this script                |")
    print("|~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~|")

    # BLE scanning and data collection
    target_name = "Scient BLE Node"
    print(f"Scanning for devices with name '{target_name}'...")
    myble = TachyonBleDriver()
    found_devices = myble.scan_for_devices(target_name)
    pkt_cnt = 0
    while found_devices != []:
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        devices_len = len(found_devices)
        print(f"Found devices: {devices_len}")
        got_data = myble.get_data_from_devices(found_devices)

        for n in range(devices_len):
            print(f"pkt : {pkt_cnt} | {got_data[n]}")

            if (type(got_data[n]) != type(None)):
                pkt_cnt += 1
                env_api_payload = {
                    "deviceId": "1", 
                    "humidity": str(got_data[n][3]), 
                    "temperature": str(got_data[n][1]), 
                    "pressure": str(got_data[n][2]), 
                    "gas": str(got_data[n][4]), 
                    "location": "", 
                    "region": "" 
                }

                dev_api_payload = {
                    "deviceId": "1", 
                    "cpuUsage": str(psutil.cpu_percent(4)), 
                    "memoryUsage": str(psutil.virtual_memory()[2]), 
                    "latitude": str(getLoc.latitude), 
                    "longitude": str(getLoc.longitude), 
                    "temperatureC": str(cpu.temperature)
                }
                
                print(f"apiPayload : {env_api_payload}")

                make_post_api_call(env_api_url, payload=env_api_payload)
                make_post_api_call(dev_api_url, payload=dev_api_payload)

                print(f"node {n} | {got_data[n][0]} updated at : {datetime.datetime.now()}")
            else:
                print("##E GOT NONE VALUE##")
        time.sleep(90)

if __name__ == "__main__":
    run()
