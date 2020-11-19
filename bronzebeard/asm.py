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
#   name: str
#   label: str
#   alignment: int
#   fmt: str
#   data: bytes
#   rd, rs1, rs2: int, str
#   expr: %position, %offset, %hi, %lo, or simple python expression

# items
Align = namedtuple('Align', 'alignment')  # 0-3 bytes
Label = namedtuple('Label', 'name')  # 0 bytes
Constant = namedtuple('Constant', 'name expr')  # 0 bytes
Pack = namedtuple('Pack', 'fmt expr')  # struct.calcsize(fmt) bytes
Blob = namedtuple('Blob', 'data')  # len(data) bytes
RTypeInstruction = namedtuple('RTypeInstruction', 'name rd rs1 rs2')  # 4 bytes
ITypeInstruction = namedtuple('ITypeInstruction', 'name rd rs1 expr')  # 4 bytes
STypeInstruction = namedtuple('STypeInstruction', 'name rs1 rs2 expr')  # 4 bytes
BTypeInstruction = namedtuple('BTypeInstruction', 'name rs1 rs2 expr')  # 4 bytes
UTypeInstruction = namedtuple('UTypeInstruction', 'name rd expr')  # 4 bytes
JTypeInstruction = namedtuple('JTypeInstruction', 'name rd expr')  # 4 bytes

# expression modifiers
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
    assembly = re.sub(r'#.*?$', r'', assembly, flags=re.MULTILINE)  # strip comments
    lines = assembly.splitlines()  # split into lines
    lines = [line.strip() for line in lines]  # strip whitespace
    lines = [line for line in lines if len(line) > 0]  # skip empty lines
    items = [re.split(r'[\s,()\'"]+', line) for line in lines]  # split lines into tokens

    # remove empty tokens
    for item in items:
        while '' in item:
            item.remove('')

    return items

def parse_assembly(items):
    def parse_expression(expr):
        if expr[0].lower() == '%position':
            _, label, *expr = expr
            expr = ' '.join(expr)
            return Position(label, expr)
        elif expr[0].lower() == '%offset':
            _, label = expr
            return Offset(label)
        elif expr[0].lower() == '%hi':
            _, *expr = expr
            expr = parse_expression(expr)
            return Hi(expr)
        elif expr[0].lower() == '%lo':
            _, *expr = expr
            expr = parse_expression(expr)
            return Lo(expr)
        else:
            return ' '.join(expr)

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
            expr = parse_expression(expr)
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
            _, fmt, *expr = item
            expr = parse_expression(expr)
            item = Pack(fmt, expr)
            program.append(item)
        # bytes
        elif item[0].lower() == 'bytes':
            _, *data = item
            data = [int(byte, base=0) for byte in data]
            for byte in data:
                if byte < 0 or byte > 255:
                    raise SystemExit('bytes literal not in range [0, 255]: {}'.format(data))
            data = bytes(data)
            item = Blob(data)
            program.append(item)
        # string
        elif item[0].lower() == 'string':
            _, *data = item
            data = ' '.join(data)
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
            name, rd, rs1, *expr = item
            expr = parse_expression(expr)
            item = ITypeInstruction(name, rd, rs1, expr)
            program.append(item)
        # s-type instructions
        elif item[0].lower() in S_TYPE_INSTRUCTIONS:
            name, rs1, rs2, *expr = item
            expr = parse_expression(expr)
            item = STypeInstruction(name, rs1, rs2, expr)
            program.append(item)
        # b-type instructions
        elif item[0].lower() in B_TYPE_INSTRUCTIONS:
            name, rs1, rs2, *expr = item
            # ensure behavior is "offset" for branch instructions
            if expr[0] != '%offset':
                expr.insert(0, '%offset')
            expr = parse_expression(expr)
            item = BTypeInstruction(name, rs1, rs2, expr)
            program.append(item)
        # u-type instructions
        elif item[0].lower() in U_TYPE_INSTRUCTIONS:
            name, rd, *expr = item
            expr = parse_expression(expr)
            item = UTypeInstruction(name, rd, expr)
            program.append(item)
        # j-type instructions
        elif item[0].lower() in J_TYPE_INSTRUCTIONS:
            name, rd, *expr = item
            # ensure behavior is "offset" for jump instructions
            if expr[0] != '%offset':
                expr.insert(0, '%offset')
            expr = parse_expression(expr)
            item = JTypeInstruction(name, rd, expr)
            program.append(item)
        else:
            raise SystemExit('invalid item: {}'.format(' '.join(item)))

    return program

# helper func, not a pass
def resolve_expression(expr, env, position):
    # TODO: better error messages
    try:
        if type(expr) == Position:
            dest = env[expr.label]
            base = eval(expr.expr, env)
            return base + dest
        elif type(expr) == Offset:
            dest = env[expr.label]
            return dest - position
        elif type(expr) == Hi:
            if type(expr.expr) in [Position, Offset]:
                value = resolve_expression(expr.expr, env, position)
            else:
                value = eval(expr.expr, env)
            value = relocate_hi(value)
            return value
        elif type(expr) == Lo:
            if type(expr.expr) in [Position, Offset]:
                value = resolve_expression(expr.expr, env, position)
            else:
                value = eval(expr.expr, env)
            value = relocate_lo(value)
            return value
        else:
            value = eval(expr, env)
            return value
    except:
        raise SystemExit('invalid expression: {}'.format(expr))

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
        elif type(item) == Label:
            output.append(item)
        elif type(item) == Constant:
            output.append(item)
        elif type(item) == Pack:
            position += struct.calcsize(item.fmt)
            output.append(item)
        elif type(item) == Blob:
            position += len(item.data)
            output.append(item)
        else:  # instruction
            position += 4
            output.append(item)

    return output

def resolve_labels(program, env):
    env = dict(env)
    position = 0

    output = []
    for item in program:
        if type(item) == Label:
            env[item.name] = position
        elif type(item) == Constant:
            output.append(item)
        elif type(item) == Pack:
            position += struct.calcsize(item.fmt)
            output.append(item)
        elif type(item) == Blob:
            position += len(item.data)
            output.append(item)
        else:  # instruction
            position += 4
            output.append(item)

    return output, env

def resolve_constants(program, env):
    env = dict(env)
    position = 0

    output = []
    for item in program:
        if type(item) == Constant:
            if item.name in REGISTERS:
                raise SystemExit('constant name shadows register name: {}'.format(item.name))
            env[item.name] = resolve_expression(item.expr, env, position)
        elif type(item) == Pack:
            position += struct.calcsize(item.fmt)
            output.append(item)
        elif type(item) == Blob:
            position += len(item.data)
            output.append(item)
        else:  # instruction
            position += 4
            output.append(item)

    return output, env

def resolve_registers(program, env):
    output = []
    for item in program:
        if type(item) == RTypeInstruction:
            name, rd, rs1, rs2 = item
            rd = env.get(rd) or rd
            rs1 = env.get(rs1) or rs1
            rs2 = env.get(rs2) or rs2
            inst = RTypeInstruction(name, rd, rs1, rs2)
            output.append(inst)
        elif type(item) == ITypeInstruction:
            name, rd, rs1, expr = item
            rd = env.get(rd) or rd
            rs1 = env.get(rs1) or rs1
            inst = ITypeInstruction(name, rd, rs1, expr)
            output.append(inst)
        elif type(item) == STypeInstruction:
            name, rs1, rs2, expr = item
            rs1 = env.get(rs1) or rs1
            rs2 = env.get(rs2) or rs2
            inst = STypeInstruction(name, rs1, rs2, expr)
            output.append(inst)
        elif type(item) == BTypeInstruction:
            name, rs1, rs2, expr = item
            rs1 = env.get(rs1) or rs1
            rs2 = env.get(rs2) or rs2
            inst = BTypeInstruction(name, rs1, rs2, expr)
            output.append(inst)
        elif type(item) == UTypeInstruction:
            name, rd, expr = item
            rd = env.get(rd) or rd
            inst = UTypeInstruction(name, rd, expr)
            output.append(inst)
        elif type(item) == JTypeInstruction:
            name, rd, expr = item
            rd = env.get(rd) or rd
            inst = JTypeInstruction(name, rd, expr)
            output.append(inst)
        else:
            output.append(item)

    return output

def resolve_immediates(program, env):
    position = 0

    # check for items that have an immediate field and resolve it
    output = []
    for item in program:
        if type(item) == ITypeInstruction:
            name, rd, rs1, expr = item
            imm = resolve_expression(expr, env, position)
            inst = ITypeInstruction(name, rd, rs1, imm)
            position += 4
            output.append(inst)
        elif type(item) == STypeInstruction:
            name, rs1, rs2, expr = item
            imm = resolve_expression(expr, env, position)
            inst = STypeInstruction(name, rs1, rs2, imm)
            position += 4
            output.append(inst)
        elif type(item) == BTypeInstruction:
            name, rs1, rs2, expr = item
            imm = resolve_expression(expr, env, position)
            inst = BTypeInstruction(name, rs1, rs2, imm)
            position += 4
            output.append(inst)
        elif type(item) == UTypeInstruction:
            name, rd, expr = item
            imm = resolve_expression(expr, env, position)
            inst = UTypeInstruction(name, rd, imm)
            position += 4
            output.append(inst)
        elif type(item) == JTypeInstruction:
            name, rd, expr = item
            imm = resolve_expression(expr, env, position)
            inst = JTypeInstruction(name, rd, imm)
            position += 4
            output.append(inst)
        elif type(item) == Pack:
            fmt, expr = item
            imm = resolve_expression(expr, env, position)
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

def resolve_instructions(program):
    output = []
    for item in program:
        if type(item) == RTypeInstruction:
            name, rd, rs1, rs2 = item
            encode_func = INSTRUCTIONS[name]
            code = encode_func(rd, rs1, rs2)
            blob = Blob(code)
            output.append(blob)
        elif type(item) == ITypeInstruction:
            name, rd, rs1, imm = item
            encode_func = INSTRUCTIONS[name]
            code = encode_func(rd, rs1, imm)
            blob = Blob(code)
            output.append(blob)
        elif type(item) == STypeInstruction:
            name, rs1, rs2, imm = item
            encode_func = INSTRUCTIONS[name]
            code = encode_func(rs1, rs2, imm)
            blob = Blob(code)
            output.append(blob)
        elif type(item) == BTypeInstruction:
            name, rs1, rs2, imm = item
            encode_func = INSTRUCTIONS[name]
            code = encode_func(rs1, rs2, imm)
            blob = Blob(code)
            output.append(blob)
        elif type(item) == UTypeInstruction:
            name, rd, imm = item
            encode_func = INSTRUCTIONS[name]
            code = encode_func(rd, imm)
            blob = Blob(code)
            output.append(blob)
        elif type(item) == JTypeInstruction:
            name, rd, imm = item
            encode_func = INSTRUCTIONS[name]
            code = encode_func(rd, imm)
            blob = Blob(code)
            output.append(blob)
        else:
            output.append(item)

    return output

def resolve_packs(program):
    output = []
    for item in program:
        if type(item) == Pack:
            fmt, imm = item
            data = struct.pack(fmt, imm)
            blob = Blob(data)
            output.append(blob)
        else:
            output.append(item)

    return output

def resolve_blobs(program):
    output = bytearray()
    for item in program:
        if type(item) != Blob:
            raise SystemExit('expected only blobs but got: {}'.format(item))
        output.extend(item.data)

    return output

# Passes (labels, position):
# 0. Lex + Parse assembly source
# 1. Resolve aligns  (convert aligns to blobs based on position)
# 2. Resolve labels  (store label locations into dict)
# 3. Resolve constants  (NAME = expr)
# 4. Resolve registers  (could be constants for readability)
# 5. Resolve immediates  (Position, Offset, Hi, Lo)
# 6. Resolve instructions  (convert xTypeInstruction to Blob)
# 7. Resolve packs  (convert Pack to Blob)
# 8. Resolve blobs  (merge all Blobs into a single binary)

def assemble(source):
    items = lex_assembly(source)
    prog = parse_assembly(items)

    # exclude Python builtins from eval env
    # https://docs.python.org/3/library/functions.html#eval
    env = {
        '__builtins__': None,
    }
    env.update(REGISTERS)

    prog = resolve_aligns(prog)
    prog, env = resolve_labels(prog, env)
    prog, env = resolve_constants(prog, env)
    prog = resolve_registers(prog, env)
    prog = resolve_immediates(prog, env)
    prog = resolve_instructions(prog)
    prog = resolve_packs(prog)
    prog = resolve_blobs(prog)
    return prog


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

    # exclude Python builtins from eval env
    # https://docs.python.org/3/library/functions.html#eval
    env = {
        '__builtins__': None,
    }
    env.update(REGISTERS)

    prog = resolve_aligns(prog)
    pprint(prog)

    prog, env = resolve_labels(prog, env)
    pprint(prog)
    pprint(env)

    prog, env = resolve_constants(prog, env)
    pprint(prog)
    pprint(env)

    prog = resolve_registers(prog, env)
    pprint(prog)

    prog = resolve_immediates(prog, env)
    pprint(prog)

    prog = resolve_instructions(prog)
    pprint(prog)

    prog = resolve_packs(prog)
    pprint(prog)

    prog = resolve_blobs(prog)
    pprint(prog)

    with open(output_bin, 'wb') as f:
        f.write(prog)
