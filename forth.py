from simpleriscv import asm

# Based heavily on "sectorforth" and "Moving Forth":
# https://github.com/cesarblum/sectorforth
# https://www.bradrodriguez.com/papers/moving1.htm

#       Register Assignment
# |------------------------------|
# | reg | name |   description   |
# |------------------------------|
# |  x0 | zero | always 0        |
# |  x1 |  ra  | working reg     |
# |  x2 |  sp  | data stack ptr  |
# |  x3 |  gp  | forth inst ptr  |
# |  x4 |  tp  | ret stack ptr   |
# |  x5 |  t0  | temp reg 0      |
# |  x6 |  t1  | temp reg 1      |
# |  x7 |  t2  | temp reg 2      |
# |  x8 |  s0  | STATE var       |
# |  x9 |  s1  | TIB var         |
# | x18 |  s2  | >IN var         |
# | x19 |  s3  | HERE var        |
# | x20 |  s4  | LATEST var      |
# |------------------------------|

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

#            Memory Map
#        |----------------|
#        |                |
#        |  Return Stack  |
#        |                |
# 0x3000 |----------------|
#        |                |
#        |   Data Stack   |
#        |                |
# 0x2000 |----------------|
#        |                |
#        |   Dictionary   |
#        |                |
# 0x1000 |----------------|
#        |                |
#        |   Interpreter  |
#        |                |
# 0x0000 |----------------|

# Total RAM: 16KB
# Each section gets 4KB
RETURN_STACK_BASE = 0x3000
DATA_STACK_BASE = 0x2000
DICTIONARY_BASE = 0x1000
INTERPRETER_BASE = 0x0000


PREV_WORD = None
def defword(p, name, label, flags=0):
    if len(name) > 0x1f:
        raise ValueError('Word name is longer than 0x1f (31): {}'.format(name))

    word_label = 'word_' + label
    p.LABEL(word_label)

    global PREV_WORD
    if PREV_WORD is None:
        link = 0
    else:
        link = p.labels[PREV_WORD] - p.labels[word_label]
    PREV_WORD = word_label

    p.BLOB(struct.pack('<h', link))
    p.BLOB(struct.pack('<B', len(name)))
    p.BLOB(name.encode())
    p.ALIGN()

    p.LABEL(name)

p = asm.Program()
with p.LABEL('start'):
    p.JAL('zero', 'init')
with p.LABEL('error'):
    # TODO: print error indicator ("!!" or something like that)
    pass
with p.LABEL('init'):
    # setup data stack pointer
    p.LUI('sp', p.HI(DATA_STACK_BASE))
    p.ADDI('sp', 'sp', p.LO(DATA_STACK_BASE))
    # setup return stack pointer
    p.LUI('gp', p.HI(RETURN_STACK_BASE))
    p.ADDI('gp', 'gp', p.LO(RETURN_STACK_BASE))

p.LABEL('interpreter')
p.LABEL('token')


with open('forth.bin', 'wb') as f:
    f.write(p.machine_code)
