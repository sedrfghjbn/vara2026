from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Sum, Q
from django.utils import timezone
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import datetime, timedelta, date
from .models import Transaction, Budget, Goal, Category
from .forms import TransactionForm, BudgetForm, GoalForm, RegisterForm, LoginForm, CategoryForm

# Стандартные категории (для новых пользователей)
DEFAULT_CATEGORIES = {
    'income': ['Зарплата', 'Подарки', 'Инвестиции', 'Другое'],
    'expense': ['Продукты', 'Транспорт', 'Развлечения', 'Здоровье', 'Образование', 'Коммунальные', 'Одежда', 'Другое']
}


@login_required
def index(request):
    # Получаем выбранный месяц и год из GET-параметров
    selected_month = request.GET.get('month')
    selected_year = request.GET.get('year')
    
    # Если месяц не выбран в GET, проверяем сессию
    if not selected_month or not selected_year:
        selected_month = request.session.get('selected_month')
        selected_year = request.session.get('selected_year')
    
    # Если в сессии тоже нет, используем текущий месяц
    if not selected_month or not selected_year:
        today = timezone.now().date()
        selected_month = today.month
        selected_year = today.year
    else:
        # Преобразуем в int, если пришли из GET или сессии
        selected_month = int(selected_month)
        selected_year = int(selected_year)
    
    # Сохраняем выбранный месяц и год в сессию
    request.session['selected_month'] = selected_month
    request.session['selected_year'] = selected_year
    
    # Определяем начало и конец выбранного месяца
    month_start = timezone.datetime(selected_year, selected_month, 1).date()
    if selected_month == 12:
        month_end = timezone.datetime(selected_year + 1, 1, 1).date()
    else:
        month_end = timezone.datetime(selected_year, selected_month + 1, 1).date()
    
    # Фильтруем транзакции по выбранному месяцу
    transactions = Transaction.objects.filter(
        user=request.user,
        date__gte=month_start,
        date__lt=month_end
    ).order_by('-date', '-id')[:50]
    
    budgets = Budget.objects.filter(user=request.user)
    goals = Goal.objects.filter(user=request.user)

    # Расчет баланса за ВЫБРАННЫЙ МЕСЯЦ
    total_income = Transaction.objects.filter(
        user=request.user, 
        type='income',
        date__gte=month_start,
        date__lt=month_end
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    total_expense = Transaction.objects.filter(
        user=request.user, 
        type='expense',
        date__gte=month_start,
        date__lt=month_end
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Общий баланс (накопленный) - только до конца выбранного месяца включительно
    total_balance_income = Transaction.objects.filter(
        user=request.user, 
        type='income',
        date__lte=month_end - timedelta(days=1)  # До конца выбранного месяца
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    total_balance_expense = Transaction.objects.filter(
        user=request.user, 
        type='expense',
        date__lte=month_end - timedelta(days=1)  # До конца выбранного месяца
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    balance = total_balance_income - total_balance_expense

    # Расчет расходов для бюджетов
    budgets_with_expenses = []
    for budget in budgets:
        period_start = get_period_start(budget.period, budget.created_at.date())
        period_expenses = get_period_expenses(budget.category, period_start, budget.period, request.user)
        percentage = (float(period_expenses) / float(budget.limit)) * 100 if budget.limit > 0 else 0
        budgets_with_expenses.append({
            'budget': budget,
            'expenses': period_expenses,
            'percentage': percentage
        })

    # Фильтры
    filter_type = request.GET.get('filter_type', 'all')
    filter_category = request.GET.get('filter_category', 'all')

    if filter_type != 'all':
        transactions = transactions.filter(type=filter_type)
    if filter_category != 'all':
        transactions = transactions.filter(category=filter_category)

    # Генерируем список месяцев для выпадающего списка (последние 12 месяцев)
    months = []
    today = timezone.now().date()
    current_year = today.year
    current_month = today.month
    
    month_names = {
        1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
        5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
        9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
    }
    
    for i in range(12):
        year = current_year
        month = current_month - i
        
        while month <= 0:
            month += 12
            year -= 1
        
        months.append({
            'value': f"{year}-{month:02d}",
            'label': f"{month_names[month]} {year}",
            'year': year,
            'month': month
        })

    # Получаем категории пользователя из БД
    user_categories = Category.objects.filter(user=request.user)
    categories = {
        'income': [cat.name for cat in user_categories.filter(type='income')],
        'expense': [cat.name for cat in user_categories.filter(type='expense')]
    }
    
    # Если у пользователя нет категорий, используем стандартные
    if not categories['income'] and not categories['expense']:
        categories = DEFAULT_CATEGORIES
    
    context = {
        'transactions': transactions,
        'budgets_with_expenses': budgets_with_expenses,
        'goals': goals,
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'categories': categories,
        'filter_type': filter_type,
        'filter_category': filter_category,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'months': months,
        'user_categories': user_categories,
    }
    return render(request, 'finance/index.html', context)


@login_required
def add_transaction(request):
    if request.method == 'POST':
        transaction = Transaction(
            user=request.user,
            type=request.POST.get('type'),
            category=request.POST.get('category'),
            amount=request.POST.get('amount'),
            description=request.POST.get('description', '').strip(),
            date=request.POST.get('date')
        )
        transaction.save()
        messages.success(request, 'Транзакция добавлена!')
    return redirect('index')


@login_required
def edit_transaction(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    if request.method == 'POST':
        transaction.type = request.POST.get('type')
        transaction.category = request.POST.get('category')
        transaction.amount = request.POST.get('amount')
        transaction.description = request.POST.get('description', '').strip()
        transaction.date = request.POST.get('date')
        transaction.save()
        messages.success(request, 'Транзакция обновлена!')
        return redirect('index')
    return redirect('index')


@login_required
def delete_transaction(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    if request.method == 'POST':
        transaction.delete()
        messages.success(request, 'Транзакция удалена!')
    return redirect('index')


@login_required
def add_budget(request):
    if request.method == 'POST':
        budget = Budget(
            user=request.user,
            category=request.POST.get('category'),
            limit=request.POST.get('limit'),
            period=request.POST.get('period')
        )
        budget.save()
        messages.success(request, 'Бюджет создан!')
    return redirect('index')


@login_required
def edit_budget(request, budget_id):
    budget = get_object_or_404(Budget, id=budget_id, user=request.user)
    if request.method == 'POST':
        budget.category = request.POST.get('category')
        budget.limit = request.POST.get('limit')
        budget.period = request.POST.get('period')
        budget.save()
        messages.success(request, 'Бюджет обновлен!')
        return redirect('index')
    return redirect('index')


@login_required
def delete_budget(request, budget_id):
    budget = get_object_or_404(Budget, id=budget_id, user=request.user)
    if request.method == 'POST':
        budget.delete()
        messages.success(request, 'Бюджет удален!')
    return redirect('index')


@login_required
def add_goal(request):
    if request.method == 'POST':
        goal = Goal(
            user=request.user,
            name=request.POST.get('name'),
            amount=request.POST.get('amount'),
            current=request.POST.get('current', 0),
            deadline=request.POST.get('deadline')
        )
        goal.save()
        messages.success(request, 'Цель создана!')
    return redirect('index')


@login_required
def delete_goal(request, goal_id):
    goal = get_object_or_404(Goal, id=goal_id, user=request.user)
    if request.method == 'POST':
        goal.delete()
        messages.success(request, 'Цель удалена!')
    return redirect('index')


@login_required
def update_goal(request, goal_id):
    goal = get_object_or_404(Goal, id=goal_id, user=request.user)
    if request.method == 'POST':
        current = request.POST.get('current', 0)
        try:
            goal.current = float(current)
            goal.save()
            messages.success(request, 'Цель обновлена!')
        except ValueError:
            pass
    return redirect('index')


def get_period_start(period, created_at):
    """Получить начало периода для бюджета"""
    from datetime import date
    if isinstance(created_at, date):
        created_date = created_at
    else:
        created_date = created_at.date() if hasattr(created_at, 'date') else created_at
    
    if period == 'week':
        # Начало недели (понедельник)
        days_since_monday = created_date.weekday()
        return created_date - timedelta(days=days_since_monday)
    else:
        # Начало месяца
        return date(created_date.year, created_date.month, 1)


def get_period_expenses(category, period_start, period, user):
    """Получить расходы за период"""
    from datetime import date
    if isinstance(period_start, date):
        period_start = period_start
    else:
        period_start = period_start.date() if hasattr(period_start, 'date') else period_start
    
    if period == 'week':
        period_end = period_start + timedelta(days=7)
    else:
        # Следующий месяц
        if period_start.month == 12:
            period_end = date(period_start.year + 1, 1, 1)
        else:
            period_end = date(period_start.year, period_start.month + 1, 1)

    result = Transaction.objects.filter(
        user=user,
        type='expense',
        category=category,
        date__gte=period_start,
        date__lt=period_end
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    return float(result)


@login_required
def report(request):
    # Используем выбранный месяц/год из сессии или GET параметров
    selected_month = request.GET.get('month') or request.session.get('selected_month')
    selected_year = request.GET.get('year') or request.session.get('selected_year')
    
    if selected_month and selected_year:
        selected_month = int(selected_month)
        selected_year = int(selected_year)
        # Сохраняем в сессию
        request.session['selected_month'] = selected_month
        request.session['selected_year'] = selected_year
    else:
        # По умолчанию текущий месяц
        today = timezone.now().date()
        selected_month = today.month
        selected_year = today.year
    
    # Формируем диапазон дат для выбранного месяца
    from calendar import monthrange
    start_date = date(selected_year, selected_month, 1)
    last_day = monthrange(selected_year, selected_month)[1]
    end_date = date(selected_year, selected_month, last_day)

    # Общая статистика
    total_income = Transaction.objects.filter(
        user=request.user,
        type='income',
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    total_expense = Transaction.objects.filter(
        user=request.user,
        type='expense',
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    balance = float(total_income) - float(total_expense)
    
    # Количество дней в периоде
    days_count = (end_date - start_date).days + 1
    
    # Средние значения
    avg_income_per_day = float(total_income) / days_count if days_count > 0 else 0
    avg_expense_per_day = float(total_expense) / days_count if days_count > 0 else 0
    
    # Количество транзакций
    income_count = Transaction.objects.filter(
        user=request.user,
        type='income',
        date__gte=start_date,
        date__lte=end_date
    ).count()
    
    expense_count = Transaction.objects.filter(
        user=request.user,
        type='expense',
        date__gte=start_date,
        date__lte=end_date
    ).count()
    
    # Расходы по категориям
    expenses_by_category = Transaction.objects.filter(
        user=request.user,
        type='expense',
        date__gte=start_date,
        date__lte=end_date
    ).values('category').annotate(total=Sum('amount')).order_by('-total')
    
    # Доходы по категориям
    income_by_category = Transaction.objects.filter(
        user=request.user,
        type='income',
        date__gte=start_date,
        date__lte=end_date
    ).values('category').annotate(total=Sum('amount')).order_by('-total')
    
    # Максимальная сумма расходов для нормализации графиков
    max_expense = expenses_by_category.first()['total'] if expenses_by_category else 1
    
    # Динамика доходов и расходов по дням
    daily_data = Transaction.objects.filter(
        user=request.user,
        date__gte=start_date,
        date__lte=end_date
    ).values('date', 'type').annotate(total=Sum('amount')).order_by('date')

    # Группировка по датам
    income_expense_data = {}
    for item in daily_data:
        date_str = item['date'].strftime('%Y-%m-%d')
        if date_str not in income_expense_data:
            income_expense_data[date_str] = {'income': 0, 'expense': 0}
        income_expense_data[date_str][item['type']] = float(item['total'])
    
    # Топ-5 категорий расходов
    top_expenses = list(expenses_by_category[:5])
    
    # Топ-5 категорий доходов
    top_income = list(income_by_category[:5])

    # Генерируем список месяцев для выпадающего списка (последние 12 месяцев)
    months = []
    today = timezone.now().date()
    current_year = today.year
    current_month = today.month
    
    month_names = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                   'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    
    for i in range(12):
        month = current_month - i
        year = current_year
        if month <= 0:
            month += 12
            year -= 1
        months.append({
            'month': month,
            'year': year,
            'label': f"{month_names[month - 1]} {year}"
        })
    
    context = {
        'expenses': expenses_by_category,
        'income_by_category': income_by_category,
        'income_expense_data': income_expense_data,
        'start_date': start_date,
        'end_date': end_date,
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'days_count': days_count,
        'avg_income_per_day': avg_income_per_day,
        'avg_expense_per_day': avg_expense_per_day,
        'income_count': income_count,
        'expense_count': expense_count,
        'max_expense': max_expense,
        'top_expenses': top_expenses,
        'top_income': top_income,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'months': months,
        'month_name': month_names[selected_month - 1],
    }
    return render(request, 'finance/report.html', context)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Аккаунт создан для {username}! Теперь вы можете войти.')
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'finance/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {username}!')
                return redirect('index')
            else:
                messages.error(request, 'Неверное имя пользователя или пароль.')
    else:
        form = LoginForm()
    return render(request, 'finance/login.html', {'form': form})


from django.contrib.auth import logout

def logout_view(request):
    logout(request)
    messages.success(request, 'Вы вышли из системы.')
    return redirect('login')


@login_required
def add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category_type = request.POST.get('type')
        
        if name and category_type:
            # Проверяем, не существует ли уже такая категория
            existing = Category.objects.filter(
                user=request.user,
                name=name,
                type=category_type
            ).first()
            
            if existing:
                messages.error(request, 'Категория с таким именем уже существует!')
            else:
                category = Category.objects.create(
                    user=request.user,
                    name=name,
                    type=category_type
                )
                messages.success(request, f'Категория "{name}" успешно добавлена!')
        else:
            messages.error(request, 'Заполните все поля!')
    
    return redirect('index')


@login_required
def delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id, user=request.user)
    category_name = category.name
    category.delete()
    messages.success(request, f'Категория "{category_name}" удалена!')
    return redirect('index')

