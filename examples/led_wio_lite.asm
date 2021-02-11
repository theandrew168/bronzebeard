# Turn on the blue LED on the Wio-Lite

# LED Locations
# (based on schematic)
# --------------------
# Blue:   GPIO Port A, Pin 8

RCU_BASE_ADDR = 0x40021000  # GD32VF103 Manual: Section 5.3
RCU_APB2EN_OFFSET = 0x18  # GD32VF103 Manual: Section 5.3.7

GPIO_BASE_ADDR_A = 0x40010800  # GD32VF103 Manual: Section 7.5 (blue LED)
GPIO_BASE_ADDR_C = 0x40011000  # GD32VF103 Manual: Section 7.5
GPIO_CTL0_OFFSET = 0x00  # GD32VF103 Manual: Section 7.5.1 (pins 0-7)
GPIO_CTL1_OFFSET = 0x04  # GD32VF103 Manual: Section 7.5.2 (pins 8-15)
GPIO_OCTL_OFFSET = 0x0c  # GD32VF103 Manual: Section 7.5.4
GPIO_MODE_OUT_50MHZ = 0b11  # GD32VF103 Manual: Section 7.3
GPIO_CTL_OUT_PUSH_PULL = 0b00  # GD32VF103 Manual: Section 7.3

rcu_init:
    # load RCU APB2EN addr into t0
    lui t0, %hi(RCU_BASE_ADDR)
    addi t0, t0, %lo(RCU_BASE_ADDR)
    addi t0, t0, RCU_APB2EN_OFFSET

    # load ABP2EN config into t1
    lw t1, t0, 0

    # prepare the GPIO A and C bits (we only need port A for the blue LED, though)
    addi t2, zero, 0b00010100
    or t1, t1, t2

    # store APB2EN config
    sw t0, t1, 0

gpio_init:
    # load GPIO base addr into t0
    lui t0, %hi(GPIO_BASE_ADDR_A)
    addi t0, t0, %lo(GPIO_BASE_ADDR_A)

    # move t0 forward to control 1 register
    addi t0, t0, GPIO_CTL1_OFFSET

    # load current GPIO config into t1
    lw t1, t0, 0

    # clear existing config (don't want to disturb the other pin configs)
    addi t2, zero, 0b1111
    # no need to shift since pin 8 config occupies bottom 4 bits of reg
    xori t2, t2, -1  # flip value to have zeroes over pin 8
    and t1, t1, t2  # clear the config for pin 8 while leaving all others untouched

    # set new config settings
    addi t2, zero, GPIO_CTL_OUT_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ
    # same story here: no shift needed for pin 8
    or t1, t1, t2  # set the config for pin 8 while leaving all other untouched

    # store the GPIO config
    sw t0, t1, 0

    # load GPIO base addr into t0
    lui t0, %hi(GPIO_BASE_ADDR_A)
    addi t0, t0, %lo(GPIO_BASE_ADDR_A)

    # move t0 forward to output control register
    addi t0, t0, GPIO_OCTL_OFFSET

    # enable pin 8
    addi t1, zero, 1
    slli t1, t1, 8
    sw t0, t1, 0
