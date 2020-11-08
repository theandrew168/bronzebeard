from collections import namedtuple


# definitions for the "items" that can be found in an assembly program
Instruction = namedtuple('Instruction', 'name arg0 arg1 arg2', defaults=[None, None, None])
RTypeInstruction = namedtuple('RTypeInstruction', 'name rd rs1 rs2')
ITypeInstruction = namedtuple('ITypeInstruction', 'name rd rs1 imm')
STypeInstruction = namedtuple('STypeInstruction', 'name rs1 rs2 imm')
BTypeInstruction = namedtuple('BTypeInstruction', 'name rs1 rs2 imm')
UTypeInstruction = namedtuple('UTypeInstruction', 'name rd imm')
JTypeInstruction = namedtuple('JTypeInstruction', 'name rd imm')
Label = namedtuple('Label', 'name')
Align = namedtuple('Align', 'alignment')
Blob = namedtuple('Blob', 'data')
Hi = namedtuple('Hi', 'imm')
Lo = namedtuple('Lo', 'imm')
Position = namedtuple('Position', 'label')
PositionFrom = namedtuple('PositionFrom', 'label imm')
Offset = namedtuple('Offset', 'label')
OffsetFrom = namedtuple('OffsetFrom', 'label imm')

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
# 2. Resolve Instructions to xTypeInstructions  (check name and switch, validate params)
# 3. Resolve immediates  (resolve refs to labels, error if not found, leaves integers)
# 4. Resolve relocations  (resolve Hi / Lo relocations)
# 5. Resolve registers  (resolve nice names to integers)
# 6. Assemble!  (convert everything to bytes)

def resolve_aligns_and_labels(program):
    position = 0
    labels = {}
    output = []

    for item in program:
        if isinstance(item, Label):
            labels[item.name] = position
        elif isinstance(item, Align):
            data = b''
            while position % item.alignment != 0:
                data += b'\x00'
                position += 1
            output.append(Blob(data))
        elif isinstance(item, Blob):
            position += len(item)
            output.append(item)
        else:
            position += 4
            output.append(item)

    return output, labels

def resolve_instructions(program):
    output = []

    for item in program:
        if isinstance(item, Instruction):
            name, arg0, arg1, arg2 = item
            if name in R_TYPE_INSTRUCTIONS:
                inst = RTypeInstruction(name, arg0, arg1, arg2)
                output.append(inst)
            elif name in I_TYPE_INSTRUCTIONS:
                inst = ITypeInstruction(name, arg0, arg1, arg2)
                output.append(inst)
            elif name in S_TYPE_INSTRUCTIONS:
                inst = STypeInstruction(name, arg0, arg1, arg2)
                output.append(inst)
            elif name in B_TYPE_INSTRUCTIONS:
                inst = BTypeInstruction(name, arg0, arg1, arg2)
                output.append(inst)
            elif name in U_TYPE_INSTRUCTIONS:
                inst = UTypeInstruction(name, arg0, arg1)
                output.append(inst)
            elif name in J_TYPE_INSTRUCTIONS:
                inst = JTypeInstruction(name, arg0, arg1)
                output.append(inst)
            else:
                raise RuntimeError('Invalid instruction: "{}"'.format(name))
        else:
            output.append(item)

    return output


# example program starts here
ROM_BASE_ADDR = 0x08000000
RAM_BASE_ADDR = 0x20000000

prog = []

prog += [
    # t0 = src, t1 = dest, t2 = count
    Label('copy'),
    # setup copy src (ROM_BASE_ADDR)
    Instruction('lui', 't0', Hi(ROM_BASE_ADDR)),
    Instruction('addi', 't0', 't0', Lo(ROM_BASE_ADDR)),
    # setup copy dest (RAM_BASE_ADDR)
    UTypeInstruction('lui', 't1', Hi(RAM_BASE_ADDR)),
    ITypeInstruction('addi', 't1', 't1', Lo(RAM_BASE_ADDR)),
    # setup copy count (everything up to "here" label)
    Instruction('addi', 't2', 0, Position('here'))
]

prog += [
    Label('copy_loop'),
    Instruction('beq', 't2', 'zero', 'copy_done'),
    Instruction('lw', 't3', 't0', 0),
]


from pprint import pprint
pprint(prog)

prog, labels = resolve_aligns_and_labels(prog)
pprint(prog)
pprint(labels)

prog = resolve_instructions(prog)
pprint(prog)
