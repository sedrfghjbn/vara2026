-- SQL схема для системы автоматизации отдела кадров
-- База данных: SQLite (для разработки) или PostgreSQL/MySQL (для продакшена)

-- Таблица пользователей (расширенная модель User)
CREATE TABLE IF NOT EXISTS hr_user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    password VARCHAR(128) NOT NULL,
    last_login DATETIME,
    is_superuser BOOLEAN NOT NULL DEFAULT 0,
    username VARCHAR(150) UNIQUE NOT NULL,
    first_name VARCHAR(150),
    last_name VARCHAR(150),
    email VARCHAR(254) UNIQUE NOT NULL,
    is_staff BOOLEAN NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    date_joined DATETIME NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'employee',
    phone VARCHAR(20),
    CHECK (role IN ('admin', 'hr_manager', 'employee'))
);

-- Таблица отделов
CREATE TABLE IF NOT EXISTS hr_department (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) UNIQUE NOT NULL,
    description TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Таблица должностей
CREATE TABLE IF NOT EXISTS hr_position (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) UNIQUE NOT NULL,
    description TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Таблица сотрудников
CREATE TABLE IF NOT EXISTS hr_employee (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    first_name VARCHAR(150) NOT NULL,
    last_name VARCHAR(150) NOT NULL,
    middle_name VARCHAR(150),
    date_of_birth DATE NOT NULL,
    email VARCHAR(254) UNIQUE NOT NULL,
    phone VARCHAR(20) NOT NULL,
    position_id INTEGER,
    department_id INTEGER,
    hire_date DATE NOT NULL DEFAULT CURRENT_DATE,
    photo VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES hr_user(id) ON DELETE SET NULL,
    FOREIGN KEY (position_id) REFERENCES hr_position(id) ON DELETE SET NULL,
    FOREIGN KEY (department_id) REFERENCES hr_department(id) ON DELETE SET NULL,
    CHECK (status IN ('active', 'on_leave', 'sick_leave', 'dismissed'))
);

-- Таблица вакансий
CREATE TABLE IF NOT EXISTS hr_vacancy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    salary_min DECIMAL(10, 2),
    salary_max DECIMAL(10, 2),
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    hr_manager_id INTEGER,
    position_id INTEGER,
    department_id INTEGER,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at DATETIME,
    FOREIGN KEY (hr_manager_id) REFERENCES hr_user(id) ON DELETE SET NULL,
    FOREIGN KEY (position_id) REFERENCES hr_position(id) ON DELETE SET NULL,
    FOREIGN KEY (department_id) REFERENCES hr_department(id) ON DELETE SET NULL,
    CHECK (status IN ('open', 'closed', 'archived'))
);

-- Таблица обучения
CREATE TABLE IF NOT EXISTS hr_training (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    responsible_id INTEGER,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'planned',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (responsible_id) REFERENCES hr_user(id) ON DELETE SET NULL,
    CHECK (status IN ('planned', 'in_progress', 'completed', 'cancelled')),
    CHECK (start_date <= end_date)
);

-- Связующая таблица для участников обучения (Many-to-Many)
CREATE TABLE IF NOT EXISTS hr_training_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    training_id INTEGER NOT NULL,
    employee_id INTEGER NOT NULL,
    FOREIGN KEY (training_id) REFERENCES hr_training(id) ON DELETE CASCADE,
    FOREIGN KEY (employee_id) REFERENCES hr_employee(id) ON DELETE CASCADE,
    UNIQUE(training_id, employee_id)
);

-- Таблица сертификатов
CREATE TABLE IF NOT EXISTS hr_certificate (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    training_id INTEGER NOT NULL,
    document VARCHAR(100) NOT NULL,
    issue_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES hr_employee(id) ON DELETE CASCADE,
    FOREIGN KEY (training_id) REFERENCES hr_training(id) ON DELETE CASCADE,
    UNIQUE(employee_id, training_id)
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_employee_email ON hr_employee(email);
CREATE INDEX IF NOT EXISTS idx_employee_status ON hr_employee(status);
CREATE INDEX IF NOT EXISTS idx_employee_department ON hr_employee(department_id);
CREATE INDEX IF NOT EXISTS idx_employee_position ON hr_employee(position_id);
CREATE INDEX IF NOT EXISTS idx_vacancy_status ON hr_vacancy(status);
CREATE INDEX IF NOT EXISTS idx_training_status ON hr_training(status);
CREATE INDEX IF NOT EXISTS idx_training_dates ON hr_training(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_user_role ON hr_user(role);

-- Примеры данных для тестирования
-- Вставка тестовых отделов
INSERT OR IGNORE INTO hr_department (name, description) VALUES
('IT отдел', 'Отдел информационных технологий'),
('HR отдел', 'Отдел кадров'),
('Финансы', 'Финансовый отдел'),
('Маркетинг', 'Отдел маркетинга');

-- Вставка тестовых должностей
INSERT OR IGNORE INTO hr_position (name, description) VALUES
('Разработчик', 'Разработчик программного обеспечения'),
('HR-менеджер', 'Менеджер по персоналу'),
('Бухгалтер', 'Бухгалтер'),
('Маркетолог', 'Специалист по маркетингу'),
('Директор', 'Руководитель отдела');

