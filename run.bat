@echo off
chcp 1251 > nul
title 🤖 Учёт секонд-хенда — Локальный сервер

echo.
echo =======================================
echo    🤖 СЕКОНД-ХЕНД: ЛОКАЛЬНЫЙ СЕРВЕР
echo =======================================
echo.

:: Определяем свой IP в локальной сети
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "127.0.0.1"') do (
    set IP=%%a
    goto :gotip
)
:gotip
set IP=%IP: =%

if "%IP%"=="" set IP=127.0.0.1

echo  Локальный IP: %IP%
echo  Порт: 5000
echo.
echo  📱 Открой на телефоне:
echo     http://%IP%:5000
echo.
echo  🔒 Закрыть окно — остановить сервер.
echo.

:: Проверяем .env
if not exist ".env" (
    echo  ⚠ Файл настроек не найден.
    echo     Создаю базовый .env...
    echo     WEB_PASSWORD=secondhand > .env
    echo     FLASK_SECRET_KEY=%random%%random%%random% >> .env
    echo     Пароль по умолчанию: secondhand
    echo.
)

:: Устанавливаем переменную PORT
set PORT=5000

:: Запускаем сервер
python app.py

pause