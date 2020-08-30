# References:
# https://en.wikipedia.org/wiki/Mach-O
# https://github.com/aidansteele/osx-abi-macho-file-format-reference
# https://lowlevelbits.org/parsing-mach-o-files/
# https://h3adsh0tzz.com/2020/01/macho-file-format/

class MachO:

    def __init__(self, code):
        self.code = code

    def build(self):
        macho = bytearray()
        return bytes(macho)
