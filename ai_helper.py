#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Модуль генерации описаний товаров.
Поддерживает:
  - YandexGPT (работает из России, бесплатный стартовый пакет)
  - OpenAI GPT-4o (не работает из РФ, но можно через VPN)
  - Шаблонное описание (всегда работает, ничего не нужно)
"""

import logging
from typing import Optional

try:
    from config import config
except ImportError:
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config import config

logger = logging.getLogger(__name__)


class DescriptionGenerator:
    """Генератор описаний. Выбирает провайдера автоматически."""

    def __init__(self):
        self._provider = None  # lazy init

    def _get_provider(self):
        """Возвращает подходящего провайдера."""
        if self._provider:
            return self._provider

        if config.AI_PROVIDER == "yandex" and config.has_yandexgpt:
            try:
                from yandex_provider import YandexGPTProvider
                self._provider = YandexGPTProvider()
                logger.info("AI: YandexGPT")
                return self._provider
            except Exception as e:
                logger.warning(f"YandexGPT не загрузился: {e}")

        if config.AI_PROVIDER == "openai" and config.has_openai:
            try:
                from openai_provider import OpenAIProvider
                self._provider = OpenAIProvider()
                logger.info("AI: OpenAI GPT-4o")
                return self._provider
            except Exception as e:
                logger.warning(f"OpenAI не загрузился: {e}")

        self._provider = _TemplateProvider()
        logger.info("AI: шаблон (нет ключа)")
        return self._provider

    def generate_description(
        self,
        image_bytes: Optional[bytes],
        category: str,
        brand: str,
        size: str,
        condition: str,
        purchase_price: float,
        sale_price: float,
    ) -> str:
        """Генерирует описание товара."""
        provider = self._get_provider()
        try:
            return provider.generate(image_bytes, category, brand, size,
                                     condition, purchase_price, sale_price)
        except Exception as e:
            logger.error(f"Ошибка AI провайдера: {e}")
            return _TemplateProvider().generate(image_bytes, category, brand,
                                                 size, condition,
                                                 purchase_price, sale_price)

    def improve_description(self, current_description: str) -> str:
        """Улучшает существующее описание (если есть AI)."""
        provider = self._get_provider()
        if isinstance(provider, _TemplateProvider):
            return current_description
        try:
            return provider.improve(current_description)
        except Exception as e:
            logger.error(f"Ошибка улучшения: {e}")
            return current_description


class _TemplateProvider:
    """Шаблонный генератор — не требует никаких ключей."""

    def generate(self, image_bytes, category, brand, size,
                 condition, purchase_price, sale_price):
        return (
            f"📌 {brand} — {category}\n\n"
            f"Продаю {category.lower()} бренда {brand}, "
            f"размер {size}. Состояние: {condition.lower()}.\n"
            f"Оригинальная вещь из секонд-хенда.\n\n"
            f"📏 Размер: {size}\n"
            f"📊 Состояние: {condition}\n"
            f"💰 Цена: {sale_price:.0f} ₽\n\n"
            f"#секондхенд #{brand.lower().replace(' ', '')} "
            f"#{category.lower().replace(' ', '')} #avito"
        )

    def improve(self, current_description):
        return current_description


# Экспорт
description_gen = DescriptionGenerator()