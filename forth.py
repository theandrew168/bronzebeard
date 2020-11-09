from contextlib import contextmanager
import struct

import asm

# Types of Immediate values (one of Literal / Position / Location / Address):
# An Immediate can be resolved to a Number given a map[string]int of labels (can be nil, too)
# Resolution wouldn't happen until subsequent passes of the assembler
# Usually I just want the number (imm args to insts) but sometimes I want bytes
#   kinda like a blob. Usually a 32-bit LE encoding of a number (4 blob bytes).
#
# 1. Literal numeric value (needs no resolution)
#       Number -> Number            0x42
# 2. PC location (anytime I dig into p.location manually)
#       PC -> Number                Position()  # implicit PC
# 3. Label location (anytime I dig into p.labels manually)
#       String -> Number            PositionFrom('foo')
#                                   PositionAt('foo')
#                                   AbsolutePosition(0, 'foo')  # args: base, label
#                                   Position(0, 'foo')
#                                   Location(0, 'foo')
# 4. Relative to PC (jumps / branches, forward and backward)
#       String + PC -> Number       Offset('bar')  # implicit PC
#                                   RelativePosition('bar')
# 5. Relative to base address (absolute locations in memory: TIB, DSP, RSP, etc)
#       String + Number -> Number   OffsetFrom('baz', RAM_BASE_ADDR)
#                                   PositionRelativeTo('baz', RAM_BASE_ADDR)
#                                   AbsolutePosition(RAM_BASE_ADDR, 'baz')
# 6. Relative to other position (forth word links)
#       String + String -> Number   OffsetBetween('foo', 'bar')

# Based heavily on "sectorforth" and "Moving Forth":
# https://github.com/cesarblum/sectorforth
# https://www.bradrodriguez.com/papers/moving1.htm

# Bronzebeard details
FORTH_SIZE = 16 * 1024  # 16K
USART_BAUD = 115200

# GD32VF103[CBT6]: Longan Nano, Wio Lite
ROM_BASE_ADDR = 0x08000000
ROM_SIZE = 128 * 1024  # 128K
RAM_BASE_ADDR = 0x20000000
RAM_SIZE = 32 * 1024  # 32K
DISK_BASE_ADDR = ROM_BASE_ADDR + FORTH_SIZE
DISK_SIZE = ROM_SIZE - FORTH_SIZE
HEAP_BASE_ADDR = RAM_BASE_ADDR + FORTH_SIZE
HEAP_SIZE = RAM_SIZE - FORTH_SIZE
CLOCK_FREQ = 8000000
MTIME_FREQ = 2000000

# FE310-G002: HiFive1 Rev B
#ROM_BASE_ADDR  = 0x20000000  # 4M
#ROM_BASE_ADDR += 0x00010000  # first 64K of ROM is taken by the bootloader
#RAM_BASE_ADDR  = 0x80000000  # 16K

# PicoRV32/PicoSoC: iCEBreaker (Lattice iCE40UP5K FPGA)
#ROM_BASE_ADDR = 0x00100000  # 16M
#RAM_BASE_ADDR = 0x00000000  # 128K

# PicoRV32/PicoSoC: TinyFPGA BX (Lattice iCE40LP8K FPGA)
#ROM_BASE_ADDR = 0x00050000  # 1M
#RAM_BASE_ADDR = 0x00000000  # 16K

# Longan Nano Details:
RCU_BASE_ADDR = 0x40021000

RCU_CTL_OFFSET = 0x00
RCU_CLK_CONFIG0_OFFSET = 0x04
RCU_CLK_INTERRUPT_OFFSET = 0x08
RCU_APB2_RESET_OFFSET = 0x0c
RCU_APB1_RESET_OFFSET = 0x10
RCU_AHB_ENABLE_OFFSET = 0x14
RCU_APB2_ENABLE_OFFSET = 0x18
RCU_APB1_ENABLE_OFFSET = 0x1c
RCU_BACKUP_DOMAIN_CTRL_OFFSET = 0x20
RCU_RESET_SRC_CLK_OFFSET = 0x24
RCU_AHB_RESET_OFFSET = 0x28
RCU_CLK_CONFIG1_OFFSET = 0x2c
RCU_DEEP_SLEEP_VOLTAGE_OFFSET = 0x34

GPIO_BASE_ADDR_A = 0x40010800
GPIO_BASE_ADDR_B = 0x40010c00
GPIO_BASE_ADDR_C = 0x40011000
GPIO_BASE_ADDR_D = 0x40011400
GPIO_BASE_ADDR_E = 0x40011800

GPIO_CTL0_OFFSET = 0x00
GPIO_CTL1_OFFSET = 0x04
GPIO_IN_STATUS_OFFSET = 0x08
GPIO_OUT_CTRL_OFFSET = 0x0c
GPIO_BIT_OPERATE_OFFSET = 0x10
GPIO_BIT_CLEAR_OFFSET = 0x14
GPIO_LOCK_OFFSET = 0x18

GPIO_MODE_IN = 0b00
GPIO_MODE_OUT_10MHZ = 0b01
GPIO_MODE_OUT_2MHZ = 0b10
GPIO_MODE_OUT_50MHZ = 0b11

GPIO_CTL_IN_ANALOG = 0b00
GPIO_CTL_IN_FLOATING = 0b01
GPIO_CTL_IN_PULL = 0b10
GPIO_CTL_IN_RESERVED = 0b11

GPIO_CTL_OUT_PUSH_PULL = 0b00
GPIO_CTL_OUT_OPEN_DRAIN = 0b01
GPIO_CTL_OUT_ALT_PUSH_PULL = 0b10
GPIO_CTL_OUT_ALT_OPEN_DRAIN = 0b11

LED_R_GPIO = GPIO_BASE_ADDR_C
LED_R_PIN = 13  # GPIO_CTL1
LED_G_GPIO = GPIO_BASE_ADDR_A
LED_G_PIN = 1  # GPIO_CTL0
LED_B_GPIO = GPIO_BASE_ADDR_A
LED_B_PIN = 2  # GPIO_CTL0

USART_BASE_ADDR_0 = 0x40013800

USART_STAT_OFFSET = 0x00
USART_DATA_OFFSET = 0x04
USART_BAUD_OFFSET = 0x08
USART_CTL0_OFFSET = 0x0c
USART_CTL1_OFFSET = 0x10
USART_CTL2_OFFSET = 0x14
USART_GP_OFFSET = 0x18


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

@contextmanager
def defword(p, name, flags=0):
    # hack to impl a static function var (alternative is using the 'global' keyword)
    if not hasattr(defword, 'link'): defword.link = 0

    if len(name) > 0x3f:
        raise ValueError('Word name is longer than 0x3f (63 chars): {}'.format(name))

    # create a label for the word header (word name prefixed with 'header_')
    header_label = 'header_' + name
    p.LABEL(header_label)

    # write the link to previous word and update link to point to this word
    #   OffsetFrom(RAM_BASE_ADDR, header_label)
    #   AbsoluteAddress(RAM_BASE_ADDR, header_label)
    p.BLOB(struct.pack('<I', defword.link))
    defword.link = RAM_BASE_ADDR + p.labels[header_label]

    # write word flags + length
    p.BLOB(struct.pack('<B', flags | len(name)))

    # write word name and align to multiple of 4 bytes
    p.BLOB(name.encode())
    p.ALIGN()

    # create helper label for code field
    word_label = 'word_' + name
    p.LABEL(word_label)

    # write code word (addr to raw machine code that will follow)
    #   OffsetFrom(RAM_BASE_ADDR, body_label)
    addr = RAM_BASE_ADDR + p.location + 4
    p.BLOB(struct.pack('<I', addr))

    # create helper label for word's actual code / address list
    #   used by COLON for writing addr of ENTER machine code
    body_label = 'body_' + name
    p.LABEL(body_label)

    # context manager aesthetics hack
    yield


p = asm.Program()

# t0 = src, t1 = dest, t2 = count
with p.LABEL('copy'):
    # setup copy src (ROM_BASE_ADDR)
    p.LUI('t0', p.HI(ROM_BASE_ADDR))
    p.ADDI('t0', 't0', p.LO(ROM_BASE_ADDR))
    # setup copy dest (RAM_BASE_ADDR)
    p.LUI('t1', p.HI(RAM_BASE_ADDR))
    p.ADDI('t1', 't1', p.LO(RAM_BASE_ADDR))
    # setup copy count (everything up to the "here" label)
    p.ADDI('t2', 'zero', 'here')  # RelativeOffset('here')
with p.LABEL('copy_loop'):
    p.BEQ('t2', 'zero', 'copy_done')
    p.LW('t3', 't0', 0)  # [src] -> t3
    p.SW('t1', 't3', 0)  # t3 -> [dest]
    p.ADDI('t0', 't0', 4)  # src += 4
    p.ADDI('t1', 't1', 4)  # dest += 4
    p.ADDI('t2', 't2', -4)  # count -= 4
    p.JAL('zero', 'copy_loop')
with p.LABEL('copy_done'):
    # jump to RAM:start
    #   PositionFrom('start', RAM_BASE_ADDR)
    p.LUI('t0', p.HI(RAM_BASE_ADDR))
    p.ADDI('t0', 't0', p.LO(RAM_BASE_ADDR))
    p.ADDI('t0', 't0', 'start')
    p.JALR('zero', 't0', 0)

# Procedure: token
# Usage: p.JAL('ra', 'token')
# Ret: a0 = addr of word name (0 if not found)
# Ret: a1 = length of word name (0 if not found)
# TODO: Make TBUF / TLEN / TPOS args of some sort?
with p.LABEL('token'):
    p.ADDI('t0', 'zero', 33)  # put whitespace threshold value into t0
with p.LABEL('token_skip_whitespace'):
    p.ADD('t1', TBUF, TPOS)  # point t1 at current char
    p.LBU('t2', 't1', 0)  # load current char into t2
    p.BGE('t2', 't0', 'token_scan')  # check if done skipping whitespace
    p.ADDI(TPOS, TPOS, 1)  # inc TPOS
    p.BGE(TPOS, TLEN, 'token_not_found')  # no token if TPOS exceeds TLEN
    p.JAL('zero', 'token_skip_whitespace')  # check again
with p.LABEL('token_scan'):
    p.ADDI('t1', TPOS, 0)  # put current TPOS value into t1
with p.LABEL('token_scan_loop'):
    p.ADD('t2', TBUF, 't1')  # point t2 at next char
    p.LBU('t3', 't2', 0)  # load next char into t3
    p.BLT('t3', 't0', 'token_found')  # check for whitespace
    p.ADDI('t1', 't1', 1)  # increment offset
    p.BGE('t1', TLEN, 'token_not_found')  # no token if t1 exceeds TLEN
    p.JAL('zero', 'token_scan_loop')  # scan the next char
with p.LABEL('token_found'):
    p.ADD('a0', TBUF, TPOS)  # a0 = address of word
    p.SUB('a1', 't1', TPOS)  # a1 = length of word
    p.ADDI(TPOS, 't1', 0)  # update TPOS
    p.JALR('zero', 'ra', 0)  # return
with p.LABEL('token_not_found'):
    p.ADDI('a0', 'zero', 0)  # a0 = 0
    p.ADDI('a1', 'zero', 0)  # a1 = 0
    p.ADDI(TPOS, 't1', 0)  # update TPOS
    p.JALR('zero', 'ra', 0)  # return

# Procedure: lookup
# Usage: p.JAL('ra', 'lookup')
# Arg: a0 = addr of word name
# Arg: a1 = length of word name
# Ret: a2 = addr of found word (0 if not found)
with p.LABEL('lookup'):
    p.ADDI('t0', LATEST, 0)  # copy addr of latest word into t0
with p.LABEL('lookup_body'):
    p.LW('t1', 't0', 0)  # load link of current word into t1
    p.LBU('t2', 't0', 4)  # load flags / len of current word into t2
    p.ANDI('t2', 't2', F_LENGTH)  # TODO (check hidden) wipe out flags for now leaving word length
    p.BEQ('a1', 't2', 'lookup_strcmp')  # start strcmp if len matches
with p.LABEL('lookup_next'):
    p.BEQ('t1', 'zero', 'lookup_not_found')  # if link is zero then the word isn't found
    p.ADDI('t0', 't1', 0)  # point t0 at the next word (move link addr into t0)
    p.JAL('zero', 'lookup_body')  # continue the search
with p.LABEL('lookup_not_found'):
    p.ADDI('a2', 'zero', 0)  # a2 = 0
    p.JALR('zero', 'ra', 0)  # return
with p.LABEL('lookup_strcmp'):
    p.ADDI('t3', 'a0', 0)  # t3 points at name in TIB string
    p.ADDI('t4', 't0', 5)  # t4 points at name in word dict
with p.LABEL('lookup_strcmp_body'):
    p.LBU('t5', 't3', 0)  # load TIB char into t5
    p.LBU('t6', 't4', 0)  # load dict char into t6
    p.BNE('t5', 't6', 'lookup_next')  # try next word if current chars don't match
with p.LABEL('lookup_strcmp_next'):
    p.ADDI('t2', 't2', -1)  # dec len by 1
    p.BEQ('t2', 'zero', 'lookup_found')  # if all chars have been checked, its a match!
    p.ADDI('t3', 't3', 1)  # inc TIB ptr
    p.ADDI('t4', 't4', 1)  # inc word dict ptr
    p.JAL('zero', 'lookup_strcmp_body')  # check next char
with p.LABEL('lookup_found'):
    p.ADDI('a2', 't0', 0)  # a2 = addr of found word
    p.JALR('zero', 'ra', 0)  # return

# Procedure: align
# Usage: p.JAL('ra', 'align')
# Arg: a3 = value to be aligned
# Ret: a3 = value after alignment
with p.LABEL('align'):
    p.ANDI('t0', 'a3', 0b11)  # t0 = bottom 2 bits of a3
    p.BEQ('t0', 'zero', 'align_done')  # if they are zero, a3 is aligned
    p.ADDI('a3', 'a3', 1)  # else inc a3 by 1
    p.JAL('zero', 'align')  # and loop again
with p.LABEL('align_done'):
    p.JALR('zero', 'ra', 0)  # return

# Procedure: pad
# Usage: p.JAL('ra', 'pad')
# Arg: a4 = addr to be padded
# Ret: a4 = addr after padding
with p.LABEL('pad'):
    p.ANDI('t0', 'a4', 0b11)  # t0 = bottom 2 bits of a3
    p.BEQ('t0', 'zero', 'pad_done')  # if they are zero, a4 is aligned
    p.SB('a4', 'zero', 0)  # write a 0 to addr at a4
    p.ADDI('a4', 'a4', 1)  # inc a4 by 1
    p.JAL('zero', 'pad')  # loop again
with p.LABEL('pad_done'):
    p.JALR('zero', 'ra', 0)  # return

# Procedure: getc
# Usage: p.JAL('ra', 'getc')
# Ret: a5 = character received from serial
with p.LABEL('getc'):
    # t1 = stat, t2 = data
    p.LUI('t0', p.HI(USART_BASE_ADDR_0))
    p.ADDI('t0', 't0', p.LO(USART_BASE_ADDR_0))
    p.ADDI('t1', 't0', USART_STAT_OFFSET)
    p.ADDI('t2', 't0', USART_DATA_OFFSET)
with p.LABEL('getc_wait'):
    p.LW('t4', 't1', 0)  # load stat into t4
    p.ANDI('t4', 't4', 1 << 5)  # isolate RBNE bit
    p.BEQ('t4', 'zero', 'getc_wait')  # keep looping until a char comes in
    p.LW('a5', 't2', 0)  # load char into a5
    p.JALR('zero', 'ra', 0)  # return

# Procedure: putc
# Usage: p.JAL('ra', 'putc')
# Arg: a5 = character to send over serial
with p.LABEL('putc'):
    # t1 = stat, t2 = data
    p.LUI('t0', p.HI(USART_BASE_ADDR_0))
    p.ADDI('t0', 't0', p.LO(USART_BASE_ADDR_0))
    p.ADDI('t1', 't0', USART_STAT_OFFSET)
    p.ADDI('t2', 't0', USART_DATA_OFFSET)
    p.SW('t2', 'a5', 0)  # write char from a5
with p.LABEL('putc_wait'):
    p.LW('t4', 't1', 0)  # load stat into t4
    p.ANDI('t4', 't4', 1 << 7)  # isolate TBE bit
    p.BEQ('t4', 'zero', 'putc_wait')  # keep looping until char gets sent
    p.JALR('zero', 'ra', 0)  # return

# Main program starts here!
with p.LABEL('start'):
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

    # setup addr and load current APB2 config into t1
    p.LUI('t0', p.HI(RCU_BASE_ADDR))
    p.ADDI('t0', 't0', p.LO(RCU_BASE_ADDR))
    p.ADDI('t0', 't0', RCU_APB2_ENABLE_OFFSET)
    p.LW('t1', 't0', 0)

    # setup enable bit for GPIOA
    p.ADDI('t2', 'zero', 1)
    p.SLLI('t2', 't2', 2)
    p.OR('t1', 't1', 't2')

    # setup enable bit for GPIOC
    p.ADDI('t2', 'zero', 1)
    p.SLLI('t2', 't2', 4)
    p.OR('t1', 't1', 't2')

    # setup enable bit for USART0
    p.ADDI('t2', 'zero', 1)
    p.SLLI('t2', 't2', 14)
    p.OR('t1', 't1', 't2')

    # store APB2 config
    p.SW('t0', 't1', 0)

    # setup addr and load current GPIOA config into t1
    p.LUI('t0', p.HI(GPIO_BASE_ADDR_A))
    p.ADDI('t0', 't0', p.LO(GPIO_BASE_ADDR_A))
    p.ADDI('t0', 't0', GPIO_CTL1_OFFSET)
    p.LW('t1', 't0', 0)

    # clear existing config (pin 9)
    p.ADDI('t2', 'zero', 0b1111)
    p.SLLI('t2', 't2', 4)
    p.XORI('t2', 't2', -1)
    p.AND('t1', 't1', 't2')

    # setup config bits (pin 9)
    p.ADDI('t2', 'zero', (GPIO_CTL_OUT_ALT_PUSH_PULL << 2) | GPIO_MODE_OUT_50MHZ)
    p.SLLI('t2', 't2', 4)
    p.OR('t1', 't1', 't2')

    # clear existing config (pin 10)
    p.ADDI('t2', 'zero', 0b1111)
    p.SLLI('t2', 't2', 8)
    p.XORI('t2', 't2', -1)
    p.AND('t1', 't1', 't2')

    # setup config bits (pin 10)
    p.ADDI('t2', 'zero', (GPIO_CTL_IN_FLOATING << 2) | GPIO_MODE_IN)
    p.SLLI('t2', 't2', 8)
    p.OR('t1', 't1', 't2')

    # store GPIOA config
    p.SW('t0', 't1', 0)

    # setup addr for USART0
    p.LUI('t0', p.HI(USART_BASE_ADDR_0))
    p.ADDI('t0', 't0', p.LO(USART_BASE_ADDR_0))

    # set baud rate
    p.ADDI('t1', 't0', USART_BAUD_OFFSET)
    p.ADDI('t2', 'zero', CLOCK_FREQ // USART_BAUD)
    p.SW('t1', 't2', 0)

    # load current USART0 config into t1
    p.ADDI('t0', 't0', USART_CTL0_OFFSET)
    p.LW('t1', 't0', 0)

    # setup enable bit for RX
    p.ADDI('t2', 'zero', 1)
    p.SLLI('t2', 't2', 2)
    p.OR('t1', 't1', 't2')

    # setup enable bit for TX
    p.ADDI('t2', 'zero', 1)
    p.SLLI('t2', 't2', 3)
    p.OR('t1', 't1', 't2')

    # setup enable bit for USART
    p.ADDI('t2', 'zero', 1)
    p.SLLI('t2', 't2', 13)
    p.OR('t1', 't1', 't2')

    # store USART0 config
    p.SW('t0', 't1', 0)

    # set HERE var to "here" location
    #   PositionFrom('here', RAM_BASE_ADDR)
    p.LUI(HERE, p.HI(RAM_BASE_ADDR))
    p.ADDI(HERE, HERE, p.LO(RAM_BASE_ADDR))
    p.ADDI(HERE, HERE, 'here')

    # set LATEST var to "latest" location
    #   PositionFrom('latest', RAM_BASE_ADDR)
    p.LUI(LATEST, p.HI(RAM_BASE_ADDR))
    p.ADDI(LATEST, LATEST, p.LO(RAM_BASE_ADDR))
    p.ADDI(LATEST, LATEST, 'latest')

    p.JAL('zero', 'init')

with p.LABEL('error'):
    # print error indicator and fall through into reset
    p.ADDI('a5', 'zero', ord(' '))
    p.JAL('ra', 'putc')
    p.ADDI('a5', 'zero', ord('?'))
    p.JAL('ra', 'putc')
    p.ADDI('a5', 'zero', ord('\n'))
    p.JAL('ra', 'putc')

with p.LABEL('init'):
    # set working register to zero
    p.ADDI(W, 'zero', 0)

    # setup data stack pointer
    p.LUI(DSP, p.HI(RAM_BASE_ADDR + DATA_STACK_BASE))
    p.ADDI(DSP, DSP, p.LO(RAM_BASE_ADDR + DATA_STACK_BASE))

    # setup return stack pointer
    p.LUI(RSP, p.HI(RAM_BASE_ADDR + RETURN_STACK_BASE))
    p.ADDI(RSP, RSP, p.LO(RAM_BASE_ADDR + RETURN_STACK_BASE))

    # set STATE to zero
    p.ADDI(STATE, 'zero', 0)

    # set TIB var to TIB_BASE
    #   Number(RAM_BASE_ADDR + TIB_BASE)
    #   Literal(RAM_BASE_ADDR + TIB_BASE)
    #   Immediate(RAM_BASE_ADDR + TIB_BASE)
    p.LUI(TIB, p.HI(RAM_BASE_ADDR + TIB_BASE))
    p.ADDI(TIB, TIB, p.LO(RAM_BASE_ADDR + TIB_BASE))

p.JAL('zero', 'interpreter')

# print "ok" and fall through into interpreter
with p.LABEL('interpreter_ok'):
    p.ADDI('a5', 'zero', ord(' '))
    p.JAL('ra', 'putc')
    p.ADDI('a5', 'zero', ord('o'))
    p.JAL('ra', 'putc')
    p.ADDI('a5', 'zero', ord('k'))
    p.JAL('ra', 'putc')
    p.ADDI('a5', 'zero', ord('\n'))
    p.JAL('ra', 'putc')

# main interpreter loop
with p.LABEL('interpreter'):
    # fill TIB with zeroes
    p.LABEL('tib_clear')
    p.ADDI('t0', TIB, 0)  # t0 = addr
    p.ADDI('t1', 'zero', TIB_SIZE)  # t1 = TIB_SIZE (1024)
    p.LABEL('tib_clear_body')
    p.SB('t0', 'zero', 0)  # [t0] = 0
    p.LABEL('tib_clear_next')
    p.ADDI('t0', 't0', 1)  # t0 += 1
    p.ADDI('t1', 't1', -1)  # t1 -= 1
    p.BNE('t1', 'zero', 'tib_clear_body')  # keep looping til t1 == 0

    # set TBUF to TIB
    p.ADDI(TBUF, TIB, 0)

    # set TLEN to zero
    p.ADDI(TLEN, 'zero', 0)

    # set TPOS to zero
    p.ADDI(TPOS, 'zero', 0)

with p.LABEL('interpreter_repl'):
    p.JAL('ra', 'getc')  # read char into a5
    p.JAL('ra', 'putc')  # echo back
    p.ADDI('t0', 'zero', ord('\b'))  # load backspace char into t0
    p.BNE('a5', 't0', 'interpreter_repl_char')  # proceed normally if not a BS
    p.BEQ(TLEN, 'zero', 'interpreter_repl')  # skip BS if TLEN is zero
    p.ADDI(TLEN, TLEN, -1)  # reduce TLEN, effectively erasing a character
    p.JAL('zero', 'interpreter_repl')  # loop back to top of REPL
with p.LABEL('interpreter_repl_char'):
    p.ADD('t0', TBUF, TLEN)  # t0 = TBUF addr for this char
    p.SW('t0', 'a5', 0)  # write char into TBUF
    p.ADDI(TLEN, TLEN, 1)  # TLEN += 1
    p.ADDI('t0', 'zero', ord('\n'))  # t0 = newline char
    p.BEQ('a5', 't0', 'interpreter_interpret')  # interpret the input upon newline
    p.JAL('zero', 'interpreter_repl')  # else wait for more input

with p.LABEL('interpreter_interpret'):
    p.JAL('ra', 'token')  # call token procedure (a0 = addr, a1 = len)
    p.BEQ('a0', 'zero', 'interpreter_ok')  # loop back to repl if input is expended

    p.JAL('ra', 'lookup')  # call lookup procedure (a2 = addr)
    p.BEQ('a2', 'zero', 'error')  # error and reset if word isn't found

    # decide whether to compile or execute the word
    p.LB('t0', 'a2', 4)  # load word flags + len into t0
    p.ANDI('t0', 't0', F_IMMEDIATE)  # isolate immediate flag
    p.BNE('t0', 'zero', 'interpreter_execute')  # execute if word is immediate
    p.BEQ(STATE, 'zero', 'interpreter_execute')  # execute if STATE is zero
with p.LABEL('interpreter_compile'):
    # otherwise compile!
    p.ADDI('t0', 'a2', 5)  # set t0 = start of word name
    p.ADD('t0', 't0', 'a1')  # skip to end of word name
    p.ADDI('a3', 't0', 0)  # setup arg for align
    p.JAL('ra', 'align')  # align to start of code word (a3 = addr of code word)
    p.SW(HERE, 'a3', 0)  # write addr of code word to definition
    p.ADDI(HERE, HERE, 4)  # HERE += 4
    p.JAL('zero', 'interpreter_interpret')
with p.LABEL('interpreter_execute'):
    # set interpreter pointer to indirect addr back to interpreter loop
    # TODO: can't just pre-calc addr here because its a forward ref
    #   and I can't dig into p.labels yet. Fix in v3.
    #   PositionFrom('interpreter_addr_addr', RAM_BASE_ADDR)
    p.LUI(IP, p.HI(RAM_BASE_ADDR))
    p.ADDI(IP, IP, p.LO(RAM_BASE_ADDR))
    p.ADDI(IP, IP, 'interpreter_addr_addr')
    # word is found and located at a2
    p.ADDI(W, 'a2', 5)  # skip to start of word name (skip link and len)
    p.ADD(W, W, 'a1')  # point W to end of word name (might need padding)
    p.ADDI('a4', W, 0)  # setup arg for pad (a4 = W)
    p.JAL('ra', 'pad')  # call pad procedure
    p.ADDI(W, 'a4', 0)  # handle ret from pad (W = a4)
    # At this point, W holds the addr of the target word's code field
    p.LW('t0', W, 0)  # load code addr into t0 (t0 now holds addr of the word's code)
    p.JALR('zero', 't0', 0)  # execute the word!

# TODO: this feels real hacky (v3: Location('interpreter'), abs or rel? abs in this case)
#   OffsetFrom(RAM_BASE_ADDR, 'interpreter')
#   AbsolutePosition(RAM_BASE_ADDR, 'interpreter')
# This situation also differs because I want the imm value as LE bytes, not a number.
# What special keyword denotes that? ImmAsLE32(Position(RAM_BASE_ADDR, 'interp')), ImmAsLE16, etc?
with p.LABEL('interpreter_addr'):
    addr = RAM_BASE_ADDR + p.labels['interpreter_interpret']
    p.BLOB(struct.pack('<I', addr))
with p.LABEL('interpreter_addr_addr'):
    addr = RAM_BASE_ADDR + p.labels['interpreter_addr']
    p.BLOB(struct.pack('<I', addr))

p.ALIGN()  # not required but should be here since this is data between insts

# standard forth routine: next
with p.LABEL('next'):
    p.LW(W, IP, 0)
    p.ADDI(IP, IP, 4)
    p.LW('t0', W, 0)
    p.JALR('zero', 't0', 0)

# standard forth routine: enter
with p.LABEL('enter'):
    p.SW(RSP, IP, 0)
    p.ADDI(RSP, RSP, 4)
    p.ADDI(IP, W, 4)  # skip code field
    p.JAL('zero', 'next')

###
### dictionary starts here
###

# standard forth routine: exit
with defword(p, 'exit'):
    p.ADDI(RSP, RSP, -4)
    p.LW(IP, RSP, 0)
    p.JAL('zero', 'next')

# TODO: error if word name is too long (> 63) (if len & F_LENGTH != 0)
with defword(p, ':'):
    p.JAL('ra', 'token')  # a0 = addr, a1 = len
    p.SW(HERE, LATEST, 0)  # write link to prev word (write LATEST to HERE)
    p.SB(HERE, 'a1', 4)  # write word length
    p.ADDI(LATEST, HERE, 0)  # set LATEST = HERE (before HERE gets modified)
    p.ADDI(HERE, HERE, 5)  # move HERE past link and len (start of name)
with p.LABEL('strncpy'):  # NOTE: breaks if len <= 0
    p.ADDI('t0', 'a0', 0)  # t0 = strncpy src
    p.ADDI('t1', HERE, 0)  # t1 = strncpy dest
    p.ADDI('t2', 'a1', 0)  # t2 = strncpy len
with p.LABEL('strncpy_body'):
    p.LBU('t3', 't0', 0)  # t3 = [src]
    p.SB('t1', 't3', 0)  # [dest] = t3
with p.LABEL('strncpy_next'):
    p.ADDI('t2', 't2', -1)  # len--
    p.BEQ('t2', 'zero', 'strncpy_done')  # done if len == 0
    p.ADDI('t0', 't0', 1)  # src++
    p.ADDI('t1', 't1', 1)  # dest++
    p.JAL('zero', 'strncpy_body')  # copy next char
with p.LABEL('strncpy_done'):
    p.ADDI(HERE, 't1', 1)  # HERE = end of word, start of padding / code, need +1 cuz still on last char
    p.ADDI('a4', HERE, 0)  # setup arg for pad (a4 = HERE)
    p.JAL('ra', 'pad')  # call pad procedure
    p.ADDI(HERE, 'a4', 0)  # handle ret from pad (HERE = a4)
    #   OffsetFrom(RAM_BASE_ADDR, 'enter')
    #   AddressFrom(RAM_BASE_ADDR, 'enter')
    addr = RAM_BASE_ADDR + p.labels['enter']
    p.LUI('t0', p.HI(addr))  # load addr of ENTER into t0
    p.ADDI('t0', 't0', p.LO(addr))  # ...
    p.SW(HERE, 't0', 0)  # write addr of ENTER to word definition
    p.ADDI(HERE, HERE, 4)  # HERE += 4
    p.ADDI(STATE, 'zero', 1)  # STATE = 1 (compile)
    p.JAL('zero', 'next')  # next

with defword(p, ';', flags=F_IMMEDIATE):
    #   OffsetFrom(RAM_BASE_ADDR, 'word_exit')
    #   AddressFrom(RAM_BASE_ADDR, 'word_exit')
    addr = RAM_BASE_ADDR + p.labels['word_exit']
    p.LUI('t0', p.HI(addr))  # load addr of EXIT into t0
    p.ADDI('t0', 't0', p.LO(addr))  # ...
    p.SW(HERE, 't0', 0)  # write addr of EXIT to word definition
    p.ADDI(HERE, HERE, 4)  # HERE += 4
    p.ADDI(STATE, 'zero', 0)  # STATE = 0 (execute)
    p.JAL('zero', 'next')  # next

with defword(p, 'load'):
    # TBUF = disk_start
    p.LUI(TBUF, p.HI(ROM_BASE_ADDR))
    p.ADDI(TBUF, TBUF, p.LO(ROM_BASE_ADDR))
    # TODO: allow HI/LO relocations to deferred labels in ASMv3
    p.ADDI('t0', 'zero', 1)
    p.SLLI('t0', 't0', 14)
    p.ADD(TBUF, TBUF, 't0')

    # TLEN = disk_end - dist_start
    # TLEN = 4096
    # TODO: fix this hard-coded value in ASMv3
    p.ADDI('t0', 'zero', 1)
    p.SLLI(TLEN, 't0', 12)

    # TPOS = 0
    p.ADDI(TPOS, 'zero', 0)

    # next
    p.JAL('zero', 'next')

with defword(p, 'key'):
    # call getc (a5 = char)
    p.JAL('ra', 'getc')

    # isolate bottom 8 bits
    p.ANDI('a5', 'a5', 0xff)

    # push char onto stack
    p.SW(DSP, 'a5', 0)
    p.ADDI(DSP, DSP, 4)

    # next
    p.JAL('zero', 'next')

with defword(p, 'emit'):
    # pop char into a5
    p.ADDI(DSP, DSP, -4)
    p.LW('a5', DSP, 0)

    # isolate bottom 8 bits
    p.ANDI('a5', 'a5', 0xff)

    # call putc (char = a5)
    p.JAL('ra', 'putc')

    # next
    p.JAL('zero', 'next')

with defword(p, '@'):
    # pop address into t0
    p.ADDI(DSP, DSP, -4)
    p.LW('t0', DSP, 0)
    # load value from address
    p.LW('t0', 't0', 0)
    # push value onto stack
    p.SW(DSP, 't0', 0)
    p.ADDI(DSP, DSP, 4)
    # next
    p.JAL('zero', 'next')

with defword(p, '!'):
    # pop address into t0
    p.ADDI(DSP, DSP, -4)
    p.LW('t0', DSP, 0)
    # pop value into t1
    p.ADDI(DSP, DSP, -4)
    p.LW('t1', DSP, 0)
    # store value to address
    p.SW('t0', 't1', 0)
    # next
    p.JAL('zero', 'next')

with defword(p, 'sp@'):
    # copy DSP into t0 and decrement to current top value
    p.ADDI('t0', DSP, 0)
    p.ADDI('t0', 't0', -4)
    # push t0 onto stack
    p.SW(DSP, 't0', 0)
    p.ADDI(DSP, DSP, 4)
    # next
    p.JAL('zero', 'next')

with defword(p, 'rp@'):
    # copy RSP into t0 and decrement to current top value
    p.ADDI('t0', RSP, 0)
    p.ADDI('t0', 't0', -4)
    # push t0 onto stack
    p.SW(DSP, 't0', 0)
    p.ADDI(DSP, DSP, 4)
    # next
    p.JAL('zero', 'next')

with defword(p, '0='):
    # pop value into t0
    p.ADDI(DSP, DSP, -4)
    p.LW('t0', DSP, 0)
    # check equality between t0 and 0
    p.ADDI('t1', 'zero', 0)  # setup result (0 if nonzero)
    p.BNE('t0', 'zero', 'notzero')
    p.ADDI('t1', 'zero', -1)  # -1 if zero
with p.LABEL('notzero'):
    # push result of comparison onto stack
    p.SW(DSP, 't1', 0)
    p.ADDI(DSP, DSP, 4)
    # next
    p.JAL('zero', 'next')

with defword(p, '+'):
    # pop first value into t0
    p.ADDI(DSP, DSP, -4)
    p.LW('t0', DSP, 0)
    # pop second value into t1
    p.ADDI(DSP, DSP, -4)
    p.LW('t1', DSP, 0)
    # add the two together into t0
    p.ADD('t0', 't0', 't1')
    # push resulting sum onto stack
    p.SW(DSP, 't0', 0)
    p.ADDI(DSP, DSP, 4)
    # next
    p.JAL('zero', 'next')

p.LABEL('latest')  # mark the latest builtin word
with defword(p, 'nand'):
    # pop first value into t0
    p.ADDI(DSP, DSP, -4)
    p.LW('t0', DSP, 0)
    # pop second value into t1
    p.ADDI(DSP, DSP, -4)
    p.LW('t1', DSP, 0)
    # AND the two together into t0
    p.AND('t0', 't0', 't1')
    # NOT the value in t0
    p.XORI('t0', 't0', -1)
    # push resulting value onto stack
    p.SW(DSP, 't0', 0)
    p.ADDI(DSP, DSP, 4)
    # next
    p.JAL('zero', 'next')

p.LABEL('here')  # mark the location of the next new word

p.ALIGN(FORTH_SIZE)  # pad binary out to start of disk memory
p.LABEL('disk_start')

# duplicate the item on top of the stack
p.BLOB(b': dup sp@ @ ; ')

# basic decimal numbers
p.BLOB(b': -1 dup dup nand dup dup nand nand ; ')
p.BLOB(b': 0 -1 dup nand ; ')
p.BLOB(b': 1 -1 dup + dup nand ; ')
p.BLOB(b': 2 1 1 + ; ')
p.BLOB(b': 3 2 1 + ; ')
p.BLOB(b': 4 2 2 + ; ')
p.BLOB(b': 5 4 1 + ; ')
p.BLOB(b': 6 4 2 + ; ')
p.BLOB(b': 7 4 3 + ; ')
p.BLOB(b': 8 4 4 + ; ')
p.BLOB(b': 9 8 1 + ; ')
p.BLOB(b': 10 8 2 + ; ')
p.BLOB(b': 11 8 3 + ; ')
p.BLOB(b': 12 8 4 + ; ')
p.BLOB(b': 13 12 1 + ; ')
p.BLOB(b': 14 12 2 + ; ')
p.BLOB(b': 15 12 3 + ; ')
p.BLOB(b': 16 8 8 + ; ')

# inversion and negation
p.BLOB(b': invert dup nand ; ')
p.BLOB(b': negate invert 1 + ; ')
p.BLOB(b': - negate + ; ')

# stack manipulation words
p.BLOB(b': drop dup - + ; ')
p.BLOB(b': over sp@ 4 - @ ; ')
p.BLOB(b': swap over over sp@ 12 - ! sp@ 4 - ! ; ')
p.BLOB(b': nip swap drop ; ')
p.BLOB(b': 2dup over over ; ')
p.BLOB(b': 2drop drop drop ; ')

# logic operators
p.BLOB(b': and nand invert ; ')
p.BLOB(b': or invert swap invert and invert ; ')

# equality checks
p.BLOB(b': = - 0= ; ')
p.BLOB(b': <> = invert ; ')

# left shift operators (1, 4, and 8 bits)
p.BLOB(b': 2* dup + ; ')
p.BLOB(b': 16* 2* 2* 2* 2* ; ')
p.BLOB(b': 256* 16* 16* ; ')

# basic binary numbers
p.BLOB(b': 0b00 0 ; ')
p.BLOB(b': 0b01 1 ; ')
p.BLOB(b': 0b10 2 ; ')
p.BLOB(b': 0b11 3 ; ')
p.BLOB(b': 0b1111 15 ; ')

# basic hex numbers
p.BLOB(b': 0x00 0 ; ')
p.BLOB(b': 0x04 1 2* 2* ; ')
p.BLOB(b': 0x08 1 2* 2* 2* ; ')
p.BLOB(b': 0x0c 0x08 0x04 or ; ')
p.BLOB(b': 0x10 1 16* ; ')
p.BLOB(b': 0x14 0x10 0x04 or ; ')
p.BLOB(b': 0x18 0x10 0x08 or ; ')
p.BLOB(b': 0x1c 0x10 0x0c or ; ')
p.BLOB(b': 0x20 1 16* 2* ; ')
p.BLOB(b': 0x24 0x20 0x04 or ; ')
p.BLOB(b': 0x28 0x20 0x08 or ; ')
p.BLOB(b': 0x2c 0x20 0x0c or ; ')
p.BLOB(b': 0x30 0x20 0x10 or ; ')
p.BLOB(b': 0x34 0x30 0x04 or ; ')
p.BLOB(b': 0x38 0x30 0x08 or ; ')
p.BLOB(b': 0x3c 0x30 0x0c or ; ')

# define GPIO base address
p.BLOB(b': 0x40010800 1 256* 256* 256* 16* 2* 2* 1 256* 256* 1 256* 2* 2* 2* or or ; ')
p.BLOB(b': GPIO_BASE_ADDR 0x40010800 ; ')

# define offsets for each GPIO port
p.BLOB(b': GPIO_A_OFFSET 0x00 256* ; ')
p.BLOB(b': GPIO_B_OFFSET 0x04 256* ; ')
p.BLOB(b': GPIO_C_OFFSET 0x08 256* ; ')
p.BLOB(b': GPIO_D_OFFSET 0x0c 256* ; ')
p.BLOB(b': GPIO_E_OFFSET 0x10 256* ; ')

# define addresses for each GPIO port
p.BLOB(b': GPIO_A_ADDR GPIO_BASE_ADDR GPIO_A_OFFSET + ; ')
p.BLOB(b': GPIO_B_ADDR GPIO_BASE_ADDR GPIO_B_OFFSET + ; ')
p.BLOB(b': GPIO_C_ADDR GPIO_BASE_ADDR GPIO_C_OFFSET + ; ')
p.BLOB(b': GPIO_D_ADDR GPIO_BASE_ADDR GPIO_D_OFFSET + ; ')
p.BLOB(b': GPIO_E_ADDR GPIO_BASE_ADDR GPIO_E_OFFSET + ; ')

# define GPIO register offsets
p.BLOB(b': GPIO_CTL0_OFFSET 0x00 ; ')
p.BLOB(b': GPIO_CTL1_OFFSET 0x04 ; ')
p.BLOB(b': GPIO_ISTAT_OFFSET 0x08 ; ')
p.BLOB(b': GPIO_OCTL_OFFSET 0x0c ; ')
p.BLOB(b': GPIO_BOP_OFFSET 0x10 ; ')
p.BLOB(b': GPIO_BC_OFFSET 0x14 ; ')
p.BLOB(b': GPIO_LOCK_OFFSET 0x18 ; ')

# define GPIO mode constants
p.BLOB(b': GPIO_MODE_IN 0b00 ; ')
p.BLOB(b': GPIO_MODE_OUT_10MHZ 0b01 ; ')
p.BLOB(b': GPIO_MODE_OUT_2MHZ 0b10 ; ')
p.BLOB(b': GPIO_MODE_OUT_50MHZ 0b11 ; ')

# define GPIO input control constants
p.BLOB(b': GPIO_CTL_IN_ANALOG 0b00 ; ')
p.BLOB(b': GPIO_CTL_IN_FLOATING 0b01 ; ')
p.BLOB(b': GPIO_CTL_IN_PULL 0b10 ; ')
p.BLOB(b': GPIO_CTL_IN_RESERVED 0b11 ; ')

# define GPIO output control constants
p.BLOB(b': GPIO_CTL_OUT_PUSH_PULL 0b00 ; ')
p.BLOB(b': GPIO_CTL_OUT_OPEN_DRAIN 0b01 ; ')
p.BLOB(b': GPIO_CTL_OUT_ALT_PUSH_PULL 0b10 ; ')
p.BLOB(b': GPIO_CTL_OUT_ALT_OPEN_DRAIN 0b11 ; ')

# turn on the red LED from Forth!
p.BLOB(b': rled ')
p.BLOB(b'    GPIO_C_ADDR GPIO_CTL1_OFFSET + @ ')  # load current control
p.BLOB(b'    0b1111 ')  # setup mask for config pins
p.BLOB(b'    256* 256* 16* invert and ')  # shift over and clear existing config for pin 13
p.BLOB(b'    GPIO_CTL_OUT_PUSH_PULL 2* 2* GPIO_MODE_OUT_50MHZ or ')  # setup GPIO CTL and MODE
p.BLOB(b'    256* 256* 16* or ')  # shift over and set new config for pin 13
p.BLOB(b'    GPIO_C_ADDR GPIO_CTL1_OFFSET + ! ')  # store new control
p.BLOB(b'; ')

# turn on the green LED from Forth!
p.BLOB(b': gled ')
p.BLOB(b'    GPIO_A_ADDR GPIO_CTL0_OFFSET + @ ')  # load current control
p.BLOB(b'    0b1111 ')  # setup mask for config pins
p.BLOB(b'    16* invert and ')  # shift over and clear existing config for pin 1
p.BLOB(b'    GPIO_CTL_OUT_PUSH_PULL 2* 2* GPIO_MODE_OUT_50MHZ or ')  # setup GPIO CTL and MODE
p.BLOB(b'    16* or ')  # shift over and set new config for pin 1
p.BLOB(b'    GPIO_A_ADDR GPIO_CTL0_OFFSET + ! ')  # store new control
p.BLOB(b'; ')

# turn on the blue LED from Forth!
p.BLOB(b': bled ')
p.BLOB(b'    GPIO_A_ADDR GPIO_CTL0_OFFSET + @ ')  # load current control
p.BLOB(b'    0b1111 ')  # setup mask for config pins
p.BLOB(b'    256* invert and ')  # shift over and clear existing config for pin 2
p.BLOB(b'    GPIO_CTL_OUT_PUSH_PULL 2* 2* GPIO_MODE_OUT_50MHZ or ')  # setup GPIO CTL and MODE
p.BLOB(b'    256* or ')  # shift over and set new config for pin 2
p.BLOB(b'    GPIO_A_ADDR GPIO_CTL0_OFFSET + ! ')  # store new control
p.BLOB(b'; ')

p.LABEL('disk_end')


with open('forth.bin', 'wb') as f:
    f.write(p.machine_code)
