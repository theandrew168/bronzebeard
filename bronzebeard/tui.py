# curses-based TUI will go here

import curses
from curses.textpad import Textbox, rectangle
import time


def main(win):
    lines, cols = curses.LINES - 1, curses.COLS - 1
    editor_height = int(lines * 0.6)
    editor_width = cols
    editor = curses.newwin(editor_height - 1, editor_width - 1, 1, 1)
    rectangle(win, 0, 0, editor_height, editor_width)

    terminal_height = lines - editor_height
    terminal_width = cols
    terminal = curses.newwin(terminal_height - 1, terminal_width - 1, editor_height + 1, 1)
    rectangle(win, editor_height + 1, 0, lines - 1, cols)

    win.addstr( 1, 1, 'rcu_init:')
    win.addstr( 2, 1, '    # load RCU base addr into t0')
    win.addstr( 3, 1, '    lui t0 %hi(RCU_BASE_ADDR)')
    win.addstr( 4, 1, '    addi t0 t0 %lo(RCU_BASE_ADDR)')
    win.addstr( 5, 1, '    addi t0 t0 RCU_APB2EN_OFFSET')

    win.addstr( 7, 1, '    # load ABP2EN config into t1')
    win.addstr( 8, 1, '    lw t1 t0 0')

    win.addstr(10, 1, '    # prepare the GPIO C bit')
    win.addstr(11, 1, '    addi t2 zero 1')
    win.addstr(12, 1, '    slli t2 t2 4')


    win.addstr(15, 1, '--- Miniterm on COM3  115200,8,N,1 ---')
    win.addstr(16, 1, '--- Quit: Ctrl+] | Menu: Ctrl+T | Help: Ctrl+T followed by Ctrl+H ---')
    win.addstr(17, 1, ': pled rled bled ;')
    win.addstr(18, 1, ' ok')
    win.addstr(19, 1, 'pled')
    win.addstr(20, 1, ' ok')

    win.refresh()
    win.getkey()


if __name__ == '__main__':
    curses.wrapper(main)
