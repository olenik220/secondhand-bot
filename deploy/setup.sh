#!/bin/bash
set -e

echo "========================================"
echo "  🤖 УСТАНОВКА БОТА СЕКОНД-ХЕНД"
echo "  github.com/olenik220/secondhand-bot"
echo "========================================"
echo ""

# ───── Цвета ─────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
done_s() { echo -e "${GREEN}[DONE]${NC} $1"; }

# ───── 1. Обновление системы ─────
info "Обновление системы..."
apt-get update -y && apt-get upgrade -y -q
done_s "Система обновлена"

# ───── 2. Установка пакетов ─────
info "Установка Python, nginx, certbot..."
apt-get install -y -q python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git
done_s "Пакеты установлены"

# ───── 3. Клонирование репозитория ─────
APP_DIR="/opt/secondhand-bot"
if [ -d "$APP_DIR" ]; then
    warn "Папка $APP_DIR уже существует. Обновляю..."
    cd $APP_DIR && git pull
else
    info "Клонирование репозитория..."
    git clone https://github.com/olenik220/secondhand-bot.git $APP_DIR
fi
done_s "Код загружен в $APP_DIR"

# ───── 4. Виртуальное окружение ─────
cd $APP_DIR
info "Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
done_s "Зависимости установлены"

# ───── 5. Настройка .env ─────
if [ ! -f "$APP_DIR/.env" ]; then
    info "Создание .env файла..."
    echo "⏳ Сейчас нужно будет ввести настройки."
    read -p "  Введите FLASK_SECRET_KEY (любое слово): " FLASK_SECRET_KEY
    read -p "  Введите пароль для входа на сайт (WEB_PASSWORD): " WEB_PASSWORD
    read -p "  AI провайдер (yandex / пусто для шаблона): " AI_PROVIDER
    read -p "  YandexGPT API Key (если нужно): " YANDEX_API_KEY
    read -p "  Yandex Folder ID (если нужно): " YANDEX_FOLDER_ID

    cat > "$APP_DIR/.env" << EOF
FLASK_SECRET_KEY=${FLASK_SECRET_KEY:-change-me}
WEB_PASSWORD=${WEB_PASSWORD:-}
AI_PROVIDER=${AI_PROVIDER:-}
YANDEX_API_KEY=${YANDEX_API_KEY:-}
YANDEX_FOLDER_ID=${YANDEX_FOLDER_ID:-}
EOF
    done_s ".env создан"
else
    warn ".env уже существует, пропускаю"
fi

# ───── 6. Создание systemd сервиса gunicorn ─────
SERVICE_FILE="/etc/systemd/system/secondhand-bot.service"
info "Настройка автозапуска..."

cat > $SERVICE_FILE << 'SERVICEEOF'
[Unit]
Description=SecondHand Bot Web App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/secondhand-bot
Environment="PATH=/opt/secondhand-bot/venv/bin"
ExecStart=/opt/secondhand-bot/venv/bin/gunicorn wsgi:application \
    --workers 2 \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/secondhand-bot/access.log \
    --error-logfile /var/log/secondhand-bot/error.log
Restart=always

[Install]
WantedBy=multi-user.target
SERVICEEOF

mkdir -p /var/log/secondhand-bot
chown -R www-data:www-data /var/log/secondhand-bot
chown -R www-data:www-data $APP_DIR

systemctl daemon-reload
systemctl enable secondhand-bot
systemctl start secondhand-bot
done_s "Сервис gunicorn запущен"

# ───── 7. Настройка nginx ─────
info "Настройка nginx..."
read -p "  Введите домен или IP сервера (например 123.123.123.123): " SERVER_NAME

# Если домена нет, используем IP
if [ -z "$SERVER_NAME" ]; then
    SERVER_NAME="_"
fi

NGINX_CONF="/etc/nginx/sites-enabled/secondhand-bot"

cat > $NGINX_CONF << NGINXEOF
server {
    listen 80;
    server_name ${SERVER_NAME};

    client_max_body_size 16M;

    location /static/ {
        alias /opt/secondhand-bot/static/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINXEOF

rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
done_s "Nginx настроен"

# ───── 8. HTTPS (Let's Encrypt) ─────
if [ "$SERVER_NAME" != "_" ]; then
    info "Попытка выпустить SSL-сертификат..."
    certbot --nginx -d $SERVER_NAME --non-interactive --agree-tos --email admin@$SERVER_NAME || true
    if systemctl is-active --quiet certbot.timer; then
        done_s "Автообновление сертификата включено"
    fi
fi

# ───── 9. Финальная проверка ─────
echo ""
echo "========================================"
echo "  ✅ УСТАНОВКА ЗАВЕРШЕНА!"
echo "========================================"
echo ""
echo "  Сайт: http://${SERVER_NAME}"
echo "  Путь: $APP_DIR"
echo ""
echo "  Команды для управления:"
echo "    Перезапуск: systemctl restart secondhand-bot"
echo "    Логи:      journalctl -u secondhand-bot -f"
echo "    Обновление: cd $APP_DIR && git pull"
echo "               systemctl restart secondhand-bot"
echo ""
echo "  Настройки: nano $APP_DIR/.env"
echo "========================================"