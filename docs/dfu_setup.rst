DFU Setup
=========
Device Firmware Upgrade is a USB-based protocol for updating the firmware on certain embedded devices.
At the moment, the DFU implemention included with Bronzebeard only supports the `Longan Nano <https://www.seeedstudio.com/Sipeed-Longan-Nano-RISC-V-GD32VF103CBT6-DEV-Board-p-4725.html>`_ and `Wio Lite <https://www.seeedstudio.com/Wio-Lite-RISC-V-GD32VF103-p-4293.html>`_.

Windows
-------
The USB-based devices that Bronzebeard targets don't work well with Windows by default.
They each need to be associated with the generic `WinUSB <https://docs.microsoft.com/en-us/windows-hardware/drivers/usbcon/winusb>`_ driver in order to be identified and programmed.
The easiest way to accomplish this is with a tool called `Zadig <https://zadig.akeo.ie/>`_.
With the device attached to your computer (and in DFU mode, if applicable), use Zadig to assign the WinUSB driver to the device.
Note that you will have to apply this driver assignment to each physical USB port that you want to use for programming the device.

macOS
-----
The only extra requirement on macOS is `libusb <https://libusb.info>`_.
It can be easily installed via `homebrew <https://brew.sh/>`_::

  brew install libusb

Linux
-----
Programming devices over DFU requires `libusb <https://libusb.info>`_ version 1.0 or greater.
The following command will install the library on Debian-based Linux systems such as Debian, Ubuntu, Linux Mint, and Pop!_OS::

  sudo apt install libusb-1.0-0-dev

For other Linux ecosystems, consult their respective package repositories.

If you'd like to program and interact with the device as a normal, non-root user, create the following `udev <https://en.wikipedia.org/wiki/Udev>`_ rules file::

  # /etc/udev/rules.d/99-bronzebeard.rules

  # Longan Nano / Wio Lite
  ATTRS{idVendor}=="28e9", ATTRS{idProduct}=="0189", MODE="0666"
  # Silicon Labs CP2102 USB to UART Bridge
  ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", MODE="0666"

After the rules file is setup, reload udev via :code:`sudo udevadm control --reload`.

Basic Usage
-----------
With the target device in DFU mode::

  python3 -m bronzebeard.dfu 28e9:0189 bb.out
