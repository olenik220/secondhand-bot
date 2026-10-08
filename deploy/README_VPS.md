# 🚀 Как развернуть на VPS

## Купить VPS (Timeweb / Selectel / VDSina)

**Минимальный тариф:**
- 1 CPU, 512 MB-1 GB RAM, Ubuntu 22.04
- 150-300 ₽/месяц

После покупки тебе дадут:
- **IP-адрес** (например 123.45.67.89)
- **root-пароль** (доступ по SSH)

## Запустить одной командой

Подключись к серверу через SSH (на Windows — PuTTY или PowerShell):

```bash
ssh root@твой-ip-адрес
```

Введи пароль. Дальше выполни:

```bash
wget -O setup.sh https://raw.githubusercontent.com/olenik220/secondhand-bot/main/deploy/setup.sh
bash setup.sh
```

Скрипт спросит:
- `FLASK_SECRET_KEY` — придумай любую строку
- `WEB_PASSWORD` — придумай пароль для входа на сайт
- AI настройки — можно просто Enter, пропустятся
- **Домен или IP** — введи свой IP-адрес

Всё. Через 2-3 минуты сайт работает.

Открой в браузере: `http://твой-ip-адрес`

## Команды для управления

```bash
# Перезапустить
systemctl restart secondhand-bot

# Посмотреть логи
journalctl -u secondhand-bot -f

# Обновить код
cd /opt/secondhand-bot
git pull
systemctl restart secondhand-bot

# Поменять настройки
nano /opt/secondhand-bot/.env
systemctl restart secondhand-bot
```

## HTTPS домен (по желанию)

Купи домен (например secondhand.ru), в DNS сделай A-запись на IP сервера.
Запусти скрипт повторно, указав домен — он сам выпустит бесплатный SSL-сертификат.