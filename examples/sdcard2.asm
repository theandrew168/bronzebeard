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
    addi a0, a0, RCU_APB2EN_OFFSET
    # enable GPIO ports A, B, and C
    # enable AFIO
    addi t0, zero, 0b00011101
    sw a0, t0, 0

    # advance to APB1EN
    addi a0, a0, 4
    # enable SPI1
    addi t0, zero, 1
    slli t0, t0, 14
    sw a0, t0, 0

    # return
    jalr zero, ra, 0

# Func: gpio_init
# Arg: a0 = GPIO port base addr
# Arg: a1 = GPIO pin number
# Arg: a2 = GPIO config
gpio_init:
    # advance to CTL0
    addi a0, a0, GPIO_CTL0_OFFSET
    # if pin number is less than 8, CTL0 is correct
    addi t0, zero, 8
    blt a1, t0, gpio_init_config
    # else we need CTL1 and then subtract 8 from the pin number
    addi a0, a0, 4
    addi a1, a1, -8
gpio_init_config:
    # multiply pin number by 4 to get shift amount
    addi t0, zero, 4
    mul a1, a1, t0

    # load current config
    lw t0, a0, 0
    # clear existing pin config
    addi t1, zero, 0b1111
    sll t1, t1, a1
    xori t1, t1, -1
    and t0, t0, t1
    # set new pin config
    sll a2, a2, a1
    or t0, t0, a2
    # store updated config
    sw a0, t0, 0

    # return
    jalr zero, ra, 0

# Func: gpio_on
# Arg: a0 = GPIO port base addr
# Arg: a1 = GPIO pin number
gpio_on:
    # advance to BOP
    addi a0, a0, GPIO_BOP_OFFSET
    # prepare BOP bit
    addi t0, zero, 1
    sll t0, t0, a1
    # turn the pin on
    sw a0, t0, 0

    # return
    jalr zero, ra, 0

# Func: gpio_off
# Arg: a0 = GPIO port base addr
# Arg: a1 = GPIO pin number
gpio_off:
    # advance to BOP
    addi a0, a0, GPIO_BOP_OFFSET
    # prepare BOP bit
    addi t0, zero, 1
    sll t0, t0, a1
    slli t0, t0, 16
    # turn the pin off
    sw a0, t0, 0

    # return
    jalr zero, ra, 0

# Func: spi_init
# Arg: a0 = SPI base addr
# Arg: a1 = SPI clock div
spi_init:
    # advance to CTL0
    addi a0, a0, SPI_CTL0_OFFSET

    # load current config
    lw t0, a0, 0
    # enable SPI
    addi t1, zero, 1
    slli t1, t1, 6
    or t0, t0, t1
    # set SPI clock divider
    slli a1, a1, 3
    or t0, t0, a1
    # enable master mode
    addi t1, zero, 1
    slli t1, t1, 2
    or t0, t0, t1
    # store updated config
    sw a0, t0, 0

    # advance to CTL1
    addi a0, a0, 4
    # load current config
    lw t0, a0, 0
    # enable NSSDRV
    addi t1, zero, 1
    slli t1, t1, 2
    or t0, t0, t1
    # store updated config
    sw a0, t0, 0

    # return
    jalr zero, ra, 0

# Func: sd_init
# Arg: a0 = SPI base addr
sd_init:
    addi t0, a0, SPI_STAT_OFFSET  # t0 = STAT addr
    addi t1, a0, SPI_DATA_OFFSET  # t1 = DATA addr
    # send 80 (>= 74) clock pulses to "boot" the SD card
    addi t2, zero, 10
sd_init_cond:
    # done once counter reaches zero
    beq t2, zero, sd_init_done
sd_init_body:
    # wait for TBE
    lw t3, t0, 0  # load SPI status
    andi t3, t3, 0x02  # isolate TBE bit
    beq t3, zero, sd_init_body
    # send 0xff to pulse SD card clock
    addi t3, zero, 0xff
    sw t1, t3, 0
sd_init_next:
    # decrement counter and check cond again
    addi t2, t2, -1
    jal zero, sd_init_cond
sd_init_done:
    # return
    jalr zero, ra, 0

# Func: sd_cmd
# Arg: a0 = SPI base addr
# Arg: a1 = SD cmd (1 byte)
# Arg: a2 = SD arg (4 bytes)
# Arg: a3 = SD crc (1 byte)
# Ret: a0 = SD r1 (1 byte)
# Ret: a1 = SD r3/r7 (4 bytes)
sd_cmd:
    addi t0, a0, SPI_STAT_OFFSET  # t0 = STAT addr
    addi t1, a0, SPI_DATA_OFFSET  # t1 = DATA addr

sd_cmd_send_wait:
    # pulse clock til 0xff is recv'd and SD card is "ready"
    # wait for TBE
    lw t2, t0, 0  # load SPI status
    andi t2, t2, 0x02  # isolate TBE bit
    beq t2, zero, sd_cmd_send_wait
    # send 0xff (dummy bits) to pulse clock
    addi t2, zero, 0xff
    sw t1, t2, zero
    # wait for RBNE
    lw t2, t0, 0  # load SPI status
    andi t2, t2, 0x01  # isolate RBNE bit
    beq t2, zero, sd_cmd_send_wait
    # read a byte and loop again if not 0xff
    lw t2, t1, 0
    addi t3, zero, 0xff
    bne t2, t3, sd_cmd_send_wait

sd_cmd_send:
    # ready to send!
    # have to repeat the TBE wait because funcs can't nest
sd_cmd_send_cmd:
    # wait for TBE
    lw t2, t0, 0  # load SPI status
    andi t2, t2, 0x02  # isolate TBE bit
    beq t2, zero, sd_cmd_send_cmd
    # send cmd
    ori t2, a1, 0x40
    sw t1, t2, 0
sd_cmd_send_arg3:
    # wait for TBE
    lw t2, t0, 0  # load SPI status
    andi t2, t2, 0x02  # isolate TBE bit
    beq t2, zero, sd_cmd_send_arg3
    # send arg[31..24]
    srli t2, a2, 24
    andi t2, t2, 0xff
    sw t1, t2, 0
sd_cmd_send_arg2:
    # wait for TBE
    lw t2, t0, 0  # load SPI status
    andi t2, t2, 0x02  # isolate TBE bit
    beq t2, zero, sd_cmd_send_arg2
    # send arg[23..16]
    srli t2, a2, 16
    andi t2, t2, 0xff
    sw t1, t2, 0
sd_cmd_send_arg1:
    # wait for TBE
    lw t2, t0, 0  # load SPI status
    andi t2, t2, 0x02  # isolate TBE bit
    beq t2, zero, sd_cmd_send_arg1
    # send arg[15..8]
    srli t2, a2, 8
    andi t2, t2, 0xff
    sw t1, t2, 0
sd_cmd_send_arg0:
    # wait for TBE
    lw t2, t0, 0  # load SPI status
    andi t2, t2, 0x02  # isolate TBE bit
    beq t2, zero, sd_cmd_send_arg0
    # send arg[7..0]
    srli t2, a2, 0
    andi t2, t2, 0xff
    sw t1, t2, 0
sd_cmd_send_crc:
    # wait for TBE
    lw t2, t0, 0  # load SPI status
    andi t2, t2, 0x02  # isolate TBE bit
    beq t2, zero, sd_cmd_send_crc
    # send crc
    ori a3, a3, 1
    sw t1, a3, 0

sd_cmd_recv_wait:
    # wait for TBE
    lw t2, t0, 0  # load SPI status
    andi t2, t2, 0x02  # isolate TBE bit
    beq t2, zero, sd_cmd_recv_wait
    # send 0xff (dummy bits) to pulse clock
    addi t2, zero, 0xff
    sw t1, t2, zero
    # wait for RBNE
    lw t2, t0, 0  # load SPI status
    andi t2, t2, 0x01  # isolate RBNE bit
    beq t2, zero, sd_cmd_recv_wait
    # read a byte and loop again if 0xff
    lw t2, t1, 0
    addi t3, zero, 0xff
    beq t2, t3, sd_cmd_recv_wait

sd_cmd_recv:
    # recv r1 (will already be in t2)
    addi a0, t2, 0
    # check if CMD has an r3/r7 response (CMD8 or CMD58)
    addi t2, zero, 8
    beq a1, t2, sd_cmd_recv_r3r7
    addi t2, zero, 58
    beq a1, t2, sd_cmd_recv_r3r7
    # else done
    jal zero, sd_cmd_done
sd_cmd_recv_r3r7:
    # init a1 (resp) to zero
    addi a1, zero, 0
sd_cmd_recv_resp3:
    # wait for TBE
    lw t2, t0, 0  # load SPI status
    andi t2, t2, 0x02  # isolate TBE bit
    beq t2, zero, sd_cmd_recv_resp3
    # send 0xff (dummy bits) to pulse clock
    addi t2, zero, 0xff
    sw t1, t2, zero
    # wait for RBNE
    lw t2, t0, 0  # load SPI status
    andi t2, t2, 0x01  # isolate RBNE bit
    beq t2, zero, sd_cmd_recv_resp3
    # read a byte
    lw t2, t1, 0
    andi t2, t2, 0xff
    slli t2, t2, 24
    or a1, a1, t2
sd_cmd_recv_resp2:
    # wait for TBE
    lw t2, t0, 0  # load SPI status
    andi t2, t2, 0x02  # isolate TBE bit
    beq t2, zero, sd_cmd_recv_resp2
    # send 0xff (dummy bits) to pulse clock
    addi t2, zero, 0xff
    sw t1, t2, zero
    # wait for RBNE
    lw t2, t0, 0  # load SPI status
    andi t2, t2, 0x01  # isolate RBNE bit
    beq t2, zero, sd_cmd_recv_resp2
    # read a byte
    lw t2, t1, 0
    andi t2, t2, 0xff
    slli t2, t2, 16
    or a1, a1, t2
sd_cmd_recv_resp1:
    # wait for TBE
    lw t2, t0, 0  # load SPI status
    andi t2, t2, 0x02  # isolate TBE bit
    beq t2, zero, sd_cmd_recv_resp1
    # send 0xff (dummy bits) to pulse clock
    addi t2, zero, 0xff
    sw t1, t2, zero
    # wait for RBNE
    lw t2, t0, 0  # load SPI status
    andi t2, t2, 0x01  # isolate RBNE bit
    beq t2, zero, sd_cmd_recv_resp1
    # read a byte
    lw t2, t1, 0
    andi t2, t2, 0xff
    slli t2, t2, 8
    or a1, a1, t2
sd_cmd_recv_resp0:
    # wait for TBE
    lw t2, t0, 0  # load SPI status
    andi t2, t2, 0x02  # isolate TBE bit
    beq t2, zero, sd_cmd_recv_resp0
    # send 0xff (dummy bits) to pulse clock
    addi t2, zero, 0xff
    sw t1, t2, zero
    # wait for RBNE
    lw t2, t0, 0  # load SPI status
    andi t2, t2, 0x01  # isolate RBNE bit
    beq t2, zero, sd_cmd_recv_resp0
    # read a byte
    lw t2, t1, 0
    andi t2, t2, 0xff
    slli t2, t2, 0
    or a1, a1, t2
sd_cmd_done:
    # return
    jalr zero, ra, 0

main:
    # init RCU for GPIO[ABC], AFIO, and SPI1
    lui a0, %hi(RCU_BASE_ADDR)
    addi a0, a0, %lo(RCU_BASE_ADDR)
    jal ra, rcu_init

    # init SPI1_CS_TF (B12)
    lui a0, %hi(GPIOB_BASE_ADDR)
    addi a0, a0, %lo(GPIOB_BASE_ADDR)
    addi a1, zero, 12
    addi a2, zero, GPIO_CTL_OUT_AF_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ
    jal ra, gpio_init

    # init SPI1_SCLK (B13)
    lui a0, %hi(GPIOB_BASE_ADDR)
    addi a0, a0, %lo(GPIOB_BASE_ADDR)
    addi a1, zero, 13
    addi a2, zero, GPIO_CTL_OUT_AF_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ
    jal ra, gpio_init

    # init SPI1_MISO (B14)
    lui a0, %hi(GPIOB_BASE_ADDR)
    addi a0, a0, %lo(GPIOB_BASE_ADDR)
    addi a1, zero, 14
    addi a2, zero, GPIO_CTL_IN_FLOATING << 2 | 0
    jal ra, gpio_init

    # init SPI1_MOSI (B15)
    lui a0, %hi(GPIOB_BASE_ADDR)
    addi a0, a0, %lo(GPIOB_BASE_ADDR)
    addi a1, zero, 15
    addi a2, zero, GPIO_CTL_OUT_AF_PUSH_PULL << 2 | GPIO_MODE_OUT_50MHZ
    jal ra, gpio_init

    # init SPI1 for SD Card
    lui a0, %hi(SPI1_BASE_ADDR)
    addi a0, a0, %lo(SPI1_BASE_ADDR)
    addi a1, zero, 0b101  # 8MHz / 64 = 125kHz
    jal ra, spi_init

    # init SD card
    lui a0, %hi(SPI1_BASE_ADDR)
    addi a0, a0, %lo(SPI1_BASE_ADDR)
    jal ra, sd_init

    # send CMD0 (software reset)
    lui a0, %hi(SPI1_BASE_ADDR)
    addi a0, a0, %lo(SPI1_BASE_ADDR)
    addi a1, zero, 0
    addi a2, zero, 0
    addi a3, zero, 0x95
    jal ra, sd_cmd

    # failure if r1 not 0x01
    addi t0, zero, 0x01
    bne a0, t0, failure

    # send CMD8 (check voltage range)
    lui a0, %hi(SPI1_BASE_ADDR)
    addi a0, a0, %lo(SPI1_BASE_ADDR)
    addi a1, zero, 8
    addi a2, zero, 0x000001aa
    addi a3, zero, 0x87
    jal ra, sd_cmd

    # failure if r1 not 0x01
    addi t0, zero, 0x01
    bne a0, t0, failure

    # failure if r3/r7 not 0x000001aa
    addi t0, zero, 0x000001aa
    bne a1, t0, failure

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

# infinite idle loop
done:
    jal zero done
