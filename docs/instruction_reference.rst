Instruction Reference
=====================
These tables provide summaries for the baseline RISC-V instructions and common extensions.
Full `specifications <https://riscv.org/technical/specifications/>`_ be found on the RISC-V website.
Additionally, more details about each instruction can be found `here <https://msyksphinz-self.github.io/riscv-isadoc/html/index.html>`_.

Psuedo Instructions
-------------------
These pseudo-instructions represent additional actions and can be used like regular instructions.
One of the early passes in the assembler will transform them as described in this table.

===========================  ===========================  ===========
Instruction                  Expansion                    Description
===========================  ===========================  ===========
:code:`nop`                  :code:`addi x0, x0, 0`       No operation
:code:`li rd, imm`           See below                    Load immediate
:code:`mv rd, rs`            :code:`addi rd, rs, 0`       Copy register
:code:`not rd, rs`           :code:`xori rd, rs, -1`      One's complement
:code:`neg rd, rs`           :code:`sub rd, x0, rs`       Two's complement
:code:`seqz rd, rs`          :code:`sltiu rd, rs, 1`      Set if == zero
:code:`snez rd, rs`          :code:`sltu rd, x0, rs`      Set if != zero
:code:`sltz rd, rs`          :code:`slt rd, rs, x0`       Set if < zero
:code:`sgtz rd, rs`          :code:`slt rd, x0, rs`       Set if > zero
:code:`beqz rs, offset`      :code:`beq rs, x0, offset`   Branch if == zero
:code:`bnez rs, offset`      :code:`bne rs, x0, offset`   Branch if != zero
:code:`blez rs, offset`      :code:`bge x0, rs, offset`   Branch if <= zero
:code:`bgez rs, offset`      :code:`bge rs, x0, offset`   Branch if >= zero
:code:`bltz rs, offset`      :code:`blt rs, x0, offset`   Branch if < zero
:code:`bgtz rs, offset`      :code:`blt x0, rs, offset`   Branch if > zero
:code:`bgt rs, rt, offset`   :code:`blt rt, rs, offset`   Branch if >
:code:`ble rs, rt, offset`   :code:`bge rt, rs, offset`   Branch if <=
:code:`bgtu rs, rt, offset`  :code:`bltu rt, rs, offset`  Branch if >, unsigned
:code:`bleu rs, rt, offset`  :code:`bgeu rt, rs, offset`  Branch if <=, unsigned
:code:`j offset`             :code:`jal x0, offset`       Jump
:code:`jal offset`           :code:`jal x1, offset`       Jump and link
:code:`jr rs`                :code:`jalr x0, 0(rs)`       Jump register
:code:`jalr rs`              :code:`jalr x1, 0(rs)`       Jump and link register
:code:`ret`                  :code:`jalr x0, 0(x1)`       Return from subroutine
:code:`call offset`          See below                    Call far-away subroutine
:code:`tail offset`          See below                    Tail call fair-away subroutine
:code:`fence`                :code:`fence iorw, iorw`     Fence on all memory and I/O
===========================  ===========================  ===========

RV32I Base Instruction Set
--------------------------

RV32M Standard Extension
------------------------

RV32A Standard Extension
------------------------

RV32C Standard Extension
------------------------
