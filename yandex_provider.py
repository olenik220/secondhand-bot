#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Провайдер YandexGPT для генерации описаний.
Работает из России, нужен API-ключ Yandex Cloud.
"""

import os
import json
import logging
from typing import Optional

import requests

try:
    from config import config
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import config

logger = logging.getLogger(__name__)


class YandexGPTProvider:
    """Генерация описаний через YandexGPT API."""

    # URL для YandexGPT (Foundation Models API)
    API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    def generate(
        self,
        image_bytes: Optional[bytes],
        category: str,
        brand: str,
        size: str,
        condition: str,
        purchase_price: float,
        sale_price: float,
    ) -> str:
        """Генерирует описание через YandexGPT."""
        prompt = self._build_prompt(category, brand, size, condition, sale_price)

        try:
            response = self._call_yandexgpt(prompt)
            if response:
                return response
        except Exception as e:
            logger.error(f"YandexGPT ошибка: {e}")

        return self._fallback(category, brand, size, condition, sale_price)

    def improve(self, current_description: str) -> str:
        """Улучшает описание."""
        prompt = (
            "Ты — редактор объявлений Avito. Улучши описание товара: "
            "сделай его более привлекательным, структурированным, "
            "но сохрани все факты. Максимум 1000 символов.\n\n"
            f"Описание:\n{current_description}"
        )
        try:
            return self._call_yandexgpt(prompt) or current_description
        except Exception:
            return current_description

    def _build_prompt(self, category, brand, size, condition, price) -> str:
        return (
            "Ты — профессиональный копирайтер для Avito в категории секонд-хенд. "
            "Составь привлекательное описание товара на русском языке.\n\n"
            "Правила:\n"
            "1. Укажи бренд, размер и состояние\n"
            "2. Опиши внешний вид, материал, цвет\n"
            "3. Упомяни особенности\n"
            "4. Добавь хештеги в конце через #\n"
            "5. Будь честным о состоянии\n"
            "6. Максимум 1000 символов\n\n"
            f"Категория: {category}\n"
            f"Бренд: {brand}\n"
            f"Размер: {size}\n"
            f"Состояние: {condition}\n"
            f"Цена: {price:.0f} ₽\n\n"
            "Формат ответа:\n"
            "📌 [Бренд] — [Название/тип]\n\n"
            "[Описание]\n\n"
            "📏 Размер: [размер]\n"
            "📊 Состояние: [состояние]\n"
            "💰 Цена: [цена] ₽\n\n"
            "#секондхенд #[бренд] #[категория] #avito"
        )

    def _call_yandexgpt(self, prompt: str) -> Optional[str]:
        """Выполняет запрос к YandexGPT."""
        headers = {
            "Authorization": f"Api-Key {config.YANDEX_API_KEY}",
            "Content-Type": "application/json",
        }

        data = {
            "modelUri": f"gpt://{config.YANDEX_FOLDER_ID}/yandexgpt/latest",
            "completionOptions": {
                "stream": False,
                "temperature": 0.7,
                "maxTokens": 1000,
            },
            "messages": [
                {
                    "role": "system",
                    "content": "Ты — копирайтер для Avito, специалист по секонд-хенду.",
                },
                {"role": "user", "content": prompt},
            ],
        }

        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=data,
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()

            # Парсим ответ
            alternatives = result.get("result", {}).get("alternatives", [])
            if alternatives:
                text = alternatives[0].get("message", {}).get("content", "")
                if text:
                    return text.strip()

        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP ошибка YandexGPT: {e}")

        return None

    def _fallback(self, category, brand, size, condition, price) -> str:
        """Запасной вариант."""
        return (
            f"📌 {brand} — {category}\n\n"
            f"Продаю {category.lower()} бренда {brand}, размер {size}. "
            f"Состояние: {condition.lower()}.\n\n"
            f"📏 Размер: {size}\n"
            f"📊 Состояние: {condition}\n"
            f"💰 Цена: {price:.0f} ₽\n\n"
            f"#секондхенд #{brand.lower().replace(' ', '')} "
            f"#{category.lower().replace(' ', '')} #avito"
        )