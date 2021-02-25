import abc
import argparse
from collections import namedtuple
from ctypes import c_uint32
from functools import partial
import os
import re
import struct
import sys
from typing import cast, Dict, Iterable, List, Tuple, Union


REGISTERS: Dict[str, int] = {
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


# a register can be int 0-31 or a "nice" name like x0, zero, or t10
Register = Union[int, str]

def lookup_register(reg: Register) -> int:
    # check if register corresponds to a valid name
    if reg in REGISTERS:
        reg = REGISTERS[str(reg)]#cast(str, reg)]

    # ensure register is a number
    try:
        reg = int(reg)
    except ValueError:
        raise ValueError('Register is not a number or valid name: {}'.format(reg))

    # ensure register is between 0 and 31
    if reg < 0 or reg > 31:
        raise ValueError('Register must be between 0 and 31: {}'.format(reg))

    return reg


def r_type(rd: Register, rs1: Register, rs2: Register, opcode: int, funct3: int, funct7: int) -> bytes:
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


def i_type(rd: Register, rs1: Register, imm: int, opcode: int, funct3: int) -> bytes:
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


def s_type(rs1: Register, rs2: Register, imm: int, opcode: int, funct3: int) -> bytes:
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


def b_type(rs1: Register, rs2: Register, imm: int, opcode: int, funct3: int) -> bytes:
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


def u_type(rd: Register, imm: int, opcode: int) -> bytes:
    rd = lookup_register(rd)

    if imm < -0x80000 or imm > 0x7ffff:
        raise ValueError('20-bit immediate must be between -0x80000 (-524288) and 0x7ffff (524287): {}'.format(imm))

    imm = c_uint32(imm).value & 0b11111111111111111111

    code = 0
    code |= opcode
    code |= rd << 7
    code |= imm << 12

    return struct.pack('<I', code)


def j_type(rd: Register, imm: int, opcode: int) -> bytes:
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


# RV32I Base Instruction Set
LUI    = partial(u_type, opcode=0b0110111)
AUIPC  = partial(u_type, opcode=0b0010111)
JAL    = partial(j_type, opcode=0b1101111)
JALR   = partial(i_type, opcode=0b1100111, funct3=0b000)
BEQ    = partial(b_type, opcode=0b1100011, funct3=0b000)
BNE    = partial(b_type, opcode=0b1100011, funct3=0b001)
BLT    = partial(b_type, opcode=0b1100011, funct3=0b100)
BGE    = partial(b_type, opcode=0b1100011, funct3=0b101)
BLTU   = partial(b_type, opcode=0b1100011, funct3=0b110)
BGEU   = partial(b_type, opcode=0b1100011, funct3=0b111)
LB     = partial(i_type, opcode=0b0000011, funct3=0b000)
LH     = partial(i_type, opcode=0b0000011, funct3=0b001)
LW     = partial(i_type, opcode=0b0000011, funct3=0b010)
LBU    = partial(i_type, opcode=0b0000011, funct3=0b100)
LHU    = partial(i_type, opcode=0b0000011, funct3=0b101)
SB     = partial(s_type, opcode=0b0100011, funct3=0b000)
SH     = partial(s_type, opcode=0b0100011, funct3=0b001)
SW     = partial(s_type, opcode=0b0100011, funct3=0b010)
ADDI   = partial(i_type, opcode=0b0010011, funct3=0b000)
SLTI   = partial(i_type, opcode=0b0010011, funct3=0b010)
SLTIU  = partial(i_type, opcode=0b0010011, funct3=0b011)
XORI   = partial(i_type, opcode=0b0010011, funct3=0b100)
ORI    = partial(i_type, opcode=0b0010011, funct3=0b110)
ANDI   = partial(i_type, opcode=0b0010011, funct3=0b111)
SLLI   = partial(r_type, opcode=0b0010011, funct3=0b001, funct7=0b0000000)
SRLI   = partial(r_type, opcode=0b0010011, funct3=0b101, funct7=0b0000000)
SRAI   = partial(r_type, opcode=0b0010011, funct3=0b101, funct7=0b0100000)
ADD    = partial(r_type, opcode=0b0110011, funct3=0b000, funct7=0b0000000)
SUB    = partial(r_type, opcode=0b0110011, funct3=0b000, funct7=0b0100000)
SLL    = partial(r_type, opcode=0b0110011, funct3=0b001, funct7=0b0000000)
SLT    = partial(r_type, opcode=0b0110011, funct3=0b010, funct7=0b0000000)
SLTU   = partial(r_type, opcode=0b0110011, funct3=0b011, funct7=0b0000000)
XOR    = partial(r_type, opcode=0b0110011, funct3=0b100, funct7=0b0000000)
SRL    = partial(r_type, opcode=0b0110011, funct3=0b101, funct7=0b0000000)
SRA    = partial(r_type, opcode=0b0110011, funct3=0b101, funct7=0b0100000)
OR     = partial(r_type, opcode=0b0110011, funct3=0b110, funct7=0b0000000)
AND    = partial(r_type, opcode=0b0110011, funct3=0b111, funct7=0b0000000)

# RV32M Standard Extension
MUL    = partial(r_type, opcode=0b0110011, funct3=0b000, funct7=0b0000001)
MULH   = partial(r_type, opcode=0b0110011, funct3=0b001, funct7=0b0000001)
MULHSU = partial(r_type, opcode=0b0110011, funct3=0b010, funct7=0b0000001)
MULHU  = partial(r_type, opcode=0b0110011, funct3=0b011, funct7=0b0000001)
DIV    = partial(r_type, opcode=0b0110011, funct3=0b100, funct7=0b0000001)
DIVU   = partial(r_type, opcode=0b0110011, funct3=0b101, funct7=0b0000001)
REM    = partial(r_type, opcode=0b0110011, funct3=0b110, funct7=0b0000001)
REMU   = partial(r_type, opcode=0b0110011, funct3=0b111, funct7=0b0000001)

R_TYPE_INSTRUCTIONS = {
    'slli':   SLLI,
    'srli':   SRLI,
    'srai':   SRAI,
    'add':    ADD,
    'sub':    SUB,
    'sll':    SLL,
    'slt':    SLT,
    'sltu':   SLTU,
    'xor':    XOR,
    'srl':    SRL,
    'sra':    SRA,
    'or':     OR,
    'and':    AND,
    'mul':    MUL,
    'mulh':   MULH,
    'mulhsu': MULHSU,
    'mulhu':  MULHU,
    'div':    DIV,
    'divu':   DIVU,
    'rem':    REM,
    'remu':   REMU,
}

I_TYPE_INSTRUCTIONS = {
    'jalr':   JALR,
    'lb':     LB,
    'lh':     LH,
    'lw':     LW,
    'lbu':    LBU,
    'lhu':    LHU,
    'addi':   ADDI,
    'slti':   SLTI,
    'sltiu':  SLTIU,
    'xori':   XORI,
    'ori':    ORI,
    'andi':   ANDI,
}

S_TYPE_INSTRUCTIONS = {
    'sb':     SB,
    'sh':     SH,
    'sw':     SW,
}

B_TYPE_INSTRUCTIONS = {
    'beq':    BEQ,
    'bne':    BNE,
    'blt':    BLT,
    'bge':    BGE,
    'bltu':   BLTU,
    'bgeu':   BGEU,
}

U_TYPE_INSTRUCTIONS = {
    'lui':    LUI,
    'auipc':  AUIPC,
}

J_TYPE_INSTRUCTIONS = {
    'jal':    JAL,
}

INSTRUCTIONS = {}
INSTRUCTIONS.update(R_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(I_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(S_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(B_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(U_TYPE_INSTRUCTIONS)
INSTRUCTIONS.update(J_TYPE_INSTRUCTIONS)


def sign_extend(value: int, bits: int) -> int:
    sign_bit = 1 << (bits - 1)
    return (value & (sign_bit - 1)) - (value & sign_bit)


def relocate_hi(imm: int) -> int:
    if imm & 0x800:
        imm += 2**12
    return sign_extend((imm >> 12) & 0x000fffff, 20)


def relocate_lo(imm: int) -> int:
    return sign_extend(imm & 0x00000fff, 12)


# environment and expressions
Env = Dict[str, int]

class Expression(abc.ABC):

    @abc.abstractmethod
    def eval(self, position: int, env: Env) -> int:
        """Evaluate an expression to an integer"""


class Arithmetic(Expression):
    expr: str

    def __init__(self, expr: str) -> None:
        self.expr = expr

    def eval(self, position: int, env: Env) -> int:
        return eval(self.expr, env)


class Position(Expression):
    label: str
    expr: Arithmetic

    def __init__(self, label: str, expr: Arithmetic) -> None:
        self.label = label
        self.expr = expr

    def eval(self, position: int, env: Env) -> int:
        dest = env[self.label]
        base = self.expr.eval(position, env)
        return base + dest


class Offset(Expression):
    label: str

    def __init__(self, label: str) -> None:
        self.label = label

    def eval(self, position: int, env: Env) -> int:
        dest = env[self.label]
        return dest - position


class Hi(Expression):
    expr: Expression

    def __init__(self, expr: Expression) -> None:
        self.expr = expr

    def eval(self, position: int, env: Env) -> int:
        if isinstance(self.expr, Hi) or isinstance(self.expr, Lo):
            raise TypeError('%hi and %lo expressions cannot nest')

        value = self.expr.eval(position, env)
        return relocate_hi(value)


class Lo(Expression):
    expr: Expression

    def __init__(self, expr: Expression) -> None:
        self.expr = expr

    def eval(self, position: int, env: Env) -> int:
        if isinstance(self.expr, Hi) or isinstance(self.expr, Lo):
            raise TypeError('%hi and %lo expressions cannot nest')

        value = self.expr.eval(position, env)
        return relocate_lo(value)


# a single, unmodified line of assembly source code
class Line:
    file: str
    number: int
    contents: str

    def __init__(self, file: str, number: int, contents: str) -> None:
        self.file = file
        self.number = number
        self.contents = contents

    def __str__(self) -> str:
        return '{}:{}: {}'.format(self.file, self.number, self.contents)


# tokens emitted from a lexed line
class Tokens:
    line: Line
    tokens: List[str]

    def __init__(self, line: Line, tokens: List[str]):
        self.line = line
        self.tokens = tokens

    def __str__(self) -> str:
        return str(self.tokens)


# base class for assembly "things"
class Item(abc.ABC):
    line: Line

    def __init__(self, line: Line) -> None:
        self.line = line

    def __str__(self) -> str:
        return '{} @ {}'.format(self.__class__.__name__, self.line)

    @abc.abstractmethod
    def size(self, position: int) -> int:
        """Check the size of this item at the given position in a program"""


class Align(Item):
    alignment: int

    def __init__(self, line: Line, alignment: int) -> None:
        super().__init__(line)
        self.alignment = alignment

    def size(self, position: int) -> int:
        return self.alignment - (position % self.alignment)


class Label(Item):
    name: str

    def __init__(self, line: Line, name: str) -> None:
        super().__init__(line)
        self.name = name

    def size(self, position: int) -> int:
        return 0


class Constant(Item):
    name: str
    expr: Expression

    def __init__(self, line: Line, name: str, expr: Expression) -> None:
        super().__init__(line)
        self.name = name
        self.expr = expr

    def size(self, position: int) -> int:
        return 0


class Pack(Item):
    fmt: str
    expr: Expression

    def __init__(self, line: Line, fmt: str, expr: Expression) -> None:
        super().__init__(line)
        self.fmt = fmt
        self.expr = expr

    def size(self, position: int) -> int:
        return struct.calcsize(self.fmt)


class Blob(Item):
    data: bytes

    def __init__(self, line: Line, data: bytes) -> None:
        super().__init__(line)
        self.data = data

    def size(self, position: int) -> int:
        return len(self.data)


class RTypeInstruction(Item):
    name: str
    rd: Register
    rs1: Register
    rs2: Register

    def __init__(self, line: Line, name: str, rd: Register, rs1: Register, rs2: Register) -> None:
        super().__init__(line)
        self.name = name
        self.rd = rd
        self.rs1 = rs1
        self.rs2 = rs2

    def size(self, position: int) -> int:
        return 4


class ITypeInstruction(Item):
    name: str
    rd: Register
    rs1: Register
    expr: Expression

    def __init__(self, line: Line, name: str, rd: Register, rs1: Register, expr: Expression) -> None:
        super().__init__(line)
        self.name = name
        self.rd = rd
        self.rs1 = rs1
        self.expr = expr

    def size(self, position: int) -> int:
        return 4


class STypeInstruction(Item):
    name: str
    rs1: Register
    rs2: Register
    expr: Expression

    def __init__(self, line: Line, name: str, rs1: Register, rs2: Register, expr: Expression) -> None:
        super().__init__(line)
        self.name = name
        self.rs1 = rs1
        self.rs2 = rs2
        self.expr = expr

    def size(self, position: int) -> int:
        return 4


class BTypeInstruction(Item):
    name: str
    rs1: Register
    rs2: Register
    expr: Expression

    def __init__(self, line: Line, name: str, rs1: Register, rs2: Register, expr: Expression) -> None:
        super().__init__(line)
        self.name = name
        self.rs1 = rs1
        self.rs2 = rs2
        self.expr = expr

    def size(self, position: int) -> int:
        return 4


class UTypeInstruction(Item):
    name: str
    rd: Register
    expr: Expression

    def __init__(self, line: Line, name: str, rd: Register, expr: Expression) -> None:
        super().__init__(line)
        self.name = name
        self.rd = rd
        self.expr = expr

    def size(self, position: int) -> int:
        return 4


class JTypeInstruction(Item):
    name: str
    rd: Register
    expr: Expression

    def __init__(self, line: Line, name: str, rd: Register, expr: Expression) -> None:
        super().__init__(line)
        self.name = name
        self.rd = rd
        self.expr = expr

    def size(self, position: int) -> int:
        return 4


def read_assembly(path_or_source: str) -> Iterable[Line]:
    if os.path.exists(path_or_source):
        path = path_or_source
        with open(path) as f:
            source = f.read()
    else:
        path = __name__
        source = path_or_source

    for i, line in enumerate(source.splitlines(), start=1):
        yield Line(path, i, line)


def lex_assembly(lines: Iterable[Line]) -> Iterable[Tokens]:
    for line in lines:
        # strip comments
        contents = re.sub(r'#.*?$', r'', line.contents, flags=re.MULTILINE)

        # strip whitespace
        contents = contents.strip()

        # skip empty lines
        if len(contents) == 0:
            continue

        # split line into tokens
        tokens = re.split(r'[\s,()\'"]+', contents)

        # remove empty tokens
        while '' in tokens:
            tokens.remove('')

        yield Tokens(line, tokens)


# helper for parsing exprs since they occur in multiple places
def parse_expression(expr: List[str]):
    if expr[0].lower() == '%position':
        _, label, *expr = expr
        return Position(label, Arithmetic(' '.join(expr)))
    elif expr[0].lower() == '%offset':
        _, label = expr
        return Offset(label)
    elif expr[0].lower() == '%hi':
        _, *expr = expr
        return Hi(parse_expression(expr))
    elif expr[0].lower() == '%lo':
        _, *expr = expr
        return Lo(parse_expression(expr))
    else:
        return Arithmetic(' '.join(expr))


def parse_assembly(tokens: Iterable[Tokens]) -> Iterable[Item]:
    for t in tokens:
        line = t.line
        toks = t.tokens

        # labels
        if len(toks) == 1 and toks[0].endswith(':'):
            label = toks[0].rstrip(':')
            yield Label(line, label)
        # constants
        elif len(toks) >= 3 and toks[1] == '=':
            name, _, *expr = toks
            yield Constant(line, name, parse_expression(expr))
        # aligns
        elif toks[0].lower() == 'align':
            _, alignment = toks
            yield Align(line, int(alignment))
        # packs
        elif toks[0].lower() == 'pack':
            _, fmt, *expr = toks
            yield Pack(line, fmt, parse_expression(expr))
        # bytes (TODO: essentially eval'd here, should they be?)
        elif toks[0].lower() == 'bytes':
            _, *expr = toks
            data = [int(byte, base=0) for byte in expr]
            for byte in data:
                if byte < 0 or byte > 255:
                    raise ValueError('bytes literal not in range [0, 255] at {}'.format(line))
            yield Blob(line, bytes(data))
        # strings (TODO: essentially eval'd here, should they be?)
        elif toks[0].lower() == 'string':
            _, *expr = toks
            text = ' '.join(expr)
            yield Blob(line, text.encode())
        # r-type instructions
        elif toks[0].lower() in R_TYPE_INSTRUCTIONS:
            name, rd, rs1, rs2 = toks
            name = name.lower()
            yield RTypeInstruction(line, name, rd, rs1, rs2)
        # i-type instructions
        elif toks[0].lower() in I_TYPE_INSTRUCTIONS:
            name, rd, rs1, *expr = toks
            name = name.lower()
            yield ITypeInstruction(line, name, rd, rs1, parse_expression(expr))
        # s-type instructions
        elif toks[0].lower() in S_TYPE_INSTRUCTIONS:
            name, rs1, rs2, *expr = toks
            name = name.lower()
            yield STypeInstruction(line, name, rs1, rs2, parse_expression(expr))
        # b-type instructions
        elif toks[0].lower() in B_TYPE_INSTRUCTIONS:
            name, rs1, rs2, *expr = toks
            name = name.lower()
            # ensure behavior is "offset" for branch instructions
            if expr[0] != '%offset':
                expr.insert(0, '%offset')
            yield BTypeInstruction(line, name, rs1, rs2, parse_expression(expr))
        # u-type instructions
        elif toks[0].lower() in U_TYPE_INSTRUCTIONS:
            name, rd, *expr = toks
            name = name.lower()
            yield UTypeInstruction(line, name, rd, parse_expression(expr))
        # j-type instructions
        elif toks[0].lower() in J_TYPE_INSTRUCTIONS:
            name, rd, *expr = toks
            name = name.lower()
            # ensure behavior is "offset" for branch instructions
            if expr[0] != '%offset':
                expr.insert(0, '%offset')
            yield JTypeInstruction(line, name, rd, parse_expression(expr))
        else:
            print(toks)
            raise ValueError('invalid item at {}'.format(line))


def resolve_aligns(items: Iterable[Item]) -> Iterable[Item]:
    position = 0

    for item in items:
        if isinstance(item, Align):
            padding = item.size(position)
            position += padding
            yield Blob(item.line, b'\x00' * padding)
        else:
            position += item.size(position)
            yield item


def resolve_labels(items: Iterable[Item], env: Env) -> Iterable[Item]:
    position = 0

    for item in items:
        if isinstance(item, Label):
            env[item.name] = position
        else:
            position += item.size(position)
            yield item


def resolve_constants(items: Iterable[Item], env: Env) -> Iterable[Item]:
    position = 0

    for item in items:
        if isinstance(item, Constant):
            if item.name in REGISTERS:
                raise ValueError('constant name shadows register name "{}" at: {}'.format(item.name, item.line))
            env[item.name] = item.expr.eval(position, env)
        else:
            position += item.size(position)
            yield item


def resolve_registers(items: Iterable[Item], env: Env) -> Iterable[Item]:
    for item in items:
        if hasattr(item, 'rd'):
            item.rd = env.get(item.rd) or item.rd
        if hasattr(item, 'rs1'):
            item.rs1 = env.get(item.rs1) or item.rs1
        if hasattr(item, 'rs2'):
            item.rs2 = env.get(item.rs2) or item.rs2
        yield item


def resolve_immediates(items: Iterable[Item], env: Env) -> Iterable[Item]:
    position = 0

    for item in items:
        if hasattr(item, 'expr'):
            item.expr = item.expr.eval(position, env)
        position += item.size(position)
        yield item


def resolve_instructions(items: Iterable[Item]) -> Iterable[Item]:
    for item in items:
        if isinstance(item, RTypeInstruction):
            encode_func = INSTRUCTIONS[item.name]
            code = encode_func(item.rd, item.rs1, item.rs2)
            yield Blob(item.line, code)
        elif isinstance(item, ITypeInstruction):
            encode_func = INSTRUCTIONS[item.name]
            code = encode_func(item.rd, item.rs1, item.expr)
            yield Blob(item.line, code)
        elif isinstance(item, STypeInstruction):
            encode_func = INSTRUCTIONS[item.name]
            code = encode_func(item.rs1, item.rs2, item.expr)
            yield Blob(item.line, code)
        elif isinstance(item, BTypeInstruction):
            encode_func = INSTRUCTIONS[item.name]
            code = encode_func(item.rs1, item.rs2, item.expr)
            yield Blob(item.line, code)
        elif isinstance(item, UTypeInstruction):
            encode_func = INSTRUCTIONS[item.name]
            code = encode_func(item.rd, item.expr)
            yield Blob(item.line, code)
        elif isinstance(item, JTypeInstruction):
            encode_func = INSTRUCTIONS[item.name]
            code = encode_func(item.rd, item.expr)
            yield Blob(item.line, code)
        else:
            yield item


def resolve_packs(items: Iterable[Item]) -> Iterable[Item]:
    for item in items:
        if isinstance(item, Pack):
            data = struct.pack(item.fmt, item.expr)
            yield Blob(item.line, data)
        else:
            yield item


def resolve_blobs(items: Iterable[Item]) -> bytes:
    output = bytearray()
    for item in items:
        if not isinstance(item, Blob):
            raise ValueError('expected only blobs at {}'.format(item.line))
        output.extend(item.data)
    return output


# Passes:
# 0. Read + Lex + Parse source
# 1. Resolve aligns  (convert aligns to blobs based on position)
# 2. Resolve labels  (store label locations into env)
# 3. Resolve constants  (eval expr and update env)
# 4. Resolve registers  (could be constants for readability)
# 5. Resolve immediates  (Arithmetic, Position, Offset, Hi, Lo)
# 6. Resolve instructions  (convert xTypeInstruction to Blob)
# 7. Resolve packs  (convert Pack to Blob)
# 8. Resolve blobs  (merge all Blobs into a single binary)

def assemble(path: str) -> bytes:
    """
    Assemble a RISC-V assembly program into a raw binary.

    :param source: A string of the assembly source program.
    :returns: The assembled binary as bytes.
    """

    # lex and parse the source
    lines = read_assembly(path)
    tokens = lex_assembly(lines)
    items = parse_assembly(tokens)

    # exclude Python builtins from eval env
    # https://docs.python.org/3/library/functions.html#eval
    env: Dict[str, int] = {
        '__builtins__': 0,
    }
    env.update(REGISTERS)

    items = resolve_aligns(items)
    items = list(resolve_labels(items, env))
    items = list(resolve_constants(items, env))
    items = resolve_registers(items, env)
    items = resolve_immediates(items, env)
    items = resolve_instructions(items)
    items = resolve_packs(items)
    program = resolve_blobs(items)
    from pprint import pprint
    pprint(env)
    return program


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Assemble RISC-V source code',
        prog='python -m bronzebeard.asm',
    )
    parser.add_argument('input_asm', type=str, help='input source file')
    parser.add_argument('output_bin', type=str, help='output binary file')
    args = parser.parse_args()

    binary = assemble(args.input_asm)
    with open(args.output_bin, 'wb') as out_bin:
        out_bin.write(binary)
