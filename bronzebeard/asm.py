import abc
import argparse
import copy
from ctypes import c_uint32
from functools import partial
import os
import re
import struct
import sys


REGISTERS = {
    # ints  # strs    # names    # aliases
    0:  0,  '0':  0,  'x0':  0,  'zero': 0,
    1:  1,  '1':  1,  'x1':  1,  'ra':   1,
    2:  2,  '2':  2,  'x2':  2,  'sp':   2,
    3:  3,  '3':  3,  'x3':  3,  'gp':   3,
    4:  4,  '4':  4,  'x4':  4,  'tp':   4,
    5:  5,  '5':  5,  'x5':  5,  't0':   5,
    6:  6,  '6':  6,  'x6':  6,  't1':   6,
    7:  7,  '7':  7,  'x7':  7,  't2':   7,
    8:  8,  '8':  8,  'x8':  8,  's0':   8, 'fp': 8,
    9:  9,  '9':  9,  'x9':  9,  's1':   9,
    10: 10, '10': 10, 'x10': 10, 'a0':   10,
    11: 11, '11': 11, 'x11': 11, 'a1':   11,
    12: 12, '12': 12, 'x12': 12, 'a2':   12,
    13: 13, '13': 13, 'x13': 13, 'a3':   13,
    14: 14, '14': 14, 'x14': 14, 'a4':   14,
    15: 15, '15': 15, 'x15': 15, 'a5':   15,
    16: 16, '16': 16, 'x16': 16, 'a6':   16,
    17: 17, '17': 17, 'x17': 17, 'a7':   17,
    18: 18, '18': 18, 'x18': 18, 's2':   18,
    19: 19, '19': 19, 'x19': 19, 's3':   19,
    20: 20, '20': 20, 'x20': 20, 's4':   20,
    21: 21, '21': 21, 'x21': 21, 's5':   21,
    22: 22, '22': 22, 'x22': 22, 's6':   22,
    23: 23, '23': 23, 'x23': 23, 's7':   23,
    24: 24, '24': 24, 'x24': 24, 's8':   24,
    25: 25, '25': 25, 'x25': 25, 's9':   25,
    26: 26, '26': 26, 'x26': 26, 's10':  26,
    27: 27, '27': 27, 'x27': 27, 's11':  27,
    28: 28, '28': 28, 'x28': 28, 't3':   28,
    29: 29, '29': 29, 'x29': 29, 't4':   29,
    30: 30, '30': 30, 'x30': 30, 't5':   30,
    31: 31, '31': 31, 'x31': 31, 't6':   31,
}


# low-level funcs just return value errors
# high-level funcs watch for ValueErrors attach Line info
class AssemblerError(Exception):

    def __init__(self, message, line):
        super().__init__(message)
        self.message = message
        self.line = line

    def __str__(self):
        return 'AssemblerError: {}\n  {}'.format(self.message, self.line)


def lookup_register(reg, compressed=False):
    if reg not in REGISTERS:
        raise ValueError('register must be a valid integer, name, or alias: {}'.format(reg))

    reg = REGISTERS[reg]

    # check for compressed instruction register, validate and apply
    if compressed:
        # must be in "common" registers: x8-x15
        if reg < 8 or reg > 15:
            raise ValueError('compressed register must be between 8 and 15: {}'.format(reg))
        # subtract 8 to get compressed, 3-bit reg value
        reg -= 8

    return reg


def r_type(rd, rs1, rs2, *, opcode, funct3, funct7):
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

    return code


def i_type(rd, rs1, imm, *, opcode, funct3):
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

    return code


# i-type variation for JALR
def ij_type(rd, rs1, imm, *, opcode, funct3):
    rd = lookup_register(rd)
    rs1 = lookup_register(rs1)

    if imm < -0x800 or imm > 0x7ff:
        raise ValueError('12-bit immediate must be between -0x800 (-2048) and 0x7ff (2047): {}'.format(imm))
    if imm % 2 != 0:
        raise ValueError('12-bit immediate must be a muliple of 2: {}'.format(imm))

    imm = c_uint32(imm).value & 0b111111111111

    code = 0
    code |= opcode
    code |= rd << 7
    code |= funct3 << 12
    code |= rs1 << 15
    code |= imm << 20

    return code


def s_type(rs1, rs2, imm, *, opcode, funct3):
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

    return code


def b_type(rs1, rs2, imm, *, opcode, funct3):
    rs1 = lookup_register(rs1)
    rs2 = lookup_register(rs2)

    if imm < -0x1000 or imm > 0x0fff:
        raise ValueError('12-bit MO2 immediate must be between -0x1000 (-4096) and 0x0fff (4095): {}'.format(imm))
    if imm % 2 != 0:
        raise ValueError('12-bit MO2 immediate must be a muliple of 2: {}'.format(imm))

    imm = imm >> 1
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

    return code


def u_type(rd, imm, *, opcode):
    rd = lookup_register(rd)

    if imm < -0x80000 or imm > 0x7ffff:
        raise ValueError('20-bit immediate must be between -0x80000 (-524288) and 0x7ffff (524287): {}'.format(imm))

    imm = c_uint32(imm).value & 0b11111111111111111111

    code = 0
    code |= opcode
    code |= rd << 7
    code |= imm << 12

    return code


def j_type(rd, imm, *, opcode):
    rd = lookup_register(rd)

    if imm < -0x100000 or imm > 0x0fffff:
        raise ValueError('20-bit MO2 immediate must be between -0x100000 (-1048576) and 0x0fffff (1048575): {}'.format(imm))
    if imm % 2 != 0:
        raise ValueError('20-bit MO2 immediate must be a muliple of 2: {}'.format(imm))

    imm = imm >> 1
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

    return code


def fence(succ, pred, *, opcode, funct3, rd, rs1, fm):
    succ = succ if type(succ) == int else int(succ, base=0)
    pred = pred if type(pred) == int else int(pred, base=0)
    if succ < 0b0000 or succ > 0b1111:
        raise ValueError('invalid successor value for FENCE instruction: {}'.format(succ))
    if pred < 0b0000 or pred > 0b1111:
        raise ValueError('invalid predecessor value for FENCE instruction: {}'.format(pred))

    imm = (fm << 8) | (pred << 4) | succ
    return i_type(rd, rs1, imm, opcode=opcode, funct3=funct3)


def a_type(rd, rs1, rs2, *, opcode, funct3, funct5, aq=0, rl=0):
    aq = aq if type(aq) == int else int(aq, base=0)
    rl = rl if type(rl) == int else int(rl, base=0)
    if aq not in [0, 1]:
        raise ValueError('aq must be either 0 or 1')
    if rl not in [0, 1]:
        raise ValueError('rl must be either 0 or 1')

    # build aq/rl into a funct7 and defer to r_type
    funct7 = funct5 << 2 | aq << 1 | rl
    return r_type(rd, rs1, rs2, opcode=opcode, funct3=funct3, funct7=funct7)


# c.jr, c.mv, c.jalr, c.add
def cr_type(rd_rs1, rs2, *, opcode, funct4):
    rd_rs1 = lookup_register(rd_rs1)
    rs2 = lookup_register(rs2)

    code = 0
    code |= opcode
    code |= rs2 << 2
    code |= rd_rs1 << 7
    code |= funct4 << 12

    return code


# c.nop, c.addi, c.li, c.lui, c.slli
def ci_type(rd_rs1, imm, *, opcode, funct3):
    rd_rs1 = lookup_register(rd_rs1)

    if imm < -32 or imm > 31:
        raise ValueError('6-bit immediate must be between -32 (-0x20) and 31 (0x1f): {}'.format(imm))

    imm = c_uint32(imm).value & 0b111111

    imm_5 = (imm >> 5) & 0b1
    imm_4_0 = imm & 0b11111

    code = 0
    code |= opcode
    code |= imm_4_0 << 2
    code |= rd_rs1 << 7
    code |= imm_5 << 12
    code |= funct3 << 13

    return code


# CI variation
# c.addi16sp
def cis_type(rd_rs1, imm, *, opcode, funct3):
    rd_rs1 = lookup_register(rd_rs1)

    if imm < -512 or imm > 511:
        raise ValueError('6-bit MO16 immediate must be between -512 (-0x200) and 511 (0x1ff): {}'.format(imm))
    if imm % 16 != 0:
        raise ValueError('6-bit MO16 immediate must be a multiple of 16: {}'.format(imm))

    imm = imm >> 4
    imm = c_uint32(imm).value & 0b111111

    imm_9 = (imm >> 5) & 0b1
    imm_8_4 = imm & 0b11111

    code = 0
    code |= opcode
    code |= imm_8_4 << 2
    code |= rd_rs1 << 7
    code |= imm_9 << 12
    code |= funct3 << 13

    return code


# CI variation
# c.lwsp
def cls_type(rd, imm, *, opcode, funct3):
    rd = lookup_register(rd)

    if imm < 0 or imm > 255:
        raise ValueError('6-bit MO4 unsigned immediate must be between 0 (0x00) and 0xff (255): {}'.format(imm))
    if imm % 4 != 0:
        raise ValueError('6-bit MO4 unsigned immediate must be a multiple of 4: {}'.format(imm))

    imm = imm >> 2
    imm = c_uint32(imm).value & 0b111111

    imm_7 = (imm >> 5) & 0b1
    imm_6_2 = imm & 0b11111

    code = 0
    code |= opcode
    code |= imm_6_2 << 2
    code |= rd << 7
    code |= imm_7 << 12
    code |= funct3 << 13

    return code


# c.swsp
def css_type(rs2, imm, *, opcode, funct3):
    rs2 = lookup_register(rs2)

    if imm < 0 or imm > 255:
        raise ValueError('6-bit MO4 unsigned immediate must be between 0 (0x00) and 0xff (255): {}'.format(imm))
    if imm % 4 != 0:
        raise ValueError('6-bit MO4 unsigned immediate must be a multiple of 4: {}'.format(imm))

    imm = imm >> 2
    imm = c_uint32(imm).value & 0b111111

    imm_7_6 = (imm >> 4) & 0b11
    imm_5_2 = imm & 0b1111

    code = 0
    code |= opcode
    code |= rs2 << 2
    code |= imm_7_6 << 7
    code |= imm_5_2 << 9
    code |= funct3 << 13

    return code


# c.addi4spn
def ciw_type(rd, imm, *, opcode, funct3):
    rd = lookup_register(rd, compressed=True)

    if imm < 0 or imm > 1023:
        raise ValueError('8-bit MO4 unsigned immediate must be between 0 (0x00) and 0x3ff (1023): {}'.format(imm))
    if imm % 4 != 0:
        raise ValueError('8-bit MO4 unsigned immediate must be a multiple of 4: {}'.format(imm))

    imm = imm >> 2
    imm = c_uint32(imm).value & 0b11111111

    imm_9_6 = (imm >> 4) & 0b1111
    imm_5_4 = (imm >> 2) & 0b11
    imm_3 = (imm >> 1) & 0b1
    imm_2 = imm & 0b1

    code = 0
    code |= opcode
    code |= rd << 2
    code |= imm_3 << 5
    code |= imm_2 << 6
    code |= imm_9_6 << 7
    code |= imm_5_4 << 11
    code |= funct3 << 13

    return code


# c.lw
def cl_type(rd, rs1, imm, *, opcode, funct3):
    rd = lookup_register(rd, compressed=True)
    rs1 = lookup_register(rs1, compressed=True)

    if imm < 0 or imm > 127:
        raise ValueError('5-bit MO4 unsigned immediate must be between 0 (0x00) and 0x7f (127): {}'.format(imm))
    if imm % 4 != 0:
        raise ValueError('5-bit MO4 unsigned immediate must be a multiple of 4: {}'.format(imm))

    imm = imm >> 2
    imm = c_uint32(imm).value & 0b11111

    imm_6 = (imm >> 4) & 0b1
    imm_5_3 = (imm >> 1) & 0b111
    imm_2 = imm & 0b1

    code = 0
    code |= opcode
    code |= rd << 2
    code |= imm_6 << 5
    code |= imm_2 << 6
    code |= rs1 << 7
    code |= imm_5_3 << 10
    code |= funct3 << 13

    return code


# c.sw
def cs_type(rs1, rs2, imm, *, opcode, funct3):
    rs1 = lookup_register(rs1, compressed=True)
    rs2 = lookup_register(rs2, compressed=True)

    if imm < 0 or imm > 127:
        raise ValueError('5-bit MO4 unsigned immediate must be between 0 (0x00) and 0x7f (127): {}'.format(imm))
    if imm % 4 != 0:
        raise ValueError('5-bit MO4 unsigned immediate must be a multiple of 4: {}'.format(imm))

    imm = imm >> 2
    imm = c_uint32(imm).value & 0b11111

    imm_6 = (imm >> 4) & 0b1
    imm_5_3 = (imm >> 1) & 0b111
    imm_2 = imm & 0b1

    code = 0
    code |= opcode
    code |= rs2 << 2
    code |= imm_6 << 5
    code |= imm_2 << 6
    code |= rs1 << 7
    code |= imm_5_3 << 10
    code |= funct3 << 13

    return code


# c.sub, c.xor, c.or, c.and
def ca_type(rd_rs1, rs2, *, opcode, funct2, funct6):
    rd_rs1 = lookup_register(rd_rs1, compressed=True)
    rs2 = lookup_register(rs2, compressed=True)

    code = 0
    code |= opcode
    code |= rs2 << 2
    code |= funct2 << 5
    code |= rd_rs1 << 7
    code |= funct6 << 10

    return code


# c.beqz, c.bnez
def cb_type(rs1, imm, *, opcode, funct3):
    rs1 = lookup_register(rs1, compressed=True)

    imm = imm >> 1
    imm = c_uint32(imm).value & 0b11111111

    imm_8 = (imm >> 7) & 0b1
    imm_7_6 = (imm >> 5) & 0b11
    imm_5 = (imm >> 4) & 0b1
    imm_4_3 = (imm >> 2) & 0b11
    imm_2_1 = imm & 0b11

    code = 0
    code |= opcode
    code |= imm_5 << 2
    code |= imm_2_1 << 3
    code |= imm_7_6 << 5
    code |= rs1 << 7
    code |= imm_4_3 << 10
    code |= imm_8 << 12
    code |= funct3 << 13

    return code


# CB variation
# c.srli, c.srai, c.andi
def cbi_type(rd_rs1, imm, *, opcode, funct2, funct3):
    rd_rs1 = lookup_register(rd_rs1, compressed=True)

    imm = c_uint32(imm).value & 0b111111

    imm_5 = (imm >> 5) & 0b1
    imm_4_0 = imm & 0b11111

    code = 0
    code |= opcode
    code |= imm_4_0 << 2
    code |= rd_rs1 << 7
    code |= funct2 << 10
    code |= imm_5 << 12
    code |= funct3 << 13

    return code


# c.jal, c.j
def cj_type(imm, *, opcode, funct3):
    if imm < -2048 or imm > 2047:
        raise ValueError('11-bit MO2 immediate must be between -0x800 (-2048) and 0x7ff (2047): {}'.format(imm))
    if imm % 2 != 0:
        raise ValueError('11-bit MO2 immediate must be a muliple of 2: {}'.format(imm))

    imm = imm >> 1
    imm = c_uint32(imm).value & 0b11111111111

    imm_11 = (imm >> 10) & 0b1
    imm_10 = (imm >> 9) & 0b1
    imm_9_8 = (imm >> 7) & 0b11
    imm_7 = (imm >> 6) & 0b1
    imm_6 = (imm >> 5) & 0b1
    imm_5 = (imm >> 4) & 0b1
    imm_4 = (imm >> 3) & 0b1
    imm_3_1 = imm & 0b111

    code = 0
    code |= opcode
    code |= imm_5 << 2
    code |= imm_3_1 << 3
    code |= imm_7 << 6
    code |= imm_6 << 7
    code |= imm_10 << 8
    code |= imm_9_8 << 9
    code |= imm_4 << 11
    code |= imm_11 << 12
    code |= funct3 << 13

    return code


# RV32I Base Integer Instruction Set
LUI        = partial(u_type,   opcode=0b0110111)
AUIPC      = partial(u_type,   opcode=0b0010111)
JAL        = partial(j_type,   opcode=0b1101111)
JALR       = partial(ij_type,  opcode=0b1100111, funct3=0b000)
BEQ        = partial(b_type,   opcode=0b1100011, funct3=0b000)
BNE        = partial(b_type,   opcode=0b1100011, funct3=0b001)
BLT        = partial(b_type,   opcode=0b1100011, funct3=0b100)
BGE        = partial(b_type,   opcode=0b1100011, funct3=0b101)
BLTU       = partial(b_type,   opcode=0b1100011, funct3=0b110)
BGEU       = partial(b_type,   opcode=0b1100011, funct3=0b111)
LB         = partial(i_type,   opcode=0b0000011, funct3=0b000)
LH         = partial(i_type,   opcode=0b0000011, funct3=0b001)
LW         = partial(i_type,   opcode=0b0000011, funct3=0b010)
LBU        = partial(i_type,   opcode=0b0000011, funct3=0b100)
LHU        = partial(i_type,   opcode=0b0000011, funct3=0b101)
SB         = partial(s_type,   opcode=0b0100011, funct3=0b000)
SH         = partial(s_type,   opcode=0b0100011, funct3=0b001)
SW         = partial(s_type,   opcode=0b0100011, funct3=0b010)
ADDI       = partial(i_type,   opcode=0b0010011, funct3=0b000)
SLTI       = partial(i_type,   opcode=0b0010011, funct3=0b010)
SLTIU      = partial(i_type,   opcode=0b0010011, funct3=0b011)
XORI       = partial(i_type,   opcode=0b0010011, funct3=0b100)
ORI        = partial(i_type,   opcode=0b0010011, funct3=0b110)
ANDI       = partial(i_type,   opcode=0b0010011, funct3=0b111)
SLLI       = partial(r_type,   opcode=0b0010011, funct3=0b001, funct7=0b0000000)
SRLI       = partial(r_type,   opcode=0b0010011, funct3=0b101, funct7=0b0000000)
SRAI       = partial(r_type,   opcode=0b0010011, funct3=0b101, funct7=0b0100000)
ADD        = partial(r_type,   opcode=0b0110011, funct3=0b000, funct7=0b0000000)
SUB        = partial(r_type,   opcode=0b0110011, funct3=0b000, funct7=0b0100000)
SLL        = partial(r_type,   opcode=0b0110011, funct3=0b001, funct7=0b0000000)
SLT        = partial(r_type,   opcode=0b0110011, funct3=0b010, funct7=0b0000000)
SLTU       = partial(r_type,   opcode=0b0110011, funct3=0b011, funct7=0b0000000)
XOR        = partial(r_type,   opcode=0b0110011, funct3=0b100, funct7=0b0000000)
SRL        = partial(r_type,   opcode=0b0110011, funct3=0b101, funct7=0b0000000)
SRA        = partial(r_type,   opcode=0b0110011, funct3=0b101, funct7=0b0100000)
OR         = partial(r_type,   opcode=0b0110011, funct3=0b110, funct7=0b0000000)
AND        = partial(r_type,   opcode=0b0110011, funct3=0b111, funct7=0b0000000)
FENCE      = partial(fence,    opcode=0b0001111, funct3=0b000, rd=0, rs1=0, fm=0)  # special syntax (unique)
ECALL      = partial(i_type,   opcode=0b1110011, funct3=0b000, rd=0, rs1=0, imm=0)  # special syntax (arity)
EBREAK     = partial(i_type,   opcode=0b1110011, funct3=0b000, rd=0, rs1=0, imm=1)  # special syntax (arity)

# RV32M Standard Extension for Integer Multiplication and Division
MUL        = partial(r_type,   opcode=0b0110011, funct3=0b000, funct7=0b0000001)
MULH       = partial(r_type,   opcode=0b0110011, funct3=0b001, funct7=0b0000001)
MULHSU     = partial(r_type,   opcode=0b0110011, funct3=0b010, funct7=0b0000001)
MULHU      = partial(r_type,   opcode=0b0110011, funct3=0b011, funct7=0b0000001)
DIV        = partial(r_type,   opcode=0b0110011, funct3=0b100, funct7=0b0000001)
DIVU       = partial(r_type,   opcode=0b0110011, funct3=0b101, funct7=0b0000001)
REM        = partial(r_type,   opcode=0b0110011, funct3=0b110, funct7=0b0000001)
REMU       = partial(r_type,   opcode=0b0110011, funct3=0b111, funct7=0b0000001)

# RV32A Standard Extension for Atomic Instructions
LR_W       = partial(a_type,   opcode=0b0101111, funct3=0b010, funct5=0b00010, rs2=0)  # special syntax (arity)
SC_W       = partial(a_type,   opcode=0b0101111, funct3=0b010, funct5=0b00011)
AMOSWAP_W  = partial(a_type,   opcode=0b0101111, funct3=0b010, funct5=0b00001)
AMOADD_W   = partial(a_type,   opcode=0b0101111, funct3=0b010, funct5=0b00000)
AMOXOR_W   = partial(a_type,   opcode=0b0101111, funct3=0b010, funct5=0b00100)
AMOAND_W   = partial(a_type,   opcode=0b0101111, funct3=0b010, funct5=0b01100)
AMOOR_W    = partial(a_type,   opcode=0b0101111, funct3=0b010, funct5=0b01000)
AMOMIN_W   = partial(a_type,   opcode=0b0101111, funct3=0b010, funct5=0b10000)
AMOMAX_W   = partial(a_type,   opcode=0b0101111, funct3=0b010, funct5=0b10100)
AMOMINU_W  = partial(a_type,   opcode=0b0101111, funct3=0b010, funct5=0b11000)
AMOMAXU_W  = partial(a_type,   opcode=0b0101111, funct3=0b010, funct5=0b11100)

# RV32C Standard Extension for Compressed Instructions
# TODO: custom logic for these is diff because the dev still specifies _something_
# TODO: it isn't a "value MUST be foo" like the other special cases
# TODO: maybe just do it as a separate pass? validate_compressed() or something like that
C_ADDI4SPN = partial(ciw_type, opcode=0b00, funct3=0b000)
C_LW       = partial(cl_type,  opcode=0b00, funct3=0b010)
C_SW       = partial(cs_type,  opcode=0b00, funct3=0b110)
C_NOP      = partial(ci_type,  opcode=0b01, funct3=0b000, rd_rs1=0, imm=0)  # special syntax (arity)
C_ADDI     = partial(ci_type,  opcode=0b01, funct3=0b000)
C_JAL      = partial(cj_type,  opcode=0b01, funct3=0b001)
C_LI       = partial(ci_type,  opcode=0b01, funct3=0b010)
C_ADDI16SP = partial(cis_type, opcode=0b01, funct3=0b011)
C_LUI      = partial(ci_type,  opcode=0b01, funct3=0b011)
C_SRLI     = partial(cbi_type, opcode=0b01, funct2=0b00, funct3=0b100)
C_SRAI     = partial(cbi_type, opcode=0b01, funct2=0b01, funct3=0b100)
C_ANDI     = partial(cbi_type, opcode=0b01, funct2=0b10, funct3=0b100)
C_SUB      = partial(ca_type,  opcode=0b01, funct2=0b00, funct6=0b100011)
C_XOR      = partial(ca_type,  opcode=0b01, funct2=0b01, funct6=0b100011)
C_OR       = partial(ca_type,  opcode=0b01, funct2=0b10, funct6=0b100011)
C_AND      = partial(ca_type,  opcode=0b01, funct2=0b11, funct6=0b100011)
C_J        = partial(cj_type,  opcode=0b01, funct3=0b101)
C_BEQZ     = partial(cb_type,  opcode=0b01, funct3=0b110)
C_BNEZ     = partial(cb_type,  opcode=0b01, funct3=0b111)
C_SLLI     = partial(ci_type,  opcode=0b10, funct3=0b000)
C_LWSP     = partial(cls_type, opcode=0b10, funct3=0b010)
C_JR       = partial(cr_type,  opcode=0b10, funct4=0b1000)
C_MV       = partial(cr_type,  opcode=0b10, funct4=0b1000)
C_JALR     = partial(cr_type,  opcode=0b10, funct4=0b1001)
C_ADD      = partial(cr_type,  opcode=0b10, funct4=0b1001)
C_SWSP     = partial(css_type, opcode=0b10, funct3=0b110)


R_TYPE_INSTRUCTIONS = {
    'slli':       SLLI,
    'srli':       SRLI,
    'srai':       SRAI,
    'add':        ADD,
    'sub':        SUB,
    'sll':        SLL,
    'slt':        SLT,
    'sltu':       SLTU,
    'xor':        XOR,
    'srl':        SRL,
    'sra':        SRA,
    'or':         OR,
    'and':        AND,
    'mul':        MUL,
    'mulh':       MULH,
    'mulhsu':     MULHSU,
    'mulhu':      MULHU,
    'div':        DIV,
    'divu':       DIVU,
    'rem':        REM,
    'remu':       REMU,
}

I_TYPE_INSTRUCTIONS = {
    'jalr':       JALR,
    'lb':         LB,
    'lh':         LH,
    'lw':         LW,
    'lbu':        LBU,
    'lhu':        LHU,
    'addi':       ADDI,
    'slti':       SLTI,
    'sltiu':      SLTIU,
    'xori':       XORI,
    'ori':        ORI,
    'andi':       ANDI,
}

IE_TYPE_INSTRUCTIONS = {
    'ecall':      ECALL,
    'ebreak':     EBREAK,
}

S_TYPE_INSTRUCTIONS = {
    'sb':         SB,
    'sh':         SH,
    'sw':         SW,
}

B_TYPE_INSTRUCTIONS = {
    'beq':        BEQ,
    'bne':        BNE,
    'blt':        BLT,
    'bge':        BGE,
    'bltu':       BLTU,
    'bgeu':       BGEU,
}

U_TYPE_INSTRUCTIONS = {
    'lui':        LUI,
    'auipc':      AUIPC,
}

J_TYPE_INSTRUCTIONS = {
    'jal':        JAL,
}

FENCE_INSTRUCTIONS = {
    'fence':      FENCE,
}

A_TYPE_INSTRUCTIONS = {
    'sc.w':       SC_W,
    'amoswap.w':  AMOSWAP_W,
    'amoadd.w':   AMOADD_W,
    'amoxor.w':   AMOXOR_W,
    'amoand.w':   AMOAND_W,
    'amoor.w':    AMOOR_W,
    'amomin.w':   AMOMIN_W,
    'amomax.w':   AMOMAX_W,
    'amominu.w':  AMOMINU_W,
    'amomaxu.w':  AMOMAXU_W,
}

AL_TYPE_INSTRUCTIONS = {
    'lr.w':       LR_W,
}

CR_TYPE_INSTRUCTIONS = {
    'c.jr':       C_JR,
    'c.mv':       C_MV,
    'c.jalr':     C_JALR,
    'c.add':      C_ADD,
}

CI_TYPE_INSTRUCTIONS = {
    'c.nop':      C_NOP,
    'c.addi':     C_ADDI,
    'c.li':       C_LI,
    'c.lui':      C_LUI,
    'c.slli':     C_SLLI,
}

CIS_TYPE_INSTRUCTIONS = {
    'c.addi16sp': C_ADDI16SP,
}

CLS_TYPE_INSTRUCTIONS = {
    'c.lwsp':     C_LWSP,    
}

CSS_TYPE_INSTRUCTIONS = {
    'c.swsp':     C_SWSP,
}

CIW_TYPE_INSTRUCTIONS = {
    'c.addi4spn': C_ADDI4SPN,
}

CL_TYPE_INSTRUCTIONS = {
    'c.lw':       C_LW,
}

CS_TYPE_INSTRUCTIONS = {
    'c.sw':       C_SW,
}

CA_TYPE_INSTRUCTIONS = {
    'c.sub':      C_SUB,
    'c.xor':      C_XOR,
    'c.or':       C_OR,
    'c.and':      C_AND,
}

CB_TYPE_INSTRUCTIONS = {
    'c.beqz':     C_BEQZ,
    'b.bnez':     C_BNEZ,
}

CBI_TYPE_INSTRUCTIONS = {
    'c.srli':     C_SRLI,
    'c.srai':     C_SRAI,
    'c.andi':     C_ANDI,
}

CJ_TYPE_INSTRUCTIONS = {
    'c.jal':      C_JAL,
    'c.j':        C_J,
}

INSTRUCTIONS = {}
INSTRUCTIONS.update(R_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(I_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(IE_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(S_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(B_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(U_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(J_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(FENCE_INSTRUCTIONS)
INSTRUCTIONS.update(A_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(AL_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(CR_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(CI_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(CIS_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(CLS_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(CSS_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(CIW_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(CL_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(CS_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(CA_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(CB_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(CBI_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(CJ_TYPE_INSTRUCTIONS)

PSEUDO_INSTRUCTIONS = {
    'nop',
    'li',
    'mv',
    'not',
    'neg',
    'seqz',
    'snez',
    'sltz',
    'sgtz',

    'beqz',
    'bnez',
    'blez',
    'bgez',
    'bltz',
    'bgtz',

    'bgt',
    'ble',
    'bgtu',
    'bleu',

    'j',
    'jal',
    'jr',
    'jalr',
    'ret',
    'call',
    'tail',

    'fence',
}

# alternate offset syntax applies to insts w/ base reg + offset imm
BASE_OFFSET_INSTRUCTIONS = {
    'jalr',
    'lb',
    'lh',
    'lw',
    'lbu',
    'lhu',
    'sb',
    'sh',
    'sw',
}

SHORTHAND_PACK_NAMES = {
    'db',
    'dh',
    'dw',
}

KEYWORDS = {
    'string',
    'bytes',
    'pack',
    'align',
}
KEYWORDS.update(INSTRUCTIONS.keys())
KEYWORDS.update(PSEUDO_INSTRUCTIONS)
KEYWORDS.update(SHORTHAND_PACK_NAMES)


def is_int(value):
    try:
        int(value)
        return True
    except:
        return False


def sign_extend(value, bits):
    sign_bit = 1 << (bits - 1)
    return (value & (sign_bit - 1)) - (value & sign_bit)


def relocate_hi(imm):
    if imm & 0x800:
        imm += 2**12
    return sign_extend((imm >> 12) & 0x000fffff, 20)


def relocate_lo(imm):
    return sign_extend(imm & 0x00000fff, 12)


class Line:

    def __init__(self, file, number, contents):
        self.file = file
        self.number = number
        self.contents = contents

    def __len__(self):
        return len(self.contents)

    def __repr__(self):
        return '{}({!r}, {!r}, {!r})'.format(type(self).__name__, self.file, self.number, self.contents)

    def __str__(self):
        return 'File "{}", line {}: {}'.format(self.file, self.number, self.contents)


class LineTokens:

    def __init__(self, line, tokens):
        self.line = line
        self.tokens = tokens

    def __len__(self):
        return len(self.tokens)

    def __repr__(self):
        return '{}({!r}, {!r})'.format(type(self).__name__, self.line, self.tokens)

    def __str__(self):
        return str(self.tokens)


class Immediate(abc.ABC):

    @abc.abstractmethod
    def eval(self, position, env, line):
        """Evaluate an expression to an integer"""


# arithmetic / lookup / combo of both
# defers evaulation to Python's builtin eval (RIP double-slash comments)
class Arithmetic(Immediate):

    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        return '{}({!r})'.format(type(self).__name__, self.expr)

    # be sure to not leak internal python exceptions out of this
    def eval(self, position, env, line):
        try:
            return eval(self.expr, env)
        except SyntaxError:
            raise AssemblerError('invalid syntax in expr: "{}"'.format(self.expr), line)
        except TypeError:
            raise AssemblerError('unknown variable in expr: "{}"'.format(self.expr), line)
        except:
            raise AssemblerError('other error in expr: "{}"'.format(self.expr), line)


class Position(Immediate):

    def __init__(self, reference, expr):
        self.reference = reference
        self.expr = expr

    def __repr__(self):
        return '{}({!r}, {!r})'.format(type(self).__name__, self.reference, self.expr)

    def eval(self, position, env, line):
        dest = env[self.reference]
        base = self.expr.eval(position, env, line)
        return base + dest


class Offset(Immediate):

    def __init__(self, reference):
        self.reference = reference

    def __repr__(self):
        return '{}({!r})'.format(type(self).__name__, self.reference)

    def eval(self, position, env, line):
        dest = env[self.reference]
        return dest - position


class Hi(Immediate):

    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        return '{}({!r})'.format(type(self).__name__, self.expr)

    def eval(self, position, env, line):
        value = self.expr.eval(position, env, line)
        return relocate_hi(value)


class Lo(Immediate):

    def __init__(self, expr) -> None:
        self.expr = expr

    def __repr__(self):
        return '{}({!r})'.format(type(self).__name__, self.expr)

    def eval(self, position, env, line):
        value = self.expr.eval(position, env, line)
        return relocate_lo(value)


# base class for assembly "things"
class Item(abc.ABC):

    def __init__(self, line):
        self.line = line

    @abc.abstractmethod
    def size(self, position):
        """Check the size of this item at the given position in a program"""


class Align(Item):

    def __init__(self, line, alignment):
        super().__init__(line)
        self.alignment = alignment

    def __repr__(self):
        return '{}({!r})'.format(type(self).__name__, self.alignment)

    def size(self, position):
        padding = self.alignment - (position % self.alignment)
        if padding == self.alignment:
            return 0
        else:
            return padding


class Label(Item):

    def __init__(self, line, name):
        super().__init__(line)
        self.name = name

    def __repr__(self):
        return '{}({!r})'.format(type(self).__name__, self.name)

    def size(self, position):
        return 0


class Constant(Item):

    def __init__(self, line, name, imm):
        super().__init__(line)
        self.name = name
        self.imm = imm

    def __repr__(self):
        return '{}(name={!r}, imm={!r})'.format(type(self).__name__, self.name, self.imm)

    def size(self, position):
        return 0


class Bytes(Item):

    def __init__(self, line, values):
        super().__init__(line)
        self.values = values

    def __repr__(self):
        return '{}({!r})'.format(type(self).__name__, self.values)

    def size(self, position):
        # this works because each byte occupies 1 byte
        return len(self.values)


class String(Item):

    def __init__(self, line, value):
        super().__init__(line)
        self.value = value

    def __repr__(self):
        return '{}({!r})'.format(type(self).__name__, self.value)

    def size(self, position):
        return len(self.value.encode('utf-8'))


class Pack(Item):

    def __init__(self, line, fmt, imm):
        super().__init__(line)
        self.fmt = fmt
        self.imm = imm

    def __repr__(self):
        return '{}(fmt={!r}, imm={!r})'.format(type(self).__name__, self.fmt, self.imm)

    def size(self, position):
        return struct.calcsize(self.fmt)


class ShorthandPack(Item):

    def __init__(self, line, name, imm):
        super().__init__(line)
        self.name = name
        self.imm = imm

    def __repr__(self):
        return '{}(name={!r}, imm={!r})'.format(type(self).__name__, self.name, self.imm)

    def size(self, position):
        sizes = {
            'db': 1,
            'dh': 2,
            'dw': 4,
        }
        return sizes[self.name]


class Blob(Item):

    def __init__(self, line, data):
        super().__init__(line)
        self.data = data

    def __repr__(self):
        # repr is still "correct", just wanted a more consistent hex format
        s = ''.join(['\\x{:02x}'.format(b) for b in self.data])
        return "{}(b'{}')".format(type(self).__name__, s)

    def size(self, position):
        return len(self.data)


class Instruction(Item):

    def size(self, position):
        return 4


class CompressedInstruction(Instruction):

    def size(self, position):
        return 2


class RTypeInstruction(Instruction):

    def __init__(self, line, name, rd, rs1, rs2):
        super().__init__(line)
        self.name = name
        self.rd = rd
        self.rs1 = rs1
        self.rs2 = rs2

    def __repr__(self):
        return '{}({!r}, rd={!r}, rs1={!r}, rs2={!r})'.format(type(self).__name__, self.name, self.rd, self.rs1, self.rs2)


class ITypeInstruction(Instruction):

    def __init__(self, line, name, rd, rs1, imm):
        super().__init__(line)
        self.name = name
        self.rd = rd
        self.rs1 = rs1
        self.imm = imm

    def __repr__(self):
        return '{}({!r}, rd={!r}, rs1={!r}, imm={!r})'.format(type(self).__name__, self.name, self.rd, self.rs1, self.imm)


# custom syntax for ecall / ebreak insts
class IETypeInstruction(Instruction):

    def __init__(self, line, name):
        super().__init__(line)
        self.name = name

    def __repr__(self):
        return '{}({!r})'.format(type(self).__name__, self.name)


class STypeInstruction(Instruction):

    def __init__(self, line, name, rs1, rs2, imm):
        super().__init__(line)
        self.name = name
        self.rs1 = rs1
        self.rs2 = rs2
        self.imm = imm

    def __repr__(self):
        return '{}({!r}, rs1={!r}, rs2={!r}, imm={!r})'.format(type(self).__name__, self.name, self.rs1, self.rs2, self.imm)


class BTypeInstruction(Instruction):

    def __init__(self, line, name, rs1, rs2, imm):
        super().__init__(line)
        self.name = name
        self.rs1 = rs1
        self.rs2 = rs2
        self.imm = imm

    def __repr__(self):
        return '{}({!r}, rs1={!r}, rs2={!r}, imm={!r})'.format(type(self).__name__, self.name, self.rs1, self.rs2, self.imm)


class UTypeInstruction(Instruction):

    def __init__(self, line, name, rd, imm):
        super().__init__(line)
        self.name = name
        self.rd = rd
        self.imm = imm

    def __repr__(self):
        return '{}({!r}, rd={!r}, imm={!r})'.format(type(self).__name__, self.name, self.rd, self.imm)


class JTypeInstruction(Instruction):

    def __init__(self, line, name, rd, imm):
        super().__init__(line)
        self.name = name
        self.rd = rd
        self.imm = imm

    def __repr__(self):
        return '{}({!r}, rd={!r}, imm={!r})'.format(type(self).__name__, self.name, self.rd, self.imm)


# custom syntax for fence inst
class FenceInstruction(Instruction):

    def __init__(self, line, name, succ, pred):
        super().__init__(line)
        self.name = name
        self.succ = succ
        self.pred = pred

    def __repr__(self):
        return '{}({!r}, succ={!r}, pred={!r})'.format(type(self).__name__, self.name, self.succ, self.pred)


class ATypeInstruction(Instruction):

    def __init__(self, line, name, rd, rs1, rs2, aq=0, rl=0):
        super().__init__(line)
        self.name = name
        self.rd = rd
        self.rs1 = rs1
        self.rs2 = rs2
        self.aq = aq
        self.rl = rl

    def __repr__(self):
        s = '{}({!r}, rd={!r}, rs1={!r}, rs2={!r}, aq={!r}, rl={!r})'
        s = s.format(type(self).__name__, self.name, self.rd, self.rs1, self.rs2, self.aq, self.rl)
        return s


# custom syntax for lr.w inst
class ALTypeInstruction(Instruction):

    def __init__(self, line, name, rd, rs1, aq=0, rl=0):
        super().__init__(line)
        self.name = name
        self.rd = rd
        self.rs1 = rs1
        self.aq = aq
        self.rl = rl

    def __repr__(self):
        s = '{}({!r}, rd={!r}, rs1={!r}, aq={!r}, rl={!r})'
        s = s.format(type(self).__name__, self.name, self.rd, self.rs1, self.aq, self.rl)
        return s


# TODO: classes for compressed instruction types


class PseudoInstruction(Instruction):

    def __init__(self, line, name, *args):
        super().__init__(line)
        self.name = name
        self.args = args

    def __repr__(self):
        s = '{}({!r}, args={!r})'
        s = s.format(type(self).__name__, self.name, self.args)
        return s

    def size(self, position):
        # some pseudo-instructions expand into 2 regular ones
        if self.name in ['li', 'call', 'tail']:
            return 8
        else:
            return 4


def read_lines(path_or_source):
    if os.path.exists(path_or_source):
        path = path_or_source
        with open(path) as f:
            source = f.read()
    else:
        path = '<string>'
        source = path_or_source

    lines = []
    for i, line in enumerate(source.splitlines(), start=1):
        # skip empty lines
        if len(line.strip()) == 0:
            continue
        lines.append(Line(path, i, line))

    return lines


RE_STRING = re.compile(r'\s*string (.*)')

def lex_tokens(line):
    # simplify lexing a single string
    if type(line) == str:
        line = Line('<string>', 1, line)

    # check for string literals (needs custom lexing)
    match = RE_STRING.match(line.contents)
    if match is not None:
        value = match.group(1)
        value = value.encode('utf-8').decode('unicode_escape')
        tokens = ['string', value]
        return LineTokens(line, tokens)

    # strip comments
    contents = re.sub(r'#.*$', r'', line.contents, flags=re.MULTILINE)
    # pad parens before split
    contents = contents.replace('(', ' ( ').replace(')', ' ) ')
    # strip whitespace
    contents = contents.strip()
    # skip empty lines
    if len(contents) == 0:
        return LineTokens(line, [])
    # split line into tokens
    tokens = re.split(r'[\s,\'"]+', contents)
    # remove empty tokens
    while '' in tokens:
        tokens.remove('')
    # carry the line and its tokens forward
    return LineTokens(line, tokens)


# helper for parsing immediates since they occur in multiple places
def parse_immediate(imm):
    head = imm[0].lower()
    if head == '%position':
        if imm[1] == '(':
            _, _, reference, *imm, _ = imm
        else:
            _, reference, *imm = imm
        return Position(reference, Arithmetic(' '.join(imm)))
    elif head == '%offset':
        if imm[1] == '(':
            _, _, reference, _ = imm
        else:
            _, reference = imm
        return Offset(reference)
    elif head == '%hi':
        if imm[1] == '(':
            _, _, *imm, _ = imm
        else:
            _, *imm = imm
        return Hi(parse_immediate(imm))
    elif head == '%lo':
        if imm[1] == '(':
            _, _, *imm, _ = imm
        else:
            _, *imm = imm
        return Lo(parse_immediate(imm))
    else:
        return Arithmetic(' '.join(imm))


def parse_item(line_tokens):
    line = line_tokens.line
    tokens = line_tokens.tokens
    head = tokens[0].lower()

    # labels
    if len(tokens) == 1 and tokens[0].endswith(':'):
        name = tokens[0].rstrip(':')
        return Label(line, name)
    # constants
    elif len(tokens) >= 3 and tokens[1] == '=':
        name, _, *imm = tokens
        imm = parse_immediate(imm)
        return Constant(line, name, imm)
    # aligns
    elif head == 'align':
        _, alignment = tokens
        try:
            alignment = int(alignment, base=0)
        except ValueError:
            raise AssemblerError('alignment must be an integer', line)
        return Align(line, alignment)
    # packs
    elif head == 'pack':
        _, fmt, *imm = tokens
        imm = parse_immediate(imm)
        return Pack(line, fmt, imm)
    # shorthand packs
    elif head in SHORTHAND_PACK_NAMES:
        name, *imm = tokens
        imm = parse_immediate(imm)
        return ShorthandPack(line, name, imm)
    # bytes
    elif head == 'bytes':
        _, *values = tokens
        return Bytes(line, values)
    # strings
    elif head == 'string':
        _, value = tokens
        return String(line, value)
    # r-type instructions
    elif head in R_TYPE_INSTRUCTIONS:
        if len(tokens) != 4:
            raise AssemblerError('r-type instructions require exactly 3 args', line)
        name, rd, rs1, rs2 = tokens
        name = name.lower()
        return RTypeInstruction(line, name, rd, rs1, rs2)
    # i-type instructions
    elif head in I_TYPE_INSTRUCTIONS:
        # check for jalr PI
        if len(tokens) == 2:
            name, *args = tokens
            name = name.lower()
            return PseudoInstruction(line, name, *args)
        if tokens[0].lower() in BASE_OFFSET_INSTRUCTIONS and tokens[3] == '(':
            name, rd, offset, _, rs1, _ = tokens
            imm = [offset]
        else:
            name, rd, rs1, *imm = tokens
        name = name.lower()
        imm = parse_immediate(imm)
        return ITypeInstruction(line, name, rd, rs1, imm)
    # ie-type instructions
    elif head in IE_TYPE_INSTRUCTIONS:
        name, = tokens
        name = name.lower()
        return IETypeInstruction(line, name)
    # s-type instructions (all are base offset insts)
    elif head in S_TYPE_INSTRUCTIONS:
        if tokens[3] == '(':
            name, rs2, offset, _, rs1, _ = tokens
            imm = [offset]
        else:
            name, rs1, rs2, *imm = tokens
        name = name.lower()
        imm = parse_immediate(imm)
        return STypeInstruction(line, name, rs1, rs2, imm)
    # b-type instructions
    elif head in B_TYPE_INSTRUCTIONS:
        if len(tokens) != 4:
            raise AssemblerError('b-type instructions require 3 args', line)
        name, rs1, rs2, reference = tokens
        name = name.lower()
        if is_int(reference):
            imm = [reference]
        else:
            # behavior is "offset" for branches to labels
            imm = ['%offset', reference]
        imm = parse_immediate(imm)
        return BTypeInstruction(line, name, rs1, rs2, imm)
    # u-type instructions
    elif head in U_TYPE_INSTRUCTIONS:
        name, rd, *imm = tokens
        name = name.lower()
        imm = parse_immediate(imm)
        return UTypeInstruction(line, name, rd, imm)
    # j-type instructions
    elif head in J_TYPE_INSTRUCTIONS:
        # check for jal PI
        if len(tokens) == 2:
            name, *args = tokens
            name = name.lower()
            return PseudoInstruction(line, name, *args)
        if len(tokens) != 3:
            raise AssemblerError('j-type instructions require 1 or 2 args', line)
        name, rd, reference = tokens
        name = name.lower()
        if is_int(reference):
            imm = [reference]
        else:
            # behavior is "offset" for jumps to labels
            imm = ['%offset', reference]
        imm = parse_immediate(imm)
        return JTypeInstruction(line, name, rd, imm)
    # fence instructions
    elif head in FENCE_INSTRUCTIONS:
        # check for fence PI
        if len(tokens) == 1:
            name, *args = tokens
            name = name.lower()
            return PseudoInstruction(line, name, *args)
        if len(tokens) != 3:
            raise AssemblerError('fence instructions require 0 or 2 args', line)
        name, succ, pred = tokens
        name = name.lower()
        return FenceInstruction(line, name, succ, pred)
    # a-type instructions
    elif head in A_TYPE_INSTRUCTIONS:
        name, rd, rs1, rs2, *ordering = tokens
        name = name.lower()
        # check for specific ordering bits
        if len(ordering) == 0:
            aq, rl = 0, 0
        elif len(ordering) == 2:
            aq, rl = ordering
        else:
            raise AssemblerError('invalid syntax for atomic instruction', line)
        return ATypeInstruction(line, name, rd, rs1, rs2, aq, rl)
    # al-type instructions
    elif head in AL_TYPE_INSTRUCTIONS:
        name, rd, rs1, *ordering = tokens
        name = name.lower()
        # check for specific ordering bits
        if len(ordering) == 0:
            aq, rl = 0, 0
        elif len(ordering) == 2:
            aq, rl = ordering
        else:
            raise AssemblerError('invalid syntax for atomic instruction', line)
        return ALTypeInstruction(line, name, rd, rs1, aq, rl)
    # TODO: compressed instructions
    elif head in PSEUDO_INSTRUCTIONS:
        name, *args = tokens
        name = name.lower()
        return PseudoInstruction(line, name, *args)
    else:
        raise AssemblerError('invalid syntax', line)
        


def transform_pseudo_instructions(items):
    new_items = []
    for item in items:
        # save an indent by early-exiting non PIs
        if not isinstance(item, PseudoInstruction):
            new_items.append(item)
            continue

        if item.name == 'nop':
            inst = ITypeInstruction(item.line, 'addi', rd='x0', rs1='x0', imm=Arithmetic('0'))
            new_items.append(inst)
        elif item.name == 'li':
            rd, *imm = item.args
            imm = parse_immediate(imm)
            inst = UTypeInstruction(item.line, 'lui', rd=rd, imm=Hi(imm))
            new_items.append(inst)
            inst = ITypeInstruction(item.line, 'addi', rd=rd, rs1=rd, imm=Lo(imm))
            new_items.append(inst)
        elif item.name == 'mv':
            rd, rs = item.args
            inst = ITypeInstruction(item.line, 'addi', rd=rd, rs1=rs, imm=Arithmetic('0'))
            new_items.append(inst)
        elif item.name == 'not':
            rd, rs = item.args
            inst = ITypeInstruction(item.line, 'xori', rd=rd, rs1=rs, imm=Arithmetic('-1'))
            new_items.append(inst)
        elif item.name == 'neg':
            rd, rs = item.args
            inst = RTypeInstruction(item.line, 'sub', rd=rd, rs1='x0', rs2=rs)
            new_items.append(inst)
        elif item.name == 'seqz':
            rd, rs = item.args
            inst = ITypeInstruction(item.line, 'sltiu', rd=rd, rs1=rs, imm=Arithmetic('1'))
            new_items.append(inst)
        elif item.name == 'snez':
            rd, rs = item.args
            inst = RTypeInstruction(item.line, 'sltu', rd=rd, rs1='x0', rs2=rs)
            new_items.append(inst)
        elif item.name == 'sltz':
            rd, rs = item.args
            inst = RTypeInstruction(item.line, 'slt', rd=rd, rs1=rs, rs2='x0')
            new_items.append(inst)
        elif item.name == 'sgtz':
            rd, rs = item.args
            inst = RTypeInstruction(item.line, 'slt', rd=rd, rs1='x0', rs2=rs)
            new_items.append(inst)

        elif item.name == 'beqz':
            rs, reference = item.args
            imm = ['%offset', reference]
            imm = parse_immediate(imm)
            inst = BTypeInstruction(item.line, 'beq', rs1=rs, rs2='x0', imm=imm)
            new_items.append(inst)
        elif item.name == 'bnez':
            rs, reference = item.args
            imm = ['%offset', reference]
            imm = parse_immediate(imm)
            inst = BTypeInstruction(item.line, 'bne', rs1=rs, rs2='x0', imm=imm)
            new_items.append(inst)
        elif item.name == 'blez':
            rs, reference = item.args
            imm = ['%offset', reference]
            imm = parse_immediate(imm)
            inst = BTypeInstruction(item.line, 'bge', rs1='x0', rs2=rs, imm=imm)
            new_items.append(inst)
        elif item.name == 'bgez':
            rs, reference = item.args
            imm = ['%offset', reference]
            imm = parse_immediate(imm)
            inst = BTypeInstruction(item.line, 'bge', rs1=rs, rs2='x0', imm=imm)
            new_items.append(inst)
        elif item.name == 'bltz':
            rs, reference = item.args
            imm = ['%offset', reference]
            imm = parse_immediate(imm)
            inst = BTypeInstruction(item.line, 'blt', rs1=rs, rs2='x0', imm=imm)
            new_items.append(inst)
        elif item.name == 'bgtz':
            rs, reference = item.args
            imm = ['%offset', reference]
            imm = parse_immediate(imm)
            inst = BTypeInstruction(item.line, 'blt', rs1='x0', rs2=rs, imm=imm)
            new_items.append(inst)

        elif item.name == 'bgt':
            rs, rt, reference = item.args
            imm = ['%offset', reference]
            imm = parse_immediate(imm)
            inst = BTypeInstruction(item.line, 'blt', rs1=rt, rs2=rs, imm=imm)
            new_items.append(inst)
        elif item.name == 'ble':
            rs, rt, reference = item.args
            imm = ['%offset', reference]
            imm = parse_immediate(imm)
            inst = BTypeInstruction(item.line, 'bge', rs1=rt, rs2=rs, imm=imm)
            new_items.append(inst)
        elif item.name == 'bgtu':
            rs, rt, reference = item.args
            imm = ['%offset', reference]
            imm = parse_immediate(imm)
            inst = BTypeInstruction(item.line, 'bltu', rs1=rt, rs2=rs, imm=imm)
            new_items.append(inst)
        elif item.name == 'bleu':
            rs, rt, reference = item.args
            imm = ['%offset', reference]
            imm = parse_immediate(imm)
            inst = BTypeInstruction(item.line, 'bgeu', rs1=rt, rs2=rs, imm=imm)
            new_items.append(inst)

        elif item.name == 'j':
            reference, = item.args
            imm = ['%offset', reference]
            imm = parse_immediate(imm)
            inst = JTypeInstruction(item.line, 'jal', rd='x0', imm=imm)
            new_items.append(inst)
        elif item.name == 'jal':
            reference, = item.args
            imm = ['%offset', reference]
            imm = parse_immediate(imm)
            inst = JTypeInstruction(item.line, 'jal', rd='x1', imm=imm)
            new_items.append(inst)
        elif item.name == 'jr':
            rs, = item.args
            inst = ITypeInstruction(item.line, 'jalr', rd='x0', rs1=rs, imm=Arithmetic('0'))
            new_items.append(inst)
        elif item.name == 'jalr':
            rs, = item.args
            inst = ITypeInstruction(item.line, 'jalr', rd='x1', rs1=rs, imm=Arithmetic('0'))
            new_items.append(inst)
        elif item.name == 'ret':
            inst = ITypeInstruction(item.line, 'jalr', rd='x0', rs1='x1', imm=Arithmetic('0'))
            new_items.append(inst)
        elif item.name == 'call':
            imm = parse_immediate(item.args)
            inst = UTypeInstruction(item.line, 'auipc', rd='x1', imm=Hi(imm))
            new_items.append(inst)
            inst = ITypeInstruction(item.line, 'jalr', rd='x1', rs1='x1', imm=Lo(imm))
            new_items.append(inst)
        elif item.name == 'tail':
            imm = parse_immediate(item.args)
            inst = UTypeInstruction(item.line, 'auipc', rd='x6', imm=Hi(imm))
            new_items.append(inst)
            inst = ITypeInstruction(item.line, 'jalr', rd='x0', rs1='x6', imm=Lo(imm))
            new_items.append(inst)

        elif item.name == 'fence':
            inst = FenceInstruction(item.line, 'fence', succ=0b1111, pred=0b1111)
            new_items.append(inst)

        else:
            raise AssemblerError('no translation for pseudo-instruction: {}'.format(item.name), item.line)

    return new_items


def resolve_aligns(items):
    position = 0
    new_items = []
    for item in items:
        if not isinstance(item, Align):
            position += item.size(position)
            new_items.append(item)
            continue

        padding = item.size(position)
        position += padding
        blob = Blob(item.line, b'\x00' * padding)
        new_items.append(blob)

    return new_items


def resolve_labels(items, env):
    new_env = copy.deepcopy(env)

    position = 0
    new_items = []
    for item in items:
        if not isinstance(item, Label):
            position += item.size(position)
            new_items.append(item)
            continue

        new_env[item.name] = position

    return new_items, new_env


def resolve_constants(items, env):
    new_env = copy.deepcopy(env)

    position = 0
    new_items = []
    for item in items:
        if not isinstance(item, Constant):
            position += item.size(position)
            new_items.append(item)
            continue

        if item.name in REGISTERS:
            raise AssemblerError('constant name shadows register name "{}"'.format(item.name), item.line)
        new_env[item.name] = item.imm.eval(position, new_env, item.line)

    return new_items, new_env


def resolve_registers(items, env):
    new_items = []
    for item in items:
        if isinstance(item, RTypeInstruction):
            rd = env.get(item.rd, item.rd)
            rs1 = env.get(item.rs1, item.rs1)
            rs2 = env.get(item.rs2, item.rs2)
            inst = RTypeInstruction(item.line, item.name, rd, rs1, rs2)
            new_items.append(inst)
        elif isinstance(item, ITypeInstruction):
            rd = env.get(item.rd, item.rd)
            rs1 = env.get(item.rs1, item.rs1)
            inst = ITypeInstruction(item.line, item.name, rd, rs1, item.imm)
            new_items.append(inst)
        elif isinstance(item, STypeInstruction):
            rs1 = env.get(item.rs1, item.rs1)
            rs2 = env.get(item.rs2, item.rs2)
            inst = STypeInstruction(item.line, item.name, rs1, rs2, item.imm)
            new_items.append(inst)
        elif isinstance(item, BTypeInstruction):
            rs1 = env.get(item.rs1, item.rs1)
            rs2 = env.get(item.rs2, item.rs2)
            inst = BTypeInstruction(item.line, item.name, rs1, rs2, item.imm)
            new_items.append(inst)
        elif isinstance(item, UTypeInstruction):
            rd = env.get(item.rd, item.rd)
            inst = UTypeInstruction(item.line, item.name, rd, item.imm)
            new_items.append(inst)
        elif isinstance(item, JTypeInstruction):
            rd = env.get(item.rd, item.rd)
            inst = JTypeInstruction(item.line, item.name, rd, item.imm)
            new_items.append(inst)
        elif isinstance(item, ATypeInstruction):
            rd = env.get(item.rd, item.rd)
            rs1 = env.get(item.rs1, item.rs1)
            rs2 = env.get(item.rs2, item.rs2)
            inst = ATypeInstruction(item.line, item.name, rd, rs1, rs2, item.aq, item.rl)
            new_items.append(inst)
        elif isinstance(item, ALTypeInstruction):
            rd = env.get(item.rd, item.rd)
            rs1 = env.get(item.rs1, item.rs1)
            inst = ALTypeInstruction(item.line, item.name, rd, rs1, item.aq, item.rl)
            new_items.append(inst)
        # TODO: compressed instructions
        else:
            new_items.append(item)

    return new_items


def resolve_immediates(items, env):
    position = 0
    new_items = []
    for item in items:
        if isinstance(item, ITypeInstruction):
            imm = item.imm.eval(position, env, item.line)
            position += item.size(position)
            inst = ITypeInstruction(item.line, item.name, item.rd, item.rs1, imm)
            new_items.append(inst)
        elif isinstance(item, STypeInstruction):
            imm = item.imm.eval(position, env, item.line)
            position += item.size(position)
            inst = STypeInstruction(item.line, item.name, item.rs1, item.rs2, imm)
            new_items.append(inst)
        elif isinstance(item, BTypeInstruction):
            imm = item.imm.eval(position, env, item.line)
            position += item.size(position)
            inst = BTypeInstruction(item.line, item.name, item.rs1, item.rs2, imm)
            new_items.append(inst)
        elif isinstance(item, UTypeInstruction):
            imm = item.imm.eval(position, env, item.line)
            position += item.size(position)
            inst = UTypeInstruction(item.line, item.name, item.rd, imm)
            new_items.append(inst)
        elif isinstance(item, JTypeInstruction):
            imm = item.imm.eval(position, env, item.line)
            position += item.size(position)
            inst = JTypeInstruction(item.line, item.name, item.rd, imm)
            new_items.append(inst)
        # TODO: compressed instructions
        elif isinstance(item, Pack):
            imm = item.imm.eval(position, env, item.line)
            position += item.size(position)
            pack = Pack(item.line, item.fmt, imm)
            new_items.append(pack)
        elif isinstance(item, ShorthandPack):
            imm = item.imm.eval(position, env, item.line)
            position += item.size(position)
            pack = ShorthandPack(item.line, item.name, imm)
            new_items.append(pack)
        else:
            position += item.size(position)
            new_items.append(item)

    return new_items


def check_compressible(items):
    # TODO: check if any instructions meet the criteria for a compressed equivalent
    return items


def validate_compressed(items):
    # TODO: ensure compressed inst regs / imms are valid
    # c.addi:     rd/rs1 != 0, nzimm
    # c.li:       rd != 0
    # c.addi16sp: nzimm
    # c.lui:      rd != {0,2}
    # c.srli:     nzimm
    # c.srai:     nzimm
    # c.slli:     rd/rs1 != 0, nzimm
    # c.lwsp:     rd != 0
    # c.jr:       rs1 != 0
    # c.mv:       rd != 0, rs2 != 0
    # c.jalr:     rs1 != 0
    # c.add:      rd/rs1 != 0, rs2 != 0
    return items


def resolve_instructions(items):
    new_items = []
    for item in items:
        if isinstance(item, RTypeInstruction):
            encode_func = INSTRUCTIONS[item.name]
            try:
                code = encode_func(item.rd, item.rs1, item.rs2)
            except ValueError as e:
                raise AssemblerError(str(e), item.line)
            code = struct.pack('<I', code)
            blob = Blob(item.line, code)
            new_items.append(blob)
        elif isinstance(item, ITypeInstruction):
            encode_func = INSTRUCTIONS[item.name]
            try:
                code = encode_func(item.rd, item.rs1, item.imm)
            except ValueError as e:
                raise AssemblerError(str(e), item.line)
            code = struct.pack('<I', code)
            blob = Blob(item.line, code)
            new_items.append(blob)
        elif isinstance(item, IETypeInstruction):
            encode_func = INSTRUCTIONS[item.name]
            try:
                code = encode_func()
            except ValueError as e:
                raise AssemblerError(str(e), item.line)
            code = struct.pack('<I', code)
            blob = Blob(item.line, code)
            new_items.append(blob)
        elif isinstance(item, STypeInstruction):
            encode_func = INSTRUCTIONS[item.name]
            try:
                code = encode_func(item.rs1, item.rs2, item.imm)
            except ValueError as e:
                raise AssemblerError(str(e), item.line)
            code = struct.pack('<I', code)
            blob = Blob(item.line, code)
            new_items.append(blob)
        elif isinstance(item, BTypeInstruction):
            encode_func = INSTRUCTIONS[item.name]
            try:
                code = encode_func(item.rs1, item.rs2, item.imm)
            except ValueError as e:
                raise AssemblerError(str(e), item.line)
            code = struct.pack('<I', code)
            blob = Blob(item.line, code)
            new_items.append(blob)
        elif isinstance(item, UTypeInstruction):
            encode_func = INSTRUCTIONS[item.name]
            try:
                code = encode_func(item.rd, item.imm)
            except ValueError as e:
                raise AssemblerError(str(e), item.line)
            code = struct.pack('<I', code)
            blob = Blob(item.line, code)
            new_items.append(blob)
        elif isinstance(item, JTypeInstruction):
            encode_func = INSTRUCTIONS[item.name]
            try:
                code = encode_func(item.rd, item.imm)
            except ValueError as e:
                raise AssemblerError(str(e), item.line)
            code = struct.pack('<I', code)
            blob = Blob(item.line, code)
            new_items.append(blob)
        elif isinstance(item, FenceInstruction):
            encode_func = INSTRUCTIONS[item.name]
            try:
                code = encode_func(item.succ, item.pred)
            except ValueError as e:
                raise AssemblerError(str(e), item.line)
            code = struct.pack('<I', code)
            blob = Blob(item.line, code)
            new_items.append(blob)
        elif isinstance(item, ATypeInstruction):
            encode_func = INSTRUCTIONS[item.name]
            try:
                code = encode_func(item.rd, item.rs1, item.rs2, aq=item.aq, rl=item.rl)
            except ValueError as e:
                raise AssemblerError(str(e), item.line)
            code = struct.pack('<I', code)
            blob = Blob(item.line, code)
            new_items.append(blob)
        elif isinstance(item, ALTypeInstruction):
            encode_func = INSTRUCTIONS[item.name]
            try:
                code = encode_func(item.rd, item.rs1, aq=item.aq, rl=item.rl)
            except ValueError as e:
                raise AssemblerError(str(e), item.line)
            code = struct.pack('<I', code)
            blob = Blob(item.line, code)
            new_items.append(blob)
        # TODO: compressed instructions
        else:
            new_items.append(item)

    return new_items


def transform_shorthand_packs(items):
    endianness = '<'
    formats = {
        'db': 'B',
        'dh': 'H',
        'dw': 'I',
    }

    new_items = []
    for item in items:
        if not isinstance(item, ShorthandPack):
            new_items.append(item)
            continue

        fmt = endianness + formats[item.name]
        if item.imm < 0:
            fmt = fmt.lower()

        pack = Pack(item.line, fmt, item.imm)
        new_items.append(pack)

    return new_items


def resolve_packs(items):
    new_items = []
    for item in items:
        if not isinstance(item, Pack):
            new_items.append(item)
            continue

        data = struct.pack(item.fmt, item.imm)
        blob = Blob(item.line, data)
        new_items.append(blob)

    return new_items


def resolve_bytes(items):
    new_items = []
    for item in items:
        if not isinstance(item, Bytes):
            new_items.append(item)
            continue

        data = [int(byte, base=0) for byte in item.values]
        for byte in data:
            if byte < 0 or byte > 255:
                raise AssemblerError('bytes literal not in range [0, 255]', line)
        blob = Blob(item.line, bytes(data))
        new_items.append(blob)

    return new_items


def resolve_strings(items):
    new_items = []
    for item in items:
        if not isinstance(item, String):
            new_items.append(item)
            continue

        blob = Blob(item.line, item.value.encode('utf-8'))
        new_items.append(blob)

    return new_items


def resolve_blobs(items):
    output = bytearray()
    for item in items:
        if not isinstance(item, Blob):
            raise ValueError('expected only blobs at this point')

        output.extend(item.data)

    return output


# Passes:
#   - Read -> Lex -> Parse source
#   - Transform pseudo-instructions (expand PIs into regular instructions)
#   - Resolve aligns  (convert aligns to blobs based on position)
#   - Resolve labels  (store label locations into env)
#   - Resolve constants  (eval expr and update env)
#   - Resolve registers  (could be constants for readability)
#   - Resolve immediates  (Arithmetic, Position, Offset, Hi, Lo)
#   - Check compressible  (identify and compress eligible instructions)
#   - Valitate compressed  (validate compressed inst reg / imm values)
#   - Resolve instructions  (convert xTypeInstruction to Blob)
#   - Resolve bytes  (convert Bytes to Blob)
#   - Resolve strings  (convert String to Blob)
#   - Transform shorthand packs (expand shorthand pack syntax into the full syntax)
#   - Resolve packs  (convert Pack to Blob)
#   - Resolve blobs  (merge all Blobs into a single binary)

def assemble(path_or_source, compress=False, verbose=False):
    """
    Assemble a RISC-V assembly program into a raw binary.

    :param path_or_source: Path to an assembly file or raw assembly source
    :returns: Assembled binary as bytes
    """

    # exclude Python builtins from eval env
    # https://docs.python.org/3/library/functions.html#eval
    env = {
        '__builtins__': None,
    }
    env.update(REGISTERS)

    # read, lex, and parse the source
    lines = read_lines(path_or_source)
    lines = [l for l in lines if len(l) > 0]
    tokens = [lex_tokens(l) for l in lines]
    tokens = [t for t in tokens if len(t) > 0]
    items = [parse_item(t) for t in tokens]
    items = [i for i in items if i is not None]

    # run items through each pass
    items = transform_pseudo_instructions(items)
    items = resolve_aligns(items)
    items, env = resolve_labels(items, env)
    items, env = resolve_constants(items, env)
    items = resolve_registers(items, env)
    items = resolve_immediates(items, env)
    if compress:
        items = check_compressible(items)
    items = validate_compressed(items)
    items = resolve_instructions(items)
    items = resolve_bytes(items)
    items = resolve_strings(items)
    items = transform_shorthand_packs(items)
    items = resolve_packs(items)
    program = resolve_blobs(items)

    if verbose:
        # print resolved environment
        succint_env = {k: v for k, v in env.items() if k not in REGISTERS}
        succint_env.pop('__builtins__')
        for k, v in succint_env.items():
            print('{} = {} (0x{:08x})'.format(k, v, v))

    return program


if __name__ == '__main__':
    # TODO: better way to handle this?
    if sys.argv[1] == '--version':
        from bronzebeard import __version__
        version = 'bronzebeard {}'.format(__version__)
        raise SystemExit(version)

    parser = argparse.ArgumentParser(
        description='Assemble RISC-V source code',
        prog='python -m bronzebeard.asm',
    )
    parser.add_argument('input_asm', type=str, help='input source file')
    parser.add_argument('output_bin', type=str, help='output binary file')
    parser.add_argument('--compress', action='store_true', help='identify and compress eligible instructions')
    parser.add_argument('--verbose', action='store_true', help='verbose assembler output')
    parser.add_argument('--version', action='store_true', help='print assembler version and exit')
    args = parser.parse_args()

    try:
        binary = assemble(args.input_asm, args.compress, args.verbose)
    except Exception as e:
        raise SystemExit(e)

    with open(args.output_bin, 'wb') as out_bin:
        out_bin.write(binary)
