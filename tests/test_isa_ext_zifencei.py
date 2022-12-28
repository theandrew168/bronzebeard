import struct

import pytest

from bronzebeard import asm


@pytest.mark.parametrize(
    'rd, rs1, imm, code', [
    (0,  0,   0,   0b00000000000000000001000000001111),
    (0,  0,   1,   0b00000000000100000001000000001111),
    (31, 0,   0,   0b00000000000000000001111110001111),
    (0,  31,  0,   0b00000000000011111001000000001111),
    (31, 31,  0,   0b00000000000011111001111110001111),
    (31, 0,   1,   0b00000000000100000001111110001111),
    (0,  31,  1,   0b00000000000111111001000000001111),
    (31, 31,  1,   0b00000000000111111001111110001111),
])
def test_fence_i(rd, rs1, imm, code):
    assert asm.FENCE_I(rd, rs1, imm) == code


@pytest.mark.parametrize(
    'source,            expected', [
    ('fence.i x0 x1 0', asm.FENCE_I('x0', 'x1', 0)),
])
def test_assemble_ext_zifencei(source, expected):
    binary = asm.assemble(source)
    target = struct.pack('<I', expected)
    assert binary == target
