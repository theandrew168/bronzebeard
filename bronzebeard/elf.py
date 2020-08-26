# Based on the big breakout image from:
# https://en.wikipedia.org/wiki/Executable_and_Linkable_Format

class ELF:

    def __init__(self, code):
        self.code = code

    def build(self):
        elf = bytearray()
        elf.extend(b'\x7f\x45\x4c\x46')  # ident magic: constant signature
        elf.extend(b'\x02')  # itent class: 64 bit
        elf.extend(b'\x01')  # itent data: little endian
        elf.extend(b'\x01')  # itent version: 1
        elf.extend(b'\x00')  # itent os abi: System V
        elf.extend(b'\x00')  # itent abi version: 0
        elf.extend(b'\x00\x00\x00\x00\x00\x00\x00')  # unused padding
        elf.extend(b'\x02\x00')  # type: executable
        elf.extend(b'\x3e\x00')  # machine: amd64
        elf.extend(b'\x01\x00\x00\x00')  # version: 1
        elf.extend(b'\x00\x00\x40\x00\x00\x00\x00\x00')  # TODO entry point: 0x400000 + offset to _start (0x401000)
        elf.extend(b'\x40\x00\x00\x00\x00\x00\x00\x00')  # program header table offset: 0x40
        elf.extend(b'\x80\x00\x00\x00\x00\x00\x00\x00')  # TODO section header table offset: depends
        elf.extend(b'\x00\x00\x00\x00')  # flags: 0
        elf.extend(b'\x40\x00')  # header size: 64 bytes
        elf.extend(b'\x40\x00')  # program header entry size: 64 bytes
        elf.extend(b'\x01\x00')  # TODO program header entries: depends
        elf.extend(b'\x40\x00')  # section header entry size: 64 bytes
        elf.extend(b'\x04\x00')  # TODO section header entries: depends
        elf.extend(b'\x04\x00')  # index of names in section header entry: 4

        return bytes(elf)
