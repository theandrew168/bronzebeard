Command Line Usage
==================
The Bronzebeard RISC-V assembler is a command line tool meant to be used from a terminal.
As such, it has various parameters and flags that can be used to customize its inputs, outputs, and behavior.

.. code-block:: none

  usage: bronzebeard [-h] [-v] [-c] [-i DIR] [-o FILE] [-l FILE] [--hex-offset OFFSET]
                     [--include-definitions] [--version]
                     input_asm
  
  Assemble RISC-V source code
  
  positional arguments:
    input_asm             input source file
  
  options:
    -h, --help            show this help message and exit
    -v, --verbose         verbose assembler output
    -c, --compress        identify and compress eligible instructions
    -i DIR, --include DIR
                          add a directory to the assembler search path
    -o FILE, --output FILE
                          output binary file (default "bb.out")
    -l FILE, --labels FILE
                          output resolved labels and their addresses
    --hex-offset OFFSET   output an additional Intel HEX file with the given offset
    --include-definitions
                          update the assembler search path to include common chip and
                          peripheral definitions
    --version             print assembler version and exit

Required Arguments
------------------

Input
^^^^^
An assembly source file to be assembled.
This file may include other files but the assembly process originates from a single file.

.. code-block:: none

  bronzebeard my_asm_file.asm

Optional Arguments
------------------

Help
^^^^
Print the assembler help message (shown above) and exit.

.. code-block:: none

  bronzebeard -h
  bronzebeard --help

Verbose
^^^^^^^
Output various diagnostic and debugging messages while assembling the source code.

.. code-block:: none

  bronzebeard -v my_asm_file.asm
  bronzebeard --verbose my_asm_file.asm

Compress
^^^^^^^^
Identify and compress eligible RISC-V instructions.
Note that while this option often reduces output binary size, compressed intructions may not be supported on all RV32 chips.
Be sure to check for a :code:`C` in the CPU description such as in :code:`RV32IMAC`.

.. code-block:: none

  bronzebeard -c my_asm_file.asm
  bronzebeard --compress my_asm_file.asm

Include
^^^^^^^
Add a directory to the assembler's search path.
This argument can be supplied multiple times and each invocation will add an additional directory to the search path.
The search path is used by the assembler to find files specified by :code:`include` directives within the source code.

.. code-block:: none

  bronzebeard -i foo/ -i bar/ my_asm_file.asm
  bronzebeard --include foo/ --include bar/ my_asm_file.asm

Output
^^^^^^
Specify the name and location of the output binary.

.. code-block:: none

  bronzebeard -o foo.out my_asm_file.asm
  bronzebeard --output foo.out my_asm_file.asm

Labels
^^^^^^
Output resolved labels and their addresses to a specified file.

.. code-block:: none

  bronzebeard -l labels.txt my_asm_file.asm
  bronzebeard --labels labels.txt my_asm_file.asm

Hex Offset
^^^^^^^^^^
Output an additional binary in the `Intel HEX <https://en.wikipedia.org/wiki/Intel_HEX>`_ format with the provided offset.
The output file will be named the same as the original binary but with a :code:`.hex` suffix attached.

.. code-block:: none

  bronzebeard --hex-offset 0x08000000 my_asm_file.asm

Include Definitions
^^^^^^^^^^^^^^^^^^^
Update the assembler's search path to include common chip and peripheral definitions.
This feature exists to absolve every project from having to redefine the large set of unchanging contants present in each RISC-V chip's documentation.
You can browse which devices and constants are supported `in the repo <https://github.com/theandrew168/bronzebeard/tree/master/bronzebeard/definitions>`_.

Once this argument is provided, you'll still need to include the specific definitions file into your source code (:code:`include "GD32VF103.asm"` for example).

.. code-block:: none

  bronzebeard --include-definitions my_asm_file.asm

Version
^^^^^^^
Print the assembler's current version and exit.

.. code-block:: none

  bronzebeard --version
