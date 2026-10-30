@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto usar_python
py -3 app.py --open-browser
goto fim
:usar_python
where python >nul 2>nul
if errorlevel 1 goto sem_python
python app.py --open-browser
goto fim
:sem_python
echo Para iniciar, instale o Python 3.12 ou mais recente de https://www.python.org/downloads/windows/
echo Na instalacao, marque "Add Python to PATH". Depois abra este arquivo novamente.
:fim
echo.
echo Se houve um erro acima, envie uma foto desta janela para receber ajuda.
pause
