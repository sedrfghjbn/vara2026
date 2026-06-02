import os
import sys
import subprocess

# Устанавливаем рабочую директорию
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

print("Создание миграций...")
result1 = subprocess.run([sys.executable, 'manage.py', 'makemigrations', 'hr'], 
                        cwd=script_dir, capture_output=False)
print("\nПрименение миграций...")
result2 = subprocess.run([sys.executable, 'manage.py', 'migrate'], 
                        cwd=script_dir, capture_output=False)
print("\nГотово!")

