import atexit
import os
import readline
import struct

from bronzebeard import asm


def repl():
    history_path = os.path.join(os.path.expanduser("~"), ".bronzebeard_history")
    try:
        readline.read_history_file(history_path)
        readline.set_history_length(1000)
    except FileNotFoundError:
        pass

    atexit.register(readline.write_history_file, history_path)

    # exclude Python builtins from eval env
    # https://docs.python.org/3/library/functions.html#eval
    env = {
        '__builtins__': None,
    }
    env.update(asm.REGISTERS)

    # TODO: make this better when it comes to PIs (one to many, etc)
    while True:
        try:
            line = input('RV32IMAC> ')
            tokens = asm.lex_tokens(line)
            item = asm.parse_item(tokens)

            items = [item]
            items = asm.transform_pseudo_instructions(items)
            items = asm.resolve_immediates(items, env)
            items = asm.resolve_instructions(items)

            blob = items[0]
            code, = struct.unpack('<I', blob.data)

            print('tokens: {}'.format(tokens.tokens))
            print('item:   {}'.format(item))
            print('binary: {:032b}'.format(code))
        except (EOFError, KeyboardInterrupt):
            break
        except Exception as e:
            print(e)
            continue


if __name__ == '__main__':
    repl()
