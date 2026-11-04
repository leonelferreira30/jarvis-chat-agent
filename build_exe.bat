@echo off
setlocal
cd /d "%~dp0"
py -m pip install --upgrade pip
if errorlevel 1 goto failed
py -m pip install -r requirements.txt
if errorlevel 1 goto failed
py -m PyInstaller --noconfirm --clean --windowed --name JARVIS --collect-all keyring jarvis.py
if errorlevel 1 goto failed
py -m PyInstaller --noconfirm --onefile --console --name JARVIS-MCP jarvis_mcp.py
if errorlevel 1 goto failed
echo.
echo Build concluido.
echo Aplicativo: dist\JARVIS\JARVIS.exe
echo Servidor MCP para o Codex: dist\JARVIS-MCP.exe
pause
exit /b 0

:failed
echo.
echo Falha ao gerar os executaveis. Verifique a mensagem acima.
pause
exit /b 1
