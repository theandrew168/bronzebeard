# Read blocks from the SDCard on the Longan Nano
#
# References:
# https://github.com/riscv-mcu/GD32VF103_Firmware_Library/blob/master/Examples/SPI/SPI_master_slave_fullduplex_polling/main.c
# http://elm-chan.org/docs/mmc/mmc_e.html
# https://github.com/arduino-libraries/SD/blob/master/src/utility/Sd2Card.cpp
# http://www.dejazzer.com/ee379/lecture_notes/lec12_sd_card.pdf
# https://github.com/esmil/gd32vf103inator/blob/master/examples/LonganNano/sdcard.c
# https://github.com/sipeed/Longan_GD32VF_examples/blob/master/gd32v_lcd/src/fatfs/tf_card.c

# GPIO Config
# (based on schematic and data sheet)
# --------------------
# SPI1_CS_TF - B12 (OUT_AF_PUSH_PULL, 50MHz)
# SPI1_SCLK  - B13 (OUT_AF_PUSH_PULL, 50MHz)
# SPI1_MISO  - B14 (IN_FLOATING, 0)
# SPI1_MOSI  - B15 (OUT_AF_PUSH_PULL, 50MHz)

# SPI Config
# ----------
# SPIEN  - SPI enable
# PSC    - Master clock prescaler selection (PCLK/64) (8MHz / 64 = 125kHz)
# MSTMOD - Master mode enable
# NSSDRV - Drive NSS output

# SD Card Config
# --------------
# send 80 (>= 74) clock pulses
# CMD0 (arg=0, software reset)
#   check for 0x01
# CMD8 (arg=0x000001aa, check voltage range)
#   check for 0x01 0x00 0x00 0x01 0xaa
# CMD55 (arg=0, setup app cmd)
# CMD41 (arg=0x40000000, start init w/ host capacity support (HCS))
#   may take up to 1s
#   if 0x01, retry
#   if 0x00, success
# CMD58 (arg=0, read operation conditions register (OCR))
#   check card capacity status (CCS) bit
#   if bit30 == 1, done (card is SDHC/SDXC w/ block of 512)
#   if bit30 == 0, send CMD16 (arg=0x00000200, set block size to 512 bytes), check for 0x01

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

    # SPI1_CS_TF:  B12 (OUT_AF_PUSH_PULL, 50MHz)
    addi t2, zero, 0b1111
    slli t2, t2, 16
    xori t2, t2, -1
    and t1, t1, t2

    addi t2, zero, GPIO_CTL_OUT_AF_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ
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

    # enable SPI
    addi t2, zero, 1
    slli t2, t2, 6
    or t1, t1, t2

    # set SPI clock: 8MHz / 64 = 125kHz
    addi t2, zero, 0b101
    slli t2, t2, 3
    or t1, t1, t2

    # master mode
    addi t2, zero, 1
    slli t2, t2, 2
    or t1, t1, t2

    # store the SPI config
    sw t0, t1, 0

    # load SPI1 CTL1 addr into t0
    lui t0, %hi(SPI1_BASE_ADDR)
    addi t0, t0, %lo(SPI1_BASE_ADDR)
    addi t0, t0, SPI_CTL1_OFFSET

    # load current SPI config into t1
    lw t1, t0, 0

    # enable NSSDRV
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
# TODO: limit attempts to prevent infinite loop?
spi_recv:
    # t1 = stat, t2 = data
    lui t0, %hi(SPI1_BASE_ADDR)
    addi t0, t0, %lo(SPI1_BASE_ADDR)
    addi t1, t0, SPI_STAT_OFFSET
    addi t2, t0, SPI_DATA_OFFSET
spi_recv_wait:
    # wait for TBE to send dummy clock bits
    lw t3, t1, 0  # load stat into t3
    andi t3, t3, 0b10  # isolate TBE bit
    beq t3, zero, spi_recv_wait  # keep looping til dummy bits can be sent
    # send dummy clock bits
    addi t3, zero, 0xff
    sw t2, t3, 0
    # wait for RBNE to confirm data was received
    lw t3, t1, 0  # load stat into t3
    andi t3, t3, 0b01  # isolate RBNE bit
    beq t3, zero, spi_recv_wait  # keep looping until data was received
    # got data! let's read it
    lw a0, t2, 0  # read byte into a0
    addi t4, zero, 0xff  # load 0xff into t4 (MISO defaults to high)
    # if the data is all 1s, it wasn't legit
    beq a0, t4, spi_recv_wait  # keep looping until "real" response arrives
    jalr zero, ra, 0  # return

# Procedure: sd_init
sd_init:
    # for 10 times:
    # assert TBE
    # send 0xff
    jal zero, ra, 0  # return

# Procedure: sd_cmd
# Arg: a0 = cmd (1 byte)
# Arg: a1 = arg (4 bytes)
# Arg: a2 = crc (1 byte)
# Ret: a0 = r1 (1 byte)
# Ret: a1 = r3/r7 (4 bytes)
sd_cmd:
    # send cmd
    # send arg
    # send crc (or determine CRC via simple case)
    # recv r1
    # recv r3/r7 (optionally)
    # send extra 0xff
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
    # write CRC (1 byte): 0x95 (CMD0 -> 0x95, CMD8 -> 0x87, default 0xff (dont care?))
    # total: 0x40 0x00 x00 0x00 x00 0x95
    addi a0, zero, 0xff
    jal ra spi_send
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

    # failure if not 0x01
    addi t0, zero, 0x01
    bne a0 t0 failure

    # write CMD8 (1 byte): 0x40 | 0x08 = 0x48 (0b01 + CMD)
    # write ARG (4 bytes): 0x00 0x00 0x01 0xaa
    # write CRC (1 byte): 0x87 (CMD0 -> 0x95, CMD8 -> 0x87, default 0xff (dont care?))
    # total: 0x40 0x00 x00 0x00 x00 0x95
    addi a0, zero, 0xff
    jal ra spi_send
    addi a0, zero, 0x48
    jal ra spi_send
    addi a0, zero, 0x00
    jal ra spi_send
    addi a0, zero, 0x00
    jal ra spi_send
    addi a0, zero, 0x01
    jal ra spi_send
    addi a0, zero, 0xaa
    jal ra spi_send
    addi a0, zero, 0x87
    jal ra spi_send

    # wait for trans to finish
    jal ra spi_flush

    # read resp from SD Card
    jal ra spi_recv

    # failure if not 0x01
    addi t0, zero, 0x01
    bne a0 t0 failure

    # read 4 more bytes (should be 0x00 0x00 0x01 0xaa)
    jal ra spi_recv
    addi t0, zero, 0x00
    bne a0 t0 failure

    jal ra spi_recv
    addi t0, zero, 0x00
    bne a0 t0 failure

    jal ra spi_recv
    addi t0, zero, 0x01
    bne a0 t0 failure

    jal ra spi_recv
    addi t0, zero, 0xaa
    bne a0 t0 failure

try_init:
    # write CMD55 (1 byte): 0x40 | 0x37 = 0x77 (0b01 + CMD)
    # write ARG (4 bytes): 4 * 0x00
    # write CRC (1 byte): 0x01 (CMD0 -> 0x95, CMD8 -> 0x87, default 0x01)
    # total: 0x77 0x00 x00 0x00 x00 0x01
    addi a0, zero, 0xff
    jal ra spi_send
    addi a0, zero, 0x77
    jal ra spi_send
    addi a0, zero, 0x00
    jal ra spi_send
    addi a0, zero, 0x00
    jal ra spi_send
    addi a0, zero, 0x00
    jal ra spi_send
    addi a0, zero, 0x00
    jal ra spi_send
    addi a0, zero, 0x01
    jal ra spi_send

    # failure if not 0x01
    jal ra spi_recv
    addi t0, zero, 0x01
    bne a0 t0 failure

    # write CMD41 (1 byte): 0x40 | 0x29 = 0x69 (0b01 + CMD)
    # write ARG (4 bytes): 0x40 0x00 0x00 0x00
    # write CRC (1 byte): 0x01 (CMD0 -> 0x95, CMD8 -> 0x87, default 0x01)
    # total: 0x69 0x00 x00 0x00 x00 0x01
    addi a0, zero, 0xff
    jal ra spi_send
    addi a0, zero, 0x69
    jal ra spi_send
    addi a0, zero, 0x40
    jal ra spi_send
    addi a0, zero, 0x00
    jal ra spi_send
    addi a0, zero, 0x00
    jal ra spi_send
    addi a0, zero, 0x00
    jal ra spi_send
    addi a0, zero, 0x01
    jal ra spi_send

    # try again if 0x01
    jal ra spi_recv
    addi t0, zero, 0x01
    beq a0 t0 try_init

    # failed if not 0x01 or 0x00
    bne a0 zero failure

    # resp must be 0x00 at this point (good to go)
    #jal zero success

    # write CMD58 (1 byte): 0x40 | 0x3a = 0x7a (0b01 + CMD)
    # write ARG (4 bytes): 4 * 0x00
    # write CRC (1 byte): 0x01 (CMD0 -> 0x95, CMD8 -> 0x87, default 0x01)
    # total: 0x7a 0x00 x00 0x00 x00 0x01
    addi a0, zero, 0xff
    jal ra spi_send
    addi a0, zero, 0x7a
    jal ra spi_send
    addi a0, zero, 0x00
    jal ra spi_send
    addi a0, zero, 0x00
    jal ra spi_send
    addi a0, zero, 0x00
    jal ra spi_send
    addi a0, zero, 0x00
    jal ra spi_send
    addi a0, zero, 0x01
    jal ra spi_send

    # failure if not 0x00
    jal ra spi_recv
    bne a0 zero failure

    # read 4 byte resp (OCR) into t0
    addi s0 zero 0
    jal ra spi_recv
    slli a0 a0 24
    or s0 s0 a0
    jal ra spi_recv
    slli a0 a0 16
    or s0 s0 a0
    jal zero success  # TODO: bug here, part of OCR is 0xff. need to adjust spi_recv
    jal ra spi_recv
    slli a0 a0 8
    or s0 s0 a0
    jal ra spi_recv
    slli a0 a0 0
    or s0 s0 a0

    # isolate CCS bit
    addi t1 zero 1
    slli t1 t1 30
    andi s0 s0 t1

    # failure if not in block address mode
    beq s0 zero failure

#    # write CMD17 (1 byte): 0x40 | 0x11 = 0x51 (0b01 + CMD)
#    # write ARG (4 bytes): block or addr: 0x00 0x00 0x00 0x00
#    # write CRC (1 byte): 0x01 (CMD0 -> 0x95, CMD8 -> 0x87, default 0x01)
#    # total: 0x51 0x00 x00 0x00 x00 0x01
#    addi a0, zero, 0xff
#    jal ra spi_send
#    addi a0, zero, 0x51
#    jal ra spi_send
#    addi a0, zero, 0x00
#    jal ra spi_send
#    addi a0, zero, 0x00
#    jal ra spi_send
#    addi a0, zero, 0x00
#    jal ra spi_send
#    addi a0, zero, 0x00
#    jal ra spi_send
#    addi a0, zero, 0x01
#    jal ra spi_send
#
#    # failure if not 0x00
#    jal ra spi_recv
#    bne a0 zero failure
#
#    # read data token
#    jal ra spi_recv
#    addi t0 zero 0b11111110
#    bne a0 t0 failure
#
#    # read first byte (should be a backslash)
#    jal ra spi_recv
#    addi t0 zero 0x5a
#    bne a0 t0 failure
#
#    # read 512 bytes
#    addi s0 zero 1
#    slli s0 s0 9
#    addi s0 s0 -1
#recv:
#recv_cond:
#    beq s0 zero recv_done
#recv_body:
#    jal ra spi_recv
#recv_next:
#    addi s0 s0 -1
#    jal zero recv_cond
#recv_done:
#
#    # read CRC (2 bytes)
#    jal ra spi_recv
#    jal ra spi_recv

    # else success!
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
    jal zero done
