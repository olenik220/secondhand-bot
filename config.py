"""
Конфигурация бота для учета товаров секонд-хенда.
Загружает настройки из .env файла и переменных окружения.
Работает как из .py, так и из .exe (PyInstaller).
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv


def _get_base_path() -> str:
    """
    Определяет базовую папку приложения.
    Для .exe — папка с исполняемым файлом.
    Для .py — папка с этим скриптом.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


BASE_PATH = _get_base_path()
ENV_FILE = os.path.join(BASE_PATH, ".env")

# .env не обязателен — на Render переменные из Dashboard
if os.path.exists(ENV_FILE):
    load_dotenv(ENV_FILE)


class Config:
    """Настройки приложения."""

    # ---- Telegram ----
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    ALLOWED_USER_ID: int = int(os.getenv("ALLOWED_USER_ID", "0"))

    # ---- Google Sheets (опционально) ----
    GOOGLE_SHEETS_ID: str = os.getenv("GOOGLE_SHEETS_ID", "")
    GOOGLE_CREDENTIALS_FILE: str = os.path.join(BASE_PATH, "credentials.json")

    # ---- AI ----
    # ai_provider: "yandex" | "openai" | ""  (пусто = шаблон)
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "").lower().strip()

    # YandexGPT
    YANDEX_FOLDER_ID: str = os.getenv("YANDEX_FOLDER_ID", "")
    YANDEX_API_KEY: str = os.getenv("YANDEX_API_KEY", "")
    YANDEX_CATALOG_ID: str = os.getenv("YANDEX_CATALOG_ID", "")

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Пути
    ENV_FILE: str = ENV_FILE
    TOKEN_PICKLE: str = os.path.join(BASE_PATH, "token.pickle")
    DB_PATH: str = os.path.join(BASE_PATH, "data.db")

    # Заголовки колонок (для Google Sheets, если подключена)
    SHEET_HEADERS = [
        "ID", "Дата", "Категория", "Бренд", "Размер", "Состояние",
        "Цена закупки", "Цена продажи", "Статус", "Этап",
        "Фото (Telegram File ID)", "Описание для Авито",
        "Ссылка на Avito", "Примечание",
    ]

    # Категории, состояния, статусы, этапы
    CATEGORIES = [
        "Верхняя одежда", "Куртки/Пальто", "Свитера/Кофты",
        "Футболки/Поло", "Рубашки", "Джинсы/Брюки",
        "Юбки/Платья", "Костюмы", "Спорт", "Обувь",
        "Аксессуары", "Сумки/Рюкзаки", "Детское", "Другое",
    ]

    CONDITIONS = [
        "Новое с биркой", "Отличное", "Хорошее", "Удовлетворительное",
    ]

    STATUSES = ["В наличии", "На Avito", "Продано", "Списано"]

    STAGES = [
        "🛍️ Закупка",
        "📸 Фотосессия",
        "🤖 Генерация описания",
        "📢 На модерации Avito",
        "📢 Опубликовано на Avito",
        "💬 Торг",
        "📦 Упаковка",
        "🚚 Отправка",
        "✅ Продажа завершена",
    ]

    DEFAULT_STAGE_BY_STATUS = {
        "В наличии": "🛍️ Закупка",
        "На Avito": "📢 Опубликовано на Avito",
        "Продано": "✅ Продажа завершена",
        "Списано": "✅ Продажа завершена",
    }

    # ---- Свойства-помощники ----

    @property
    def is_configured(self) -> bool:
        """Проверяет, хватает ли для запуска."""
        return bool(self.TELEGRAM_BOT_TOKEN)

    @property
    def has_google_credentials(self) -> bool:
        return os.path.exists(self.GOOGLE_CREDENTIALS_FILE)

    @property
    def use_google_sheets(self) -> bool:
        """Google Sheets используется, если есть ID и credentials."""
        return bool(self.GOOGLE_SHEETS_ID) and self.has_google_credentials

    @property
    def has_openai(self) -> bool:
        return bool(self.OPENAI_API_KEY)

    @property
    def has_yandexgpt(self) -> bool:
        return bool(self.YANDEX_API_KEY)

    @property
    def ai_label(self) -> str:
        """Название текущего AI провайдера (для отображения)."""
        if self.AI_PROVIDER == "yandex" and self.has_yandexgpt:
            return "YandexGPT"
        elif self.AI_PROVIDER == "openai" and self.has_openai:
            return "OpenAI GPT-4o"
        return "нет (шаблон)"


config = Config()