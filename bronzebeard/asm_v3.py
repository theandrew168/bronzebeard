from collections import namedtuple
import struct


# definitions for the "items" that can be found in an assembly program
# name: str
# rd, rs1, rs2: int, str
# imm: int, Position, Offset
# alignment: int
# data: str, bytes
# format: str
# value: int
# label: str
RTypeInstruction = namedtuple('RTypeInstruction', 'name rd rs1 rs2')
ITypeInstruction = namedtuple('ITypeInstruction', 'name rd rs1 imm')
STypeInstruction = namedtuple('STypeInstruction', 'name rs1 rs2 imm')
BTypeInstruction = namedtuple('BTypeInstruction', 'name rs1 rs2 imm')
UTypeInstruction = namedtuple('UTypeInstruction', 'name rd imm')
JTypeInstruction = namedtuple('JTypeInstruction', 'name rd imm')
Label = namedtuple('Label', 'name')
Align = namedtuple('Align', 'alignment')
Blob = namedtuple('Blob', 'data')
Pack = namedtuple('Pack', 'format imm')
Position = namedtuple('Position', 'label value')
Offset = namedtuple('Offset', 'label')
Hi = namedtuple('Hi', 'value')
Lo = namedtuple('Lo', 'value')

# name rd rs1 rs2
R_TYPE_INSTRUCTIONS = [
    'slli', 'srli', 'srai', 'add', 'sub', 'sll', 'slt',
    'sltu', 'xor', 'srl', 'sra', 'or', 'and',
]

# name rd rs1 imm
I_TYPE_INSTRUCTIONS = [
    'jalr', 'lb', 'lh', 'lw', 'lbu', 'lhu', 'addi',
    'slti', 'sltiu', 'xori', 'ori', 'andi',
]

# name rs1 rs2 imm
S_TYPE_INSTRUCTIONS = [
    'sb', 'sh', 'sw',
]

# name rs1 rs2 imm
B_TYPE_INSTRUCTIONS = [
    'beq', 'bne', 'blt', 'bge', 'bltu', 'bgeu',
]

# name rd imm
U_TYPE_INSTRUCTIONS = [
    'lui', 'auipc',
]

# name rd imm
J_TYPE_INSTRUCTIONS = [
    'jal',
]

# Passes (labels, position):
# 1. Resolve aligns and labels  (Aligns -> Blobs, store label locations into dict)
# 2. Resolve immediates  (resolve refs to labels, error if not found, leaves integers)
# 3. Resolve relocations  (resolve Hi / Lo relocations)
# 4. Resolve registers  (resolve nice names to integers)
# 5. Assemble!  (convert everything to bytes)

# these two steps occur in the same pass because they both
# require the same sort of item inspection and counting
def resolve_aligns_and_labels(program):
    position = 0
    labels = {}
    output = []

    for item in program:
        if isinstance(item, Label):
            labels[item.name] = position
        elif isinstance(item, Align):
            padding = item.alignment - (position % item.alignment)
            if padding == item.alignment:
                continue

            position += padding
            output.append(Blob(b'\x00' * padding))
        elif isinstance(item, Blob):
            position += len(item.data)
            output.append(item)
        elif isinstance(item, Pack):
            position += struct.calcsize(item.format)
            output.append(item)
        else:
            position += 4
            output.append(item)

    return output, labels

def resolve_immediates(program, labels):
    output = []
    for item in program:
        output.append(item)
    return output


# example program starts here
FORTH_SIZE = 16 * 1024  # 16K
USART_BAUD = 115200

ROM_BASE_ADDR = 0x08000000
RAM_BASE_ADDR = 0x20000000
CLOCK_FREQ = 8000000

W = 's0'
IP = 'gp'
DSP = 'sp'
RSP = 'tp'

STATE = 's1'
TIB = 's2'
TBUF = 's3'
TLEN = 's4'
TPOS = 's5'
HERE = 's6'
LATEST = 's7'

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

prog = []

prog += [
    # t0 = src, t1 = dest, t2 = count
    Label('copy'),
    # setup copy src (ROM_BASE_ADDR)
    UTypeInstruction('lui', 't0', Hi(ROM_BASE_ADDR)),
    ITypeInstruction('addi', 't0', 't0', Lo(ROM_BASE_ADDR)),
    # setup copy dest (RAM_BASE_ADDR)
    UTypeInstruction('lui', 't1', Hi(RAM_BASE_ADDR)),
    ITypeInstruction('addi', 't1', 't1', Lo(RAM_BASE_ADDR)),
    # setup copy count (everything up to "here" label)
    ITypeInstruction('addi', 't2', 0, Position('here', 0)),

    Label('token_skip_whitespace'),
    RTypeInstruction('add', 't1', TBUF, TPOS),
    ITypeInstruction('lbu', 't2', 't1', 0),
    BTypeInstruction('bge', 't2', 't0', Offset('token_scan')),
    ITypeInstruction('addi', TPOS, TPOS, 1),
    JTypeInstruction('jal', 'zero', Offset('token_skip_whitespace')),

    UTypeInstruction('lui', HERE, Hi(Position('here', RAM_BASE_ADDR))),
    ITypeInstruction('addi', HERE, HERE, Lo(Position('here', RAM_BASE_ADDR))),

    Label('interpreter_interpret'),
    JTypeInstruction('jal', 'ra', Offset('token')),

    # dub ref to interpreter hack
    Label('interpreter_addr'),
    Pack('<I', Position('interpreter_interpret', RAM_BASE_ADDR)),
    Label('interpreter_addr_addr'),
    Pack('<I', Position('interpreter_addr', RAM_BASE_ADDR)),

    Label('next'),
    ITypeInstruction('lw', W, IP, 0),
    ITypeInstruction('addi', IP, IP, 4),
    ITypeInstruction('lw', 't0', W, 0),
    ITypeInstruction('jalr', 'zero', 't0', 0),

    # literal output from defword: +
    Label('word_+'),
    Pack('<I', 0),  # link
    Pack('<B', 1),  # flags | len
    Blob('+'),  # name
    Align(4),
    Pack('<I', Position('code_+', RAM_BASE_ADDR)),  # code field
    Label('code_+'),
    ITypeInstruction('addi', DSP, DSP, -4),
    ITypeInstruction('lw', 't0', DSP, 0),
    ITypeInstruction('addi', DSP, DSP, -4),
    ITypeInstruction('lw', 't1', DSP, 0),
    RTypeInstruction('add', 't0', 't0', 't1'),
    STypeInstruction('sw', DSP, 't0', 0),
    ITypeInstruction('addi', DSP, DSP, 4),
    JTypeInstruction('jal', 'zero', Offset('next')),

    # literal output from defword: nand
    Label('latest'),
    Label('word_nand'),
    Pack('<I', Position('word_+', RAM_BASE_ADDR)),  # link
    Pack('<B', 4),  # flags | len
    Blob('nand'),  # name
    Align(4),
    Pack('<I', Position('code_nand', RAM_BASE_ADDR)),  # code field
    Label('code_nand'),
    ITypeInstruction('addi', DSP, DSP, -4),
    ITypeInstruction('lw', 't0', DSP, 0),
    ITypeInstruction('addi', DSP, DSP, -4),
    ITypeInstruction('lw', 't1', DSP, 0),
    RTypeInstruction('and', 't0', 't0', 't1'),
    ITypeInstruction('xori', 't0', 't0', -1),
    STypeInstruction('sw', DSP, 't0', 0),
    ITypeInstruction('addi', DSP, DSP, 4),
    JTypeInstruction('jal', 'zero', Offset('next')),

    Label('here'),

#    Align(FORTH_SIZE),
    Label('prelude_start'),
    Blob(': dup sp@ @ ; '),
    Blob(': -1 dup dup nand dup dup nand nand ; '),
    Label('prelude_end'),
]


from pprint import pprint

print('pass 0: raw assembly program')
pprint(prog)

print('pass 1: resolve aligns and determine label positions')
prog, labels = resolve_aligns_and_labels(prog)
pprint(prog)
pprint(labels)

print('pass 2: resolve immediates - Position / Offset')
prog = resolve_immediates(prog, labels)
pprint(prog)

print('pass 3: resolve relocations - Hi / Lo')
print('pass 4: resolve registers')
print('pass 5: assemble!')
