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
DST = os.getcwd()

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
        except CouldntDecodeError:
            pass
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
    os.mkdir(basename)
    folder = tree.insert("", 1, "", text=basename)
    for filename in os.listdir(src_path):
        src = os.path.join(src_path, filename)
        dst = os.path.join(DST, basename, filename)
        if func(src, dst):
            tree.insert(folder, "end", "", text=filename[:-4] + ".wav")
    convB.pack_forget()
    copyB.pack_forget()
    backB.pack_forget()
    tree.pack()
    currentfolder.pack_forget()
    convertOrCopyLabel.pack_forget()
    selectFolderB.pack()
    enterPathLabel.pack()
    entryForFolder.pack()
    entryForFolder.focus_set()

def back():
    convB.pack_forget()
    copyB.pack_forget()
    backB.pack_forget()
    currentfolder.pack_forget()
    convertOrCopyLabel.pack_forget()
    selectFolderB.pack()
    enterPathLabel.pack()
    entryForFolder.pack()
    entryForFolder.focus_set()
    
def callback(event):
    master.path = entryForFolder.get()
    doAfterEnterPath()

def firstCallback(event):
    dest = entryForDest.get()
    if os.path.isdir(dest):
        master.dest = dest
        doAfterSelectDest()
    else:
        entryForDest.delete(0, 'end')
        notValidDestLabel.pack()
        InitialWindow.append(notValidDestLabel)

def doAfterEnterPath():
    notValidPathLabel.pack_forget()
    ChoiceWindow = [backB, currentfolder]
    haveToConvert = False
    haveToCopy = False
    currentfolder.delete(*currentfolder.get_children())
    try:
        for filename in os.listdir(master.path):
            src = os.path.join(master.path, filename)
            res = classifyFile(src)
            if res == FileFormat.goodWav:
                currentfolder.insert("", 1, "", text=filename)
                haveToCopy = True
            elif res == FileFormat.notMusic:
                currentfolder.insert("", 1, "", text=filename, tags = ('grey',))
            else:
                currentfolder.insert("", 1, "", text=filename, tags = ('red',))
                haveToConvert = True
                
        if haveToConvert:
            ChoiceWindow = [convertOrCopyLabel, convB] + ChoiceWindow
        if haveToCopy:
            ChoiceWindow = [copyB] + ChoiceWindow
            
        for widget in SelectFolderWindow:
            widget.pack_forget()
        for widget in ChoiceWindow:
            widget.pack()

    except (FileNotFoundError, OSError):
        notValidPathLabel.pack()
        SelectFolderWindow.append(notValidPathLabel)
    entryForFolder.delete(0, 'end')

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
    for widget in InitialWindow:
        widget.pack_forget()
    for widget in SelectFolderWindow:
        widget.pack()
    entryForFolder.focus_set()
    

######################################

master = Tk()
master.geometry('500x600')


currentfolder=ttk.Treeview(master)
currentfolder.tag_configure('red', foreground='#EE0000')
currentfolder.tag_configure('grey', foreground='#888888')

entryForFolder = Entry(master)
entryForFolder.bind('<Return>', callback)
selectFolderB = Button(master, text="Выбрать папку", width=15, command=selectFolder)
enterPathLabel = Label(master, text="\nИЛИ\nВведите путь к папке", justify=CENTER)
SelectFolderWindow = [selectFolderB, enterPathLabel, entryForFolder]

notValidPathLabel = Label(master, text="Некорректный путь", foreground='#EE0000')
convertOrCopyLabel = Label(master, text="Есть звуковые файлы в неподходящем формате, конвертировать?")

entryForDest = Entry(master)
entryForDest.bind('<Return>', firstCallback)
selectDestB = Button(master, text="Выбрать папку для записи музыки", width=30, command=selectDestFolder)
enterDestLabel = Label(master, text="\nИЛИ\nВведите путь к папке", justify=CENTER)
notValidDestLabel = Label(master, text="Некорректный путь", foreground='#EE0000')
InitialWindow = [selectDestB, enterDestLabel, entryForDest]


tree=ttk.Treeview(master)

convB = Button(master, text="конвертировать", width=15, command=lambda : convertOrCopy(convert))
copyB = Button(master, text="копировать только подходящие", width=30, command=lambda : convertOrCopy(copyOnly))
backB = Button(master, text="назад", width=10, command=back)
ChoiceWindow = [backB, currentfolder]

WriteWindow = [tree]

########################################

for widget in InitialWindow:
    widget.pack()
entryForDest.focus_set()

mainloop()
