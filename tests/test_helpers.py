from ctypes import c_int32

import pytest

from bronzebeard import asm


@pytest.mark.parametrize(
    'value,  expected', [
    ('-1',   True),
    ('1',    True),
    ('0x20', True),
    ('zero', False),
    ('foo:', False),
    ('cat',  False),
    ('x0',   False),
])
def test_is_int(value, expected):
    assert asm.is_int(value) == expected


@pytest.mark.parametrize(
    'value,      bits, expected', [
    # full-size extension simply applies two's complement
    (0b00000000, 8,    0),
    (0b01111111, 8,    127),
    (0b11111111, 8,    -1),
    (0b10000000, 8,    -128),
    (0b00000110, 8,    6),
    (0b00000110, 4,    6),
    (0b00000110, 3,    -2),
    (0x00000000, 32,   0),
    (0xffffffff, 32,   -1),
    (0x00000fff, 12,   -1),
])
def test_sign_extend(value, bits, expected):
    assert asm.sign_extend(value, bits) == expected


@pytest.mark.parametrize(
    'value,      expected', [
    (0x00000000, 0),
    (0x00001000, 1),
    (0x7ffff000, 0x7ffff),
    (0xfffff000, -1),
    (0x80000000, -0x80000),
    # MSB of lower portion being 1 should affect result
    (0x00000800, 1),
    (0x00001800, 2),
    (0x7ffff800, -0x80000),
    (0xfffff800, 0),
    (0x80000800, -0x7ffff),
])
def test_relocate_hi(value, expected):
    assert asm.relocate_hi(value) == expected


@pytest.mark.parametrize(
    'value,      expected', [
    (0x00000000, 0),
    (0x00000001, 1),
    (0x000007ff, 2047),
    (0x00000fff, -1),
    (0x00000800, -2048),
    # upper 20 bits should have no affect
    (0xfffff000, 0),
    (0xfffff001, 1),
    (0xfffff7ff, 2047),
    (0xffffffff, -1),
    (0xfffff800, -2048),
])
def test_relocate_lo(value, expected):
    assert asm.relocate_lo(value) == expected


@pytest.mark.parametrize(
    'value', [
    (0x00000000),
    (0x00000001),
    (0x000007ff),
    (0x00000fff),
    (0x00000800),
    (0xfffff000),
    (0xfffff7ff),
    (0xfffff800),
    (0xffffffff),
    (0x7fffffff),
    (0x02000000),
    (0x02000004),
    (0xdeadbeef),
    (0x12345678),
    (0xcafec0fe),
])
def test_relocate_hi_lo_sum(value):
    hi = asm.relocate_hi(value)
    lo = asm.relocate_lo(value)
    expected = asm.sign_extend(value, 32)

    sum_raw = (hi << 12) + lo
    sum_wrapped = c_int32(sum_raw).value
    assert sum_wrapped == expected
