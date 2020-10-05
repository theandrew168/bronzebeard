from ctypes import c_uint32
from functools import partial
import struct

# Low-level interface to RISC-V instruction encoding


def r_type(rd, rs1, rs2, opcode, funct3, funct7):
    if rd < 0 or rd > 31:
        raise ValueError('Register must be between 0 and 31: {}'.format(rd))
    if rs1 < 0 or rs1 > 31:
        raise ValueError('Register must be between 0 and 31: {}'.format(rs1))
    if rs2 < 0 or rs2 > 31:
        raise ValueError('Register must be between 0 and 31: {}'.format(rs2))

    code = 0
    code |= opcode
    code |= rd << 7
    code |= funct3 << 12
    code |= rs1 << 15
    code |= rs2 << 20
    code |= funct7 << 25

    return struct.pack('<I', code)

def i_type(rd, rs1, imm, opcode, funct3):
    if rd < 0 or rd > 31:
        raise ValueError('Register must be between 0 and 31: {}'.format(rd))
    if rs1 < 0 or rs1 > 31:
        raise ValueError('Register must be between 0 and 31: {}'.format(rs1))
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
    if rs1 < 0 or rs1 > 31:
        raise ValueError('Register must be between 0 and 31: {}'.format(rs1))
    if rs2 < 0 or rs2 > 31:
        raise ValueError('Register must be between 0 and 31: {}'.format(rs2))
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
    if imm < -0x80000 or imm > 0x7ffff:
        raise ValueError('20-bit immediate must be between -0x80000 (-524288) and 0x7ffff (524287): {}'.format(imm))

    imm = c_uint32(imm).value & 0b11111111111111111111

    code = 0
    code |= opcode
    code |= rd << 7
    code |= imm << 12

    return struct.pack('<I', code)

def j_type(rd, imm, opcode):
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
FENCE = partial(i_type, opcode=0b0001111, funct3=0b000)
ECALL = partial(i_type, opcode=0b1110011, funct3=0b000)
EBREAK = partial(i_type, opcode=0b1110011, funct3=0b000)
