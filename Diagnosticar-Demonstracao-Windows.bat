@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto usar_python
py -3 diagnostico.py
goto fim
:usar_python
where python >nul 2>nul
if errorlevel 1 goto sem_python
python diagnostico.py
goto fim
:sem_python
echo Python nao encontrado. Instale Python 3.12 ou mais recente para iniciar o sistema.
:fim
echo.
echo Envie uma foto desta janela ou o arquivo data/diagnostico-demonstracao.txt.
pause
