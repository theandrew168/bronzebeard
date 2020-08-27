from peachpy import *
from peachpy.x86_64 import *

from bronzebeard.elf import ELF

code = bytearray()
code.extend(MOV(rax, 60).encode())
code.extend(MOV(rdi, 42).encode())
code.extend(SYSCALL().encode())

elf = ELF(code)
with open('output.elf', 'wb') as f:
    f.write(elf.build())
