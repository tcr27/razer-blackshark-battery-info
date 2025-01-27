import usb.core
import usb.util
import time
import signal

# Device Information
DEVICE_VENDOR_ID = 0x1532
DEVICE_PRODUCT_ID = 0x0555
ENDPOINT_OUT = 0x02  # Interrupt OUT Endpoint
ENDPOINT_IN = 0x83  # Interrupt IN Endpoint
INTERFACE = 3  # Change value if Resource is busy

# Global flag for the loop
running = True
reattach = False

def signal_handler(sig, frame):
    """Handle Ctrl+C to exit gracefully."""
    global running
    print("\nCtrl+C detected. Exiting gracefully...")
    running = False

# Register the signal handler for Ctrl+C
signal.signal(signal.SIGINT, signal_handler)

def communicate_with_device():
    global running, reattach
    try:
        # Find the USB device
        device = usb.core.find(idVendor=DEVICE_VENDOR_ID, idProduct=DEVICE_PRODUCT_ID)
        if device is None:
            raise ValueError("Device not found")

        # Detach kernel driver if necessary
        if device.is_kernel_driver_active(INTERFACE):
            reattach = True
            device.detach_kernel_driver(INTERFACE)

        # Change to alternate Interface in order to retrieve battery information
        interface_response = device.ctrl_transfer(bmRequestType=0x01, bRequest=0x0B, wValue=1, wIndex=2, data_or_wLength=0)
        print(interface_response)

        # Prepare the Interrupt OUT payload
        battery_data_request = [
            0x2, 0x80, 0x8, 0x0, 0x0, 0x50, 0x41, 0x08, 0x0, 0x03, 0x21, 0x0, 0x0, 0x0, 0x0, 0x0,
            0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
            0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0,
            0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0
        ]

        while running:
            try:
                device.write(ENDPOINT_OUT, bytes(battery_data_request))
                time.sleep(0.1)

                # Read Interrupt IN transfer
                interrupt_in_response = device.read(ENDPOINT_IN, 128, timeout=1000)

                battery_position = 15
                if len(interrupt_in_response) > battery_position:
                    battery_status = interrupt_in_response[battery_position]
                    # First output is 0, but I don't know why
                    print(f"Battery Status: {battery_status}%")

                time.sleep(2)

            except usb.core.USBError as e:
                if e.errno == 110:
                    print("No data received within timeout period.")
                else:
                    print(f"USB Error: {e}")
                    break

    except usb.core.USBError as e:
        print(f"USB Error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Reattach the kernel driver if it was detached
        if reattach:
            try:
                device.attach_kernel_driver(INTERFACE)
                print("Kernel driver reattached successfully.")
            except usb.core.USBError as e:
                print(f"Failed to reattach kernel driver: {e}")
        print("Exiting program.")


if __name__ == "__main__":
    communicate_with_device()