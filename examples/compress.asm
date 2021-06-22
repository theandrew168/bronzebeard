test:
    addi x8 sp 4
    lw x8 0(x9)
    sw x8 0(x9)
    addi x0 x0 0
    addi x1 x1 1
near:
    jal x0 near
    jal ra near
