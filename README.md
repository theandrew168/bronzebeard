# bronzebeard
Bare-metal RISC-V Forth implementation

## What
Bronzebeard is an implementation of the [Forth programming language](https://en.wikipedia.org/wiki/Forth_(programming_language)) for the [RISC-V ISA](https://en.wikipedia.org/wiki/RISC-V).
It is designed to run on [bare metal](https://en.wikipedia.org/wiki/Bare_machine) with no reliance on an [operating system](https://en.wikipedia.org/wiki/Operating_system) or existing software of any kind.

## Why
Much of modern software has accrued vast amounts of bulk and complexity throughout the years.
Can useful software be developed without relying on any of it?
That's the question that this project seeks to answer.
I believe that the rise of RISC-V provides a great opportunity to explore different methods of program development.
Installing a full operating system isn't always a prerequisite to building something valuable.

## How
Bronzebeard is written directly in RISC-V assembly.
The [simpleriscv](https://github.com/theandrew168/simpleriscv) assembler is used because of its independence from large, complex toolchains.
It is portable, minimal, and easy to understand.

## Prior Art
Forth was initially designed and created by [Charles Moore](https://en.wikipedia.org/wiki/Charles_H._Moore).
Many folks have adapted its ideas and principles to solve their own problems.
[Moving Forth](http://www.bradrodriguez.com/papers/moving1.htm) by Brad Rodriguez is an amazing source of Forth implementation details and tradeoffs.
If you are looking for some introductory content surrounding the Forth language in general, I recommend the book [Starting Forth](https://www.forth.com/starting-forth/) by Leo Brodie.

[Sectorforth](https://github.com/cesarblum/sectorforth) by Cesar Blum is the source of Bronzebeard's general structure.
He took inspiration from a [1996 Usenet thread](https://groups.google.com/g/comp.lang.forth/c/NS2icrCj1jQ) wherein folks discussed requirements for a minimal yet fully functional Forth implementation.

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

### Windows
The USB-based devices that Bronzebeard targets don't work well with Windows by default.
They each need to be associated with the generic [WinUSB](https://docs.microsoft.com/en-us/windows-hardware/drivers/usbcon/winusb) driver in order to be identified and programmed.
The easiest way to accomplish this is with a tool called [Zadig](https://zadig.akeo.ie/).
With the device attached to your computer (and in DFU mode, if applicable), use Zadig to assign the WinUSB driver to the device.

### macOS
Once Python is installed, everything else should simply work out of the box!

### Linux
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
pip install -r requirements.txt
```

## Longan Nano
This section details how to run Bronzebeard on the [Longan Nano](https://www.seeedstudio.com/Sipeed-Longan-Nano-RISC-V-GD32VF103CBT6-Development-Board-p-4205.html).

### Cables
1. Attach the USB to USB-C cable for programming via DFU
2. Attach the USB to TTL Serial cable for interacting over serial
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
python dfu.py 28e9:0189 forth.bin
```

### Interact
TODO: what does this look like on other platforms?
```
python -m serial.tools.miniterm /dev/ttyUSB0 115200
```
