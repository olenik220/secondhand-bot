#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Провайдер OpenAI для генерации описаний.
Не работает из России без VPN, но доступен через него.
"""

import base64
import logging
from typing import Optional

try:
    from config import config
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import config

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """Генерация описаний через OpenAI GPT-4o Vision."""

    def __init__(self):
        from openai import OpenAI as OpenAIClient
        self.client = OpenAIClient(api_key=config.OPENAI_API_KEY)

    def _encode_image(self, image_bytes: bytes) -> str:
        """Кодирует изображение в base64."""
        return base64.b64encode(image_bytes).decode("utf-8")

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
        """Генерирует описание через OpenAI GPT-4o Vision."""
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "Ты — профессиональный копирайтер для Avito в категории секонд-хенд. "
                        "Составь привлекательное, честное и подробное описание товара "
                        "на русском языке.\n\n"
                        "ПРАВИЛА:\n"
                        "1. Укажи бренд, модель (если видно), размер и состояние\n"
                        "2. Опиши материал, цвет, фасон (по фото)\n"
                        "3. Добавь хештеги в конце через #\n"
                        "4. Будь честным о состоянии\n"
                        "5. Максимум 1000 символов\n\n"
                        "Формат:\n"
                        "📌 [Бренд] — [Название/тип]\n\n"
                        "[Описание]\n\n"
                        "📏 Размер: [размер]\n"
                        "📊 Состояние: [состояние]\n"
                        "💰 Цена: [цена] ₽\n\n"
                        "#секондхенд #[бренд] #[категория] #avito"
                    ),
                }
            ]

            user_content = (
                f"Составь описание для Avito:\n"
                f"Категория: {category}\n"
                f"Бренд: {brand}\n"
                f"Размер: {size}\n"
                f"Состояние: {condition}\n"
                f"Цена: {sale_price:.0f} ₽\n"
            )

            if image_bytes:
                base64_image = self._encode_image(image_bytes)
                user_message = {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_content + "\n\nВот фото товара:"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            else:
                user_message = {
                    "role": "user",
                    "content": user_content + "\n\n(Фото не приложено, опиши из параметров)"
                }

            messages.append(user_message)

            response = self.client.chat.completions.create(
                model="gpt-4o-2024-11-20",
                messages=messages,
                max_tokens=1000,
                temperature=0.7,
            )

            text = response.choices[0].message.content.strip()
            return text or self._fallback(category, brand, size, condition, sale_price)

        except Exception as e:
            logger.error(f"OpenAI ошибка: {e}")
            return self._fallback(category, brand, size, condition, sale_price)

    def improve(self, current_description: str) -> str:
        """Улучшает существующее описание."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты — редактор объявлений Avito. Улучши описание товара: "
                            "сделай его более привлекательным, структурированным, "
                            "но сохрани все факты. Максимум 1000 символов."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Улучши это описание:\n\n{current_description}",
                    },
                ],
                max_tokens=1000,
                temperature=0.5,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI улучшение ошибка: {e}")
            return current_description

    def _fallback(self, category, brand, size, condition, price) -> str:
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