# Turn on the red, green, and blue LEDs on the Longan Nano

RCU_BASE_ADDR     = 0x40021000  # GD32VF103 Manual: Section 5.3
RCU_APB2EN_OFFSET = 0x18  # GD32VF103 Manual: Section 5.3.7

GPIO_BASE_ADDR_A = 0x40010800  # GD32VF103 Manual: Section 7.5 (green and blue LEDs)
GPIO_BASE_ADDR_C = 0x40011000  # GD32VF103 Manual: Section 7.5 (red LED)
GPIO_CTL0_OFFSET = 0x00  # GD32VF103 Manual: Section 7.5.1 (pins 0-7)
GPIO_CTL1_OFFSET = 0x04  # GD32VF103 Manual: Section 7.5.2 (pins 8-15)

# GD32VF103 Manual: Section 7.3
GPIO_MODE_OUT_50MHZ    = 0b11
GPIO_CTL_OUT_PUSH_PULL = 0b00


# jump to "main" since programs execute top to bottom
# we do this to enable writing helper funcs at the top
j main


# Func: rcu_init
# Arg: a0 = RCU base addr
# Arg: a1 = RCU config
# Ret: none
rcu_init:
    # store config
    sw a1, RCU_APB2EN_OFFSET(a0)

    ret


# Func: gpio_init
# Arg: a0 = GPIO port base addr
# Arg: a1 = GPIO pin number
# Arg: a2 = GPIO config (4 bits)
# Ret: none
gpio_init:
    # advance to CTL0
    addi t0, a0, GPIO_CTL0_OFFSET

    # if pin number is less than 8, CTL0 is correct
    slti t1, a1, 8
    bnez t1, gpio_init_config

    # else we need CTL1 and then subtract 8 from the pin number
    addi t0, t0, 4
    addi a1, a1, -8

gpio_init_config:
    # multiply pin number by 4 to get shift amount
    addi t1, zero, 4
    mul a1, a1, t1

    # load current config
    lw t1, 0(t0)

    # align and clear existing pin config
    li t2, 0b1111
    sll t2, t2, a1
    not t2, t2
    and t1, t1, t2

    # align and apply new pin config
    sll a2, a2, a1
    or t1, t1, a2

    # store updated config
    sw t1, 0(t0)

    ret


# LED Locations
# (based on schematic)
# --------------------
# Red:    GPIO Port C, Pin 13
# Green:  GPIO Port A, Pin 1
# Blue:   GPIO Port A, Pin 2

main:
    # enable RCU (GPIO ports A and C)
    li a0, RCU_BASE_ADDR
    li a1, 0b00010100
    call rcu_init

    # enable red LED
    li a0, GPIO_BASE_ADDR_C
    li a1, 13
    li a2, (GPIO_CTL_OUT_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ)
    call gpio_init

    # enable green LED
    li a0, GPIO_BASE_ADDR_A
    li a1, 1
    li a2, (GPIO_CTL_OUT_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ)
    call gpio_init

    # enable blue LED
    li a0, GPIO_BASE_ADDR_A
    li a1, 2
    li a2, (GPIO_CTL_OUT_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ)
    call gpio_init
