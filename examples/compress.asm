test:
    addi x8 sp 4
    lw x8 0(x9)
    sw x8 0(x9)
    addi x0 x0 0
    addi x1 x1 1
    jal ra test
    addi x1 x0 1
    lui x1 1
    lui x1 0xfffff
    addi x2 x2 16
    srli x8 x8 1
    srai x8 x8 1
    andi x8 x8 0
    sub x8 x8 x9
    xor x8 x8 x9
    or x8 x8 x9
    and x8 x8 x9
    jal x0 test
    beq x8 x0 0
    bne x8 x0 0
    slli x1 x1 1
    lw x1 0(x2)
    jalr x0 0(x1)
    add x1 x0 x2
    ebreak
    jalr x1 0(x1)
    add x1 x1 x2
    sw x1 0(x2)
