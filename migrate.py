import os
import sys
import django

# Установка пути к проекту
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_project.settings')
django.setup()

# Выполнение миграций
from django.core.management import execute_from_command_line

if __name__ == '__main__':
    print("Создание миграций...")
    execute_from_command_line(['manage.py', 'makemigrations'])
    
    print("\nПрименение миграций...")
    execute_from_command_line(['manage.py', 'migrate'])
    
    print("\nГотово! Теперь можно запустить сервер: python manage.py runserver")

