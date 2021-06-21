import struct

import pytest

from bronzebeard import asm


def test_read_assembly():
    source = 'addi t0 zero 1\naddi t1, zero, 2\naddi t2, zero, 3'
    lines = asm.read_lines(source)
    assert len(lines) == 3
    assert lines[1].contents.strip() == 'addi t1, zero, 2'
    for i, line in enumerate(lines, start=1):
        assert line.file == '<string>'
        assert line.number == i


def test_lex_assembly():
    line = r'addi t0 zero 1'
    tokens = asm.lex_tokens(line)
    assert len(tokens) == 4
    assert tokens.tokens == ['addi', 't0', 'zero', '1']


def test_parse_assembly():
    line = r'addi t0 zero 1'
    tokens = asm.lex_tokens(line)
    item = asm.parse_item(tokens)
    assert isinstance(item, asm.ITypeInstruction)
    assert item.name == 'addi'
    assert item.rd == 't0'
    assert item.rs1 == 'zero'


def test_assemble_string():
    source = r"""
    string hello
    string "world"
    string "hello world"
    string hello  ##  world
    string hello\nworld
    string   hello\\nworld
    """
    binary = asm.assemble(source)
    target = b'hello"world""hello world"hello  ##  worldhello\nworld  hello\\nworld'
    assert binary == target


@pytest.mark.parametrize(
    'source,                expected', [
    ('bytes 1 2 0x03 0b100', b'\x01\x02\x03\x04'),
    ('bytes -1 0xff',        b'\xff\xff'),
    ('shorts 0x1234 0x5678', b'\x34\x12\x78\x56'),
    ('ints  1 2 3 4',        b'\x01\x00\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00\x04\x00\x00\x00'),
    ('longs 1 2 3 4',        b'\x01\x00\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00\x04\x00\x00\x00'),
])
def test_assemble_sequence(source, expected):
    binary = asm.assemble(source)
    assert binary == expected


def test_assemble_align():
    source = r"""
    addi zero zero 0
    pack <B 42
    align 4
    addi zero zero 0
    """
    binary = asm.assemble(source)
    target = b''.join([
        struct.pack('<I', asm.ADDI(0, 0, 0)),
        b'\x2a\x00\x00\x00',
        struct.pack('<I', asm.ADDI(0, 0, 0)),
    ])
    assert binary == target


def test_assemble_pack():
    source = r"""
    ADDR = 0x20000000
    pack <B 0
    pack <B 255
    pack <I ADDR
    """
    binary = asm.assemble(source)
    target = b''.join([
        struct.pack('<B', 0),
        struct.pack('<B', 255),
        struct.pack('<I', 0x20000000),
    ])
    assert binary == target


@pytest.mark.parametrize(
    'shorthand,                transformed', [
    ('db  0',                  'pack <B 0'),
    ('db  -1',                 'pack <b -1'),
    ('db  0xff',               'pack <B 0xff'),
    ('db -128',                'pack <b -128'),
    ('dh  0',                  'pack <H 0'),
    ('dh  0xffff',             'pack <H 0xffff'),
    ('dh -0x7fff',             'pack <h -0x7fff'),
    ('dw  0',                  'pack <I 0'),
    ('dw  0xffffffff',         'pack <I 0xffffffff'),
    ('dw -0x7fffffff',         'pack <i -0x7fffffff'),
    ('dd  0',                  'pack <Q 0'),
    ('dd  0xffffffffffffffff', 'pack <Q 0xffffffffffffffff'),
    ('dd -0x7fffffffffffffff', 'pack <q -0x7fffffffffffffff'),
])
def test_assemble_shorthand_packs(shorthand, transformed):
    shorthand_bin = asm.assemble(shorthand)
    transformed_bin = asm.assemble(transformed)
    assert shorthand_bin == transformed_bin


def test_assemble_constants():
    source = r"""
    FOO = 42
    BAR = FOO * 2
    BAZ = BAR >> 1 & 0b11111
    W = 's0'
    IP = gp
    addi zero zero BAR
    addi W IP BAZ
    """
    binary = asm.assemble(source)
    target = b''.join(struct.pack('<I', inst) for inst in [
        asm.ADDI(0, 0, 84),
        asm.ADDI('s0', 'gp', 10),
    ])
    assert binary == target


def test_assemble_modifiers():
    source = r"""
    ADDR = 0x20000000

    addi zero zero 0
    addi zero zero 0
    addi zero zero 0

    main:
        # without nestable exprs under hi / lo
        lui t0 %hi ADDR
        addi t0 t0 %lo(ADDR)
        addi t0 t0 main

        # with nestable exprs under hi / lo
        lui t0 %hi %position main ADDR
        addi t0 t0 %lo(%position(main, ADDR))
    """
    binary = asm.assemble(source)
    target = b''.join(struct.pack('<I', inst) for inst in [
        asm.ADDI(0, 0, 0),
        asm.ADDI(0, 0, 0),
        asm.ADDI(0, 0, 0),
        asm.LUI('t0', asm.relocate_hi(0x20000000)),
        asm.ADDI('t0', 't0', asm.relocate_lo(0x20000000)),
        asm.ADDI('t0', 't0', 12),
        asm.LUI('t0', asm.relocate_hi(0x20000000 + 12)),
        asm.ADDI('t0', 't0', asm.relocate_lo(0x20000000 + 12)),
    ])
    assert binary == target


def test_assemble_labels_and_jumps():
    source = r"""
    start:
        addi t0 zero 42
        jal zero end
    middle:
        beq t0 zero main
        addi t0 t0 -1
    end:
        jal zero middle
    main:
        addi zero zero 0
    """
    binary = asm.assemble(source)
    target = b''.join(struct.pack('<I', inst) for inst in [
        asm.ADDI('t0', 'zero', 42),
        asm.JAL('zero', 12),
        asm.BEQ('t0', 'zero', 12),
        asm.ADDI('t0', 't0', -1),
        asm.JAL('zero', -8),
        asm.ADDI(0, 0, 0),
    ])
    assert binary == target


def test_assemble_alternate_offset_syntax():
    source = r"""
    jalr x0, x1, 0
    jalr x0, 0(x1)
    lw x0, x1, 0
    lw x0, 0(x1)
    sb x0, x1, 0
    sb x1, 0(x0)
    """
    binary = asm.assemble(source)
    target = b''.join(struct.pack('<I', inst) for inst in [
        asm.JALR('x0', 'x1', 0),
        asm.JALR('x0', 'x1', 0),
        asm.LW('x0', 'x1', 0),
        asm.LW('x0', 'x1', 0),
        asm.SB('x0', 'x1', 0),
        asm.SB('x0', 'x1', 0),
    ])
    assert binary == target


def test_assemble_alternate_offset_syntax_compressed():
    source = r"""
    c.lw x8, x9, 0
    c.lw x8, 0(x9)
    c.sw x8, x9, 0
    c.sw x9, 0(x8)
    """
    binary = asm.assemble(source)
    target = b''.join(struct.pack('<I', inst) for inst in [
        asm.C_LW('x8', 'x9', 0),
        asm.C_LW('x8', 'x9', 0),
        asm.C_SW('x8', 'x9', 0),
        asm.C_SW('x8', 'x9', 0),
    ])
    assert binary == target


@pytest.mark.parametrize(
    'pseudo,             transformed', [

    ('nop',              'addi x0 x0 0'),
    ('li t0 0',          'addi t0 x0 0'),
    ('li t0 -2048',      'addi t0 x0 -2048'),
    ('li t0 2047',       'addi t0 x0 2047'),
    ('li t0 -2049',      'lui t0 %hi(-2049)\n addi t0 t0 %lo(-2049)'),
    ('li t0 2048',       'lui t0 %hi(2048)\n addi t0 t0 %lo(2048)'),
    ('mv t0 t1',         'addi t0 t1 0'),
    ('not t0 t1',        'xori t0 t1 -1'),
    ('neg t0 t1',        'sub t0 x0 t1'),
    ('seqz t0 t1',       'sltiu t0 t1 1'),
    ('snez t0 t1',       'sltu t0 x0 t1'),
    ('sltz t0 t1',       'slt t0 t1 x0'),
    ('sgtz t0 t1',       'slt t0 x0 t1'),

    ('beqz t0 test',     'beq t0 x0 test'),
    ('bnez t0 test',     'bne t0 x0 test'),
    ('blez t0 test',     'bge x0 t0 test'),
    ('bgez t0 test',     'bge t0 x0 test'),
    ('bltz t0 test',     'blt t0 x0 test'),
    ('bgtz t0 test',     'blt x0 t0 test'),

    ('bgt t0 t1 test',   'blt t1 t0 test'),
    ('ble t0 t1 test',   'bge t1 t0 test'),
    ('bgtu t0 t1 test',  'bltu t1 t0 test'),
    ('bleu t0 t1 test',  'bgeu t1 t0 test'),

    ('j test',           'jal x0 test'),
    ('jal test',         'jal x1 test'),
    ('jr t0',            'jalr x0 0(t0)'),
    ('jalr t0',          'jalr x1 0(t0)'),
    ('ret',              'jalr x0 0(x1)'),

    ('fence',            'fence 0b1111 0b1111'),
])
def test_assemble_pseudo_instructions(pseudo, transformed):
    labels = {'test': 0}
    pseudo_bin = asm.assemble(pseudo, labels=labels)
    transformed_bin = asm.assemble(transformed, labels=labels)
    assert pseudo_bin == transformed_bin


def test_assemble_pseudo_instruction_call():
    source = r"""
    call main

    align 0x00020000
    main:
        j main
    """
    binary = asm.assemble(source)[:8]
    target = b''.join(struct.pack('<I', inst) for inst in [
        asm.AUIPC('x1', asm.relocate_hi(0x00020000)),
        asm.JALR('x1', 'x1', asm.relocate_lo(0x00020000)),
    ])
    assert binary == target


def test_assemble_pseudo_instruction_tail():
    source = r"""
    tail main

    align 0x00020000
    main:
        j main
    """
    binary = asm.assemble(source)[:8]
    target = b''.join(struct.pack('<I', inst) for inst in [
        asm.AUIPC('x6', asm.relocate_hi(0x00020000)),
        asm.JALR('x0', 'x6', asm.relocate_lo(0x00020000)),
    ])
    assert binary == target


@pytest.mark.parametrize(
    'regular,       compressed', [
    ('jal x0 test', 'c.j test'),
    ('jal x1 test', 'c.jal test'),
])
def test_assemble_compress(regular, compressed):
    labels = {'test': 0}
    regular_bin = asm.assemble(regular, labels=labels, compress=True)
    compressed_bin = asm.assemble(compressed, labels=labels)
    assert regular_bin == compressed_bin


# https://github.com/theandrew168/bronzebeard/issues/9
def test_assemble_hex_register():
    source = r"""
    slli a4,a4,0xa
    """
    binary = asm.assemble(source)
    target = b''.join(struct.pack('<I', inst) for inst in [
        asm.SLLI('a4', 'a4', 10),
    ])
    assert binary == target
