\ duplicate the item on top of the stack
: dup sp@ @ ;

\ make some numbers
: -1 dup dup nand dup dup nand nand ;
: 0 -1 dup nand ;
: 1 -1 dup + dup nand ;
: 2 1 1 + ;
: 3 1 2 + ;
: 4 2 2 + ;
: 8 4 4 + ;
: 12 4 8 + ;
: 16 8 8 + ;

\ logic and arithmetic operators
: invert dup nand ;
: and nand invert ;
: negate invert 1 + ;
: - negate + ;

\ equality checks
: = - 0= ;
: <> = invert ;

\ stack manipulation words
: drop dup - + ;
: over sp@ 4 - @ ;
: swap over over sp@ 12 - ! sp@ 4 - ! ;
: nip swap drop ;
: 2dup over over ;
: 2drop drop drop ;

\ more logic
: or invert swap invert and invert ;

\ left shift operators (1, 4, and 8 bits)
: 2* dup + ;
: 16* 2* 2* 2* 2* ;
: 256* 16* 16* ;

\ basic binary numbers
: 0b00 0 ;
: 0b01 1 ;
: 0b10 2 ;
: 0b11 3 ;

\ basic hex numbers
: 0x00 0 ;
: 0x04 1 2* 2* ;
: 0x08 1 2* 2* 2* ;
: 0x0c 0x08 0x04 or ;
: 0x10 1 16* ;
: 0x14 0x10 0x04 or ;
: 0x18 0x10 0x08 or ;
: 0x1c 0x10 0x0c or ;
: 0x20 1 16* 2* ;
: 0x24 0x20 0x04 or ;
: 0x28 0x20 0x08 or ;
: 0x2c 0x20 0x0c or ;
: 0x30 0x20 0x10 or ;
: 0x34 0x30 0x04 or ;
: 0x38 0x30 0x08 or ;
: 0x3c 0x30 0x0c or ;
