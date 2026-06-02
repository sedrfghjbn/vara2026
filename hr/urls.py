from django.urls import path
from . import views
from hr.integrations.telegram.webhook import telegram_webhook

app_name = 'hr'

urlpatterns = [
    # Аутентификация
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    
    # Главная
    path('', views.index, name='index'),
    
    # Сотрудники
    path('employees/', views.employees_list, name='employees_list'),
    path('employees/<int:employee_id>/', views.employee_detail, name='employee_detail'),
    path('employees/create/', views.employee_create, name='employee_create'),
    path('employees/<int:employee_id>/edit/', views.employee_edit, name='employee_edit'),
    path('employees/<int:employee_id>/delete/', views.employee_delete, name='employee_delete'),
    
    # Вакансии
    path('vacancies/', views.vacancies_list, name='vacancies_list'),
    path('vacancies/<int:vacancy_id>/', views.vacancy_detail, name='vacancy_detail'),
    path('vacancies/create/', views.vacancy_create, name='vacancy_create'),
    path('vacancies/<int:vacancy_id>/edit/', views.vacancy_edit, name='vacancy_edit'),
    path('vacancies/<int:vacancy_id>/delete/', views.vacancy_delete, name='vacancy_delete'),
    
    # Обучение
    path('trainings/', views.trainings_list, name='trainings_list'),
    path('trainings/<int:training_id>/', views.training_detail, name='training_detail'),
    path('trainings/create/', views.training_create, name='training_create'),
    path('trainings/<int:training_id>/edit/', views.training_edit, name='training_edit'),
    path('trainings/<int:training_id>/delete/', views.training_delete, name='training_delete'),
    
    # Отчёты
    path('reports/', views.reports, name='reports'),
    path('reports/vacancies/', views.report_vacancies, name='report_vacancies'),
    path('reports/training/', views.report_training, name='report_training'),
    path('reports/staffing/', views.report_staffing, name='report_staffing'),
    
    # Импорт
    path('import/employees/', views.import_employees, name='import_employees'),

    # Telegram IS2
    path('integrations/telegram/webhook/', telegram_webhook, name='telegram_webhook'),
]

