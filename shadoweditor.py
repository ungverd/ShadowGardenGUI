import sys
import os
from shutil import copyfile
from enum import Enum
import wave
import csv
import subprocess

from tkinter import filedialog
from tkinter import *
import tkinter.ttk as ttk

import serial

import Usbhost


FRAMERATE = 48000
SAMPLEWIDTH = 2 #2 bytes == 16 bits
SAMPLEFMT = 's16' #ffmpeg format

master = Tk()
master.geometry('500x600')
tree=ttk.Treeview(master)
tree.tag_configure('active', foreground='#FFFFFF', background='#1111FF')

class WindowState:
    initWidgets = []
    nowWidgets = []

    def begin(self):
        for widget in self.initWidgets:
            widget.pack()
        self.nowWidgets += self.initWidgets

    def end(self):
        for widget in self.nowWidgets:
            widget.pack_forget()
        self.nowWidgets = []

    def add(self, widget):
        widget.pack()
        self.nowWidgets.append(widget)

    def addTop(self, widget):
        widget.pack()
        self.nowWidgets = [widget] + self.nowWidgets


class EnterDest(WindowState):
    def __init__(self):
        self.createDestB = Button(master, text="Создать папку для записи музыки", width=30, command=createDestFolder)
        self.entryForDest = Entry(master)
        self.entryForDest.bind('<Return>', firstCallback)
        self.selectDestB = Button(master, text="Выбрать папку для записи музыки", width=30, command=selectDestFolder)
        self.enterDestLabel = Label(master, text="\nИЛИ\nВведите путь к папке", justify=CENTER)
        self.notValidDestLabel = Label(master, text="Некорректный путь", foreground='#EE0000')
        self.initWidgets = [self.createDestB, self.selectDestB, self.enterDestLabel, self.entryForDest]

    def begin(self):
        WindowState.begin(self)
        self.entryForDest.focus_set()

class EnterSource(WindowState):
    def __init__(self):
        self.entryForFolder = Entry(master)
        self.entryForFolder.bind('<Return>', callback)
        self.selectFolderB = Button(master, text="Выбрать исходную папку с музыкой", width=30, command=selectFolder)
        self.enterPathLabel = Label(master, text="\nИЛИ\nВведите путь к папке", justify=CENTER)
        self.notValidPathLabel = Label(master, text="Некорректный путь", foreground='#EE0000')
        self.tree = tree
        self.writeMusicB = Button(master, text='Соотнести музыку с карточками', width=30, command=applyCards)
        self.initWidgets = [self.selectFolderB, self.enterPathLabel, self.entryForFolder]

    def begin(self):
        WindowState.begin(self)
        self.entryForFolder.focus_set()

    def end(self):
        WindowState.end(self)
        self.entryForFolder.delete(0, 'end')

    def clearField(self):
        self.entryForFolder.delete(0, 'end')

class WriteMusic(WindowState):
    def __init__(self):
        self.folder_names = []
        self.folders_in_tree = []
        self.tree = tree
        self.initWidgets = [tree]

class ConvertCopy(WindowState):
    def __init__(self):
        self.currentfolder=ttk.Treeview(master)
        self.currentfolder.tag_configure('red', foreground='#EE0000')
        self.currentfolder.tag_configure('grey', foreground='#888888')
        self.convB = Button(master, text="конвертировать", width=15, command=lambda : convertOrCopy(convert))
        self.copyB = Button(master, text="копировать только подходящие", width=30, command=lambda : convertOrCopy(copyOnly))
        self.backB = Button(master, text="назад", width=10, command=back)
        self.convertOrCopyLabel = Label(master, text="Есть файлы в неподходящем формате (выделены красным). Конвертировать?")
        self.initWidgets = [self.backB, self.currentfolder]

    def end(self):
        WindowState.end(self)
        self.currentfolder.delete(*self.currentfolder.get_children())



class FileFormat(Enum):
    notMusic = 1
    good = 2
    bad = 3

def classifyFile(path):
    if len(path) >= 4:
        if path[-4:] in (".mp3", ".oog"):
            return FileFormat.bad
        elif path[-4:] == ".wav":
            try:
                sound = wave.open(path, mode='rb')
                if sound.getsampwidth() == SAMPLEWIDTH and sound.getframerate() == FRAMERATE:
                    return FileFormat.good
                else:
                    return FileFormat.bad
            except wave.Error:
                return FileFormat.notMusic
    return FileFormat.notMusic


def convert(src, dst):
    res = classifyFile(src)
    if res == FileFormat.good:
        if src != dst:
            copyfile(src, dst)
        return True
    elif res == FileFormat.bad:
        code = subprocess.call('ffmpeg -i "%s" -ar %d -sample_fmt %s "%s"' % (src, FRAMERATE, SAMPLEFMT, dst), shell=True)
        if code == 0:
            return True
        else:
            print ("Error converting file %s" % src)
            return False

def copyOnly(src, dst):
    if classifyFile(src) == FileFormat.good:
        if src != dst:
            copyfile(src, dst)
        return True


def convertOrCopy(func):
    src_path = master.path
    basename = os.path.basename(src_path)
    full_dest = os.path.join(master.dest, basename)
    if not os.path.isdir(full_dest):
        os.mkdir(full_dest)
    else:
        i = 1
        new_name = full_dest + str(i)
        while os.path.isdir(new_name):
            i += 1
            new_name = full_dest + str(i)
        os.mkdir(new_name)
        full_dest = new_name
        basename = os.path.basename(full_dest)
    writeMusicObj.folder_names.append(basename)
    folder = enterSourceObj.tree.insert("", 'end', text=basename)
    writeMusicObj.folders_in_tree.append(folder)
    for filename in os.listdir(src_path):
        src = os.path.join(src_path, filename)
        dst_name = filename[:-4] + ".wav"
        dst = os.path.join(full_dest, dst_name)
        if func(src, dst):
            enterSourceObj.tree.insert(folder, "end", text=dst_name)

    convertCopyObj.end()
    enterSourceObj.begin()
    enterSourceObj.add(enterSourceObj.tree)
    enterSourceObj.add(enterSourceObj.writeMusicB)

def back():
    convertCopyObj.end()
    enterSourceObj.begin()

def callback(event):
    master.path = enterSourceObj.entryForFolder.get()
    doAfterEnterPath()

def firstCallback(event):
    dest = enterDestObj.entryForDest.get()
    if os.path.isdir(dest):
        master.dest = dest
        doAfterSelectDest()
    else:
        enterDestObj.entryForDest.delete(0, 'end')
        enterDestObj.add(enterDestObj.notValidDestLabel)

def doAfterEnterPath():
    haveToConvert = False
    haveToCopy = False
    try:
        for filename in os.listdir(master.path):
            src = os.path.join(master.path, filename)
            res = classifyFile(src)
            if res == FileFormat.good:
                convertCopyObj.currentfolder.insert("", 'end', text=filename)
                haveToCopy = True
            elif res == FileFormat.notMusic:
                convertCopyObj.currentfolder.insert("", 'end', text=filename, tags = ('grey',))
            else:
                convertCopyObj.currentfolder.insert("", 'end', text=filename, tags = ('red',))
                haveToConvert = True

        enterSourceObj.end()

        if haveToConvert:
            convertCopyObj.addTop(convertCopyObj.convertOrCopyLabel)
            convertCopyObj.addTop(convertCopyObj.convB)
        if haveToCopy:
            convertCopyObj.addTop(convertCopyObj.copyB)

        convertCopyObj.begin()

    except (FileNotFoundError, OSError):
        enterSourceObj.add(enterSourceObj.notValidPathLabel)
        enterSourceObj.clearField()

def selectFolder():
    master.path =  filedialog.askdirectory(initialdir = "/")
    doAfterEnterPath()

def applyCards():
    enterSourceObj.end()
    writeMusicObj.begin()
    gen = contextGen()
    gen.send(None)
    master.after_idle(recursive, gen, 0)


def recursive(gen, i):
    res = gen.send(i)
    if i < len(writeMusicObj.folder_names):
        if res:
            master.after_idle(recursive, gen, i+1)
        else:
            master.after_idle(recursive, gen, i)

def contextGen():
    tree = writeMusicObj.tree
    names = writeMusicObj.folder_names
    folders = writeMusicObj.folders_in_tree
    port = Usbhost.get_device_port()
    with serial.Serial(port, baudrate=115200, timeout=0.1) as ser:
        with open(os.path.join(master.dest, 'folders.csv'), 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, dialect='excel')
            previous = ""
            while True:
                i = yield(True)
                if i > 0:
                    name = names[i-1]
                    folder = folders[i-1]

                    done = False
                    while not done:
                        answer = ser.readall().decode('utf-8').split('\r')
                        _ = yield(False)
                        for line in answer:
                            if line.startswith("Card: ") and line != previous:
                                previous = line
                                words = line.split(" ")
                                writer.writerow([words[1], words[2], name])
                                done = True

                    tree.item(folder, tags=())
                if i < len(names):
                    tree.item(folders[i], tags=('active'))
                
                
def selectDestFolder():
    master.dest =  filedialog.askdirectory(initialdir = "/")
    doAfterSelectDest()

def createDestFolder():
    cur_path = os.getcwd()
    full_path = os.path.join(cur_path, "new")
    if not os.path.isdir(full_path):
        os.mkdir(full_path)
    else:
        i = 1
        new_name = full_path + str(i)
        while os.path.isdir(new_name):
            i += 1
            new_name = full_path + str(i)
        os.mkdir(new_name)
        full_path = new_name
    master.dest = full_path
    doAfterSelectDest()

def doAfterSelectDest():
    enterDestObj.end()
    enterSourceObj.begin()


######################################

enterDestObj = EnterDest()
enterSourceObj = EnterSource()
writeMusicObj = WriteMusic()
convertCopyObj = ConvertCopy()


enterDestObj.begin()
mainloop()
