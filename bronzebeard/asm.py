from collections import namedtuple
from ctypes import c_uint32
from functools import partial
import re
import struct
import sys

from pprint import pprint


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


def lookup_register(reg):
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
    rd = lookup_register(rd)
    rs1 = lookup_register(rs1)
    rs2 = lookup_register(rs2)

    code = 0
    code |= opcode
    code |= rd << 7
    code |= funct3 << 12
    code |= rs1 << 15
    code |= rs2 << 20
    code |= funct7 << 25

    return struct.pack('<I', code)


def i_type(rd, rs1, imm, opcode, funct3):
    rd = lookup_register(rd)
    rs1 = lookup_register(rs1)

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
    rs1 = lookup_register(rs1)
    rs2 = lookup_register(rs2)

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
    rs1 = lookup_register(rs1)
    rs2 = lookup_register(rs2)

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
    rd = lookup_register(rd)

    if imm < -0x80000 or imm > 0x7ffff:
        raise ValueError('20-bit immediate must be between -0x80000 (-524288) and 0x7ffff (524287): {}'.format(imm))

    imm = c_uint32(imm).value & 0b11111111111111111111

    code = 0
    code |= opcode
    code |= rd << 7
    code |= imm << 12

    return struct.pack('<I', code)


def j_type(rd, imm, opcode):
    rd = lookup_register(rd)

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

R_TYPE_INSTRUCTIONS = {
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

I_TYPE_INSTRUCTIONS = {
    'jalr': JALR,
    'lb': LB,
    'lh': LH,
    'lw': LW,
    'lbu': LBU,
    'lhu': LHU,
    'addi': ADDI,
    'slti': SLTI,
    'sltiu': SLTIU,
    'xori': XORI,
    'ori': ORI,
    'andi': ANDI,
}

S_TYPE_INSTRUCTIONS = {
    'sb': SB,
    'sh': SH,
    'sw': SW,
}

B_TYPE_INSTRUCTIONS = {
    'beq': BEQ,
    'bne': BNE,
    'blt': BLT,
    'bge': BGE,
    'bltu': BLTU,
    'bgeu': BGEU,
}

U_TYPE_INSTRUCTIONS = {
    'lui': LUI,
    'auipc': AUIPC,
}

J_TYPE_INSTRUCTIONS = {
    'jal': JAL,
}

INSTRUCTIONS = {}
INSTRUCTIONS.update(R_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(I_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(S_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(B_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(U_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(J_TYPE_INSTRUCTIONS)

# Arg types:
#   rd, rs1, rs2: int, str
#   name: str
#   imm: Position, Offset, Hi, Lo, expr
#   alignment: int
#   data: bytes
#   fmt: str
#   label: str
#   expr: simple python expression

# items
RTypeInstruction = namedtuple('RTypeInstruction', 'name rd rs1 rs2')  # 4 bytes
ITypeInstruction = namedtuple('ITypeInstruction', 'name rd rs1 imm')  # 4 bytes
STypeInstruction = namedtuple('STypeInstruction', 'name rs1 rs2 imm')  # 4 bytes
BTypeInstruction = namedtuple('BTypeInstruction', 'name rs1 rs2 imm')  # 4 bytes
UTypeInstruction = namedtuple('UTypeInstruction', 'name rd imm')  # 4 bytes
JTypeInstruction = namedtuple('JTypeInstruction', 'name rd imm')  # 4 bytes
Constant = namedtuple('Constant', 'name expr')  # 0 bytes
Label = namedtuple('Label', 'name')  # 0 bytes
Align = namedtuple('Align', 'alignment')  # 0-3 bytes
Pack = namedtuple('Pack', 'fmt imm')  # struct.calcsize(fmt) bytes
Blob = namedtuple('Blob', 'data')  # len(data) bytes

# immediates
Position = namedtuple('Position', 'label expr')
Offset = namedtuple('Offset', 'label')
Hi = namedtuple('Hi', 'expr')
Lo = namedtuple('Lo', 'expr')

def sign_extend(value, bits):
    sign_bit = 1 << (bits - 1)
    return (value & (sign_bit - 1)) - (value & sign_bit)

def relocate_hi(imm):
    if imm & 0x800:
        imm += 2**12
    return sign_extend((imm >> 12) & 0x000fffff, 20)

def relocate_lo(imm):
    return sign_extend(imm & 0x00000fff, 12)

def lex_assembly(assembly):
    # strip comments
    assembly = re.sub(r'#.*?$', r'', assembly, flags=re.MULTILINE)

    # split into lines
    lines = assembly.splitlines()

    # strip whitespace
    lines = [line.strip() for line in lines]

    # skip empty lines
    lines = [line for line in lines if len(line) > 0]

    # split lines into tokens
    items = [re.split(r'[\s,()]+', line) for line in lines]

    # remove empty tokens
    for item in items:
        while '' in item:
            item.remove('')

    return items

def parse_assembly(items):
    def parse_immediate(imm):
        if imm[0].lower() == '%position':
            _, label, *expr = imm
            expr = ' '.join(expr)
            return Position(label, expr)
        elif imm[0].lower() == '%offset':
            _, label = imm
            return Offset(label)
        elif imm[0].lower() == '%hi':
            _, *expr = imm
            expr = ' '.join(expr)
            return Hi(expr)
        elif imm[0].lower() == '%lo':
            _, *expr = imm
            expr = ' '.join(expr)
            return Lo(expr)
        else:
            return ' '.join(imm)

    program = []
    for item in items:
        # labels
        if len(item) == 1 and item[0].endswith(':'):
            label = item[0]
            label = label.rstrip(':')
            item = Label(label)
            program.append(item)
        # constants
        elif len(item) >= 3 and item[1] == '=':
            name, _, *expr = item
            expr = ' '.join(expr)
            item = Constant(name, expr)
            program.append(item)
        # aligns
        elif item[0].lower() == 'align':
            _, alignment = item
            alignment = int(alignment)
            item = Align(alignment)
            program.append(item)
        # packs
        elif item[0].lower() == 'pack':
            _, fmt, *imm = item
            imm = parse_immediate(imm)
            item = Pack(fmt, imm)
            program.append(item)
        # blobs
        elif item[0].lower() == 'blob':
            _, data = item
            data = data.encode()
            item = Blob(data)
            program.append(item)
        # r-type instructions
        elif item[0].lower() in R_TYPE_INSTRUCTIONS:
            name, rd, rs1, rs2 = item
            item = RTypeInstruction(name, rd, rs1, rs2)
            program.append(item)
        # i-type instructions
        elif item[0].lower() in I_TYPE_INSTRUCTIONS:
            name, rd, rs1, *imm = item
            imm = parse_immediate(imm)
            item = ITypeInstruction(name, rd, rs1, imm)
            program.append(item)
        # s-type instructions
        elif item[0].lower() in S_TYPE_INSTRUCTIONS:
            name, rs1, rs2, *imm = item
            imm = parse_immediate(imm)
            item = STypeInstruction(name, rs1, rs2, imm)
            program.append(item)
        # b-type instructions
        elif item[0].lower() in B_TYPE_INSTRUCTIONS:
            name, rs1, rs2, *imm = item
            imm = parse_immediate(imm)
            item = BTypeInstruction(name, rs1, rs2, imm)
            program.append(item)
        # u-type instructions
        elif item[0].lower() in U_TYPE_INSTRUCTIONS:
            name, rd, *imm = item
            imm = parse_immediate(imm)
            item = UTypeInstruction(name, rd, imm)
            program.append(item)
        # j-type instructions
        elif item[0].lower() in J_TYPE_INSTRUCTIONS:
            name, rd, *imm = item
            imm = parse_immediate(imm)
            item = JTypeInstruction(name, rd, imm)
            program.append(item)
        else:
            raise SystemExit('invalid item: {}'.format(' '.join(item)))

    return program

def resolve_constants(program):
    # exclude Python builtins from eval env (safer?)
    context = {
        '__builtins__': None,
    }

    output = []
    for item in program:
        if type(item) == Constant:
            context[item.name] = eval(item.expr, context)
        else:
            output.append(item)

    return output, context

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
        elif type(item) == Pack:
            position += struct.calcsize(item.fmt)
            output.append(item)
        elif type(item) == Blob:
            position += len(item.data)
            output.append(item)
        elif type(item) == Label:
            output.append(item)
        else:
            position += 4
            output.append(item)

    return output

def resolve_labels(program):
    position = 0
    labels = {}

    output = []
    for item in program:
        if type(item) == Label:
            labels[item.name] = position
        elif type(item) == Pack:
            position += struct.calcsize(item.fmt)
            output.append(item)
        elif type(item) == Blob:
            position += len(item.data)
            output.append(item)
        else:
            position += 4
            output.append(item)

    return output, labels

def resolve_registers(program, context):
    # helper functions for resolving register names (could be a constant)
    def resolve_register(register, context):
        if register in context:
            return context[register]
        return register

    output = []
    for item in program:
        if type(item) == RTypeInstruction:
            name, rd, rs1, rs2 = item
            rd = resolve_register(rd, context)
            rs1 = resolve_register(rs1, context)
            rs2 = resolve_register(rs2, context)
            inst = RTypeInstruction(name, rd, rs1, rs2)
            output.append(inst)
        elif type(item) == ITypeInstruction:
            name, rd, rs1, imm = item
            rd = resolve_register(rd, context)
            rs1 = resolve_register(rs1, context)
            inst = ITypeInstruction(name, rd, rs1, imm)
            output.append(inst)
        elif type(item) == STypeInstruction:
            name, rs1, rs2, imm = item
            rs1 = resolve_register(rs1, context)
            rs2 = resolve_register(rs2, context)
            inst = STypeInstruction(name, rs1, rs2, imm)
            output.append(inst)
        elif type(item) == BTypeInstruction:
            name, rs1, rs2, imm = item
            rs1 = resolve_register(rs1, context)
            rs2 = resolve_register(rs2, context)
            inst = BTypeInstruction(name, rs1, rs2, imm)
            output.append(inst)
        elif type(item) == UTypeInstruction:
            name, rd, imm = item
            rd = resolve_register(rd, context)
            inst = UTypeInstruction(name, rd, imm)
            output.append(inst)
        elif type(item) == JTypeInstruction:
            name, rd, imm = item
            rd = resolve_register(rd, context)
            inst = JTypeInstruction(name, rd, imm)
            output.append(inst)
        else:
            output.append(item)

    return output

def resolve_immediates(program, context, labels):
    # helper function for resolving immediate items
    def resolve_immediate(imm, context, labels, position):
        try:
            if type(imm) == Position:
                dest = labels[imm.label]
                base = eval(imm.expr, context)
                return base + dest
            elif type(imm) == Offset:
                dest = labels[imm.label]
                return dest - position
            elif type(imm) == Hi:
                value = eval(imm.expr, context)
                value = relocate_hi(value)
                return value
            elif type(imm) == Lo:
                value = eval(imm.expr, context)
                value = relocate_lo(value)
                return value
            elif imm in labels:
                return labels[imm]
            else:
                value = eval(imm, context)
                return value
        except:
            raise SystemExit('invalid immediate: {}'.format(imm))

    position = 0

    # check for items that have an immediate field and resolve it
    output = []
    for item in program:
        if type(item) == ITypeInstruction:
            name, rd, rs1, imm = item
            imm = resolve_immediate(imm, context, labels, position)
            inst = ITypeInstruction(name, rd, rs1, imm)
            position += 4
            output.append(inst)
        elif type(item) == STypeInstruction:
            name, rs1, rs2, imm = item
            imm = resolve_immediate(imm, context, labels, position)
            inst = STypeInstruction(name, rs1, rs2, imm)
            position += 4
            output.append(inst)
        elif type(item) == BTypeInstruction:
            name, rs1, rs2, imm = item
            imm = resolve_immediate(imm, context, labels, position)
            inst = BTypeInstruction(name, rs1, rs2, imm)
            position += 4
            output.append(inst)
        elif type(item) == UTypeInstruction:
            name, rd, imm = item
            imm = resolve_immediate(imm, context, labels, position)
            inst = UTypeInstruction(name, rd, imm)
            position += 4
            output.append(inst)
        elif type(item) == JTypeInstruction:
            name, rd, imm = item
            imm = resolve_immediate(imm, context, labels, position)
            inst = JTypeInstruction(name, rd, imm)
            position += 4
            output.append(inst)
        elif type(item) == Pack:
            fmt, imm = item
            imm = resolve_immediate(imm, context, labels, position)
            pack = Pack(fmt, imm)
            position += struct.calcsize(fmt)
            output.append(pack)
        elif type(item) == Blob:
            position += len(item.data)
            output.append(item)
        else:
            position += 4
            output.append(item)

    return output


def assemble(program):
    output = bytearray()
    for item in program:
        if type(item) == RTypeInstruction:
            name, rd, rs1, rs2 = item
            encode_func = INSTRUCTIONS[name]
            code = encode_func(rd, rs1, rs2)
            output.extend(code)
        elif type(item) == ITypeInstruction:
            name, rd, rs1, imm = item
            encode_func = INSTRUCTIONS[name]
            code = encode_func(rd, rs1, imm)
            output.extend(code)
        elif type(item) == STypeInstruction:
            name, rs1, rs2, imm = item
            encode_func = INSTRUCTIONS[name]
            code = encode_func(rs1, rs2, imm)
            output.extend(code)
        elif type(item) == BTypeInstruction:
            name, rs1, rs2, imm = item
            encode_func = INSTRUCTIONS[name]
            code = encode_func(rs1, rs2, imm)
            output.extend(code)
        elif type(item) == UTypeInstruction:
            name, rd, imm = item
            encode_func = INSTRUCTIONS[name]
            code = encode_func(rd, imm)
            output.extend(code)
        elif type(item) == JTypeInstruction:
            name, rd, imm = item
            encode_func = INSTRUCTIONS[name]
            code = encode_func(rd, imm)
            output.extend(code)
        elif type(item) == Pack:
            fmt, imm = item
            data = struct.pack(fmt, imm)
            output.extend(data)
        elif type(item) == Blob:
            data = item.data
            output.extend(data)
        else:
            raise SystemExit('invalid item at assemble pass: {}'.format(item))

    return bytes(output)


# Passes (labels, position):
# 0. Lex + Parse assembly source
# 1. Resolve constants  (NAME = expr)
# 2. Resolve aligns  (convert aligns to blobs based on position)
# 3. Resolve labels  (store label locations into dict)
# 4. Resolve registers  (could be constants for readability)
# 5. Resolve immediates  (Position, Offset, Hi, Lo)
# 6. Assemble!  (convert everything to bytes)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        usage = 'usage: python -m bronzebeard.asm <input_asm> <output_bin>'
        raise SystemExit(usage)

    input_asm = sys.argv[1]
    output_bin = sys.argv[2]

    with open(input_asm) as f:
        assembly = f.read()

    items = lex_assembly(assembly)
    prog = parse_assembly(items)

    pprint(prog)

    prog, context = resolve_constants(prog)
    pprint(prog)
    pprint(context)

    prog = resolve_aligns(prog)
    pprint(prog)

    prog, labels = resolve_labels(prog)
    pprint(prog)
    pprint(labels)

    prog = resolve_registers(prog, context)
    pprint(prog)

    prog = resolve_immediates(prog, context, labels)
    pprint(prog)

    prog = assemble(prog)
    pprint(prog)

    with open(output_bin, 'wb') as f:
        f.write(prog)
