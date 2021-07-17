# Turn on the red, green, and blue LEDs on the HiFive1 Rev B

include ../bronzebeard/definitions/FE310-G002.asm

# jump to "main" since programs execute top to bottom
# we do this to enable writing helper funcs at the top
j main

# LED Locations
# (based on schematic)
# --------------------
# Red:   GPIO Pin 22 (active-low)
# Green: GPIO Pin 19 (active-low)
# Blue:  GPIO Pin 21 (active-low)

main:
    li t0, GPIO_BASE_ADDR
    li t1, (1 << 22) | (1 << 21) | (1 << 19)
    sw t1, GPIO_OUTPUT_EN_OFFSET(t0)
