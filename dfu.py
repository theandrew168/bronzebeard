# Dependencies:
# pip install pyusb

import usb.core

DFU_DEVICE_CLASS = 0xFE
DFU_DEVICE_SUBCLASS = 0x01

for dev in usb.core.find(find_all=True):
    print(dev)
    for config in dev:
        for interface in config:
            if interface.bInterfaceClass != DFU_DEVICE_CLASS:
                continue
            if interface.bInterfaceSubClass != DFU_DEVICE_SUBCLASS:
                continue

            print('Found a DFU interface!!!')
            print(interface)
