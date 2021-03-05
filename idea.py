# Base I
# --------
# Opcode
# Funct3
# Funct7
# Reg_RD
# Reg_RS1
# Reg_RS2
# Imm_I
# Imm_S
# Imm_B
# Imm_U
# Imm_J

# Ext M
# -----
# Nothing custom!

# Ext A
# -----
# A_Release
# A_Acquire
# A_Funct5

# Ext C
# -----
# C_Opcode
# C_Funct2
# C_Funct3
# C_Funct4
# C_Funct6
# C_Reg_RD     : compressed=False
# C_Reg_RS1    : compressed=False
# C_Reg_RS2    : compressed=False
# C_Reg_RD_RS1 : compressed=False
# C_Imm_CI
# C_Imm_CIS
# C_Imm_CLS
# C_Imm_CSS
# C_Imm_CIW
# C_Imm_CL
# C_Imm_CS
# C_Imm_CB
# C_Imm_CBI
# C_Imm_CJ


class Instruction:
    pass


class C_ADDI16SP(Instruction):
    opcode = C_Opcode(0b01)
    funct3 = C_Funct3(0b011)
    rd_rs1 = C_Reg_RD_RS1()
    imm = C_Imm_CIS()

    def __init__(self, rd_rs1, imm):
        self.rd_rs1 = rd_rs1
        self.imm = imm
