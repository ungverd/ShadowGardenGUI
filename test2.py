import random
import time
import csv

from tkinter import filedialog
from tkinter import *
import tkinter.ttk as ttk

def applyCard(i, folders, g):
    
    folder = folders[i]
    tree.item(folder, tags=('active'))
    if i > 0:
        tree.item(folders[i-1], tags=())
    if i < len(folders)-1:
        g.send(folder)
        tree.after_idle(applyCard, i+1, folders, g)

def c():
    g = gen()
    g.send(None)
    tree.after_idle(applyCard, 0, folders, g)

def gen():
    a = yield()
    with open('folders.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, dialect='excel')
        while True:
            time.sleep(0.5)
            writer.writerow([str(a)])
            a = yield()


master = Tk()
master.geometry('500x600')
tree=ttk.Treeview(master)
tree.tag_configure('active', foreground='#FFFFFF', background='#1111FF')
folders = []
for i in range(10):
    f = tree.insert("", 0, text=str(i)*10)
    folders.append(f)
tree.pack()

b = Button(master, text="xxx", command=c)
b.pack()

mainloop()


