import os
import sys
import subprocess

# Абсолютный путь к проекту (из workspace path)
BASE_DIR = r'C:\Users\alisa\Desktop\курсач пи ВАРЯ'

# Проверяем существование manage.py
manage_py = os.path.join(BASE_DIR, 'manage.py')
if not os.path.exists(manage_py):
    print(f"Ошибка: {manage_py} не найден!")
    sys.exit(1)

os.chdir(BASE_DIR)

print("=" * 60)
print("Создание и применение миграций")
print("=" * 60)
print(f"Рабочая директория: {os.getcwd()}")
print()

print("Шаг 1: Создание миграций для hr...")
result1 = subprocess.run([sys.executable, 'manage.py', 'makemigrations', 'hr'], 
                        cwd=BASE_DIR)
if result1.returncode != 0:
    print("ОШИБКА при создании миграций!")
    sys.exit(1)

print("\nШаг 2: Применение миграций...")
result2 = subprocess.run([sys.executable, 'manage.py', 'migrate'], 
                        cwd=BASE_DIR)
if result2.returncode != 0:
    print("ОШИБКА при применении миграций!")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ Готово! Миграции созданы и применены!")
print("=" * 60)

