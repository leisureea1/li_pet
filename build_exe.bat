@echo off
echo Building Python executable...
pyinstaller --noconsole --onefile --hidden-import edge_tts --hidden-import pygame --hidden-import pkg_resources.py2_warn --hidden-import pycaw --hidden-import comtypes --add-data "character_fullbody.png;." --add-data "pat_hand_nobg.png;." pet.py
pause
