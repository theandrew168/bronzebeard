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

# PicoRV32/PicoSoC: iCEBreaker (Lattice iCE40UP5K FPGA)
#ROM_BASE_ADDR = 0x00100000  # 16M
#RAM_BASE_ADDR = 0x00000000  # 128K

# PicoRV32/PicoSoC: TinyFPGA BX (Lattice iCE40LP8K FPGA)
#ROM_BASE_ADDR = 0x00050000  # 1M
#RAM_BASE_ADDR = 0x00000000  # 16K


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
# | x12 |  a2  | <unused>        |
# | x13 |  a3  | <unused>        |
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

    TODO: is the second label necessary?
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

    p.BLOB(struct.pack('<B', flags | len(name)))
    p.BLOB(struct.pack('<h', link))
    p.BLOB(name.encode())
    p.ALIGN()

    p.LABEL('code_' + name)
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
    p.ADDI('t0', 't0', 'start')
    p.JALR('zero', 't0', 0)


# code in RAM starts here
# main Forth interpreter starts here

with p.LABEL('start'):
    p.JAL('zero', 'init')
with p.LABEL('error'):
    # TODO: print error indicator ("!!" or "?" or something like that)
    pass
with p.LABEL('init'):
    # setup data stack pointer
    p.LUI(DSP, p.HI(RAM_BASE_ADDR + DATA_STACK_BASE))
    p.ADDI(DSP, DSP, p.LO(RAM_BASE_ADDR + DATA_STACK_BASE))

    # setup return stack pointer
    p.LUI(RSP, p.HI(RAM_BASE_ADDR + RETURN_STACK_BASE))
    p.ADDI(RSP, RSP, p.LO(RAM_BASE_ADDR + RETURN_STACK_BASE))

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

# main interpreter loop
with p.LABEL('interpreter'):
    p.JAL('zero', 'code_led')

with p.LABEL('token'):
    p.ADDI('t0', TOIN, 0)
    p.ADDI('t1', 'zero', 33)
with p.LABEL('token_scan'):
    # point t2 at next char
    p.ADD('t2', TIB, 't0')
    # load next char into t3
    p.LW('t3', 't2', 0)
    # check for non-printing character
    p.BLT('t3', 't1', 'token_delimiter')
    # increment offset
    p.ADDI('t0', 't0', 1)
    # scan the next char
    p.JAL('zero', 'token_scan')
with p.LABEL('token_delimiter'):
    # word starts at TIB + TOIN
    # word len is t0 - TOIN
    pass

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
    # call the building "led" word
    p.BLOB(b'led ')

    # make some numbers
    p.BLOB(b': dup sp@ @ ; ')
    p.BLOB(b': -1 dup dup nand dup dup nand nand ; ')
    p.BLOB(b': 0 -1 dup nand ; ')
    p.BLOB(b': 1 -1 dup + dup nand ; ')
    p.BLOB(b': 2 1 1 + ; ')
    p.BLOB(b': 4 2 2 + ; ')
    p.BLOB(b': 8 4 4 + ; ')
    p.BLOB(b': 12 4 8 + ; ')
    p.BLOB(b': 16 8 8 + ; ')

    # logic and arithmetic operators
    p.BLOB(b': invert dup nand ; ')
    p.BLOB(b': and nand invert ; ')
    p.BLOB(b': negate invert 1 + ; ')
    p.BLOB(b': - negate + ; ')

    # equality checks
    p.BLOB(b': = - 0= ; ')
    p.BLOB(b': <> = invert ; ')

    # stack manipulation words
    p.BLOB(b': drop dup - + ; ')
    p.BLOB(b': over sp@ 4 + @ ; ')
    p.BLOB(b': swap over over sp@ 12 + ! sp@ 4 + ! ; ')
    p.BLOB(b': nip swap drop ; ')
    p.BLOB(b': 2dup over over ; ')
    p.BLOB(b': 2drop drop drop ; ')

    # more logic
    p.BLOB(b': or invert swap invert and invert ; ')

    # left shift 1 bit
    p.BLOB(b': 2* dup + ; ')

    # paranoid align just to be safe
    p.ALIGN()


# dictionary starts here

# TODO: implement colon
with defword(p, ':', 'COLON'):
    pass

# TODO: implement semicolon
with defword(p, ';', 'SEMICOLON', flags=F_IMMEDIATE):
    pass

# this just exists to ensure that code got correctly copied from ROM to RAM
with defword(p, 'led', 'LED'):
    RCU_BASE_ADDR = 0x40021000
    RCU_APB2_ENABLE_OFFSET = 0x18
    GPIO_BASE_ADDR_C = 0x40011000
    GPIO_CTRL1_OFFSET = 0x04
    GPIO_MODE_OUT_50MHZ = 0b11
    GPIO_CTRL_OUT_PUSH_PULL = 0b00

    # load RCU base addr into t0
    p.LUI('t0', p.HI(RCU_BASE_ADDR))
    p.ADDI('t0', 't0', p.LO(RCU_BASE_ADDR))

    p.ADDI('t0', 't0', RCU_APB2_ENABLE_OFFSET)  # move t0 forward to APB2 enable register
    p.LW('t1', 't0', 0)  # load current APB2 enable config into t1

    # prepare the GPIO enable bits
    #                     | EDCBA  |
    p.ADDI('t2', 'zero', 0b00010100)

    # set GPIO clock enable bits
    p.OR('t1', 't1', 't2')
    p.SW('t0', 't1', 0)  # store the ABP2 config

    # load GPIO base addr into t0
    p.LUI('t0', p.HI(GPIO_BASE_ADDR_C))
    p.ADDI('t0', 't0', p.LO(GPIO_BASE_ADDR_C))

    # move t0 forward to control 1 register
    p.ADDI('t0', 't0', GPIO_CTRL1_OFFSET)

    p.ADDI('t1', 'zero', (GPIO_CTRL_OUT_PUSH_PULL << 2) | GPIO_MODE_OUT_50MHZ)  # load pin settings into t1
    p.SLLI('t1', 't1', 20)  # shift settings over to correct pin ((PIN - 8) * 4)

    # store the GPIO config
    p.SW('t0', 't1', 0)
    # next
    p.JAL('zero', 'next')

with defword(p, 'state', 'STATEVAR'):
    # push STATE onto stack
    p.SW(DSP, STATE, 0)
    p.ADDI(DSP, DSP, 4)
    # next
    p.JAL('zero', 'next')

with defword(p, 'tib', 'TIBVAR'):
    # push TIB onto stack
    p.SW(DSP, TIB, 0)
    p.ADDI(DSP, DSP, 4)
    # next
    p.JAL('zero', 'next')

with defword(p, '>in', 'TOINVAR'):
    # push TOIN onto stack
    p.SW(DSP, TOIN, 0)
    p.ADDI(DSP, DSP, 4)
    # next
    p.JAL('zero', 'next')

with defword(p, 'here', 'HEREVAR'):
    # push HERE onto stack
    p.SW(DSP, HERE, 0)
    p.ADDI(DSP, DSP, 4)
    # next
    p.JAL('zero', 'next')

with defword(p, 'latest', 'LATESTVAR'):
    # push LATEST onto stack
    p.SW(DSP, LATEST, 0)
    p.ADDI(DSP, DSP, 4)
    # next
    p.JAL('zero', 'next')

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
    # copy DSP into t0 and decrement to current top value
    p.ADDI('t0', DSP, 0)
    p.ADDI('t0', 't0', -4)
    # push t0 onto stack
    p.SW(DSP, 't0', 0)
    p.ADDI(DSP, DSP, 4)
    # next
    p.JAL('zero', 'next')

with defword(p, 'rp@', 'RPFETCH'):
    # copy RSP into t0 and decrement to current top value
    p.ADDI('t0', RSP, 0)
    p.ADDI('t0', 't0', -4)
    # push t0 onto stack
    p.SW(DSP, 't0', 0)
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

p.LABEL('latest')  # mark the latest builtin word
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

p.LABEL('here')  # mark the location of the next new word


with open('forth.bin', 'wb') as f:
    f.write(p.machine_code)
