@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo DEMONSTRACAO - empresa e documentos ficticios, sem validade fiscal.
where py >nul 2>nul
if errorlevel 1 goto usar_python
py -3 demo.py --open-browser
goto fim
:usar_python
where python >nul 2>nul
if errorlevel 1 goto sem_python
python demo.py --open-browser
goto fim
:sem_python
echo Instale Python 3.12 ou mais recente de https://www.python.org/downloads/windows/
echo Marque "Add Python to PATH" na instalacao e abra este arquivo novamente.
:fim
echo.
echo Se ocorreu um erro, envie uma foto desta janela para receber ajuda.
pause
