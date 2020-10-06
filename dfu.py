import struct
import time

# pip install pyusb
import usb.core
import usb.util

VENDOR_GIGADEVICE = 0x28e9
PRODUCT_GD32 = 0x0189

GD32VF103_FLASH_BASE = 0x08000000
GD32VF103_FLASH_PAGE_SIZE = 1024
GD32VF103_FLASH_PAGE_COUNT = 128

# USB commands
USB_CLASS_OUT_REQUEST_TO_INTERFACE = 0b00100001
USB_CLASS_IN_REQUEST_TO_INTERFACE = 0b10100001

# DFU USB device identifiers
DFU_DEVICE_CLASS = 0xfe
DFU_DEVICE_SUBCLASS = 0x01

# DFU commands
DFU_DETACH = 0
DFU_DOWNLOAD = 1
DFU_UPLOAD = 2
DFU_GET_STATUS = 3
DFU_CLEAR_STATUS = 4
DFU_GET_STATE = 5
DFU_ABORT = 6

# DFU states.
DFU_STATE_APP_IDLE = 0x00
DFU_STATE_APP_DETACH = 0x01
DFU_STATE_DFU_IDLE = 0x02
DFU_STATE_DFU_DOWNLOAD_SYNC = 0x03
DFU_STATE_DFU_DOWNLOAD_BUSY = 0x04
DFU_STATE_DFU_DOWNLOAD_IDLE = 0x05
DFU_STATE_DFU_MANIFEST_SYNC = 0x06
DFU_STATE_DFU_MANIFEST = 0x07
DFU_STATE_DFU_MANIFEST_WAIT_RESET = 0x08
DFU_STATE_DFU_UPLOAD_IDLE = 0x09
DFU_STATE_DFU_ERROR = 0x0a

# Misc constants.
DFU_STATUS_LENGTH = 6

# USB standard constants.
DFU_DEVICE_CLASS = 0xfe
DFU_DEVICE_SUBCLASS = 0x01
DFU_DESCRIPTOR_TYPE = 0x21


def is_dfu_device(device):
    for config in device:
        interface = usb.util.find_descriptor(
            config,
            bInterfaceClass=DFU_DEVICE_CLASS,
            bInterfaceSubClass=DFU_DEVICE_SUBCLASS)

        return interface is not None


# might be useful for non 128 page count GD32 devices
def dfu_get_GD32VF103_page_count(device):
    serial = device.serial_number.encode('utf-16-le')
    if serial[2] == ord('B'):
        return 128
    elif serial[2] == ord('8'):
        return 64
    elif serial[2] == ord('6'):
        return 32
    elif serial[2] == ord('4'):
        return 16
    else:
        raise RuntimeError('Unknown GD32VF103 page count')


def dfu_get_status(device):
    config = list(device)[0]
    interface = list(config)[0]

    resp = device.ctrl_transfer(
        USB_CLASS_IN_REQUEST_TO_INTERFACE,
        DFU_GET_STATUS,
        0,
        interface.bInterfaceNumber,
        DFU_STATUS_LENGTH,
        5000)
    status, poll1, poll2, poll3, state = struct.unpack('<BBBBBx', resp)
    poll_timeout = (poll3 << 16) | (poll2 << 8) | poll1

    return status, poll_timeout, state


def dfu_wait_command(device):
    while True:
        status, poll_timeout, state = dfu_get_status(device)
        if state in [DFU_STATE_DFU_ERROR, DFU_STATE_DFU_DOWNLOAD_IDLE]:
            break
        if poll_timeout > 0:
            time.sleep(poll_timeout / 1000)

    if status != 0:
        raise RuntimeError('DFU error: {}'.format(status))


def dfu_write_page(device, page, data):
    config = list(device)[0]
    interface = list(config)[0]

    device.ctrl_transfer(
        USB_CLASS_OUT_REQUEST_TO_INTERFACE,
        DFU_DOWNLOAD,
        page,
        interface.bInterfaceNumber,
        data,
        5000)
    dfu_wait_command(device)


def dfu_write_program(device, program):
    pages = len(program) // GD32VF103_FLASH_PAGE_SIZE + 1
    if pages > GD32VF103_FLASH_PAGE_COUNT:
        raise RuntimeError('Program is too large!')

    for page in range(pages):
        print('Writing page: {}'.format(page))
        address_start = page * GD32VF103_FLASH_PAGE_SIZE
        address_end = address_start + GD32VF103_FLASH_PAGE_SIZE

        data = program[address_start:address_end]
        dfu_write_page(device, page, data)

    # send empty page to signal end of write
    dfu_write_page(pages, b'')
    print('Write complete!')


for device in usb.core.find(find_all=True, custom_match=is_dfu_device):
    print(device)
    if device.idVendor == VENDOR_GIGADEVICE and device.idProduct == PRODUCT_GD32:
        print('Found GD32VF103 device (needs hacks for page size and page count)')

    config = list(device)[0]
    interface = list(config)[0]
    device.set_configuration(config.bConfigurationValue)
#    device.detach_kernel_driver(interface.bInterfaceNumber)

    status, poll_timeout, state = dfu_get_status(device)
    print(status, poll_timeout, state)

    with open('longan_nano_led_on.bin', 'rb') as f:
        program = f.read()

#    dfu_write_program(device, program)
