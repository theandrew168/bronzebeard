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
# TODO this loop is terrible! come up with a better design for the CF
with p.LABEL('interpreter'):
    # set interpreter pointer to indirect addr back to interpreter loop
    p.LUI(IP, p.HI(RAM_BASE_ADDR))
    p.ADDI(IP, IP, p.LO(RAM_BASE_ADDR))
    p.ADDI(IP, IP, 'interpreter_addr')

    p.JAL('ra', 'token')  # call token procedure (a0 = addr, a1 = len)
    p.JAL('ra', 'lookup')  # call lookup procedure (a2 = addr)
    p.BEQ('a2', 'zero', 'error')  # error and reset if word isn't found

    # word is found and located at a2
    p.ADDI(W, 'a2', 8)  # TODO: hack to manually skip name pad bytes (word len must be <= 5)
    p.JALR('zero', W, 0)  # execute the word!

# TODO: this feels real hacky (v2: Location('interpreter'))
with p.LABEL('interpreter_addr'):
    addr = RAM_BASE_ADDR + p.labels['interpreter']
    p.BLOB(struct.pack('<I', addr))

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

with p.LABEL('lookup'):
    p.ADDI('t0', LATEST, 0)  # copy addr of latest word into t0
with p.LABEL('lookup_body'):
    p.LH('t1', 't0', 0)  # load link of current word into t1
    p.LBU('t2', 't0', 2)  # load flags / len of current word into t2
    p.ANDI('t2', 't2', LEN_MASK)  # TODO wipe out flags for now leaving word length
    p.BEQ('a1', 't2', 'lookup_strcmp')  # start strcmp if len matches
with p.LABEL('lookup_next'):
    p.BEQ('t1', 'zero', 'lookup_not_found')  # if link is zero then the word isn't found
    p.ADD('t0', 't0', 't1')  # point t0 at the next word (add the link offset)
    p.JAL('zero', 'lookup_body')  # continue the search
with p.LABEL('lookup_not_found'):
    p.ADDI('a2', 'zero', 0)  # a2 = 0
    p.JALR('zero', 'ra', 0)  # return
with p.LABEL('lookup_strcmp'):
    p.ADDI('t3', 'a0', 0)  # t3 points at name in TIB string
    p.ADDI('t4', 't0', 3)  # t4 points at name in word dict
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
    p.BLOB(b'rcu rled bled ')

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

with defword(p, 'rcu', 'RCU'):
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

# red LED: GPIO port C, ctrl 1, pin 13
# offset: ((PIN - 8) * 4) = 20
with defword(p, 'rled', 'RLED'):
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
with defword(p, 'gled', 'GLED'):
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
with defword(p, 'bled', 'BLED'):
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
with defword(p, 'usart0', 'USART0'):
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

    CLOCK = 8000000  # 8MHz
    BAUD = 115200  # 115200 bits per second
    #BAUD = 9600
    udiv = CLOCK // BAUD // 16
    udiv = 70  # 115200
    #udiv = 834  # 9600
    #intdiv = 4
    #fracdiv = 5
    #udiv = intdiv << 4 | fracdiv

    # load USART0 base address
    p.LUI('t0', p.HI(USART_BASE_ADDR_0))
    p.ADDI('t0', 't0', p.LO(USART_BASE_ADDR_0))

    # configure USART0 baud rate
    p.ADDI('t1', 't0', USART_BAUD_OFFSET)
    p.ADDI('t2', 'zero', udiv)
    p.SLLI('t2', 't2', 4)  # shift over to intdiv?
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
