# Bronzebeard Documentation
This document describes the assembly language dialect that Bronzebeard understands.

## General
RISC-V assembly programs are written as plain text files.
The file extension is mostly arbitrary but `.asm` and `.S` are quite common.
An assembly program is a linear sequence of "items".
Items can be many things: labels, instructions, literal bytes and strings, etc.

The Bronzebeard assembly syntax also supports basic comments.
Single-line comments can be intermixed with the source code by using the `#` character.
Multi-line comments are not supported at this point in time.
However, you can always emulate multi-line comments by using multiple single-line comments to construct larger blocks.

### Labels
Labels are single-token items that end with a colon such as `foo:` or `bar:`.
They effectively mark a location in the assembly program with a human-readable name.
Labels have two primary use cases: being targets for jump / branch offsets and marking the position of data.

Here is an example that utilizes a label in order to create an infinite loop:
```
# loop forever
loop:
    jal zero, loop
```
Notice how the label ends with a colon when it is defined but not when it is referenced.
This is necessary to distinguish label definitions from other keywords.

### Instructions
An instruction is the basic building block of any CPU.
At a bare minimum, RISC-V supports [37 instructions](https://github.com/theandrew168/bronzebeard/tree/master/docs#instructions-1).
An instruction tells the CPU to do something with a given set of registers and/or immediate values.
Registers are named 32-bit "slots" that the CPU can use to store information at runtime.
Immediate values are typically integers of varying sizes (depending on the specific instruction at hand).

An instruction is written as a name followed by its arguments.
The arguments can be separated by a comma for readability but this isn't a requirement (commas are treated as whitespace).
Here is an example of using the `addi` instruction to the value `12` into register `x1`:
```
# x1 = 0 + 12
addi x1, zero, 12
```

### Constants
A constant in Bronzebeard is the named result of an integer expression.
Floating point numbers or any other non-integer expression results aren't supported at this time.
Numbers can be represented as decimal, binary, or hex.
Simple math operations such as addition, multiplication, shifting, and binary ops all work (mostly) as expected.
The actual precedence rules and evaluation of arithmetic expressions is handled by the Python lauguage itself (via the [eval](https://docs.python.org/3/library/functions.html#eval) builtin).

Here are a few examples:
```
RCU_BASE_ADDR = 0x40021000
RCU_APB2EN_OFFSET = 0x18

GPIO_BASE_ADDR_C = 0x40011000
GPIO_CTL1_OFFSET = 0x04
GPIO_MODE_OUT_50MHZ = 0b11
GPIO_CTL_OUT_PUSH_PULL = 0b00

FOO = 42
BAR = FOO * 2
BAZ = (BAR >> 1) & 0b11111
```

### Modifiers
In addition to basic arithmetic operations, Bronzebeard assembly supports a small number of "modifiers".
You can think of these like simple, builtin functions:
* **%hi(value)** - Calculate the sign-adjusted top 20 bits of a value
* **%lo(value)** - Calculate the sign-adjusted bottom 12 bits of a value
* **%position(label, addr)** - Calculate the absolute position of a label from a given base address

### String Literals
String literals allow you to embed UTF-8 strings into your binary.
They start with the `string` keyword and are followed by one or words.
```
string hello
string world
string hello world
string hello   world  # same as above
```
**NOTE:** Since the lexer compresses whitespace, any gap between words will be reduced to a single space.
The lexer also strips any leading or trailing whitespace from the sequence of words.
Be careful with this!
If you have a need for leading / trailing / duplicate whitespace, consider using a `bytes` literal instead.

### Bytes Literals
Bytes literals allow you to embed arbitrary byte sequences into your binary.
They start with the `bytes` keyword and followed by one or more integers between 0 and 255.
The integers can be expressed in decimal, binary, or hex.
```
bytes 1 2 0x03 0b100 5 0x06 0b111 8
```

### Packed Literals
Packed literals allow you embed packed integer / float values into your binary.
They start with the `pack` keyword and are followed by a format specifier and a value.
The format specifier is based on Python's builtin [struct module](https://docs.python.org/3/library/struct.html#format-characters).
The value can be a literal or another expression (such as a constant or result of a modifier).
As with all other items, commas are optional.
```
pack <B, 0
pack <B, 255
pack <I ADDR
pack <f 3.14159
pack <I %position(foo, ADDR)
```

### Alignment
The `align` keyword tells the assembler to enforce alignment to a certain byte boundary.
This alignment is achieved by padding the binary with `0x00` bytes until it aligns with the bounary.
In pseudo-code, the assembler adds zeroes until: `len(binary) % alignment == 0`.
```
# align the current location in the binary to 2 bytes
align 2
```

Alignment is important when mixing instructions and data into the same binary (which happens quite often).
According to the RISC-V spec, instructions MUST be aligned to a 32-bit (4 byte) boundary unless the CPU supports the "C" Standard Extension for Compressed Instructions (in which case the alignment requirement is relaxed to a 16-bit (2 byte) boundary).

For example, the following code is invalid (on an RV32IMAC device) because the instruction is not on a 16-bit boundary:
```
bytes 0x42          # occupies 1 byte
addi zero, zero, 0  # misaligned :(
```

To fix this, we need to tell the assembler to ensure that the binary is aligned to 16 bits (2 bytes) before proceeding:
```
bytes 0x42          # occupies 1 byte
align 2             # will pad the binary with 1 0x00 byte
addi zero, zero, 0  # aligned :)
```

## Example
Consider the following example:
```
ROM_ADDR = 0x02000000

# CPU starts executing here, skip data and jump to main
start:
    jal zero, main

# misc data that the program needs
data:
    string foo bar data here
    bytes 0x00 0x01 0x02 0x03

# instructions must be aligned to a 16-bit boundary (32-bit boundary without C extension support)
align 2

# main program starts here
main:
    # load address of data into register t0
    lui t0, %hi(%position(data, ROM_ADDR))
    addi t0, t0, %lo(%position(data, ROM_ADDR))
    # do stuff with data
    # ...
```

This program contains three labels: `start`, `data`, and `main`.
The CPU will execute this program starting at `start` simply because it is at the top and assembly programs always execute top-to-bottom by default.
The program then skips over the `data` segment by jumping to `main`, where the main program logic / loop exists.
Since the program data is marked with a label, it can be referenced by name in subsequent code.

You might be wondering: why are `%position` and `ROM_ADDR` needed here?
If the data is marked with a label, can't we just load that directly and reference it?
This would be the case IF your device's flash ROM happened to start at address zero (which will likely never happen).
Flash ROM is more likely to be mapped to a higher location in memory (such as `0x08000000` on GD32 devices).
This means that in order to obtain the actual, absolute position of `data` in memory, we need to add its position to the ROM address.

## Common Patterns
Given that the RISC-V ISA is so minimal, you end up developing small "recipes" for common operations.

### Load Immediate
Loading an integer that is outside of the range [-2048, 2047] requires two instructions.
The first instruction loads the upper 20 bits of the value and the second loads the bottom 12.

This pattern loads the hex value `0x20000000` into register `x1`.
```
lui x1, %hi(0x20000000)
addi x1, x1, %lo(0x20000000)
```

### Copy Register
This pattern copies a value from register `x1` to `x2`.
```
addi x2, x1, 0
```

### Bitwise Negation
This pattern flips all 1s to 0s and 0s to 1s for register `x1`.
```
xori x1, x1, -1
```

### No Operation
This pattern intentionally does nothing.
```
addi zero, zero, 0
```

## Registers
The RISC-V ISA specifies 32 general purpose registers.
Each register is cable of a holding a single 32-bit value (or 64 bits on a 64-bit system).
Register 0 is the only special case: it always holds the value zero no matter what gets written to it.
There also exists the "program counter" which is a register that holds the location of the current program's execution.
This `pc` register can't be accessed directly but is utilized by certain instructions.

A given register can be referenced in multiple ways: by number, by name, or by its alias.
The alias and suggested usage of each register can be ignored when writing simple assembly programs.
They are given more meaning when dealing with more complex [ABIs](https://en.wikipedia.org/wiki/Application_binary_interface) and [calling conventions](https://en.wikipedia.org/wiki/Calling_convention).

| Number  | Name     | Alias   | Suggested Usage |
| ------- | -------- | ------- | --------------- |
| `0`     | `x0`     | `zero`  | Hard-wired zero |
| `1`     | `x1`     | `ra`    | Return address  |
| `2`     | `x2`     | `sp`    | Stack pointer   |
| `3`     | `x3`     | `gp`    | Global pointer  |
| `4`     | `x4`     | `tp`    | Thread pointer  |
| `5`     | `x5`     | `t0`    | Temporary register |
| `6-7`   | `x6-7`   | `t1-2`  | Temporary registers |
| `8`     | `x8`     | `s0/fp` | Saved register / frame pointer |
| `9`     | `x9`     | `s1`    | Saved register  |
| `10-11` | `x10-11` | `a0-1`  | Function arguments / return values |
| `12-17` | `x12-17` | `a2-7`  | Function arguments |
| `18-27` | `x18-27` | `s2-11` | Saved registers |
| `28-31` | `x28-31` | `t3-6`  | Temporary registers |

## Instructions
These tables provide summaries for the baseline RISC-V instructions and common extensions.
Full [specifications](https://riscv.org/technical/specifications/) be found on the RISC-V website.

### RV32I Base Instruction Set
| Name     | Parameters    | Description |
| -------- | ------------- | ----------- |
| `lui`    | rd, imm       | load upper 20 bits of `rd` with 20-bit `imm`, fill lower 12 bits with zeroes |
| `auipc`  | rd, imm       | load upper 20 bits of `pc` with 20-bit `imm`, fill lower 12 bits with zeroes, add this offset to address of this instruction and store into `rd` |
| `jal`    | rd, imm       | jump offset 20-bit `imm` and store return address into `rd` |
| `jalr`   | rd, rs1, imm  | jump offset 12-bit `imm` plus `rs1` and store return addres into `rd` |
| `beq`    | rs1, rs2, imm | jump offset 12-bit `imm` if `rs1` is equal to `rs2` |
| `bne`    | rs1, rs2, imm | jump offset 12-bit `imm` if `rs1` is not equal to `rs2` |
| `blt`    | rs1, rs2, imm | jump offset 12-bit `imm` if `rs1` is less than `rs2` |
| `bge`    | rs1, rs2, imm | jump offset 12-bit `imm` if `rs1` is greater than or equal to `rs2` |
| `bltu`   | rs1, rs2, imm | same as `blt` but treat values as unsigned numbers |
| `bgeu`   | rs1, rs2, imm | same as `bge` but treat values as unsigned numbers |
| `lb`     | rd, rs1, imm  | load 8-bit value from addr in `rs1` plus 12-bit `imm` into `rd` (sign extend) |
| `lh`     | rd, rs1, imm  | load 16-bit value from addr in `rs1` plus 12-bit `imm` into `rd` (sign extend) |
| `lw`     | rd, rs1, imm  | load 32-bit value from addr in `rs1` plus 12-bit `imm` into `rd` |
| `lbu`    | rd, rs1, imm  | load 8-bit value from addr in `rs1` plus 12-bit `imm` into `rd` (zero extend) |
| `lhu`    | rd, rs1, imm  | load 16-bit value from addr in `rs1` plus 12-bit `imm` into `rd` (zero extend) |
| `sb`     | rs1, rs2, imm | store 8-bit value from `rs2` into addr in `rs1` plus 12-bit `imm` |
| `sh`     | rs1, rs2, imm | store 16-bit value from `rs2` into addr in `rs1` plus 12-bit `imm` |
| `sw`     | rs1, rs2, imm | store 32-bit value from `rs2` into addr in `rs1` plus 12-bit `imm` |
| `addi`   | rd, rs1, imm  | add 12-bit `imm` to `rs1` and store into `rd` |
| `slti`   | rd, rs1, imm  | store 1 into `rd` if `rs1` is less than 12-bit `imm` else store 0|
| `sltiu`  | rd, rs1, imm  | same as `slti` but treat values as unsigned numbers |
| `xori`   | rd, rs1, imm  | bitwise XOR 12-bit `imm` with `rs1` and store into `rd` |
| `ori`    | rd, rs1, imm  | bitwise OR 12-bit `imm` with `rs1` and store into `rd` |
| `andi`   | rd, rs1, imm  | bitwise AND 12-bit `imm` with `rs1` and store into `rd` |
| `slli`   | rd, rs1, amt  | shift `rs1` left by `amt` bits and store into `rd` |
| `srli`   | rd, rs1, amt  | shift `rs1` right by `amt` bits and store into `rd` (shift in zeroes) |
| `srai`   | rd, rs1, amt  | shift `rs1` right by `amt` bits and store into `rd` (shift in sign bit) |
| `add`    | rd, rs1, rs2  | add `rs2` to `rs1` and store into `rd` |
| `sub`    | rd, rs1, rs2  | subtract `rs2` from `rs1` and store into `rd` |
| `sll`    | rd, rs1, rs2  | shift `rs1` left by `rs2` bits and store into `rd` |
| `slt`    | rd, rs1, rs2  | store 1 into `rd` if `rs1` is less than `rs2` else store 0 |
| `sltu`   | rd, rs1, rs2  | same as `slt` but treat values as unsigned numbers |
| `xor`    | rd, rs1, rs2  | bitwise XOR `rs2` with `rs1` and store into `rd` |
| `srl`    | rd, rs1, rs2  | shift `rs1` right by `rs2` bits and store into `rd` (shift in zeroes) |
| `sra`    | rd, rs1, rs2  | shift `rs1` right by `rs2` bits and store into `rd` (shift in sign bit) |
| `or`     | rd, rs1, rs2  | bitwise OR `rs2` with `rs1` and store into `rd` |
| `and`    | rd, rs1, rs2  | bitwise AND `rs2` with `rs1` and store into `rd` |
| `fence`  | succ, pred    | TODO |
| `ecall`  | \<none\>      | TODO |
| `ebreak` | \<none\>      | TODO |

### RV32M Standard Extension
| Name     | Parameters   | Description |
| -------- | ------------ | ----------- |
| `mul`    | rd, rs1, rs2 | multiply `rs1` (signed) by `rs2` (signed) and store lower 32 bits into `rd` |
| `mulh`   | rd, rs1, rs2 | multiply `rs1` (signed) by `rs2` (signed) and store upper 32 bits into `rd` |
| `mulhsu` | rd, rs1, rs2 | multiply `rs1` (signed) by `rs2` (unsigned) and store upper 32 bits into `rd` |
| `mulhu`  | rd, rs1, rs2 | multiply `rs1` (unsigned) by `rs2` (unsigned) and store upper 32 bits into `rd` |
| `div`    | rd, rs1, rs2 | divide (signed) `rs1` by `rs2` and store into `rd` |
| `divu`   | rd, rs1, rs2 | divide (unsigned) `rs1` by `rs2` and store into `rd` |
| `rem`    | rd, rs1, rs2 | remainder (signed) of `rs1` divided by `rs2` and store into `rd` |
| `remu`   | rd, rs1, rs2 | remainder (unsigned) of `rs1` divided by `rs2` and store into `rd` |

### RV32A Standard Extension
All of the following atomic instructions also accept two additional parameters: `aq` and `rl`.
These are short for "acquire" and "release" and must either be both specified or both unspecified.
The default for each if unspecified is zero.

For example:
```
# both aq and rl are zero
lr.w t0 t1
lr.w t0 t1 0 0

# both aq and rl are one
lr.w t0 t1 1 1

# mix and match
lr.w t0 t1 0 1  # aq=0, rl=1
lr.w t0 t1 1 0  # aq=1, rl=0
```
 
| Name        | Parameters   | Description |
| ----------- | ------------ | ----------- |
| `lr.w`      | rd, rs1      | TODO        |
| `sc.w`      | rd, rs1, rs2 | TODO        |
| `amoswap.w` | rd, rs1, rs2 | TODO        |
| `amoadd.w`  | rd, rs1, rs2 | TODO        |
| `amoxor.w`  | rd, rs1, rs2 | TODO        |
| `amoand.w`  | rd, rs1, rs2 | TODO        |
| `amoor.w`   | rd, rs1, rs2 | TODO        |
| `amomin.w`  | rd, rs1, rs2 | TODO        |
| `amomax.w`  | rd, rs1, rs2 | TODO        |
| `amominu.w` | rd, rs1, rs2 | TODO        |
| `amomaxu.w` | rd, rs1, rs2 | TODO        |

### RV32C Standard Extension
| Name         | Parameters        | Description |
| ------------ | ----------------- | ----------- |
| `c.addi4spn` | rd', nzuimm       | TODO        |
| `c.lw`       | rd', rs1', uimm   | TODO        |
| `c.sw`       | rs1', rs2', uimm  | TODO        |
| `c.nop`      | \<none\>          | TODO        |
| `c.addi`     | rd/rs1!=0, nzimm  | TODO        |
| `c.jal`      | imm               | TODO        |
| `c.li`       | rd!=0, imm        | TODO        |
| `c.addi16sp` | nzimm             | TODO        |
| `c.lui`      | rd!={0,2}, nzimm  | TODO        |
| `c.srli`     | rd'/rs1', nzuimm  | TODO        |
| `c.srai`     | rd'/rs1', nzuimm  | TODO        |
| `c.andi`     | rd'/rs1', imm     | TODO        |
| `c.sub`      | rd'/rs1', rs2'    | TODO        |
| `c.xor`      | rd'/rs1', rs2'    | TODO        |
| `c.or`       | rd'/rs1', rs2'    | TODO        |
| `c.and`      | rd'/rs1', rs2'    | TODO        |
| `c.j`        | imm               | TODO        |
| `c.beqz`     | rs1', imm         | TODO        |
| `c.bnez`     | rs1', imm         | TODO        |
| `c.slli`     | rd/rs1!=0, nzuimm | TODO        |
| `c.lwsp`     | rd!=0, uimm       | TODO        |
| `c.jr`       | rs1!=0            | TODO        |
| `c.mv`       | rd!=0, rs2!=0     | TODO        |
| `c.jalr`     | rs1!=0            | TODO        |
| `c.add`      | rd/rs1!=0, rs2!=0 | TODO        |
| `c.swsp`     | rs2, uimm         | TODO        |
