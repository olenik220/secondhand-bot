@echo off
chcp 1251 > nul
title 🌐 Туннель для клиента — Учёт секонд-хенда

echo.
echo =======================================
echo    🌐 ТУННЕЛЬ ДЛЯ КЛИЕНТА
echo    Пробрасывает сайт в интернет
echo =======================================
echo.

:: Проверяем, запущен ли сервер
curl -s -o nul http://127.0.0.1:5000/ 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo  ⚠ Локальный сервер не запущен!
    echo     Сначала запусти run.bat
    pause
    exit /b 1
)

:: Проверяем ngrok
where ngrok >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  ⚠ ngrok не найден.
    echo.
    echo  Чтобы клиент мог заходить из любого места,
    echo  нужно установить ngrok:
    echo.
    echo  1. https://ngrok.com/download
    echo  2. Настроить: ngrok config add-authtoken ТОКЕН
    echo  3. Зарегистрироваться на ngrok.com (бесплатно)
    echo.
    echo  После установки запусти этот файл снова.
    pause
    exit /b 1
)

echo.
echo  🚀 Запускаю туннель для клиента...
echo  Ссылка будет готова через 5 секунд
echo.

:: Запускаем туннель
ngrok http 5000 --log=stdout

pause