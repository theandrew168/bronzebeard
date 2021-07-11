# constants related to the SiFive FE310-G002 chip
#
# datasheet: https://sifive.cdn.prismic.io/sifive/4999db8a-432f-45e4-bab2-57007eed0a43_fe310-g002-datasheet-v1p2.pdf 
# manual: https://sifive.cdn.prismic.io/sifive/654b2b4c-a6dd-4aef-afaf-f7ca89f99583_fe310-g002-manual-v1p0.pdf

# NOTE: The first 64KB of Flash is occupied by the bootloader
# (which jumps to 0x20010000 at the end). That leaves
# (4MB - 64KB = 4032KB) starting at 0x20010000 for programs.

# 4MB @ 0x20000000 (actually ~4MB @ 0x20010000)
ROM_ADDR = 0x20000000 + (64 * 1024)
ROM_SIZE = (4 * 1024 * 1024) - (64 * 1024)

# 16KB @ 0x80000000
RAM_ADDR = 0x80000000
RAM_SIZE = 16 * 1024
