// Категории для доходов и расходов
const categories = {
    income: ['Зарплата', 'Подарки', 'Инвестиции', 'Другое'],
    expense: ['Продукты', 'Транспорт', 'Развлечения', 'Здоровье', 'Образование', 'Коммунальные', 'Одежда', 'Другое']
};

// Инициализация данных
let transactions = JSON.parse(localStorage.getItem('transactions')) || [];
let budgets = JSON.parse(localStorage.getItem('budgets')) || [];
let goals = JSON.parse(localStorage.getItem('goals')) || [];

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

function initializeApp() {
    setupTabs();
    setupForms();
    populateCategories();
    updateBalance();
    renderTransactions();
    renderBudgets();
    renderGoals();
    setupReportFilters();
    setDefaultDates();
}

// Настройка вкладок
function setupTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
        });
    });
}

// Настройка форм
function setupForms() {
    // Форма транзакций
    document.getElementById('transactionForm').addEventListener('submit', (e) => {
        e.preventDefault();
        addTransaction();
    });

    // Форма бюджетов
    document.getElementById('budgetForm').addEventListener('submit', (e) => {
        e.preventDefault();
        addBudget();
    });

    // Форма целей
    document.getElementById('goalForm').addEventListener('submit', (e) => {
        e.preventDefault();
        addGoal();
    });

    // Фильтры транзакций
    document.getElementById('filterType').addEventListener('change', renderTransactions);
    document.getElementById('filterCategory').addEventListener('change', renderTransactions);
}

// Заполнение категорий
function populateCategories() {
    const transactionCategory = document.getElementById('transactionCategory');
    const budgetCategory = document.getElementById('budgetCategory');
    const filterCategory = document.getElementById('filterCategory');

    // Для транзакций
    const typeSelect = document.getElementById('transactionType');
    typeSelect.addEventListener('change', () => {
        const type = typeSelect.value;
        transactionCategory.innerHTML = '<option value="">Выберите категорию</option>';
        categories[type].forEach(cat => {
            const option = document.createElement('option');
            option.value = cat;
            option.textContent = cat;
            transactionCategory.appendChild(option);
        });
    });
    typeSelect.dispatchEvent(new Event('change'));

    // Для бюджетов
    categories.expense.forEach(cat => {
        const option = document.createElement('option');
        option.value = cat;
        option.textContent = cat;
        budgetCategory.appendChild(option.cloneNode(true));
    });

    // Для фильтров
    const allCategories = [...categories.income, ...categories.expense];
    allCategories.forEach(cat => {
        const option = document.createElement('option');
        option.value = cat;
        option.textContent = cat;
        filterCategory.appendChild(option);
    });
}

// Добавление транзакции
function addTransaction() {
    const type = document.getElementById('transactionType').value;
    const category = document.getElementById('transactionCategory').value;
    const amount = parseFloat(document.getElementById('transactionAmount').value);
    const description = document.getElementById('transactionDescription').value;
    const date = document.getElementById('transactionDate').value;

    const transaction = {
        id: Date.now(),
        type,
        category,
        amount,
        description,
        date
    };

    transactions.push(transaction);
    saveData();
    updateBalance();
    renderTransactions();
    renderBudgets();
    document.getElementById('transactionForm').reset();
}

// Добавление бюджета
function addBudget() {
    const category = document.getElementById('budgetCategory').value;
    const limit = parseFloat(document.getElementById('budgetLimit').value);
    const period = document.getElementById('budgetPeriod').value;

    const budget = {
        id: Date.now(),
        category,
        limit,
        period,
        createdAt: new Date().toISOString()
    };

    budgets.push(budget);
    saveData();
    renderBudgets();
    document.getElementById('budgetForm').reset();
}

// Добавление цели
function addGoal() {
    const name = document.getElementById('goalName').value;
    const amount = parseFloat(document.getElementById('goalAmount').value);
    const current = parseFloat(document.getElementById('goalCurrent').value) || 0;
    const deadline = document.getElementById('goalDeadline').value;

    const goal = {
        id: Date.now(),
        name,
        amount,
        current,
        deadline
    };

    goals.push(goal);
    saveData();
    renderGoals();
    document.getElementById('goalForm').reset();
}

// Обновление баланса
function updateBalance() {
    const totalIncome = transactions
        .filter(t => t.type === 'income')
        .reduce((sum, t) => sum + t.amount, 0);

    const totalExpense = transactions
        .filter(t => t.type === 'expense')
        .reduce((sum, t) => sum + t.amount, 0);

    const balance = totalIncome - totalExpense;

    document.getElementById('totalIncome').textContent = formatCurrency(totalIncome);
    document.getElementById('totalExpense').textContent = formatCurrency(totalExpense);
    document.getElementById('totalBalance').textContent = formatCurrency(balance);
}

// Отображение транзакций
function renderTransactions() {
    const list = document.getElementById('transactionsList');
    const filterType = document.getElementById('filterType').value;
    const filterCategory = document.getElementById('filterCategory').value;

    let filtered = transactions;

    if (filterType !== 'all') {
        filtered = filtered.filter(t => t.type === filterType);
    }

    if (filterCategory !== 'all') {
        filtered = filtered.filter(t => t.category === filterCategory);
    }

    // Сортировка по дате (новые сначала)
    filtered.sort((a, b) => new Date(b.date) - new Date(a.date));

    if (filtered.length === 0) {
        list.innerHTML = '<div class="empty-state">Нет транзакций</div>';
        return;
    }

    list.innerHTML = filtered.map(transaction => `
        <div class="transaction-item ${transaction.type}">
            <div class="transaction-info">
                <div class="transaction-category">${transaction.category}</div>
                <div class="transaction-description">${transaction.description}</div>
                <div class="transaction-date">${formatDate(transaction.date)}</div>
            </div>
            <div class="transaction-amount ${transaction.type}">
                ${transaction.type === 'income' ? '+' : '-'}${formatCurrency(transaction.amount)}
            </div>
            <button class="btn btn-danger" onclick="deleteTransaction(${transaction.id})">Удалить</button>
        </div>
    `).join('');
}

// Отображение бюджетов
function renderBudgets() {
    const list = document.getElementById('budgetsList');

    if (budgets.length === 0) {
        list.innerHTML = '<div class="empty-state">Нет бюджетов</div>';
        return;
    }

    list.innerHTML = budgets.map(budget => {
        const periodStart = getPeriodStart(budget.period, budget.createdAt);
        const periodExpenses = getPeriodExpenses(budget.category, periodStart, budget.period);
        const percentage = (periodExpenses / budget.limit) * 100;
        const status = percentage >= 100 ? 'danger' : percentage >= 80 ? 'warning' : '';

        return `
            <div class="budget-item">
                <div class="budget-info">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-weight: 600; color: #374151; margin-bottom: 5px;">${budget.category}</div>
                            <div style="color: #6b7280; font-size: 0.9em;">
                                Лимит: ${formatCurrency(budget.limit)} / ${budget.period === 'month' ? 'месяц' : 'неделя'}
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 1.2em; font-weight: bold; color: #374151;">
                                ${formatCurrency(periodExpenses)} / ${formatCurrency(budget.limit)}
                            </div>
                            <div style="color: #6b7280; font-size: 0.9em;">${percentage.toFixed(1)}%</div>
                        </div>
                    </div>
                    <div class="budget-progress">
                        <div class="budget-progress-bar ${status}" style="width: ${Math.min(percentage, 100)}%"></div>
                    </div>
                </div>
                <button class="btn btn-danger" onclick="deleteBudget(${budget.id})">Удалить</button>
            </div>
        `;
    }).join('');
}

// Отображение целей
function renderGoals() {
    const list = document.getElementById('goalsList');

    if (goals.length === 0) {
        list.innerHTML = '<div class="empty-state">Нет целей</div>';
        return;
    }

    list.innerHTML = goals.map(goal => {
        const percentage = (goal.current / goal.amount) * 100;
        const daysLeft = Math.ceil((new Date(goal.deadline) - new Date()) / (1000 * 60 * 60 * 24));
        const isOverdue = daysLeft < 0;

        return `
            <div class="goal-item">
                <div class="goal-info">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <div style="font-weight: 600; color: #374151; font-size: 1.1em;">${goal.name}</div>
                        <div style="text-align: right;">
                            <div style="font-size: 1.2em; font-weight: bold; color: #374151;">
                                ${formatCurrency(goal.current)} / ${formatCurrency(goal.amount)}
                            </div>
                            <div style="color: ${isOverdue ? '#ef4444' : '#6b7280'}; font-size: 0.9em;">
                                ${isOverdue ? 'Просрочено' : `Осталось ${daysLeft} дн.`}
                            </div>
                        </div>
                    </div>
                    <div class="goal-progress">
                        <div class="goal-progress-bar" style="width: ${Math.min(percentage, 100)}%">
                            ${percentage.toFixed(1)}%
                        </div>
                    </div>
                </div>
                <button class="btn btn-danger" onclick="deleteGoal(${goal.id})">Удалить</button>
            </div>
        `;
    }).join('');
}

// Настройка фильтров отчетов
function setupReportFilters() {
    document.getElementById('generateReport').addEventListener('click', generateReport);
}

// Установка дат по умолчанию
function setDefaultDates() {
    const today = new Date();
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
    const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);

    document.getElementById('transactionDate').valueAsDate = today;
    document.getElementById('reportStartDate').valueAsDate = firstDay;
    document.getElementById('reportEndDate').valueAsDate = lastDay;
}

// Генерация отчета
function generateReport() {
    const startDate = document.getElementById('reportStartDate').value;
    const endDate = document.getElementById('reportEndDate').value;

    const filtered = transactions.filter(t => {
        const tDate = new Date(t.date);
        return tDate >= new Date(startDate) && tDate <= new Date(endDate);
    });

    // Расходы по категориям
    const expensesByCategory = {};
    filtered.filter(t => t.type === 'expense').forEach(t => {
        expensesByCategory[t.category] = (expensesByCategory[t.category] || 0) + t.amount;
    });

    const expensesContainer = document.getElementById('expensesByCategory');
    if (Object.keys(expensesByCategory).length === 0) {
        expensesContainer.innerHTML = '<div class="empty-state">Нет данных за выбранный период</div>';
    } else {
        const maxExpense = Math.max(...Object.values(expensesByCategory));
        expensesContainer.innerHTML = Object.entries(expensesByCategory)
            .sort((a, b) => b[1] - a[1])
            .map(([category, amount]) => {
                const percentage = (amount / maxExpense) * 100;
                return `
                    <div class="chart-item">
                        <div class="chart-label">${category}</div>
                        <div class="chart-bar-container">
                            <div class="chart-bar" style="width: ${percentage}%">${percentage.toFixed(0)}%</div>
                        </div>
                        <div class="chart-value">${formatCurrency(amount)}</div>
                    </div>
                `;
            }).join('');
    }

    // Динамика доходов и расходов
    const incomeExpenseData = {};
    filtered.forEach(t => {
        const date = t.date;
        if (!incomeExpenseData[date]) {
            incomeExpenseData[date] = { income: 0, expense: 0 };
        }
        if (t.type === 'income') {
            incomeExpenseData[date].income += t.amount;
        } else {
            incomeExpenseData[date].expense += t.amount;
        }
    });

    const incomeExpenseContainer = document.getElementById('incomeExpenseChart');
    const dates = Object.keys(incomeExpenseData).sort();
    if (dates.length === 0) {
        incomeExpenseContainer.innerHTML = '<div class="empty-state">Нет данных за выбранный период</div>';
    } else {
        const maxValue = Math.max(
            ...dates.map(d => incomeExpenseData[d].income + incomeExpenseData[d].expense)
        );
        incomeExpenseContainer.innerHTML = dates.map(date => {
            const data = incomeExpenseData[date];
            const total = data.income + data.expense;
            const percentage = (total / maxValue) * 100;
            return `
                <div class="chart-item">
                    <div class="chart-label">${formatDate(date)}</div>
                    <div class="chart-bar-container">
                        <div class="chart-bar" style="width: ${percentage}%">
                            Доход: ${formatCurrency(data.income)} | Расход: ${formatCurrency(data.expense)}
                        </div>
                    </div>
                    <div class="chart-value">${formatCurrency(total)}</div>
                </div>
            `;
        }).join('');
    }
}

// Вспомогательные функции
function deleteTransaction(id) {
    if (confirm('Удалить эту транзакцию?')) {
        transactions = transactions.filter(t => t.id !== id);
        saveData();
        updateBalance();
        renderTransactions();
        renderBudgets();
    }
}

function deleteBudget(id) {
    if (confirm('Удалить этот бюджет?')) {
        budgets = budgets.filter(b => b.id !== id);
        saveData();
        renderBudgets();
    }
}

function deleteGoal(id) {
    if (confirm('Удалить эту цель?')) {
        goals = goals.filter(g => g.id !== id);
        saveData();
        renderGoals();
    }
}

function getPeriodStart(period, createdAt) {
    const date = new Date(createdAt);
    if (period === 'week') {
        const day = date.getDay();
        const diff = date.getDate() - day + (day === 0 ? -6 : 1);
        return new Date(date.setDate(diff));
    } else {
        return new Date(date.getFullYear(), date.getMonth(), 1);
    }
}

function getPeriodExpenses(category, periodStart, period) {
    const periodEnd = new Date(periodStart);
    if (period === 'week') {
        periodEnd.setDate(periodEnd.getDate() + 7);
    } else {
        periodEnd.setMonth(periodEnd.getMonth() + 1);
    }

    return transactions
        .filter(t => 
            t.type === 'expense' &&
            t.category === category &&
            new Date(t.date) >= periodStart &&
            new Date(t.date) < periodEnd
        )
        .reduce((sum, t) => sum + t.amount, 0);
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB',
        minimumFractionDigits: 0
    }).format(amount);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

function saveData() {
    localStorage.setItem('transactions', JSON.stringify(transactions));
    localStorage.setItem('budgets', JSON.stringify(budgets));
    localStorage.setItem('goals', JSON.stringify(goals));
}

