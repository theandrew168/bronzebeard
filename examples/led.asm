# Turn on the red LED on the Longan Nano

rcu_init:
    # load RCU base addr into t0
    lui t0 %hi(RCU_BASE_ADDR)
    addi t0 t0 %lo(RCU_BASE_ADDR)
    addi t0 t0 RCU_APB2EN_OFFSET

    # load ABP2EN config into t1
    lw t1 t0 0

    # prepare the GPIO C bit
    addi t2 zero 1
    slli t2 t2 4
    or t1 t1 t2

    # store APB2EN config
    sw t0 t1 0

gpio_init:
    # load GPIO C base addr into t0
    lui t0 %hi(GPIO_BASE_ADDR_C)
    addi t0 t0 %lo(GPIO_BASE_ADDR_C)

    # move t0 forward to control 1 register
    addi t0 t0 GPIO_CTL1_OFFSET

    # load current GPIO confing into t1
    lw t1 t0 0

    # clear existing config
    addi t2 zero 0b1111
    slli t2 t2 20
    xori t2 t2 -1
    and t1 t1 t2

    # set new config settings
    addi t2 zero (GPIO_CTL_OUT_PUSH_POLL << 2 | GPIO_MODE_OUT_50MHZ)
    slli t2 t2 20
    or t1 t1 t2

    # store the GPIO config
    sw t0 t1 0
