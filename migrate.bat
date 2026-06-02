@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo Настройка HR системы
echo ========================================
echo.

echo Шаг 1: Создание миграций для приложения hr...
python manage.py makemigrations hr
if errorlevel 1 (
    echo ОШИБКА при создании миграций!
    pause
    exit /b 1
)

echo.
echo Шаг 2: Применение миграций...
python manage.py migrate
if errorlevel 1 (
    echo ОШИБКА при применении миграций!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Готово! Миграции выполнены успешно!
echo ========================================
echo.
echo Теперь вы можете:
echo 1. Создать суперпользователя: python manage.py createsuperuser
echo 2. Запустить сервер: python manage.py runserver
echo.
pause

