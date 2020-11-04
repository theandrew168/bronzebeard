import sys

import usb.core
import usb.util

# Example:
# python dfu.py 28e9:0189

# Program Flow:
# 1. Connect
# 2. Check for error
# 3. Clear error if present
# 4. Erase flash
# 5. Upload new program
# 6. Disconnect

# References:
# https://usb.org/sites/default/files/DFU_1.1.pdf
# https://github.com/usb-tools/pyfwup/blob/master/fwup/dfu.py

DFU_DEVICE_CLASS = 0xfe
DFU_DEVICE_SUBCLASS = 0x01
DFU_DESCRIPTOR_TYPE = 0x21

# DFU 1.1 Spec: Table 3.2
REQUEST_DFU_DETACH = 0
REQUEST_DFU_DNLOAD = 1
REQUEST_DFU_UPLOAD = 2
REQUEST_DFU_GETSTATUS = 3
REQUEST_DFU_CLRSTATUS = 4
REQUEST_DFU_GETSTATE = 5
REQUEST_DFU_ABORT = 6

# DFU 1.1 Spec: Page 21
STATUS_OK = 0x00
STATUS_ERR_TARGET = 0x01
STATUS_ERR_FILE = 0x02
STATUS_ERR_WRITE = 0x03
STATUS_ERR_ERASE = 0x04
STATUS_ERR_CHECK_ERASED = 0x05
STATUS_ERR_PROG = 0x06
STATUS_ERR_VERIFY = 0x07
STATUS_ERR_ADDRESS = 0x08
STATUS_ERR_NOTDONE = 0x09
STATUS_ERR_FIRMWARE = 0x0a
STATUS_ERR_VENDOR = 0x0b
STATUS_ERR_USBR = 0x0c
STATUS_ERR_POR = 0x0d
STATUS_ERR_UNKNOWN = 0x0e
STATUS_ERR_STALLEDPKT = 0x0f

# DFU 1.1 Spec: Page 22
STATE_APP_IDLE = 0x00
STATE_APP_DETACH = 0x01
STATE_DFU_IDLE = 0x02
STATE_DFU_DOWNLOAD_SYNC = 0x03
STATE_DFU_DOWNLOAD_BUSY = 0x04
STATE_DFU_DOWNLOAD_IDLE = 0x05
STATE_DFU_MANIFEST_SYNC = 0x06
STATE_DFU_MANIFEST = 0x07
STATE_DFU_MANIFEST_WAIT_RESET = 0x08
STATE_DFU_UPLOAD_IDLE = 0x09
STATE_DFU_ERROR = 0x0a

DFU_STATUS_LENGTH = 6

# 0 01 00001
# ^           out
#   ^^        class request
#      ^^^^^  to interface
USB_CLASS_OUT_REQUEST_TO_INTERFACE = 0b00100001

# 1 01 00001
# ^           in
#   ^^        class request
#      ^^^^^  to interface
USB_CLASS_IN_REQUEST_TO_INTERFACE = 0b10100001


def find_dfu_conf_and_iface(dev):
    for conf in dev:
        for iface in conf:
            if iface.bInterfaceClass != DFU_DEVICE_CLASS:
                continue
            if iface.bInterfaceSubClass != DFU_DEVICE_SUBCLASS:
                continue
            return conf.bConfigurationValue, iface.bInterfaceNumber

    raise RuntimeError('device lacks a DFU interface')


# ensure correct args
if len(sys.argv) != 2:
    usage = '{} <vendor:product>'.format(sys.argv[0])
    raise RuntimeError(usage)

# parse args and find device
device_id = sys.argv[1]
vendor, product = device_id.split(':')
vendor, product = int(vendor, 16), int(product, 16)
dev = usb.core.find(idVendor=vendor, idProduct=product)
if dev is None:
    raise RuntimeError('device not found')

# TODO: get page_size and page_count via the protocol

# quirks for GD32 devices (Longan Nano, Wio Lite)
if vendor == 0x28e9 and product == 0x0189:
    print('Found GD32 device, overriding page size and count')
    # fix mis-encoded serial number
    sn = dev.serial_number.encode('utf-16-le').decode('utf-8')
    # page size is always 1024
    page_size = 1024
    # page count can be determined based on the serial number
    if sn[2] == 'B':
        page_count = 128
    elif sn[2] == '8':
        page_count = 64
    elif sn[2] == '6':
        page_count = 32
    elif sn[2] == '4':
        page_count = 16
    else:
        raise RuntimeError('invalid serial number for a GD32 device')

conf, iface = find_dfu_conf_and_iface(dev)

# set the correct configuration
dev.set_configuration(conf)

status = dev.ctrl_transfer(USB_CLASS_IN_REQUEST_TO_INTERFACE, DFU_GET_STATUS, 0, iface, 6, 5000)
