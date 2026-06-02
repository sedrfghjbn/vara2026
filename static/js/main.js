// Простой JS для работы с вкладками и категориями
document.addEventListener('DOMContentLoaded', function() {
    // Заполнение категорий при изменении типа транзакции
    const transactionType = document.getElementById('transactionType');
    const transactionCategory = document.getElementById('transactionCategory');
    
    if (transactionType && transactionCategory) {
        const categories = {
            income: ['Зарплата', 'Подарки', 'Инвестиции', 'Другое'],
            expense: ['Продукты', 'Транспорт', 'Развлечения', 'Здоровье', 'Образование', 'Коммунальные', 'Одежда', 'Другое']
        };
        
        transactionType.addEventListener('change', function() {
            const type = this.value;
            transactionCategory.innerHTML = '<option value="">Выберите категорию</option>';
            
            categories[type].forEach(function(cat) {
                const option = document.createElement('option');
                option.value = cat;
                option.textContent = cat;
                transactionCategory.appendChild(option);
            });
        });
        
        // Инициализация при загрузке
        if (transactionType.value) {
            transactionType.dispatchEvent(new Event('change'));
        }
    }
    
    // Установка даты по умолчанию
    const transactionDate = document.getElementById('transactionDate');
    if (transactionDate && !transactionDate.value) {
        const today = new Date();
        transactionDate.valueAsDate = today;
    }
    
    // Работа с якорями для вкладок
    if (window.location.hash) {
        const hash = window.location.hash.substring(1);
        const targetTab = document.getElementById(hash);
        if (targetTab) {
            document.querySelectorAll('.tab-content').forEach(function(tab) {
                tab.classList.remove('active');
            });
            targetTab.classList.add('active');
        }
    }

    // Маска телефона +7(999)999-99-99
    const phoneInputs = document.querySelectorAll('input[name="phone"]');
    const formatPhone = (value) => {
        let digits = (value || '').replace(/\D/g, '');
        if (digits.startsWith('8')) {
            digits = '7' + digits.slice(1);
        }
        if (!digits.startsWith('7')) {
            digits = '7' + digits;
        }
        digits = digits.slice(0, 11);

        let result = '+7(';
        if (digits.length > 1) result += digits.slice(1, 4);
        if (digits.length >= 4) result += ')';
        if (digits.length > 4) result += digits.slice(4, 7);
        if (digits.length >= 7) result += '-';
        if (digits.length > 7) result += digits.slice(7, 9);
        if (digits.length >= 9) result += '-';
        if (digits.length > 9) result += digits.slice(9, 11);
        return result;
    };

    phoneInputs.forEach((input) => {
        input.addEventListener('input', (e) => {
            const currentPos = input.selectionStart;
            input.value = formatPhone(e.target.value);
            input.setSelectionRange(input.value.length, input.value.length);
        });
        input.addEventListener('blur', (e) => {
            if (e.target.value && e.target.value.trim() !== '+7(') {
                input.value = formatPhone(e.target.value);
            } else if (!e.target.value || e.target.value.trim() === '+7(') {
                input.value = '';
            }
        });
        // Инициализация при загрузке - форматируем только если есть значение
        if (input.value && input.value.trim() !== '+7(') {
            input.value = formatPhone(input.value);
        } else {
            input.value = '';
        }
    });
});

