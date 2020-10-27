from contextlib import contextmanager
import struct

from simpleriscv import asm

# Types of Immediate values (one of Literal / Position / Location / Address):
# An Immediate can be resolved to a Number given a map[string]int of labels (can be nil, too)
# Resolution wouldn't happen until subsequent passes of the assembler
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

# GD32VF103[CBT6]: Longan Nano, Wio Lite
ROM_BASE_ADDR = 0x08000000  # 128K
RAM_BASE_ADDR = 0x20000000  # 32K

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
# |  x2 |  sp  | data stack ptr  |
# |  x3 |  gp  | interpreter ptr |
# |  x4 |  tp  | ret stack ptr   |
# |  x5 |  t0  | scratch         |
# |  x6 |  t1  | scratch         |
# |  x7 |  t2  | scratch         |
# |  x8 |  s0  | working reg     |
# |  x9 |  s1  | STATE var       |
# | x10 |  a0  | token address   |
# | x11 |  a1  | token length    |
# | x12 |  a2  | lookup address  |
# | x13 |  a3  | align arg / ret |
# | x14 |  a4  | <unused>        |
# | x15 |  a5  | <unused>        |
# | x16 |  a6  | <unused>        |
# | x17 |  a7  | <unused>        |
# | x18 |  s2  | TIB var         |
# | x19 |  s3  | >IN var         |
# | x20 |  s4  | HERE var        |
# | x21 |  s5  | LATEST var      |
# | x22 |  s6  | <unused>        |
# | x23 |  s7  | <unused>        |
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
# | TIB    | terminal input buffer         |
# | >IN    | current offset into TIB       |
# | HERE   | ptr to next free pos in dict  |
# | LATEST | ptr to most recent dict entry |
# |----------------------------------------|

# Variable registers
STATE = 's1'
TIB = 's2'
TOIN = 's3'
HERE = 's4'
LATEST = 's5'


#  16KB      Memory Map
# 0x0000 |----------------|
#        |                |
#        |  Interpreter   |
#        |       +        |
# 0x1000 |      TIB       |
#        |       +        |
#        |   Dictionary   |
#        |                |
# 0x2000 |----------------|
#        |                |
#        |   Data Stack   |
#        |                |
# 0x3000 |----------------|
#        |                |
#        |  Return Stack  |
#        |                |
# 0x3FFF |----------------|

INTERPRETER_BASE = 0x0000
DATA_STACK_BASE = 0x2000
RETURN_STACK_BASE = 0x3000

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
    p.LUI('t0', p.HI(RAM_BASE_ADDR))
    p.ADDI('t0', 't0', p.LO(RAM_BASE_ADDR))
    p.ADDI('t0', 't0', 'start')
    p.JALR('zero', 't0', 0)

with p.LABEL('start'):
    p.JAL('zero', 'init')
with p.LABEL('error'):
    # TODO: print error indicator ("?" or something like that)
    # can do this once UART works and can print stuff using "emit"
    pass
with p.LABEL('init'):
    # setup data stack pointer
    p.LUI(DSP, p.HI(RAM_BASE_ADDR + DATA_STACK_BASE))
    p.ADDI(DSP, DSP, p.LO(RAM_BASE_ADDR + DATA_STACK_BASE))

    # setup return stack pointer
    p.LUI(RSP, p.HI(RAM_BASE_ADDR + RETURN_STACK_BASE))
    p.ADDI(RSP, RSP, p.LO(RAM_BASE_ADDR + RETURN_STACK_BASE))

    # set working register to zero
    p.ADDI(W, 'zero', 0)

    # set STATE var to zero
    p.ADDI(STATE, 'zero', 0)

    # set TIB var to "tib" location
    p.LUI(TIB, p.HI(RAM_BASE_ADDR))
    p.ADDI(TIB, TIB, p.LO(RAM_BASE_ADDR))
    p.ADDI(TIB, TIB, 'tib')

    # fill TIB with zeroes
#    p.LABEL('tib_clear')
#    p.ADDI('t0', TIB, 9)  # t0 = addr
#    p.ADDI('t1', 'zero', 1)  # t1 = 1
#    p.SLLI('t1', 't1', 10)  # t1 = 1024 (count)
#    p.LABEL('tib_clear_body')
#    p.SB('t0', 'zero', 0)  # [t0] = 0
#    p.LABEL('tib_clear_next')
#    p.ADDI('t0', 't0', 1)  # t0 += 1
#    p.ADDI('t1', 't1', -1)  # t1 -= 1
#    p.BNE('t1', 'zero', 'tib_clear_body')  # keep looping til t1 == 0

    # set TOIN var to zero
    p.ADDI(TOIN, 'zero', 0)

    # set HERE var to "here" location
    #   Position(RAM_BASE_ADDR, 'here') -> Number, not bytes
    p.LUI(HERE, p.HI(RAM_BASE_ADDR))
    p.ADDI(HERE, HERE, p.LO(RAM_BASE_ADDR))
    p.ADDI(HERE, HERE, 'here')

    # set LATEST var to "latest" location
    p.LUI(LATEST, p.HI(RAM_BASE_ADDR))
    p.ADDI(LATEST, LATEST, p.LO(RAM_BASE_ADDR))
    p.ADDI(LATEST, LATEST, 'latest')

# main interpreter loop
with p.LABEL('interpreter'):
    p.JAL('ra', 'token')  # call token procedure (a0 = addr, a1 = len)
    p.JAL('ra', 'lookup')  # call lookup procedure (a2 = addr)
    p.BEQ('a2', 'zero', 'error')  # error and reset if word isn't found

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
    p.JAL('zero', 'interpreter')
with p.LABEL('interpreter_execute'):
    # set interpreter pointer to indirect addr back to interpreter loop
    # TODO: can't just pre-calc addr here because its a forward ref
    #   and I can't dig into p.labels yet. Fix in v3.
    p.LUI(IP, p.HI(RAM_BASE_ADDR))
    p.ADDI(IP, IP, p.LO(RAM_BASE_ADDR))
    p.ADDI(IP, IP, 'interpreter_addr_addr')
    # word is found and located at a2
    p.ADDI(W, 'a2', 5)  # skip to start of word name (skip link and len)
    p.ADD(W, W, 'a1')  # point W to end of word name (might need padding)
with p.LABEL('interpreter_padding'):
    p.ANDI('t0', W, 0b11)  # isolate bottom two bits of W
    p.BEQ('t0', 'zero', 'interpreter_padding_done')  # done if they are zero (which means W is a multiple of 4)
    p.ADDI(W, W, 1)  # W += 1
    p.JAL('zero', 'interpreter_padding')  # keep on padding
with p.LABEL('interpreter_padding_done'):
    # At this point, W holds the addr of the target word's code field
    p.LW('t0', W, 0)  # load code addr into t0 (t0 now holds addr of the word's code)
    p.JALR('zero', 't0', 0)  # execute the word!

# TODO: this feels real hacky (v3: Location('interpreter'), abs or rel? abs in this case)
#   OffsetFrom(RAM_BASE_ADDR, 'interpreter')
#   AbsolutePosition(RAM_BASE_ADDR, 'interpreter')
with p.LABEL('interpreter_addr'):
    addr = RAM_BASE_ADDR + p.labels['interpreter']
    p.BLOB(struct.pack('<I', addr))
with p.LABEL('interpreter_addr_addr'):
    addr = RAM_BASE_ADDR + p.labels['interpreter_addr']
    p.BLOB(struct.pack('<I', addr))

p.ALIGN()  # not required but should be here since this is data between insts

# Procedure: token
# Usage: p.JAL('ra', 'token')
# Ret: a0 = addr of word name
# Ret: a1 = length of word name
with p.LABEL('token'):
    # TODO: handle running off the TIB (max 1024 bytes or something)
    p.ADDI('t0', 'zero', 33)  # put whitespace threshold value into t0
with p.LABEL('token_skip_whitespace'):
    p.ADD('t1', TIB, TOIN)  # point t1 at current char
    p.LBU('t2', 't1', 0)  # load current char into t2
    p.BGE('t2', 't0', 'token_scan')  # check if done skipping whitespace
    p.ADDI(TOIN, TOIN, 1)  # inc TOIN
    p.JAL('zero', 'token_skip_whitespace')  # check again
with p.LABEL('token_scan'):
    p.ADDI('t1', TOIN, 0)  # put current TOIN value into t1
with p.LABEL('token_scan_loop'):
    p.ADD('t2', TIB, 't1')  # point t2 at next char
    p.LBU('t3', 't2', 0)  # load next char into t3
    p.BLT('t3', 't0', 'token_done')  # check for whitespace
    p.ADDI('t1', 't1', 1)  # increment offset
    p.JAL('zero', 'token_scan_loop')  # scan the next char
with p.LABEL('token_done'):
    p.ADD('a0', TIB, TOIN)  # a0 = address of word
    p.SUB('a1', 't1', TOIN)  # a1 = length of word
    p.ADDI(TOIN, 't1', 0)  # update TOIN
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

with p.LABEL('tib'):
#    p.BLOB(b'rcu rled gled usart0 gled ')

    # TODO: Option 1: after compile, lookup can't find pled (strncpy bug?)
    # TODO: Option 2: after compile, after lookup, execution of pled goes wonky (inner interp bug?)
    p.BLOB(b'rcu ')
    p.BLOB(b': pled rcu rled bled ; ')
    p.BLOB(b'rled ')
    p.BLOB(b'pled ')
    p.BLOB(b'gled ')

#    # make some numbers
#    p.BLOB(b': dup sp@ @ ; ')
#    p.BLOB(b': -1 dup dup nand dup dup nand nand ; ')
#    p.BLOB(b': 0 -1 dup nand ; ')
#    p.BLOB(b': 1 -1 dup + dup nand ; ')
#    p.BLOB(b': 2 1 1 + ; ')
#    p.BLOB(b': 4 2 2 + ; ')
#    p.BLOB(b': 8 4 4 + ; ')
#    p.BLOB(b': 12 4 8 + ; ')
#    p.BLOB(b': 16 8 8 + ; ')
#
#    # logic and arithmetic operators
#    p.BLOB(b': invert dup nand ; ')
#    p.BLOB(b': and nand invert ; ')
#    p.BLOB(b': negate invert 1 + ; ')
#    p.BLOB(b': - negate + ; ')
#
#    # equality checks
#    p.BLOB(b': = - 0= ; ')
#    p.BLOB(b': <> = invert ; ')
#
#    # stack manipulation words
#    p.BLOB(b': drop dup - + ; ')
#    p.BLOB(b': over sp@ 4 + @ ; ')
#    p.BLOB(b': swap over over sp@ 12 + ! sp@ 4 + ! ; ')
#    p.BLOB(b': nip swap drop ; ')
#    p.BLOB(b': 2dup over over ; ')
#    p.BLOB(b': 2drop drop drop ; ')
#
#    # more logic
#    p.BLOB(b': or invert swap invert and invert ; ')
#
#    # left shift 1 bit
#    p.BLOB(b': 2* dup + ; ')

    # paranoid align just to be safe
    p.ALIGN()


# standard forth routine: next
with p.LABEL('next'):
    p.LW(W, IP, 0)
    p.ADDI(IP, IP, 4)
    p.LW('t0', W, 0)
    p.JALR('zero', 't0', 0)

###
### dictionary starts here
###

# standard forth routine: enter
with defword(p, 'enter'):
    p.JAL('zero', 'body_reddy')
    p.SW(RSP, IP, 0)
    p.ADDI(RSP, RSP, 4)
    p.ADDI(IP, W, 4)  # skip code field
    p.JAL('zero', 'next')

# standard forth routine: exit
with defword(p, 'exit'):
    p.ADDI(RSP, RSP, -4)
    p.LW(IP, RSP, 0)
    p.JAL('zero', 'next')

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
with p.LABEL('padding_body'):
    p.ANDI('t0', HERE, 0b11)  # isolate bottom two bits of HERE
    p.BEQ('t0', 'zero', 'padding_done')  # done if they are zero (which means HERE is a multiple of 4)
    p.SB(HERE, 'zero', 0)  # else store a zero
with p.LABEL('padding_next'):
    p.ADDI(HERE, HERE, 1)  # HERE++
    p.JAL('zero', 'padding_body')  # loop again
with p.LABEL('padding_done'):
    #   OffsetFrom(RAM_BASE_ADDR, 'word_enter')
    #   AddressFrom(RAM_BASE_ADDR, 'word_enter')
    addr = RAM_BASE_ADDR + p.labels['word_enter']
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

with defword(p, 'rcu'):
    # load RCU base addr into t0
    p.LUI('t0', p.HI(RCU_BASE_ADDR))
    p.ADDI('t0', 't0', p.LO(RCU_BASE_ADDR))

    p.ADDI('t0', 't0', RCU_APB2_ENABLE_OFFSET)  # move t0 forward to APB2 enable register
    p.LW('t1', 't0', 0)  # load current APB2 enable config into t1

    # prepare enable bits for GPIO A and GPIO C
    #                     | EDCBA  |
    p.ADDI('t2', 'zero', 0b00010100)

    # prepare enable bit for USART0
    p.ADDI('t3', 'zero', 1)
    p.SLLI('t3', 't3', 14)
    p.OR('t2', 't2', 't3')

    # set GPIO clock enable bits
    p.OR('t1', 't1', 't2')
    p.SW('t0', 't1', 0)  # store the ABP2 config

    # next
    p.JAL('zero', 'next')

# debug place to jump to check if the code got somewhere
with defword(p, 'reddy'):
    # load RCU base addr into t0
    p.LUI('t0', p.HI(RCU_BASE_ADDR))
    p.ADDI('t0', 't0', p.LO(RCU_BASE_ADDR))

    p.ADDI('t0', 't0', RCU_APB2_ENABLE_OFFSET)  # move t0 forward to APB2 enable register
    p.LW('t1', 't0', 0)  # load current APB2 enable config into t1

    # prepare enable bits for GPIO A and GPIO C
    #                     | EDCBA  |
    p.ADDI('t2', 'zero', 0b00010100)

    # prepare enable bit for USART0
    p.ADDI('t3', 'zero', 1)
    p.SLLI('t3', 't3', 14)
    p.OR('t2', 't2', 't3')

    # set GPIO clock enable bits
    p.OR('t1', 't1', 't2')
    p.SW('t0', 't1', 0)  # store the ABP2 config

    # load GPIO base addr into t0
    p.LUI('t0', p.HI(GPIO_BASE_ADDR_C))
    p.ADDI('t0', 't0', p.LO(GPIO_BASE_ADDR_C))

    # move t0 forward to control 1 register
    p.ADDI('t0', 't0', GPIO_CTL1_OFFSET)

    # load current GPIO config into t1
    p.LW('t1', 't0', 0)

    # clear existing config
    p.ADDI('t2', 'zero', 0b1111)
    p.SLLI('t2', 't2', 20)
    p.XORI('t2', 't2', -1)
    p.AND('t1', 't1', 't2')

    # set new config settings
    p.ADDI('t2', 'zero', (GPIO_CTL_OUT_PUSH_PULL << 2) | GPIO_MODE_OUT_50MHZ)
    p.SLLI('t2', 't2', 20)
    p.OR('t1', 't1', 't2')

    # store the GPIO config
    p.SW('t0', 't1', 0)

    # next
    p.JAL('zero', 'next')

# red LED: GPIO port C, ctrl 1, pin 13
# offset: ((PIN - 8) * 4) = 20
with defword(p, 'rled'):
    # load GPIO base addr into t0
    p.LUI('t0', p.HI(GPIO_BASE_ADDR_C))
    p.ADDI('t0', 't0', p.LO(GPIO_BASE_ADDR_C))

    # move t0 forward to control 1 register
    p.ADDI('t0', 't0', GPIO_CTL1_OFFSET)

    # load current GPIO config into t1
    p.LW('t1', 't0', 0)

    # clear existing config
    p.ADDI('t2', 'zero', 0b1111)
    p.SLLI('t2', 't2', 20)
    p.XORI('t2', 't2', -1)
    p.AND('t1', 't1', 't2')

    # set new config settings
    p.ADDI('t2', 'zero', (GPIO_CTL_OUT_PUSH_PULL << 2) | GPIO_MODE_OUT_50MHZ)
    p.SLLI('t2', 't2', 20)
    p.OR('t1', 't1', 't2')

    # store the GPIO config
    p.SW('t0', 't1', 0)

    # next
    p.JAL('zero', 'next')

# green LED: GPIO port A, ctrl 0, pin 1
# offset: (PIN * 4) = 4
with defword(p, 'gled'):
    # load GPIO base addr into t0
    p.LUI('t0', p.HI(GPIO_BASE_ADDR_A))
    p.ADDI('t0', 't0', p.LO(GPIO_BASE_ADDR_A))

    # move t0 forward to control 0 register
    p.ADDI('t0', 't0', GPIO_CTL0_OFFSET)

    # load current GPIO config into t1
    p.LW('t1', 't0', 0)

    # clear existing config
    p.ADDI('t2', 'zero', 0b1111)
    p.SLLI('t2', 't2', 4)
    p.XORI('t2', 't2', -1)
    p.AND('t1', 't1', 't2')

    # set new config settings
    p.ADDI('t2', 'zero', (GPIO_CTL_OUT_PUSH_PULL << 2) | GPIO_MODE_OUT_50MHZ)
    p.SLLI('t2', 't2', 4)
    p.OR('t1', 't1', 't2')

    # store the GPIO config
    p.SW('t0', 't1', 0)

    # next
    p.JAL('zero', 'next')

# blue LED: GPIO port A, ctrl 0, pin 2
# offset: (PIN * 4) = 8
with defword(p, 'bled'):
    # load GPIO base addr into t0
    p.LUI('t0', p.HI(GPIO_BASE_ADDR_A))
    p.ADDI('t0', 't0', p.LO(GPIO_BASE_ADDR_A))

    # move t0 forward to control 0 register
    p.ADDI('t0', 't0', GPIO_CTL0_OFFSET)

    # load current GPIO config into t1
    p.LW('t1', 't0', 0)

    # clear existing config
    p.ADDI('t2', 'zero', 0b1111)
    p.SLLI('t2', 't2', 8)
    p.XORI('t2', 't2', -1)
    p.AND('t1', 't1', 't2')

    # set new config settings
    p.ADDI('t2', 'zero', (GPIO_CTL_OUT_PUSH_PULL << 2) | GPIO_MODE_OUT_50MHZ)
    p.SLLI('t2', 't2', 8)
    p.OR('t1', 't1', 't2')

    # store the GPIO config
    p.SW('t0', 't1', 0)

    # next
    p.JAL('zero', 'next')

# USART0: GPIO port A, ctrl 1, pins 9 and 10
# offset: ((PIN - 8) * 4) = 4 (pin 9)
# offset: ((PIN - 8) * 4) = 8 (pin 10)
with defword(p, 'usart0'):
    # load GPIO base addr into t0
    p.LUI('t0', p.HI(GPIO_BASE_ADDR_A))
    p.ADDI('t0', 't0', p.LO(GPIO_BASE_ADDR_A))

    # move t0 forward to control 1 register
    p.ADDI('t0', 't0', GPIO_CTL1_OFFSET)

    # load current GPIO config into t1
    p.LW('t1', 't0', 0)

    # clear existing config (pin 9)
    p.ADDI('t2', 'zero', 0b1111)
    p.SLLI('t2', 't2', 4)
    p.XORI('t2', 't2', -1)
    p.AND('t1', 't1', 't2')

    # set new config settings (pin 9)
    p.ADDI('t2', 'zero', (GPIO_CTL_OUT_ALT_PUSH_PULL << 2) | GPIO_MODE_OUT_50MHZ)
    p.SLLI('t2', 't2', 4)
    p.OR('t1', 't1', 't2')

    # clear existing config (pin 10)
    p.ADDI('t2', 'zero', 0b1111)
    p.SLLI('t2', 't2', 8)
    p.XORI('t2', 't2', -1)
    p.AND('t1', 't1', 't2')

    # set new config settings (pin 10)
    p.ADDI('t2', 'zero', (GPIO_CTL_IN_FLOATING << 2) | GPIO_MODE_IN)
    p.SLLI('t2', 't2', 8)
    p.OR('t1', 't1', 't2')

    # store the GPIO config
    p.SW('t0', 't1', 0)

    # USART config: 115200 8N1
    # enabled (USART_CTL0 bit 13)
    # rx/tx enabled (USART_CTL0 bits 2 and 3)
    # 115200 baud (USART_BAUD)
    # 8 bits per word (USART_CTL0 bit 12, default)
    # 1 stop bit (USART_CTL1 bits 13:12, default)
    # 0 parity bits (USART_CTL0 bit 10, default)

    # load RCU base addr into t0
    p.LUI('t0', p.HI(RCU_BASE_ADDR))
    p.ADDI('t0', 't0', p.LO(RCU_BASE_ADDR))
    # move t0 forward to APB2 reset register
    p.ADDI('t0', 't0', RCU_APB2_RESET_OFFSET)

    # reset USART0
    p.ADDI('t1', 'zero', 1)
    p.SLLI('t1', 't1', 14)
    p.SW('t0', 't1', 0)
    p.ADDI('t1', 'zero', 0)
    p.SLLI('t1', 't1', 14)
    p.SW('t0', 't1', 0)

    # NOTE: This math yields the same results achieved from
    #   following the GD32VF103 manual (16.3.2). I'm not sure
    #   if this is always the case or just happens to work out
    #   for a few common baud rates (9600 and 115200, at least).
    #
    # Example 1:
    # >>> import math
    # >>> PCLK = 8000000
    # >>> BAUD = 9600
    # >>> PCLK // BAUD
    # 833
    # >>>
    # >>> d = PCLK / BAUD / 16
    # >>> fracdiv, intdiv = math.modf(d)
    # >>> intdiv = int(intdiv)
    # >>> fracdiv = round(16 * fracdiv)
    # >>> intdiv << 4 | fracdiv
    # 833
    #
    # Example 2:
    # >>> import math
    # >>> PCLK = 8000000
    # >>> BAUD = 115200
    # >>> PCLK // BAUD
    # 69
    # >>>
    # >>> d = PCLK / BAUD / 16
    # >>> fracdiv, intdiv = math.modf(d)
    # >>> intdiv = int(intdiv)
    # >>> fracdiv = round(16 * fracdiv)
    # >>> intdiv << 4 | fracdiv
    # 69

    CLOCK = 8000000  # 8MHz
    BAUD = 115200  # 115200 bits per second
    udiv = CLOCK // BAUD

    # load USART0 base address
    p.LUI('t0', p.HI(USART_BASE_ADDR_0))
    p.ADDI('t0', 't0', p.LO(USART_BASE_ADDR_0))

    # configure USART0 baud rate
    p.ADDI('t1', 't0', USART_BAUD_OFFSET)
    p.ADDI('t2', 'zero', udiv)
    p.SW('t1', 't2', 0)

    # enable TX and RX
    p.ADDI('t1', 't0', USART_CTL0_OFFSET)
    p.ADDI('t2', 'zero', 0b1100)
    p.SW('t1', 't2', 0)

    # enable USART0 (but don't overwrite TX/RX config)
    p.ADDI('t1', 't0', USART_CTL0_OFFSET)
    p.ADDI('t2', 'zero', 0b1100)
    p.ADDI('t3', 'zero', 1)
    p.SLLI('t3', 't3', 13)
    p.OR('t2', 't2', 't3')
    p.SW('t1', 't2', 0)

    # write out a continuous stream of '!' to serial
    p.ADDI('t1', 't0', USART_STAT_OFFSET)
    p.ADDI('t2', 't0', USART_DATA_OFFSET)
    p.ADDI('t3', 'zero', 33)
    p.LABEL('usart_loop')
    p.LW('t4', 't1', 0)  # load stat
    p.ANDI('t4', 't4', 1 << 7)
    p.BEQ('t4', 'zero', 'usart_loop')  # loop til TBE
    p.SW('t2', 't3', 0)  # write the '!'
    p.JAL('zero', 'usart_loop')  # loop again

    # next
    p.JAL('zero', 'next')

with defword(p, 'state'):
    # push STATE onto stack
    p.SW(DSP, STATE, 0)
    p.ADDI(DSP, DSP, 4)
    # next
    p.JAL('zero', 'next')

with defword(p, 'tib'):
    # push TIB onto stack
    p.SW(DSP, TIB, 0)
    p.ADDI(DSP, DSP, 4)
    # next
    p.JAL('zero', 'next')

with defword(p, '>in'):
    # push TOIN onto stack
    p.SW(DSP, TOIN, 0)
    p.ADDI(DSP, DSP, 4)
    # next
    p.JAL('zero', 'next')

with defword(p, 'here'):
    # push HERE onto stack
    p.SW(DSP, HERE, 0)
    p.ADDI(DSP, DSP, 4)
    # next
    p.JAL('zero', 'next')

with defword(p, 'latest'):
    # push LATEST onto stack
    p.SW(DSP, LATEST, 0)
    p.ADDI(DSP, DSP, 4)
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
    p.ADDI('t1', 'zero', 0)
    p.BNE('t0', 'zero', 'notzero')
    p.ADDI('t1', 't1', -1)  # -1 if zero, 0 otherwise
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

print(hex(RAM_BASE_ADDR + p.labels['latest']))
print(hex(RAM_BASE_ADDR + p.labels['here']))
print(hex(RAM_BASE_ADDR + p.labels['word_enter']))
print(hex(RAM_BASE_ADDR + p.labels['word_rcu']))
print(hex(RAM_BASE_ADDR + p.labels['word_exit']))

with open('forth.bin', 'wb') as f:
    f.write(p.machine_code)
