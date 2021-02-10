import tempfile
from tkinter import *
from tkinter import ttk

from asm import assemble


class Gui:

    def __init__(self, window):

        window.title("Bronzebeard - Riscv Toolset")

        frame = ttk.Frame(window, padding="3 3 12 12")
        frame.grid(column=0, row=0, sticky=(N, W, E, S))
        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)

        sample_assembly = "addi x1 zero 2\naddi x2 zero 3\nadd x3 x1 x2 \n"
        self.text_box = Text(frame)
        self.text_box.insert(END, sample_assembly)
        self.text_box.focus()
        self.text_box.grid(column=0, row=0)

        btn_assemble = Button(frame, text="Assemble", command=self.assemble_input)
        btn_assemble.grid(column=0, row=1)

        for child in frame.winfo_children():
            child.grid_configure(padx=15, pady=15)

    def assemble_input(self, *args):
        assembly = self.text_box.get(0.0, END)
        program = assemble(assembly)
        with tempfile.TemporaryFile() as f:
            f.write(program)


if __name__ == "__main__":

    window = Tk()
    Gui(window)
    window.mainloop()
