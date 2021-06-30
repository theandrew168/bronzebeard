# Read blocks from the SDCard on the Longan Nano
#
# References:
# https://github.com/riscv-mcu/GD32VF103_Firmware_Library/blob/master/Examples/SPI/SPI_master_slave_fullduplex_polling/main.c
# http://elm-chan.org/docs/mmc/mmc_e.html
# https://github.com/arduino-libraries/SD/blob/master/src/utility/Sd2Card.cpp
# http://www.dejazzer.com/ee379/lecture_notes/lec12_sd_card.pdf
# https://github.com/esmil/gd32vf103inator/blob/master/examples/LonganNano/sdcard.c
# https://github.com/sipeed/Longan_GD32VF_examples/blob/master/gd32v_lcd/src/fatfs/tf_card.c

# RCU Config
# ----------
# Enable GPIO ports A, B, and C
# Enable AFIO

# GPIO Config
# -----------
# LED_RED    - C13 (OUT_PUSH_PULL, 50MHz)
# LED_GREEN  - A1  (OUT_PUSH_PULL, 50MHz)
# LED_BLUE   - A2  (OUT_PUSH_PULL, 50MHz)
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
#   check for 0x01 : 0x00 0x00 0x01 0xaa
# CMD55 (arg=0, setup app cmd)
#   check for 0x01
# CMD41 (arg=0x40000000, start init w/ host capacity support (HCS))
#   if 0x01, retry @ CMD55
#   if 0x00, success
# CMD58 (arg=0, read operation conditions register (OCR))
#   check card capacity status (CCS) bit (need this fact later!)
#   if bit30 == 1, ready to read (card is SDHC/SDXC w/ block of 512)
#   if bit30 == 0,
#       CMD16 (arg=0x00000200, set block size to 512 bytes), check for 0x00
# CMD17 (arg=0, read first block of data)
#   check for 0x00
# READ_BLOCK
#   wait til resp isn't 0xff
#   check data token (should be 0xfe)
#   read 512 bytes of data
#   read 2 byte CRC

ROM_BASE_ADDR = 0x08000000
RAM_BASE_ADDR = 0x20000000

RCU_BASE_ADDR = 0x40021000  # GD32VF103 Manual: Section 5.3
RCU_APB2EN_OFFSET = 0x18  # GD32VF103 Manual: Section 5.3.7 (GPIO[ABC], AFIO)
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

jal zero main

# Func: rcu_init
# Arg: a0 = RCU base addr
rcu_init:
    # advance to APB2EN
    addi t0, a0, RCU_APB2EN_OFFSET
    # enable GPIO ports A, B, and C
    # enable AFIO
    addi t1, zero, 0b00011101
    sw t0, t1, 0

    # advance to APB1EN
    addi t0, t0, 4
    # enable SPI1
    addi t1, zero, 1
    slli t1, t1, 14
    sw t0, t1, 0

    ret

# Func: gpio_init
# Arg: a0 = GPIO port base addr
# Arg: a1 = GPIO pin number
# Arg: a2 = GPIO config
gpio_init:
    # advance to CTL0
    addi t0, a0, GPIO_CTL0_OFFSET
    # if pin number is less than 8, CTL0 is correct
    addi t1, zero, 8
    blt a1, t1, gpio_init_config
    # else we need CTL1 and then subtract 8 from the pin number
    addi t0, t0, 4
    addi a1, a1, -8
gpio_init_config:
    # multiply pin number by 4 to get shift amount
    slli a1, a1, 2

    # load current config
    lw t1, t0, 0
    # clear existing pin config
    addi t2, zero, 0b1111
    sll t2, t2, a1
    xori t2, t2, -1
    and t1, t1, t2
    # set new pin config
    sll a2, a2, a1
    or t1, t1, a2
    # store updated config
    sw t0, t1, 0

    # return
    jalr zero, ra, 0

# Func: gpio_on
# Arg: a0 = GPIO port base addr
# Arg: a1 = GPIO pin number
gpio_on:
    # advance to BOP
    addi t0, a0, GPIO_BOP_OFFSET
    # prepare BOP bit
    addi t1, zero, 1
    sll t1, t1, a1
    # turn the pin on
    sw t0, t1, 0

    # return
    jalr zero, ra, 0

# Func: gpio_off
# Arg: a0 = GPIO port base addr
# Arg: a1 = GPIO pin number
gpio_off:
    # advance to BOP
    addi t0, a0, GPIO_BOP_OFFSET
    # prepare BOP bit
    addi t1, zero, 1
    sll t1, t1, a1
    slli t1, t1, 16  # extra 16 bits to "clear" section
    # turn the pin off
    sw t0, t1, 0

    # return
    jalr zero, ra, 0

# Func: spi_init
# Arg: a0 = SPI base addr
# Arg: a1 = SPI clock div
spi_init:
    # advance to CTL0
    addi t0, a0, SPI_CTL0_OFFSET

    # load current config
    lw t1, t0, 0
    # enable SPI
    addi t2, zero, 1
    slli t2, t2, 6
    or t1, t1, t2
    # set SPI clock divider
    slli a1, a1, 3
    or t1, t1, a1
    # enable master mode
    addi t2, zero, 1
    slli t2, t2, 2
    or t1, t1, t2
    # store updated config
    sw t0, t1, 0

    # advance to CTL1
    addi t0, t0, 4
    # load current config
    lw t1, t0, 0
    # enable NSSDRV
    addi t2, zero, 1
    slli t2, t2, 2
    or t1, t1, t2
    # store updated config
    sw t0, t1, 0

    # return
    jalr zero, ra, 0

# Func: spi_swap
# Regs: t0-t2 (called by sd_init, sd_cmd, sd_read)
# Arg: a0 = SPI base addr
# Arg: a1 = byte to send
# Ret: a1 = byte received
spi_swap:
    addi t0, a0, SPI_STAT_OFFSET  # t0 = STAT addr
    addi t1, a0, SPI_DATA_OFFSET  # t1 = DATA addr
sd_swap_wait_tbe:
    # wait for TBE
    lw t2, t0, 0  # load SPI status
    andi t2, t2, 0x02  # isolate TBE bit
    beq t2, zero, sd_swap_wait_tbe
    # send byte
    sw t1, a1, 0
sd_swap_wait_rbne:
    # wait for RBNE
    lw t2, t0, 0  # load SPI status
    andi t2, t2, 0x01  # isolate RBNE bit
    beq t2, zero, sd_swap_wait_rbne
    # read byte
    lw a1, t1, 0
    # return
    jalr zero, ra, 0

# Func: sd_init
# Regs: ~t0-t2 (calls spi_swap)
# Arg: a0 = SPI base addr
sd_init:
    # save ra into sp
    addi sp, ra, 0
    # send 80 (>= 74) clock pulses to "boot" the SD card
    addi t3, zero, 10
sd_init_cond:
    # done once counter reaches zero
    beq t3, zero, sd_init_done
sd_init_body:
    # send 0xff to pulse SD card clock
    addi a1, zero, 0xff
    jal ra, spi_swap
sd_init_next:
    # decrement counter and check cond again
    addi t3, t3, -1
    jal zero, sd_init_cond
sd_init_done:
    # restore ra and return
    addi ra, sp, 0
    jalr zero, ra, 0

# Func: sd_read
# Regs: ~t0-t2 (calls spi_swap)
# Arg: a0 = SPI base addr
# Arg: a2 = dest addr
# Arg: a3 = count
sd_read:
    # save ra into sp
    addi sp, ra, 0
sd_read_wait:
    # loop til non 0xff is received
    addi t3, zero, 0xff
    addi a1, t3, 0
    jal ra, spi_swap
    beq a1, t3, sd_read_wait
sd_read_check:
    # check for valid data token
    addi t3, zero, 0xfe
    bne a1, t3, sd_read_done
sd_read_cond:
    beq a3, zero, sd_read_crc
sd_read_body:
    # read next byte
    addi a1, zero, 0xff
    jal ra, spi_swap
    # write byte to dest addr and inc ptr
    sb a2, a1, 0
    addi a2, a2, 1
sd_read_next:
    # dec counter
    addi a3, a3, -1
    jal zero, sd_read_cond
sd_read_crc:
    # discard CRC from response (2 bytes)
    addi a1, zero, 0xff
    jal ra, spi_swap
    addi a1, zero, 0xff
    jal ra, spi_swap
sd_read_done:
    # restore ra and return
    addi ra, sp, 0
    jalr zero, ra, 0

# Func: sd_cmd
# Regs: ~t0-t2 (calls spi_swap)
# Arg: a0 = SPI base addr
# Arg: a2 = SD cmd (1 byte)
# Arg: a3 = SD arg (4 bytes)
# Arg: a4 = SD crc (1 byte)
# Ret: a1 = SD r1 (1 byte)
# Ret: a2 = SD r3/r7 (4 bytes)
sd_cmd:
    # save ra into sp
    addi sp, ra, 0
sd_cmd_wait:
    # pulse clock til 0xff is recv'd and SD card is "ready"
    addi t3, zero, 0xff
    addi a1, t3, 0
    jal ra, spi_swap
    bne a1, t3, sd_cmd_wait

sd_cmd_send:
    # send cmd (OR w/ 0x40 first)
    ori a1, a2, 0x40
    jal ra, spi_swap

    # send arg[31..24]
    srli a1, a3, 24
    andi a1, a1, 0xff
    jal ra, spi_swap

    # send arg[23..16]
    srli a1, a3, 16
    andi a1, a1, 0xff
    jal ra, spi_swap

    # send arg[15..8]
    srli a1, a3, 8
    andi a1, a1, 0xff
    jal ra, spi_swap

    # send arg[7..0]
    srli a1, a3, 0
    andi a1, a1, 0xff
    jal ra, spi_swap

    # send crc (OR w/ 0x01 first)
    ori a1, a4, 0x01
    jal ra, spi_swap

sd_cmd_recv:
    # loop til non 0xff is received
    addi t3, zero, 0xff
    addi a1, t3, 0
    jal ra, spi_swap
    beq a1, t3, sd_cmd_recv

    # recv r1 (will already be in a1, save into a5 for now)
    addi a5, a1, 0
    # check if CMD has an r3/r7 response (CMD8 or CMD58)
    addi t3, zero, 8
    beq a2, t3, sd_cmd_recv_r3r7
    addi t3, zero, 58
    beq a2, t3, sd_cmd_recv_r3r7
    # else done
    addi a2, zero, 0  # set r3/r7 resp to zero
    jal zero, sd_cmd_done
sd_cmd_recv_r3r7:
    # init a2 (r3/r7 resp) to zero
    addi a2, zero, 0

    # read resp[31..24]
    addi a1, zero, 0xff
    jal ra, spi_swap
    andi a1, a1, 0xff
    slli a1, a1, 24
    or a2, a2, a1

    # read resp[23..16]
    addi a1, zero, 0xff
    jal ra, spi_swap
    andi a1, a1, 0xff
    slli a1, a1, 16
    or a2, a2, a1

    # read resp[15..8]
    addi a1, zero, 0xff
    jal ra, spi_swap
    andi a1, a1, 0xff
    slli a1, a1, 8
    or a2, a2, a1

    # read resp[7..0]
    addi a1, zero, 0xff
    jal ra, spi_swap
    andi a1, a1, 0xff
    slli a1, a1, 0
    or a2, a2, a1

sd_cmd_done:
    # put r1 back into a1 (from a5)
    addi a1, a5, 0
    # restore ra and return
    addi ra, sp, 0
    jalr zero, ra, 0



main:
    # setup RCU base addr
    # init RCU for GPIO[ABC], AFIO, and SPI1
    lui a0, %hi(RCU_BASE_ADDR)
    addi a0, a0, %lo(RCU_BASE_ADDR)
    call rcu_init

    # setup GPIOB base addr
    lui a0, %hi(GPIOB_BASE_ADDR)
    addi a0, a0, %lo(GPIOB_BASE_ADDR)

    # init SPI1_CS_TF (B12)
    addi a1, zero, 12
    addi a2, zero, GPIO_CTL_OUT_AF_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ
    jal ra, gpio_init

    # init SPI1_SCLK (B13)
    addi a1, zero, 13
    addi a2, zero, GPIO_CTL_OUT_AF_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ
    jal ra, gpio_init

    # init SPI1_MISO (B14)
    addi a1, zero, 14
    addi a2, zero, GPIO_CTL_IN_FLOATING << 2 | 0
    jal ra, gpio_init

    # init SPI1_MOSI (B15)
    addi a1, zero, 15
    addi a2, zero, GPIO_CTL_OUT_AF_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ
    jal ra, gpio_init

    # setup SPI1 base addr
    lui a0, %hi(SPI1_BASE_ADDR)
    addi a0, a0, %lo(SPI1_BASE_ADDR)

    # init SPI1
    addi a1, zero, 0b101  # 8MHz / 64 = 125kHz
    jal ra, spi_init

    # init SD card
    jal ra, sd_init

    # send CMD0 (software reset)
    addi a2, zero, 0
    addi a3, zero, 0
    addi a4, zero, 0x95
    jal ra, sd_cmd

    # failure if r1 != 0x01
    addi t0, zero, 0x01
    bne a1, t0, failure

    # send CMD8 (check voltage range)
    addi a2, zero, 8
    addi a3, zero, 0x000001aa
    addi a4, zero, 0x87
    jal ra, sd_cmd

    # failure if r1 != 0x01
    addi t0, zero, 0x01
    bne a1, t0, failure

    # failure if r3/r7 != 0x000001aa
    addi t0, zero, 0x000001aa
    bne a2, t0, failure

init_loop:
    # send CMD55 (app cmd)
    addi a2, zero, 55
    addi a3, zero, 0
    addi a4, zero, 0x01
    jal ra, sd_cmd

    # failure if r1 != 0x01
    addi t0, zero, 0x01
    bne a1, t0, failure

    # send CMD41 (start init w/ host capacity support (HCS) bit set)
    addi a2, zero, 41
    addi a3, zero, 1
    slli a3, a3, 30
    addi a4, zero, 0x01
    jal ra, sd_cmd

    # try again if r1 == 0x01
    addi t0, zero, 0x01
    beq a1, t0, init_loop

    # failure if r1 not 0x00 or 0x01
    bne a1, zero, failure

init_done:
    # send CMD58 (read operation conditions register (OCR))
    addi a2, zero, 58
    addi a3, zero, 0
    addi a4, zero, 0x01
    jal ra, sd_cmd

    # failure if r1 != 0x00
    bne a1, zero, failure

    # isolate card capacity status (CCS) bit
    addi t0, zero, 1
    slli t0, t0, 30
    and a2, a2, t0

    # success if block address mode w/ 512 byte blocks
    bne a2, zero, read_block

    # else set block size to 512 bytes
    # send CMD16 (set block size)
    addi a2, zero, 16
    addi a3, zero, 0x00000200
    addi a4, zero, 0x01
    jal ra, sd_cmd

    # error if r1 != 0x00
    bne a1, zero, failure

read_block:
    # send CMD17 (read single block)
    addi a2, zero, 17
    addi a3, zero, 0x00000000
    addi a4, zero, 0x01
    jal ra, sd_cmd

    # failure if r1 != 0x00
    bne a1, zero, failure

    # read 512 bytes
    lui a2, %hi(RAM_BASE_ADDR)
    addi a2, a2, %lo(RAM_BASE_ADDR)
    addi a3, zero, 512
    jal ra, sd_read

    # check data in RAM, should be Forth code!
    lui t0, %hi(RAM_BASE_ADDR)
    addi t0, t0, %lo(RAM_BASE_ADDR)

    # first char should be a backslash
    addi t2, zero, 92
    lb t1, t0, 0
    bne t1, t2, failure

    # second char should be a space
    addi t2, zero, 32
    lb t1, t0, 1
    bne t1, t2, failure

    # third char should be a 'd'
    addi t2, zero, 100
    lb t1, t0, 2
    bne t1, t2, failure

    jal zero, success

failure:
    # init red LED (defaults to on)
    lui a0, %hi(GPIOC_BASE_ADDR)
    addi a0, a0, %lo(GPIOC_BASE_ADDR)
    addi a1, zero, 13
    addi a2, zero, GPIO_CTL_OUT_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ
    jal ra, gpio_init
    jal zero, done

success:
    # init green LED (defaults to on)
    lui a0, %hi(GPIOA_BASE_ADDR)
    addi a0, a0, %lo(GPIOA_BASE_ADDR)
    addi a1, zero, 1
    addi a2, zero, GPIO_CTL_OUT_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ
    jal ra, gpio_init
    jal zero, done

other:
    # init blue LED (defaults to on)
    lui a0, %hi(GPIOA_BASE_ADDR)
    addi a0, a0, %lo(GPIOA_BASE_ADDR)
    addi a1, zero, 2
    addi a2, zero, GPIO_CTL_OUT_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ
    jal ra, gpio_init
    jal zero, done

# infinite idle loop
done:
    jal zero done
