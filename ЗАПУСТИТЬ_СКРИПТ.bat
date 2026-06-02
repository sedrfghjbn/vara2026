@echo off
chcp 65001 >nul
echo Заполнение базы данных начальными данными для рекламного агентства...
echo.
python manage.py shell -c "exec(open('seed_data.py', encoding='utf-8').read())"
pause

