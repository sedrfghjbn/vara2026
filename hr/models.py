from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils import timezone
import os
import secrets


def user_photo_path(instance, filename):
    """Путь для сохранения фото пользователя"""
    return f'user_photos/{instance.id}/{filename}'

def employee_photo_path(instance, filename):
    """Путь для сохранения фото сотрудника"""
    return f'employees/{instance.id}/{filename}'


class User(AbstractUser):
    """Расширенная модель пользователя с ролями"""
    ROLE_CHOICES = [
        ('hr_manager', 'HR-менеджер'),
        ('employee', 'Обычный сотрудник'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee', verbose_name='Роль')
    phone = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Номер телефона должен быть в формате: '+999999999'.")],
        verbose_name='Телефон'
    )
    first_name = models.CharField(max_length=150, blank=True, verbose_name='Имя')
    last_name = models.CharField(max_length=150, blank=True, verbose_name='Фамилия')
    middle_name = models.CharField(max_length=150, blank=True, verbose_name='Отчество')
    date_of_birth = models.DateField(null=True, blank=True, verbose_name='Дата рождения')
    email = models.EmailField(unique=True, verbose_name='Email')
    photo = models.ImageField(upload_to=user_photo_path, blank=True, null=True, verbose_name='Фото')
    telegram_bind_code = models.CharField(
        max_length=16,
        unique=True,
        blank=True,
        editable=False,
        verbose_name='Код привязки Telegram',
    )
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def is_hr_manager(self):
        """HR-менеджер - это суперпользователь или пользователь с ролью hr_manager"""
        return self.is_superuser or self.role == 'hr_manager'
    
    def is_employee(self):
        """Обычный сотрудник"""
        return self.role == 'employee' and not self.is_superuser

    def ensure_telegram_bind_code(self, save=True):
        """Постоянный персональный код привязки Telegram (генерируется один раз, не меняется)."""
        if self.telegram_bind_code:
            return self.telegram_bind_code
        for _ in range(20):
            code = secrets.token_urlsafe(8)[:12].upper()
            if not User.objects.filter(telegram_bind_code=code).exists():
                self.telegram_bind_code = code
                if save and self.pk:
                    User.objects.filter(pk=self.pk).update(telegram_bind_code=code)
                return code
        raise ValueError('Не удалось сгенерировать уникальный код привязки Telegram')

    def save(self, *args, **kwargs):
        # Код привязки нельзя изменить после выдачи
        if self.pk:
            original_code = (
                User.objects.filter(pk=self.pk)
                .values_list('telegram_bind_code', flat=True)
                .first()
            )
            if original_code:
                self.telegram_bind_code = original_code
        super().save(*args, **kwargs)
        if not self.telegram_bind_code:
            self.ensure_telegram_bind_code(save=True)


class Department(models.Model):
    """Отделы компании"""
    name = models.CharField(max_length=200, unique=True, verbose_name='Название отдела')
    description = models.TextField(blank=True, verbose_name='Описание')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Отдел'
        verbose_name_plural = 'Отделы'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Position(models.Model):
    """Должности"""
    name = models.CharField(max_length=200, unique=True, verbose_name='Название должности')
    description = models.TextField(blank=True, verbose_name='Описание')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Должность'
        verbose_name_plural = 'Должности'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Employee(models.Model):
    """Сотрудники"""
    STATUS_CHOICES = [
        ('active', 'Работает'),
        ('on_leave', 'В отпуске'),
        ('sick_leave', 'На больничном'),
        ('dismissed', 'Уволен'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile', null=True, blank=True, verbose_name='Пользователь')
    first_name = models.CharField(max_length=150, verbose_name='Имя')
    last_name = models.CharField(max_length=150, verbose_name='Фамилия')
    middle_name = models.CharField(max_length=150, blank=True, verbose_name='Отчество')
    date_of_birth = models.DateField(verbose_name='Дата рождения')
    email = models.EmailField(unique=True, verbose_name='Email')
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Номер телефона должен быть в формате: '+999999999'.")],
        verbose_name='Телефон'
    )
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, verbose_name='Должность')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, verbose_name='Отдел')
    hire_date = models.DateField(default=timezone.now, verbose_name='Дата приема на работу')
    photo = models.ImageField(upload_to=employee_photo_path, blank=True, null=True, verbose_name='Фото')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='Статус')
    note = models.TextField(blank=True, verbose_name='Заметка')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Сотрудник'
        verbose_name_plural = 'Сотрудники'
        ordering = ['last_name', 'first_name']
    
    def __str__(self):
        return f"{self.last_name} {self.first_name}"
    
    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name} {self.middle_name}".strip()
    
    @property
    def experience_years(self):
        """Стаж работы в годах"""
        if self.hire_date:
            delta = timezone.now().date() - self.hire_date
            return delta.days // 365
        return 0


class Vacancy(models.Model):
    """Вакансии"""
    STATUS_CHOICES = [
        ('open', 'Открыта'),
        ('closed', 'Закрыта'),
        ('archived', 'В архиве'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Зарплата от')
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Зарплата до')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', verbose_name='Статус')
    hr_manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_vacancies', verbose_name='HR-менеджер')
    position = models.ForeignKey(Position, on_delete=models.SET_NULL, null=True, verbose_name='Должность')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, verbose_name='Отдел')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата закрытия')
    
    class Meta:
        verbose_name = 'Вакансия'
        verbose_name_plural = 'Вакансии'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class Training(models.Model):
    """Обучение сотрудников"""
    STATUS_CHOICES = [
        ('planned', 'Запланировано'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершено'),
        ('cancelled', 'Отменено'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='Название курса')
    description = models.TextField(blank=True, verbose_name='Описание')
    responsible = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='trainings', verbose_name='Ответственный')
    start_date = models.DateField(verbose_name='Дата начала')
    end_date = models.DateField(verbose_name='Дата окончания')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned', verbose_name='Статус')
    participants = models.ManyToManyField(Employee, related_name='trainings', blank=True, verbose_name='Участники')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Обучение'
        verbose_name_plural = 'Обучение'
        ordering = ['-start_date']
    
    def __str__(self):
        return self.title


def certificate_path(instance, filename):
    """Путь для сохранения сертификатов"""
    return f'certificates/{instance.training.id}/{instance.employee.id}/{filename}'


class Certificate(models.Model):
    """Сертификаты сотрудников"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='certificates', verbose_name='Сотрудник')
    training = models.ForeignKey(Training, on_delete=models.CASCADE, related_name='certificates', verbose_name='Обучение')
    document = models.FileField(upload_to=certificate_path, verbose_name='Документ')
    issue_date = models.DateField(default=timezone.now, verbose_name='Дата выдачи')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Сертификат'
        verbose_name_plural = 'Сертификаты'
        unique_together = ['employee', 'training']
    
    def __str__(self):
        return f"{self.employee} - {self.training}"


# Telegram IS2 notification models (регистрация для миграций Django)
from hr.integrations.telegram.models import (
    EmployeeTelegramLink,
    NotificationLog,
    TelegramLinkCode,
    TelegramLinkSession,
    UserTelegramLink,
)

