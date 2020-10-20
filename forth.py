from contextlib import contextmanager
import struct

from simpleriscv import asm

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


#       Register Assignment
# |------------------------------|
# | reg | name |   description   |
# |------------------------------|
# |  x0 | zero | always 0        |
# |  x1 |  ra  | working reg     |
# |  x2 |  sp  | data stack ptr  |
# |  x3 |  gp  | interpreter ptr |
# |  x4 |  tp  | ret stack ptr   |
# |  x5 |  t0  | temp reg 0      |
# |  x6 |  t1  | temp reg 1      |
# |  x7 |  t2  | temp reg 2      |
# |  x8 |  s0  | STATE var       |
# |  x9 |  s1  | TIB var         |
# | x18 |  s2  | >IN var         |
# | x19 |  s3  | HERE var        |
# | x20 |  s4  | LATEST var      |
# | x28 |  t3  | temp reg 3      |
# | x29 |  t4  | temp reg 4      |
# | x30 |  t5  | temp reg 5      |
# | x31 |  t6  | temp reg 6      |
# |------------------------------|

# "The Classical Forth Registers"
W = 'ra'  # working register
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
STATE = 's0'
TIB = 's1'
TOIN = 's2'
HERE = 's3'
LATEST = 's4'


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


F_IMMEDIATE = 0x80
F_HIDDEN = 0x40
LEN_MASK = 0x1f

LINK = None

@contextmanager
def defword(p, name, label, flags=0):
    """
    Macro to define a Forth word. The LINK stuff is really hacky and
    I'd like to replace it with something else. The "flags" param be any
    or'd combo of the 2 F_FOO constants defined above.

    TODO: are any of these 2 internal labels necessary?
    """

    if len(name) > 0x1f:
        raise ValueError('Word name is longer than 0x1f (31 chars): {}'.format(name))

    word_label = 'word_' + label
    p.LABEL(word_label)

    # these links will above be relative and negative
    #  (since new words are higher in the address space)
    global LINK
    if LINK is None:
        link = 0
    else:
        link = p.labels[LINK] - p.labels[word_label]
    LINK = word_label

    p.BLOB(struct.pack('<h', link))
    p.BLOB(struct.pack('<B', len(name)))
    p.BLOB(name.encode())
    p.ALIGN()

    p.LABEL(name)
    yield


p = asm.Program()


# code in ROM starts here
# code for copying ROM to RAM starts here

# t0 = src, t1 = dest, t2 = count
with p.LABEL('copy'):
    # setup copy src (ROM_BASE_ADDR)
    p.LUI('t0', p.HI(ROM_BASE_ADDR))
    p.ADDI('t0', 't0', p.LO(ROM_BASE_ADDR))
    # setup copy dest (RAM_BASE_ADDR)
    p.LUI('t1', p.HI(RAM_BASE_ADDR))
    p.ADDI('t1', 't1', p.LO(RAM_BASE_ADDR))
    # setup copy count (everything up to the "here" label)
    p.ADDI('t2', 'zero', 'here')

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
    p.ADDI('t0', 't0', 'start_led')
    p.JALR('zero', 't0', 0)


# code in RAM starts here
# main Forth interpreter starts here

# this just exists to ensure that code got correctly copied from ROM to RAM
with p.LABEL('start_led'):
    RCU_BASE_ADDR = 0x40021000
    RCU_APB2_ENABLE_OFFSET = 0x18
    GPIO_BASE_ADDR_C = 0x40011000
    GPIO_CTRL1_OFFSET = 0x04
    GPIO_MODE_OUT_50MHZ = 0b11
    GPIO_CTRL_OUT_PUSH_PULL = 0b00

    # load RCU base addr into x1
    p.LUI('x1', p.HI(RCU_BASE_ADDR))
    p.ADDI('x1', 'x1', p.LO(RCU_BASE_ADDR))

    p.ADDI('x1', 'x1', RCU_APB2_ENABLE_OFFSET)  # move x1 forward to APB2 enable register
    p.LW('x2', 'x1', 0)  # load current APB2 enable config into x2

    # prepare the GPIO enable bits
    #                     | EDCBA  |
    p.ADDI('x3', 'zero', 0b00010100)

    # enable GPIO clock
    p.OR('x2', 'x2', 'x3')
    p.SW('x1', 'x2', 0)

    # load GPIO base addr into x1
    p.LUI('x1', p.HI(GPIO_BASE_ADDR_C))
    p.ADDI('x1', 'x1', p.LO(GPIO_BASE_ADDR_C))

    # move x1 forward to control 1 register
    p.ADDI('x1', 'x1', GPIO_CTRL1_OFFSET)

    # TODO: this is destructive
    p.ADDI('x2', 'zero', (GPIO_CTRL_OUT_PUSH_PULL << 2) | GPIO_MODE_OUT_50MHZ)  # load pin settings into x2
    p.SLLI('x2', 'x2', 20)  # shift settings over to correct pin ((PIN - 8) * 4)

    # apply the GPIO config back
    p.SW('x1', 'x2', 0)

with p.LABEL('start'):
    p.JAL('zero', 'init')
with p.LABEL('error'):
    # TODO: print error indicator ("!!" or "?" or something like that)
    pass
with p.LABEL('init'):
    # setup data stack pointer
    p.LUI(DSP, p.HI(DATA_STACK_BASE))
    p.ADDI(DSP, DSP, p.LO(DATA_STACK_BASE))

    # setup return stack pointer
    p.LUI(RSP, p.HI(RETURN_STACK_BASE))
    p.ADDI(RSP, RSP, p.LO(RETURN_STACK_BASE))

    # set STATE var to zero
    p.ADDI(STATE, 'zero', 0)

    # set TIB var to "tib" location
    p.LUI(TIB, p.HI(RAM_BASE_ADDR))
    p.ADDI(TIB, TIB, p.LO(RAM_BASE_ADDR))
    p.ADDI(TIB, TIB, 'tib')

    # set TOIN var to zero
    p.ADDI(TOIN, 'zero', 0)

    # set HERE var to "here" location
    p.LUI(HERE, p.HI(RAM_BASE_ADDR))
    p.ADDI(HERE, HERE, p.LO(RAM_BASE_ADDR))
    p.ADDI(HERE, HERE, 'here')

    # set LATEST var to "latest" location
    p.LUI(LATEST, p.HI(RAM_BASE_ADDR))
    p.ADDI(LATEST, LATEST, p.LO(RAM_BASE_ADDR))
    p.ADDI(LATEST, LATEST, 'latest')


# TODO: fill in all these goodies
p.LABEL('interpreter')
p.LABEL('token')


# standard forth routine: next
with p.LABEL('next'):
    p.LW(W, IP, 0)
    p.ADDI(IP, IP, 4)
    p.JALR('zero', W, 0)

# standard forth routine: enter (aka docol)
with p.LABEL('enter'):
    p.SW(RSP, IP, 0)
    p.ADDI(RSP, RSP, 4)
    p.ADDI(IP, W, 4)  # skip code field
    p.JAL('zero', 'next')

# standard forth routine: exit (aka semi)
with p.LABEL('exit'):
    p.ADDI(RSP, RSP, -4)
    p.LW(IP, RSP, 0)
    p.JAL('zero', 'next')

with p.LABEL('tib'):
    # make some numbers
    p.BLOB(b': dup sp@ @ ;')
    p.BLOB(b': -1 dup dup nand dup dup nand nand ;')
    p.BLOB(b': 0 -1 dup nand ;')
    p.BLOB(b': 1 -1 dup + dup nand ;')
    p.BLOB(b': 2 1 1 + ;')
    p.BLOB(b': 4 2 2 + ;')
    p.BLOB(b': 8 4 4 + ;')

    # logic and arithmetic operators
    p.BLOB(b': invert dup nand ;')
    p.BLOB(b': and nand invert ;')
    p.BLOB(b': negate invert 1 + ;')
    p.BLOB(b': - negate + ;')

p.ALIGN()

# dictionary starts here

with defword(p, '@', 'FETCH'):
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

with defword(p, '!', 'STORE'):
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

with defword(p, 'sp@', 'SPFETCH'):
    # push DSP onto stack
    p.SW(DSP, DSP, 0)
    p.ADDI(DSP, DSP, 4)
    # next
    p.JAL('zero', 'next')

with defword(p, 'rp@', 'RPFETCH'):
    # push RSP onto stack
    p.SW(DSP, RSP, 0)
    p.ADDI(DSP, DSP, 4)
    # next
    p.JAL('zero', 'next')

with defword(p, '0=', 'ZEROEQUALS'):
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

with defword(p, '+', 'PLUS'):
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

with defword(p, 'nand', 'NAND'):
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

p.LABEL('latest')
p.LABEL('here')

with open('forth.bin', 'wb') as f:
    f.write(p.machine_code)
