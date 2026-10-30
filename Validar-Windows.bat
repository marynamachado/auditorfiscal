@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto usar_python
py -3 validar_ambiente.py
goto fim
:usar_python
python validar_ambiente.py
:fim
echo.
echo Guarde o relatorio data/validacao-tecnica.json. Este teste usa somente dados ficticios.
pause
