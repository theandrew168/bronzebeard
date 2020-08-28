import os
import sys

from peachpy import *
from peachpy.x86_64 import *

from bronzebeard.elf import ELF

# User-level applications use as integer registers for passing the sequence:
# %rdi, %rsi, %rdx, %rcx, %r8 and %r9

# read in the BF file to be compiled
with open(sys.argv[1], 'rb') as f:
    source = f.read()

with Function("_start", tuple()) as start:
    # get current break addr (it'll be in rax)
    MOV(rax, 12)  # setup 'brk' syscall
    MOV(rdi, 0)  # arg0: NULL
    SYSCALL()
    
    # save base ptr in r13
    MOV(r13, rax)
    
    # extend by 30000 bytes and re-break
    MOV(rdi, rax)  # setup 'brk' syscall
    ADD(rdi, 30000)  # arg0: base + 30000
    MOV(rax, 12)
    SYSCALL()

#    # init all cells to zero
#    MOV(r14, r13)
#    loop_start = Label('loop_start')
#    LABEL(loop_start)
#    MOV([r14], 0)
#    CMP(r13, r14)
#    JNE(loop_start)

    for c in source:
        if chr(c) == '>':
            ADD(r13, 1)  # move ptr forward
        elif chr(c) == '<':
            SUB(r13, 1)  # move ptr backward
        elif chr(c) == '+':
            ADD([r13], 1)  # increment cell
        elif chr(c) == '-':
            SUB([r13], 1)  # decrement cell
        elif chr(c) == '.':
            MOV(rax, 1)  # setup 'write' syscall
            MOV(rdi, 1)  # arg0: stdout
            MOV(rsi, r13)  # arg1: addr of data cell
            MOV(rdx, 1)  # arg2: size
            SYSCALL()
        elif chr(c) == ',':
            MOV(rax, 0)  # setup 'read' syscall
            MOV(rdi, 0)  # arg0: stdin
            MOV(rsi, r13)  # arg1: addr of data cell
            MOV(rdx, 1)  # arg2: size
            SYSCALL()

    # reset brk'd memory
    MOV(rax, 12)  # setup 'brk' syscall
    MOV(rdi, r13)  # arg0: base
    SYSCALL()
    
    # exit
    MOV(rax, 60)  # setup 'exit' syscall
    MOV(rdi, 42)  # arg0: 42
    SYSCALL()

    # unreachable return to make Function happy
    RETURN()

code = start.finalize(abi.detect()).encode().load().code_segment
elf = ELF(code)
with open('output.elf', 'wb') as f:
    f.write(elf.build())

os.chmod('output.elf', 0o775)
