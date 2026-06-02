# -*- coding: utf-8 -*-
import os
import sys
import django

# Получаем директорию, где находится этот скрипт
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Переходим в эту директорию
os.chdir(BASE_DIR)

# Добавляем путь в sys.path
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_project.settings')

try:
    django.setup()
    
    from django.core.management import call_command
    
    print("=" * 50)
    print("Создание миграций...")
    print("=" * 50)
    call_command('makemigrations')
    
    print("\n" + "=" * 50)
    print("Применение миграций...")
    print("=" * 50)
    call_command('migrate')
    
    print("\n" + "=" * 50)
    print("✓ Готово! База данных создана.")
    print("=" * 50)
    print("\nВАЖНО: Если у вас есть старые записи без пользователя,")
    print("они не будут отображаться после входа в систему.")
    print("Рекомендуется удалить их или создать нового пользователя.")
    print("\nТеперь можно запустить сервер:")
    print("  python manage.py runserver")
    print("\nИли просто запустите run.bat")
    
except Exception as e:
    print(f"\nОшибка: {e}")
    import traceback
    traceback.print_exc()
    input("\nНажмите Enter для выхода...")

