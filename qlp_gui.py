#!/usr/bin/env python
# Python 2.7.14

import Tkinter
import tkFileDialog
import os
import sys
import qlp_plot

data_dir = 'data'
file_type = [('pointing log data', '*.txt')]

button_width = 10


class MainFrame(Tkinter.Frame):
    def __init__(self, master=None):
        Tkinter.Frame.__init__(self, master)
        self.master.title('Pointing Monitor')

        f1 = Tkinter.Frame(self)
        button_qlp = Tkinter.Button(f1, text='qlp',
                                    width=button_width)
        button_qlp.bind('<1>', self.quick_look_plot)
        button_qlp.pack()
        f1.pack()

        f2 = Tkinter.Frame(self)
        button_exit = Tkinter.Button(f2, text='Exit',
                                     width=button_width)
        button_exit.bind('<1>', self.exit)
        button_exit.pack(side=Tkinter.LEFT)
        f2.pack()

    @staticmethod
    def quick_look_plot(event):
        qlp = QuickLookPlot()

    @staticmethod
    def exit(event):
        sys.exit()


class QuickLookPlot:
    def __init__(self):
        self.file_path = ''

        self.win = Tkinter.Toplevel()
        self.win.title('Quick Look')

        f1 = Tkinter.Frame(self.win)
        button_list = Tkinter.Button(f1, text='List',
                                     width=button_width)
        button_list.bind('<1>', self.select_file)
        button_list.pack()
        l1 = Tkinter.Label(f1, text='File name: ')
        l1.pack(side=Tkinter.LEFT)
        self.buff = Tkinter.StringVar()
        self.buff.set('')
        l2 = Tkinter.Label(f1, textvariable=self.buff, width=18,
                           relief=Tkinter.SUNKEN)
        l2.pack(side=Tkinter.LEFT)
        f1.pack()

        f2 = Tkinter.Frame(self.win)
        button_plot = Tkinter.Button(f2, text='Plot',
                                     width=button_width)
        button_plot.bind('<1>', self.plot)
        button_plot.pack(side=Tkinter.LEFT)
        button_close = Tkinter.Button(f2, text='Close',
                                      width=button_width)
        button_close.bind('<1>', self.close)
        button_close.pack(side=Tkinter.LEFT)
        f2.pack()

    def select_file(self, event):
        self.file_path = tkFileDialog.askopenfilename(filetypes=file_type,
                                                      initialdir=data_dir)
        self.buff.set(os.path.basename(self.file_path))

    def plot(self, event):
        if self.file_path != '':
            qlp = qlp_plot.Pointing(self.file_path)
            qlp.read_data()
            qlp.add_params()
            qlp.select_array()
            qlp.plot_data()
            qlp.show_figure_gui()

    def close(self, event):
        self.win.destroy()


if __name__ == '__main__':
    f = MainFrame()
    f.pack()
    f.mainloop()
