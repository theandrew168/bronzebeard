import ctypes
import struct
import sys
import time

import libusb


def dfu_get_status(device):
    USB_ENDPOINT_OUT = 0b00000000
    USB_ENDPOINT_IN = 0b10000000
    USB_REQUEST_TYPE_CLASS = 0b00100000
    USB_RECIPIENT_INTERFACE = 0b00000001

    REQUEST_DFU_GETSTATUS = 3

    cls = USB_ENDPOINT_IN | USB_REQUEST_TYPE_CLASS | USB_RECIPIENT_INTERFACE
    req = REQUEST_DFU_GETSTATUS
    data_type = ctypes.c_uint8 * 6
    data = data_type()
    rc = libusb.control_transfer(device, cls, req, 0, 0, data, 6, 5000)
    assert rc == 6

    status, pt0, pt1, pt2, state, desc = struct.unpack('<BBBBBB', data)
    poll_timeout = pt2 << 16 | pt1 << 8 | pt0
    poll_timeout = poll_timeout / 1000
    time.sleep(poll_timeout)

    return status, state


def main():
    # ensure correct args
    if len(sys.argv) != 2:
        usage = '{} <vendor:product>'.format(sys.argv[0])
        raise RuntimeError(usage)

    # parse args
    device_id = sys.argv[1]
    vendor, product = device_id.split(':')
    vendor, product = int(vendor, base=16), int(product, base=16)

    # init libusb
    rc = libusb.init(None)
    assert rc == 0

    # locate device by vendor / product
    dev = libusb.open_device_with_vid_pid(None, vendor, product)
    assert dev != 0

    # get DFU status
    status, state = dfu_get_status(dev)
    print(status)
    print(state)


if __name__ == '__main__':
    main()
