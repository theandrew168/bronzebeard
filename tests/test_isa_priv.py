import struct

import pytest

from bronzebeard import asm


def test_sret():
    assert asm.SRET() == 0b00010000001000000000000001110011


def test_mret():
    assert asm.MRET() == 0b00110000001000000000000001110011


def test_mnret():
    assert asm.MNRET() == 0b01110000001000000000000001110011


def test_wfi():
    assert asm.WFI() == 0b00010000010100000000000001110011
    

def test_sctrclr():
    assert asm.SCTRCLR() == 0b00010000010000000000000001110011
    

@pytest.mark.parametrize(
    'rs1, rs2, code', [
    (0,   0,   0b00010010000000000000000001110011),
    (31,  0,   0b00010010000011111000000001110011),
    (0,   31,  0b00010011111100000000000001110011),
    (31,  31,  0b00010011111111111000000001110011),
])
def test_sfence_vma(rs1, rs2, code):
    assert asm.SFENCE_VMA(rs1, rs2) == code


@pytest.mark.parametrize(
    'rs1, rs2, code', [
    (0,   0,   0b00100010000000000000000001110011),
    (31,  0,   0b00100010000011111000000001110011),
    (0,   31,  0b00100011111100000000000001110011),
    (31,  31,  0b00100011111111111000000001110011),
])
def test_hfence_vvma(rs1, rs2, code):
    assert asm.HFENCE_VVMA(rs1, rs2) == code


@pytest.mark.parametrize(
    'rs1, rs2, code', [
    (0,   0,   0b01100010000000000000000001110011),
    (31,  0,   0b01100010000011111000000001110011),
    (0,   31,  0b01100011111100000000000001110011),
    (31,  31,  0b01100011111111111000000001110011),
])
def test_hfence_gvma(rs1, rs2, code):
    assert asm.HFENCE_GVMA(rs1, rs2) == code


@pytest.mark.parametrize(
    'rd, rs1, code', [
    (0,  0,   0b01100000000000000100000001110011),
    (31, 0,   0b01100000000000000100111111110011),
    (0,  31,  0b01100000000011111100000001110011),
    (31, 31,  0b01100000000011111100111111110011),
])
def test_hlv_b(rd, rs1, code):
    assert asm.HLV_B(rd, rs1) == code


@pytest.mark.parametrize(
    'rd, rs1, code', [
    (0,  0,   0b01100000000100000100000001110011),
    (31, 0,   0b01100000000100000100111111110011),
    (0,  31,  0b01100000000111111100000001110011),
    (31, 31,  0b01100000000111111100111111110011),
])
def test_hlv_bu(rd, rs1, code):
    assert asm.HLV_BU(rd, rs1) == code


@pytest.mark.parametrize(
    'rd, rs1, code', [
    (0,  0,   0b01100100000000000100000001110011),
    (31, 0,   0b01100100000000000100111111110011),
    (0,  31,  0b01100100000011111100000001110011),
    (31, 31,  0b01100100000011111100111111110011),
])
def test_hlv_h(rd, rs1, code):
    assert asm.HLV_H(rd, rs1) == code


@pytest.mark.parametrize(
    'rd, rs1, code', [
    (0,  0,   0b01100100000100000100000001110011),
    (31, 0,   0b01100100000100000100111111110011),
    (0,  31,  0b01100100000111111100000001110011),
    (31, 31,  0b01100100000111111100111111110011),
])
def test_hlv_hu(rd, rs1, code):
    assert asm.HLV_HU(rd, rs1) == code


@pytest.mark.parametrize(
    'rd, rs1, code', [
    (0,  0,   0b01101000000000000100000001110011),
    (31, 0,   0b01101000000000000100111111110011),
    (0,  31,  0b01101000000011111100000001110011),
    (31, 31,  0b01101000000011111100111111110011),
])
def test_hlv_w(rd, rs1, code):
    assert asm.HLV_W(rd, rs1) == code


@pytest.mark.parametrize(
    'rd, rs1, code', [
    (0,  0,   0b01100100001100000100000001110011),
    (31, 0,   0b01100100001100000100111111110011),
    (0,  31,  0b01100100001111111100000001110011),
    (31, 31,  0b01100100001111111100111111110011),
])
def test_hlvx_hu(rd, rs1, code):
    assert asm.HLVX_HU(rd, rs1) == code


@pytest.mark.parametrize(
    'rd, rs1, code', [
    (0,  0,   0b01101000001100000100000001110011),
    (31, 0,   0b01101000001100000100111111110011),
    (0,  31,  0b01101000001111111100000001110011),
    (31, 31,  0b01101000001111111100111111110011),
])
def test_hlvx_wu(rd, rs1, code):
    assert asm.HLVX_WU(rd, rs1) == code


@pytest.mark.parametrize(
    'rs1, rs2, code', [
    (0,   0,   0b01100010000000000100000001110011),
    (31,  0,   0b01100010000011111100000001110011),
    (0,   31,  0b01100011111100000100000001110011),
    (31,  31,  0b01100011111111111100000001110011),
])
def test_hsv_b(rs1, rs2, code):
    assert asm.HSV_B(rs1, rs2) == code


@pytest.mark.parametrize(
    'rs1, rs2, code', [
    (0,   0,   0b01100110000000000100000001110011),
    (31,  0,   0b01100110000011111100000001110011),
    (0,   31,  0b01100111111100000100000001110011),
    (31,  31,  0b01100111111111111100000001110011),
])
def test_hsv_h(rs1, rs2, code):
    assert asm.HSV_H(rs1, rs2) == code


@pytest.mark.parametrize(
    'rs1, rs2, code', [
    (0,   0,   0b01101010000000000100000001110011),
    (31,  0,   0b01101010000011111100000001110011),
    (0,   31,  0b01101011111100000100000001110011),
    (31,  31,  0b01101011111111111100000001110011),
])
def test_hsv_w(rs1, rs2, code):
    assert asm.HSV_W(rs1, rs2) == code


@pytest.mark.parametrize(
    'rs1, rs2, code', [
    (0,   0,   0b00010110000000000000000001110011),
    (31,  0,   0b00010110000011111000000001110011),
    (0,   31,  0b00010111111100000000000001110011),
    (31,  31,  0b00010111111111111000000001110011),
])
def test_sinval_vma(rs1, rs2, code):
    assert asm.SINVAL_VMA(rs1, rs2) == code


def test_sfence_w_inval():
    assert asm.SFENCE_W_INVAL() == 0b00011000000000000000000001110011


def test_sfence_inval_ir():
    assert asm.SFENCE_INVAL_IR() == 0b00011000000100000000000001110011


@pytest.mark.parametrize(
    'rs1, rs2, code', [
    (0,   0,   0b00100110000000000000000001110011),
    (31,  0,   0b00100110000011111000000001110011),
    (0,   31,  0b00100111111100000000000001110011),
    (31,  31,  0b00100111111111111000000001110011),
])
def test_hinval_vvma(rs1, rs2, code):
    assert asm.HINVAL_VVMA(rs1, rs2) == code


@pytest.mark.parametrize(
    'rs1, rs2, code', [
    (0,   0,   0b01100110000000000000000001110011),
    (31,  0,   0b01100110000011111000000001110011),
    (0,   31,  0b01100111111100000000000001110011),
    (31,  31,  0b01100111111111111000000001110011),
])
def test_hinval_gvma(rs1, rs2, code):
    assert asm.HINVAL_GVMA(rs1, rs2) == code


@pytest.mark.parametrize(
    'source,              expected', [
    ('sret',              asm.SRET()),
    ('mret',              asm.MRET()),
    ('mnret',             asm.MNRET()),
    ('wfi',               asm.WFI()),
    ('sctrclr',           asm.SCTRCLR()),
    ('sfence.vma x0 x1',  asm.SFENCE_VMA('x0', 'x1')),
    ('hfence.vvma x0 x1', asm.HFENCE_VVMA('x0', 'x1')),
    ('hfence.gvma x0 x1', asm.HFENCE_GVMA('x0', 'x1')),
    ('hlv.b x0 x1',       asm.HLV_B('x0', 'x1')),
    ('hlv.bu x0 x1',      asm.HLV_BU('x0', 'x1')),
    ('hlv.h x0 x1',       asm.HLV_H('x0', 'x1')),
    ('hlv.hu x0 x1',      asm.HLV_HU('x0', 'x1')),
    ('hlv.w x0 x1',       asm.HLV_W('x0', 'x1')),
    ('hlvx.hu x0 x1',     asm.HLVX_HU('x0', 'x1')),
    ('hlvx.wu x0 x1',     asm.HLVX_WU('x0', 'x1')),
    ('hsv.b x0 x1',       asm.HSV_B('x0', 'x1')),
    ('hsv.h x0 x1',       asm.HSV_H('x0', 'x1')),
    ('hsv.w x0 x1',       asm.HSV_W('x0', 'x1')),
    ('sinval.vma x0 x1',  asm.SINVAL_VMA('x0', 'x1')),
    ('sfence.w.inval',    asm.SFENCE_W_INVAL()),
    ('sfence.inval.ir',   asm.SFENCE_INVAL_IR()),
])
def test_assemble_priv(source, expected):
    binary = asm.assemble(source)
    target = struct.pack('<I', expected)
    assert binary == target
