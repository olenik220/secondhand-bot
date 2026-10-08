#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Vova40 — учёт секонд-хенда. Локальный сервер.
"""

import os, sys, uuid, logging, socket
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))
sys.path.insert(0, BASE_DIR)

from config import config
from db import db, WAREHOUSES
from ai_helper import description_gen
from sheets import sheets_sync

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24).hex())
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
for w in WAREHOUSES:
    os.makedirs(os.path.join(UPLOAD_FOLDER, w['id']), exist_ok=True)

WEB_PASSWORD = os.getenv('WEB_PASSWORD', '')
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

def login_required(f):
    @wraps(f)
    def d(*a, **kw):
        if WEB_PASSWORD and not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*a, **kw)
    return d

@app.route('/login', methods=['GET', 'POST'])
def login():
    if not WEB_PASSWORD:
        return redirect(url_for('warehouse_choice'))
    if request.method == 'POST':
        if request.form.get('password') == WEB_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('warehouse_choice'))
        flash('Неверный пароль', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# ───── ВЫБОР СКЛАДА ─────
@app.route('/')
@login_required
def warehouse_choice():
    return render_template('warehouses.html', warehouses=WAREHOUSES)

# ───── ТОВАРЫ ИЗ СКЛАДА ─────
@app.route('/warehouse/<wh_id>')
@login_required
def warehouse_items(wh_id):
    article = request.args.get('article', '').strip()
    items = db.get_items_by_warehouse(wh_id, article)
    wh_name = db.get_warehouse_name(wh_id)
    return render_template('warehouse_items.html',
        items=items, wh_id=wh_id, wh_name=wh_name, article=article)

# ───── ВЫБОР КАТЕГОРИИ ПЕРЕД ДОБАВЛЕНИЕМ ─────
@app.route('/add/<wh_id>', methods=['GET'])
@login_required
def choose_category(wh_id):
    return render_template('choose_category.html',
        wh_id=wh_id, categories=config.CATEGORIES)

# ───── ДОБАВЛЕНИЕ ТОВАРА ─────
@app.route('/add/<wh_id>/<category>', methods=['GET', 'POST'])
@login_required
def add_item(wh_id, category):
    if request.method == 'POST':
        article = request.form.get('article', '').strip()
        brand = request.form.get('brand', '').strip() or 'Неизвестный бренд'
        size = request.form.get('size', '').strip() or 'Не указан'
        condition = request.form.get('condition', 'Хорошее')
        purchase_price = float(request.form.get('purchase_price', 0) or 0)
        sale_price = float(request.form.get('sale_price', 0) or 0)
        photos = []
        image_bytes = None
        for i in range(10):
            key = f'photo_{i}'
            if key in request.files and request.files[key].filename:
                f = request.files[key]
                ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else 'jpg'
                name = f"{uuid.uuid4().hex}.{ext}"
                path = os.path.join(UPLOAD_FOLDER, wh_id, name)
                f.save(path)
                photos.append(f"/static/uploads/{wh_id}/{name}")
                if image_bytes is None:
                    with open(path, 'rb') as img_f:
                        image_bytes = img_f.read()
        desc = description_gen.generate_description(
            image_bytes=image_bytes, category=category, brand=brand, size=size,
            condition=condition, purchase_price=purchase_price, sale_price=sale_price)
        item_id = db.add_item(
            warehouse=wh_id, article=article, category=category, brand=brand,
            size=size, condition=condition, purchase_price=purchase_price,
            sale_price=sale_price, photos=photos, description=desc)
        flash(f'Товар #{item_id} добавлен!', 'success')
        return redirect(url_for('warehouse_items', wh_id=wh_id))
    return render_template('add.html',
        wh_id=wh_id, category=category, conditions=config.CONDITIONS)

# ───── КАРТОЧКА ТОВАРА ─────
@app.route('/item/<int:item_id>')
@login_required
def item_card(item_id):
    item = db.get_item_by_id(item_id)
    if not item:
        flash('Товар не найден', 'danger')
        return redirect(url_for('warehouse_choice'))
    wh_name = db.get_warehouse_name(item.get('warehouse', 'base'))
    photos = item.get('photos', '').split(',') if item.get('photos') else []
    return render_template('card.html',
        item=item, wh_name=wh_name, photos=photos,
        stages=config.STAGES, statuses=config.STATUSES,
        categories=config.CATEGORIES, conditions=config.CONDITIONS,
        warehouses=WAREHOUSES)

# ───── РЕДАКТИРОВАНИЕ ТОВАРА ─────
@app.route('/item/<int:item_id>/edit', methods=['POST'])
@login_required
def edit_item(item_id):
    brand = request.form.get('brand', '').strip() or 'Неизвестный бренд'
    size = request.form.get('size', '').strip() or 'Не указан'
    condition = request.form.get('condition', 'Хорошее')
    purchase_price = float(request.form.get('purchase_price', 0) or 0)
    sale_price = float(request.form.get('sale_price', 0) or 0)
    article = request.form.get('article', '').strip()
    warehouse = request.form.get('warehouse', 'base')
    description = request.form.get('description', '').strip()
    avito_link = request.form.get('avito_link', '').strip()
    item = db.get_item_by_id(item_id)
    old_photos = item.get('photos', '').split(',') if item and item.get('photos') else []
    photos = [p for p in old_photos if p.strip()]
    for i in range(10):
        key = f'photo_{i}'
        if key in request.files and request.files[key].filename:
            f = request.files[key]
            ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else 'jpg'
            name = f"{uuid.uuid4().hex}.{ext}"
            path = os.path.join(UPLOAD_FOLDER, warehouse, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            f.save(path)
            photos.append(f"/static/uploads/{warehouse}/{name}")
    db.update_item(item_id,
        brand=brand, size=size, condition=condition,
        purchase_price=purchase_price, sale_price=sale_price,
        article=article, warehouse=warehouse,
        description=description, avito_link=avito_link,
        photos=",".join(photos))
    flash('Товар обновлён!', 'success')
    return redirect(url_for('item_card', item_id=item_id))

# ───── СТАТУС ─────
@app.route('/item/<int:item_id>/status', methods=['POST'])
@login_required
def update_status(item_id):
    status = request.form.get('status', '')
    if status in config.STATUSES:
        db.update_status(item_id, status)
        flash(f'Статус: {status}', 'success')
    return redirect(url_for('item_card', item_id=item_id))

# ───── ЭТАП ─────
@app.route('/item/<int:item_id>/stage', methods=['POST'])
@login_required
def update_stage(item_id):
    stage = request.form.get('stage', '')
    if stage in config.STAGES:
        db.update_stage(item_id, stage)
        flash(f'Этап: {stage}', 'success')
    return redirect(url_for('item_card', item_id=item_id))

# ───── AI ─────
@app.route('/item/<int:item_id>/ai-generate', methods=['POST'])
@login_required
def ai_generate(item_id):
    item = db.get_item_by_id(item_id)
    if not item:
        flash('Товар не найден', 'danger')
        return redirect(url_for('warehouse_choice'))
    image_bytes = None
    photos = item.get('photos', '').split(',') if item.get('photos') else []
    if photos:
        try:
            with open(os.path.join(BASE_DIR, photos[0][1:]), 'rb') as f:
                image_bytes = f.read()
        except Exception:
            pass
    desc = description_gen.generate_description(
        image_bytes=image_bytes, category=item.get('category',''),
        brand=item.get('brand',''), size=item.get('size',''),
        condition=item.get('condition',''),
        purchase_price=item.get('purchase_price',0),
        sale_price=item.get('sale_price',0))
    db.update_description(item_id, desc)
    flash('Описание сгенерировано AI!', 'success')
    return redirect(url_for('item_card', item_id=item_id))

# ───── СПИСАТЬ ─────
@app.route('/item/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_item(item_id):
    db.update_status(item_id, 'Списано')
    flash('Товар списан', 'warning')
    return redirect(url_for('warehouse_choice'))

# ───── СТАТИСТИКА ─────
@app.route('/stats/<wh_id>')
@login_required
def stats(wh_id):
    s = db.get_statistics(wh_id)
    profit = s['total_sale'] - s['total_purchase']
    wh_name = db.get_warehouse_name(wh_id)
    return render_template('stats.html', stats=s, profit=profit, wh_name=wh_name)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    local_ip = '127.0.0.1'
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass
    print(f"40 Vova40 — учёт секонд-хенда")
    print(f"   На этом ПК:  http://127.0.0.1:{port}")
    print(f"   С телефона:  http://{local_ip}:{port}")
    print(f"   AI: {config.ai_label}")
    print(f"   Нажми Ctrl+C для остановки.")
    app.run(host='0.0.0.0', port=port, debug=debug)