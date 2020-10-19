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
R_W = 'ra'
R_IP = 'gp'
R_DSP = 'sp'
R_RSP = 'tp'


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
V_STATE = 's0'
V_TIB = 's1'
V_TOIN = 's2'
V_HERE = 's3'
V_LATEST = 's4'


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
def defword(p, name, label, flags=0):
    """
    Macro to define a Forth word. The LINK stuff is really hacky and
    I'd like to replace it with something else. The "flags" param be any
    or'd combo of the 2 F_FOO constants defined above.
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


p = asm.Program()

# code in ROM starts here
# code for copying ROM to RAM starts here

# t0 = src, t1 = dest, t2 = count
with p.LABEL('copy'):
    # setup copy src (RAM_BASE_ADDR + start)
    p.LUI('t0', p.HI(ROM_BASE_ADDR))
    p.ADDI('t0', 't0', p.LO(ROM_BASE_ADDR))
    p.ADDI('t0', 't0', 'start')

    # setup copy dest (RAM_BASE_ADDR)
    p.LUI('t1', p.HI(RAM_BASE_ADDR))
    p.ADDI('t1', 't1', p.LO(RAM_BASE_ADDR))

    # setup copy count (here - start)
    p.ADDI('t2', 'zero', 'here')
    p.ADDI('t3', 'zero', 'start')
    p.SUB('t2', 't2', 't3')

with p.LABEL('copy_loop'):
    p.BEQ('t2', 'zero', 'copy_done')
    p.LW('t3', 't0', 0)  # [src] -> t3
    p.SW('t1', 't3', 0)  # t3 -> [dest]
    p.ADDI('t0', 't0', 4)  # src += 4
    p.ADDI('t1', 't1', 4)  # dest += 4
    p.ADDI('t2', 't2', -4)  # count -= 4
    p.JAL('zero', 'copy_loop')

with p.LABEL('copy_done'):
    # jump to RAM
    p.LUI('t0', p.HI(RAM_BASE_ADDR))
    p.JALR('zero', 't0', p.LO(RAM_BASE_ADDR))


# code in RAM starts here
# main Forth interpreter starts here

with p.LABEL('start'):
    p.JAL('zero', 'init')
with p.LABEL('error'):
    # TODO: print error indicator ("!!" or something like that)
    pass
with p.LABEL('init'):
    # setup data stack pointer
    p.LUI(R_DSP, p.HI(DATA_STACK_BASE))
    p.ADDI(R_DSP, R_DSP, p.LO(DATA_STACK_BASE))

    # setup return stack pointer
    p.LUI(R_RSP, p.HI(RETURN_STACK_BASE))
    p.ADDI(R_RSP, R_RSP, p.LO(RETURN_STACK_BASE))

    # set STATE var to zero
    p.ADDI(V_STATE, 'zero', 0)

    # set TIB var to "tib" location
    p.LUI(V_TIB, p.HI(RAM_BASE_ADDR))
    p.ADDI(V_TIB, V_TIB, p.LO(RAM_BASE_ADDR))
    p.ADDI(V_TIB, V_TIB, 'tib')

    # set TOIN var to zero
    p.ADDI(V_TOIN, 'zero', 0)

    # set HERE var to "here" location
    p.LUI(V_HERE, p.HI(RAM_BASE_ADDR))
    p.ADDI(V_HERE, V_HERE, p.LO(RAM_BASE_ADDR))
    p.ADDI(V_HERE, V_HERE, 'here')

    # set LATEST var to "latest" location
    p.LUI(V_LATEST, p.HI(RAM_BASE_ADDR))
    p.ADDI(V_LATEST, V_LATEST, p.LO(RAM_BASE_ADDR))
    p.ADDI(V_LATEST, V_LATEST, 'latest')


# TODO: fill in all these goodies
p.LABEL('interpreter')
p.LABEL('token')
p.LABEL('tib')
p.LABEL('latest')
p.LABEL('here')


with open('forth.bin', 'wb') as f:
    f.write(p.machine_code)
