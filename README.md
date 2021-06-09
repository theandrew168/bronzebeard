# bronzebeard
Minimal ecosystem for bare-metal RISC-V development

## What
Bronzebeard is first and foremost a [single-file](https://github.com/theandrew168/bronzebeard/blob/master/bronzebeard/asm.py) [nanopass](https://legacy.cs.indiana.edu/~dyb/pubs/nano-jfp.pdf) assembler for developing [bare metal](https://en.wikipedia.org/wiki/Bare_machine) [RISC-V](https://en.wikipedia.org/wiki/Riscv) programs.
It is designed for applications that stand on their own without relying on [operating systems](https://en.wikipedia.org/wiki/Operating_system), frameworks, SDKs, or pre-existing software of any kind.

## Why
Much of modern software has accrued vast amounts of bulk and complexity throughout the years.
Can useful software be developed without relying on any of it?
That's the question that this project seeks to answer.
I believe that the rise of RISC-V provides a great opportunity to explore different methods of program development.
Installing a full operating system doesn't have to be a prerequisite to building something useful.

Check out the [DerzForth](https://github.com/theandrew168/derzforth) project for further elaboration of this idea.

## How
Bronzebeard and its tools are implemented purely in Python.
It has been written in order to be free from large, complex toolchains.
This keeps the project portable, minimal, and easy to understand.

## Devices
The assembler itself supports the base 32-bit instruction set as well as the M, A, and C extensions (RV32IMAC).
At the moment, Bronzebeard has only been used to target the [Longan Nano](https://www.seeedstudio.com/Sipeed-Longan-Nano-RISC-V-GD32VF103CBT6-Development-Board-p-4205.html) and the [Wio Lite](https://www.seeedstudio.com/Wio-Lite-RISC-V-GD32VF103-p-4293.html).
There are plans to test on additional RISC-V boards such as the [HiFive1 Rev B](https://www.sifive.com/boards/hifive1-rev-b) in the future.

## Documentation
Most of the surface-level documentation for Bronzebeard lives right here in this README.
For more specific details regarding the usage and accepted syntax of the assembler, check out the [docs](https://github.com/theandrew168/bronzebeard/tree/master/docs) directory.
This is where the project's primary documentation will live until the time comes to setup something more official.

## Installation
If you are unfamiliar with [virtual environments](https://docs.python.org/3/library/venv.html), I suggest taking a brief moment to learn about them and set one up.
The Python docs provide a great [tutorial](https://docs.python.org/3/tutorial/venv.html) for getting started with virtual environments and packages.

Bronzebeard can be installed via pip:
```
pip install bronzebeard
```

## Setup
All major operating system platforms are supported: Windows, macOS, and Linux.
In order to utilize Bronzebeard, you need to download and install a recent version of [Python](https://www.python.org/downloads/).
For more info, [Real Python](https://realpython.com/) has a great [installation and setup guide](https://realpython.com/installing-python/) that I recommend following.

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

## Usage
```
usage: python -m bronzebeard.asm [-h] [--compress] [--verbose] [--version] input_asm output_bin

Assemble RISC-V source code

positional arguments:
  input_asm   input source file
  output_bin  output binary file

optional arguments:
  -h, --help  show this help message and exit
  --compress  identify and compress eligible instructions
  --verbose   verbose assembler output
  --version   print assembler version and exit
```

## Assemble
With Bronzebeard installed:
```
python3 -m bronzebeard.asm examples/example.asm example.bin
```

## Program (via DFU)
NOTE: The DFU implemention included with Bronzebeard only supports the Longan Nano and Wio Lite at this time.

With the target device in DFU mode:
```
python3 -m bronzebeard.dfu <device_id> example.bin
```
