from simpleriscv import asm

# data stack pointer:   sp (x2)
# return stack pointer: gp (x3)

# Total RAM: 16KB
# Each section gets 4KB
INTERPRETER_BASE = 0x0000
DICTIONARY_BASE = 0x1000
DATA_STACK_BASE = 0x2000
RETURN_STACK_BASE = 0x3000

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
