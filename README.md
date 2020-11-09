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
Additionally, if you are looking for some introductory content surrounding the Forth language in general, I recommend the book [Starting Forth](https://www.forth.com/starting-forth/) by Leo Brodie.

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

## Cables
USB-C for programming  
USB to TTL Serial for interacting (VCC attached to 5V, not 3.3V!)  

## Setup
Need custom build of dfu-util:
```
git clone git://git.code.sf.net/p/dfu-util/dfu-util
cd dfu-util
./autogen.sh
./configure
make
sudo make install
cd ..
rm -r dfu-util/
```

If you want to be able to do this stuff as non-root:  
Need udev rules (for the Longan Nano and serial cable[s]):
```
sudo vim /etc/udev/rules.d/99-bronzebeard.rules
```
```
# Longan Nano / Wio Lite
ATTRS{idVendor}=="28e9", ATTRS{idProduct}=="0189", MODE="0666"
# Adafruit USB to TTL Serial Cable
ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", MODE="0666"
# SparkFun USB to TTL Serial Cable
ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", MODE="0666"
```
```
sudo udevadm control --reload
```

## Build
```
python3 -m venv venv
. venv/bin/activate
python forth.py
```

## Program
Enable DFU mode: press BOOT, press RESET, release RESET, release BOOT.
```
dfu-util --download forth.bin --alt 0 --dfuse-address 0x08000000:0x20000
```

## Usage
```
python -m serial.tools.miniterm /dev/ttyUSB0 115200
```
