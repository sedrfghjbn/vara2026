#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import django
from pathlib import Path

# Получаем путь к директории скрипта
BASE_DIR = Path(__file__).resolve().parent

# Добавляем путь в sys.path
sys.path.insert(0, str(BASE_DIR))

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_project.settings')
os.chdir(BASE_DIR)

django.setup()

# Теперь можем использовать команды Django
from django.core.management import call_command

if __name__ == '__main__':
    print("Создание миграций...")
    try:
        call_command('makemigrations')
        print("✓ Миграции созданы")
    except Exception as e:
        print(f"Ошибка при создании миграций: {e}")
    
    print("\nПрименение миграций...")
    try:
        call_command('migrate')
        print("✓ Миграции применены")
    except Exception as e:
        print(f"Ошибка при применении миграций: {e}")
    
    print("\n✓ Готово! Теперь можно запустить сервер:")
    print("  python manage.py runserver")

