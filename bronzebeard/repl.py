import atexit
import os
from pprint import pprint
import readline
import struct

import appdirs

from bronzebeard import asm


def repl():
    config_dir = appdirs.user_cache_dir('bronzebeard')
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    history_path = os.path.join(config_dir, '.bronzebeard_history')
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

    while True:
        try:
            line = input('RV32IMAC> ')

            lines = asm.read_assembly(line)
            line_tokens = asm.lex_assembly(lines)

            items = asm.parse_assembly(line_tokens)
            items = asm.resolve_immediates(items, env)
            item = items[0]
            items = asm.resolve_instructions(items)

            blob = items[0]
            code = struct.unpack('<I', blob.data)[0]
            tokens = line_tokens[0].tokens

            print('tokens: {}'.format(tokens))
            print('item:   {}'.format(item))
            print('binary: {:032b}'.format(code))
        except (EOFError, KeyboardInterrupt):
            break
        except Exception as e:
            print(e)
            continue


if __name__ == '__main__':
    repl()
