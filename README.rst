Bronzebeard
===========
Bronzebeard is a simple, standalone assembler for developing bare metal `RISC-V <https://en.wikipedia.org/wiki/Riscv>`_ programs.
It is designed for applications that stand on their own without relying on `operating systems <https://en.wikipedia.org/wiki/Operating_system>`_, frameworks, SDKs, or pre-existing software of any kind.
Bronzebeard and its tools are implemented purely in Python.
It has been written in order to be free from large, complex toolchains.
This keeps the project portable, minimal, and easy to understand.

Motivation
----------
Much of modern software has accrued vast amounts of bulk and complexity throughout the years.
Can useful software be developed without relying on any of it?
That's the question that this project seeks to answer.
I believe that the rise of RISC-V provides a great opportunity to explore different methods of program development.
Installing a full operating system doesn't have to be a prerequisite to building something useful.

Check out the `DerzForth <https://github.com/theandrew168/derzforth>`_ project for further elaboration of this idea.

Devices
-------
The assembler itself supports the base 32-bit instruction set as well as the M, A, and C extensions (RV32IMAC).
At the moment, Bronzebeard has only been used to target the `Longan Nano <https://www.seeedstudio.com/Sipeed-Longan-Nano-RISC-V-GD32VF103CBT6-Development-Board-p-4205.html>`_ and the `Wio Lite <https://www.seeedstudio.com/Wio-Lite-RISC-V-GD32VF103-p-4293.html>`_.
There are plans to test on additional RISC-V boards such as the `HiFive1 Rev B <https://www.sifive.com/boards/hifive1-rev-b>`_ in the future.

Installation
------------
If you are unfamiliar with `virtual environments <https://docs.python.org/3/library/venv.html>`_, I suggest taking a brief moment to learn about them and set one up.
The Python docs provide a great `tutorial <https://docs.python.org/3/tutorial/venv.html>`_ for getting started with virtual environments and packages.

Bronzebeard can be installed via pip::

  pip install bronzebeard

Assemble!
---------
With Bronzebeard installed::

  bronzebeard examples/example.asm

By default, the assembled output binary will be placed in a file named `bb.out`.

Command Line Interface
----------------------
.. code-block:: none

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
    --version             print assembler version and exit