@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Установка зависимостей...
pip install -r requirements.txt

echo.
echo Создание миграций...
python manage.py makemigrations

echo.
echo Применение миграций...
python manage.py migrate

echo.
echo Запуск сервера...
python manage.py runserver

