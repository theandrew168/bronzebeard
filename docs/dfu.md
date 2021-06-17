# DFU Setup
[DFU (Device Firmware Upgrade)](https://en.wikipedia.org/wiki/USB#Device_Firmware_Upgrade_mechanism) is a USB-based protocol for updating the firmware on certain embedded devices.
At the moment, the DFU implemention included with Bronzebeard only supports the [Longan Nano](https://www.seeedstudio.com/Sipeed-Longan-Nano-RISC-V-GD32VF103CBT6-Development-Board-p-4205.html) and [Wio Lite](https://www.seeedstudio.com/Wio-Lite-RISC-V-GD32VF103-p-4293.html).

### Windows
The USB-based devices that Bronzebeard targets don't work well with Windows by default.
They each need to be associated with the generic [WinUSB](https://docs.microsoft.com/en-us/windows-hardware/drivers/usbcon/winusb) driver in order to be identified and programmed.
The easiest way to accomplish this is with a tool called [Zadig](https://zadig.akeo.ie/).
With the device attached to your computer (and in DFU mode, if applicable), use Zadig to assign the WinUSB driver to the device.
Note that you will have to apply this driver assignment to each physical USB port that you want to use for programming the device.

### macOS
The only extra requirement on macOS is [libusb](https://libusb.info).
It can be easily installed via [homebrew](https://brew.sh/).
```
brew install libusb
```

### Linux
Programming devices over DFU requires [libusb](https://libusb.info) version 1.0 or greater.
The following command will install the library on Debian-based Linux systems such as Debian, Ubuntu, Linux Mint, and Pop!\_OS.
```
sudo apt install libusb-1.0-0-dev
```

For other Linux ecosystems, consult their respective package repositories.

If you'd like to program and interact with the device as a normal, non-root user, create the following [udev](https://en.wikipedia.org/wiki/Udev) rules file:
```
# /etc/udev/rules.d/99-bronzebeard.rules

# Longan Nano / Wio Lite
ATTRS{idVendor}=="28e9", ATTRS{idProduct}=="0189", MODE="0666"
# Adafruit USB to TTL Serial Cable
ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", MODE="0666"
# SparkFun USB to TTL Serial Cable
ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", MODE="0666"
```

After the rules file is setup, reload udev via `sudo udevadm control --reload`.

## Flash the Program (via DFU)
With the target device in DFU mode:
```
python3 -m bronzebeard.dfu <device_id> example.bin
```
