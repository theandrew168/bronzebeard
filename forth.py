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

F_IMMEDIATE = 0b10000000
F_HIDDEN    = 0b01000000
LEN_MASK    = 0b00011111

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
    # TODO: this is just too hacky: doesn't respect defer, digs into labels...
    # Feature: deferred blob that refs a label, specify the size? 8, 16, 32, etc
    #   but then it also updates a var? almost seems cleaner to just collect
    #   the "normal" segments (label, inst, blob, align) into a list and make
    #   a first pass that just collects label locations. then the second pass
    #   handle "macros" and does the actual assembling? Second pass can include
    #   an API for querying label locations since they'll all be present.
    #   Immediate values can also use this. Maybe have two functions, one for
    #   raw location and one for relative offset? (for PIC on jump / branch insts)
    global LINK
    if LINK is None:
        link = 0
    else:
        link = p.labels[LINK] - p.labels[word_label]
    LINK = word_label

    p.BLOB(struct.pack('<h', link))
    p.BLOB(struct.pack('<B', flags | len(name)))
    p.BLOB(name.encode())
    p.ALIGN()

    p.LABEL('code_' + name)
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

    # set working register to zero
    p.ADDI(W, 'zero', 0)

    # set interpreter pointer to "interpreter" location
    p.LUI(IP, p.HI(RAM_BASE_ADDR))
    p.ADDI(IP, IP, p.LO(RAM_BASE_ADDR))
    p.ADDI(IP, IP, 'interpreter')

    # set STATE var to zero
    p.ADDI(STATE, 'zero', 0)

    # set TIB var to "tib" location
    p.LUI(TIB, p.HI(RAM_BASE_ADDR))
    p.ADDI(TIB, TIB, p.LO(RAM_BASE_ADDR))
    p.ADDI(TIB, TIB, 'tib')
    # TODO: fill TIB with zeroes

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
    p.JAL('ra', 'token')  # call token procedure (a0 = addr, a1 = len)
    p.ADDI('t0', 'zero', 3)
    p.BEQ('a1', 't0', 'code_led')
with p.LABEL('search'):
    p.ADDI('t0', LATEST, 0)  # copy addr of latest word into t0
with p.LABEL('search_loop'):
    p.LH('t1', 't0', 0)  # load link of current word into t1
    p.LBU('t2', 't0', 2)  # load flags / len of current word into t2
    p.ANDI('t2', 't2', LEN_MASK)  # TODO wipe out flags for now leaving word length
    p.BEQ('a1', 't2', 'search_compare')  # continue the search if length matches
    p.BEQ('t1', 'zero', 'error')  # if link is zero then the word isn't found: error and reset
    p.ADD('t0', 't0', 't1')  # point t0 at the next word (add the link offset)
    p.JAL('zero', 'search_loop')  # continue the search
with p.LABEL('search_compare_next'):
    p.ADDI('t2', 't2', -1)  # dec len by 1
    p.BEQ('t2', 'zero', 'search_found')  # if all chars have been checked, its a match!
    p.ADDI('t3', 't3', 1)  # inc TIB ptr
    p.ADDI('t4', 't4', 1)  # inc word dict ptr
    p.JAL('zero', 'search_compare_loop')  # check next char
with p.LABEL('search_compare'):
    p.ADDI('t3', 'a0', 0)  # t3 points at name in TIB string
    p.ADDI('t4', 't0', 3)  # t4 points at name in word dict
with p.LABEL('search_compare_loop'):
    p.LBU('t5', 't3', 0)  # load TIB char into t5
    p.LBU('t6', 't4', 0)  # load dict char into t6
    p.BEQ('t5', 't6', 'search_compare_next')  # continue comparing if current chars match
    p.BEQ('t1', 'zero', 'error')  # if link is zero then the word isn't found: error and reset
    p.ADD('t0', 't0', 't1')  # point t0 at the next word (add the link offset)
    p.JAL('zero', 'search_loop')  # continue the search
with p.LABEL('search_found'):
    # word is found and located at t0
    p.ADDI(W, 't0', 8)  # TODO: hack to manually skip name pad bytes
    p.JAL('zero', 'next')  # execute the word!

# TODO: handle running off the TIB (max 1024 bytes or something)
with p.LABEL('token'):
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
    # call the builtin "led" word
    p.BLOB(b'  led ')

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
#with defword(p, ':', 'COLON'):
#    pass

# TODO: implement semicolon
#with defword(p, ';', 'SEMICOLON', flags=F_IMMEDIATE):
#    pass

p.LABEL('latest')  # mark the latest builtin word
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

#with defword(p, 'state', 'STATEVAR'):
#    # push STATE onto stack
#    p.SW(DSP, STATE, 0)
#    p.ADDI(DSP, DSP, 4)
#    # next
#    p.JAL('zero', 'next')
#
#with defword(p, 'tib', 'TIBVAR'):
#    # push TIB onto stack
#    p.SW(DSP, TIB, 0)
#    p.ADDI(DSP, DSP, 4)
#    # next
#    p.JAL('zero', 'next')
#
#with defword(p, '>in', 'TOINVAR'):
#    # push TOIN onto stack
#    p.SW(DSP, TOIN, 0)
#    p.ADDI(DSP, DSP, 4)
#    # next
#    p.JAL('zero', 'next')
#
#with defword(p, 'here', 'HEREVAR'):
#    # push HERE onto stack
#    p.SW(DSP, HERE, 0)
#    p.ADDI(DSP, DSP, 4)
#    # next
#    p.JAL('zero', 'next')
#
#with defword(p, 'latest', 'LATESTVAR'):
#    # push LATEST onto stack
#    p.SW(DSP, LATEST, 0)
#    p.ADDI(DSP, DSP, 4)
#    # next
#    p.JAL('zero', 'next')
#
#with defword(p, '@', 'FETCH'):
#    # pop address into t0
#    p.ADDI(DSP, DSP, -4)
#    p.LW('t0', DSP, 0)
#    # load value from address
#    p.LW('t0', 't0', 0)
#    # push value onto stack
#    p.SW(DSP, 't0', 0)
#    p.ADDI(DSP, DSP, 4)
#    # next
#    p.JAL('zero', 'next')
#
#with defword(p, '!', 'STORE'):
#    # pop address into t0
#    p.ADDI(DSP, DSP, -4)
#    p.LW('t0', DSP, 0)
#    # pop value into t1
#    p.ADDI(DSP, DSP, -4)
#    p.LW('t1', DSP, 0)
#    # store value to address
#    p.SW('t0', 't1', 0)
#    # next
#    p.JAL('zero', 'next')
#
#with defword(p, 'sp@', 'SPFETCH'):
#    # copy DSP into t0 and decrement to current top value
#    p.ADDI('t0', DSP, 0)
#    p.ADDI('t0', 't0', -4)
#    # push t0 onto stack
#    p.SW(DSP, 't0', 0)
#    p.ADDI(DSP, DSP, 4)
#    # next
#    p.JAL('zero', 'next')
#
#with defword(p, 'rp@', 'RPFETCH'):
#    # copy RSP into t0 and decrement to current top value
#    p.ADDI('t0', RSP, 0)
#    p.ADDI('t0', 't0', -4)
#    # push t0 onto stack
#    p.SW(DSP, 't0', 0)
#    p.ADDI(DSP, DSP, 4)
#    # next
#    p.JAL('zero', 'next')
#
#with defword(p, '0=', 'ZEROEQUALS'):
#    # pop value into t0
#    p.ADDI(DSP, DSP, -4)
#    p.LW('t0', DSP, 0)
#    # check equality between t0 and 0
#    p.ADDI('t1', 'zero', 0)
#    p.BNE('t0', 'zero', 'notzero')
#    p.ADDI('t1', 't1', -1)  # -1 if zero, 0 otherwise
#with p.LABEL('notzero'):
#    # push result of comparison onto stack
#    p.SW(DSP, 't1', 0)
#    p.ADDI(DSP, DSP, 4)
#    # next
#    p.JAL('zero', 'next')
#
#with defword(p, '+', 'PLUS'):
#    # pop first value into t0
#    p.ADDI(DSP, DSP, -4)
#    p.LW('t0', DSP, 0)
#    # pop second value into t1
#    p.ADDI(DSP, DSP, -4)
#    p.LW('t1', DSP, 0)
#    # add the two together into t0
#    p.ADD('t0', 't0', 't1')
#    # push resulting sum onto stack
#    p.SW(DSP, 't0', 0)
#    p.ADDI(DSP, DSP, 4)
#    # next
#    p.JAL('zero', 'next')
#
#p.LABEL('latest')  # mark the latest builtin word
#with defword(p, 'nand', 'NAND'):
#    # pop first value into t0
#    p.ADDI(DSP, DSP, -4)
#    p.LW('t0', DSP, 0)
#    # pop second value into t1
#    p.ADDI(DSP, DSP, -4)
#    p.LW('t1', DSP, 0)
#    # AND the two together into t0
#    p.AND('t0', 't0', 't1')
#    # NOT the value in t0
#    p.XORI('t0', 't0', -1)
#    # push resulting value onto stack
#    p.SW(DSP, 't0', 0)
#    p.ADDI(DSP, DSP, 4)
#    # next
#    p.JAL('zero', 'next')

p.LABEL('here')  # mark the location of the next new word


with open('forth.bin', 'wb') as f:
    f.write(p.machine_code)
