from collections import deque, namedtuple
import operator

BuiltinWord = namedtuple('BuiltinWord', 'name func')
CompoundWord = namedtuple('CompoundWord', 'name body')
class VariableWord:
    def __init__(self, name):
        self.name = name
        self.value = None

s = deque()

def push(data):
    s.append(data)

def pop():
    if len(s) == 0:
        raise RuntimeError('Stack underflow')
    return s.pop()

def word_add():
    a = pop()
    b = pop()
    push(a + b)

def word_sub():
    a = pop()
    b = pop()
    push(a - b)

def word_mul():
    a = pop()
    b = pop()
    push(a * b)

def word_div():
    a = pop()
    b = pop()
    push(a / b)

def word_print():
    a = pop()
    print(a, end='')
    print(' ', end='')

def word_cr():
    pass

def word_dup():
    a = pop()
    push(a)
    push(a)

def word_ps():
    print(list(s), end='')
    print(' ', end='')

WORDS = [
    BuiltinWord('+', word_add),
    BuiltinWord('-', word_sub),
    BuiltinWord('*', word_mul),
    BuiltinWord('/', word_div),
    BuiltinWord('.', word_print),
    BuiltinWord('cr', word_cr),
    BuiltinWord('dup', word_dup),
    BuiltinWord('ps', word_ps),
]

def forth_eval(exp):
    tokens = iter(exp)
    for token in tokens:
        # numbers
        if token.isdigit():
            push(int(token))
            continue

        # comments
        if token == '(':
            for t in tokens:
                if t == ')': break
            continue

        # word definitions
        if token == ':':
            name = next(tokens)
            body = []
            for t in tokens:
                if t == ';': break
                body.append(t)
            WORDS.insert(0, CompoundWord(name, body))
            continue

        # variable store
        if token == '!':
            word = pop()
            value = pop()
            word.value = value
            continue

        # variable fetch
        if token == '@':
            word = pop()
            value = word.value
            push(value)
            continue

        # constant / variable definitions
        if token.lower() in ['constant', 'variable']:
            name = next(tokens)
            WORDS.insert(0, VariableWord(name))
            continue

        # else must be calling a word
        for word in WORDS:
            if token.lower() == word.name:
                if isinstance(word, BuiltinWord):
                    word.func()
                elif isinstance(word, VariableWord):
                    push(word)
                else:
                    forth_eval(word.body)
                break
        else:
            raise RuntimeError('Invalid word')

while True:
    try:
        line = input('> ')
    except:
        print()
        break

    try:
        forth_eval(line.split())
        print('ok')
    except RuntimeError as e:
        print(e)
        pass
