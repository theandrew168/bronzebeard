# Read blocks from the SDCard on the Longan Nano
# Based on:
# https://github.com/riscv-mcu/GD32VF103_Firmware_Library/blob/master/Examples/SPI/SPI_master_slave_fullduplex_polling/main.c

# SPI Locations
# (based on schematic)
# --------------------
# SPI1_MOSI:  B15 (OUT_AF_PUSH_PULL, 50MHz)
# SPI1_MISO:  B14 (IN_FLOATING, 0)
# SPI1_SCLK:  B13 (OUT_AF_PUSH_PULL, 50MHz)
# SPI1_CS_TF: B12 (just leave untouched since CS is active low?)

RCU_BASE_ADDR = 0x40021000  # GD32VF103 Manual: Section 5.3
RCU_APB2EN_OFFSET = 0x18  # GD32VF103 Manual: Section 5.3.7 (GPIO ABCDE, AFIO)
RCU_APB1EN_OFFSET = 0x1c  # GD32VF103 Manual: Section 5.3.8 (SPI1)

GPIOA_BASE_ADDR = 0x40010800  # GD32VF103 Manual: Section 7.5 (green and blue LEDs)
GPIOB_BASE_ADDR = 0x40010c00  # GD32VF103 Manual: Section 7.5 (SPI1)
GPIOC_BASE_ADDR = 0x40011000  # GD32VF103 Manual: Section 7.5 (red LED)
GPIO_CTL0_OFFSET = 0x00  # GD32VF103 Manual: Section 7.5.1 (pins 0-7)
GPIO_CTL1_OFFSET = 0x04  # GD32VF103 Manual: Section 7.5.2 (pins 8-15)

# GD32VF103 Manual: Section 7.3
GPIO_CTL_IN_ANALOG = 0b00
GPIO_CTL_IN_FLOATING = 0b01
GPIO_CTL_IN_PULL_DOWN = 0b10
GPIO_CTL_IN_PULL_UP = 0b10
GPIO_CTL_OUT_PUSH_PULL = 0b00
GPIO_CTL_OUT_OPEN_DRAIN = 0b01
GPIO_CTL_OUT_AF_PUSH_PULL = 0b10
GPIO_CTL_OUT_AF_OPEN_DRAIN = 0b11
GPIO_MODE_OUT_RESERVED = 0b00
GPIO_MODE_OUT_10MHZ = 0b01
GPIO_MODE_OUT_2MHZ = 0b10
GPIO_MODE_OUT_50MHZ = 0b11

SPI1_BASE_ADDR = 0x40003800
SPI_CTL0_OFFSET = 0x00
SPI_CTL1_OFFSET = 0x04
SPI_STAT_OFFSET = 0x08
SPI_DATA_OFFSET = 0x0c

rcu_init:
    # load RCU APB2EN addr into t0
    lui t0, %hi(RCU_BASE_ADDR)
    addi t0, t0, %lo(RCU_BASE_ADDR)
    addi t0, t0, RCU_APB2EN_OFFSET

    # enable GPIO ports A, B, and C
    # enable AFIO
    addi t1, zero, 0b00011101
    sw t0, t1, 0

    # load RCU APB1EN addr into t0
    lui t0, %hi(RCU_BASE_ADDR)
    addi t0, t0, %lo(RCU_BASE_ADDR)
    addi t0, t0, RCU_APB1EN_OFFSET

    # enable SPI1
    addi t1, zero, 1
    slli t1, t1, 14
    sw t0, t1, 0

gpio_init:
    # load GPIOB CTL1 addr into t0
    lui t0, %hi(GPIOB_BASE_ADDR)
    addi t0, t0, %lo(GPIOB_BASE_ADDR)
    addi t0, t0, GPIO_CTL1_OFFSET

    # load current GPIO config into t1
    lw t1, t0, 0

    # SPI1_MOSI:  B15 (OUT_AF_PUSH_PULL, 50MHz)
    addi t2, zero, 0b1111
    slli t2, t2, 28
    xori t2, t2, -1
    and t1, t1, t2

    addi t2, zero, GPIO_CTL_OUT_AF_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ
    slli t2, t2, 28
    or t1, t1, t2

    # SPI1_MISO:  B14 (IN_FLOATING, 0)
    addi t2, zero, 0b1111
    slli t2, t2, 24
    xori t2, t2, -1
    and t1, t1, t2

    addi t2, zero, GPIO_CTL_IN_FLOATING << 2 | 0
    slli t2, t2, 24
    or t1, t1, t2

    # SPI1_SCLK:  B13 (OUT_AF_PUSH_PULL, 50MHz)
    addi t2, zero, 0b1111
    slli t2, t2, 20
    xori t2, t2, -1
    and t1, t1, t2

    addi t2, zero, GPIO_CTL_OUT_AF_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ
    slli t2, t2, 20
    or t1, t1, t2

    # store the GPIO config
    sw t0, t1, 0

# enable SPI
# spi_init_struct.trans_mode           = SPI_TRANSMODE_FULLDUPLEX; (default)
# spi_init_struct.device_mode          = SPI_MASTER;
# spi_init_struct.frame_size           = SPI_FRAMESIZE_8BIT; (default)
# spi_init_struct.clock_polarity_phase = SPI_CK_PL_HIGH_PH_2EDGE; (CLK_HI | 2ND_CLK)
# spi_init_struct.nss                  = SPI_NSS_SOFT;
# spi_init_struct.prescale             = SPI_PSC_8; (PCLK/8 = 0b010)
# spi_init_struct.endian               = SPI_ENDIAN_MSB; (default)

spi_init:
    # load SPI1 CTL0 addr into t0
    lui t0, %hi(SPI1_BASE_ADDR)
    addi t0, t0, %lo(SPI1_BASE_ADDR)
    addi t0, t0, SPI_CTL0_OFFSET

    # load current SPI config into t1
    lw t1, t0, 0

    # enable SPI
    addi t2, zero, 1
    slli t2, t2, 6
    or t1, t1, t2

    # master mode
    addi t2, zero, 1
    slli t2, t2, 2
    or t1, t1, t2

    # clock pull high + first data at second clock
    addi t2, zero, 0b11
    slli t2, t2, 0
    or t1, t1, t2

    # nss software mode
    addi t2, zero, 1
    slli t2, t2, 9
    or t1, t1, t2

    # prescale 8
    addi t2, zero, 0b010
    slli t2, t2, 3
    or t1, t1, t2

    # store the SPI config
    sw t0, t1, 0

main:
    jal zero success

failure:
    # load GPIOC CTL1 addr into t0
    lui t0, %hi(GPIOC_BASE_ADDR)
    addi t0, t0, %lo(GPIOC_BASE_ADDR)
    addi t0, t0, GPIO_CTL1_OFFSET

    # load current GPIO config into t1
    lw t1, t0, 0

    # turn on red LED
    addi t2, zero, 0b1111
    slli t2, t2, 20
    xori t2, t2, -1
    and t1, t1, t2

    addi t2, zero, GPIO_CTL_OUT_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ
    slli t2, t2, 20
    or t1, t1, t2

    # store the GPIO config
    sw t0, t1, 0
    jal zero end

success:
    # load GPIOA CTL0 addr into t0
    lui t0, %hi(GPIOA_BASE_ADDR)
    addi t0, t0, %lo(GPIOA_BASE_ADDR)
    addi t0, t0, GPIO_CTL0_OFFSET

    # load current GPIO config into t1
    lw t1, t0, 0

    # turn on green LED
    addi t2, zero, 0b1111
    slli t2, t2, 4
    xori t2, t2, -1
    and t1, t1, t2

    addi t2, zero, GPIO_CTL_OUT_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ
    slli t2, t2, 4
    or t1, t1, t2

    # store the GPIO config
    sw t0, t1, 0
    jal zero end

end:
