import abc
import argparse
import copy
from collections import ChainMap
from ctypes import c_int32, c_uint32
from functools import partial
import logging
import os
import re
import struct
import sys

# Python Cookbook: Section 13.12
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


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
        return '{}\nAssemblerError: {}'.format(self.line, self.message)


def log_constant(pass_name, item, value):
    s = '{}: file {}, line {}: "{}" -> "{} = 0x{:08x} ({})"'
    s = s.format(pass_name, os.path.basename(item.line.file), item.line.number, item, item.name, value, value)
    log.info(s)


def log_conversion(pass_name, item_a, item_b):
    s = '{}: file {}, line {}: "{}" -> "{}"'
    s = s.format(pass_name, os.path.basename(item_a.line.file), item_a.line.number, item_a, item_b)
    log.info(s)


def lookup_register(reg, compressed=False):
    # reg might be a hex / octal value
    try:
        reg = int(reg, base=0)
    except:
        pass

    # at this point, any valid reg will be in the REGISTERS dict
    try:
        reg = REGISTERS[reg]
    except KeyError:
        raise ValueError('register must be a valid integer, name, or alias: {}'.format(reg))

    # check for compressed instruction register, validate and apply
    if compressed:
        # must be in "common" registers: x8-x15
        if reg < 8 or reg > 15:
            raise ValueError('compressed register must be between 8 and 15: {}'.format(reg))
        # subtract 8 to get compressed, 3-bit reg value
        reg -= 8

    return reg


def is_int(value):
    try:
        int(value, base=0)
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


def constraint_not(field, value):
    def inner(**kwargs):
        if kwargs[field] == value:
            raise ValueError('constraint failed: {} must not be {}'.format(field, value))
    return inner


def constraint_bit(field, bit, value):
    def inner(**kwargs):
        if (kwargs[field] & (1 << bit)) != value:
            raise ValueError('constraint failed: bit {} of {} must be {}'.format(bit, field, value))
    return inner


# constraints used to validate compressed instruction fields
RegRdNotZero = constraint_not('rd', 0)
RegRs1NotZero = constraint_not('rs1', 0)
RegRs2NotZero = constraint_not('rs2', 0)
RegRdRs1NotZero = constraint_not('rd_rs1', 0)
RegRdRs1NotTwo = constraint_not('rd_rs1', 2)
ImmNotZero = constraint_not('imm', 0)
ShamtBit5Zero = constraint_bit('imm', 5, 0)


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
        raise ValueError('12-bit immediate must be a multiple of 2: {}'.format(imm))

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

    # be flexible with the "upper" range here (wraps to negative)
    if imm >= 0x80000 and imm <= 0xfffff:
        imm = imm - 2**20
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


# c.jr, c.mv, c.ebreak, c.jalr, c.add
def cr_type(rd_rs1, rs2, *, opcode, funct4, cs=None):
    rd_rs1 = lookup_register(rd_rs1)
    rs2 = lookup_register(rs2)

    # validate constraints
    for c in cs or []:
        c(rd_rs1=rd_rs1, rs2=rs2)

    code = 0
    code |= opcode
    code |= rs2 << 2
    code |= rd_rs1 << 7
    code |= funct4 << 12

    return code


# c.nop, c.addi, c.li, c.slli
def ci_type(rd_rs1, imm, *, opcode, funct3, cs=None):
    rd_rs1 = lookup_register(rd_rs1)

    if imm < -32 or imm > 31:
        raise ValueError('6-bit immediate must be between -0x20 (-32) and 0x1f (31): {}'.format(imm))

    # validate constraints
    for c in cs or []:
        c(rd_rs1=rd_rs1, imm=imm)

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
def cia_type(imm, *, opcode, funct3, cs=None):
    if imm < -512 or imm > 511:
        raise ValueError('6-bit MO16 immediate must be between -0x200 (-512) and 0x1ff (511): {}'.format(imm))
    if imm % 16 != 0:
        raise ValueError('6-bit MO16 immediate must be a multiple of 16: {}'.format(imm))

    # validate constraints
    for c in cs or []:
        c(imm=imm)

    imm = imm >> 4
    imm = c_uint32(imm).value & 0b111111

    imm_9 = (imm >> 5) & 0b1
    imm_8_7 = (imm >> 3) & 0b11
    imm_6 = (imm >> 2) & 0b1
    imm_5 = (imm >> 1) & 0b1
    imm_4 = imm & 0b1

    code = 0
    code |= opcode
    code |= imm_5 << 2
    code |= imm_8_7 << 3
    code |= imm_6 << 5
    code |= imm_4 << 6
    code |= 0b00010 << 7
    code |= imm_9 << 12
    code |= funct3 << 13

    return code


# CI variation
# c.lui
def ciu_type(rd_rs1, imm, *, opcode, funct3, cs=None):
    rd_rs1 = lookup_register(rd_rs1)

    # be flexible with the "upper" range here (wraps to negative)
    # https://stackoverflow.com/questions/63881445/what-are-the-operands-of-c-lui-instructioncompressed-subset-of-risc-v
    if imm >= 0xfffe0 and imm <= 0xfffff:
        imm = imm - 2**20
    if imm < -32 or imm > 31:
        raise ValueError('6-bit immediate must be between -0x20 (-32) and 0x1f (31): {}'.format(imm))

    # validate constraints
    for c in cs or []:
        c(rd_rs1=rd_rs1, imm=imm)

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
# c.lwsp
def cil_type(rd_rs1, imm, *, opcode, funct3, cs=None):
    rd_rs1 = lookup_register(rd_rs1)

    if imm < 0 or imm > 255:
        raise ValueError('6-bit MO4 unsigned immediate must be between 0x00 (0) and 0xff (255): {}'.format(imm))
    if imm % 4 != 0:
        raise ValueError('6-bit MO4 unsigned immediate must be a multiple of 4: {}'.format(imm))

    # validate constraints
    for c in cs or []:
        c(rd_rs1=rd_rs1, imm=imm)

    imm = imm >> 2
    imm = c_uint32(imm).value & 0b111111

    imm_7_6 = (imm >> 4) & 0b11
    imm_5 = (imm >> 3) & 0b1
    imm_4_2 = imm & 0b111

    code = 0
    code |= opcode
    code |= imm_7_6 << 2
    code |= imm_4_2 << 4
    code |= rd_rs1 << 7
    code |= imm_5 << 12
    code |= funct3 << 13

    return code


# c.swsp
def css_type(rs2, imm, *, opcode, funct3, cs=None):
    rs2 = lookup_register(rs2)

    if imm < 0 or imm > 255:
        raise ValueError('6-bit MO4 unsigned immediate must be between 0x00 (0) and 0xff (255): {}'.format(imm))
    if imm % 4 != 0:
        raise ValueError('6-bit MO4 unsigned immediate must be a multiple of 4: {}'.format(imm))

    # validate constraints
    for c in cs or []:
        c(rs2=rs2, imm=imm)

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
def ciw_type(rd, imm, *, opcode, funct3, cs=None):
    rd = lookup_register(rd, compressed=True)

    if imm < 0 or imm > 1023:
       raise ValueError('8-bit MO4 unsigned immediate must be between 0x00 (0) and 0x3ff (1023): {}'.format(imm))
    if imm % 4 != 0:
        raise ValueError('8-bit MO4 unsigned immediate must be a multiple of 4: {}'.format(imm))

    # validate constraints
    for c in cs or []:
        c(rd=rd, imm=imm)

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
def cl_type(rd, rs1, imm, *, opcode, funct3, cs=None):
    rd = lookup_register(rd, compressed=True)
    rs1 = lookup_register(rs1, compressed=True)

    if imm < 0 or imm > 127:
        raise ValueError('5-bit MO4 unsigned immediate must be between 0x00 (0) and 0x7f (127): {}'.format(imm))
    if imm % 4 != 0:
        raise ValueError('5-bit MO4 unsigned immediate must be a multiple of 4: {}'.format(imm))

    # validate constraints
    for c in cs or []:
        c(rd=rd, rs1=rs1, imm=imm)

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
def cs_type(rs1, rs2, imm, *, opcode, funct3, cs=None):
    rs1 = lookup_register(rs1, compressed=True)
    rs2 = lookup_register(rs2, compressed=True)

    if imm < 0 or imm > 127:
        raise ValueError('5-bit MO4 unsigned immediate must be between 0x00 (0) and 0x7f (127): {}'.format(imm))
    if imm % 4 != 0:
        raise ValueError('5-bit MO4 unsigned immediate must be a multiple of 4: {}'.format(imm))

    # validate constraints
    for c in cs or []:
        c(rs1=rs1, rs2=rs2, imm=imm)

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
def ca_type(rd_rs1, rs2, *, opcode, funct2, funct6, cs=None):
    rd_rs1 = lookup_register(rd_rs1, compressed=True)
    rs2 = lookup_register(rs2, compressed=True)

    # validate constraints
    for c in cs or []:
        c(rd_rs1=rd_rs1, rs2=rs2)

    code = 0
    code |= opcode
    code |= rs2 << 2
    code |= funct2 << 5
    code |= rd_rs1 << 7
    code |= funct6 << 10

    return code


# c.beqz, c.bnez
def cb_type(rs1, imm, *, opcode, funct3, cs=None):
    rs1 = lookup_register(rs1, compressed=True)

    # validate constraints
    for c in cs or []:
        c(rs1=rs1, imm=imm)

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
def cbi_type(rd_rs1, imm, *, opcode, funct2, funct3, cs=None):
    rd_rs1 = lookup_register(rd_rs1, compressed=True)

    # validate constraints
    for c in cs or []:
        c(rd_rs1=rd_rs1, imm=imm)

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
def cj_type(imm, *, opcode, funct3, cs=None):
    if imm < -2048 or imm > 2047:
        raise ValueError('11-bit MO2 immediate must be between -0x800 (-2048) and 0x7ff (2047): {}'.format(imm))
    if imm % 2 != 0:
        raise ValueError('11-bit MO2 immediate must be a muliple of 2: {}'.format(imm))

    # validate constraints
    for c in cs or []:
        c(imm=imm)

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
FENCE      = partial(fence,    opcode=0b0001111, funct3=0b000, rd=0, rs1=0, fm=0)  # special syntax*
ECALL      = partial(i_type,   opcode=0b1110011, funct3=0b000, rd=0, rs1=0, imm=0)  # special syntax
EBREAK     = partial(i_type,   opcode=0b1110011, funct3=0b000, rd=0, rs1=0, imm=1)  # special syntax

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
LR_W       = partial(a_type,   opcode=0b0101111, funct3=0b010, funct5=0b00010, rs2=0)  # special syntax
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
C_ADDI4SPN = partial(ciw_type, opcode=0b00, funct3=0b000, cs=[ImmNotZero])
C_LW       = partial(cl_type,  opcode=0b00, funct3=0b010)
C_SW       = partial(cs_type,  opcode=0b00, funct3=0b110)
C_NOP      = partial(ci_type,  opcode=0b01, funct3=0b000, rd_rs1=0, imm=0)  # special syntax
C_ADDI     = partial(ci_type,  opcode=0b01, funct3=0b000, cs=[RegRdRs1NotZero, ImmNotZero])
C_JAL      = partial(cj_type,  opcode=0b01, funct3=0b001)
C_LI       = partial(ci_type,  opcode=0b01, funct3=0b010, cs=[RegRdRs1NotZero])
C_ADDI16SP = partial(cia_type, opcode=0b01, funct3=0b011, cs=[ImmNotZero])  # special syntax
C_LUI      = partial(ciu_type, opcode=0b01, funct3=0b011, cs=[RegRdRs1NotZero, RegRdRs1NotTwo, ImmNotZero])
C_SRLI     = partial(cbi_type, opcode=0b01, funct2=0b00, funct3=0b100, cs=[ImmNotZero])
C_SRAI     = partial(cbi_type, opcode=0b01, funct2=0b01, funct3=0b100, cs=[ImmNotZero])
C_ANDI     = partial(cbi_type, opcode=0b01, funct2=0b10, funct3=0b100)
C_SUB      = partial(ca_type,  opcode=0b01, funct2=0b00, funct6=0b100011)
C_XOR      = partial(ca_type,  opcode=0b01, funct2=0b01, funct6=0b100011)
C_OR       = partial(ca_type,  opcode=0b01, funct2=0b10, funct6=0b100011)
C_AND      = partial(ca_type,  opcode=0b01, funct2=0b11, funct6=0b100011)
C_J        = partial(cj_type,  opcode=0b01, funct3=0b101)
C_BEQZ     = partial(cb_type,  opcode=0b01, funct3=0b110)
C_BNEZ     = partial(cb_type,  opcode=0b01, funct3=0b111)
C_SLLI     = partial(ci_type,  opcode=0b10, funct3=0b000, cs=[RegRdRs1NotZero, ImmNotZero])
C_LWSP     = partial(cil_type, opcode=0b10, funct3=0b010, cs=[RegRdRs1NotZero])
C_JR       = partial(cr_type,  opcode=0b10, funct4=0b1000, rs2=0, cs=[RegRdRs1NotZero])  # special syntax
C_MV       = partial(cr_type,  opcode=0b10, funct4=0b1000, cs=[RegRdRs1NotZero, RegRs2NotZero])
C_EBREAK   = partial(cr_type,  opcode=0b10, funct4=0b1001, rd_rs1=0, rs2=0)  # special syntax
C_JALR     = partial(cr_type,  opcode=0b10, funct4=0b1001, rs2=0, cs=[RegRdRs1NotZero])  # special syntax
C_ADD      = partial(cr_type,  opcode=0b10, funct4=0b1001, cs=[RegRdRs1NotZero, RegRs2NotZero])
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
    'c.mv':       C_MV,
    'c.add':      C_ADD,
}

CRJ_TYPE_INSTRUCTIONS = {
    'c.jr':       C_JR,
    'c.jalr':     C_JALR,
}

CRE_TYPE_INSTRUCTIONS = {
    'c.ebreak':   C_EBREAK,
}

CI_TYPE_INSTRUCTIONS = {
    'c.addi':     C_ADDI,
    'c.li':       C_LI,
    'c.lui':      C_LUI,
    'c.slli':     C_SLLI,
    'c.lwsp':     C_LWSP,
}

CIA_TYPE_INSTRUCTIONS = {
    'c.addi16sp': C_ADDI16SP,
}

CIN_TYPE_INSTRUCTIONS = {
    'c.nop':      C_NOP,
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
    'c.srli':     C_SRLI,
    'c.srai':     C_SRAI,
    'c.andi':     C_ANDI,
    'c.beqz':     C_BEQZ,
    'c.bnez':     C_BNEZ,
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
INSTRUCTIONS.update(CRJ_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(CRE_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(CI_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(CIA_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(CIN_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(CSS_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(CIW_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(CL_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(CS_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(CA_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(CB_TYPE_INSTRUCTIONS)
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
    'c.lw',
    'c.sw',
}

NUMERIC_SEQUENCE_NAMES = {
    'bytes',
    'shorts',
    'ints',
    'longs',
    'longlongs',
}

SHORTHAND_PACK_NAMES = {
    'db',
    'dh',
    'dw',
    'dd',
}

KEYWORDS = {
    'align',
    'string',
    'pack',
}
KEYWORDS.update(INSTRUCTIONS.keys())
KEYWORDS.update(PSEUDO_INSTRUCTIONS)
KEYWORDS.update(NUMERIC_SEQUENCE_NAMES)
KEYWORDS.update(SHORTHAND_PACK_NAMES)


class Line:

    def __init__(self, file, number, contents):
        self.file = file
        self.number = number
        self.contents = contents

    def __len__(self):
        return len(self.contents)

    def __repr__(self):
        s = '{}({!r}, {!r}, {!r})'
        s = s.format(type(self).__name__, self.file, self.number, self.contents)
        return s

    def __str__(self):
        s = 'File "{}", line {}\n  {}'
        s = s.format(self.file, self.number, self.contents.lstrip())
        return s


class LineTokens:

    def __init__(self, line, tokens):
        self.line = line
        self.tokens = tokens

    def __len__(self):
        return len(self.tokens)

    def __repr__(self):
        s = '{}({!r}, {!r})'
        s = s.format(type(self).__name__, self.line, self.tokens)
        return s

    def __str__(self):
        return str(self.tokens)


class Expr(abc.ABC):

    @abc.abstractmethod
    def eval(self, position, env, line):
        """Evaluate an expression to an integer"""


# basic arithmetic expression
# defers evaulation to Python's builtin eval (RIP double-slash comments)
class Arithmetic(Expr):

    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        s = '{}({!r})'
        s = s.format(type(self).__name__, self.expr)
        return s

    def __str__(self):
        s = '{}'
        s = s.format(self.expr)
        return s

    # be sure to not leak internal python exceptions out of this
    def eval(self, position, env, line):
        # check for single ASCII characters
        if self.expr.startswith('\'') and self.expr.endswith('\''):
            c = self.expr[1:-1]
            c = c.encode('utf-8').decode('unicode_escape')
            try:
                return ord(c)
            except TypeError:
                raise AssemblerError('invalid char literal in expr: "{}"'.format(self.expr), line)

        try:
            # exclude Python builtins from eval env
            # https://docs.python.org/3/library/functions.html#eval
            result = eval(self.expr, {'__builtins__': None}, env)
        except SyntaxError:
            raise AssemblerError('invalid syntax in expr: "{}"'.format(self.expr), line)
        except TypeError:
            raise AssemblerError('unknown variable in expr: "{}"'.format(self.expr), line)
        except:
            raise AssemblerError('other error in expr: "{}"'.format(self.expr), line)

        # ensure resulting value is an integer
        if type(result) != int:
            s = 'result "{}" is not an integer from expr: "{}"'
            s = s.format(result, self.expr)
            raise AssemblerError(s, line)

        return result


class Position(Expr):

    def __init__(self, reference, expr):
        self.reference = reference
        self.expr = expr

    def __repr__(self):
        s = '{}({!r}, {!r})'
        s = s.format(type(self).__name__, self.reference, self.expr)
        return s

    def __str__(self):
        s = '%position({}, {})'
        s = s.format(self.reference, self.expr)
        return s

    def eval(self, position, env, line):
        if self.reference not in env:
            s = 'invalid reference in %position modifier: {}'
            s = s.format(self.reference)
            raise AssemblerError(s, line)
        dest = env[self.reference]
        base = self.expr.eval(position, env, line)
        return base + dest


class Offset(Expr):

    def __init__(self, reference):
        self.reference = reference

    def __repr__(self):
        s = '{}({!r})'
        s = s.format(type(self).__name__, self.reference)
        return s

    def __str__(self):
        s = '%offset({})'
        s = s.format(self.reference)
        return s

    def eval(self, position, env, line):
        if self.reference not in env:
            s = 'invalid reference in %offset modifier: {}'
            s = s.format(self.reference)
            raise AssemblerError(s, line)
        dest = env[self.reference]
        return dest - position


class Hi(Expr):

    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        s = '{}({!r})'
        s = s.format(type(self).__name__, self.expr)
        return s

    def __str__(self):
        s = '%hi({})'
        s = s.format(self.expr)
        return s

    def eval(self, position, env, line):
        value = self.expr.eval(position, env, line)
        return relocate_hi(value)


class Lo(Expr):

    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        s = '{}({!r})'
        s = s.format(type(self).__name__, self.expr)
        return s

    def __str__(self):
        s = '%lo({})'
        s = s.format(self.expr)
        return s

    def eval(self, position, env, line):
        value = self.expr.eval(position, env, line)
        return relocate_lo(value)


# base class for assembly "things"
class Item(abc.ABC):

    def __init__(self, line):
        self.line = line

    @abc.abstractmethod
    def size(self):
        """Check the size of this item at the given position in a program"""


class Label(Item):

    def __init__(self, line, name):
        super().__init__(line)
        self.name = name

    def __repr__(self):
        s = '{}({!r})'
        s = s.format(type(self).__name__, self.name)
        return s

    def __str__(self):
        s = '{}:'
        s = s.format(self.name)
        return s

    def size(self):
        return 0


class Constant(Item):

    def __init__(self, line, name, expr):
        super().__init__(line)
        self.name = name
        self.expr = expr

    def __repr__(self):
        s = '{}(name={!r}, expr={!r})'
        s = s.format(type(self).__name__, self.name, self.expr)
        return s

    def __str__(self):
        s = '{} = {}'
        s = s.format(self.name, self.expr)
        return s

    def size(self):
        return 0


class IncludeBytes(Item):

    def __init__(self, line, path, fsize):
        super().__init__(line)
        self.path = path
        self.fsize = fsize

    def __repr__(self):
        s = '{}(path={!r}, fsize={!r})'
        s = s.format(type(self).__name__, self.path, self.fsize)
        return s

    def __str__(self):
        s = 'include_bytes {} {}'
        s = s.format(self.path, self.fsize)
        return s

    def size(self):
        return self.fsize


class String(Item):

    def __init__(self, line, value):
        super().__init__(line)
        self.value = value

    def __repr__(self):
        s = '{}({!r})'
        s = s.format(type(self).__name__, self.value)
        return s

    def __str__(self):
        s = 'string {}'
        s = s.format(self.value)
        return s

    def size(self):
        return len(self.value.encode('utf-8'))


class Sequence(Item):

    def __init__(self, line, name, values):
        super().__init__(line)
        self.name = name
        self.values = values

    def __repr__(self):
        s = '{}(name={!r}, {!r})'
        s = s.format(type(self).__name__, self.name, self.values)
        return s

    def __str__(self):
        s = '{} {}'
        s = s.format(self.name, ' '.join(self.values))
        return s

    def size(self):
        sizes = {
            'bytes': 1,
            'shorts': 2,
            'ints': 4,
            'longs': 4,
            'longlongs': 8,
        }
        return sizes[self.name] * len(self.values)


class Pack(Item):

    def __init__(self, line, fmt, imm):
        super().__init__(line)
        self.fmt = fmt
        self.imm = imm

    def __repr__(self):
        s = '{}(fmt={!r}, imm={!r})'
        s = s.format(type(self).__name__, self.fmt, self.imm)
        return s

    def __str__(self):
        s = 'pack {} {}'
        s = s.format(self.fmt, self.imm)
        return s

    def size(self):
        return struct.calcsize(self.fmt)


class ShorthandPack(Item):

    def __init__(self, line, name, imm):
        super().__init__(line)
        self.name = name
        self.imm = imm

    def __repr__(self):
        s = '{}(name={!r}, imm={!r})'
        s = s.format(type(self).__name__, self.name, self.imm)
        return s

    def __str__(self):
        s = '{} {}'
        s = s.format(self.name, self.imm)
        return s

    def size(self):
        sizes = {
            'db': 1,
            'dh': 2,
            'dw': 4,
            'dd': 8,
        }
        return sizes[self.name]


class Align(Item):

    def __init__(self, line, alignment):
        super().__init__(line)
        self.alignment = alignment

    def __repr__(self):
        s = '{}({!r})'
        s = s.format(type(self).__name__, self.alignment)
        return s

    def __str__(self):
        s = 'align {}'
        s = s.format(self.alignment)
        return s

    def size(self):
        # have to be pessimistic here, will shrink later
        return self.alignment

    def resolution_size(self, position):
        padding = self.alignment - (position % self.alignment)
        if padding == self.alignment:
            return 0
        else:
            return padding


class Blob(Item):

    def __init__(self, line, data):
        super().__init__(line)
        self.data = data

    def __repr__(self):
        # repr is still "correct", just wanted a more consistent hex format
        if len(self.data) <= 16:
            s = ''.join(['\\x{:02x}'.format(b) for b in self.data])
        else:
            s = ''.join(['\\x{:02x}'.format(b) for b in self.data[:16]])
            s += '...'

        return "{}(b'{}')".format(type(self).__name__, s)

    def __str__(self):
        s = 'blob {}'
        if len(self.data) <= 16:
            s = s.format(' '.join('0x{:02x}'.format(b) for b in self.data))
        else:
            s = s.format(' '.join('0x{:02x}'.format(b) for b in self.data[:16]))
            s += ' ...'

        return s

    def size(self):
        return len(self.data)


class Instruction(Item):

    def size(self):
        return 4

    @abc.abstractmethod
    def args(self):
        """Return list of arguments for this instruction"""


class PseudoInstruction(Instruction):

    def __init__(self, line, name, *args):
        super().__init__(line)
        self.name = name
        self.args = args

    def __repr__(self):
        s = '{}({!r}, args={!r})'
        s = s.format(type(self).__name__, self.name, self.args)
        return s

    def __str__(self):
        if len(self.args) == 0:
            return self.name
        s = '{} {}'
        s = s.format(self.name, list(self.args))
        return s

    def args(self):
        return self.args

    def size(self):
        # intentionally pessimistic here (may get shrunk after transform)
        # some pseudo-instructions expand into 2 regular ones
        if self.name in ['li', 'call', 'tail']:
            return 8
        else:
            return 4


class RTypeInstruction(Instruction):

    def __init__(self, line, name, rd, rs1, rs2):
        super().__init__(line)
        self.name = name
        self.rd = rd
        self.rs1 = rs1
        self.rs2 = rs2

    def __repr__(self):
        s = '{}({!r}, rd={!r}, rs1={!r}, rs2={!r})'
        s = s.format(type(self).__name__, self.name, self.rd, self.rs1, self.rs2)
        return s

    def __str__(self):
        s = '{} {}, {}, {}'
        s = s.format(self.name, self.rd, self.rs1, self.rs2)
        return s

    def args(self):
        return [self.rd, self.rs1, self.rs2]


class ITypeInstruction(Instruction):

    def __init__(self, line, name, rd, rs1, imm, is_auipc_jump=False):
        super().__init__(line)
        self.name = name
        self.rd = rd
        self.rs1 = rs1
        self.imm = imm
        self.is_auipc_jump = is_auipc_jump

    def __repr__(self):
        s = '{}({!r}, rd={!r}, rs1={!r}, imm={!r})'
        s = s.format(type(self).__name__, self.name, self.rd, self.rs1, self.imm)
        return s

    def __str__(self):
        s = '{} {}, {}, {}'
        s = s.format(self.name, self.rd, self.rs1, self.imm)
        return s

    def args(self):
        return [self.rd, self.rs1, self.imm]


# custom syntax for: ecall, ebreak
class IETypeInstruction(Instruction):

    def __init__(self, line, name):
        super().__init__(line)
        self.name = name

    def __repr__(self):
        s = '{}({!r})'
        s = s.format(type(self).__name__, self.name)
        return s

    def __str__(self):
        s = '{}'
        s = s.format(self.name)
        return s

    def args(self):
        return []


class STypeInstruction(Instruction):

    def __init__(self, line, name, rs1, rs2, imm):
        super().__init__(line)
        self.name = name
        self.rs1 = rs1
        self.rs2 = rs2
        self.imm = imm

    def __repr__(self):
        s = '{}({!r}, rs1={!r}, rs2={!r}, imm={!r})'
        s = s.format(type(self).__name__, self.name, self.rs1, self.rs2, self.imm)
        return s

    def __str__(self):
        s = '{} {}, {}, {}'
        s = s.format(self.name, self.rs1, self.rs2, self.imm)
        return s

    def args(self):
        return [self.rs1, self.rs2, self.imm]


class BTypeInstruction(Instruction):

    def __init__(self, line, name, rs1, rs2, imm):
        super().__init__(line)
        self.name = name
        self.rs1 = rs1
        self.rs2 = rs2
        self.imm = imm

    def __repr__(self):
        s = '{}({!r}, rs1={!r}, rs2={!r}, imm={!r})'
        s = s.format(type(self).__name__, self.name, self.rs1, self.rs2, self.imm)
        return s

    def __str__(self):
        s = '{} {}, {}, {}'
        s = s.format(self.name, self.rs1, self.rs2, self.imm)
        return s

    def args(self):
        return [self.rs1, self.rs2, self.imm]


class UTypeInstruction(Instruction):

    def __init__(self, line, name, rd, imm):
        super().__init__(line)
        self.name = name
        self.rd = rd
        self.imm = imm

    def __repr__(self):
        s = '{}({!r}, rd={!r}, imm={!r})'
        s = s.format(type(self).__name__, self.name, self.rd, self.imm)
        return s

    def __str__(self):
        s = '{} {}, {}'
        s = s.format(self.name, self.rd, self.imm)
        return s

    def args(self):
        return [self.rd, self.imm]


class JTypeInstruction(Instruction):

    def __init__(self, line, name, rd, imm):
        super().__init__(line)
        self.name = name
        self.rd = rd
        self.imm = imm

    def __repr__(self):
        s = '{}({!r}, rd={!r}, imm={!r})'
        s = s.format(type(self).__name__, self.name, self.rd, self.imm)
        return s

    def __str__(self):
        s = '{} {}, {}'
        s = s.format(self.name, self.rd, self.imm)
        return s

    def args(self):
        return [self.rd, self.imm]


# custom syntax for: fence
class FenceInstruction(Instruction):

    def __init__(self, line, name, succ, pred):
        super().__init__(line)
        self.name = name
        self.succ = succ
        self.pred = pred

    def __repr__(self):
        s = '{}({!r}, succ={!r}, pred={!r})'
        s = s.format(type(self).__name__, self.name, self.succ, self.pred)
        return s

    def __str__(self):
        s = '{} {}, {}'
        s = s.format(self.name, self.succ, self.pred)
        return s

    def args(self):
        return [self.succ, self.pred]


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

    def __str__(self):
        s = '{} {}, {}, {}, {}, {}'
        s = s.format(self.name, self.rd, self.rs1, self.rs2, self.aq, self.rl)
        return s

    def args(self):
        return [self.rd, self.rs1, self.rs2, self.aq, self.rl]


# custom syntax for: lr.w
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

    def __str__(self):
        s = '{} {}, {}, {}, {}'
        s = s.format(self.name, self.rd, self.rs1, self.aq, self.rl)
        return s

    def args(self):
        return [self.rd, self.rs1, self.aq, self.rl]


class CompressedInstruction(Instruction):

    def size(self):
        return 2


class CRTypeInstruction(CompressedInstruction):

    def __init__(self, line, name, rd_rs1, rs2):
        super().__init__(line)
        self.name = name
        self.rd_rs1 = rd_rs1
        self.rs2 = rs2

    def __repr__(self):
        s = '{}({!r}, rd_rs1={!r}, rs2={!r})'
        s = s.format(type(self).__name__, self.name, self.rd_rs1, self.rs2)
        return s

    def __str__(self):
        s = '{} {}, {}'
        s = s.format(self.name, self.rd_rs1, self.rs2)
        return s

    def args(self):
        return [self.rd_rs1, self.rs2]


# custom syntax for: c.jr, c.jalr
class CRJTypeInstruction(CompressedInstruction):

    def __init__(self, line, name, rd_rs1, is_auipc_jump=False):
        super().__init__(line)
        self.name = name
        self.rd_rs1 = rd_rs1
        self.is_auipc_jump = is_auipc_jump

    def __repr__(self):
        s = '{}({!r}, rd_rs1={!r})'
        s = s.format(type(self).__name__, self.name, self.rd_rs1)
        return s

    def __str__(self):
        s = '{} {}'
        s = s.format(self.name, self.rd_rs1)
        return s

    def args(self):
        return [self.rd_rs1]


# custom syntax for: c.ebreak
class CRETypeInstruction(CompressedInstruction):

    def __init__(self, line, name):
        super().__init__(line)
        self.name = name

    def __repr__(self):
        s = '{}({!r})'
        s = s.format(type(self).__name__, self.name)
        return s

    def __str__(self):
        s = '{}'
        s = s.format(self.name)
        return s

    def args(self):
        return []


class CITypeInstruction(CompressedInstruction):

    def __init__(self, line, name, rd_rs1, imm):
        super().__init__(line)
        self.name = name
        self.rd_rs1 = rd_rs1
        self.imm = imm

    def __repr__(self):
        s = '{}({!r}, rd_rs1={!r}, imm={!r})'
        s = s.format(type(self).__name__, self.name, self.rd_rs1, self.imm)
        return s

    def __str__(self):
        s = '{} {}, {}'
        s = s.format(self.name, self.rd_rs1, self.imm)
        return s

    def args(self):
        return [self.rd_rs1, self.imm]


# custom syntax for: c.addi16sp
class CIATypeInstruction(CompressedInstruction):

    def __init__(self, line, name, imm):
        super().__init__(line)
        self.name = name
        self.imm = imm

    def __repr__(self):
        s = '{}({!r}, imm={!r})'
        s = s.format(type(self).__name__, self.name, self.imm)
        return s

    def __str__(self):
        s = '{} {}'
        s = s.format(self.name, self.imm)
        return s

    def args(self):
        return [self.imm]


# custom syntax for: c.nop
class CINTypeInstruction(CompressedInstruction):

    def __init__(self, line, name):
        super().__init__(line)
        self.name = name

    def __repr__(self):
        s = '{}({!r})'
        s = s.format(type(self).__name__, self.name)
        return s

    def __str__(self):
        s = '{}'
        s = s.format(self.name)
        return s

    def args(self):
        return []


class CSSTypeInstruction(CompressedInstruction):

    def __init__(self, line, name, rs2, imm):
        super().__init__(line)
        self.name = name
        self.rs2 = rs2
        self.imm = imm

    def __repr__(self):
        s = '{}({!r}, rs2={!r}, imm={!r})'
        s = s.format(type(self).__name__, self.name, self.rs2, self.imm)
        return s

    def __str__(self):
        s = '{} {}, {}'
        s = s.format(self.name, self.rs2, self.imm)
        return s

    def args(self):
        return [self.rs2, self.imm]


class CIWTypeInstruction(CompressedInstruction):

    def __init__(self, line, name, rd, imm):
        super().__init__(line)
        self.name = name
        self.rd = rd
        self.imm = imm

    def __repr__(self):
        s = '{}({!r}, rd={!r}, imm={!r})'
        s = s.format(type(self).__name__, self.name, self.rd, self.imm)
        return s

    def __str__(self):
        s = '{} {}, {}'
        s = s.format(self.name, self.rd, self.imm)
        return s

    def args(self):
        return [self.rd, self.imm]


class CLTypeInstruction(CompressedInstruction):

    def __init__(self, line, name, rd, rs1, imm):
        super().__init__(line)
        self.name = name
        self.rd = rd
        self.rs1 = rs1
        self.imm = imm

    def __repr__(self):
        s = '{}({!r}, rd={!r}, rs1={!r}, imm={!r})'
        s = s.format(type(self).__name__, self.name, self.rd, self.rs1, self.imm)
        return s

    def __str__(self):
        s = '{} {}, {}, {}'
        s = s.format(self.name, self.rd, self.rs1, self.imm)
        return s

    def args(self):
        return [self.rd, self.rs1, self.imm]


class CSTypeInstruction(CompressedInstruction):

    def __init__(self, line, name, rs1, rs2, imm):
        super().__init__(line)
        self.name = name
        self.rs1 = rs1
        self.rs2 = rs2
        self.imm = imm

    def __repr__(self):
        s = '{}({!r}, rs1={!r}, rs2={!r}, imm={!r})'
        s = s.format(type(self).__name__, self.name, self.rs1, self.rs2, self.imm)
        return s

    def __str__(self):
        s = '{} {}, {}, {}'
        s = s.format(self.name, self.rs1, self.rs2, self.imm)
        return s

    def args(self):
        return [self.rs1, self.rs2, self.imm]


class CATypeInstruction(CompressedInstruction):

    def __init__(self, line, name, rd_rs1, rs2):
        super().__init__(line)
        self.name = name
        self.rd_rs1 = rd_rs1
        self.rs2 = rs2

    def __repr__(self):
        s = '{}({!r}, rd_rs1={!r}, rs2={!r})'
        s = s.format(type(self).__name__, self.name, self.rd_rs1, self.rs2)
        return s

    def __str__(self):
        s = '{} {}, {}'
        s = s.format(self.name, self.rd_rs1, self.rs2)
        return s

    def args(self):
        return [self.rd_rs1, self.rs2]


class CBTypeInstruction(CompressedInstruction):

    def __init__(self, line, name, rs1, imm):
        super().__init__(line)
        self.name = name
        self.rs1 = rs1
        self.imm = imm

    def __repr__(self):
        s = '{}({!r}, rs1={!r}, imm={!r})'
        s = s.format(type(self).__name__, self.name, self.rs1, self.imm)
        return s

    def __str__(self):
        s = '{} {}, {}'
        s = s.format(self.name, self.rs1, self.imm)
        return s

    def args(self):
        return [self.rs1, self.imm]


class CJTypeInstruction(CompressedInstruction):

    def __init__(self, line, name, imm):
        super().__init__(line)
        self.name = name
        self.imm = imm

    def __repr__(self):
        s = '{}({!r}, imm={!r})'
        s = s.format(type(self).__name__, self.name, self.imm)
        return s

    def __str__(self):
        s = '{} {}'
        s = s.format(self.name, self.imm)
        return s

    def args(self):
        return [self.imm]


def read_lines(path_or_source, *, include=False, include_dirs=None):
    def lookup(path, dirs):
        base_path = os.path.dirname(os.path.abspath(path))
        for dir in dirs:
            try_path = os.path.join(dir, path)
            if os.path.exists(try_path):
                return try_path
        else:
            return None

    if os.path.exists(path_or_source) or include:
        log.info('reading file: {}'.format(os.path.abspath(path_or_source)))
        # exceptions here will be caught by the recursive parent
        path = path_or_source
        with open(path) as f:
            source = f.read()
    else:
        path = '<string>'
        source = path_or_source

    # determine base path based on whether a path or source was given
    is_path = os.path.exists(path_or_source)
    if is_path:
        base_path = os.path.dirname(os.path.abspath(path_or_source))
    else:
        base_path = os.getcwd()

    # the adjacent dir is always present and include-able
    current_dirs = copy.deepcopy(include_dirs or [])
    current_dirs.append(base_path)

    lines = []
    for i, raw_line in enumerate(source.splitlines(), start=1):
        # skip empty lines
        if len(raw_line.strip()) == 0:
            continue

        line = Line(path, i, raw_line)

        # handle include in the reader
        if raw_line.lower().startswith('include '):
            try:
                _, path = raw_line.split()
            except ValueError:
                raise AssemblerError('include must specify a file', line)

            # bail out here if the file doesn't exist (or can't be read)
            include_path = lookup(path, current_dirs)
            if include_path is None:
                raise AssemblerError('failed to include file: {}'.format(path), line)

            include_lines = read_lines(include_path, include=True, include_dirs=include_dirs)
            lines.extend(include_lines)
        # handle existence and size of include_bytes in the reader
        elif raw_line.lower().startswith('include_bytes '):
            try:
                _, path = raw_line.split()
            except ValueError:
                raise AssemblerError('include_bytes must specify a file', line)

            # ensure file exists
            include_path = lookup(path, current_dirs)
            if include_path is None:
                raise AssemblerError('failed to include bytes: {}'.format(path), line)

            # grab its size
            size = os.path.getsize(include_path)

            # modify the line by appending the size to the end (too hacky?)
            line.contents = '{} {}'.format(raw_line, size)
            lines.append(line)
        else:
            lines.append(line)

    return lines


def lex_tokens(line):
    RE_ERROR = re.compile(r'\s*error (.*)')
    RE_STRING = re.compile(r'\s*string (.*)')

    # simplify lexing a single string
    if type(line) == str:
        line = Line('<string>', 1, line)

    # check for error literal (needs custom lexing)
    match = RE_ERROR.match(line.contents)
    if match is not None:
        message = match.group(1)
        message = message.encode('utf-8').decode('unicode_escape')
        tokens = ['error', message]
        return LineTokens(line, tokens)

    # check for string literal (needs custom lexing)
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
    tokens = re.split(r'[\s,]+', contents)

    # remove empty tokens
    while '' in tokens:
        tokens.remove('')

    # carry the line and its tokens forward
    return LineTokens(line, tokens)


# helper for parsing immediates since they occur in multiple places
def parse_immediate(imm, line):
    if len(imm) == 0:
        raise AssemblerError('empty immediate value', line)

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
        return Hi(parse_immediate(imm, line))
    elif head == '%lo':
        if imm[1] == '(':
            _, _, *imm, _ = imm
        else:
            _, *imm = imm
        return Lo(parse_immediate(imm, line))
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
        imm = parse_immediate(imm, line)
        return Constant(line, name, imm)
    # errors
    elif head == 'error':
        _, message = tokens
        raise AssemblerError(message, line)
    # include_bytes
    elif head == 'include_bytes':
        if len(tokens) != 3:
            raise AssemblerError('include_bytes must specify a file', line)
        _, path, size = tokens
        size = int(size, base=0)
        return IncludeBytes(line, path, size)
    # strings
    elif head == 'string':
        _, value = tokens
        return String(line, value)
    # sequences
    elif head in NUMERIC_SEQUENCE_NAMES:
        name, *values = tokens
        name = name.lower()
        return Sequence(line, name, values)
    # packs
    elif head == 'pack':
        _, fmt, *imm = tokens
        imm = parse_immediate(imm, line)
        return Pack(line, fmt, imm)
    # shorthand packs
    elif head in SHORTHAND_PACK_NAMES:
        name, *imm = tokens
        imm = parse_immediate(imm, line)
        return ShorthandPack(line, name, imm)
    # aligns
    elif head == 'align':
        _, alignment = tokens
        try:
            alignment = int(alignment, base=0)
        except ValueError:
            raise AssemblerError('alignment must be an integer', line)
        return Align(line, alignment)
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
        imm = parse_immediate(imm, line)
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
        imm = parse_immediate(imm, line)
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
        imm = parse_immediate(imm, line)
        return BTypeInstruction(line, name, rs1, rs2, imm)
    # u-type instructions
    elif head in U_TYPE_INSTRUCTIONS:
        name, rd, *imm = tokens
        name = name.lower()
        imm = parse_immediate(imm, line)
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
        imm = parse_immediate(imm, line)
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
    # cr-type instructions
    elif head in CR_TYPE_INSTRUCTIONS:
        if len(tokens) != 3:
            raise AssemblerError('cr-type instructions require exactly 2 args', line)
        name, rd_rs1, rs2 = tokens
        name = name.lower()
        return CRTypeInstruction(line, name, rd_rs1, rs2)
    # crj-type instructions
    elif head in CRJ_TYPE_INSTRUCTIONS:
        if len(tokens) != 2:
            raise AssemblerError('crj-type instructions require exactly 1 arg', line)
        name, rd_rs1 = tokens
        name = name.lower()
        return CRJTypeInstruction(line, name, rd_rs1)
    # cre-type instructions
    elif head in CRE_TYPE_INSTRUCTIONS:
        if len(tokens) != 1:
            raise AssemblerError('cre-type instructions require no args', line)
        name, = tokens
        name = name.lower()
        return CRETypeInstruction(line, name)
    # ci-type instructions
    elif head in CI_TYPE_INSTRUCTIONS:
        name, rd_rs1, *imm = tokens
        name = name.lower()
        imm = parse_immediate(imm, line)
        return CITypeInstruction(line, name, rd_rs1, imm)
    # cia-type instructions
    elif head in CIA_TYPE_INSTRUCTIONS:
        name, *imm = tokens
        name = name.lower()
        imm = parse_immediate(imm, line)
        return CIATypeInstruction(line, name, imm)
    # cin-type instructions
    elif head in CIN_TYPE_INSTRUCTIONS:
        if len(tokens) != 1:
            raise AssemblerError('cin-type instructions require no args', line)
        name, = tokens
        name = name.lower()
        return CINTypeInstruction(line, name)
    # css-type instructions
    elif head in CSS_TYPE_INSTRUCTIONS:
        name, rs2, *imm = tokens
        name = name.lower()
        imm = parse_immediate(imm, line)
        return CSSTypeInstruction(line, name, rs2, imm)
    # ciw-type instructions
    elif head in CIW_TYPE_INSTRUCTIONS:
        name, rd, *imm = tokens
        name = name.lower()
        imm = parse_immediate(imm, line)
        return CIWTypeInstruction(line, name, rd, imm)
    # cl-type instructions (all are base offset insts)
    elif head in CL_TYPE_INSTRUCTIONS:
        if tokens[3] == '(':
            name, rd, offset, _, rs1, _ = tokens
            imm = [offset]
        else:
            name, rd, rs1, *imm = tokens
        name = name.lower()
        imm = parse_immediate(imm, line)
        return CLTypeInstruction(line, name, rd, rs1, imm)
    # cs-type instructions (all are base offset insts)
    elif head in CS_TYPE_INSTRUCTIONS:
        if tokens[3] == '(':
            name, rs2, offset, _, rs1, _ = tokens
            imm = [offset]
        else:
            name, rs1, rs2, *imm = tokens
        name = name.lower()
        imm = parse_immediate(imm, line)
        return CSTypeInstruction(line, name, rs1, rs2, imm)
    # ca-type instructions
    elif head in CA_TYPE_INSTRUCTIONS:
        if len(tokens) != 3:
            raise AssemblerError('ca-type instructions require exactly 2 args', line)
        name, rd_rs1, rs2 = tokens
        name = name.lower()
        return CATypeInstruction(line, name, rd_rs1, rs2)
    # cb-type instructions
    elif head in CB_TYPE_INSTRUCTIONS:
        name, rs1, *imm = tokens
        name = name.lower()
        imm = parse_immediate(imm, line)
        return CBTypeInstruction(line, name, rs1, imm)
    # cj-type instructions
    elif head in CJ_TYPE_INSTRUCTIONS:
        name, *imm = tokens
        name = name.lower()
        imm = parse_immediate(imm, line)
        return CJTypeInstruction(line, name, imm)
    # pseudo instructions
    elif head in PSEUDO_INSTRUCTIONS:
        name, *args = tokens
        name = name.lower()
        return PseudoInstruction(line, name, *args)
    else:
        raise AssemblerError('invalid syntax (expected constant, label, or instruction)', line)


def resolve_constants(items, constants):
    new_items = []
    for item in items:
        if not isinstance(item, Constant):
            new_items.append(item)
            continue

        if not isinstance(item.expr, Arithmetic):
            s = 'constants only support arithmetic expressions'
            raise AssemblerError(s, item.line)

        if item.name in REGISTERS:
            s = 'constant name cannot shadow a register name "{}"'
            s = s.format(item.name)
            raise AssemblerError(s, item.line)

        if is_int(item.name):
            s = 'constant name cannot be a number "{}"'
            s = s.format(item.name)
            raise AssemblerError(s, item.line)

        # intentionally no labels here
        env = ChainMap(constants, REGISTERS)
        value = item.expr.eval(None, env, item.line)
        constants[item.name] = value

        log_constant('resolve_constants', item, value)

    return new_items


def resolve_labels(items, labels):
    position = 0
    new_items = []
    for item in items:
        if not isinstance(item, Label):
            position += item.size()
            new_items.append(item)
            continue

        labels[item.name] = position

    return new_items


def resolve_register_aliases(items, constants):
    REGS = {'rd', 'rs1', 'rs2', 'rd_rs1'}

    new_items = []
    for item in items:
        d = copy.deepcopy(vars(item))

        # skip items without any register fields
        if not set(d.keys()) & REGS:
            new_items.append(item)
            continue

        # resolve all fields that are registers
        modified = False
        resolved_regs = {}
        for key, value in d.items():
            # skip if item field is not a register
            if key not in REGS:
                continue
            # skip if reg is not a constant
            if value not in constants:
                continue
            # reg IS a constant
            modified = True
            reg = constants[value]
            resolved_regs[key] = reg

        if not modified:
            new_items.append(item)
            continue

        d.update(resolved_regs)

        # create the new item using the resolved registers
        new_item = item.__class__(*d.values())
        new_items.append(new_item)

        log_conversion('resolve_register_aliases', item, new_item)

    return new_items


def transform_compressible(items, constants, labels):

    def NameEquals(value):
        def inner(i, p, e):
            return i.name == value
        return inner

    def RegEquals(name, value):
        def inner(i, p, e):
            reg = getattr(i, name)
            reg = lookup_register(reg)
            return reg == value
        return inner

    def RegNotEquals(name, value):
        def inner(i, p, e):
            reg = getattr(i, name)
            reg = lookup_register(reg)
            return reg != value
        return inner

    def RegBetween(name, lo, hi):
        def inner(i, p, e):
            reg = getattr(i, name)
            reg = lookup_register(reg)
            return reg >= lo and reg <= hi
        return inner

    def RegsMatch(a, b):
        def inner(i, p, e):
            reg_a = getattr(i, a)
            reg_a = lookup_register(reg_a)
            reg_b = getattr(i, b)
            reg_b = lookup_register(reg_b)
            return reg_a == reg_b
        return inner

    def ImmEquals(value):
        def inner(i, p, e):
            imm = i.imm.eval(p, e, i.line)
            return imm == value
        return inner

    def ImmNotEquals(value):
        def inner(i, p, e):
            imm = i.imm.eval(p, e, i.line)
            return imm != value
        return inner

    def ImmDivisibleBy(value):
        def inner(i, p, e):
            imm = i.imm.eval(p, e, i.line)
            return imm % value == 0
        return inner

    def ImmBetween(lo, hi):
        def inner(i, p, e):
            imm = i.imm.eval(p, e, i.line)
            return imm >= lo and imm <= hi
        return inner

    criteria = {
        # this has to be first since it collides with c.addi
        'c.addi16sp': [
            NameEquals('addi'),
            RegEquals('rd', 2),
            RegEquals('rs1', 2),
            ImmNotEquals(0),
            ImmDivisibleBy(16),
            ImmBetween(-2**5 * 16, 2**5 * 16 - 1),
        ],
        'c.addi4spn': [
            NameEquals('addi'),
            RegBetween('rd', 8, 15),
            RegEquals('rs1', 2),
            ImmNotEquals(0),
            ImmDivisibleBy(4),
            ImmBetween(0, 2**8 * 4 - 1),
        ],
        'c.lw': [
            NameEquals('lw'),
            RegBetween('rd', 8, 15),
            RegBetween('rs1', 8, 15),
            ImmDivisibleBy(4),
            ImmBetween(0, 2**5 * 4 - 1),
        ],
        'c.sw': [
            NameEquals('sw'),
            RegBetween('rs1', 8, 15),
            RegBetween('rs2', 8, 15),
            ImmDivisibleBy(4),
            ImmBetween(0, 2**5 * 4 - 1),
        ],
        'c.nop': [
            NameEquals('addi'),
            RegEquals('rd', 0),
            RegEquals('rs1', 0),
            ImmEquals(0),
        ],
        'c.addi': [
            NameEquals('addi'),
            RegNotEquals('rd', 0),
            RegNotEquals('rs1', 0),
            RegsMatch('rd', 'rs1'),
            ImmNotEquals(0),
            ImmBetween(-2**5, 2**5 - 1),
        ],
        'c.jal': [
            NameEquals('jal'),
            RegEquals('rd', 1),
            ImmDivisibleBy(2),
            ImmBetween(-2**10 * 2, 2**10 * 2 - 1),
        ],
        'c.li': [
            NameEquals('addi'),
            RegNotEquals('rd', 0),
            RegEquals('rs1', 0),
            ImmBetween(-2**5, 2**5 - 1),
        ],
        'c.lui': [
            NameEquals('lui'),
            RegNotEquals('rd', 0),
            RegNotEquals('rd', 2),
            ImmNotEquals(0),
            ImmBetween(-2**5, 2**5 - 1),
        ],
        # check for alternate upper bound case
        'c.lui_alt': [
            NameEquals('lui'),
            RegNotEquals('rd', 0),
            RegNotEquals('rd', 2),
            ImmNotEquals(0),
            ImmBetween(0xfffe0, 0xfffff),
        ],
        'c.srli': [
            NameEquals('srli'),
            RegBetween('rd', 8, 15),
            RegBetween('rs1', 8, 15),
            RegsMatch('rd', 'rs1'),
            RegNotEquals('rs2', 0),
            RegBetween('rs2', 0, 2**5 - 1),
        ],
        'c.srai': [
            NameEquals('srai'),
            RegBetween('rd', 8, 15),
            RegBetween('rs1', 8, 15),
            RegsMatch('rd', 'rs1'),
            RegNotEquals('rs2', 0),
            RegBetween('rs2', 0, 2**5 - 1),
        ],
        'c.andi': [
            NameEquals('andi'),
            RegBetween('rd', 8, 15),
            RegBetween('rs1', 8, 15),
            RegsMatch('rd', 'rs1'),
            ImmBetween(-2**5, 2**5 - 1),
        ],
        'c.sub': [
            NameEquals('sub'),
            RegBetween('rd', 8, 15),
            RegBetween('rs1', 8, 15),
            RegsMatch('rd', 'rs1'),
            RegBetween('rs2', 8, 15),
        ],
        'c.xor': [
            NameEquals('xor'),
            RegBetween('rd', 8, 15),
            RegBetween('rs1', 8, 15),
            RegsMatch('rd', 'rs1'),
            RegBetween('rs2', 8, 15),
        ],
        'c.or': [
            NameEquals('or'),
            RegBetween('rd', 8, 15),
            RegBetween('rs1', 8, 15),
            RegsMatch('rd', 'rs1'),
            RegBetween('rs2', 8, 15),
        ],
        'c.and': [
            NameEquals('and'),
            RegBetween('rd', 8, 15),
            RegBetween('rs1', 8, 15),
            RegsMatch('rd', 'rs1'),
            RegBetween('rs2', 8, 15),
        ],
        'c.j': [
            NameEquals('jal'),
            RegEquals('rd', 0),
            ImmDivisibleBy(2),
            ImmBetween(-2**10 * 2, 2**10 * 2 - 1),
        ],
        'c.beqz': [
            NameEquals('beq'),
            RegBetween('rs1', 8, 15),
            RegEquals('rs2', 0),
            ImmDivisibleBy(2),
            ImmBetween(-2**7 * 2, 2**7 * 2 - 1),
        ],
        'c.bnez': [
            NameEquals('bne'),
            RegBetween('rs1', 8, 15),
            RegEquals('rs2', 0),
            ImmDivisibleBy(2),
            ImmBetween(-2**7 * 2, 2**7 * 2 - 1),
        ],
        'c.slli': [
            NameEquals('slli'),
            RegNotEquals('rd', 0),
            RegNotEquals('rs1', 0),
            RegsMatch('rd', 'rs1'),
            RegNotEquals('rs2', 0),
            RegBetween('rs2', 0, 2**5 - 1),
        ],
        'c.lwsp': [
            NameEquals('lw'),
            RegNotEquals('rd', 0),
            RegEquals('rs1', 2),
            ImmDivisibleBy(4),
            ImmBetween(0, 2**6 * 4 - 1),
        ],
        'c.jr': [
            NameEquals('jalr'),
            RegEquals('rd', 0),
            RegNotEquals('rs1', 0),
            ImmEquals(0),
        ],
        'c.mv': [
            NameEquals('add'),
            RegNotEquals('rd', 0),
            RegEquals('rs1', 0),
            RegNotEquals('rs2', 0),
        ],
        'c.ebreak': [
            NameEquals('ebreak'),
        ],
        'c.add': [
            NameEquals('add'),
            RegNotEquals('rd', 0),
            RegNotEquals('rs1', 0),
            RegsMatch('rd', 'rs1'),
            RegNotEquals('rs2', 0),
        ],
        'c.jalr': [
            NameEquals('jalr'),
            RegEquals('rd', 1),
            RegNotEquals('rs1', 0),
            ImmEquals(0),
        ],
        'c.swsp': [
            NameEquals('sw'),
            RegEquals('rs1', 2),
            ImmDivisibleBy(4),
            ImmBetween(0, 2**6 * 4 - 1),
        ],
    }

    # used for imm evaluation
    env = ChainMap(constants, labels)

    position = 0
    new_items = []
    for item in items:
        # skip non-instructions and pseudo-instructions
        if not isinstance(item, Instruction) or isinstance(item, PseudoInstruction):
            position += item.size()
            new_items.append(item)
            continue

        # check if any set of criteria is all true for this item
        compressed = None
        for name, preds in criteria.items():
            if all(pred(item, position, env) for pred in preds):
                compressed = name
                break

        # swap out the instruction for its compressed counterpart
        if compressed is not None:
            if compressed == 'c.addi4spn':
                inst = CIWTypeInstruction(item.line, compressed, item.rd, item.imm)
            elif compressed == 'c.lw':
                inst = CLTypeInstruction(item.line, compressed, item.rd, item.rs1, item.imm)
            elif compressed == 'c.sw':
                inst = CSTypeInstruction(item.line, compressed, item.rs1, item.rs2, item.imm)
            elif compressed == 'c.nop':
                inst = CINTypeInstruction(item.line, compressed)
            elif compressed == 'c.addi':
                inst = CITypeInstruction(item.line, compressed, item.rd, item.imm)
            elif compressed == 'c.jal':
                inst = CJTypeInstruction(item.line, compressed, item.imm)
            elif compressed == 'c.li':
                inst = CITypeInstruction(item.line, compressed, item.rd, item.imm)
            elif compressed in ['c.lui', 'c.lui_alt']:
                compressed = 'c.lui'
                inst = CITypeInstruction(item.line, compressed, item.rd, item.imm)
            elif compressed == 'c.addi16sp':
                inst = CIATypeInstruction(item.line, compressed, item.imm)
            elif compressed == 'c.srli':
                inst = CBTypeInstruction(item.line, compressed, item.rd, Arithmetic(item.rs2))
            elif compressed == 'c.srai':
                inst = CBTypeInstruction(item.line, compressed, item.rd, Arithmetic(item.rs2))
            elif compressed == 'c.andi':
                inst = CBTypeInstruction(item.line, compressed, item.rd, item.imm)
            elif compressed == 'c.sub':
                inst = CATypeInstruction(item.line, compressed, item.rd, item.rs2)
            elif compressed == 'c.xor':
                inst = CATypeInstruction(item.line, compressed, item.rd, item.rs2)
            elif compressed == 'c.or':
                inst = CATypeInstruction(item.line, compressed, item.rd, item.rs2)
            elif compressed == 'c.and':
                inst = CATypeInstruction(item.line, compressed, item.rd, item.rs2)
            elif compressed == 'c.j':
                inst = CJTypeInstruction(item.line, compressed, item.imm)
            elif compressed == 'c.beqz':
                inst = CBTypeInstruction(item.line, compressed, item.rs1, item.imm)
            elif compressed == 'c.bnez':
                inst = CBTypeInstruction(item.line, compressed, item.rs1, item.imm)
            elif compressed == 'c.slli':
                inst = CITypeInstruction(item.line, compressed, item.rd, Arithmetic(item.rs2))
            elif compressed == 'c.lwsp':
                inst = CITypeInstruction(item.line, compressed, item.rd, item.imm)
            elif compressed == 'c.jr':
                inst = CRJTypeInstruction(item.line, compressed, item.rs1, item.is_auipc_jump)
            elif compressed == 'c.mv':
                inst = CRTypeInstruction(item.line, compressed, item.rd, item.rs2)
            elif compressed == 'c.ebreak':
                inst = CRETypeInstruction(item.line, compressed)
            elif compressed == 'c.jalr':
                inst = CRJTypeInstruction(item.line, compressed, item.rs1, item.is_auipc_jump)
            elif compressed == 'c.add':
                inst = CRTypeInstruction(item.line, compressed, item.rd, item.rs2)
            elif compressed == 'c.swsp':
                inst = CSSTypeInstruction(item.line, compressed, item.rs2, item.imm)
            else:
                raise AssemblerError('bad logic in inst compression', item.line)

            # shrink all subsequent labels by 2
            new_labels = {k: v - 2 for k, v in labels.items() if v > position}
            labels.update(new_labels)

            # add compressed inst to items and break the search loop
            position += inst.size()
            new_items.append(inst)

            log_conversion('resolve_compressible', item, inst)

        # if inst wasn't compressed, append to list like normal
        else:
            position += item.size()
            new_items.append(item)

    return new_items


def transform_pseudo_instructions(items, constants, labels):
    position = 0
    new_items = []
    for item in items:
        # save an indent by early-exiting non PIs
        if not isinstance(item, PseudoInstruction):
            position += item.size()
            new_items.append(item)
            continue

        if item.name == 'nop':
            inst = ITypeInstruction(item.line, 'addi', rd='x0', rs1='x0', imm=Arithmetic('0'))
        elif item.name == 'li':
            rd, *imm = item.args
            imm = parse_immediate(imm, item.line)
            # check if eligible for single inst expansion
            env = ChainMap(constants, labels)
            value = imm.eval(position, env, item.line)
            value = c_int32(value).value  # signed imm
            if value >= (-2**11) and value <= (2**11 - 1):
                inst = ITypeInstruction(item.line, 'addi', rd=rd, rs1='x0', imm=Lo(imm))
                # shrink all subsequent labels by 4
                new_labels = {k: v - 4 for k, v in labels.items() if v > position}
                labels.update(new_labels)
            elif (value & 0xfff) == 0:
                inst = UTypeInstruction(item.line, 'lui', rd=rd, imm=Hi(imm))
                # shrink all subsequent labels by 4
                new_labels = {k: v - 4 for k, v in labels.items() if v > position}
                labels.update(new_labels)
            else:
                # expanding 1 inst into 2
                inst = UTypeInstruction(item.line, 'lui', rd=rd, imm=Hi(imm))
                position += inst.size()
                new_items.append(inst)
                log_conversion('transform_pseudo_instructions', item, inst)

                inst = ITypeInstruction(item.line, 'addi', rd=rd, rs1=rd, imm=Lo(imm))
        elif item.name == 'mv':
            rd, rs = item.args
            inst = ITypeInstruction(item.line, 'addi', rd=rd, rs1=rs, imm=Arithmetic('0'))
        elif item.name == 'not':
            rd, rs = item.args
            inst = ITypeInstruction(item.line, 'xori', rd=rd, rs1=rs, imm=Arithmetic('-1'))
        elif item.name == 'neg':
            rd, rs = item.args
            inst = RTypeInstruction(item.line, 'sub', rd=rd, rs1='x0', rs2=rs)
        elif item.name == 'seqz':
            rd, rs = item.args
            inst = ITypeInstruction(item.line, 'sltiu', rd=rd, rs1=rs, imm=Arithmetic('1'))
        elif item.name == 'snez':
            rd, rs = item.args
            inst = RTypeInstruction(item.line, 'sltu', rd=rd, rs1='x0', rs2=rs)
        elif item.name == 'sltz':
            rd, rs = item.args
            inst = RTypeInstruction(item.line, 'slt', rd=rd, rs1=rs, rs2='x0')
        elif item.name == 'sgtz':
            rd, rs = item.args
            inst = RTypeInstruction(item.line, 'slt', rd=rd, rs1='x0', rs2=rs)

        elif item.name in ['beqz', 'bnez', 'bgez', 'bltz']:
            names = {'beqz': 'beq', 'bnez': 'bne', 'bgez': 'bge', 'bltz': 'blt'}
            rs, reference = item.args
            imm = ['%offset', reference]
            imm = parse_immediate(imm, item.line)
            inst = BTypeInstruction(item.line, names[item.name], rs1=rs, rs2='x0', imm=imm)
        elif item.name in ['blez', 'bgtz']:
            names = {'blez': 'bge', 'bgtz': 'blt'}
            rs, reference = item.args
            imm = ['%offset', reference]
            imm = parse_immediate(imm, item.line)
            inst = BTypeInstruction(item.line, names[item.name], rs1='x0', rs2=rs, imm=imm)

        elif item.name in ['bgt', 'ble', 'bgtu', 'bleu']:
            names = {'bgt': 'blt', 'ble': 'bge', 'bgtu': 'bltu', 'bleu': 'bgeu'}
            rs, rt, reference = item.args
            imm = ['%offset', reference]
            imm = parse_immediate(imm, item.line)
            inst = BTypeInstruction(item.line, names[item.name], rs1=rt, rs2=rs, imm=imm)

        elif item.name == 'j':
            reference, = item.args
            imm = ['%offset', reference]
            imm = parse_immediate(imm, item.line)
            inst = JTypeInstruction(item.line, 'jal', rd='x0', imm=imm)
        elif item.name == 'jal':
            reference, = item.args
            imm = ['%offset', reference]
            imm = parse_immediate(imm, item.line)
            inst = JTypeInstruction(item.line, 'jal', rd='x1', imm=imm)
        elif item.name == 'jr':
            rs, = item.args
            inst = ITypeInstruction(item.line, 'jalr', rd='x0', rs1=rs, imm=Arithmetic('0'))
        elif item.name == 'jalr':
            rs, = item.args
            inst = ITypeInstruction(item.line, 'jalr', rd='x1', rs1=rs, imm=Arithmetic('0'))
        elif item.name == 'ret':
            inst = ITypeInstruction(item.line, 'jalr', rd='x0', rs1='x1', imm=Arithmetic('0'))
        elif item.name == 'call':
            reference, = item.args
            imm = ['%offset', reference]
            imm = parse_immediate(imm, item.line)
            # check if eligible for single inst expansion
            env = ChainMap(constants, labels)
            value = imm.eval(position, env, item.line)
            value = c_int32(value).value  # signed imm
            if value >= (-2**20) and value <= (2**20 - 1):
                inst = JTypeInstruction(item.line, 'jal', rd='x1', imm=Lo(imm))
                # shrink all subsequent labels by 4
                new_labels = {k: v - 4 for k, v in labels.items() if v > position}
                labels.update(new_labels)
            else:
                # expanding 1 inst into 2
                inst = UTypeInstruction(item.line, 'auipc', rd='x1', imm=Hi(imm))
                position += inst.size()
                new_items.append(inst)
                log_conversion('transform_pseudo_instructions', item, inst)

                inst = ITypeInstruction(item.line, 'jalr', rd='x1', rs1='x1', imm=Lo(imm), is_auipc_jump=True)
        elif item.name == 'tail':
            reference, = item.args
            imm = ['%offset', reference]
            imm = parse_immediate(imm, item.line)
            # check if eligible for single inst expansion
            env = ChainMap(constants, labels)
            value = imm.eval(position, env, item.line)
            value = c_int32(value).value  # signed imm
            if value >= (-2**20) and value <= (2**20 - 1):
                inst = JTypeInstruction(item.line, 'jal', rd='x0', imm=Lo(imm))
                # shrink all subsequent labels by 4
                new_labels = {k: v - 4 for k, v in labels.items() if v > position}
                labels.update(new_labels)
            else:
                # expanding 1 inst into 2
                inst = UTypeInstruction(item.line, 'auipc', rd='x6', imm=Hi(imm))
                position += inst.size()
                new_items.append(inst)
                log_conversion('transform_pseudo_instructions', item, inst)

                inst = ITypeInstruction(item.line, 'jalr', rd='x0', rs1='x6', imm=Lo(imm), is_auipc_jump=True)

        elif item.name == 'fence':
            inst = FenceInstruction(item.line, 'fence', succ=0b1111, pred=0b1111)

        else:
            raise AssemblerError('no translation for pseudo-instruction: {}'.format(item.name), item.line)

        position += inst.size()
        new_items.append(inst)

        log_conversion('transform_pseudo_instructions', item, inst)

    return new_items


def resolve_aligns(items, labels):
    position = 0
    new_items = []
    for item in items:
        if not isinstance(item, Align):
            position += item.size()
            new_items.append(item)
            continue

        # determine actual padding and amount to shrink subsequent labels
        padding = item.resolution_size(position)
        shrink = item.size() - padding 

        # shrink subsequent labels
        new_labels = {k: v - shrink for k, v in labels.items() if v > position}
        labels.update(new_labels)

        # skip if already aligned
        if padding == 0:
            continue

        position += padding
        blob = Blob(item.line, b'\x00' * padding)
        new_items.append(blob)

        log_conversion('resolve_aligns', item, blob)

    return new_items


def resolve_immediates(items, constants, labels):
    position = 0
    new_items = []
    for item in items:
        d = copy.deepcopy(vars(item))

        # skip items without an immediate field
        if 'imm' not in d:
            position += item.size()
            new_items.append(item)
            continue

        # check if imm is trivial for nicer logging later
        trivial = False
        if isinstance(item.imm, Arithmetic) and is_int(item.imm.expr):
            trivial = True

        # resolve the immediate field
        env = ChainMap(constants, labels)
        imm = item.imm.eval(position, env, item.line)

        # account for AUIPC "PC based on previous inst" nuance
        if hasattr(item, 'is_auipc_jump') and item.is_auipc_jump:
            if isinstance(item, CompressedInstruction):
                imm += 2
            else:
                imm += 4

        d['imm'] = imm

        # create the new item using the resolved immediate
        new_item = item.__class__(*d.values())
        position += new_item.size()
        new_items.append(new_item)

        if not trivial:
            log_conversion('resolve_immediates', item, new_item)

    return new_items


def resolve_instructions(items):
    new_items = []

    for item in items:
        if not isinstance(item, Instruction):
            new_items.append(item)
            continue

        encode_func = INSTRUCTIONS[item.name]
        try:
            # atomic insts expect aq and rl as kwargs
            if isinstance(item, ATypeInstruction) or isinstance(item, ALTypeInstruction):
                *args, aq, rl = item.args()
                code = encode_func(*args, aq=aq, rl=rl)
            else:
                args = item.args()
                code = encode_func(*args)
        except ValueError as e:
            raise AssemblerError(str(e), item.line)

        # pack into 2 bytes if item is a CompressedInstruction, else 4
        if isinstance(item, CompressedInstruction):
            fmt = '<H'
        else:
            fmt = '<I'

        code = struct.pack(fmt, code)
        blob = Blob(item.line, code)
        new_items.append(blob)

        log_conversion('resolve_instructions', item, blob)

    return new_items


def resolve_strings(items):
    new_items = []
    for item in items:
        if not isinstance(item, String):
            new_items.append(item)
            continue

        blob = Blob(item.line, item.value.encode('utf-8'))
        new_items.append(blob)

        log_conversion('resolve_strings', item, blob)

    return new_items


def resolve_sequences(items):
    endianness = '<'
    formats = {
        'bytes': 'B',
        'shorts': 'H',
        'ints': 'I',
        'longs': 'L',
        'longlongs': 'Q',
    }

    new_items = []
    for item in items:
        if not isinstance(item, Sequence):
            new_items.append(item)
            continue

        values = [int(value, base=0) for value in item.values]

        data = bytearray()
        for value in values:
            fmt = endianness + formats[item.name]
            if value < 0:
                fmt = fmt.lower()
            value = struct.pack(fmt, value)
            data.extend(value)
        blob = Blob(item.line, bytes(data))
        new_items.append(blob)

        log_conversion('resolve_sequences', item, blob)

    return new_items


def transform_shorthand_packs(items):
    endianness = '<'
    formats = {
        'db': 'B',
        'dh': 'H',
        'dw': 'I',
        'dd': 'Q',
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

        log_conversion('transform_shorthand_packs', item, pack)

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

        log_conversion('resolve_packs', item, blob)

    return new_items


def resolve_include_bytes(items):
    new_items = []
    for item in items:
        if not isinstance(item, IncludeBytes):
            new_items.append(item)
            continue

        with open(item.path, 'rb') as f:
            data = f.read()

        # defense against the dark race conditions
        assert len(data) == item.fsize

        blob = Blob(item.line, data)
        new_items.append(blob)

        log_conversion('resolve_include_bytes', item, blob)

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
#   - Resolve constants  (eval expr and update env)
#   - Resolve labels  (store label locations into env)
#   - Resolve register aliases  (could be constants for readability)
#   - Transform compressible  (identify and compress eligible instructions)
#   - Transform pseudo-instructions  (expand PIs into regular instructions)
#   - Resolve register aliases  (again)
#   - Transform compressible  (again)
#   - Resolve aligns  (convert aligns to blobs based on position)
#   - Resolve immediates  (Arithmetic, Position, Offset, Hi, Lo)
#   - Resolve instructions  (convert xTypeInstruction to Blob)
#   - Resolve strings  (convert String to Blob)
#   - Resolve sequences (convert Sequence to Blob)
#   - Transform shorthand packs (expand shorthand pack syntax into the full syntax)
#   - Resolve packs  (convert Pack to Blob)
#   - Resolve include_bytes  (read include_bytes files into Blobs)
#   - Resolve blobs  (merge all Blobs into a single binary)
def assemble(path_or_source, *, constants=None, labels=None, compress=False, include_dirs=None):
    """
    Assemble a RISC-V assembly program into a raw binary.

    :param path_or_source: Path to an assembly file or raw assembly source
    :returns: Assembled binary as bytes
    """

    # keep constants and labels in separate namespaces
    constants = constants if constants is not None else {}
    labels = labels if labels is not None else {}

    # read, lex, and parse the source
    lines = read_lines(path_or_source, include_dirs=include_dirs)
    lines = [l for l in lines if len(l) > 0]
    tokens = [lex_tokens(l) for l in lines]
    tokens = [t for t in tokens if len(t) > 0]
    items = [parse_item(t) for t in tokens]
    items = [i for i in items if i is not None]
    for item in items:
        log.info('parsed file {}, line {}: "{}"'.format(os.path.basename(item.line.file), item.line.number, item))

    # run items through each pass
    items = resolve_constants(items, constants)
    items = resolve_labels(items, labels)
    items = resolve_register_aliases(items, constants)
    if compress:
        items = transform_compressible(items, constants, labels)
    items = transform_pseudo_instructions(items, constants, labels)
    items = resolve_register_aliases(items, constants)
    if compress:
        items = transform_compressible(items, constants, labels)
    items = resolve_aligns(items, labels)
    items = resolve_immediates(items, constants, labels)
    items = resolve_instructions(items)
    items = resolve_strings(items)
    items = resolve_sequences(items)
    items = transform_shorthand_packs(items)
    items = resolve_packs(items)
    items = resolve_include_bytes(items)
    program = resolve_blobs(items)

    return program


def cli_main():
    # any cleaner way to handle this w/ argparse positional args?
    if len(sys.argv) >= 2 and sys.argv[1] == '--version':
        from bronzebeard import __version__
        version = 'bronzebeard {}'.format(__version__)
        raise SystemExit(version)

    boards = [
        'gd32_dev_board',
        'hifive1_rev_b',
        'longan_nano',
        'wio_lite',
    ]

    parser = argparse.ArgumentParser(
        description='Assemble RISC-V source code',
        prog='bronzebeard',
    )
    parser.add_argument('input_asm', type=str, help='input source file')
    parser.add_argument('-b', '--board', choices=boards,
        help='include feature abstractions for a given board: {}'.format(', '.join(boards)), metavar='BOARD')
    parser.add_argument('-c', '--compress', action='store_true', help='identify and compress eligible instructions')
    parser.add_argument('-i', '--include', action='append', help='add a directory to the assembler search path')
    parser.add_argument('-o', '--output', type=str, default='bb.out', help='output binary file (default "bb.out")')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose assembler output')
    parser.add_argument('--version', action='store_true', help='print assembler version and exit')
    args = parser.parse_args()

    if args.version:
        from bronzebeard import __version__
        version = 'bronzebeard {}'.format(__version__)
        raise SystemExit(version)

    log_fmt = '%(message)s'
    if args.verbose:
        logging.basicConfig(format=log_fmt, level=logging.INFO, stream=sys.stdout)

    if not os.path.exists(args.input_asm):
        raise SystemExit('missing input file: {}'.format(args.input_asm))

    # validate and expand include dirs
    include_dirs = []
    for inc_dir in args.include or []:
        if not os.path.isdir(inc_dir):
            raise SystemExit('invalid include dir: {}'.format(inc_dir))
        include_dirs.append(os.path.abspath(inc_dir))

    # add board-specific include dirs if requested
    if args.board:
        root = os.path.abspath(os.path.dirname(__file__))
        path = os.path.join(root, 'boards', args.board)
        include_dirs.append(path)

    constants = {}
    labels = {}
    try:
        binary = assemble(args.input_asm, constants=constants, labels=labels, compress=args.compress, include_dirs=include_dirs)
    except AssemblerError as e:
        raise SystemExit(e)

    if args.verbose:
        for k, v in constants.items():
            log.info('constant: {:<25} = 0x{:08x} ({})'.format(k, v, v))
        for k, v in labels.items():
            log.info('label: {:<25} = 0x{:08x} ({})'.format(k, v, v))

    with open(args.output, 'wb') as out_bin:
        out_bin.write(binary)


if __name__ == '__main__':
    cli_main()
