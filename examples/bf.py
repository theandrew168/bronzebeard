from collections import namedtuple
import os
import sys

from peachpy import *
from peachpy.x86_64 import *

sys.path[0:0] = ['.', '..']
from bronzebeard.elf import ELF

# this is necessary to prevent mandlebrot.bf from blowing the stack
sys.setrecursionlimit(5000)

# Based on Eli Bendersky's BF Compiler:
# https://eli.thegreenplace.net/2017/adventures-in-jit-compilation-part-4-in-python/

# User-level applications use as integer registers for passing the sequence:
# %rdi, %rsi, %rdx, %rcx, %r8 and %r9

# data type to hold matching sets of looping bracket pairs
BracketLabels = namedtuple('BracketLabels', 'start end')
open_bracket_stack = []

# read in the BF file to be compiled
with open(sys.argv[1], 'rb') as f:
    source = f.read()

with Function("_start", tuple()) as start:
    # get current break addr (it'll be in rax)
    MOV(rax, 12)  # setup 'brk' syscall
    MOV(rdi, 0)  # arg0: NULL
    SYSCALL()
    
    # save base ptr in dataptr (r13)
    dataptr = r13
    MOV(dataptr, rax)
    
    # extend by 30000 bytes and re-break
    MOV(rdi, rax)  # setup 'brk' syscall
    ADD(rdi, 30000)  # arg0: base + 30000
    MOV(rax, 12)
    SYSCALL()

    for c in source:
        if chr(c) == '>':
            ADD(dataptr, 1)  # move ptr forward
        elif chr(c) == '<':
            SUB(dataptr, 1)  # move ptr backward
        elif chr(c) == '+':
            ADD([dataptr], 1)  # increment cell
        elif chr(c) == '-':
            SUB([dataptr], 1)  # decrement cell
        elif chr(c) == '.':
            MOV(rax, 1)  # setup 'write' syscall
            MOV(rdi, 1)  # arg0: stdout
            MOV(rsi, dataptr)  # arg1: addr of data cell
            MOV(rdx, 1)  # arg2: size
            SYSCALL()
        elif chr(c) == ',':
            MOV(rax, 0)  # setup 'read' syscall
            MOV(rdi, 0)  # arg0: stdin
            MOV(rsi, dataptr)  # arg1: addr of data cell
            MOV(rdx, 1)  # arg2: size
            SYSCALL()
        elif chr(c) == '[':
            # create labels for before and after the loop
            loop_start_label = Label()
            loop_end_label = Label()
            # end the loop if current cell is zero
            CMP([dataptr], 0)
            JZ(loop_end_label)
            # bind the "start loop" label here
            LABEL(loop_start_label)
            open_bracket_stack.append(BracketLabels(loop_start_label, loop_end_label))
        elif chr(c) == ']':
            if len(open_bracket_stack) == 0:
                raise RuntimeError('mismatched looping brackets')
            labels = open_bracket_stack.pop()
            # jump back to start if current cell is not zero
            CMP([dataptr], 0)
            JNZ(labels.start)
            # bind the "end loop" label here
            LABEL(labels.end)

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
