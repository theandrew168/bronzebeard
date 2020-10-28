: dup sp@ @ ;
: -1 dup dup nand dup dup nand nand ;
: 0 -1 dup nand ;
: 1 -1 dup + dup nand ;
: 2 1 1 + ;
: 4 2 2 + ;
: 8 4 4 + ;
: 12 4 8 + ;
: 16 8 8 + ;

: invert dup nand ;
: and nand invert ;
: negate invert 1 + ;
: - negate + ;

: = - 0= ;
: <> = invert ;

: drop dup - + ;
: over sp@ 4 - @ ;
: swap over over sp@ 12 - ! sp@ 4 - ! ;
: nip swap drop ;
: 2dup over over ;
: 2drop drop drop ;

: or invert swap invert and invert ;

: 2* dup + ;
: 4* 2* 2* ;
: 16* 4* 4* ;
: 256* 16* 16* ;

: 0x14 1 16* 1 4* or ;
: 0x18 1 16* 1 4* 2* or ;
: 0x40021000 1 256* 256* 256* 16* 4* 1 256* 256* 2* 1 256* 16* or or ;
: rcu 0x14 0x40021000 0x18 + ! ;
