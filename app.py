#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Веб-приложение для учёта товаров секонд-хенда.
Замена Telegram боту — всё в браузере, работает с телефона.
"""

import os
import sys
import io
import logging
import base64
from functools import wraps
from io import BytesIO

from flask import (
    Flask, render_template, request, redirect, url_for, flash, session, jsonify
)
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# ---- Путь к корню приложения ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# На Render .env не обязателен — все переменные из Dashboard
load_dotenv(os.path.join(BASE_DIR, '.env'))

sys.path.insert(0, BASE_DIR)

from config import config
from db import db
from ai_helper import description_gen
from sheets import sheets_sync

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24).hex())
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# На Render не пишем в лог-файл, только в stdout
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# ───── ПАРОЛЬНАЯ ЗАЩИТА (простая) ─────
# Если в .env указан WEB_PASSWORD — сайт будет спрашивать пароль при входе
WEB_PASSWORD = os.getenv('WEB_PASSWORD', '')

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if WEB_PASSWORD and not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ───── СТРАНИЦА ВХОДА ─────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if not WEB_PASSWORD:
        return redirect(url_for('index'))
    if request.method == 'POST':
        if request.form.get('password') == WEB_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        flash('Неверный пароль', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# ───── ГЛАВНАЯ — СПИСОК ТОВАРОВ ─────
@app.route('/')
@login_required
def index():
    items = db.get_all_items()
    stats = db.get_statistics()
    return render_template('index.html', items=items, stats=stats)

# ───── СТАТИСТИКА ─────
@app.route('/stats')
@login_required
def stats():
    s = db.get_statistics()
    profit = s['total_sale'] - s['total_purchase']
    return render_template('stats.html', stats=s, profit=profit)

# ───── ДОБАВЛЕНИЕ ТОВАРА ─────
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_item():
    if request.method == 'POST':
        category = request.form.get('category', 'Другое')
        brand = request.form.get('brand', 'Неизвестный бренд') or 'Неизвестный бренд'
        size = request.form.get('size', 'Не указан') or 'Не указан'
        condition = request.form.get('condition', 'Хорошее') or 'Хорошее'
        purchase_price = float(request.form.get('purchase_price', 0) or 0)
        sale_price = float(request.form.get('sale_price', 0) or 0)

        # Сохраняем фото
        photo_file_id = ''
        image_bytes = None
        if 'photo' in request.files and request.files['photo'].filename:
            f = request.files['photo']
            filename = secure_filename(f.filename)
            ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'jpg'
            import uuid
            save_name = f"{uuid.uuid4().hex}.{ext}"
            save_path = os.path.join(UPLOAD_FOLDER, save_name)
            f.save(save_path)
            photo_file_id = f'/static/uploads/{save_name}'

            # Для AI — читаем байты
            with open(save_path, 'rb') as img_f:
                image_bytes = img_f.read()

        # AI описание
        desc = description_gen.generate_description(
            image_bytes=image_bytes,
            category=category, brand=brand, size=size,
            condition=condition, purchase_price=purchase_price,
            sale_price=sale_price,
        )

        # Сохраняем в БД
        item_id = db.add_item(
            category=category, brand=brand, size=size,
            condition=condition, purchase_price=purchase_price,
            sale_price=sale_price,
            photo_file_id=photo_file_id,
            description=desc,
        )

        # Синхронизация с Google Sheets
        if sheets_sync.is_available:
            try:
                item = db.get_item_by_id(item_id)
                if item:
                    sheets_sync.sync_add_item(item)
            except Exception:
                pass

        flash(f'✅ Товар #{item_id} добавлен!', 'success')
        return redirect(url_for('index'))

    return render_template('add.html',
        categories=config.CATEGORIES,
        conditions=config.CONDITIONS,
    )

# ───── КАРТОЧКА ТОВАРА ─────
@app.route('/item/<int:item_id>')
@login_required
def item_card(item_id):
    item = db.get_item_by_id(item_id)
    if not item:
        flash('Товар не найден', 'danger')
        return redirect(url_for('index'))
    return render_template('card.html',
        item=item, stages=config.STAGES, statuses=config.STATUSES,
    )

# ───── ОБНОВЛЕНИЕ СТАТУСА ─────
@app.route('/item/<int:item_id>/status', methods=['POST'])
@login_required
def update_status(item_id):
    status = request.form.get('status', '')
    if status in config.STATUSES:
        db.update_status(item_id, status)
        if sheets_sync.is_available:
            item = db.get_item_by_id(item_id)
            stage = item.get('stage', '') if item else ''
            sheets_sync.sync_status(item_id, status, stage)
        flash(f'Статус обновлён: {status}', 'success')
    return redirect(url_for('item_card', item_id=item_id))

# ───── ОБНОВЛЕНИЕ ЭТАПА ─────
@app.route('/item/<int:item_id>/stage', methods=['POST'])
@login_required
def update_stage(item_id):
    stage = request.form.get('stage', '')
    if stage in config.STAGES:
        db.update_stage(item_id, stage)
        if sheets_sync.is_available:
            sheets_sync.sync_status(item_id, db.get_item_by_id(item_id).get('status', ''), stage)
        flash(f'Этап обновлён: {stage}', 'success')
    return redirect(url_for('item_card', item_id=item_id))

# ───── ССЫЛКА AVITO ─────
@app.route('/item/<int:item_id>/avito', methods=['POST'])
@login_required
def update_avito(item_id):
    link = request.form.get('avito_link', '').strip()
    if link.startswith('http'):
        db.update_avito_link(item_id, link)
        if sheets_sync.is_available:
            sheets_sync.sync_avito(item_id, link)
        flash('Ссылка Avito сохранена!', 'success')
    else:
        flash('Ссылка должна начинаться с http', 'danger')
    return redirect(url_for('item_card', item_id=item_id))

# ───── РЕДАКТИРОВАНИЕ ОПИСАНИЯ ─────
@app.route('/item/<int:item_id>/description', methods=['POST'])
@login_required
def update_description(item_id):
    desc = request.form.get('description', '').strip()
    if desc:
        db.update_description(item_id, desc)
        flash('Описание обновлено!', 'success')
    return redirect(url_for('item_card', item_id=item_id))

# ───── ГЕНЕРАЦИЯ ОПИСАНИЯ ЧЕРЕЗ AI ─────
@app.route('/item/<int:item_id>/ai-generate', methods=['POST'])
@login_required
def ai_generate(item_id):
    item = db.get_item_by_id(item_id)
    if not item:
        flash('Товар не найден', 'danger')
        return redirect(url_for('index'))

    image_bytes = None
    photo = item.get('photo_file_id', '')
    if photo and photo.startswith('/static/'):
        try:
            with open(os.path.join(BASE_DIR, photo[1:]), 'rb') as f:
                image_bytes = f.read()
        except Exception:
            pass

    desc = description_gen.generate_description(
        image_bytes=image_bytes,
        category=item.get('category', ''),
        brand=item.get('brand', ''),
        size=item.get('size', ''),
        condition=item.get('condition', ''),
        purchase_price=item.get('purchase_price', 0),
        sale_price=item.get('sale_price', 0),
    )
    db.update_description(item_id, desc)
    flash('Описание сгенерировано AI!', 'success')
    return redirect(url_for('item_card', item_id=item_id))

# ───── УДАЛЕНИЕ ТОВАРА ─────
@app.route('/item/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_item(item_id):
    # Просто помечаем как списано
    db.update_status(item_id, 'Списано')
    flash(f'Товар #{item_id} списан', 'warning')
    return redirect(url_for('index'))

# ───── ЗАПУСК ─────
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    print(f"🌐 Веб-приложение для учёта секонд-хенда")
    print(f"   Открой в браузере: http://127.0.0.1:{port}")
    print(f"   Пароль: {'установлен' if WEB_PASSWORD else 'не требуется'}")
    print(f"   Google Sheets: {'✅' if sheets_sync.is_available else '❌ не подключена'}")
    print(f"   AI: {config.ai_label}")
    print(f"   Нажми Ctrl+C для остановки.")
    app.run(host='0.0.0.0', port=port, debug=debug)