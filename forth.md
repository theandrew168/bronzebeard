# forth
Forth was initially designed and created by [Charles Moore](https://en.wikipedia.org/wiki/Charles_H._Moore).
Many folks have adapted its ideas and principles to solve their own problems.
[Moving Forth](http://www.bradrodriguez.com/papers/moving1.htm) by Brad Rodriguez is an amazing source of Forth implementation details and tradeoffs.
If you are looking for some introductory content surrounding the Forth language in general, I recommend the book [Starting Forth](https://www.forth.com/starting-forth/) by Leo Brodie.

[Sectorforth](https://github.com/cesarblum/sectorforth) by Cesar Blum is the source of this implementation's general structure.
He took inspiration from a [1996 Usenet thread](https://groups.google.com/g/comp.lang.forth/c/NS2icrCj1jQ/m/ohh9v4KphygJ) wherein folks discussed requirements for a minimal yet fully functional Forth implementation.

## Portability
As far as portability goes, Forth only requires a few pieces of information and functionality.

1. ROM base address and size
2. RAM base address and size
3. Ability to read and write characters over serial UART

All three of the aforementioned devices are capable of running Forth: it is just a matter of collecting the memory info, implementing basic UART interaction, and then flashing the ROM.

## Primitive Words
This minimal selection of primitive words comes from Sectorforth and the Usenet thread it references.

| Word   | Stack Effects | Description                                   |
| ------ | ------------- | --------------------------------------------- |
| `:`    | ( -- )        | Start the definition of a new secondary word  |
| `;`    | ( -- )        | Finish the definition of a new secondary word |
| `@`    | ( addr -- x ) | Fetch memory contents at addr                 |
| `!`    | ( x addr -- ) | Store x at addr                               |
| `sp@`  | ( -- sp )     | Get pointer to top of data stack              |
| `rp@`  | ( -- rp )     | Get pointer to top of return stack            |
| `0=`   | ( x -- flag ) | -1 if top of stack is 0, 0 otherwise          |
| `+`    | ( x y -- z )  | Sum the two numbers at the top of the stack   |
| `nand` | ( x y -- z )  | NAND the two numbers at the top of the stack  |
| `key`  | ( -- x )      | Read ASCII character from serial input        |
| `emit` | ( x -- )      | Write ASCII character to serial output        |
