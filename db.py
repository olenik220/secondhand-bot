#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Локальная база данных SQLite для учёта товаров.
Работает всегда, без интернета, без каких-либо ключей.
Заменяет Google Sheets как основное хранилище.
"""

import os
import sqlite3
import datetime
import logging
from typing import Optional

from config import config, BASE_PATH

logger = logging.getLogger(__name__)


class Database:
    """Локальная SQLite база данных."""

    def __init__(self):
        self.db_path = os.path.join(BASE_PATH, "data.db")
        self._init_db()

    def _get_conn(self):
        """Создаёт подключение к БД."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Создаёт таблицы при первом запуске."""
        conn = self._get_conn()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS items (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                    updated_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                    category    TEXT NOT NULL DEFAULT 'Другое',
                    brand       TEXT NOT NULL DEFAULT 'Неизвестный бренд',
                    size        TEXT NOT NULL DEFAULT 'Не указан',
                    condition   TEXT NOT NULL DEFAULT 'Хорошее',
                    purchase_price REAL NOT NULL DEFAULT 0,
                    sale_price     REAL NOT NULL DEFAULT 0,
                    status      TEXT NOT NULL DEFAULT 'В наличии',
                    stage       TEXT NOT NULL DEFAULT '',
                    photo_file_id TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    avito_link  TEXT NOT NULL DEFAULT '',
                    note        TEXT NOT NULL DEFAULT ''
                );
            """)
            conn.commit()
            logger.info(f"База данных инициализирована: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise
        finally:
            conn.close()

    # ──────── ДОБАВЛЕНИЕ ТОВАРА ────────

    def add_item(
        self,
        category: str,
        brand: str,
        size: str,
        condition: str,
        purchase_price: float,
        sale_price: float,
        photo_file_id: str = "",
        description: str = "",
        stage: str = "",
    ) -> int:
        """Добавляет товар в БД. Возвращает ID."""
        if not stage:
            stage = "🛍️ Закупка"

        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """INSERT INTO items 
                   (category, brand, size, condition, purchase_price, sale_price,
                    photo_file_id, description, status, stage)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'В наличии', ?)""",
                (category, brand, size, condition, purchase_price, sale_price,
                 photo_file_id, description, stage),
            )
            conn.commit()
            item_id = cursor.lastrowid
            logger.info(f"Товар #{item_id} добавлен: {brand} {category}")
            return item_id
        except sqlite3.Error as e:
            logger.error(f"Ошибка добавления товара: {e}")
            raise
        finally:
            conn.close()

    # ──────── ОБНОВЛЕНИЕ ПОЛЕЙ ────────

    def update_status(self, item_id: int, status: str) -> bool:
        """Обновляет статус товара."""
        conn = self._get_conn()
        try:
            conn.execute(
                """UPDATE items SET status = ?, updated_at = datetime('now', 'localtime')
                   WHERE id = ?""",
                (status, item_id),
            )
            conn.commit()
            if conn.total_changes == 0:
                logger.warning(f"Товар #{item_id} не найден при обновлении статуса")
                return False

            # Автоматически устанавливаем этап по статусу
            default_stage = config.DEFAULT_STAGE_BY_STATUS.get(status)
            if default_stage:
                cur = conn.execute("SELECT stage FROM items WHERE id = ?", (item_id,))
                row = cur.fetchone()
                if row:
                    current_stage = row["stage"] or ""
                    if not current_stage or current_stage not in config.STAGES:
                        conn.execute(
                            "UPDATE items SET stage = ? WHERE id = ?",
                            (default_stage, item_id),
                        )
                        conn.commit()

            logger.info(f"Статус товара #{item_id} обновлён: {status}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка обновления статуса: {e}")
            return False
        finally:
            conn.close()

    def update_stage(self, item_id: int, stage: str) -> bool:
        """Обновляет этап обработки и автоматически корректирует статус."""
        conn = self._get_conn()
        try:
            conn.execute(
                """UPDATE items SET stage = ?, updated_at = datetime('now', 'localtime')
                   WHERE id = ?""",
                (stage, item_id),
            )
            conn.commit()
            if conn.total_changes == 0:
                return False

            # Автоматически обновляем общий статус по этапу
            if stage == "✅ Продажа завершена":
                conn.execute(
                    "UPDATE items SET status = 'Продано' WHERE id = ? AND status != 'Списано'",
                    (item_id,),
                )
            elif stage in ("📢 Опубликовано на Avito", "📢 На модерации Avito"):
                conn.execute(
                    "UPDATE items SET status = 'На Avito' WHERE id = ?",
                    (item_id,),
                )
            elif stage in ("🛍️ Закупка", "📸 Фотосессия", "🤖 Генерация описания"):
                conn.execute(
                    "UPDATE items SET status = 'В наличии' WHERE id = ? AND status != 'Списано'",
                    (item_id,),
                )
            conn.commit()

            logger.info(f"Этап товара #{item_id} обновлён: {stage}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка обновления этапа: {e}")
            return False
        finally:
            conn.close()

    def update_avito_link(self, item_id: int, link: str) -> bool:
        """Сохраняет ссылку Avito и обновляет статус."""
        conn = self._get_conn()
        try:
            conn.execute(
                """UPDATE items SET avito_link = ?, status = 'На Avito',
                   stage = '📢 Опубликовано на Avito',
                   updated_at = datetime('now', 'localtime')
                   WHERE id = ?""",
                (link, item_id),
            )
            conn.commit()
            logger.info(f"Ссылка Avito для товара #{item_id} сохранена")
            return conn.total_changes > 0
        except sqlite3.Error as e:
            logger.error(f"Ошибка обновления ссылки Avito: {e}")
            return False
        finally:
            conn.close()

    def update_description(self, item_id: int, description: str) -> bool:
        """Обновляет описание товара."""
        conn = self._get_conn()
        try:
            conn.execute(
                """UPDATE items SET description = ?, updated_at = datetime('now', 'localtime')
                   WHERE id = ?""",
                (description, item_id),
            )
            conn.commit()
            return conn.total_changes > 0
        except sqlite3.Error as e:
            logger.error(f"Ошибка обновления описания: {e}")
            return False
        finally:
            conn.close()

    def update_photo_file_id(self, item_id: int, file_id: str) -> bool:
        """Обновляет ID фото в Telegram."""
        conn = self._get_conn()
        try:
            conn.execute(
                "UPDATE items SET photo_file_id = ? WHERE id = ?",
                (file_id, item_id),
            )
            conn.commit()
            return conn.total_changes > 0
        except sqlite3.Error as e:
            logger.error(f"Ошибка обновления фото: {e}")
            return False
        finally:
            conn.close()

    # ──────── ПОЛУЧЕНИЕ ДАННЫХ ────────

    def get_all_items(self) -> list:
        """Возвращает список всех товаров."""
        conn = self._get_conn()
        try:
            cursor = conn.execute("SELECT * FROM items ORDER BY id DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения списка: {e}")
            return []
        finally:
            conn.close()

    def get_item_by_id(self, item_id: int) -> Optional[dict]:
        """Находит товар по его ID."""
        conn = self._get_conn()
        try:
            cursor = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения товара #{item_id}: {e}")
            return None
        finally:
            conn.close()

    def get_statistics(self) -> dict:
        """Возвращает статистику по товарам."""
        conn = self._get_conn()
        try:
            stats = {
                "total": 0,
                "in_stock": 0,
                "on_avito": 0,
                "sold": 0,
                "total_purchase": 0.0,
                "total_sale": 0.0,
                "by_category": {},
                "by_stage": {},
            }

            cursor = conn.execute("SELECT * FROM items")
            for row in cursor.fetchall():
                stats["total"] += 1

                status = row["status"] or ""
                if status == "В наличии":
                    stats["in_stock"] += 1
                elif status == "На Avito":
                    stats["on_avito"] += 1
                elif status == "Продано":
                    stats["sold"] += 1

                stats["total_purchase"] += row["purchase_price"] or 0
                stats["total_sale"] += row["sale_price"] or 0

                cat = row["category"] or "Другое"
                stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1

                stage = row["stage"] or "Не указан"
                stats["by_stage"][stage] = stats["by_stage"].get(stage, 0) + 1

            return stats
        except sqlite3.Error as e:
            logger.error(f"Ошибка статистики: {e}")
            return {
                "total": 0, "in_stock": 0, "on_avito": 0, "sold": 0,
                "total_purchase": 0.0, "total_sale": 0.0,
                "by_category": {}, "by_stage": {},
            }
        finally:
            conn.close()

    # ──────── GOOGLE SHEETS СИНХРОНИЗАЦИЯ ────────

    def export_to_list(self) -> list[dict]:
        """Экспортирует все товары в список словарей (для sheets)."""
        return self.get_all_items()

    def import_from_list(self, items: list[dict]):
        """Импортирует товары из списка словарей (из sheets)."""
        conn = self._get_conn()
        try:
            conn.execute("DELETE FROM items")
            for item in items:
                conn.execute(
                    """INSERT INTO items 
                       (id, created_at, updated_at, category, brand, size, condition,
                        purchase_price, sale_price, status, stage, photo_file_id,
                        description, avito_link, note)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        item.get("ID") or item.get("id"),
                        item.get("Дата") or item.get("created_at", ""),
                        item.get("updated_at", ""),
                        item.get("Категория") or item.get("category", "Другое"),
                        item.get("Бренд") or item.get("brand", ""),
                        item.get("Размер") or item.get("size", ""),
                        item.get("Состояние") or item.get("condition", ""),
                        float(item.get("Цена закупки") or item.get("purchase_price", 0) or 0),
                        float(item.get("Цена продажи") or item.get("sale_price", 0) or 0),
                        item.get("Статус") or item.get("status", "В наличии"),
                        item.get("Этап") or item.get("stage", ""),
                        item.get("Фото (Telegram File ID)") or item.get("photo_file_id", ""),
                        item.get("Описание для Авито") or item.get("description", ""),
                        item.get("Ссылка на Avito") or item.get("avito_link", ""),
                        item.get("Примечание") or item.get("note", ""),
                    ),
                )
            conn.commit()
            logger.info(f"Импортировано {len(items)} товаров из Google Sheets")
        except sqlite3.Error as e:
            logger.error(f"Ошибка импорта: {e}")
            raise
        finally:
            conn.close()


# Глобальный экземпляр БД
db = Database()