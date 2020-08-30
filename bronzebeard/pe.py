# 00000000  4d 5a 90 00 03 00 00 00  04 00 00 00 ff ff 00 00  |MZ..............|
# 00000010  b8 00 00 00 00 00 00 00  40 00 00 00 00 00 00 00  |........@.......|
# 00000020  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
# 00000030  00 00 00 00 00 00 00 00  00 00 00 00 80 00 00 00  |................|
# 00000040  0e 1f ba 0e 00 b4 09 cd  21 b8 01 4c cd 21 54 68  |........!..L.!Th|
# 00000050  69 73 20 70 72 6f 67 72  61 6d 20 63 61 6e 6e 6f  |is program canno|
# 00000060  74 20 62 65 20 72 75 6e  20 69 6e 20 44 4f 53 20  |t be run in DOS |
# 00000070  6d 6f 64 65 2e 0d 0d 0a  24 00 00 00 00 00 00 00  |mode....$.......|
# 00000080  50 45 00 00 64 86 02 00  00 00 00 00 00 00 00 00  |PE..d...........|
# 00000090  00 00 00 00 f0 00 2f 02  0b 02 02 22 00 02 00 00  |....../...."....|
# 000000a0  00 02 00 00 00 00 00 00  00 10 00 00 00 10 00 00  |................|
# 000000b0  00 00 40 00 00 00 00 00  00 10 00 00 00 02 00 00  |..@.............|
# 000000c0  04 00 00 00 00 00 00 00  05 00 02 00 00 00 00 00  |................|
# 000000d0  00 30 00 00 00 02 00 00  b0 87 00 00 03 00 00 00  |.0..............|
# 000000e0  00 00 20 00 00 00 00 00  00 10 00 00 00 00 00 00  |.. .............|
# 000000f0  00 00 10 00 00 00 00 00  00 10 00 00 00 00 00 00  |................|
# 00000100  00 00 00 00 10 00 00 00  00 00 00 00 00 00 00 00  |................|
# 00000110  00 20 00 00 14 00 00 00  00 00 00 00 00 00 00 00  |. ..............|
# 00000120  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
# *
# 00000180  00 00 00 00 00 00 00 00  2e 74 65 78 74 00 00 00  |.........text...|
# 00000190  30 00 00 00 00 10 00 00  00 02 00 00 00 02 00 00  |0...............|
# 000001a0  00 00 00 00 00 00 00 00  00 00 00 00 20 00 50 60  |............ .P`|
# 000001b0  2e 69 64 61 74 61 00 00  14 00 00 00 00 20 00 00  |.idata....... ..|
# 000001c0  00 02 00 00 00 04 00 00  00 00 00 00 00 00 00 00  |................|
# 000001d0  00 00 00 00 40 00 30 c0  00 00 00 00 00 00 00 00  |....@.0.........|
# 000001e0  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
# *
# 00000200  48 c7 c0 3c 00 00 00 48  c7 c7 2a 00 00 00 0f 05  |H..<...H..*.....|
# 00000210  ff ff ff ff ff ff ff ff  00 00 00 00 00 00 00 00  |................|
# *
# 00000230  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
# *
# 00000600

class PE:

    def __init__(self, code):
        self.code = code

    def build(self):
        pe = bytearray()

        # DOS Header (64 bytes)
        pe.extend(b'\x4d\x5a')  # magic number: MZ
        pe.extend(b'\x90\x00')  # bytes on last page: 0x90 (144 bytes)
        pe.extend(b'\x03\x00')  # pages (of 512 bytes): 0x03 (3 pages)
        pe.extend(b'\x00\x00')  # relocations: 0x00 (0 relocations)
        pe.extend(b'\x04\x00')  # header size: 0x04 (4 paragraphs)
        pe.extend(b'\x00\x00')  # min extra paragraphs needed: 0x00
        pe.extend(b'\xff\xff')  # max extra paragraphs needed: 0xffff
        pe.extend(b'\x00\x00')  # initial (relative) SS value: 0x00

        pe.extend(b'\xb8\x00')  # initial SP value: 0xb8 (184)
        pe.extend(b'\x00\x00')  # checksum: 0x00
        pe.extend(b'\x00\x00')  # initial IP value: 0x00
        pe.extend(b'\x00\x00')  # initial (relative) CS value: 0x00
        pe.extend(b'\x40\x00')  # offset of relocation table: 0x40 (64 bytes)
        pe.extend(b'\x00\x00')  # overlay number: 0x00
        pe.extend(b'\x00\x00')  # reserved words
        pe.extend(b'\x00\x00')  # ...

        pe.extend(b'\x00\x00')  # ...
        pe.extend(b'\x00\x00')  # ...
        pe.extend(b'\x00\x00')  # OEM identifier: 0x00
        pe.extend(b'\x00\x00')  # OEM info: 0x00
        pe.extend(b'\x00\x00')  # reserved words
        pe.extend(b'\x00\x00')  # ...
        pe.extend(b'\x00\x00')  # ...
        pe.extend(b'\x00\x00')  # ...

        pe.extend(b'\x00\x00')  # ...
        pe.extend(b'\x00\x00')  # ...
        pe.extend(b'\x00\x00')  # ...
        pe.extend(b'\x00\x00')  # ...
        pe.extend(b'\x00\x00')  # ...
        pe.extend(b'\x00\x00')  # ...
        pe.extend(b'\x80\x00\x00\x00')  # offset of PE header: 0x80 (128 bytes)

        # Real-mode stub program (64 bytes)
        # - on DOS machines, this stub simply prints an error message and exits
        pe.extend(b'\x0e\x1f\xba\x0e\x00\xb4\x09\xcd\x21\xb8\x01\x4c\xcd\x21\x54\x68')
        pe.extend(b'\x69\x73\x20\x70\x72\x6f\x67\x72\x61\x6d\x20\x63\x61\x6e\x6e\x6f')
        pe.extend(b'\x74\x20\x62\x65\x20\x72\x75\x6e\x20\x69\x6e\x20\x44\x4f\x53\x20')
        pe.extend(b'\x6d\x6f\x64\x65\x2e\x0d\x0d\x0a\x24\x00\x00\x00\x00\x00\x00\x00')

        # PE header (24 bytes)
        pe.extend(b'\x50\x45\x00\x00')  # magic number: PE
        pe.extend(b'\x64\x86')  # machine: 0x8664 (x86-64)
        pe.extend(b'\x02\x00')  # section count: 0x02 (2 sections)
        pe.extend(b'\x00\x00\x00\x00')  # time date stamp: 0x00
        pe.extend(b'\x00\x00\x00\x00')  # ptr to symbol table: 0x00
        pe.extend(b'\x00\x00\x00\x00')  # symbol count: 0x00
        pe.extend(b'\xf0\x00')  # optional header size: 0xf0 (240 bytes)
        pe.extend(b'\x2f\x02')  # characteristics: ???

        # Optional header (64-bit version "PE32+") (240 bytes)
        pe.extend(b'\x0b\x02')  # magic number: 0x020b
        pe.extend(b'\x02')  # major linker version: 0x02
        pe.extend(b'\x22')  # minor linker version: 0x22
        pe.extend(b'\x00\x02\x00\x00')  # code size: 0x200 (512 bytes)
        pe.extend(b'\x00\x02\x00\x00')  # initialized data size: 0x200 (512 bytes)
        pe.extend(b'\x00\x00\x00\x00')  # uninitialized data size: 0x00 (0 bytes)
        pe.extend(b'\x00\x10\x00\x00')  # entry point addr: 0x1000
        pe.extend(b'\x00\x10\x00\x00')  # code base addr: 0x1000
        pe.extend(b'\x00\x00\x40\x00\x00\x00\x00\x00')  # image base addr: 0x400000
        pe.extend(b'\x00\x10\x00\x00')  # section alignment: 0x1000 (4096 bytes)
        pe.extend(b'\x00\x02\x00\x00')  # file alignment: 0x200 (512 bytes)

        pe.extend(b'\x04\x00')  # major OS version: 0x04
        pe.extend(b'\x00\x00')  # minor OS version: 0x00
        pe.extend(b'\x00\x00')  # major image version: 0x00
        pe.extend(b'\x00\x00')  # minor image version: 0x00
        pe.extend(b'\x05\x00')  # major subsystem version: 0x05
        pe.extend(b'\x02\x00')  # minor subsystem version: 0x02
        pe.extend(b'\x00\x00\x00\x00')  # win32 version: 0x00
        pe.extend(b'\x00\x30\x00\x00')  # image size: 0x3000 (12288 bytes)
        pe.extend(b'\x00\x02\x00\x00')  # headers size: 0x200 (512 bytes)
        pe.extend(b'\xb0\x87\x00\x00')  # checksum: 0x000087b0 (TODO how to calc this?)
        pe.extend(b'\x03\x00')  # subsystem: 0x03 (0x02 for GUI, 0x03 for Console)
        pe.extend(b'\x00\x00')  # DLL characteristics: 0x00
        pe.extend(b'\x00\x00\x20\x00\x00\x00\x00\x00')  # stack reserve size: 0x200000
        pe.extend(b'\x00\x10\x00\x00\x00\x00\x00\x00')  # stack commit size: 0x1000
        pe.extend(b'\x00\x00\x10\x00\x00\x00\x00\x00')  # heap reserve size: 0x100000
        pe.extend(b'\x00\x10\x00\x00\x00\x00\x00\x00')  # heap commit size: 0x1000
        pe.extend(b'\x00\x00\x00\x00')  # loader flags: 0x00
        pe.extend(b'\x10\x00\x00\x00')  # Data dirs count: 0x10 (16 data dirs)

        # Data directory 0 (8 bytes)
        pe.extend(b'\x00\x00\x00\x00')  # addr: 0x00
        pe.extend(b'\x00\x00\x00\x00')  # size: 0x00 (0 bytes)

        # Data directory 1 (8 bytes)
        pe.extend(b'\x00\x20\x00\x00')  # addr: 0x2000
        pe.extend(b'\x14\x00\x00\x00')  # size: 0x14 (20 bytes)

        # Data directory 2 (8 bytes)
        pe.extend(b'\x00\x00\x00\x00')  # addr: 0x00
        pe.extend(b'\x00\x00\x00\x00')  # size: 0x00 (0 bytes)

        # Data directory 3 (8 bytes)
        pe.extend(b'\x00\x00\x00\x00')  # addr: 0x00
        pe.extend(b'\x00\x00\x00\x00')  # size: 0x00 (0 bytes)

        # Data directory 4 (8 bytes)
        pe.extend(b'\x00\x00\x00\x00')  # addr: 0x00
        pe.extend(b'\x00\x00\x00\x00')  # size: 0x00 (0 bytes)

        # Data directory 5 (8 bytes)
        pe.extend(b'\x00\x00\x00\x00')  # addr: 0x00
        pe.extend(b'\x00\x00\x00\x00')  # size: 0x00 (0 bytes)

        # Data directory 6 (8 bytes)
        pe.extend(b'\x00\x00\x00\x00')  # addr: 0x00
        pe.extend(b'\x00\x00\x00\x00')  # size: 0x00 (0 bytes)

        # Data directory 7 (8 bytes)
        pe.extend(b'\x00\x00\x00\x00')  # addr: 0x00
        pe.extend(b'\x00\x00\x00\x00')  # size: 0x00 (0 bytes)

        # Data directory 8 (8 bytes)
        pe.extend(b'\x00\x00\x00\x00')  # addr: 0x00
        pe.extend(b'\x00\x00\x00\x00')  # size: 0x00 (0 bytes)

        # Data directory 9 (8 bytes)
        pe.extend(b'\x00\x00\x00\x00')  # addr: 0x00
        pe.extend(b'\x00\x00\x00\x00')  # size: 0x00 (0 bytes)

        # Data directory 10 (8 bytes)
        pe.extend(b'\x00\x00\x00\x00')  # addr: 0x00
        pe.extend(b'\x00\x00\x00\x00')  # size: 0x00 (0 bytes)

        # Data directory 11 (8 bytes)
        pe.extend(b'\x00\x00\x00\x00')  # addr: 0x00
        pe.extend(b'\x00\x00\x00\x00')  # size: 0x00 (0 bytes)

        # Data directory 12 (8 bytes)
        pe.extend(b'\x00\x00\x00\x00')  # addr: 0x00
        pe.extend(b'\x00\x00\x00\x00')  # size: 0x00 (0 bytes)

        # Data directory 13 (8 bytes)
        pe.extend(b'\x00\x00\x00\x00')  # addr: 0x00
        pe.extend(b'\x00\x00\x00\x00')  # size: 0x00 (0 bytes)

        # Data directory 14 (8 bytes)
        pe.extend(b'\x00\x00\x00\x00')  # addr: 0x00
        pe.extend(b'\x00\x00\x00\x00')  # size: 0x00 (0 bytes)

        # Data directory 15 (8 bytes)
        pe.extend(b'\x00\x00\x00\x00')  # addr: 0x00
        pe.extend(b'\x00\x00\x00\x00')  # size: 0x00 (0 bytes)

#                                    2e 74 65 78 74 00 00 00  |        .text...|
# 00000190  30 00 00 00 00 10 00 00  00 02 00 00 00 02 00 00  |0...............|
# 000001a0  00 00 00 00 00 00 00 00  00 00 00 00 20 00 50 60  |............ .P`|
# 000001b0  2e 69 64 61 74 61 00 00  14 00 00 00 00 20 00 00  |.idata....... ..|
# 000001c0  00 02 00 00 00 04 00 00  00 00 00 00 00 00 00 00  |................|
# 000001d0  00 00 00 00 40 00 30 c0  00 00 00 00 00 00 00 00  |....@.0.........|
# 000001e0  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
# *
# 00000200  48 c7 c0 3c 00 00 00 48  c7 c7 2a 00 00 00 0f 05  |H..<...H..*.....|
# 00000210  ff ff ff ff ff ff ff ff  00 00 00 00 00 00 00 00  |................|
# *
# 00000230  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
# *
# 00000600

        pe.extend(b'\x00')
        pe.extend(b'\x00\x00')
        pe.extend(b'\x00\x00\x00\x00')
        pe.extend(b'\x00\x00\x00\x00\x00\x00\x00\x00')
        return bytes(pe)
