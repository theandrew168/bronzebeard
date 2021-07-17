# definitions related to the SiFive FE310-G002 chip
#
# datasheet: https://sifive.cdn.prismic.io/sifive/4999db8a-432f-45e4-bab2-57007eed0a43_fe310-g002-datasheet-v1p2.pdf 
# manual:    https://sifive.cdn.prismic.io/sifive/654b2b4c-a6dd-4aef-afaf-f7ca89f99583_fe310-g002-manual-v1p0.pdf

# FE310-G002 Manual: Section 9.1
MTIME_BASE_ADDR = 0x0200bff8
MTIME_LO_OFFSET = 0x00
MTIME_HI_OFFSET = 0x04

MTIMECMP_BASE_ADDR = 0x02004000
MTIMECMP_LO_OFFSET = 0x00
MTIMECMP_HO_OFFSET = 0x04

# FE310-G002 Manual: Section 18.2
UART_BASE_ADDR_0 = 0x10013000
UART_BASE_ADDR_1 = 0x10023000

# FE310-G002 Manual: Section 18.3
UART_TXDATA_OFFSET = 0x00
UART_RXDATA_OFFSET = 0x04
UART_TXCTRL_OFFSET = 0x08
UART_RXCTRL_OFFSET = 0x0c
UART_IE_OFFSET     = 0x10
UART_IP_OFFSET     = 0x14
UART_DIV_OFFSET    = 0x18
