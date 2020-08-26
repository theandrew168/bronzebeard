from peachpy import *
from peachpy.x86_64 import *

with Function('meaning_of_life', tuple(), int64_t) as func:
    MOV(rax, 42)
    RETURN(rax)

meaning_of_life = func.finalize(abi.detect()).encode().load()
print(bytes(meaning_of_life.code_segment))
print(meaning_of_life())
