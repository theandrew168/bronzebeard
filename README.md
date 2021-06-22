# bronzebeard
Minimal ecosystem for bare-metal RISC-V development

## Overview
Bronzebeard is a [single-file](https://github.com/theandrew168/bronzebeard/blob/master/bronzebeard/asm.py), [nanopass](https://legacy.cs.indiana.edu/~dyb/pubs/nano-jfp.pdf) assembler for developing [bare metal](https://en.wikipedia.org/wiki/Bare_machine) [RISC-V](https://en.wikipedia.org/wiki/Riscv) programs.
It is designed for applications that stand on their own without relying on [operating systems](https://en.wikipedia.org/wiki/Operating_system), frameworks, SDKs, or pre-existing software of any kind.
Bronzebeard and its tools are implemented purely in Python.
It has been written in order to be free from large, complex toolchains.
This keeps the project portable, minimal, and easy to understand.

## Motivation
Much of modern software has accrued vast amounts of bulk and complexity throughout the years.
Can useful software be developed without relying on any of it?
That's the question that this project seeks to answer.
I believe that the rise of RISC-V provides a great opportunity to explore different methods of program development.
Installing a full operating system doesn't have to be a prerequisite to building something useful.

Check out the [DerzForth](https://github.com/theandrew168/derzforth) project for further elaboration of this idea.

## Documentation
Most of the surface-level documentation for Bronzebeard lives right here in this README.
For more specific details regarding the usage and accepted syntax of the assembler, check out the [docs](https://github.com/theandrew168/bronzebeard/tree/master/docs) directory.
This is where the project's primary documentation will live until the time comes to setup something more official.

## Devices
The assembler itself supports the base 32-bit instruction set as well as the M, A, and C extensions (RV32IMAC).
At the moment, Bronzebeard has only been used to target the [Longan Nano](https://www.seeedstudio.com/Sipeed-Longan-Nano-RISC-V-GD32VF103CBT6-Development-Board-p-4205.html) and the [Wio Lite](https://www.seeedstudio.com/Wio-Lite-RISC-V-GD32VF103-p-4293.html).
There are plans to test on additional RISC-V boards such as the [HiFive1 Rev B](https://www.sifive.com/boards/hifive1-rev-b) in the future.

## Installation
If you are unfamiliar with [virtual environments](https://docs.python.org/3/library/venv.html), I suggest taking a brief moment to learn about them and set one up.
The Python docs provide a great [tutorial](https://docs.python.org/3/tutorial/venv.html) for getting started with virtual environments and packages.

Bronzebeard can be installed via pip:
```
pip install bronzebeard
```

## Assemble!
With Bronzebeard installed:
```
bronzebeard examples/example.asm
```

By default, the assembled output binary will be placed in a file named `bb.out`.

## Command Line Interface
```
usage: bronzebeard [-h] [-o OUTPUT] [--compress] [-v] [-vv] [--version] input_asm

Assemble RISC-V source code

positional arguments:
  input_asm             input source file

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        output binary file (default "bb.out")
  --compress            identify and compress eligible instructions
  -v, --verbose         verbose assembler output
  -vv, --very-verbose   very verbose assembler output
  --version             print assembler version and exit
```
