# Example program to showcase assembler syntax
# This example doesn't actually do anything useful!

# constants
FOO = 42
BAR = FOO * 2
ADDR = 0x20000000

# basic labels, jumping, and branching
start:
    addi t0, zero, BAR
    jal zero, end
middle:
    beq t0, zero, main
    addi t0, t0, -1
end:
    jal zero, %offset(middle)

# string literals
string "hello"
string "world"
string "hello world"
string "hello   world"  # same as above, whitespace gets compressed by the lexer

# bytes literals
bytes 1 2 0x03 0b100 5 0x06 0b111 8

# packed values
pack <B, 0
pack <B, 255
pack <I, ADDR
pack <f, 3.14159

# align to 4-byte (32-bit) boundary
align 4

main:
    # without nestable exprs under hi / lo
    lui t0, %hi(ADDR)
    addi t0, t0, %lo(ADDR)
    addi t0, t0, main

    # with nestable exprs under hi / lo
    lui t0, %hi(%position(main, ADDR))
    addi t0, t0, %lo(%position(main, ADDR))
