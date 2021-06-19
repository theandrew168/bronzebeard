import struct

import pytest

from bronzebeard import asm


@pytest.mark.parametrize(
    'rd, rs1, rs2, code', [
    (0,  0,   0,   0b00000010000000000000000000110011),
    (31, 0,   0,   0b00000010000000000000111110110011),
    (0,  31,  0,   0b00000010000011111000000000110011),
    (31, 31,  0,   0b00000010000011111000111110110011),
    (0,  0,   31,  0b00000011111100000000000000110011),
    (31, 0,   31,  0b00000011111100000000111110110011),
    (0,  31,  31,  0b00000011111111111000000000110011),
    (31, 31,  31,  0b00000011111111111000111110110011),
])
def test_mul(rd, rs1, rs2, code):
    assert asm.MUL(rd, rs1, rs2) == code


@pytest.mark.parametrize(
    'rd, rs1, rs2, code', [
    (0,  0,   0,   0b00000010000000000001000000110011),
    (31, 0,   0,   0b00000010000000000001111110110011),
    (0,  31,  0,   0b00000010000011111001000000110011),
    (31, 31,  0,   0b00000010000011111001111110110011),
    (0,  0,   31,  0b00000011111100000001000000110011),
    (31, 0,   31,  0b00000011111100000001111110110011),
    (0,  31,  31,  0b00000011111111111001000000110011),
    (31, 31,  31,  0b00000011111111111001111110110011),
])
def test_mulh(rd, rs1, rs2, code):
    assert asm.MULH(rd, rs1, rs2) == code


@pytest.mark.parametrize(
    'rd, rs1, rs2, code', [
    (0,  0,   0,   0b00000010000000000010000000110011),
    (31, 0,   0,   0b00000010000000000010111110110011),
    (0,  31,  0,   0b00000010000011111010000000110011),
    (31, 31,  0,   0b00000010000011111010111110110011),
    (0,  0,   31,  0b00000011111100000010000000110011),
    (31, 0,   31,  0b00000011111100000010111110110011),
    (0,  31,  31,  0b00000011111111111010000000110011),
    (31, 31,  31,  0b00000011111111111010111110110011),
])
def test_mulhsu(rd, rs1, rs2, code):
    assert asm.MULHSU(rd, rs1, rs2) == code


@pytest.mark.parametrize(
    'rd, rs1, rs2, code', [
    (0,  0,   0,   0b00000010000000000011000000110011),
    (31, 0,   0,   0b00000010000000000011111110110011),
    (0,  31,  0,   0b00000010000011111011000000110011),
    (31, 31,  0,   0b00000010000011111011111110110011),
    (0,  0,   31,  0b00000011111100000011000000110011),
    (31, 0,   31,  0b00000011111100000011111110110011),
    (0,  31,  31,  0b00000011111111111011000000110011),
    (31, 31,  31,  0b00000011111111111011111110110011),
])
def test_mulhu(rd, rs1, rs2, code):
    assert asm.MULHU(rd, rs1, rs2) == code


@pytest.mark.parametrize(
    'rd, rs1, rs2, code', [
    (0,  0,   0,   0b00000010000000000100000000110011),
    (31, 0,   0,   0b00000010000000000100111110110011),
    (0,  31,  0,   0b00000010000011111100000000110011),
    (31, 31,  0,   0b00000010000011111100111110110011),
    (0,  0,   31,  0b00000011111100000100000000110011),
    (31, 0,   31,  0b00000011111100000100111110110011),
    (0,  31,  31,  0b00000011111111111100000000110011),
    (31, 31,  31,  0b00000011111111111100111110110011),
])
def test_div(rd, rs1, rs2, code):
    assert asm.DIV(rd, rs1, rs2) == code


@pytest.mark.parametrize(
    'rd, rs1, rs2, code', [
    (0,  0,   0,   0b00000010000000000101000000110011),
    (31, 0,   0,   0b00000010000000000101111110110011),
    (0,  31,  0,   0b00000010000011111101000000110011),
    (31, 31,  0,   0b00000010000011111101111110110011),
    (0,  0,   31,  0b00000011111100000101000000110011),
    (31, 0,   31,  0b00000011111100000101111110110011),
    (0,  31,  31,  0b00000011111111111101000000110011),
    (31, 31,  31,  0b00000011111111111101111110110011),
])
def test_divu(rd, rs1, rs2, code):
    assert asm.DIVU(rd, rs1, rs2) == code


@pytest.mark.parametrize(
    'rd, rs1, rs2, code', [
    (0,  0,   0,   0b00000010000000000110000000110011),
    (31, 0,   0,   0b00000010000000000110111110110011),
    (0,  31,  0,   0b00000010000011111110000000110011),
    (31, 31,  0,   0b00000010000011111110111110110011),
    (0,  0,   31,  0b00000011111100000110000000110011),
    (31, 0,   31,  0b00000011111100000110111110110011),
    (0,  31,  31,  0b00000011111111111110000000110011),
    (31, 31,  31,  0b00000011111111111110111110110011),
])
def test_rem(rd, rs1, rs2, code):
    assert asm.REM(rd, rs1, rs2) == code


@pytest.mark.parametrize(
    'rd, rs1, rs2, code', [
    (0,  0,   0,   0b00000010000000000111000000110011),
    (31, 0,   0,   0b00000010000000000111111110110011),
    (0,  31,  0,   0b00000010000011111111000000110011),
    (31, 31,  0,   0b00000010000011111111111110110011),
    (0,  0,   31,  0b00000011111100000111000000110011),
    (31, 0,   31,  0b00000011111100000111111110110011),
    (0,  31,  31,  0b00000011111111111111000000110011),
    (31, 31,  31,  0b00000011111111111111111110110011),
])
def test_remu(rd, rs1, rs2, code):
    assert asm.REMU(rd, rs1, rs2) == code


@pytest.mark.parametrize(
    'source,            expected', [
    ('mul    x0 x1 x2', asm.MUL('x0', 'x1', 'x2')),
    ('mulh   x0 x1 x2', asm.MULH('x0', 'x1', 'x2')),
    ('mulhsu x0 x1 x2', asm.MULHSU('x0', 'x1', 'x2')),
    ('mulhu  x0 x1 x2', asm.MULHU('x0', 'x1', 'x2')),
    ('div    x0 x1 x2', asm.DIV('x0', 'x1', 'x2')),
    ('divu   x0 x1 x2', asm.DIVU('x0', 'x1', 'x2')),
    ('rem    x0 x1 x2', asm.REM('x0', 'x1', 'x2')),
    ('remu   x0 x1 x2', asm.REMU('x0', 'x1', 'x2')),
])
def test_assemble_ext_m(source, expected):
    binary = asm.assemble(source)
    target = struct.pack('<I', expected)
    assert binary == target
