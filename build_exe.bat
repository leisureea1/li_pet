@echo off
echo Building Python executable...
pyinstaller --noconsole --onefile --hidden-import edge_tts --hidden-import pygame --hidden-import pkg_resources.py2_warn --hidden-import pycaw --hidden-import comtypes --hidden-import pandas --hidden-import openpyxl --hidden-import xlrd --add-data "character_fullbody.png;." --add-data "pat_hand_nobg.png;." --collect-data Cython --collect-all paddle --collect-all paddleocr pet.py
pause
