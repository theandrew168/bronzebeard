import os

from peachpy import *
from peachpy.x86_64 import *

from bronzebeard.elf import ELF

# User-level applications use as integer registers for passing the sequence:
# %rdi, %rsi, %rdx, %rcx, %r8 and %r9

code = bytearray()

# get current break addr (it'll be in rax)
code.extend(MOV(rax, 12).encode())
code.extend(MOV(rdi, 0).encode())
code.extend(SYSCALL().encode())

# extend by 30000 bytes and re-break
code.extend(MOV(rdi, rax).encode())
code.extend(ADD(rdi, 30000).encode())
code.extend(MOV(rax, 12).encode())
code.extend(SYSCALL().encode())

# exit
code.extend(MOV(rax, 60).encode())
code.extend(MOV(rdi, 42).encode())
code.extend(SYSCALL().encode())

elf = ELF(code)
with open('output.elf', 'wb') as f:
    f.write(elf.build())

os.chmod('output.elf', 0o775)
