import configparser
import asyncio
import platform
import subprocess
import ctypes
from bleak import BleakScanner

# --- Configuration ---
CONFIG_FILE = "config.ini"
DEVICE_ADDRESS = None  # To be replaced with the registered device's address
SCAN_INTERVAL = 5  # Seconds

# --- Platform-specific screen lock commands ---
LOCK_COMMANDS = {
    "Windows": "rundll32.exe user32.dll,LockWorkStation",
    "Darwin": "/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession -suspend",
    "Linux": "gnome-screensaver-command --lock"  # This may need to be adjusted for different desktop environments
}

def save_device_address(address):
    """Saves the device address to the config file."""
    config = configparser.ConfigParser()
    config["device"] = {"address": address}
    with open(CONFIG_FILE, "w") as f:
        config.write(f)
    print(f"Device address {address} saved.")

def load_device_address():
    """Loads the device address from the config file."""
    global DEVICE_ADDRESS
    config = configparser.ConfigParser()
    if config.read(CONFIG_FILE):
        DEVICE_ADDRESS = config.get("device", "address", fallback=None)
        if DEVICE_ADDRESS:
            print(f"Loaded device address: {DEVICE_ADDRESS}")
    return DEVICE_ADDRESS

async def register_device():
    """Scans for devices and prompts the user to select one to register."""
    print("Scanning for devices to register...")
    devices = await BleakScanner.discover()
    if not devices:
        print("No devices found. Please make sure your device is discoverable.")
        return

    print("Please select a device to register:")
    for i, device in enumerate(devices):
        print(f"  {i}: {device.address} - {device.name}")

    try:
        selection = int(input("Enter the number of the device: "))
        if 0 <= selection < len(devices):
            selected_device = devices[selection]
            save_device_address(selected_device.address)
            global DEVICE_ADDRESS
            DEVICE_ADDRESS = selected_device.address
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input.")

def lock_screen():
    """Locks the screen based on the operating system."""
    os_name = platform.system()
    command = LOCK_COMMANDS.get(os_name)

    if os_name == "Windows":
        try:
            ctypes.windll.user32.LockWorkStation()
            print("Screen locked on Windows.")
        except AttributeError:
            print("Failed to lock screen on Windows.")
    elif command:
        try:
            subprocess.run(command.split(), check=True)
            print(f"Screen locked on {os_name}.")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Failed to lock screen on {os_name}: {e}")
    else:
        print(f"Screen locking not supported on {os_name}.")

async def discover_devices():
    """Scans for nearby Bluetooth devices."""
    print("Scanning for devices...")
    devices = await BleakScanner.discover()
    if not devices:
        print("No devices found.")
    for device in devices:
        print(f"  - {device.address}: {device.name}")

async def check_device_presence():
    """Periodically checks for the presence of the registered device."""
    while True:
        print(f"Scanning for {DEVICE_ADDRESS}...")
        device = await BleakScanner.find_device_by_address(DEVICE_ADDRESS, timeout=SCAN_INTERVAL - 1)
        if device:
            print("Device is nearby.")
        else:
            print("Device not found. Locking screen.")
            lock_screen()
        await asyncio.sleep(SCAN_INTERVAL)

async def main():
    """Main application loop."""
    if not load_device_address():
        await register_device()

    if not DEVICE_ADDRESS:
        print("No device registered. Exiting.")
        return

    print(f"Monitoring device: {DEVICE_ADDRESS}")
    await check_device_presence()


if __name__ == "__main__":
    # On Windows, we need to use a specific event loop policy
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Application stopped.")
