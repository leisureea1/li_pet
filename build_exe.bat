@echo off
echo Building Python executable...
pyinstaller --noconsole --onedir --exclude-module sentencepiece --exclude-module paddlenlp --hidden-import edge_tts --hidden-import pygame --hidden-import pkg_resources.py2_warn --hidden-import pycaw --hidden-import comtypes --hidden-import pandas --hidden-import openpyxl --hidden-import xlrd --add-data "character_fullbody.png;." --add-data "pat_hand_nobg.png;." --collect-data Cython pet.py
pause
