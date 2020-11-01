\ duplicate the item on top of the stack
: dup sp@ @ ;

\ make some numbers
: -1 dup dup nand dup dup nand nand ;
: 0 -1 dup nand ;
: 1 -1 dup + dup nand ;
: 2 1 1 + ;
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
