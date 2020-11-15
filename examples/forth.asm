ROM_BASE_ADDR = 0x08000000
RAM_BASE_ADDR = 0x20000000

#       Register Assignment
# |------------------------------|
# | reg | name |   description   |
# |------------------------------|
# |  x0 | zero | always 0        |
# |  x1 |  ra  | return address  |
# |  x2 |  sp  | DSP             |
# |  x3 |  gp  | IP              |
# |  x4 |  tp  | RSP             |
# |  x5 |  t0  | scratch         |
# |  x6 |  t1  | scratch         |
# |  x7 |  t2  | scratch         |
# |  x8 |  s0  | W               |
# |  x9 |  s1  | STATE           |
# | x10 |  a0  | token address   |
# | x11 |  a1  | token length    |
# | x12 |  a2  | lookup address  |
# | x13 |  a3  | align arg / ret |
# | x14 |  a4  | pad arg / ret   |
# | x15 |  a5  | getc / putc     |
# | x16 |  a6  | <unused>        |
# | x17 |  a7  | <unused>        |
# | x18 |  s2  | TIB             |
# | x19 |  s3  | TBUF            |
# | x20 |  s4  | TLEN            |
# | x21 |  s5  | TPOS            |
# | x22 |  s6  | HERE            |
# | x23 |  s7  | LATEST          |
# | x24 |  s8  | <unused>        |
# | x25 |  s9  | <unused>        |
# | x26 |  s10 | <unused>        |
# | x27 |  s11 | <unused>        |
# | x28 |  t3  | scratch         |
# | x29 |  t4  | scratch         |
# | x30 |  t5  | scratch         |
# | x31 |  t6  | scratch         |
# |------------------------------|

# "The Classical Forth Registers"
W = 's0'  # working register
IP = 'gp'  # interpreter pointer
DSP = 'sp'  # data stack pointer
RSP = 'tp'  # return stack pointer

#                Variables
# |----------------------------------------|
# |  name  |          description          |
# |----------------------------------------|
# | STATE  | 0 = execute, 1 = compile      |
# | TIB    | text input buffer addr        |
# | TBUF   | text buffer addr              |
# | TLEN   | text buffer length            |
# | TPOS   | text buffer current position  |
# | HERE   | next dict entry addr          |
# | LATEST | latest dict entry addr        |
# |----------------------------------------|

# Variable registers
STATE = 's1'
TIB = 's2'
TBUF = 's3'
TLEN = 's4'
TPOS = 's5'
HERE = 's6'
LATEST = 's7'

#  16KB      Memory Map
# 0x0000 |----------------|
#        |                |
#        |  Interpreter   |
#        |       +        | 7K
#        |   Dictionary   |
#        |                |
# 0x1c00 |----------------|
#        |      TIB       | 1K
# 0x2000 |----------------|
#        |                |
#        |   Data Stack   | 4K
#        |                |
# 0x3000 |----------------|
#        |                |
#        |  Return Stack  | 4K
#        |                |
# 0x3FFF |----------------|

INTERPRETER_BASE = 0x0000
TIB_BASE = 0x1c00
DATA_STACK_BASE = 0x2000
RETURN_STACK_BASE = 0x3000

INTERPRETER_SIZE = 0x1c00  # 7K
TIB_SIZE = 0x0400  # 1K
DATA_STACK_SIZE = 0x1000  # 4K
RETURN_STACK_SIZE = 0x1000  # 4K

F_IMMEDIATE = 0b10000000
F_HIDDEN    = 0b01000000
F_LENGTH    = 0b00111111

copy:
    # setup copy src
    lui t0 %hi(ROM_BASE_ADDR)
    addi t0 t0 %lo(ROM_BASE_ADDR)
    # setup copy dest
    lui t1 %hi(RAM_BASE_ADDR)
    addi t1 t1 %lo(RAM_BASE_ADDR)
    # setup copy count
    addi t0 zero %position(here, 0)
copy_loop:
    beq t2 zero copy_done
    lw t3 t0 0  # [src] -> t3
    sw t1 t3 0  # [dest] <- t3
    addi t0 t0 4  # src += 4
    addi t1 t1 4  # dest += 4
    addi t2 t2 -4  # count -= 4
    jal zero copy_loop
copy_done:
    # t0 = addr of start
    # TODO: allow %position / %offset in %hi / %lo
    # lui t0 %hi(%position(start, RAM_BASE_ADDR))
    # addi t0 t0 %lo(%position(start, RAM_BASE_ADDR))
    lui t0 %hi(RAM_BASE_ADDR)
    addi t0 t0 %lo(RAM_BASE_ADDR)
    addi t0 t0 start
    # jump to start
    jalr zero t0 0

# Procedure: token
# Usage: p.JAL('ra', 'token')
# Ret: a0 = addr of word name (0 if not found)
# Ret: a1 = length of word name (0 if not found)
token:
    addi t0 zero 33  # put whitespace threshold value into t0
token_skip_whitespace:
    add t1 TBUF TPOS  # point t1 at current char
    lbu t2 t1 0  # load current char into t2
    bge t2 t0 token_scan  # check if non-whitespace char is found
    addi TPOS TPOS 1  # inc TPOS
    bge TPOS TLEN token_not_found  # no token if TPOS >= TLEN
    jal zero token_skip_whitespace  # else check again
token_scan:
    addi t1 TPOS 0  # put current TPOS value into t1
token_scan_loop:
    add t2 TBUF t1  # point t2 at next char
    lbu t3 t2 0  # load next char into t3
    blt t3 t0 token_found  # check for whitespace
    addi t1 t1 1  # increment offset
    bge t1 TLEN token_not_found  # no token if t1 >= TLEN
    jal zero token_scan_loop  # scan the next char
token_found:
    add a0 TBUF TPOS  # a0 = addr of word
    sub a1 t1 TPOS  # a1 = len of word
    addi TPOS t1 0  # update TPOS
    jalr zero ra 0  # return
token_not_found:
    addi a0 zero 0  # a0 = 0
    addi a1 zero 0  # a1 = 0
    addi TPOS t1 0  # update TPOS
    jalr zero ra 0  # return

# Procedure: lookup
# Usage: p.JAL('ra', 'lookup')
# Arg: a0 = addr of word name
# Arg: a1 = length of word name
# Ret: a2 = addr of found word (0 if not found)
lookup:
lookup_body:
lookup_next:
lookup_not_found:
lookup_strcmp:
lookup_strcmp_body:
lookup_strcmp_next:
lookup_found:

# Procedure: align
# Usage: p.JAL('ra', 'align')
# Arg: a3 = value to be aligned
# Ret: a3 = value after alignment
align:
align_done:

# Procedure: pad
# Usage: p.JAL('ra', 'pad')
# Arg: a4 = addr to be padded
# Ret: a4 = addr after padding
pad:
pad_done:

# Procedure: getc
# Usage: p.JAL('ra', 'getc')
# Ret: a5 = character received from serial
getc:
getc_wait:

# Procedure: putc
# Usage: p.JAL('ra', 'putc')
# Arg: a5 = character to send over serial
putc:
putc_wait:

# !!! main program starts here !!!

# Init serial comm via USART0:
# 1. RCU APB2 enable GPIOA (1 << 2)
# 2. RCU APB2 enable USART0 (1 << 14)
# 3. GPIOA config pin 9 (ctl = OUT_ALT_PUSH_PULL, mode = OUT_50MHZ)
#   Pin 9 offset = ((PIN - 8) * 4) = 4
# 4. GPIOA config pin 10 (ctl = IN_FLOATING, mode = IN)
#   Pin 10 offset = ((PIN - 8) * 4) = 8
# 5. USART0 config baud (CLOCK // BAUD = 69)
# 6. USART0 enable RX (1 << 2)
# 7. USART0 enable TX (1 << 3)
# 7. USART0 enable USART (1 << 13)
start:

here:
