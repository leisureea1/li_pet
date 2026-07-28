@echo off
echo Building Desktop Pet EXE...
pyinstaller --noconsole --onefile pet.py
echo Build finished! The executable is in the dist folder.
pause
