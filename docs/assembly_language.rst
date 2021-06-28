Assembly Language
=================
RISC-V assembly programs are written as plain text files.
The file extension is mostly arbitrary but ".asm" and ".S" are quite common.
An assembly program is a linear sequence of "items".
Items can be many things: labels, instructions, literal bytes and strings, etc.

The Bronzebeard assembly syntax also supports basic comments.
Single-line comments can be intermixed with the source code by using the "#" character.
Multi-line comments are not supported at this point in time.
However, you can always emulate multi-line comments by using multiple single-line comments to construct larger blocks.

Registers
---------
The RISC-V ISA specifies 32 general purpose registers.
Each register is cable of a holding a single 32-bit value (or 64 bits on a 64-bit system).
Register 0 is the only special case: it always holds the value zero no matter what gets written to it.
There also exists the "program counter" which is a register that holds the location of the current program's execution.
This "PC" register can't be accessed directly but is utilized by certain instructions.

A given register can be referenced in multiple ways: by number, by name, or by its alias.
The alias and suggested usage of each register can be ignored when writing simple assembly programs.
They are given more meaning when dealing with more complex `ABIs <https://en.wikipedia.org/wiki/Application_binary_interface>`_ and `calling conventions <https://en.wikipedia.org/wiki/Calling_convention>`_.

======  ======  =====  ===============
Number  Name    Alias  Suggested Usage
======  ======  =====  ===============
0       x0      zero   Hard-wired zero
1       x1      ra     Return address
2       x2      sp     Stack pointer
3       x3      gp     Global pointer
4       x4      tp     Thread pointer
5       x5      t0     Temporary register
6-7     x6-7    t1-2   Temporary registers
8       x8      s0/fp  Saved register / frame pointer
9       x9      s1     Saved register
10-11   x10-11  a0-1   Function arguments / return values
12-17   x12-17  a2-7   Function arguments
18-27   x18-27  s2-11  Saved registers
28-31   x28-31  t3-6   Temporary registers
======  ======  =====  ===============

Instructions
------------

Constants
---------

Labels
------

Include
-------

Modifiers
---------

String Literals
---------------

Numeric Sequence Literals
-------------------------

Packed Values
-------------

Alignment
---------
