Assembly Language
=================
RISC-V assembly programs are written as plain text files.
The file extension is mostly arbitrary but :code:`.asm` and :code:`.S` are quite common.
An assembly program is a linear sequence of "items".
Items can be many things: labels, instructions, literal bytes and strings, etc.

The Bronzebeard assembly syntax also supports basic comments.
Single-line comments can be intermixed with the source code by using the :code:`#` character.
Multi-line comments are not supported at this point in time.
However, you can always emulate multi-line comments by using multiple single-line comments to construct larger blocks.

Instructions
------------
Instructions instruct the CPU to do something with a given set of registers and/or immediate values.
Registers are named 32-bit "slots" that the CPU can use to store information at runtime.
Immediate values are typically integers of varying sizes (depending on the specific instruction at hand).

An instruction is written as a name followed by its arguments.
The arguments can be separated by a comma for readability but this isn't a requirement (commas are treated as whitespace).
Here is an example of using the :code:`addi` instruction to the value :code:`12` into register :code:`x1`::

  # x1 = 0 + 12
  addi x1, zero, 12

Registers
---------
The RISC-V ISA specifies 32 general purpose registers.
Each register is cable of a holding a single 32-bit value (or 64 bits on a 64-bit system).
Register 0 is the only special case: it always holds the value zero no matter what gets written to it.
There also exists the "program counter" which is a register that holds the location of the current program's execution.
This :code:`pc` register can't be accessed directly but is utilized by certain instructions.

A given register can be referenced in multiple ways: by number, by name, or by its alias.
The alias and suggested usage of each register can be ignored when writing simple assembly programs.
They are given more meaning when dealing with more complex `ABIs <https://en.wikipedia.org/wiki/Application_binary_interface>`_ and `calling conventions <https://en.wikipedia.org/wiki/Calling_convention>`_.

==============  ==============  =============  ===============
Number          Name            Alias          Suggested Usage
==============  ==============  =============  ===============
:code:`0`       :code:`x0`      :code:`zero`   Hard-wired zero
:code:`1`       :code:`x1`      :code:`ra`     Return address
:code:`2`       :code:`x2`      :code:`sp`     Stack pointer
:code:`3`       :code:`x3`      :code:`gp`     Global pointer
:code:`4`       :code:`x4`      :code:`tp`     Thread pointer
:code:`5-7`     :code:`x5-7`    :code:`t0-2`   Temporary registers
:code:`8`       :code:`x8`      :code:`s0/fp`  Saved register / frame pointer
:code:`9`       :code:`x9`      :code:`s1`     Saved register
:code:`10-11`   :code:`x10-11`  :code:`a0-1`   Function arguments / return values
:code:`12-17`   :code:`x12-17`  :code:`a2-7`   Function arguments
:code:`18-27`   :code:`x18-27`  :code:`s2-11`  Saved registers
:code:`28-31`   :code:`x28-31`  :code:`t3-6`   Temporary registers
==============  ==============  =============  ===============

Constants
---------
A constant in Bronzebeard is the named result of an integer expression.
Floating point numbers or any other non-integer expression results aren't supported at this time.
Numbers can be represented as decimal, binary, or hex.
Character literals can also be used if surrounded by single-quotes.
Simple math operations such as addition, multiplication, shifting, and binary ops all work as one would expect.
The actual precedence rules and evaluation of arithmetic expressions is handled by the Python lauguage itself (via the `eval <https://docs.python.org/3/library/functions.html#eval>`_ builtin).

Here are a few examples::

  RCU_BASE_ADDR = 0x40021000
  RCU_APB2EN_OFFSET = 0x18

  GPIO_BASE_ADDR_C = 0x40011000
  GPIO_CTL1_OFFSET = 0x04
  GPIO_MODE_OUT_50MHZ = 0b11
  GPIO_CTL_OUT_PUSH_PULL = 0b00

  FOO = 42
  BAR = FOO * 2
  BAZ = (BAR >> 1) & 0b11111

  QMARK = '?'
  SPACE = ' '

Labels
------ 
Labels are single-token items that end with a colon such as :code:`foo:` or :code:`bar:`.
They effectively mark a location in the assembly program with a human-readable name.
Labels have two primary use cases: being targets for jump / branch offsets and marking the position of data.

Here is an example that utilizes a label in order to create an infinite loop::

  loop:
      j loop

Notice how the label ends with a colon when it is defined but not when it is referenced.
This is necessary to distinguish label definitions from other keywords.

Include
-------
The :code:`include` keyword can be used to include other assembly source files into the current program.
At the moment, files are searched relative to the file containing the :code:`include` keyword.
Additional include directories can be specified on the command via the :code:`-i` (or :code:`--include`) flag.

Here is a basic example::

  include gd32vf103.asm

You can find another example of this in the `Longan Nano LED example <https://github.com/theandrew168/bronzebeard/blob/master/examples/longan_nano_led.asm>`_.

Include Bytes
-------------
Similar to :code:`include`, :code:`include_bytes` can be used to embed binary files into the output binary.
Regardless of the file's type, it will be simply be baked into the binary as raw bytes.

Here are some example::

  include_bytes cat.jpg
  include_bytes prelude.forth
  include_bytes my_random_file.dat

String Literals
---------------
String literals allow you to embed UTF-8 strings into your binary.
They start with the :code:`string` keyword (then a single space) and are followed by any number of characters (til end of line).
This item is lexed in a special way such that the literal string content remains unchanged.
This means that spaces, newlines, quotes, and comments are all preserved within the literal string value.

The regex used for lexing these items is roughly: :code:`string (.*)`::

  # note that any comments after these lines would be included in the string
  string hello
  string "world"
  string "hello world"
  string hello  ##  world
  string hello\nworld
  string   hello\\nworld

Numeric Sequence Literals
-------------------------
Numeric sequence literals allow you to embed homogeneous sequences of numbers into your binary.

Integer Sequences
^^^^^^^^^^^^^^^^^
Integers can be positive or negative and expressed in decimal, binary, or hex.

=================  ================
Keyword            Bytes per Number
=================  ================
:code:`bytes`      1
:code:`shorts`     2
:code:`ints`       4
:code:`longs`      4
:code:`longlongs`  8
=================  ================

Examples
^^^^^^^^
Here are a few examples of the various numeric sequences::

  bytes 1 2 0x03 0b100 5 0x06 0b111 8
  bytes -1 0xff  # same value once encoded as 2's comp integers
  shorts 0x1234 0x5678
  ints  1 2 3 4
  longs 1 2 3 4  # same as above (both 4 bytes each)

Packed Values
-------------
Packed values allow you embed packed numeric literals, expressions, or references into your binary.
They start with the :code:`pack` keyword and are followed by a format specifier and a value.
The format specifier is a subset of the format outlined in Python's builtin `struct module <https://docs.python.org/3/library/struct.html#format-characters>`_.

The pack format is composed of two characters: the first specifies endianness and the second details the numeric size and type:

=========  ==================  =====
Character  Meaning             Bytes
=========  ==================  =====
:code:`<`  Little endian       N/A
:code:`>`  Big endian          N/A
:code:`b`  Signed char         1
:code:`B`  Unsigned char       1
:code:`h`  Signed short        2
:code:`H`  Unsigned short      2
:code:`i`  Signed int          4
:code:`I`  Unsigned int        4
:code:`l`  Signed long         4
:code:`L`  Unsigned long       4
:code:`q`  Signed long long    8
:code:`Q`  Unsigned long long  8
=========  ==================  =====

Here are a few examples::

  pack <B, 0
  pack <B, 255
  pack <h, -1234
  pack <I ADDR
  pack <I %position(foo, ADDR)

Shorthand Syntax
^^^^^^^^^^^^^^^^
In addition to the above :code:`pack` keyword, a small set of shorthand keywords (loosely based on NASM syntax) are available for embedding integers of specific widths.
The specific endianness and signedness will be inferred by the assembler's configuration and resolved integer value, respectively.
Internally, these are implemented as AST transformations to the more general :code:`pack` syntax.

==========  =====
Keyword     Bytes
==========  =====
:code:`db`  1
:code:`dh`  2
:code:`dw`  4
:code:`dd`  8
==========  =====

Here are some examples::

  # 1-byte integers
  db -1  # 2's complement will end up as 0xff
  db 0xff
  db 0x20

  # 2-byte integers
  dh 0x2000

  # 4-byte integers
  dw 0x20000000
  dw some_label
  dw RAM_ADDR

  # 8-byte integers
  dd 0x2000000000000000

Alignment
---------
The :code:`align` keyword tells the assembler to enforce alignment to a certain byte boundary.
This alignment is achieved by padding the binary with :code:`0x00` bytes until it aligns with the boundary.
In pseudo-code, the assembler adds zeroes until: :code:`len(binary) % alignment == 0`::

  # align the current location in the binary to 4 bytes
  align 4

Alignment is important when mixing instructions and data into the same binary (which happens quite often).
According to the RISC-V spec, instructions MUST be aligned to a 32-bit (4 byte) boundary unless the CPU supports the "C" Standard Extension for Compressed Instructions (in which case the alignment requirement is relaxed to a 16-bit (2 byte) boundary).

For example, the following code may be invalid because the instruction is not on a 32-bit boundary::

  bytes 0x42      # occupies 1 byte
  addi x0, x0, 0  # misaligned :(

To fix this, we need to tell the assembler to ensure that the binary is aligned to 32 bits (4 bytes) before proceeding::

  bytes 0x42      # occupies 1 byte
  align 4         # will pad the binary with 3 0x00 bytes
  addi x0, x0, 0  # aligned :)

Modifiers
---------
In addition to basic arithmetic operations, Bronzebeard assembly supports a small number of "modifiers".
Note that the :code:`%position` modifier is NOT permitted within the value of a constant.

You can think of these like simple, builtin functions:

* :strong:`%hi(value)` - Calculate the sign-adjusted top 20 bits of a value
* :strong:`%lo(value)` - Calculate the sign-adjusted bottom 12 bits of a value
* :strong:`%position(label, addr)` - Calculate the position of a label relative to given base address

Error
-----
The keyword :code:`error` can be used to abort the assembler in a human-understandable fashion.
For example, if a given board doesn't support LCD screens but the main program requires it, an :code:`error` directive can be used to say "This device doesn't support LCD screens" instead of dropping a cryptic "symbol not found" type of error sometime later.

This keyword captures a simple message based on the regex: :code:`error (.*)`::

  error This device doesn't support LCD screens
