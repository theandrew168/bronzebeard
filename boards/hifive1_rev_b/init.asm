include ../../chips/FE310-G002.asm

# NOTE: The first 64KB of Flash is occupied by the bootloader
# (which jumps to 0x20010000 at the end). That leaves
# (4MB - 64KB = 4032KB) starting at 0x20010000 for programs.

# 4MB @ 0x20000000 (actually ~4MB @ 0x20010000)
ROM_ADDR = 0x20000000 + (64 * 1024)
ROM_SIZE = (4 * 1024 * 1024) - (64 * 1024)
