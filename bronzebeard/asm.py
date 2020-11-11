from collections import namedtuple
from ctypes import c_uint32
from functools import partial, partialmethod
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


def sign_extend(value, bits):
    sign_bit = 1 << (bits - 1)
    return (value & (sign_bit - 1)) - (value & sign_bit)


def relocate_hi(imm):
    if imm & 0x800:
        imm += 2**12
    return sign_extend((imm >> 12) & 0x000fffff, 20)


def relocate_lo(imm):
    return sign_extend(imm & 0x00000fff, 12)


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


class Program:
    RTypeInstruction = namedtuple('RTypeInstruction', 'inst location rd rs1 rs2')
    ITypeInstruction = namedtuple('ITypeInstruction', 'inst location rd rs1 imm')
    STypeInstruction = namedtuple('STypeInstruction', 'inst location rs1 rs2 imm')
    BTypeInstruction = namedtuple('BTypeInstruction', 'inst location rs1 rs2 imm')
    UTypeInstruction = namedtuple('UTypeInstruction', 'inst location rd imm')
    JTypeInstruction = namedtuple('JTypeInstruction', 'inst location rd imm')
    Blob = namedtuple('Blob', 'data')
    Align = namedtuple('Align', 'boundary')

    def __init__(self):
        self.instructions = []
        self.labels = {}
        self.location = 0

    @property
    def machine_code(self):
        code = bytearray()

        for instruction in self.instructions:
            if isinstance(instruction, Program.RTypeInstruction):
                inst, location, rd, rs1, rs2 = instruction
                code.extend(inst(rd, rs1, rs2))
            elif isinstance(instruction, Program.ITypeInstruction):
                inst, location, rd, rs1, imm = instruction
                imm = self._resolve_immediate(imm, location, inst)
                code.extend(inst(rd, rs1, imm))
            elif isinstance(instruction, Program.STypeInstruction):
                inst, location, rs1, rs2, imm = instruction
                imm = self._resolve_immediate(imm, location, inst)
                code.extend(inst(rs1, rs2, imm))
            elif isinstance(instruction, Program.BTypeInstruction):
                inst, location, rs1, rs2, imm = instruction
                imm = self._resolve_immediate(imm, location, inst)
                code.extend(inst(rs1, rs2, imm))
            elif isinstance(instruction, Program.UTypeInstruction):
                inst, location, rd, imm = instruction
                imm = self._resolve_immediate(imm, location, inst)
                code.extend(inst(rd, imm))
            elif isinstance(instruction, Program.JTypeInstruction):
                inst, location, rd, imm = instruction
                imm = self._resolve_immediate(imm, location, inst)
                code.extend(inst(rd, imm))
            elif isinstance(instruction, Program.Blob):
                code.extend(instruction.data)
            elif isinstance(instruction, Program.Align):
                while len(code) % instruction.boundary != 0:
                    code.append(0)
            else:
                raise ValueError('Invalid instruction type')

        return bytes(code)

    def __enter__(self):
        pass

    def __exit__(self, *args):
        pass

    def _resolve_immediate(self, imm, location, instruction):
        # check if immediate value references a label
        if imm in self.labels:
            # return relative offsets for jump / branch instructions
            if instruction in [JAL, JALR, BEQ, BNE, BLT, BGE, BLTU, BGEU]:
                dest = self.labels[imm]
                return dest - location + 4  # add 4 to account for the jump / branch inst itself
            # otherwise return the raw label location
            else:
                return self.labels[imm]

        # check if immediate value is a number
        try:
            return int(imm)
        except ValueError:
            pass

        # otherwise the immediate value is invalid
        raise ValueError('Invalid or unknown immediate value: {}'.format(imm))

    def _r_type(self, rd, rs1, rs2, instruction):
        self.location += 4
        inst = Program.RTypeInstruction(instruction, self.location, rd, rs1, rs2)
        self.instructions.append(inst)

    def _i_type(self, rd, rs1, imm, instruction):
        self.location += 4
        inst = Program.ITypeInstruction(instruction, self.location, rd, rs1, imm)
        self.instructions.append(inst)

    def _s_type(self, rs1, rs2, imm, instruction):
        self.location += 4
        inst = Program.STypeInstruction(instruction, self.location, rs1, rs2, imm)
        self.instructions.append(inst)

    def _b_type(self, rs1, rs2, imm, instruction):
        self.location += 4
        inst = Program.BTypeInstruction(instruction, self.location, rs1, rs2, imm)
        self.instructions.append(inst)

    def _u_type(self, rd, imm, instruction):
        self.location += 4
        inst = Program.UTypeInstruction(instruction, self.location, rd, imm)
        self.instructions.append(inst)

    def _j_type(self, rd, imm, instruction):
        self.location += 4
        inst = Program.JTypeInstruction(instruction, self.location, rd, imm)
        self.instructions.append(inst)

    def HI(self, value):
        return relocate_hi(value)

    def LO(self, value):
        return relocate_lo(value)

    def LABEL(self, name):
        if name in self.labels:
            raise ValueError('Duplicate label: {}'.format(name))
        self.labels[name] = self.location
        return self

    def BLOB(self, data):
        self.location += len(data)
        blob = Program.Blob(data)
        self.instructions.append(blob)

    def ALIGN(self, boundary=4):
        while self.location % boundary != 0:
            self.location += 1
        align = Program.Align(boundary)
        self.instructions.append(align)

    LUI = partialmethod(_u_type, instruction=LUI)
    AUIPC = partialmethod(_u_type, instruction=AUIPC)
    JAL = partialmethod(_j_type, instruction=JAL)
    JALR = partialmethod(_i_type, instruction=JALR)
    BEQ = partialmethod(_b_type, instruction=BEQ)
    BNE = partialmethod(_b_type, instruction=BNE)
    BLT = partialmethod(_b_type, instruction=BLT)
    BGE = partialmethod(_b_type, instruction=BGE)
    BLTU = partialmethod(_b_type, instruction=BLTU)
    BGEU = partialmethod(_b_type, instruction=BGEU)
    LB = partialmethod(_i_type, instruction=LB)
    LH = partialmethod(_i_type, instruction=LH)
    LW = partialmethod(_i_type, instruction=LW)
    LBU = partialmethod(_i_type, instruction=LBU)
    LHU = partialmethod(_i_type, instruction=LHU)
    SB = partialmethod(_s_type, instruction=SB)
    SH = partialmethod(_s_type, instruction=SH)
    SW = partialmethod(_s_type, instruction=SW)
    ADDI = partialmethod(_i_type, instruction=ADDI)
    SLTI = partialmethod(_i_type, instruction=SLTI)
    SLTIU = partialmethod(_i_type, instruction=SLTIU)
    XORI = partialmethod(_i_type, instruction=XORI)
    ORI = partialmethod(_i_type, instruction=ORI)
    ANDI = partialmethod(_i_type, instruction=ANDI)
    SLLI = partialmethod(_r_type, instruction=SLLI)
    SRLI = partialmethod(_r_type, instruction=SRLI)
    SRAI = partialmethod(_r_type, instruction=SRAI)
    ADD = partialmethod(_r_type, instruction=ADD)
    SUB = partialmethod(_r_type, instruction=SUB)
    SLL = partialmethod(_r_type, instruction=SLL)
    SLT = partialmethod(_r_type, instruction=SLT)
    SLTU = partialmethod(_r_type, instruction=SLTU)
    XOR = partialmethod(_r_type, instruction=XOR)
    SRL = partialmethod(_r_type, instruction=SRL)
    SRA = partialmethod(_r_type, instruction=SRA)
    OR = partialmethod(_r_type, instruction=OR)
    AND = partialmethod(_r_type, instruction=AND)
