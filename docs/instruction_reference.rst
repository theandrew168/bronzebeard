Instruction Reference
=====================
These tables provide summaries for the baseline RISC-V instructions and common extensions.
Full `specifications <https://riscv.org/technical/specifications/>`_ be found on the RISC-V website.
Additionally, more details about each instruction can be found `here <https://msyksphinz-self.github.io/riscv-isadoc/html/index.html>`_.

Pseudo Instructions
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
:code:`bgtu rs, rt, offset`  :code:`bltu rt, rs, offset`  Branch if > (unsigned)
:code:`bleu rs, rt, offset`  :code:`bgeu rt, rs, offset`  Branch if <= (unsigned)
:code:`j offset`             :code:`jal x0, offset`       Jump
:code:`jal offset`           :code:`jal x1, offset`       Jump and link
:code:`jr rs`                :code:`jalr x0, 0(rs)`       Jump register
:code:`jalr rs`              :code:`jalr x1, 0(rs)`       Jump and link register
:code:`ret`                  :code:`jalr x0, 0(x1)`       Return from subroutine
:code:`call offset`          See below                    Call far-away subroutine
:code:`tail offset`          See below                    Tail call far-away subroutine
:code:`fence`                :code:`fence iorw, iorw`     Fence on all memory and I/O
===========================  ===========================  ===========

Expansion of :code:`li rd, imm`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Depending on the value of the :code:`imm`, :code:`li` may get expanded into a few different combinations of instructions.

=================================  =========
Criteria                           Expansion
=================================  =========
:code:`imm between [-2048, 2047]`  :code:`addi rd, x0, %lo(imm)`
:code:`imm & 0xfff == 0`           :code:`lui rd, %hi(imm)`
otherwise                          | :code:`lui rd, %hi(imm)`
                                   | :code:`addi rd, rd, %lo(imm)`
=================================  =========

Expansion of :code:`call offset`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Depending on how near / far away the label referred to by :code:`offset` is, :code:`call` may get expanded into a few different combinations of instructions.

======================  =========
Criteria                Expansion
======================  =========
:code:`offset` is near  :code:`jal x1, %lo(offset)`
otherwise               | :code:`auipc x1, %hi(offset)`
                        | :code:`jalr x1, x1, %lo(offset)`
======================  =========

Expansion of :code:`tail offset`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Depending on how near / far away the label referred to by :code:`offset` is, :code:`tail` may get expanded into a few different combinations of instructions.

======================  =========
Criteria                Expansion
======================  =========
:code:`offset` is near  :code:`jal x0, %lo(offset)`
otherwise               | :code:`auipc x6, %hi(offset)`
                        | :code:`jalr x0, x6, %lo(offset)`
======================  =========

RV32I Base Instruction Set
--------------------------

===========================  ===========
Instruction                  Description
===========================  ===========
:code:`lui rd, imm`          load upper 20 bits of :code:`rd` with 20-bit :code:`imm`, fill lower 12 bits with zeroes
:code:`auipc rd, imm`        load upper 20 bits of :code:`pc` with 20-bit :code:`imm`, fill lower 12 bits with zeroes, add this offset to addr of this instruction and store into :code:`rd`
:code:`jal rd, imm`          jump offset 20-bit MO2 :code:`imm` and store return addr into :code:`rd`
:code:`jalr rd, rs1, imm`    jump offset 12-bit MO2 :code:`imm` plus :code:`rs1` and store return addr into :code:`rd`
:code:`beq rs1, rs2, imm`    jump offset 12-bit MO2 :code:`imm` if :code:`rs1` is equal to :code:`rs2`
:code:`bne rs1, rs2, imm`    jump offset 12-bit MO2 :code:`imm` if :code:`rs1` is not equal to :code:`rs2`
:code:`blt rs1, rs2, imm`    jump offset 12-bit MO2 :code:`imm` if :code:`rs1` is less than :code:`rs2`
:code:`bge rs1, rs2, imm`    jump offset 12-bit MO2 :code:`imm` if :code:`rs1` is greater than or equal to :code:`rs2`
:code:`bltu rs1, rs2, imm`   jump offset 12-bit MO2 :code:`imm` if :code:`rs1` is less than :code:`rs2` (unsigned)
:code:`bgeu rs1, rs2, imm`   jump offset 12-bit MO2 :code:`imm` if :code:`rs1` is greater than or equal to :code:`rs2` (unsigned)
:code:`lb rd, rs1, imm`      load 8-bit value from addr in :code:`rs1` plus 12-bit :code:`imm` into :code:`rd` (sign extend)
:code:`lh rd, rs1, imm`      load 16-bit value from addr in :code:`rs1` plus 12-bit :code:`imm` into :code:`rd` (sign extend)
:code:`lw rd, rs1, imm`      load 32-bit value from addr in :code:`rs1` plus 12-bit :code:`imm` into :code:`rd`
:code:`lbu rd, rs1, imm`     load 8-bit value from addr in :code:`rs1` plus 12-bit :code:`imm` into :code:`rd` (zero extend)
:code:`lhu rd, rs1, imm`     load 16-bit value from addr in :code:`rs1` plus 12-bit :code:`imm` into :code:`rd` (zero extend)
:code:`sb rs1, rs2, imm`     store 8-bit value from :code:`rs2` into addr in :code:`rs1` plus 12-bit :code:`imm`
:code:`sh rs1, rs2, imm`     store 16-bit value from :code:`rs2` into addr in :code:`rs1` plus 12-bit :code:`imm`
:code:`sw rs1, rs2, imm`     store 32-bit value from :code:`rs2` into addr in :code:`rs1` plus 12-bit :code:`imm`
:code:`addi rd, rs1, imm`    add 12-bit :code:`imm` to :code:`rs1` and store into :code:`rd`
:code:`slti rd, rs1, imm`    store 1 into :code:`rd` if :code:`rs1` is less than 12-bit :code:`imm` else store 0
:code:`sltiu rd, rs1, imm`   store 1 into :code:`rd` if :code:`rs1` is less than 12-bit :code:`imm` (unsigned) else store 0
:code:`xori rd, rs1, imm`    bitwise XOR 12-bit :code:`imm` with :code:`rs1` and store into :code:`rd`
:code:`ori rd, rs1, imm`     bitwise OR 12-bit :code:`imm` with :code:`rs1` and store into :code:`rd`
:code:`andi rd, rs1, imm`    bitwise AND 12-bit :code:`imm` with :code:`rs1` and store into :code:`rd`
:code:`slli rd, rs1, shamt`  shift :code:`rs1` left by :code:`shamt` bits and store into :code:`rd`
:code:`srli rd, rs1, shamt`  shift :code:`rs1` right by :code:`shamt` bits and store into :code:`rd` (shift in zeroes)
:code:`srai rd, rs1, shamt`  shift :code:`rs1` right by :code:`shamt` bits and store into :code:`rd` (shift in sign bit)
:code:`add rd, rs1, rs2`     add :code:`rs2` to :code:`rs1` and store into :code:`rd`
:code:`sub rd, rs1, rs2`     subtract :code:`rs2` from :code:`rs1` and store into :code:`rd`
:code:`sll rd, rs1, rs2`     shift :code:`rs1` left by :code:`rs2` bits and store into :code:`rd`
:code:`slt rd, rs1, rs2`     store 1 into :code:`rd` if :code:`rs1` is less than :code:`rs2` else store 0
:code:`sltu rd, rs1, rs2`    store 1 into :code:`rd` if :code:`rs1` is less than :code:`rs2` (unsigned) else store 0
:code:`xor rd, rs1, rs2`     bitwise XOR :code:`rs2` with :code:`rs1` and store into :code:`rd`
:code:`srl rd, rs1, rs2`     shift :code:`rs1` right by :code:`rs2` bits and store into :code:`rd` (shift in zeroes)
:code:`sra rd, rs1, rs2`     shift :code:`rs1` right by :code:`rs2` bits and store into :code:`rd` (shift in sign bit)
:code:`or rd, rs1, rs2`      bitwise OR :code:`rs2` with :code:`rs1` and store into :code:`rd`
:code:`and rd, rs1, rs2`     bitwise AND :code:`rs2` with :code:`rs1` and store into :code:`rd`
:code:`fence succ, pred`     order device I/O and memory accesses
:code:`ecall`                make a service request to the execution environment
:code:`ebreak`               return control to a debugging environment
===========================  ===========

RV32M Standard Extension
------------------------

===========================  ===========
Instruction                  Description
===========================  ===========
:code:`mul rd, rs1, rs2`     multiply :code:`rs1` (signed) by :code:`rs2` (signed) and store lower 32 bits into :code:`rd`
:code:`mulh rd, rs1, rs2`    multiply :code:`rs1` (signed) by :code:`rs2` (signed) and store upper 32 bits into :code:`rd`
:code:`mulhsu rd, rs1, rs2`  multiply :code:`rs1` (signed) by :code:`rs2` (unsigned) and store upper 32 bits into :code:`rd`
:code:`mulhu rd, rs1, rs2`   multiply :code:`rs1` (unsigned) by :code:`rs2` (unsigned) and store upper 32 bits into :code:`rd`
:code:`div rd, rs1, rs2`     divide (signed) :code:`rs1` by :code:`rs2` and store into :code:`rd`
:code:`divu rd, rs1, rs2`    divide (unsigned) :code:`rs1` by :code:`rs2` and store into :code:`rd`
:code:`rem rd, rs1, rs2`     remainder (signed) of :code:`rs1` divided by :code:`rs2` and store into :code:`rd`
:code:`remu rd, rs1, rs2`    remainder (unsigned) of :code:`rs1` divided by :code:`rs2` and store into :code:`rd`
===========================  ===========

RV32A Standard Extension
------------------------
All of the following atomic instructions also accept two additional parameters: :code:`aq` and :code:`rl`.
These are short for "acquire" and "release" and must either be both specified or both unspecified.
The default for each if unspecified is zero.

For example::

  # both aq and rl are zero
  lr.w t0 t1
  lr.w t0 t1 0 0

  # both aq and rl are one
  lr.w t0 t1 1 1

  # mix and match
  lr.w t0 t1 0 1  # aq=0, rl=1
  lr.w t0 t1 1 0  # aq=1, rl=0

==============================  ===========
Instruction                     Description
==============================  ===========
:code:`lr.w rd, rs1`            load (reserved) 32-bit value from addr in :code:`rs1` into :code:`rd` and register a reservation set
:code:`sc.w rd, rs1, rs2`       store (conditional) 32-bit value from :code:`rs2` into addr in :code:`rs1` and write status to :code:`rd`
:code:`amoswap.w rd, rs1, rs2`  atomically load value from addr in :code:`rs1` into :code:`rd`, SWAP with value in :code:`rs2`, store back to addr :code:`rs1`
:code:`amoadd.w rd, rs1, rs2`   atomically load value from addr in :code:`rs1` into :code:`rd`, ADD to value in :code:`rs2`, store back to addr :code:`rs1`
:code:`amoxor.w rd, rs1, rs2`   atomically load value from addr in :code:`rs1` into :code:`rd`, XOR with value in :code:`rs2`, store back to addr :code:`rs1`
:code:`amoand.w rd, rs1, rs2`   atomically load value from addr in :code:`rs1` into :code:`rd`, AND with value in :code:`rs2`, store back to addr :code:`rs1`
:code:`amoor.w rd, rs1, rs2`    atomically load value from addr in :code:`rs1` into :code:`rd`, OR with value in :code:`rs2`, store back to addr :code:`rs1`
:code:`amomin.w rd, rs1, rs2`   atomically load value from addr in :code:`rs1` into :code:`rd`, MIN with value in :code:`rs2`, store back to addr :code:`rs1`
:code:`amomax.w rd, rs1, rs2`   atomically load value from addr in :code:`rs1` into :code:`rd`, MAX with value in :code:`rs2`, store back to addr :code:`rs1`
:code:`amominu.w rd, rs1, rs2`  atomically load value from addr in :code:`rs1` into :code:`rd`, MIN (unsigned) with value in :code:`rs2`, store back to addr :code:`rs1`
:code:`amomaxu.w rd, rs1, rs2`  atomically load value from addr in :code:`rs1` into :code:`rd`, MAX (unsigned) with value in :code:`rs2`, store back to addr :code:`rs1`
==============================  ===========

RV32C Standard Extension
------------------------

================================  ===========
Instruction                       Description
================================  ===========
:code:`c.addi4spn rd', nzuimm`    add 8-bit MO4 :code:`nzuimm` to :code:`x2/sp` and store into :code:`rd'`
:code:`c.lw rd', rs1', uimm`      load 32-bit value from addr in :code:`rs1'` plus 5-bit MO4 :code:`uimm` into :code:`rd'`
:code:`c.sw rs1', rs2', uimm`     store 32-bit value from :code:`rs2'` into addr in :code:`rs1'` plus 5-bit MO4 :code:`uimm`
:code:`c.nop`                     no operation
:code:`c.addi rd/rs1!=0, nzimm`   add 6-bit :code:`imm` to :code:`rd/rs1` and store into :code:`rd/rs1`
:code:`c.jal imm`                 jump offset 11-bit MO2 :code:`imm` and store return addr into :code:`x1/ra`
:code:`c.li rd!=0, imm`           load 6-bit :code:`imm` into :code:`rd`, sign extend upper bits
:code:`c.addi16sp nzimm`          add 6-bit MO16 :code:`nzimm` to :code:`x2/sp` and store into :code:`x2/sp`
:code:`c.lui rd!={0,2}, nzimm`    load 6-bit :code:`imm` into middle bits [17:12] of :code:`rd`, sign extend upper bits, clear lower bits
:code:`c.srli rd'/rs1', nzuimm`   shift :code:`rd'/rs1'` right by :code:`nzuimm` bits and store into :code:`rd'/rs1'` (shift in zeroes)
:code:`c.srai rd'/rs1', nzuimm`   shift :code:`rd'/rs1'` right by :code:`nzuimm` bits and store into :code:`rd'/rs1'` (shift in sign bit)
:code:`c.andi rd'/rs1', imm`      bitwise AND 6-bit :code:`imm` with :code:`rd'/rs1'` and store into :code:`rd'/rs1'`
:code:`c.sub rd'/rs1', rs2'`      subtract :code:`rs2'` from :code:`rd'/rs1'` and store into :code:`rd'/rs1'`
:code:`c.xor rd'/rs1', rs2'`      bitwise XOR :code:`rs2'` with :code:`rd'/rs1'` and store into :code:`rd'/rs1'`
:code:`c.or rd'/rs1', rs2'`       bitwise OR :code:`rs2'` with :code:`rd'/rs1'` and store into :code:`rd'/rs1'`
:code:`c.and rd'/rs1', rs2'`      bitwise AND :code:`rs2'` with :code:`rd'/rs1'` and store into :code:`rd'/rs1'`
:code:`c.j imm`                   jump offset 11-bit MO2 :code:`imm`
:code:`c.beqz rs1', imm`          jump offset 8-bit MO2 :code:`imm` if :code:`rs1'` is equal to zero
:code:`c.bnez rs1', imm`          jump offset 8-bit MO2 :code:`imm` if :code:`rs1'` is not equal to zero
:code:`c.slli rd/rs1!=0, nziumm`  shift :code:`rd/rs1` left by :code:`nzuimm` bits and store into :code:`rd/rs1`
:code:`c.lwsp rd!=0, uimm`        load 32-bit value from addr in :code:`x2/sp` plus 6-bit MO4 :code:`uimm` into :code:`rd`
:code:`c.jr rs1!=0`               jump to addr in :code:`rs1`
:code:`c.mv rd!=0, rs2!=0`        copy value from :code:`rs2` into :code:`rd`
:code:`c.ebreak`                  return control to a debugging environment
:code:`c.jalr rs1!=0`             jump to addr in :code:`rs1` and store return addr into :code:`x1/ra`
:code:`c.add rd/rs1!=0, rs2!=0`   add :code:`rs2` to :code:`rd/rs1` and store into :code:`rd/rs1`
:code:`c.swsp rs2, uimm`          store 32-bit value from :code:`rs2` into addr in :code:`x2/sp` plus 6-bit MO4 :code:`uimm`
================================  ===========
