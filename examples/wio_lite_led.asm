# Turn on the and blue LEDs on the Wio Lite (only has the one)

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


# Func: gpio_operate
# Arg: a0 = GPIO port base addr
# Arg: a1 = GPIO pin number
# Arg: a2 = 0 for off, 1 for on
# Ret: none
gpio_operate:
    # shift 1 over to ON bit for this pin
    li t0 1
    sll t0 t0 a1

    # if a2 is 0 (off), shift extra 16 to the OFF bit for this pin
    bnez a2 gpio_operate_store
    slli t0 t0 16

gpio_operate_store:
    # store the 1 to turn the pin on / off
    sw t0 GPIO_BOP_OFFSET(a0)

    ret


# LED Locations
# (based on schematic)
# --------------------
# Blue: GPIO Port A, Pin 8 (active-high)

main:
    # enable RCU (GPIO port A)
    li a0, RCU_BASE_ADDR
    li a1, (1 << RCU_APB2EN_PAEN_BIT)
    call rcu_init

    # enable blue LED
    li a0, GPIO_BASE_ADDR_A
    li a1, 8
    li a2, (GPIO_CTL_OUT_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ)
    call gpio_init

    # turn on blue LED
    li a0, GPIO_BASE_ADDR_A
    li a1, 8
    li a2, 1
    call gpio_operate
