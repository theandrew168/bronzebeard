from pprint import pprint
import sys

from bronzebeard import asm

import pygments
from pygments.lexer import include, RegexLexer
from pygments.styles import get_style_by_name
from pygments.token import Comment, Name, Number, Operator, Punctuation, String, Text

from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import PygmentsTokens
from prompt_toolkit.styles import style_from_pygments_cls

# Usage:
# pip install prompt_toolkit
# python3 syntax.py examples/example.asm emacs
#
# References:
# https://python-prompt-toolkit.readthedocs.io/en/master/pages/printing_text.html
# https://pygments.org/docs/lexerdevelopment/
# https://pygments.org/docs/tokens/


class ASMLexer(RegexLexer):
    name = 'ASM'
    aliases = ['asm']
    filenames = ['*.asm']

    registers = sorted(asm.REGISTERS.keys(), key=len, reverse=True)
    instructions = sorted(asm.INSTRUCTIONS.keys(), key=len, reverse=True)

    tokens = {
        'root': [
            (r'\s+', Text),  # whitespace
            (r'[,()]+', Punctuation),  # punctuation
            (r'#.*?\n', Comment),  # comments
            (r'\w+:', Name.Label),  # labels
            (r'|'.join(instructions), Name.Builtin),  # instructions
            (r'|'.join(registers), Name.Variable),  # registers
            (r'(string|bytes|align|pack)', Name.Function),  # functions
            (r'%\w+', Name.Function),  # relocations
            (r'[A-Z][0-9A-Z_-]+', Name.Constant),  # constants
            (r'[+-]?0x[0-9a-fA-F]+', Number),  # numbers (hex)
            (r'[+-]?0b[0-9]+', Number),  # numbers (binary)
            (r'[+-]?[0-9]+(\.[0-9]+)?', Number),  # numbers (decimal)
            (r'"(\\"|[^"])*"', String),  # strings
            (r'\w+', Name.Label),  # references
            (r'[@=<>!]?[xcbB?hHiIlLqQnNefdspP]', Name.Constant),  # pack format
            (r'[+\-*/<>=!]+', Operator),  # operators
        ],
    }


with open(sys.argv[1]) as f:
    src = f.read()

# Printing the output of a pygments lexer.
tokens = list(pygments.lex(src, lexer=ASMLexer()))
pprint(tokens)
style = style_from_pygments_cls(get_style_by_name(sys.argv[2]))
print_formatted_text(PygmentsTokens(tokens), style=style, include_default_pygments_style=False)
