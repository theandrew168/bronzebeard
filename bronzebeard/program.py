from functools import partialmethod

from bronzebeard import asm


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


class Program:

    def __init__(self):
        self.machine_code = bytearray()
        self.labels = {}

    def __enter__(self):
        pass

    def __exit__(self, *args):
        pass

    def _resolve_immediate(self, imm):
        # check if immediate value is a number
        try:
            return int(imm)
        except ValueError:
            pass

        # check if immediate value references a label
        if imm in self.labels:
            return self.labels[imm]

        # otherwise the immediate value is invalid
        raise ValueError('Invalid immediate value: {}'.format(imm))

    def _resolve_register(self, reg):
        # check if register is a number
        try:
            return int(reg)
        except ValueError:
            pass

        # check if register corresponds to a valid name
        if reg in REGISTERS:
            return REGISTERS[reg]

        # otherwise the register is invalid
        raise ValueError('Invalid register: {}'.format(reg))

    def _r_type_instruction(self, rd, rs1, rs2, instruction):
        rd = self._resolve_register(rd)
        rs1 = self._resolve_register(rs1)
        rs2 = self._resolve_register(rs2)

        code = instruction(rd, rs1, rs2)
        self.machine_code.extend(code)

    def _i_type_instruction(self, rd, rs1, imm, instruction):
        rd = self._resolve_register(rd)
        rs1 = self._resolve_register(rs1)
        imm = self._resolve_immediate(imm)

        code = instruction(rd, rs1, imm)
        self.machine_code.extend(code)

    def _s_type_instruction(self, rs1, rs2, imm, instruction):
        rs1 = self._resolve_register(rs1)
        rs2 = self._resolve_register(rs2)
        imm = self._resolve_immediate(imm)

        code = instruction(rs1, rs2, imm)
        self.machine_code.extend(code)

    def _b_type_instruction(self, rs1, rs2, imm, instruction):
        rs1 = self._resolve_register(rs1)
        rs2 = self._resolve_register(rs2)
        imm = self._resolve_immediate(imm)

        code = instruction(rs1, rs2, imm)
        self.machine_code.extend(code)

    def _u_type_instruction(self, rd, imm, instruction):
        rd = self._resolve_register(rd)
        imm = self._resolve_immediate(imm)

        code = instruction(rd, imm)
        self.machine_code.extend(code)

    def _j_type_instruction(self, rd, imm, instruction):
        rd = self._resolve_register(rd)
        imm = self._resolve_immediate(imm)

        code = instruction(rd, imm)
        self.machine_code.extend(code)

    def HI(self, value):
        return relocate_hi(value)

    def LO(self, value):
        return relocate_lo(value)

    def LABEL(self, name):
        if name in self.labels:
            raise ValueError('Duplicate label: {}'.format(name))
        self.labels[name] = len(self.machine_code)
        return self

    LUI = partialmethod(_u_type_instruction, instruction=asm.LUI)
    AUIPC = partialmethod(_u_type_instruction, instruction=asm.AUIPC)
    JAL = partialmethod(_j_type_instruction, instruction=asm.JAL)
    JALR = partialmethod(_i_type_instruction, instruction=asm.JALR)
    BEQ = partialmethod(_b_type_instruction, instruction=asm.BEQ)
    LW = partialmethod(_i_type_instruction, instruction=asm.LW)
    SW = partialmethod(_s_type_instruction, instruction=asm.SW)
    ADDI = partialmethod(_i_type_instruction, instruction=asm.ADDI)
    SLLI = partialmethod(_r_type_instruction, instruction=asm.SLLI)
    XOR = partialmethod(_r_type_instruction, instruction=asm.XOR)
    OR = partialmethod(_r_type_instruction, instruction=asm.OR)
    AND = partialmethod(_r_type_instruction, instruction=asm.AND)
