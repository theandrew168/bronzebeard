# Read blocks from the SDCard on the Longan Nano
#
# References:
# https://github.com/riscv-mcu/GD32VF103_Firmware_Library/blob/master/Examples/SPI/SPI_master_slave_fullduplex_polling/main.c
# http://elm-chan.org/docs/mmc/mmc_e.html
# https://github.com/arduino-libraries/SD/blob/master/src/utility/Sd2Card.cpp
# http://www.dejazzer.com/ee379/lecture_notes/lec12_sd_card.pdf
# https://github.com/esmil/gd32vf103inator/blob/master/examples/LonganNano/sdcard.c
# https://github.com/sipeed/Longan_GD32VF_examples/blob/master/gd32v_lcd/src/fatfs/tf_card.c

# SPI Locations
# (based on schematic and data sheet)
# --------------------
# SPI1_CS_TF: B12 (OUT_PUSH_PULL, 50MHz)
# SPI1_SCLK:  B13 (OUT_AF_PUSH_PULL, 50MHz)
# SPI1_MISO:  B14 (IN_FLOATING, 0)
# SPI1_MOSI:  B15 (OUT_AF_PUSH_PULL, 50MHz)

RCU_BASE_ADDR = 0x40021000  # GD32VF103 Manual: Section 5.3
RCU_APB2EN_OFFSET = 0x18  # GD32VF103 Manual: Section 5.3.7 (GPIO ABCDE, AFIO)
RCU_APB1EN_OFFSET = 0x1c  # GD32VF103 Manual: Section 5.3.8 (SPI1)

GPIOA_BASE_ADDR = 0x40010800  # GD32VF103 Manual: Section 7.5 (green and blue LEDs)
GPIOB_BASE_ADDR = 0x40010c00  # GD32VF103 Manual: Section 7.5 (SPI1)
GPIOC_BASE_ADDR = 0x40011000  # GD32VF103 Manual: Section 7.5 (red LED)
GPIO_CTL0_OFFSET = 0x00  # GD32VF103 Manual: Section 7.5.1 (pins 0-7)
GPIO_CTL1_OFFSET = 0x04  # GD32VF103 Manual: Section 7.5.2 (pins 8-15)
GPIO_BOP_OFFSET = 0x10  # GD32VF103 Manual: Section 7.5.5

# GD32VF103 Manual: Section 7.3, Figure 7.1
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

SPI1_BASE_ADDR = 0x40003800  # GD32VF103 Manual: Section 18.11
SPI_CTL0_OFFSET = 0x00  # GD32VF103 Manual: Section 18.11.1
SPI_CTL1_OFFSET = 0x04  # GD32VF103 Manual: Section 18.11.2
SPI_STAT_OFFSET = 0x08  # GD32VF103 Manual: Section 18.11.3
SPI_DATA_OFFSET = 0x0c  # GD32VF103 Manual: Section 18.11.4

rcu_init:
    # load RCU APB2EN addr into t0
    lui t0, %hi(RCU_BASE_ADDR)
    addi t0, t0, %lo(RCU_BASE_ADDR)
    addi t0, t0, RCU_APB2EN_OFFSET

    # enable GPIO ports A, B, and C
    addi t1, zero, 0b00011100
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

    # SPI1_CS_TF:  B12 (OUT_PUSH_PULL, 50MHz)
    addi t2, zero, 0b1111
    slli t2, t2, 16
    xori t2, t2, -1
    and t1, t1, t2

    addi t2, zero, GPIO_CTL_OUT_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ
    slli t2, t2, 16
    or t1, t1, t2

    # SPI1_SCLK:  B13 (OUT_AF_PUSH_PULL, 50MHz)
    addi t2, zero, 0b1111
    slli t2, t2, 20
    xori t2, t2, -1
    and t1, t1, t2

    addi t2, zero, GPIO_CTL_OUT_AF_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ
    slli t2, t2, 20
    or t1, t1, t2

    # SPI1_MISO:  B14 (IN_FLOATING, 0)
    addi t2, zero, 0b1111
    slli t2, t2, 24
    xori t2, t2, -1
    and t1, t1, t2

    addi t2, zero, GPIO_CTL_IN_FLOATING << 2 | 0
    slli t2, t2, 24
    or t1, t1, t2

    # SPI1_MOSI:  B15 (OUT_AF_PUSH_PULL, 50MHz)
    addi t2, zero, 0b1111
    slli t2, t2, 28
    xori t2, t2, -1
    and t1, t1, t2

    addi t2, zero, GPIO_CTL_OUT_AF_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ
    slli t2, t2, 28
    or t1, t1, t2

    # store the GPIO config
    sw t0, t1, 0

spi_init:
    # load SPI1 CTL0 addr into t0
    lui t0, %hi(SPI1_BASE_ADDR)
    addi t0, t0, %lo(SPI1_BASE_ADDR)
    addi t0, t0, SPI_CTL0_OFFSET

    # load current SPI config into t1
    lw t1, t0, 0

    # software NSS
    addi t2, zero, 1
    slli t2, t2, 9
    or t1, t1, t2

    # NSS pulled high (won't work at all without this)
    addi t2, zero, 1
    slli t2, t2, 8
    or t1, t1, t2

    # enable SPI
    addi t2, zero, 1
    slli t2, t2, 6
    or t1, t1, t2

    # set SPI clock: 8MHz / 32 = 250KHz
    addi t2, zero, 0b100
    slli t2, t2, 3
    or t1, t1, t2

    # master mode
    addi t2, zero, 1
    slli t2, t2, 2
    or t1, t1, t2

    # store the SPI config
    sw t0, t1, 0

    jal zero main

# Procedure: spi_send
# Usage: jal ra spi_send
# Arg: a0 = byte to send over SPI
spi_send:
    # t1 = stat, t2 = data
    lui t0, %hi(SPI1_BASE_ADDR)
    addi t0, t0, %lo(SPI1_BASE_ADDR)
    addi t1, t0, SPI_STAT_OFFSET
    addi t2, t0, SPI_DATA_OFFSET
spi_send_wait:
    lw t3, t1, 0  # load stat into t3
    andi t3, t3, 0b10  # isolate TBE bit
    beq t3, zero, spi_send_wait  # keep looping until ready to send
    sw t2, a0, 0  # write byte from a0
    jalr zero, ra, 0  # return

# Procedure: spi_recv
# Usage: jal ra spi_recv
# Ret: a0 = byte received over SPI
spi_recv:
    # t1 = stat, t2 = data
    lui t0, %hi(SPI1_BASE_ADDR)
    addi t0, t0, %lo(SPI1_BASE_ADDR)
    addi t1, t0, SPI_STAT_OFFSET
    addi t2, t0, SPI_DATA_OFFSET
    # write 0xff into SPI_DATA
    # TODO: why is this required? what does it really do?
    # TODO: is this just sending 8 dummy bits to pulse the clock and read data?
    # TODO: in which case shouldn't this happen every loop? (first part)
    # TODO: and shouldn't TBE be asserted first?
    addi t3, zero, 0xff
    sw t2, t3, 0
spi_recv_wait:
    # TODO: limit attempts to prevent infinite loop?
    lw t3, t1, 0  # load stat into t3
    andi t3, t3, 0b01  # isolate RBNE bit
    beq t3, zero, spi_recv_wait  # keep looping until ready to recv
    lw a0, t2, 0  # read byte into a0
    addi t4, zero, 0xff  # load 0xff into t4 (MISO defaults to high)
    beq a0, t4, spi_recv_wait  # keep looping until "real" response arrives
    jalr zero, ra, 0  # return

# Procedure: spi_flush
# Usage: jal ra spi_flush
spi_flush:
    # t1 = stat
    lui t0, %hi(SPI1_BASE_ADDR)
    addi t0, t0, %lo(SPI1_BASE_ADDR)
    addi t1, t0, SPI_STAT_OFFSET
spi_flush_wait:
    lw t3, t1, 0  # load stat into t3
    andi t3, t3, 1 << 7  # isolate TRANS bit
    bne t3, zero, spi_flush_wait  # loop until SPI is idle
    jalr zero ra 0  # return

main:
    # t0 = GPIOB_BOP
    lui t0, %hi(GPIOB_BASE_ADDR)
    addi t0, t0, %lo(GPIOB_BASE_ADDR)
    addi t0, t0, GPIO_BOP_OFFSET

    # set CS high (disable)
    addi t1, zero, 1
    slli t1, t1, 12
    sw t0, t1, 0

    # set CS low (enable)
    addi t1, zero, 1
    slli t1, t1, 28
    sw t0, t1, 0

sd_init:
    # send 80 (>= 74) clock pulses to "boot" the SD card
    addi s0, zero, 10
sd_init_cond:
    beq s0, zero, sd_init_done
sd_init_body:
    addi a0, zero, 0xff
    jal ra spi_send
sd_init_next:
    addi s0, s0, -1
    jal zero sd_init_cond
sd_init_done:

    # write CMD0 (1 byte): 0x40 | 0x00 = 0x40 (0b01 + CMD)
    # write ARG (4 bytes): 4 * 0x00
    # write CRC (1 byte): CMD0 -> 0x95, CMD8 -> 0x87, default 0xff (dont care?)
    # total: 0x40 0x00 x00 0x00 x00 0x95
    addi a0, zero, 0x40
    jal ra spi_send
    addi a0, zero, 0x00
    jal ra spi_send
    addi a0, zero, 0x00
    jal ra spi_send
    addi a0, zero, 0x00
    jal ra spi_send
    addi a0, zero, 0x00
    jal ra spi_send
    addi a0, zero, 0x95
    jal ra spi_send

    # wait for trans to finish
    jal ra spi_flush

    # read resp from SD Card
    jal ra spi_recv

    # success if 0x01 else failure
    addi t0, zero, 0x01
    beq a0 t0 success

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
    jal zero done

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
    jal zero done

done:
