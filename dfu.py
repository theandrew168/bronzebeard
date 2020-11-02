import sys

import usb.core
import usb.util

# Example:
# python dfu.py 28e9:0189

# Longan Nano / Wio Lite
GD32_VENDOR = 0x28e9
GD32_PRODUCT = 0x0189

DFU_DEVICE_CLASS = 0xfe
DFU_DEVICE_SUBCLASS = 0x01

def dev_is_gd32(dev):
    return dev.idVendor == GD32_VENDOR and dev.idProduct == GD32_PRODUCT

def find_dfu_conf_iface(dev):
    for conf in dev:
        for iface in conf:
            if iface.bInterfaceClass != DFU_DEVICE_CLASS:
                continue
            if iface.bInterfaceSubClass != DFU_DEVICE_SUBCLASS:
                continue
            return conf.bConfigurationValue, iface.bInterfaceNumber

    raise RuntimeError('device lacks a DFU interface')

if len(sys.argv) != 2:
    usage = '{} <vendor:product>'.format(sys.argv[0])
    raise RuntimeError(usage)

vendor, product = sys.argv[1].split(':')
vendor, product = int(vendor, 16), int(product, 16)
dev = usb.core.find(idVendor=vendor, idProduct=product)
if dev is None:
    raise RuntimeError('device not found')

sn = dev.serial_number

# Fix mangled serial number on GD32 devices
if dev_is_gd32(dev):
    sn = sn.encode('utf-16-le').decode('utf-8')

print(sn)
