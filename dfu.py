import struct
import sys
import time

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

# From dfu-util:
# main
# dfuse_do_dnload(iface, xfer_size, file, opts)
# dfuse_do_bin_dnload(iface, xfer_size, file, 0x0800_0000)
# dfuse_dnload_element(iface, 0x0800_0000, len(data), data, xfer_size)
# for each page:
#   dfuse_special_command(iface, addr, ERASE_PAGE)
# for each page:
#   dfuse_special_command(iface, addr, SET_ADDRESS)
#   dfuse_dnload_chunk(iface, data + offset, xfer_size, 2)  # trans = 2 for no addr offset?
#   dfuse_download(iface, size, data, 2)
#     ctrl_transfer(OUT, DFU_DNLOAD, 2, iface, data, len)
#   dfu_get_status
#   sleep(poll_timeout)
#   ensure STATUS_OK

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

# DfuSe-specific commands (sent in-band over DFU_UPLOAD / DFU_DNLOAD)
DFUSE_CMD_SET_ADDRESS = 0x21  # includes addr, len = 5
DFUSE_CMD_ERASE_PAGE = 0x41  # includes addr, len = 5
DFUSE_CMD_MASS_ERASE = 0x41  # len = 1
DFUSE_CMD_READ_UNPROTECT = 0x92  # len = 1

# DFU 1.1 Spec: Page 21
STATUS_OK = 0
STATUS_ERR_TARGET = 1
STATUS_ERR_FILE = 2
STATUS_ERR_WRITE = 3
STATUS_ERR_ERASE = 4
STATUS_ERR_CHECK_ERASED = 5
STATUS_ERR_PROG = 6
STATUS_ERR_VERIFY = 7
STATUS_ERR_ADDRESS = 8
STATUS_ERR_NOTDONE = 9
STATUS_ERR_FIRMWARE = 10
STATUS_ERR_VENDOR = 11
STATUS_ERR_USBR = 12
STATUS_ERR_POR = 13
STATUS_ERR_UNKNOWN = 14
STATUS_ERR_STALLEDPKT = 15

# DFU 1.1 Spec: Page 21
STATUS_DESCRIPTION = {
    STATUS_OK: 'No error condition is present.',
    STATUS_ERR_TARGET: 'File is not targeted for use by this device.',
    STATUS_ERR_FILE: 'File is for this device but fails some vendor-specific verification test.',
    STATUS_ERR_WRITE: 'Device is unable to write memory.',
    STATUS_ERR_ERASE: 'Memory erase function failed.',
    STATUS_ERR_CHECK_ERASED: 'Memory erase check failed.',
    STATUS_ERR_PROG: 'Program memory function failed.',
    STATUS_ERR_VERIFY: 'Programmed memory failed verification.',
    STATUS_ERR_ADDRESS: 'Cannot program memory due to received address that is out of range.',
    STATUS_ERR_NOTDONE: 'Received DFU_DNLOAD with wLength = 0, but device does not think it has all of the data yet.',
    STATUS_ERR_FIRMWARE: 'Device\'s firmware is corrupt. It cannot return to run-time (non-DFU) operations.',
    STATUS_ERR_VENDOR: 'iString indicates a vendor-specific error.',
    STATUS_ERR_USBR: 'Device detected unexpected USB reset signaling.',
    STATUS_ERR_POR: 'Device detected unexpected power on reset.',
    STATUS_ERR_UNKNOWN: 'Something went wrong, but the device does not know what it was.',
    STATUS_ERR_STALLEDPKT: 'Device stalled an unexpected request.',
}

# DFU 1.1 Spec: Page 22
STATE_APP_IDLE = 0
STATE_APP_DETACH = 1
STATE_DFU_IDLE = 2
STATE_DFU_DNLOAD_SYNC = 3
STATE_DFU_DNBUSY = 4
STATE_DFU_DNLOAD_IDLE = 5
STATE_DFU_MANIFEST_SYNC = 6
STATE_DFU_MANIFEST = 7
STATE_DFU_MANIFEST_WAIT_RESET = 8
STATE_DFU_UPLOAD_IDLE = 9
STATE_DFU_ERROR = 10

# DFU 1.1 Spec: Page 22
STATE_DESCRIPTION = {
    STATE_APP_IDLE: 'Device is running its normal application.',
    STATE_APP_DETACH: 'Device is running its normal application, has received the DFU_DETACH request, and is waiting for a USB reset.',
    STATE_DFU_IDLE: 'Device is operating in the DFU mode and is waiting for requests.',
    STATE_DFU_DNLOAD_SYNC: 'Device has received a block and is waiting for the host to solicit the status via DFU_GETSTATUS.',
    STATE_DFU_DNBUSY: 'Device is programming a control-write block into its nonvolatile memories.',
    STATE_DFU_DNLOAD_IDLE: 'Device is processing a download operation. Expecting DFU_DNLOAD requests.',
    STATE_DFU_MANIFEST_SYNC: 'Device has received the final block of firmware from the host and is w aiting for receipt of DFU_GETSTATUS to begin the Manifestation phase; or device has completed the Manifestation phase and is waiting for receipt of DFU_GETSTATUS.',
    STATE_DFU_MANIFEST: 'Device is in the Manifestation phase.',
    STATE_DFU_MANIFEST_WAIT_RESET: 'Device has programmed its memories and is waiting for a USB reset or a power on reset.',
    STATE_DFU_UPLOAD_IDLE: 'The device is processing an upload operation. Expecting DFU_UPLOAD requests.',
    STATE_DFU_ERROR: 'An error has occurred. Awaiting the DFU_CLRSTATUS request.',
}

DFU_STATUS_LENGTH = 6

USB_ENDPOINT_OUT = 0b00000000
USB_ENDPOINT_IN = 0b10000000
USB_REQUEST_TYPE_CLASS = 0b00100000
USB_RECIPIENT_INTERFACE = 0b00000001


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

# use the DFU configuration and interface
dev.set_configuration(conf)
dev.set_interface_altsetting(iface)

# get DFU status
response = dev.ctrl_transfer(
    USB_ENDPOINT_IN | USB_REQUEST_TYPE_CLASS | USB_RECIPIENT_INTERFACE,
    REQUEST_DFU_GETSTATUS, 0, iface, 6, 5000)
status, pt0, pt1, pt2, state, desc = struct.unpack('<BBBBBB', response)
poll_timeout = pt2 << 16 | pt1 << 8 | pt0  # rebuild timeout from 3 bytes (little-endian)
poll_timeout = poll_timeout / 1000  # convert timeout to seconds
print('status:', status)
print('timeout:', poll_timeout)
print('state:', state)
print('state_desc:', STATE_DESCRIPTION[state])
time.sleep(poll_timeout)

# clear DFU error if present
if state == STATE_DFU_ERROR:
    print('Device is in error, sending DFU_CLRSTATUS')
    dev.ctrl_transfer(
        USB_ENDPOINT_OUT | USB_REQUEST_TYPE_CLASS | USB_RECIPIENT_INTERFACE,
        REQUEST_DFU_CLRSTATUS, 0, iface, 0, 5000)

    # get DFU status again
    response = dev.ctrl_transfer(
        USB_ENDPOINT_IN | USB_REQUEST_TYPE_CLASS | USB_RECIPIENT_INTERFACE,
        REQUEST_DFU_GETSTATUS, 0, iface, 6, 5000)
    status, pt0, pt1, pt2, state, desc = struct.unpack('<BBBBBB', response)
    poll_timeout = pt2 << 16 | pt1 << 8 | pt0  # rebuild timeout from 3 bytes (little-endian)
    poll_timeout = poll_timeout / 1000  # convert timeout to seconds
    print('status:', status)
    print('timeout:', poll_timeout)
    print('state:', state)
    print('state_desc:', STATE_DESCRIPTION[state])
    time.sleep(poll_timeout)
