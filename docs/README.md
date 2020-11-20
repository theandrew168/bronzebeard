# Bronzebeard Documentation
This document describes the assembly language dialect that Bronzebeard understands.

## General
RISC-V assembly programs are written as a plain text files.
The file extension is mostly arbitrary, but I recommend using `.txt` or `.asm`.
Using `.txt` will make for better default behavior on Windows systems.
An assembly program is a linear sequence of "items".
Items can be many things: labels, instructions, literal bytes and strings, etc.
Single-line comments can be intermixed with the source code by using the `#` character.

Here is a basic example containing a single comment and a single instruction:
```
# load the value 12 into register x1
addi x1, zero, 12
```

Here is another example that utilizes a label in order to create an infinite loop:
```
# loop forever!
loop:
    jal zero, loop
```

## Modifiers
### %position / %offset
### %hi / %lo

## Registers
The RISC-V ISA specifies 32 general purpose registers.
Each register is cable of a holding a single 32-bit value (or 64 bits on a 64-bit system).
Register 0 is the only special case: it always holds the value zero no matter what gets written to it.

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
| `12-17` | `x12-17` | `a2-7`  | Funciton arguments |
| `18-27` | `x18-27` | `s2-11` | Saved registers |
| `28-31` | `x28-31` | `t3-6`  | Temporary registers |

## Instructions
This table provides summaries for the baseline RISC-V instructions.
Full specifications be found on the RISC-V [website](https://riscv.org/technical/specifications/).

| Name    | Parameters    | Description |
| ------- | ------------- | ----------- |
| `lui`   | rd, imm       | TODO        |
| `auipc` | rd, imm       | TODO        |
| `jal`   | rd, imm       | TODO        |
| `jalr`  | rd, rs1, imm  | TODO        |
| `beq`   | rs1, rs2, imm | TODO        |
| `bne`   | rs1, rs2, imm | TODO        |
| `blt`   | rs1, rs2, imm | TODO        |
| `bge`   | rs1, rs2, imm | TODO        |
| `bltu`  | rs1, rs2, imm | TODO        |
| `bgeu`  | rs1, rs2, imm | TODO        |
| `lb`    | rd, rs1, imm  | TODO        |
| `lh`    | rd, rs1, imm  | TODO        |
| `lw`    | rd, rs1, imm  | TODO        |
| `lbu`   | rd, rs1, imm  | TODO        |
| `lhu`   | rd, rs1, imm  | TODO        |
| `sb`    | rs1, rs2, imm | TODO        |
| `sh`    | rs1, rs2, imm | TODO        |
| `sw`    | rs1, rs2, imm | TODO        |
| `addi`  | rd, rs1, imm  | TODO        |
| `slti`  | rd, rs1, imm  | TODO        |
| `sltiu` | rd, rs1, imm  | TODO        |
| `xori`  | rd, rs1, imm  | TODO        |
| `ori`   | rd, rs1, imm  | TODO        |
| `andi`  | rd, rs1, imm  | TODO        |
| `slli`  | rd, rs1, bits | TODO        |
| `srli`  | rd, rs1, bits | TODO        |
| `srai`  | rd, rs1, bits | TODO        |
| `add`   | rd, rs1, rs2  | TODO        |
| `sub`   | rd, rs1, rs2  | TODO        |
| `sll`   | rd, rs1, rs2  | TODO        |
| `slt`   | rd, rs1, rs2  | TODO        |
| `sltu`  | rd, rs1, rs2  | TODO        |
| `xor`   | rd, rs1, rs2  | TODO        |
| `srl`   | rd, rs1, rs2  | TODO        |
| `sra`   | rd, rs1, rs2  | TODO        |
| `or`    | rd, rs1, rs2  | TODO        |
| `and`   | rd, rs1, rs2  | TODO        |

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

### One's Complement Negation
This pattern flips all 1s to 0s and 0s to 1s for register `x1`.
```
xori x1, x1, -1
```

### No Operation
This pattern intentionally does nothing.
```
addi x0, x0, 0
```
