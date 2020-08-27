import os
import sys

from peachpy import *
from peachpy.x86_64 import *

from bronzebeard.elf import ELF

# User-level applications use as integer registers for passing the sequence:
# %rdi, %rsi, %rdx, %rcx, %r8 and %r9

code = bytearray()

# get current break addr (it'll be in rax)
code.extend(MOV(rax, 12).encode())  # setup 'brk' syscall
code.extend(MOV(rdi, 0).encode())  # arg0: NULL
code.extend(SYSCALL().encode())

# save base ptr in r13
code.extend(MOV(r13, rax).encode())

# extend by 30000 bytes and re-break
code.extend(MOV(rdi, rax).encode())  # setup 'brk' syscall
code.extend(ADD(rdi, 30000).encode())  # arg0: base + 30000
code.extend(MOV(rax, 12).encode())
code.extend(SYSCALL().encode())

# init all cells to zero
code.extend(MOV(r14, r13).encode())
loop_start = Label('loop_start')
LABEL(loop_start)
code.extend(MOV([r14], 0).encode())
code.extend(CMP(r13, r14).encode())
code.extend(JNE(loop_start).encode())

with open(sys.argv[1], 'rb') as f:
    source = f.read()

for c in source:
    if chr(c) == '>':
        code.extend(ADD(r13, 1).encode())  # move ptr forward
    elif chr(c) == '<':
        code.extend(SUB(r13, 1).encode())  # move ptr backward
    elif chr(c) == '+':
        code.extend(ADD([r13], 1).encode())  # increment cell
    elif chr(c) == '-':
        code.extend(SUB([r13], 1).encode())  # decrement cell
    elif chr(c) == '.':
        code.extend(MOV(rax, 1).encode())  # setup 'write' syscall
        code.extend(MOV(rdi, 1).encode())  # arg0: stdout
        code.extend(MOV(rsi, r13).encode())  # arg1: addr of data cell
        code.extend(MOV(rdx, 1).encode())  # arg2: size
        code.extend(SYSCALL().encode())
    elif chr(c) == ',':
        code.extend(MOV(rax, 0).encode())  # setup 'read' syscall
        code.extend(MOV(rdi, 0).encode())  # arg0: stdin
        code.extend(MOV(rsi, r13).encode())  # arg1: addr of data cell
        code.extend(MOV(rdx, 1).encode())  # arg2: size
        code.extend(SYSCALL().encode())

# reset brk'd memory
code.extend(MOV(rax, 12).encode())  # setup 'brk' syscall
code.extend(MOV(rdi, r13).encode())  # arg0: base
code.extend(SYSCALL().encode())

# exit
code.extend(MOV(rax, 60).encode())  # setup 'exit' syscall
code.extend(MOV(rdi, 42).encode())  # arg0: 42
code.extend(SYSCALL().encode())

elf = ELF(code)
with open('output.elf', 'wb') as f:
    f.write(elf.build())

os.chmod('output.elf', 0o775)
