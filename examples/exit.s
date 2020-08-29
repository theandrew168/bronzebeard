.section .data
.section .text
.globl _start

# User-level applications use as integer registers for passing the sequence:
# %rdi, %rsi, %rdx, %rcx, %r8 and %r9

_start:
    mov $60, %rax  # setup syscall 'exit'
    mov $42, %rdi  # setup exit code
    syscall
