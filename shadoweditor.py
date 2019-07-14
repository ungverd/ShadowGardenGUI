import sys
import os
from shutil import copyfile
import serial
from enum import Enum
import wave
import csv

import Usbhost

from tkinter import filedialog
from tkinter import *
import tkinter.ttk as ttk

from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

FRAMERATE = 48000
SAMPLEWIDTH = 2 #2 bytes == 16 bits

master = Tk()
master.geometry('500x600')
tree=ttk.Treeview(master)

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
        self.entryForDest = Entry(master)
        self.entryForDest.bind('<Return>', firstCallback)
        self.selectDestB = Button(master, text="Выбрать папку для записи музыки", width=30, command=selectDestFolder)
        self.enterDestLabel = Label(master, text="\nИЛИ\nВведите путь к папке", justify=CENTER)
        self.notValidDestLabel = Label(master, text="Некорректный путь", foreground='#EE0000')
        self.initWidgets = [self.selectDestB, self.enterDestLabel, self.entryForDest]

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
    mp3 = 1
    oog = 2
    goodWav = 3
    badWav = 4
    notMusic = 5

def classifyFile(path):
    if len(path) >= 4:
        if path[-4:] == ".mp3":
            return FileFormat.mp3
        if path[-4:] == ".oog":
            return FileFormat.oog
        elif path[-4:] == ".wav":
            try:
                sound = wave.open(path, mode='rb')
                if sound.getsampwidth() == SAMPLEWIDTH and sound.getframerate() == FRAMERATE:
                    return FileFormat.goodWav
                else:
                    return FileFormat.badWav
            except wave.Error:
                return FileFormat.notMusic
    return FileFormat.notMusic


def convert(src, dst):
    res = classifyFile(src)
    if res in (FileFormat.mp3, FileFormat.oog, FileFormat.badWav):
        try:
            if res == FileFormat.mp3:
                sound = AudioSegment.from_mp3(src)
            elif res == FileFormat.oog:
                sound = AudioSegment.from_ogg(src)
            elif res == FileFormat.badWav:
                sound = AudioSegment.from_wav(src)
            sound = sound.set_frame_rate(FRAMERATE)
            sound = sound.set_sample_width(SAMPLEWIDTH)
            sound.export(dst, format="wav")
            return True
        except CouldntDecodeError as e:
            print('Error during processing file %s: %s' % (src, e))
    elif res == FileFormat.goodWav:
        if src != dst:
            copyfile(src, dst)
        return True

def copyOnly(src, dst):
    if classifyFile(src) == FileFormat.goodWav:
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
    folder = enterSourceObj.tree.insert("", 1, "", text=basename)
    for filename in os.listdir(src_path):
        src = os.path.join(src_path, filename)
        dst = os.path.join(full_dest, filename)
        if func(src, dst):
            enterSourceObj.tree.insert(folder, "end", "", text=filename[:-4] + ".wav")
    
    convertCopyObj.end()
    enterSourceObj.begin()
    enterSourceObj.add(enterSourceObj.tree)

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
            if res == FileFormat.goodWav:
                convertCopyObj.currentfolder.insert("", 1, "", text=filename)
                haveToCopy = True
            elif res == FileFormat.notMusic:
                convertCopyObj.currentfolder.insert("", 1, "", text=filename, tags = ('grey',))
            else:
                convertCopyObj.currentfolder.insert("", 1, "", text=filename, tags = ('red',))
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

def applyCards(names):
    port = Usbhost.get_device_port()
    with serial.Serial(port, baudrate=115200, timeout=0.1) as ser:
        with open(os.path.join(master.dest, 'folders.csv'), 'w', newline='') as csvfile:
            spamwriter = csv.writer(csvfile, dialect='excel')
            previous = ""
            for name in names:
                done = False
                while not done:
                    answer = ser.readall().decode('utf-8').split('\r')
                    for line in answer:
                        if line.startswith("Card: ") and line != previous:
                            previous = line
                            words = line.split(" ")
                            spamwriter.writerow([words[1], words[2], name])
                            done = True

def selectDestFolder():
    master.dest =  filedialog.askdirectory(initialdir = "/")
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