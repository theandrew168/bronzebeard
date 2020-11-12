# bronzebeard
Minimal ecosystem for bare-metal RISC-V development

## What
TODO update this  
Bronzebeard is an implementation of the [Forth programming language](https://en.wikipedia.org/wiki/Forth_(programming_language)) for the [RISC-V ISA](https://en.wikipedia.org/wiki/RISC-V).
It is designed to run on [bare metal](https://en.wikipedia.org/wiki/Bare_machine) with no reliance on an [operating system](https://en.wikipedia.org/wiki/Operating_system) or existing software of any kind.

## Why
Much of modern software has accrued vast amounts of bulk and complexity throughout the years.
Can useful software be developed without relying on any of it?
That's the question that this project seeks to answer.
I believe that the rise of RISC-V provides a great opportunity to explore different methods of program development.
Installing a full operating system isn't always a prerequisite to building something valuable.

## How
TODO update this  
Bronzebeard is written directly in RISC-V assembly.
A simple, standalone [assembler](https://github.com/theandrew168/bronzebeard/blob/master/asm.py) has been written in order to be free from large, complex toolchains.
This keeps the project portable, minimal, and easy to understand.

## Prior Art
Forth was initially designed and created by [Charles Moore](https://en.wikipedia.org/wiki/Charles_H._Moore).
Many folks have adapted its ideas and principles to solve their own problems.
[Moving Forth](http://www.bradrodriguez.com/papers/moving1.htm) by Brad Rodriguez is an amazing source of Forth implementation details and tradeoffs.
If you are looking for some introductory content surrounding the Forth language in general, I recommend the book [Starting Forth](https://www.forth.com/starting-forth/) by Leo Brodie.

[Sectorforth](https://github.com/cesarblum/sectorforth) by Cesar Blum is the source of Bronzebeard's general structure.
He took inspiration from a [1996 Usenet thread](https://groups.google.com/g/comp.lang.forth/c/NS2icrCj1jQ/m/ohh9v4KphygJ) wherein folks discussed requirements for a minimal yet fully functional Forth implementation.

## Primitive Words
This minimal selection of primitive words comes from Sectorforth and the Usenet thread it references.

| Word   | Stack Effects | Description                                   |
| ------ | ------------- | --------------------------------------------- |
| `:`    | ( -- )        | Start the definition of a new secondary word  |
| `;`    | ( -- )        | Finish the definition of a new secondary word |
| `@`    | ( addr -- x ) | Fetch memory contents at addr                 |
| `!`    | ( x addr -- ) | Store x at addr                               |
| `sp@`  | ( -- sp )     | Get pointer to top of data stack              |
| `rp@`  | ( -- rp )     | Get pointer to top of return stack            |
| `0=`   | ( x -- flag ) | -1 if top of stack is 0, 0 otherwise          |
| `+`    | ( x y -- z )  | Sum the two numbers at the top of the stack   |
| `nand` | ( x y -- z )  | NAND the two numbers at the top of the stack  |
| `key`  | ( -- x )      | Read ASCII character from serial input        |
| `emit` | ( x -- )      | Write ASCII character to serial output        |

## Portability
At the moment, Bronzebeard only targets the [Longan Nano](https://www.seeedstudio.com/Sipeed-Longan-Nano-RISC-V-GD32VF103CBT6-Development-Board-p-4205.html).
However, there are plans in the near future to broaden support to also include the [Wio Lite](https://www.seeedstudio.com/Wio-Lite-RISC-V-GD32VF103-p-4293.html) and [HiFive1 Rev B](https://www.sifive.com/boards/hifive1-rev-b).
As far as portability goes, Bronzebeard only requires a few pieces of information and functionality.

1. ROM base address and size
2. RAM base address and size
3. Ability to read and write characters over serial UART

All three of the aforementioned devices are capable of running Bronzebeard: it is just a matter of collecting the memory info, implementing basic UART interaction, and then flashing the ROM.

## Setup
All major operating system platforms are supported: Windows, macOS, and Linux.
In order to utilize Bronzebeard, you need to download and install a recent version of [Python](https://www.python.org/downloads/).
For more info, [Real Python](https://realpython.com/) has a great [installation and setup guide](https://realpython.com/installing-python/) that I recommend following.

Additionally, you will need to install [git](https://git-scm.com/downloads) in order to clone this project's source code.
To obtain the code, execute the following command:
```
git clone https://github.com/theandrew168/bronzebeard.git
```

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

## Dependencies
Firstly, create a [virtual environment](https://docs.python.org/3/library/venv.html) to hold Bronzebeard's dependencies.
If you are unfamiliar with this process, the Python docs provide a great [tutorial](https://docs.python.org/3/tutorial/venv.html) for getting started with virtual environments and packages.

With the virtual environment setup and activated, we can install Bronzebeard's dependencies.
```
pip install wheel
pip install -r requirements.txt
```

## Longan Nano
This section details how to run Bronzebeard on the [Longan Nano](https://www.seeedstudio.com/Sipeed-Longan-Nano-RISC-V-GD32VF103CBT6-Development-Board-p-4205.html).

### Cables
1. Attach the USB to USB-C cable for programming via DFU
2. Attach the USB to TTL Serial cable ([adafruit](https://www.adafruit.com/product/954), [sparkfun](https://www.sparkfun.com/products/12977)) for interacting over serial
    * Attach GND to GND
    * Attach TX to RX
    * Attach RX to TX
    * Don't attach VCC (or jump to the 5V input if you want power via this cable)

### Build
With the virtual environment activated and dependencies installed:
```
python forth.py
```

### Program
Enable DFU mode on the Longan Nano: press BOOT, press RESET, release RESET, release BOOT.
```
python -m bronzebeard.dfu 28e9:0189 forth.bin
```

After programming, press and release RESET in order to put the device back into normal mode.

### Interact
We can use [pySerial's](https://pyserial.readthedocs.io/en/latest/index.html) built-in terminal to communiate with the device.

To get a list of available serial ports, run the following command:
```
python -m serial.tools.list_ports
```

One of them should be the device we want to communicate with.
You can specify the device port in the following command in order to initiate the connection.
```
python -m serial.tools.miniterm <device_port> 115200
```

Here are a few potential examples:
```
# Windows
python -m serial.tools.miniterm COM3 115200
# macOS
python -m serial.tools.miniterm /dev/TODO_what_goes_here 115200
# Linux
python -m serial.tools.miniterm /dev/ttyUSB0 115200
```
