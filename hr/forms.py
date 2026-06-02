from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import RegexValidator, ValidationError
from django.contrib.auth import password_validation
from django.utils import timezone

from .models import User, Employee, Vacancy, Training, Department, Position
from django.contrib.auth import get_user_model
from django.db.models import Q
import re

EMPLOYEE_MIN_AGE = 18
EMPLOYEE_MAX_AGE = 100


def normalize_phone(raw: str) -> str:
    """Приводим телефон к формату +7XXXXXXXXXX"""
    digits = re.sub(r'\D', '', raw or '')
    if digits.startswith('8'):
        digits = '7' + digits[1:]
    if not digits.startswith('7'):
        digits = '7' + digits
    digits = digits[:11]
    if len(digits) != 11:
        raise ValidationError("Номер телефона должен быть в формате: '+999999999'.")
    return f"+7{digits[1:]}"


def calculate_age(date_of_birth, on_date=None):
    """Полных лет на указанную дату."""
    on_date = on_date or timezone.now().date()
    years = on_date.year - date_of_birth.year
    if (on_date.month, on_date.day) < (date_of_birth.month, date_of_birth.day):
        years -= 1
    return years


def validate_employee_birth_date(date_of_birth):
    """
    Возраст в карточке сотрудника: от 18 до 100 лет.
    Регистрация на платформе этим ограничением не затрагивается.
    """
    if not date_of_birth:
        raise ValidationError('Укажите дату рождения.')

    today = timezone.now().date()
    if date_of_birth > today:
        raise ValidationError('Дата рождения не может быть в будущем.')

    age = calculate_age(date_of_birth, today)
    if age < EMPLOYEE_MIN_AGE:
        raise ValidationError(
            f'Нельзя нанять сотрудника младше 18 лет.'
        )
    if age > EMPLOYEE_MAX_AGE:
        raise ValidationError(
            f'Нельзя нанять сотрудника старше 100 лет.'
        )
    return date_of_birth


class RegisterForm(UserCreationForm):
    """Форма регистрации с валидацией (вход по email)"""
    # Прячем username и будем заполнять его автоматически email-ом
    username = forms.CharField(required=False, widget=forms.HiddenInput())
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        })
    )
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Пароль (минимум 8 символов, 1 цифра, 1 заглавная буква)'
        }),
        help_text='Минимум 8 символов, должна быть хотя бы одна цифра и одна заглавная буква'
    )
    password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Подтвердите пароль'
        })
    )
    first_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя'
        })
    )
    last_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Фамилия'
        })
    )
    middle_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Отчество'
        })
    )
    date_of_birth = forms.DateField(
        required=True,
        widget=forms.DateInput(
            attrs={
                'class': 'form-control',
                'type': 'date'
            },
            format='%Y-%m-%d'
        ),
        input_formats=['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y'],
        help_text='Дата рождения'
    )
    phone = forms.CharField(
        required=True,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (___) ___-__-__'
        }),
        # Разрешаем маску (+7(999)999-99-99), нормализуем в clean_phone
        validators=[RegexValidator(regex=r'^[\d\+\-\s\(\)]+$', message="Номер телефона должен быть в формате: '+999999999'.")]
    )
    phone_error_message = "Номер телефона должен быть в формате: '+999999999'."
    
    class Meta:
        model = User
        fields = ['email', 'password1', 'password2', 'first_name', 'last_name', 'middle_name', 'date_of_birth', 'phone']
    
    def clean_username(self):
        # Генерируем username из email, чтобы пройти валидацию базовой формы
        email = (self.cleaned_data.get('email') or '').lower()
        return email
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Пользователь с таким email уже существует.')
        return email
    
    def clean_phone(self):
        try:
            phone = normalize_phone(self.cleaned_data.get('phone', ''))
            # Проверяем, что телефона нет у другого пользователя
            if User.objects.filter(phone=phone).exists():
                raise ValidationError('Пользователь с таким телефоном уже существует.')
            return phone
        except ValidationError:
            raise ValidationError(self.phone_error_message)
    
    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if len(password1) < 8:
            raise ValidationError('Пароль должен содержать минимум 8 символов.')
        if not re.search(r'\d', password1):
            raise ValidationError('Пароль должен содержать хотя бы одну цифру.')
        if not re.search(r'[A-ZА-Я]', password1):
            raise ValidationError('Пароль должен содержать хотя бы одну заглавную букву.')
        password_validation.validate_password(password1, self.instance)
        return password1
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError({'password2': 'Пароли не совпадают.'})
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        # Используем email как основной идентификатор/username
        email = self.cleaned_data['email'].lower()
        user.username = email
        user.email = email
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.middle_name = self.cleaned_data.get('middle_name', '')
        user.date_of_birth = self.cleaned_data.get('date_of_birth')
        user.phone = self.cleaned_data.get('phone', '')
        user.role = 'employee'  # По умолчанию обычный сотрудник
        # Сохраняем дополнительные данные (middle_name и date_of_birth) в сессии для последующего использования
        # при создании карточки сотрудника
        if commit:
            user.save()
            # Сохраняем middle_name и date_of_birth в user, если они есть
            # Но так как этих полей нет в User, мы их просто игнорируем
            # Они будут использованы при создании карточки сотрудника
        return user


class LoginForm(forms.Form):
    """Форма входа по email"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Пароль'
        })
    )


class UserProfileForm(forms.ModelForm):
    """Редактирование профиля пользователя"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        })
    )
    phone = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (___) ___-__-__'
        }),
        validators=[RegexValidator(regex=r'^[\d\+\-\s\(\)]+$', message="Номер телефона должен быть в формате: '+999999999'.")]
    )
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                'class': 'form-control',
                'type': 'date'
            },
            format='%Y-%m-%d'
        ),
        input_formats=['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y'],
        help_text=(
            f'Для сотрудников: от {EMPLOYEE_MIN_AGE} до {EMPLOYEE_MAX_AGE} лет '
            '(на момент сохранения).'
        ),
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'middle_name', 'date_of_birth', 'email', 'phone', 'photo']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Фамилия'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Отчество'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').lower()
        qs = User.objects.filter(email=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Пользователь с таким email уже существует.')
        return email

    def clean_phone(self):
        phone_raw = self.cleaned_data.get('phone', '') or ''
        if not phone_raw.strip():
            return ''
        phone = normalize_phone(phone_raw)
        qs = User.objects.filter(phone=phone).exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Пользователь с таким телефоном уже существует.')
        return phone

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if not date_of_birth:
            return date_of_birth
        if self.instance.pk and Employee.objects.filter(user_id=self.instance.pk).exists():
            return validate_employee_birth_date(date_of_birth)
        return date_of_birth

    def save(self, commit=True):
        user = super().save(commit=False)
        # синхронизируем username с email
        email = self.cleaned_data.get('email', '').lower()
        if email:
            user.username = email
            user.email = email
        user.phone = self.cleaned_data.get('phone', '')
        if commit:
            user.save()
            self._sync_linked_employee(user)
        return user

    def _sync_linked_employee(self, user):
        """
        Профиль (User) и карточка сотрудника (Employee) должны совпадать.
        Сохранение Employee запускает Telegram-уведомления через signals.
        """
        try:
            employee = user.employee_profile
        except Employee.DoesNotExist:
            return

        employee.first_name = user.first_name or ''
        employee.last_name = user.last_name or ''
        employee.middle_name = user.middle_name or ''
        if user.date_of_birth:
            employee.date_of_birth = user.date_of_birth
        if user.phone:
            employee.phone = user.phone
        if user.email:
            new_email = user.email.lower()
            if employee.email != new_email:
                if not Employee.objects.filter(email=new_email).exclude(pk=employee.pk).exists():
                    employee.email = new_email
        employee._updated_by_user = user
        employee.save()


class EmployeeForm(forms.ModelForm):
    """Форма для создания/редактирования сотрудника"""
    phone = forms.CharField(
        required=True,
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (___) ___-__-__'}),
        validators=[RegexValidator(regex=r'^[\d\+\-\s\(\)]+$', message="Номер телефона должен быть в формате: '+999999999'.")]
    )
    
    # Явно определяем поля дат с правильным форматом для HTML5 date input
    date_of_birth = forms.DateField(
        widget=forms.DateInput(
            attrs={'class': 'form-control', 'type': 'date'},
            format='%Y-%m-%d'
        ),
        input_formats=['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y'],
        required=True
    )
    hire_date = forms.DateField(
        widget=forms.DateInput(
            attrs={'class': 'form-control', 'type': 'date'},
            format='%Y-%m-%d'
        ),
        input_formats=['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y'],
        required=True
    )
    
    # Поле пользователя - скрытое, управляется через модальное окно
    user = forms.ModelChoiceField(
        queryset=User.objects.filter(role='employee').order_by('username'),
        widget=forms.HiddenInput(attrs={'id': 'id_user'}),
        required=True
    )

    class Meta:
        model = Employee
        fields = [
            'user', 'first_name', 'last_name', 'middle_name', 'date_of_birth',
            'email', 'phone', 'position', 'department', 'hire_date',
            'photo', 'status', 'note'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'position': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Заметка (необязательно)'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['position'].queryset = Position.objects.all().order_by('name')
        self.fields['department'].queryset = Department.objects.all().order_by('name')
        self.fields['position'].required = False
        self.fields['department'].required = False
        self.fields['position'].empty_label = '— выберите должность —'
        self.fields['department'].empty_label = '— выберите отдел —'
        self.fields['date_of_birth'].help_text = (
            f'Для карточки сотрудника: от {EMPLOYEE_MIN_AGE} до {EMPLOYEE_MAX_AGE} лет '
            '(на момент сохранения).'
        )

    def clean_date_of_birth(self):
        return validate_employee_birth_date(self.cleaned_data.get('date_of_birth'))

    def clean_phone(self):
        try:
            phone = normalize_phone(self.cleaned_data.get('phone', ''))
            # Проверка уникальности среди сотрудников (с учетом редактирования)
            qs = Employee.objects.filter(phone=phone)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Сотрудник с таким телефоном уже существует.')
            # Проверка уникальности среди пользователей (но разрешаем, если это телефон выбранного пользователя)
            user = self.cleaned_data.get('user')
            qs_user = User.objects.filter(phone=phone)
            if self.instance.pk and self.instance.user_id:
                qs_user = qs_user.exclude(pk=self.instance.user_id)
            elif user and user.phone == phone:
                # Если телефон совпадает с телефоном выбранного пользователя - это нормально
                pass
            elif qs_user.exists():
                raise ValidationError('Пользователь с таким телефоном уже существует.')
            return phone
        except ValidationError as e:
            raise e
    
    def clean_user(self):
        user = self.cleaned_data.get('user')
        if user:
            # Проверяем, что пользователь имеет роль employee
            if user.role != 'employee':
                raise ValidationError('Сотрудник может быть создан только для пользователя с ролью "Обычный сотрудник".')
            # Проверяем, что у этого пользователя еще нет сотрудника
            if self.instance.pk:
                # При редактировании - проверяем, что другой сотрудник не использует этого пользователя
                existing = Employee.objects.filter(user=user).exclude(pk=self.instance.pk).first()
                if existing:
                    raise ValidationError(f'Пользователь {user.username} уже связан с сотрудником {existing.full_name}.')
            else:
                # При создании - проверяем, что пользователь еще не используется
                if Employee.objects.filter(user=user).exists():
                    raise ValidationError(f'Пользователь {user.username} уже имеет карточку сотрудника.')
        return user
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if self.instance.pk:
            if Employee.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise ValidationError('Сотрудник с таким email уже существует.')
        else:
            if Employee.objects.filter(email=email).exists():
                raise ValidationError('Сотрудник с таким email уже существует.')
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        email = cleaned_data.get('email')
        
        # Синхронизируем email с email пользователя, если они не совпадают
        if user and email and user.email != email:
            # Можно предупредить или автоматически синхронизировать
            pass

        return cleaned_data

    def save(self, commit=True):
        employee = super().save(commit=False)
        if commit:
            employee.save()
            self._sync_linked_user(employee)
        return employee

    def _sync_linked_user(self, employee):
        """Карточка сотрудника — источник правды; синхронизируем связанный аккаунт User."""
        user = employee.user
        if not user:
            return
        user.first_name = employee.first_name
        user.last_name = employee.last_name
        user.middle_name = employee.middle_name or ''
        user.phone = employee.phone
        user.date_of_birth = employee.date_of_birth
        if employee.email and user.email != employee.email:
            new_email = employee.email.lower()
            if not User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
                user.email = new_email
                user.username = new_email
        user.save()


class VacancyForm(forms.ModelForm):
    """Форма для создания/редактирования вакансии"""
    position_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'list': 'position_list',
            'placeholder': 'Выберите или введите название должности'
        }),
        label='Должность'
    )
    department_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'list': 'department_list',
            'placeholder': 'Выберите или введите название отдела'
        }),
        label='Отдел'
    )
    
    class Meta:
        model = Vacancy
        fields = [
            'title', 'description', 'salary_min', 'salary_max',
            'status', 'position', 'department'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'salary_min': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'salary_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'position': forms.HiddenInput(),
            'department': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Делаем position и department необязательными, так как они создаются из position_name и department_name
        self.fields['position'].required = False
        self.fields['department'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        salary_min = cleaned_data.get('salary_min')
        salary_max = cleaned_data.get('salary_max')
        
        if salary_min and salary_max and salary_min > salary_max:
            raise ValidationError('Минимальная зарплата не может быть больше максимальной.')
        
        # Обработка должности
        position_name = cleaned_data.get('position_name', '').strip()
        if position_name:
            position, created = Position.objects.get_or_create(name=position_name)
            cleaned_data['position'] = position
        
        # Обработка отдела
        department_name = cleaned_data.get('department_name', '').strip()
        if department_name:
            department, created = Department.objects.get_or_create(name=department_name)
            cleaned_data['department'] = department
        
        return cleaned_data


class TrainingForm(forms.ModelForm):
    """Форма для создания/редактирования обучения"""
    
    # Явно определяем поля дат с правильным форматом для HTML5 date input
    start_date = forms.DateField(
        widget=forms.DateInput(
            attrs={'class': 'form-control', 'type': 'date'},
            format='%Y-%m-%d'
        ),
        input_formats=['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y'],
        required=True
    )
    end_date = forms.DateField(
        widget=forms.DateInput(
            attrs={'class': 'form-control', 'type': 'date'},
            format='%Y-%m-%d'
        ),
        input_formats=['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y'],
        required=True
    )
    
    # Поле участников - скрытое, управляется через модальное окно
    participants = forms.ModelMultipleChoiceField(
        queryset=Employee.objects.filter(user__isnull=False).order_by('last_name', 'first_name'),
        widget=forms.MultipleHiddenInput(attrs={'id': 'id_participants'}),
        required=False
    )
    
    class Meta:
        model = Training
        fields = [
            'title', 'description', 'responsible', 'start_date',
            'end_date', 'status', 'participants'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'responsible': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise ValidationError('Дата начала не может быть позже даты окончания.')
        
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        UserModel = get_user_model()
        if 'responsible' in self.fields:
            self.fields['responsible'].queryset = UserModel.objects.filter(
                Q(role='hr_manager') | Q(is_superuser=True)
            ).order_by('username')

    def clean_responsible(self):
        resp = self.cleaned_data.get('responsible')
        if resp and not (getattr(resp, 'is_superuser', False) or getattr(resp, 'role', None) == 'hr_manager'):
            from django.core.exceptions import ValidationError as _VE
            raise _VE('Ответственным может быть только HR-менеджер или суперпользователь.')
        return resp


class DepartmentForm(forms.ModelForm):
    """Форма для создания/редактирования отдела"""
    class Meta:
        model = Department
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class PositionForm(forms.ModelForm):
    """Форма для создания/редактирования должности"""
    class Meta:
        model = Position
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

