title Lembretes WhatsApp - Launcher

:loop

echo ================================================
echo    Editor de Agendamentos WhatsApp
echo ================================================
echo.

python.exe "C:\Users\thisi\Desktop\celsomferramentas.com.br\python\lembretes_whatsapp\main.py"

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