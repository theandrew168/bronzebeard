from ctypes import c_uint32
from functools import partial
import struct


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

def sign_extend(value, bits):
    sign_bit = 1 << (bits - 1)
    return (value & (sign_bit - 1)) - (value & sign_bit)

def relocate_hi(imm):
    if imm & 0x800:
        imm += 2**12
    return sign_extend((imm >> 12) & 0x000fffff, 20)

def relocate_lo(imm):
    return sign_extend(imm & 0x00000fff, 12)

def r_type_instruction(rd, rs1, rs2, opcode, funct3, funct7):
    if rd not in REGISTERS:
        raise ValueError('Invalid register: {}'.format(rd))
    if rs1 not in REGISTERS:
        raise ValueError('Invalid register: {}'.format(rs1))
    if rs2 not in REGISTERS:
        raise ValueError('Invalid register: {}'.format(rs2))

    rd = REGISTERS[rd]
    rs1 = REGISTERS[rs1]
    rs2 = REGISTERS[rs2]

    inst = 0
    inst |= opcode
    inst |= rd << 7
    inst |= funct3 << 12
    inst |= rs1 << 15
    inst |= rs2 << 20
    inst |= funct7 << 25

    return struct.pack('<I', inst)

def i_type_instruction(rd, rs1, imm, opcode, funct3):
    if rd not in REGISTERS:
        raise ValueError('Invalid register: {}'.format(rd))
    if rs1 not in REGISTERS:
        raise ValueError('Invalid register: {}'.format(rs1))
    if imm < -0x800 or imm > 0x7ff:
        raise ValueError('12-bit immediate must be between -0x800 (-2048) and 0x7ff (2047): {}'.format(imm))

    rd = REGISTERS[rd]
    rs1 = REGISTERS[rs1]
    imm = c_uint32(imm).value & 0b111111111111

    inst = 0
    inst |= opcode
    inst |= rd << 7
    inst |= funct3 << 12
    inst |= rs1 << 15
    inst |= imm << 20

    return struct.pack('<I', inst)

def s_type_instruction(rs1, rs2, imm, opcode, funct3):
    if rs1 not in REGISTERS:
        raise ValueError('Invalid register: {}'.format(rs1))
    if rs2 not in REGISTERS:
        raise ValueError('Invalid register: {}'.format(rs2))
    if imm < -0x800 or imm > 0x7ff:
        raise ValueError('12-bit immediate must be between -0x800 (-2048) and 0x7ff (2047): {}'.format(imm))

    rs1 = REGISTERS[rs1]
    rs2 = REGISTERS[rs2]
    imm = c_uint32(imm).value & 0b111111111111

    imm_11_5 = (imm >> 5) & 0b1111111
    imm_4_0 = imm & 0b11111

    inst = 0
    inst |= opcode
    inst |= imm_4_0 << 7
    inst |= funct3 << 12
    inst |= rs1 << 15
    inst |= rs2 << 20
    inst |= imm_11_5 << 25

    return struct.pack('<I', inst)

def b_type_instruction(rs1, rs2, imm, opcode, funct3):
    if rs1 not in REGISTERS:
        raise ValueError('Invalid register: {}'.format(rs1))
    if rs2 not in REGISTERS:
        raise ValueError('Invalid register: {}'.format(rs2))
    if imm < -0x1000 or imm > 0x0fff:
        raise ValueError('12-bit multiple of 2 immediate must be between -0x1000 (-4096) and 0x0fff (4095): {}'.format(imm))
    if imm % 2 == 1:
        raise ValueError('12-bit multiple of 2 immediate must be a muliple of 2: {}'.format(imm))

    rs1 = REGISTERS[rs1]
    rs2 = REGISTERS[rs2]
    imm = imm // 2
    imm = c_uint32(imm).value & 0b111111111111

    imm_12 = (imm >> 11) & 0b1
    imm_11 = (imm >> 10) & 0b1
    imm_10_5 = (imm >> 4) & 0b111111
    imm_4_1 = imm & 0b1111

    inst = 0
    inst |= opcode
    inst |= imm_11 << 7
    inst |= imm_4_1 << 8
    inst |= funct3 << 12
    inst |= rs1 << 15
    inst |= rs2 << 20
    inst |= imm_10_5 << 25
    inst |= imm_12 << 31

    return struct.pack('<I', inst)

def u_type_instruction(rd, imm, opcode):
    if rd not in REGISTERS:
        raise ValueError('Invalid register: {}'.format(rd))
    if imm < -0x80000 or imm > 0x7ffff:
        raise ValueError('20-bit immediate must be between -0x80000 (-524288) and 0x7ffff (524287): {}'.format(imm))

    rd = REGISTERS[rd]
    imm = c_uint32(imm).value & 0b11111111111111111111

    inst = 0
    inst |= opcode
    inst |= rd << 7
    inst |= imm << 12

    return struct.pack('<I', inst)

def j_type_instruction(rd, imm, opcode):
    if rd not in REGISTERS:
        raise ValueError('Invalid register: {}'.format(rd))
    if imm < -0x100000 or imm > 0x0fffff:
        raise ValueError('20-bit multiple of 2 immediate must be between -0x100000 (-1048576) and 0x0fffff (1048575): {}'.format(imm))
    if imm % 2 == 1:
        raise ValueError('20-bit multiple of 2 immediate must be a muliple of 2: {}'.format(imm))

    rd = REGISTERS[rd]
    imm = self.imm // 2
    imm = c_uint32(imm).value & 0b11111111111111111111

    imm_20 = (imm >> 19) & 0b1
    imm_19_12 = (imm >> 11) & 0b11111111
    imm_11 = (imm >> 10) & 0b1
    imm_10_1 = imm & 0b1111111111

    inst = 0
    inst |= opcode
    inst |= rd << 7
    inst |= imm_19_12 << 12
    inst |= imm_11 << 20
    inst |= imm_10_1 << 21
    inst |= imm_20 << 31

    return struct.pack('<I', inst)

LUI = partial(u_type_instruction, opcode=0b0110111)
AUIPC = partial(u_type_instruction, opcode=0b0010111)
JAL = partial(j_type_instruction, opcode=0b1101111)
JALR = partial(i_type_instruction, opcode=0b1100111, funct3=0b000)
BEQ = partial(b_type_instruction, opcode=0b1100011, funct3=0b000)
LW = partial(i_type_instruction, opcode=0b0000011, funct3=0b010)
SW = partial(s_type_instruction, opcode=0b0100011, funct3=0b010)
ADDI = partial(i_type_instruction, opcode=0b0010011, funct3=0b000)
SLLI = partial(r_type_instruction, opcode=0b0010011, funct3=0b001, funct7=0b0000000)
OR = partial(r_type_instruction, opcode=0b0110011, funct3=0b110, funct7=0b0000000)

#class RISCVAssembler:
#
#    def __init__(self):
#        self.instructions = bytearray()
#        self.labels = {}
#
#    def LABEL(self, name):
#        if name in self.labels:
#            raise ValueError('Duplicate label: {}'.format(name))
#        self.labels[name] = len(self.instructions)
#
#
#def assemble(ast):
#    instructions = bytearray()
#    constants = {}
#    labels = {}
#
#    for stmt in ast:
#        head = stmt[0].lower()
#
#        # check for constant definition
#        if head == '.equ':
#            key = stmt[1]
#            value = stmt[2]
#            constants[key] = value
#        # check for label
#        elif head.endswith(':'):
#            label = head[:-1]
#            labels[label] = len(instructions)
#        # otherwise assume instruction
#        else:
#            if head not in INSTRUCTIONS:
#                raise ValueError('Invalid instruction: {}'.format(head))
##            # handle %hi relocation
##            elif token.lower() == '%hi':
##                imm = next(line)
##                imm = int(imm)
##                imm = relocate_hi(imm)
##                statement.append(imm)
##            # handle %lo relocation
##            elif token.lower() == '%lo':
##                imm = next(line)
##                imm = int(imm)
##                imm = relocate_lo(imm)
##                statement.append(imm)
#
#    return instructions
