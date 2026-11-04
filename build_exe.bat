@echo off
setlocal
cd /d "%~dp0"
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py -m PyInstaller --noconfirm --clean --windowed --name JARVIS --collect-all keyring jarvis.py
echo.
echo Build concluido. Execute dist\JARVIS\JARVIS.exe
pause
