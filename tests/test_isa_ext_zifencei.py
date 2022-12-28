import struct

import pytest

from bronzebeard import asm


def test_fence_i():
    assert asm.FENCE_I() == 0b00000000000000000001000000001111


@pytest.mark.parametrize(
    'source,    expected', [
    ('fence.i', asm.FENCE_I()),
])
def test_assemble_ext_zifencei(source, expected):
    binary = asm.assemble(source)
    target = struct.pack('<I', expected)
    assert binary == target
