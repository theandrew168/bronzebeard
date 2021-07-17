# definitions related to the ST7735S display
#
# datasheet: https://www.crystalfontz.com/controllers/Sitronix/ST7735S/320/
# reference: https://github.com/adafruit/Adafruit-ST7735-Library

# not sure about this one
#DP_CLOCKDIV_WRITE = (2 << SPI_CTL0_PSC_POS)

# PORT B
DP_CS_BIT  = 2
DP_RST_BIT = 1
DP_DC_BIT  = 0

DP_CS  = (1 << DP_CS_BIT)
DP_RST = (1 << DP_RST_BIT)
DP_DC  = (1 << DP_DC_BIT)

# PORT A
DP_SDA_BIT = 7
DP_SCL_BIT = 5

DP_SDA = (1 << DP_SDA_BIT)
DP_SCL = (1 << DP_SCL_BIT)
