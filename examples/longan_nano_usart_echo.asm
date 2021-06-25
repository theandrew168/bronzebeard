CLOCK_FREQ = 8000000
USART_BAUD = 115200
ROM_BASE_ADDR = 0x08000000
RCU_BASE_ADDR = 0x40021000
RCU_APB2EN_OFFSET = 0x18
GPIO_BASE_ADDR_A = 0x40010800
GPIO_BASE_ADDR_C = 0x40011000
GPIO_CTL1_OFFSET = 0x04
GPIO_MODE_IN = 0b00
GPIO_MODE_OUT_50MHZ = 0b11
GPIO_CTL_IN_FLOATING = 0b01
GPIO_CTL_OUT_PUSH_PULL = 0b00
GPIO_CTL_OUT_ALT_PUSH_PULL = 0b10
USART_BASE_ADDR_0 = 0x40013800
USART_STAT_OFFSET = 0x00
USART_DATA_OFFSET = 0x04
USART_BAUD_OFFSET = 0x08
USART_CTL0_OFFSET = 0x0c

j start

# Func: getc
# Arg: none
# Ret: a0 = character received from serial
getc:
    # t1 = stat, t2 = data
    lui t0 %hi(USART_BASE_ADDR_0)
    addi t0 t0 %lo(USART_BASE_ADDR_0)
    addi t1 t0 USART_STAT_OFFSET
    addi t2 t0 USART_DATA_OFFSET
getc_wait:
    lw t3 t1 0  # load stat into t3
    andi t3 t3 (1 << 5)  # isolate RBNE bit
    beq t3 zero getc_wait  # keep looping until ready to recv
    lw a0 t2 0  # load char into a0
    jalr zero ra 0  # return

# Func: putc
# Arg: a0 = character to send over serial
# Ret: none
putc:
    # t1 = stat, t2 = data
    lui t0 %hi(USART_BASE_ADDR_0)
    addi t0 t0 %lo(USART_BASE_ADDR_0)
    addi t1 t0 USART_STAT_OFFSET
    addi t2 t0 USART_DATA_OFFSET
putc_wait:
    lw t3 t1 0  # load stat into t3
    andi t3 t3 (1 << 7)  # isolate TBE bit
    beq t3 zero putc_wait  # keep looping until ready to send
    sw t2 a0 0  # write char from a0
    jalr zero ra 0  # return

# Init serial comm via USART0:
# 1. RCU APB2 enable GPIOA (1 << 2)
# 2. RCU APB2 enable USART0 (1 << 14)
# 3. GPIOA config pin 9 (ctl = OUT_ALT_PUSH_PULL, mode = OUT_50MHZ)
#   Pin 9 offset = ((PIN - 8) * 4) = 4
# 4. GPIOA config pin 10 (ctl = IN_FLOATING, mode = IN)
#   Pin 10 offset = ((PIN - 8) * 4) = 8
# 5. USART0 config baud (CLOCK // BAUD = 69)
# 6. USART0 enable RX (1 << 2)
# 7. USART0 enable TX (1 << 3)
# 7. USART0 enable USART (1 << 13)
start:
    # setup addr and load current APB2EN config into t1
    lui t0 %hi(RCU_BASE_ADDR)
    addi t0 t0 %lo(RCU_BASE_ADDR)
    addi t0 t0 RCU_APB2EN_OFFSET
    lw t1 t0 0

    # setup enable bit for AFIO
    addi t2 zero 1
    or t1 t1 t2

    # setup enable bit for GPIO A
    addi t2 zero 1
    slli t2 t2 2
    or t1 t1 t2

    # setup enable bit for GPIO C
    addi t2 zero 1
    slli t2 t2 4
    or t1 t1 t2

    # setup enable bit for USART 0
    addi t2 zero 1
    slli t2 t2 14
    or t1 t1 t2

    # store APB2EN config
    sw t0 t1 0

    # setup addr and load current GPIO A config into t1
    lui t0 %hi(GPIO_BASE_ADDR_A)
    addi t0 t0 %lo(GPIO_BASE_ADDR_A)
    addi t0 t0 GPIO_CTL1_OFFSET
    lw t1 t0 0

    # clear existing config (pin 9)
    addi t2 zero 0b1111
    slli t2 t2 4
    xori t2 t2 -1
    and t1 t1 t2

    # setup config bits (pin 9)
    addi t2 zero (GPIO_CTL_OUT_ALT_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ)
    slli t2 t2 4
    or t1 t1 t2

    # clear existing config (pin 10)
    addi t2 zero 0b1111
    slli t2 t2 8
    xori t2 t2 -1
    and t1 t1 t2

    # setup config bits (pin 10)
    addi t2 zero (GPIO_CTL_IN_FLOATING << 2 | GPIO_MODE_IN)
    slli t2 t2 8
    or t1 t1 t2

    # store GPIO A config
    sw t0 t1 0

    # setup addr for USART 0
    lui t0 %hi(USART_BASE_ADDR_0)
    addi t0 t0 %lo(USART_BASE_ADDR_0)

    # set baud rate clkdiv
    addi t1 t0 USART_BAUD_OFFSET
    addi t2 zero CLOCK_FREQ // USART_BAUD
    sw t1 t2 0

    # load current USART 0 config into t1
    addi t0 t0 USART_CTL0_OFFSET
    lw t1 t0 0

    # setup enable bit for RX
    addi t2 zero 1
    slli t2 t2 2
    or t1 t1 t2

    # setup enable bit for TX
    addi t2 zero 1
    slli t2 t2 3
    or t1 t1 t2

    # setup enable bit for USART
    addi t2 zero 1
    slli t2 t2 13
    or t1 t1 t2

    # store USART 0 config
    sw t0 t1 0

loop:
    call getc
    call putc
    j loop
