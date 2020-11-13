from ctypes import c_uint32
from functools import partial
import struct


# mapping of register names to their corresponding 5-bit integer values
REGISTERS = {
    'x0': 0, 'zero': 0,
    'x1': 1, 'ra': 1,
    'x2': 2, 'sp': 2,
    'x3': 3, 'gp': 3,
    'x4': 4, 'tp': 4,
    'x5': 5, 't0': 5,
    'x6': 6, 't1': 6,
    'x7': 7, 't2': 7,
    'x8': 8, 's0': 8, 'fp': 8,
    'x9': 9, 's1': 9,
    'x10': 10, 'a0': 10,
    'x11': 11, 'a1': 11,
    'x12': 12, 'a2': 12,
    'x13': 13, 'a3': 13,
    'x14': 14, 'a4': 14,
    'x15': 15, 'a5': 15,
    'x16': 16, 'a6': 16,
    'x17': 17, 'a7': 17,
    'x18': 18, 's2': 18,
    'x19': 19, 's3': 19,
    'x20': 20, 's4': 20,
    'x21': 21, 's5': 21,
    'x22': 22, 's6': 22,
    'x23': 23, 's7': 23,
    'x24': 24, 's8': 24,
    'x25': 25, 's9': 25,
    'x26': 26, 's10': 26,
    'x27': 27, 's11': 27,
    'x28': 28, 't3': 28,
    'x29': 29, 't4': 29,
    'x30': 30, 't5': 30,
    'x31': 31, 't6': 31,
}


def resolve_register(reg):
    # check if register corresponds to a valid name
    if reg in REGISTERS:
        reg = REGISTERS[reg]

    # ensure register is a number
    try:
        reg = int(reg)
    except ValueError:
        raise ValueError('Register is not a number or valid name: {}'.format(reg))

    # ensure register is between 0 and 31
    if reg < 0 or reg > 31:
        raise ValueError('Register must be between 0 and 31: {}'.format(reg))

    return reg


def r_type(rd, rs1, rs2, opcode, funct3, funct7):
    rd = resolve_register(rd)
    rs1 = resolve_register(rs1)
    rs2 = resolve_register(rs2)

    code = 0
    code |= opcode
    code |= rd << 7
    code |= funct3 << 12
    code |= rs1 << 15
    code |= rs2 << 20
    code |= funct7 << 25

    return struct.pack('<I', code)


def i_type(rd, rs1, imm, opcode, funct3):
    rd = resolve_register(rd)
    rs1 = resolve_register(rs1)

    if imm < -0x800 or imm > 0x7ff:
        raise ValueError('12-bit immediate must be between -0x800 (-2048) and 0x7ff (2047): {}'.format(imm))

    imm = c_uint32(imm).value & 0b111111111111

    code = 0
    code |= opcode
    code |= rd << 7
    code |= funct3 << 12
    code |= rs1 << 15
    code |= imm << 20

    return struct.pack('<I', code)


def s_type(rs1, rs2, imm, opcode, funct3):
    rs1 = resolve_register(rs1)
    rs2 = resolve_register(rs2)

    if imm < -0x800 or imm > 0x7ff:
        raise ValueError('12-bit immediate must be between -0x800 (-2048) and 0x7ff (2047): {}'.format(imm))

    imm = c_uint32(imm).value & 0b111111111111

    imm_11_5 = (imm >> 5) & 0b1111111
    imm_4_0 = imm & 0b11111

    code = 0
    code |= opcode
    code |= imm_4_0 << 7
    code |= funct3 << 12
    code |= rs1 << 15
    code |= rs2 << 20
    code |= imm_11_5 << 25

    return struct.pack('<I', code)


def b_type(rs1, rs2, imm, opcode, funct3):
    rs1 = resolve_register(rs1)
    rs2 = resolve_register(rs2)

    if imm < -0x1000 or imm > 0x0fff:
        raise ValueError('12-bit multiple of 2 immediate must be between -0x1000 (-4096) and 0x0fff (4095): {}'.format(imm))
    if imm % 2 == 1:
        raise ValueError('12-bit multiple of 2 immediate must be a muliple of 2: {}'.format(imm))

    imm = imm // 2
    imm = c_uint32(imm).value & 0b111111111111

    imm_12 = (imm >> 11) & 0b1
    imm_11 = (imm >> 10) & 0b1
    imm_10_5 = (imm >> 4) & 0b111111
    imm_4_1 = imm & 0b1111

    code = 0
    code |= opcode
    code |= imm_11 << 7
    code |= imm_4_1 << 8
    code |= funct3 << 12
    code |= rs1 << 15
    code |= rs2 << 20
    code |= imm_10_5 << 25
    code |= imm_12 << 31

    return struct.pack('<I', code)


def u_type(rd, imm, opcode):
    rd = resolve_register(rd)

    if imm < -0x80000 or imm > 0x7ffff:
        raise ValueError('20-bit immediate must be between -0x80000 (-524288) and 0x7ffff (524287): {}'.format(imm))

    imm = c_uint32(imm).value & 0b11111111111111111111

    code = 0
    code |= opcode
    code |= rd << 7
    code |= imm << 12

    return struct.pack('<I', code)


def j_type(rd, imm, opcode):
    rd = resolve_register(rd)

    if imm < -0x100000 or imm > 0x0fffff:
        raise ValueError('20-bit multiple of 2 immediate must be between -0x100000 (-1048576) and 0x0fffff (1048575): {}'.format(imm))
    if imm % 2 == 1:
        raise ValueError('20-bit multiple of 2 immediate must be a muliple of 2: {}'.format(imm))

    imm = imm // 2
    imm = c_uint32(imm).value & 0b11111111111111111111

    imm_20 = (imm >> 19) & 0b1
    imm_19_12 = (imm >> 11) & 0b11111111
    imm_11 = (imm >> 10) & 0b1
    imm_10_1 = imm & 0b1111111111

    code = 0
    code |= opcode
    code |= rd << 7
    code |= imm_19_12 << 12
    code |= imm_11 << 20
    code |= imm_10_1 << 21
    code |= imm_20 << 31

    return struct.pack('<I', code)


LUI = partial(u_type, opcode=0b0110111)
AUIPC = partial(u_type, opcode=0b0010111)
JAL = partial(j_type, opcode=0b1101111)
JALR = partial(i_type, opcode=0b1100111, funct3=0b000)
BEQ = partial(b_type, opcode=0b1100011, funct3=0b000)
BNE = partial(b_type, opcode=0b1100011, funct3=0b001)
BLT = partial(b_type, opcode=0b1100011, funct3=0b100)
BGE = partial(b_type, opcode=0b1100011, funct3=0b101)
BLTU = partial(b_type, opcode=0b1100011, funct3=0b110)
BGEU = partial(b_type, opcode=0b1100011, funct3=0b111)
LB = partial(i_type, opcode=0b0000011, funct3=0b000)
LH = partial(i_type, opcode=0b0000011, funct3=0b001)
LW = partial(i_type, opcode=0b0000011, funct3=0b010)
LBU = partial(i_type, opcode=0b0000011, funct3=0b100)
LHU = partial(i_type, opcode=0b0000011, funct3=0b101)
SB = partial(s_type, opcode=0b0100011, funct3=0b000)
SH = partial(s_type, opcode=0b0100011, funct3=0b001)
SW = partial(s_type, opcode=0b0100011, funct3=0b010)
ADDI = partial(i_type, opcode=0b0010011, funct3=0b000)
SLTI = partial(i_type, opcode=0b0010011, funct3=0b010)
SLTIU = partial(i_type, opcode=0b0010011, funct3=0b011)
XORI = partial(i_type, opcode=0b0010011, funct3=0b100)
ORI = partial(i_type, opcode=0b0010011, funct3=0b110)
ANDI = partial(i_type, opcode=0b0010011, funct3=0b111)
SLLI = partial(r_type, opcode=0b0010011, funct3=0b001, funct7=0b0000000)
SRLI = partial(r_type, opcode=0b0010011, funct3=0b101, funct7=0b0000000)
SRAI = partial(r_type, opcode=0b0010011, funct3=0b101, funct7=0b0100000)
ADD = partial(r_type, opcode=0b0110011, funct3=0b000, funct7=0b0000000)
SUB = partial(r_type, opcode=0b0110011, funct3=0b000, funct7=0b0100000)
SLL = partial(r_type, opcode=0b0110011, funct3=0b001, funct7=0b0000000)
SLT = partial(r_type, opcode=0b0110011, funct3=0b010, funct7=0b0000000)
SLTU = partial(r_type, opcode=0b0110011, funct3=0b011, funct7=0b0000000)
XOR = partial(r_type, opcode=0b0110011, funct3=0b100, funct7=0b0000000)
SRL = partial(r_type, opcode=0b0110011, funct3=0b101, funct7=0b0000000)
SRA = partial(r_type, opcode=0b0110011, funct3=0b101, funct7=0b0100000)
OR = partial(r_type, opcode=0b0110011, funct3=0b110, funct7=0b0000000)
AND = partial(r_type, opcode=0b0110011, funct3=0b111, funct7=0b0000000)

# mapping of instruction names to their corresponding encode funcs
INSTRUCTIONS = {
    'lui': LUI,
    'auipc': AUIPC,
    'jal': JAL,
    'jalr': JALR,
    'beq': BEQ,
    'bne': BNE,
    'blt': BLT,
    'bge': BGE,
    'bltu': BLTU,
    'bgeu': BGEU,
    'lb': LB,
    'lh': LH,
    'lw': LW,
    'lbu': LBU,
    'lhu': LHU,
    'sb': SB,
    'sh': SH,
    'sw': SW,
    'addi': ADDI,
    'slti': SLTI,
    'sltiu': SLTIU,
    'xori': XORI,
    'ori': ORI,
    'andi': ANDI,
    'slli': SLLI,
    'srli': SRLI,
    'srai': SRAI,
    'add': ADD,
    'sub': SUB,
    'sll': SLL,
    'slt': SLT,
    'sltu': SLTU,
    'xor': XOR,
    'srl': SRL,
    'sra': SRA,
    'or': OR,
    'and': AND,
}


class RTypeInstruction:
    def __init__(self, name, rd, rs1, rs2):
        self.name = name
        self.rd = rd
        self.rs1 = rs1
        self.rs2 = rs2
    def __bytes__(self):
        encode_func = INSTRUCTIONS[self.name]
        return encode_func(self.rd, self.rs1, self.rs2)
    def __len__(self):
        return 4
    def __repr__(self):
        return 'RTypeInstruction({}, {}, {}, {})'.format(self.name, self.rd, self.rs1, self.rs2)

class ITypeInstruction:
    def __init__(self, name, rd, rs1, imm):
        self.name = name
        self.rd = rd
        self.rs1 = rs1
        self.imm = imm
    def __bytes__(self):
        encode_func = INSTRUCTIONS[self.name]
        return encode_func(self.rd, self.rs1, self.imm)
    def __len__(self):
        return 4
    def __repr__(self):
        return 'ITypeInstruction({}, {}, {}, {})'.format(self.name, self.rd, self.rs1, self.imm)

class STypeInstruction:
    def __init__(self, name, rs1, rs2, imm):
        self.name = name
        self.rs1 = rs1
        self.rs2 = rs2
        self.imm = imm
    def __bytes__(self):
        encode_func = INSTRUCTIONS[self.name]
        return encode_func(self.rs1, self.rs2, self.imm)
    def __len__(self):
        return 4
    def __repr__(self):
        return 'STypeInstruction({}, {}, {}, {})'.format(self.name, self.rs1, self.rs2, self.imm)

class BTypeInstruction:
    def __init__(self, name, rs1, rs2, imm):
        self.name = name
        self.rs1 = rs1
        self.rs2 = rs2
        self.imm = imm
    def __bytes__(self):
        encode_func = INSTRUCTIONS[self.name]
        return encode_func(self.rs1, self.rs2, self.imm)
    def __len__(self):
        return 4
    def __repr__(self):
        return 'BTypeInstruction({}, {}, {}, {})'.format(self.name, self.rs1, self.rs2, self.imm)

class UTypeInstruction:
    def __init__(self, name, rd, imm):
        self.name = name
        self.rd = rd
        self.imm = imm
    def __bytes__(self):
        encode_func = INSTRUCTIONS[self.name]
        return encode_func(self.rd, self.imm)
    def __len__(self):
        return 4
    def __repr__(self):
        return 'UTypeInstruction({}, {}, {})'.format(self.name, self.rd, self.imm)

class JTypeInstruction:
    def __init__(self, name, rd, imm):
        self.name = name
        self.rd = rd
        self.imm = imm
    def __bytes__(self):
        encode_func = INSTRUCTIONS[self.name]
        return encode_func(self.rd, self.imm)
    def __len__(self):
        return 4
    def __repr__(self):
        return 'JTypeInstruction({}, {}, {})'.format(self.name, self.rd, self.imm)

class Blob:
    def __init__(self, data):
        self.data = data
    def __bytes__(self):
        return self.data
    def __len__(self):
        return len(self.data)
    def __repr__(self):
        return 'Blob({})'.format(self.data)

class Pack:
    def __init__(self, fmt, imm):
        self.fmt = fmt
        self.imm = imm
    def __bytes__(self):
        return struct.pack(self.fmt, self.imm)
    def __len__(self):
        return struct.calcsize(self.fmt)
    def __repr__(self):
        return 'Pack({}, {})'.format(self.fmt, self.imm)

class Label:
    def __init__(self, name):
        self.name = name
    def __len__(self):
        return 0
    def __repr__(self):
        return 'Label({})'.format(self.name)

class Align:
    def __init__(self, alignment):
        self.alignment = alignment
    def __repr__(self):
        return 'Align({})'.format(self.alignment)

class Position:
    def __init__(self, label, base):
        self.label = label
        self.base = base
    def __repr__(self):
        return 'Position({}, 0x{:08x})'.format(self.label, self.base)

class Offset:
    def __init__(self, label):
        self.label = label
    def __repr__(self):
        return 'Offset({})'.format(self.label)

class Hi:
    def __init__(self, imm):
        self.imm = imm
    def __repr__(self):
        return 'Hi({})'.format(self.imm)

class Lo:
    def __init__(self, imm):
        self.imm = imm
    def __repr__(self):
        return 'Lo({})'.format(self.imm)

# Passes (labels, position):
# 1. Resolve aligns  (convert aligns to blobs based on position)
# 2. Resolve labels  (store label locations into dict)
# 3. Resolve immediates  (resolve refs to labels, error if not found, leaves integers)
# 4. Resolve relocations  (resolve Hi / Lo relocations)
# 5. Assemble!  (convert everything to bytes)

def sign_extend(value, bits):
    sign_bit = 1 << (bits - 1)
    return (value & (sign_bit - 1)) - (value & sign_bit)

def relocate_hi(imm):
    if imm & 0x800:
        imm += 2**12
    return sign_extend((imm >> 12) & 0x000fffff, 20)

def relocate_lo(imm):
    return sign_extend(imm & 0x00000fff, 12)

def parse_assembly(assembly):
    return []

def resolve_aligns(program):
    position = 0
    output = []

    for item in program:
        if type(item) == Align:
            padding = item.alignment - (position % item.alignment)
            if padding == item.alignment:
                continue

            position += padding
            output.append(Blob(b'\x00' * padding))
        else:
            position += len(item)
            output.append(item)

    return output

def resolve_labels(program):
    position = 0
    output = []
    labels = {}

    for item in program:
        if type(item) == Label:
            labels[item.name] = position
        else:
            position += len(item)
            output.append(item)

    return output, labels

def resolve_immediates(program, labels):
    position = 0
    output = []

    immediates = [
        ITypeInstruction,
        STypeInstruction,
        BTypeInstruction,
        UTypeInstruction,
        JTypeInstruction,
        Pack,
    ]

    # TODO: way too ugly
    for item in program:
        if type(item) in immediates:
            imm = item.imm
            if type(imm) == Position:
                dest = labels[imm.label]
                base = imm.base
                item.imm = dest + base
            elif type(imm) == Offset:
                dest = labels[imm.label]
                item.imm = dest - position
            elif type(imm) in [Hi, Lo]:
                imm = item.imm.imm
                if type(imm) == Position:
                    dest = labels[imm.label]
                    base = imm.base
                    item.imm.imm = dest + base
                elif type(imm) == Offset:
                    dest = labels[imm.label]
                    item.imm.imm = dest - position

        position += len(item)
        output.append(item)

    return output

def resolve_relocations(program):
    output = []

    immediates = [
        ITypeInstruction,
        STypeInstruction,
        BTypeInstruction,
        UTypeInstruction,
        JTypeInstruction,
        Pack,
    ]

    for item in program:
        if type(item) in immediates:
            if type(item.imm) == Hi:
                item.imm = relocate_hi(item.imm.imm)
            elif type(item.imm) == Lo:
                item.imm = relocate_lo(item.imm.imm)

        output.append(item)

    return output

def assemble(program):
    output = b''

    for item in program:
        output += bytes(item)

    return output

ROM_BASE_ADDR = 0x08000000
RAM_BASE_ADDR = 0x20000000

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

prog = [
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
    Label('token_scan'),
    Label('token'),

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
    Blob(b'+'),  # name
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
    Blob(b'nand'),  # name
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
    Blob(b': dup sp@ @ ; '),
    Blob(b': -1 dup dup nand dup dup nand nand ; '),
    Label('prelude_end'),
]


from pprint import pprint

print('pass 0: raw assembly program')
pprint(prog)

print('pass 1: resolve aligns')
prog = resolve_aligns(prog)
pprint(prog)

print('pass 2: resolve labels')
prog, labels = resolve_labels(prog)
pprint(prog)
pprint(labels)

print('pass 3: resolve immediates - Position / Offset')
prog = resolve_immediates(prog, labels)
pprint(prog)

print('pass 4: resolve relocations - Hi / Lo')
prog = resolve_relocations(prog)
pprint(prog)

print('pass 5: assemble!')
prog = assemble(prog)
pprint(prog)
