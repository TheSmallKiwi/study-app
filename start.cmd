@echo off
setlocal
set "APP_DIR=%~dp0"

rem Stop any existing instance first
if exist "%APP_DIR%.lock" (
    echo.> "%APP_DIR%.stop"
    timeout /t 1 /nobreak >nul
)

rem Clean slate
if exist "%APP_DIR%.stop" del "%APP_DIR%.stop"

set "TOPIC=%~1"
if "%TOPIC%"=="" set "TOPIC=greek_letters"
start "Study App" pythonw "%APP_DIR%study_app.py" %TOPIC%
