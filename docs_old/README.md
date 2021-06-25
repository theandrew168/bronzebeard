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
At a bare minimum, RISC-V supports [37 instructions](https://github.com/theandrew168/bronzebeard/tree/master/docs#rv32i-base-instruction-set).
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
Character literals can also be used if surrounded by single-quotes.
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

QMARK = '?'
SPACE = ' '
```

### Modifiers
In addition to basic arithmetic operations, Bronzebeard assembly supports a small number of "modifiers".
You can think of these like simple, builtin functions:
* **%hi(value)** - Calculate the sign-adjusted top 20 bits of a value
* **%lo(value)** - Calculate the sign-adjusted bottom 12 bits of a value
* **%position(label, addr)** - Calculate the position of a label relative to given base address

### String Literals
String literals allow you to embed UTF-8 strings into your binary.
They start with the `string` keyword (then a single space) and are followed by any number of characters (til end of line).
This item is lexed in a special way such that the literal string content remains unchanged.
This means that spaces, newlines, quotes, and comments are all preserved within the literal string value.

The regex used for lexing these items is roughly: `string (.*)`.
```
# note that any comments after these lines would be included in the string
string hello
string "world"
string "hello world"
string hello  ##  world
string hello\nworld
string   hello\\nworld
```

### Numeric Sequence Literals
Numeric sequence literals allow you to embed homogeneous sequences of numbers into your binary.

#### Integer Sequences
Integers can be positive or negative and expressed in decimal, binary, or hex.

| Keyword     | Bytes per Number |
| ----------- | ---------------- |
| `bytes`     | 1                |
| `shorts`    | 2                |
| `ints`      | 4                |
| `longs`     | 4                |
| `longlongs` | 8                |

#### Examples
```
bytes 1 2 0x03 0b100 5 0x06 0b111 8
bytes -1 0xff  # same value once encoded as 2's comp integers
shorts 0x1234 0x5678
ints  1 2 3 4
longs 1 2 3 4  # same as above (both 4 bytes each)
```

### Packed Values
Packed values allow you embed packed numeric literals, expressions, or references into your binary.
They start with the `pack` keyword and are followed by a format specifier and a value.
The format specifier is a subset of the format outlined in Python's builtin [struct module](https://docs.python.org/3/library/struct.html#format-characters).

The pack format is composed of two characters: the first specifies endianness and the second details the numeric size and type:
| Character | Bytes | Meaning |
| --------- | ----- | ------- |
| `<`       | N/A   | Little endian |
| `>`       | N/A   | Big endian |
| `b`       | 1     | Signed char |
| `B`       | 1     | Unsigned char |
| `h`       | 2     | Signed short |
| `H`       | 2     | Unsigned short |
| `i`       | 4     | Signed int |
| `I`       | 4     | Unsigned int |
| `l`       | 4     | Signed long |
| `L`       | 4     | Unsigned long |
| `q`       | 8     | Signed long long |
| `Q`       | 8     | Unsigned long long |

Here are a few examples:
```
pack <B, 0
pack <B, 255
pack <h, -1234
pack <I ADDR
pack <I %position(foo, ADDR)
```

#### Shorthand Syntax
In addition to the above `pack` keyword, a small set of shorthand keywords (loosely based on NASM syntax) are available for embedding integers of specific widths.
The specific endianness and signedness will be inferred by the assembler's configuration and resolved integer value, respectively.
Internally, these are implemented as AST transformations to the more general `pack` syntax.

| Keyword | Bytes |
| ------- | ----- |
| `db`    | 1     |
| `dh`    | 2     |
| `dw`    | 4     |
| `dd`    | 8     |

Here are some examples:
```
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
    li t0, %position(data, ROM_ADDR)
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

## Pseudo Instructions
These pseudo-instructions represent additional actions and can be used like regular instructions.
One of the early passes in the assembler will transform them as described in this table.

| Instruction           | Expansion             | Description |
| --------------------- | --------------------- | ----------- |
| `nop`                 | `addi x0, x0, 0`      | No operation |
| `li rd, imm`          | See below             | Load immediate |
| `mv rd, rs`           | `addi rd, rs, 0`      | Copy register |
| `not rd, rs`          | `xori rd, rs, -1`     | One's complement |
| `neg rd, rs`          | `sub rd, x0, rs`      | Two's complement |
| `seqz rd, rs`         | `sltiu rd, rs, 1`     | Set if == zero |
| `snez rd, rs`         | `sltu rd, x0, rs`     | Set if != zero |
| `sltz rd, rs`         | `slt rd, rs, x0`      | Set if < zero |
| `sgtz rd, rs`         | `slt rd, x0, rs`      | Set if > zero |
| `beqz rs, offset`     | `beq rs, x0, offset`  | Branch if == zero |
| `bnez rs, offset`     | `bne rs, x0, offset`  | Branch if != zero |
| `blez rs, offset`     | `bge x0, rs, offset`  | Branch if <= zero |
| `bgez rs, offset`     | `bge rs, x0, offset`  | Branch if >= zero |
| `bltz rs, offset`     | `blt rs, x0, offset`  | Branch if < zero |
| `bgtz rs, offset`     | `blt x0, rs, offset`  | Branch if > zero |
| `bgt rs, rt, offset`  | `blt rt, rs, offset`  | Branch if > |
| `ble rs, rt, offset`  | `bge rt, rs, offset`  | Branch if <= |
| `bgtu rs, rt, offset` | `bltu rt, rs, offset` | Branch if >, unsigned |
| `bleu rs, rt, offset` | `bgeu rt, rs, offset` | Branch if <=, unsigned |
| `j offset`            | `jal x0, offset`      | Jump |
| `jal offset`          | `jal x1, offset`      | Jump and link |
| `jr rs`               | `jalr x0, 0(rs)`      | Jump register |
| `jalr rs`             | `jalr x1, 0(rs)`      | Jump and link register |
| `ret`                 | `jalr x0, 0(x1)`      | Return from subroutine |
| `call offset`         | See below             | Call far-away subroutine |
| `tail offset`         | See below             | Tail call fair-away subroutine |
| `fence`               | `fence iorw, iorw`    | Fence on all memory and I/O |

### Expansion of `li rd, imm`
Depending on the value of the `imm`, `li` may get expanded into a few different combinations of instructions.

| Criteria | Expansion |
| -------- | --------- |
| `imm between [-2048, 2047]` | `addi rd, x0, %lo(imm)` |
| `imm & 0xfff == 0` | `lui rd, %hi(imm)` |
| otherwise | `lui rd, %hi(imm)`<br/>`addi rd, rd, %lo(imm)` |

### Expansion of `call offset`
Depending on how near / far away the label referred to by `offset` is, `call` may get expanded into a few different combinations of instructions.

| Criteria | Expansion |
| -------- | --------- |
| `offset` is near | `jal x1, %lo(offset)` |
| otherwise | `auipc x1, %hi(offset)`<br/>`jalr x1, x1, %lo(offset)` |

### Expansion of `tail imm`
Depending on how near / far away the label referred to by `offset` is, `tail` may get expanded into a few different combinations of instructions.

| Criteria | Expansion |
| -------- | --------- |
| `offset` is near | `jal x0, %lo(offset)` |
| otherwise | `auipc x6, %hi(offset)`<br/>`jalr x0, x6, %lo(offset)` |

## Instructions
These tables provide summaries for the baseline RISC-V instructions and common extensions.
Full [specifications](https://riscv.org/technical/specifications/) be found on the RISC-V website.
Additionally, more details about each instruction can be found [here](https://msyksphinz-self.github.io/riscv-isadoc/html/index.html).

### RV32I Base Instruction Set
| Instruction           | Description |
| --------------------- | ----------- |
| `lui rd, imm`         | load upper 20 bits of `rd` with 20-bit `imm`, fill lower 12 bits with zeroes |
| `auipc rd, imm`       | load upper 20 bits of `pc` with 20-bit `imm`, fill lower 12 bits with zeroes, add this offset to addr of this instruction and store into `rd` |
| `jal rd, imm`         | jump offset 20-bit MO2 `imm` and store return addr into `rd` |
| `jalr rd, rs1, imm`   | jump offset 12-bit MO2 `imm` plus `rs1` and store return addr into `rd` |
| `beq rs1, rs2, imm`   | jump offset 12-bit MO2 `imm` if `rs1` is equal to `rs2` |
| `bne rs1, rs2, imm`   | jump offset 12-bit MO2 `imm` if `rs1` is not equal to `rs2` |
| `blt rs1, rs2, imm`   | jump offset 12-bit MO2 `imm` if `rs1` is less than `rs2` |
| `bge rs1, rs2, imm`   | jump offset 12-bit MO2 `imm` if `rs1` is greater than or equal to `rs2` |
| `bltu rs1, rs2, imm`  | jump offset 12-bit MO2 `imm` if `rs1` is less than `rs2` (unsigned) |
| `bgeu rs1, rs2, imm`  | jump offset 12-bit MO2 `imm` if `rs1` is greater than or equal to `rs2` (unsigned) |
| `lb rd, rs1, imm`     | load 8-bit value from addr in `rs1` plus 12-bit `imm` into `rd` (sign extend) |
| `lh rd, rs1, imm`     | load 16-bit value from addr in `rs1` plus 12-bit `imm` into `rd` (sign extend) |
| `lw rd, rs1, imm`     | load 32-bit value from addr in `rs1` plus 12-bit `imm` into `rd` |
| `lbu rd, rs1, imm`    | load 8-bit value from addr in `rs1` plus 12-bit `imm` into `rd` (zero extend) |
| `lhu rd, rs1, imm`    | load 16-bit value from addr in `rs1` plus 12-bit `imm` into `rd` (zero extend) |
| `sb rs1, rs2, imm`    | store 8-bit value from `rs2` into addr in `rs1` plus 12-bit `imm` |
| `sh rs1, rs2, imm`    | store 16-bit value from `rs2` into addr in `rs1` plus 12-bit `imm` |
| `sw rs1, rs2, imm`    | store 32-bit value from `rs2` into addr in `rs1` plus 12-bit `imm` |
| `addi rd, rs1, imm`   | add 12-bit `imm` to `rs1` and store into `rd` |
| `slti rd, rs1, imm`   | store 1 into `rd` if `rs1` is less than 12-bit `imm` else store 0 |
| `sltiu rd, rs1, imm`  | store 1 into `rd` if `rs1` is less than 12-bit `imm` (unsigned) else store 0 |
| `xori rd, rs1, imm`   | bitwise XOR 12-bit `imm` with `rs1` and store into `rd` |
| `ori rd, rs1, imm`    | bitwise OR 12-bit `imm` with `rs1` and store into `rd` |
| `andi rd, rs1, imm`   | bitwise AND 12-bit `imm` with `rs1` and store into `rd` |
| `slli rd, rs1, shamt` | shift `rs1` left by `shamt` bits and store into `rd` |
| `srli rd, rs1, shamt` | shift `rs1` right by `shamt` bits and store into `rd` (shift in zeroes) |
| `srai rd, rs1, shamt` | shift `rs1` right by `shamt` bits and store into `rd` (shift in sign bit) |
| `add rd, rs1, rs2`    | add `rs2` to `rs1` and store into `rd` |
| `sub rd, rs1, rs2`    | subtract `rs2` from `rs1` and store into `rd` |
| `sll rd, rs1, rs2`    | shift `rs1` left by `rs2` bits and store into `rd` |
| `slt rd, rs1, rs2`    | store 1 into `rd` if `rs1` is less than `rs2` else store 0 |
| `sltu rd, rs1, rs2`   | store 1 into `rd` if `rs1` is less than `rs2` (unsigned) else store 0 |
| `xor rd, rs1, rs2`    | bitwise XOR `rs2` with `rs1` and store into `rd` |
| `srl rd, rs1, rs2`    | shift `rs1` right by `rs2` bits and store into `rd` (shift in zeroes) |
| `sra rd, rs1, rs2`    | shift `rs1` right by `rs2` bits and store into `rd` (shift in sign bit) |
| `or rd, rs1, rs2`     | bitwise OR `rs2` with `rs1` and store into `rd` |
| `and rd, rs1, rs2`    | bitwise AND `rs2` with `rs1` and store into `rd` |
| `fence succ, pred`    | order device I/O and memory accesses |
| `ecall`               | make a service request to the execution environment |
| `ebreak`              | return control to a debugging environment |

### RV32M Standard Extension
| Instruction           | Description |
| --------------------- | ----------- |
| `mul rd, rs1, rs2`    | multiply `rs1` (signed) by `rs2` (signed) and store lower 32 bits into `rd` |
| `mulh rd, rs1, rs2`   | multiply `rs1` (signed) by `rs2` (signed) and store upper 32 bits into `rd` |
| `mulhsu rd, rs1, rs2` | multiply `rs1` (signed) by `rs2` (unsigned) and store upper 32 bits into `rd` |
| `mulhu rd, rs1, rs2`  | multiply `rs1` (unsigned) by `rs2` (unsigned) and store upper 32 bits into `rd` |
| `div rd, rs1, rs2`    | divide (signed) `rs1` by `rs2` and store into `rd` |
| `divu rd, rs1, rs2`   | divide (unsigned) `rs1` by `rs2` and store into `rd` |
| `rem rd, rs1, rs2`    | remainder (signed) of `rs1` divided by `rs2` and store into `rd` |
| `remu rd, rs1, rs2`   | remainder (unsigned) of `rs1` divided by `rs2` and store into `rd` |

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
 
| Instruction              | Description |
| ------------------------ | ----------- |
| `lr.w rd, rs1`           | load (reserved) 32-bit value from addr in `rs1` into `rd` and register a reservation set |
| `sc.w rd, rs1, rs2`      | store (conditional) 32-bit value from `rs2` into addr in `rs1` and write status to `rd` |
| `amoswap.w rd, rs1, rs2` | atomically load value from addr in `rs1` into `rd`, SWAP with value in `rs2`, store back to addr `rs1` |
| `amoadd.w rd, rs1, rs2`  | atomically load value from addr in `rs1` into `rd`, ADD to value in `rs2`, store back to addr `rs1` |
| `amoxor.w rd, rs1, rs2`  | atomically load value from addr in `rs1` into `rd`, XOR with value in `rs2`, store back to addr `rs1` |
| `amoand.w rd, rs1, rs2`  | atomically load value from addr in `rs1` into `rd`, AND with value in `rs2`, store back to addr `rs1` |
| `amoor.w rd, rs1, rs2`   | atomically load value from addr in `rs1` into `rd`, OR with value in `rs2`, store back to addr `rs1` |
| `amomin.w rd, rs1, rs2`  | atomically load value from addr in `rs1` into `rd`, MIN with value in `rs2`, store back to addr `rs1` |
| `amomax.w rd, rs1, rs2`  | atomically load value from addr in `rs1` into `rd`, MAX with value in `rs2`, store back to addr `rs1` |
| `amominu.w rd, rs1, rs2` | atomically load value from addr in `rs1` into `rd`, MIN (unsigned) with value in `rs2`, store back to addr `rs1` |
| `amomaxu.w rd, rs1, rs2` | atomically load value from addr in `rs1` into `rd`, MAX (unsigned) with value in `rs2`, store back to addr `rs1` |

### RV32C Standard Extension
| Instruction                | Description |
| -------------------------- | ----------- |
| `c.addi4spn rd', nzuimm`   | add 8-bit MO4 `nzuimm` to `x2/sp` and store into `rd'` |
| `c.lw rd', rs1', uimm`     | load 32-bit value from addr in `rs1'` plus 5-bit MO4 `uimm` into `rd'` |
| `c.sw rs1', rs2', uimm`    | store 32-bit value from `rs2'` into addr in `rs1'` plus 5-bit MO4 `uimm` |
| `c.nop`                    | no operation |
| `c.addi rd/rs1!=0, nzimm`  | add 6-bit `imm` to `rd/rs1` and store into `rd/rs1` |
| `c.jal imm`                | jump offset 11-bit MO2 `imm` and store return addr into `x1/ra` |
| `c.li rd!=0, imm`          | load 6-bit `imm` into `rd`, sign extend upper bits |
| `c.addi16sp nzimm`         | add 6-bit MO16 `nzimm` to `x2/sp` and store into `x2/sp` |
| `c.lui rd!={0,2}, nzimm`   | load 6-bit `imm` into middle bits [17:12] of `rd`, sign extend upper bits, clear lower bits |
| `c.srli rd'/rs1', nzuimm`  | shift `rd'/rs1'` right by `nzuimm` bits and store into `rd'/rs1'` (shift in zeroes) |
| `c.srai rd'/rs1', nzuimm`  | shift `rd'/rs1'` right by `nzuimm` bits and store into `rd'/rs1'` (shift in sign bit) |
| `c.andi rd'/rs1', imm`     | bitwise AND 6-bit `imm` with `rd'/rs1'` and store into `rd'/rs1'` |
| `c.sub rd'/rs1', rs2'`     | subtract `rs2'` from `rd'/rs1'` and store into `rd'/rs1'` |
| `c.xor rd'/rs1', rs2'`     | bitwise XOR `rs2'` with `rd'/rs1'` and store into `rd'/rs1'` |
| `c.or rd'/rs1', rs2'`      | bitwise OR `rs2'` with `rd'/rs1'` and store into `rd'/rs1'` |
| `c.and rd'/rs1', rs2'`     | bitwise AND `rs2'` with `rd'/rs1'` and store into `rd'/rs1'` |
| `c.j imm`                  | jump offset 11-bit MO2 `imm` |
| `c.beqz rs1', imm`         | jump offset 8-bit MO2 `imm` if `rs1'` is equal to zero |
| `c.bnez rs1', imm`         | jump offset 8-bit MO2 `imm` if `rs1'` is not equal to zero |
| `c.slli rd/rs1!=0, nziumm` | shift `rd/rs1` left by `nzuimm` bits and store into `rd/rs1` |
| `c.lwsp rd!=0, uimm`       | load 32-bit value from addr in `x2/sp` plus 6-bit MO4 `uimm` into `rd` |
| `c.jr rs1!=0`              | jump to addr in `rs1` |
| `c.mv rd!=0, rs2!=0`       | copy value from `rs2` into `rd` |
| `c.ebreak`                 | return control to a debugging environment |
| `c.jalr rs1!=0`            | jump to addr in `rs1` and store return addr into `x1/ra` |
| `c.add rd/rs1!=0, rs2!=0`  | add `rs2` to `rd/rs1` and store into `rd/rs1` |
| `c.swsp rs2, uimm`         | store 32-bit value from `rs2` into addr in `x2/sp` plus 6-bit MO4 `uimm` |
