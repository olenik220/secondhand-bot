#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Запуск на продакшен-сервере (gunicorn).
Использовать: gunicorn wsgi:application
"""
from app import app as application

if __name__ == "__main__":
    application.run()