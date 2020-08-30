import struct

# References:
# https://man7.org/linux/man-pages/man5/elf.5.html
# https://en.wikipedia.org/wiki/Executable_and_Linkable_Format

class ELF:

    def __init__(self, code):
        self.code = code

        # code will be aligned to 64-bit boundary
        self.code_size = len(self.code)
        if self.code_size % 8 != 0:
            self.code_size += (8 - (self.code_size % 8))

        # strtab will be aligned to 64-bit boundary
        self.strtab_size = 17
        self.sht_offset = 0x1000 + self.code_size + self.strtab_size
        if self.sht_offset % 8 != 0:
            self.sht_offset += (8 - (self.sht_offset % 8))

    def build(self):
        elf = bytearray()

        # ELF header (64 bytes)
        elf.extend(b'\x7f\x45\x4c\x46')  # ident magic: 0x7f ELF
        elf.extend(b'\x02')  # itent class: 64 bit
        elf.extend(b'\x01')  # itent data: little endian
        elf.extend(b'\x01')  # itent version: 1
        elf.extend(b'\x00')  # itent os abi: System V
        elf.extend(b'\x00')  # itent abi version: 0
        elf.extend(b'\x00\x00\x00\x00\x00\x00\x00')  # unused padding
        elf.extend(b'\x02\x00')  # type: executable
        elf.extend(b'\x3e\x00')  # machine: amd64
        elf.extend(b'\x01\x00\x00\x00')  # version: 1
        elf.extend(b'\x00\x10\x40\x00\x00\x00\x00\x00')  # entry point: 0x401000
        elf.extend(b'\x40\x00\x00\x00\x00\x00\x00\x00')  # program header table offset: 0x40 (64 bytes)
        elf.extend(struct.pack('<Q', self.sht_offset))  # section header table offset
        elf.extend(b'\x00\x00\x00\x00')  # flags: <none>
        elf.extend(b'\x40\x00')  # header size: 0x40 (64 bytes)
        elf.extend(b'\x38\x00')  # program header entry size: 0x38 (56 bytes)
        elf.extend(b'\x02\x00')  # program header entries: 2
        elf.extend(b'\x40\x00')  # section header entry size: x40 (64 bytes)
        elf.extend(b'\x03\x00')  # section header entries: 3
        elf.extend(b'\x02\x00')  # section header string table index: 2

        # Program header 0 (56 bytes)
        elf.extend(b'\x01\x00\x00\x00')  # type: loadable segment
        elf.extend(b'\x04\x00\x00\x00')  # flags: read
        elf.extend(b'\x00\x00\x00\x00\x00\x00\x00\x00')  # offset: 0x00 (0 bytes)
        elf.extend(b'\x00\x00\x40\x00\x00\x00\x00\x00')  # virtual address: 0x400000
        elf.extend(b'\x00\x00\x40\x00\x00\x00\x00\x00')  # physical address: 0x400000
        elf.extend(b'\xb0\x00\x00\x00\x00\x00\x00\x00')  # file size: 0xb0 (176 bytes)
        elf.extend(b'\xb0\x00\x00\x00\x00\x00\x00\x00')  # mem size: 0xb0 (176 bytes)
        elf.extend(b'\x00\x10\x00\x00\x00\x00\x00\x00')  # alignment: 0x1000 (4096 bytes)

        # Program header 1 (56 bytes)
        elf.extend(b'\x01\x00\x00\x00')  # type: loadable segment
        elf.extend(b'\x05\x00\x00\x00')  # flags: read | exec
        elf.extend(b'\x00\x10\x00\x00\x00\x00\x00\x00')  # offset: 0x1000 (4096 bytes)
        elf.extend(b'\x00\x10\x40\x00\x00\x00\x00\x00')  # virtual address: 0x401000
        elf.extend(b'\x00\x10\x40\x00\x00\x00\x00\x00')  # physical address: 0x401000
        elf.extend(struct.pack('<Q', self.code_size))  # file size
        elf.extend(struct.pack('<Q', self.code_size))  # mem size
        elf.extend(b'\x00\x10\x00\x00\x00\x00\x00\x00')  # alignment: 0x1000 (4096 bytes)

        # Padding to page size 0x1000 (4096 byte) alignment
        while len(elf) % 0x1000 != 0:
            elf.extend(b'\x00')

        # Code
        elf.extend(self.code)

        # ??? Padding to 64-bit (8 byte) alignment ???
        while len(elf) % 8 != 0:
            elf.extend(b'\x00')

        # Data (empty)

        # Section names (17 bytes)
        elf.extend(b'\x00')  # <empty> (1 byte)
        elf.extend(b'\x2e\x73\x68\x73\x74\x72\x74\x61\x62\x00')  # .shstrtab (10 bytes)
        elf.extend(b'\x2e\x74\x65\x78\x74\x00')  # .text (6 bytes)

        # ??? Padding to 64-bit (8 byte) alignment ???
        while len(elf) % 8 != 0:
            elf.extend(b'\x00')

        # Section header 0 (64 bytes)
        elf.extend(b'\x00\x00\x00\x00')  # name: 0x00 (0 bytes)
        elf.extend(b'\x00\x00\x00\x00')  # type: null
        elf.extend(b'\x00\x00\x00\x00\x00\x00\x00\x00')  # flags: <none>
        elf.extend(b'\x00\x00\x00\x00\x00\x00\x00\x00')  # address: 0x00
        elf.extend(b'\x00\x00\x00\x00\x00\x00\x00\x00')  # offset: 0x00 (0 bytes)
        elf.extend(b'\x00\x00\x00\x00\x00\x00\x00\x00')  # size: 0x00 (0 bytes)
        elf.extend(b'\x00\x00\x00\x00')  # link: 0
        elf.extend(b'\x00\x00\x00\x00')  # info: 0
        elf.extend(b'\x00\x00\x00\x00\x00\x00\x00\x00')  # alignment: 0x00 (0 bytes)
        elf.extend(b'\x00\x00\x00\x00\x00\x00\x00\x00')  # entry size: 0x00 (0 bytes)

        # Section header 1 (64 bytes)
        elf.extend(b'\x0b\x00\x00\x00')  # name: 0x0b (11 bytes)
        elf.extend(b'\x01\x00\x00\x00')  # type: progbits
        elf.extend(b'\x06\x00\x00\x00\x00\x00\x00\x00')  # flags: execute | alloc
        elf.extend(b'\x00\x10\x40\x00\x00\x00\x00\x00')  # address: 0x401000
        elf.extend(b'\x00\x10\x00\x00\x00\x00\x00\x00')  # offset: 0x1000 (4096 bytes)
        elf.extend(struct.pack('<Q', len(self.code)))  # size
        elf.extend(b'\x00\x00\x00\x00')  # link: 0
        elf.extend(b'\x00\x00\x00\x00')  # info: 0
        elf.extend(b'\x01\x00\x00\x00\x00\x00\x00\x00')  # alignment: 1 (no constraints)
        elf.extend(b'\x00\x00\x00\x00\x00\x00\x00\x00')  # entry size: 0 (8 bytes)

        # Section header 2 (64 bytes)
        elf.extend(b'\x01\x00\x00\x00')  # name: 0x01 (1 byte)
        elf.extend(b'\x03\x00\x00\x00')  # type: strtab
        elf.extend(b'\x00\x00\x00\x00\x00\x00\x00\x00')  # flags: <none>
        elf.extend(b'\x00\x00\x00\x00\x00\x00\x00\x00')  # address: 0x00
        elf.extend(struct.pack('<Q', 0x1000 + self.code_size))  # offset
        elf.extend(b'\x11\x00\x00\x00\x00\x00\x00\x00')  # size: 0x11 (17 bytes)
        elf.extend(b'\x00\x00\x00\x00')  # link: 0
        elf.extend(b'\x00\x00\x00\x00')  # info: 0
        elf.extend(b'\x01\x00\x00\x00\x00\x00\x00\x00')  # alignment: 0x00 (no constraints)
        elf.extend(b'\x00\x00\x00\x00\x00\x00\x00\x00')  # entry size: 0x00 (0 bytes)

        return bytes(elf)
