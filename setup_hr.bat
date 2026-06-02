@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo Настройка HR системы
echo ========================================
echo.

REM Удаление старой базы данных (если есть)
if exist "db.sqlite3" (
    echo Удаление старой базы данных...
    del "db.sqlite3"
    echo Старая БД удалена.
    echo.
)

REM Создание папки migrations если её нет
if not exist "hr\migrations" (
    echo Создание папки migrations...
    mkdir "hr\migrations"
    echo. > "hr\migrations\__init__.py"
    echo Папка migrations создана.
    echo.
)

echo Шаг 1: Создание миграций для приложения hr...
python manage.py makemigrations hr
if errorlevel 1 (
    echo.
    echo ОШИБКА при создании миграций!
    echo Проверьте, что все зависимости установлены: pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo Шаг 2: Применение миграций...
python manage.py migrate
if errorlevel 1 (
    echo.
    echo ОШИБКА при применении миграций!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Готово! Миграции выполнены успешно!
echo ========================================
echo.
echo Следующие шаги:
echo 1. Создать суперпользователя: python manage.py createsuperuser
echo 2. Запустить сервер: python manage.py runserver
echo 3. Открыть в браузере: http://127.0.0.1:8000/
echo.
pause

