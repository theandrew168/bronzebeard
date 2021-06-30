# Turn on the red, green, and blue LEDs on the Longan Nano

include gd32vf103.asm


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
    slli a1, a1, 2

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
# Red:   GPIO Port C, Pin 13 (active-low)
# Green: GPIO Port A, Pin 1  (active-low)
# Blue:  GPIO Port A, Pin 2  (active-low)

main:
    # enable RCU (GPIO ports A and C)
    li a0, RCU_BASE_ADDR
    li a1, (1 << RCU_APB2EN_PAEN_BIT) | (1 << RCU_APB2EN_PCEN_BIT)
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

    # NOTE: no need to explicitly turn the LEDs on because they are
    #   all active-low (they turn on when the GPIO pins are off / grounded)
