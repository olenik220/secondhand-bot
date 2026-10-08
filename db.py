#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Локальная БД SQLite."""

import os, sqlite3, logging
from typing import Optional
from config import config, BASE_PATH

logger = logging.getLogger(__name__)

WAREHOUSES = [
    {"id": "base", "name": "База", "icon": "🏭"},
    {"id": "apartment", "name": "Квартира", "icon": "🏠"},
    {"id": "brother", "name": "Брат", "icon": "👤"},
    {"id": "coffee", "name": "Кофейня", "icon": "☕"},
]


class Database:
    def __init__(self):
        self.db_path = os.path.join(BASE_PATH, "data.db")
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    updated_at TEXT DEFAULT (datetime('now','localtime')),
                    warehouse TEXT NOT NULL DEFAULT 'base',
                    article TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT 'Другое',
                    brand TEXT NOT NULL DEFAULT 'Неизвестный бренд',
                    size TEXT NOT NULL DEFAULT 'Не указан',
                    condition TEXT NOT NULL DEFAULT 'Хорошее',
                    purchase_price REAL NOT NULL DEFAULT 0,
                    sale_price REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'В наличии',
                    stage TEXT NOT NULL DEFAULT '',
                    photos TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    avito_link TEXT NOT NULL DEFAULT '',
                    note TEXT NOT NULL DEFAULT ''
                );
            """)
            # Проверка и доавление новых колонок
            existing = set()
            cur = conn.execute("PRAGMA table_info(items)")
            for r in cur.fetchall():
                existing.add(r["name"])
            if "warehouse" not in existing:
                conn.execute("ALTER TABLE items ADD COLUMN warehouse TEXT NOT NULL DEFAULT 'base'")
            if "article" not in existing:
                conn.execute("ALTER TABLE items ADD COLUMN article TEXT NOT NULL DEFAULT ''")
            if "photos" not in existing:
                conn.execute("ALTER TABLE items ADD COLUMN photos TEXT NOT NULL DEFAULT ''")
            conn.commit()
        except Exception as e:
            logger.error(f"DB init: {e}")
            raise
        finally:
            conn.close()

    def add_item(self, warehouse="base", article="", category="Другое", brand="",
                 size="", condition="Хорошее", purchase_price=0, sale_price=0,
                 photos=None, description="", stage=""):
        if not stage:
            stage = "🛍️ Закупка"
        if photos is None:
            photos = []
        conn = self._get_conn()
        try:
            cur = conn.execute(
                """INSERT INTO items (warehouse,article,category,brand,size,condition,
                   purchase_price,sale_price,photos,description,status,stage)
                   VALUES (?,?,?,?,?,?,?,?,?,?,'В наличии',?)""",
                (warehouse, article, category, brand, size, condition,
                 purchase_price, sale_price, ",".join(photos), description, stage))
            conn.commit()
            return cur.lastrowid
        except Exception as e:
            logger.error(f"add_item: {e}")
            raise
        finally:
            conn.close()

    def update_item(self, item_id, **kw):
        allowed = {"warehouse","article","category","brand","size","condition",
                    "purchase_price","sale_price","description","avito_link","note","photos"}
        up = {k: v for k, v in kw.items() if k in allowed}
        if not up:
            return False
        conn = self._get_conn()
        try:
            clause = ", ".join(f"{k}=?" for k in up)
            conn.execute(f"UPDATE items SET {clause}, updated_at=datetime('now','localtime') WHERE id=?",
                         (*up.values(), item_id))
            conn.commit()
            return conn.total_changes > 0
        except Exception as e:
            logger.error(f"update_item: {e}")
            return False
        finally:
            conn.close()

    def update_status(self, item_id, status):
        conn = self._get_conn()
        try:
            conn.execute("UPDATE items SET status=?, updated_at=datetime('now','localtime') WHERE id=?", (status, item_id))
            conn.commit()
            return conn.total_changes > 0
        except Exception as e:
            logger.error(f"update_status: {e}")
            return False
        finally:
            conn.close()

    def update_stage(self, item_id, stage):
        conn = self._get_conn()
        try:
            conn.execute("UPDATE items SET stage=?, updated_at=datetime('now','localtime') WHERE id=?", (stage, item_id))
            conn.commit()
            if stage == "✅ Продажа завершена":
                conn.execute("UPDATE items SET status='Продано' WHERE id=? AND status!='Списано'", (item_id,))
            elif stage in ("📢 Опубликовано на Avito", "📢 На модерации Avito"):
                conn.execute("UPDATE items SET status='На Avito' WHERE id=?", (item_id,))
            elif stage in ("🛍️ Закупка", "📸 Фотосессия", "🤖 Генерация описания"):
                conn.execute("UPDATE items SET status='В наличии' WHERE id=? AND status!='Списано'", (item_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"update_stage: {e}")
            return False
        finally:
            conn.close()

    def update_avito_link(self, item_id, link):
        conn = self._get_conn()
        try:
            conn.execute("""UPDATE items SET avito_link=?, status='На Avito',
                stage='📢 Опубликовано на Avito', updated_at=datetime('now','localtime') WHERE id=?""", (link, item_id))
            conn.commit()
            return conn.total_changes > 0
        except Exception as e:
            return False
        finally:
            conn.close()

    def update_description(self, item_id, desc):
        conn = self._get_conn()
        try:
            conn.execute("UPDATE items SET description=?, updated_at=datetime('now','localtime') WHERE id=?", (desc, item_id))
            conn.commit()
            return conn.total_changes > 0
        except Exception as e:
            return False
        finally:
            conn.close()

    def get_items_by_warehouse(self, warehouse, article=""):
        conn = self._get_conn()
        try:
            if article:
                cur = conn.execute("SELECT * FROM items WHERE warehouse=? AND article LIKE ? ORDER BY id DESC",
                                   (warehouse, f"%{article}%"))
            else:
                cur = conn.execute("SELECT * FROM items WHERE warehouse=? ORDER BY id DESC", (warehouse,))
            return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            logger.error(f"get_items: {e}")
            return []
        finally:
            conn.close()

    def get_all_items(self):
        conn = self._get_conn()
        try:
            cur = conn.execute("SELECT * FROM items ORDER BY id DESC")
            return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            return []
        finally:
            conn.close()

    def get_item_by_id(self, item_id):
        conn = self._get_conn()
        try:
            cur = conn.execute("SELECT * FROM items WHERE id=?", (item_id,))
            r = cur.fetchone()
            return dict(r) if r else None
        except Exception as e:
            return None
        finally:
            conn.close()

    def get_statistics(self, warehouse=""):
        conn = self._get_conn()
        try:
            s = {"total": 0, "in_stock": 0, "on_avito": 0, "sold": 0,
                 "total_purchase": 0.0, "total_sale": 0.0, "by_category": {}, "by_stage": {}}
            q = "SELECT * FROM items"
            p = ()
            if warehouse:
                q += " WHERE warehouse=?"
                p = (warehouse,)
            for r in conn.execute(q, p).fetchall():
                s["total"] += 1
                st = r["status"] or ""
                if st == "В наличии": s["in_stock"] += 1
                elif st == "На Avito": s["on_avito"] += 1
                elif st == "Продано": s["sold"] += 1
                s["total_purchase"] += r["purchase_price"] or 0
                s["total_sale"] += r["sale_price"] or 0
                cat = r["category"] or "Другое"
                s["by_category"][cat] = s["by_category"].get(cat, 0) + 1
                stage = r["stage"] or "Не указан"
                s["by_stage"][stage] = s["by_stage"].get(stage, 0) + 1
            return s
        except Exception:
            return {"total": 0, "in_stock": 0, "on_avito": 0, "sold": 0,
                    "total_purchase": 0, "total_sale": 0, "by_category": {}, "by_stage": {}}
        finally:
            conn.close()

    def get_warehouse_name(self, wid):
        for w in WAREHOUSES:
            if w["id"] == wid:
                return f"{w['icon']} {w['name']}"
        return wid


db = Database()