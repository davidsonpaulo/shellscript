@echo off
chcp 65001 >nul
title Editor WhatsApp - Launcher

:loop

echo ================================================
echo    Editor de Agendamentos WhatsApp
echo ================================================
echo.

python.exe "C:\Users\thisi\Desktop\celsomferramentas.com.br\python\lembretes_whatsapp\editor.py"

if %errorlevel% equ 42 (
    echo.
    echo [INFO] Reiniciando o editor...
    timeout /t 2 >nul
    cls
    goto loop
)

if %errorlevel% equ 0 (
    echo.
    echo Programa encerrado normalmente.
    pause
    exit
) else (
    echo.
    echo Programa encerrado com erro (código %errorlevel%).
    pause
    exit
)