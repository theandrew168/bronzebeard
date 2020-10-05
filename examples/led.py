from bronzebeard import asm

# GPIO info taken from:
# GD32VF103 User Manual, Section 7 (GPIO and AFIO)
#
# Each pin gets 2 bits of mode data and 2 bits of control data. The mode options
# are noted by the GPIO_MODE_* values and the control options are noted by the 
# GPIO_CTRL_IN_* and GPIO_CTRL_OUT_* values. Note that there are two sets of control
# options (IN and OUT) which correspond to the mode that is currently set. If mode is
# set to GPIO_MODE_IN, then the GPIO_CTRL_IN_* control values will be used. If mode is
# set to any of the GPIO_MODE_OUT_* values, then the GPIO_CTRL_OUT_* control values
# will be used.
#
#
# GPIO Control Register 0 (GPIO_BASE_ADDR + 0x00)
#
#   31      30   29      28   27 26   25 24   23 22   21 20   19 18   17 16
# | CTRL7[1:0] | MODE7[1:0] | CTRL6 | MODE6 | CTRL5 | MODE5 | CTRL4 | MODE4 |
#
#   15      14   13      12   11 10   9   8   7   6   5   4   3   2   1   0
# | CTRL3[1:0] | MODE3[1:0] | CTRL2 | MODE2 | CTRL1 | MODE1 | CTRL0 | MODE0 |
#
#
# GPIO Control Register 1 (GPIO_BASE_ADDR + 0x04)
#
#   31       30   29       28   27  26   25  24   23  22   21  20   19  18   17  16
# | CTRL15[1:0] | MODE15[1:0] | CTRL14 | MODE14 | CTRL13 | MODE13 | CTRL12 | MODE12 |
#
#   15       14   13       12   11  10   9    8   7   6   5   4   3   2   1   0
# | CTRL11[1:0] | MODE11[1:0] | CTRL10 | MODE10 | CTRL9 | MODE9 | CTRL8 | MODE8 |

GPIO_BASE_ADDR_A = 0x40010800
GPIO_BASE_ADDR_B = 0x40010c00
GPIO_BASE_ADDR_C = 0x40011000
GPIO_BASE_ADDR_D = 0x40011400
GPIO_BASE_ADDR_E = 0x40011800

# these register offsets are relative to the above base addresses
GPIO_CTRL0_OFFSET = 0x00
GPIO_CTRL1_OFFSET = 0x04
GPIO_IN_STATUS_OFFSET = 0x08
GPIO_OUT_CTRL_OFFSET = 0x0c
GPIO_BIT_OPERATE_OFFSET = 0x10
GPIO_BIT_CLEAR_OFFSET = 0x14
GPIO_LOCK_OFFSET = 0x18

GPIO_MODE_IN = 0b00
GPIO_MODE_OUT_10MHZ = 0b01
GPIO_MODE_OUT_2MHZ = 0b10
GPIO_MODE_OUT_50MHZ = 0b11

GPIO_CTRL_IN_ANALOG = 0b00
GPIO_CTRL_IN_FLOATING = 0b01
GPIO_CTRL_IN_PULL = 0b10
GPIO_CTRL_IN_RESERVED = 0b11

GPIO_CTRL_OUT_PUSH_PULL = 0b00
GPIO_CTRL_OUT_OPEN_DRAIN = 0b01
GPIO_CTRL_OUT_ALT_PUSH_PULL = 0b10
GPIO_CTRL_OUT_ALT_OPEN_DRAIN = 0b11

# LED location and GPIO config taken from:
# https://github.com/sipeed/platform-gd32v/blob/master/examples/longan-nano-blink/src/main.c
#
# LED: GPIO C, PIN 13
#
# GPIO Config:
#   MODE = GPIO_MODE_OUT_50MHZ
#   CTRL = GPIO_CTRL_OUT_PUSH_PULL

GPIO_MODE_MASK = 0b0011
GPIO_CTRL_MASK = 0b1100

# Reset and clock unit info taken from:
# GD32VF103 User Manual, Section 5 (RCU)

RCU_BASE_ADDR = 0x40021000

RCU_CTRL_OFFSET = 0x00
RCU_CLK_CONFIG0_OFFSET = 0x04
RCU_CLK_INTERRUPT_OFFSET = 0x08
RCU_APB2_RESET_OFFSET = 0x0c
RCU_APB1_RESET_OFFSET = 0x10
RCU_AHB_ENABLE_OFFSET = 0x14
RCU_APB2_ENABLE_OFFSET = 0x18
RCU_APB1_ENABLE_OFFSET = 0x1c
RCU_BACKUP_DOMAIN_CTRL_OFFSET = 0x20
RCU_RESET_SRC_CLK_OFFSET = 0x24
RCU_AHB_RESET_OFFSET = 0x28
RCU_CLK_CONFIG1_OFFSET = 0x2c
RCU_DEEP_SLEEP_VOLTAGE_OFFSET = 0x34
