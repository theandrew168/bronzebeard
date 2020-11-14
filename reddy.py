from bronzebeard.asm import Program

RCU_BASE_ADDR = 0x40021000
RCU_APB2_ENABLE_OFFSET = 0x18
GPIO_BASE_ADDR_C = 0x40011000
GPIO_CTL1_OFFSET = 0x04
GPIO_MODE_OUT_50MHZ = 0b11
GPIO_CTL_OUT_PUSH_PULL = 0b00


p = Program()

# load RCU APB2EN addr into t0
p.LUI('t0', p.HI(RCU_BASE_ADDR))
p.ADDI('t0', 't0', p.LO(RCU_BASE_ADDR))
p.ADDI('t0', 't0', RCU_APB2_ENABLE_OFFSET)

# load APB2EN config into t1
p.LW('t1', 't0', 0)

# prepare enable bits for GPIO A and GPIO C
#                     | EDCBA  |
p.ADDI('t2', 'zero', 0b00010100)
p.OR('t1', 't1', 't2')

# store the ABP2EN config
p.SW('t0', 't1', 0)  

# load GPIO base addr into t0
p.LUI('t0', p.HI(GPIO_BASE_ADDR_C))
p.ADDI('t0', 't0', p.LO(GPIO_BASE_ADDR_C))

# move t0 forward to control 1 register
p.ADDI('t0', 't0', GPIO_CTL1_OFFSET)

# load current GPIO config into t1
p.LW('t1', 't0', 0)

# clear existing config
p.ADDI('t2', 'zero', 0b1111)
p.SLLI('t2', 't2', 20)
p.XORI('t2', 't2', -1)
p.AND('t1', 't1', 't2')

# set new config settings
p.ADDI('t2', 'zero', (GPIO_CTL_OUT_PUSH_PULL << 2) | GPIO_MODE_OUT_50MHZ)
p.SLLI('t2', 't2', 20)
p.OR('t1', 't1', 't2')

# store the GPIO config
p.SW('t0', 't1', 0)

with open('reddy.bin', 'wb') as f:
    f.write(p.machine_code)
