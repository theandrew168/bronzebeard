from simpleriscv import asm

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

# taken from schematic
LED_R_GPIO = GPIO_BASE_ADDR_C
LED_R_PIN = 13  # GPIO_CTRL1
LED_G_GPIO = GPIO_BASE_ADDR_A
LED_G_PIN = 1  # GPIO_CTRL0
LED_B_GPIO = GPIO_BASE_ADDR_A
LED_B_PIN = 2  # GPIO_CTRL0


p = asm.Program()
with p.LABEL('rcu_init'):
    # turn on the clock for GPIO ports A and C

    # load RCU base addr into x1
    p.LUI('x1', p.HI(RCU_BASE_ADDR))
    p.ADDI('x1', 'x1', p.LO(RCU_BASE_ADDR))

    p.ADDI('x1', 'x1', RCU_APB2_ENABLE_OFFSET)  # move x1 forward to APB2 enable register
    p.LW('x2', 'x1', 0)  # load current APB2 enable config into x2

    # prepare the GPIO enable bits
    #                     | EDCBA  |
    p.ADDI('x3', 'zero', 0b00010100)

    # enable GPIO clock
    p.OR('x2', 'x2', 'x3')
    p.SW('x1', 'x2', 0)

with p.LABEL('init_gpio_port_c_pin_13'):
    # load GPIO base addr into x1
    p.LUI('x1', p.HI(GPIO_BASE_ADDR_C))
    p.ADDI('x1', 'x1', p.LO(GPIO_BASE_ADDR_C))

    # move x1 forward to control 1 register
    p.ADDI('x1', 'x1', GPIO_CTRL1_OFFSET)

    # TODO: this is destructive
    p.ADDI('x2', 'zero', (GPIO_CTRL_OUT_PUSH_PULL << 2) | GPIO_MODE_OUT_50MHZ)  # load pin settings into x2
    p.SLLI('x2', 'x2', 20)  # shift settings over to correct pin ((PIN - 8) * 4)

    # apply the GPIO config back
    p.SW('x1', 'x2', 0)

with p.LABEL('led_clear_all'):
    # load GPIO base addr C into x1
    p.LUI('x1', p.HI(GPIO_BASE_ADDR_C))
    p.ADDI('x1', 'x1', p.LO(GPIO_BASE_ADDR_C))

    # prepare the GPIO pin 13 enable bit
    p.ADDI('x2', 'zero', 1)  # load 1 into x2
    p.SLLI('x2', 'x2', 13)  # shift the 1 over to pin 13 (pins are 0-indexed)

    p.ADDI('x1', 'x1', GPIO_BIT_OPERATE_OFFSET)  # move x1 to point to the GPIO bit operation address
    p.ADDI('x1', 'x1', 4)  # HACK make this work (now at GPIO_BIT_CLEAR_OFFSET)
    p.SW('x1', 'x2', 0)  # turn on the LED by writing a 1 to the corrent pin's operate bit


with open('longan_nano_led_rainbow.bin', 'wb') as f:
    f.write(p.machine_code)
