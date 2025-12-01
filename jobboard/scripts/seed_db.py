#!/usr/bin/env python3
"""Seed script to (re)create `jobs.db` with demo data.

Usage (PowerShell):
  python scripts\seed_db.py
  # or set a different DB path via JOBS_DB env var
  $env:JOBS_DB = 'C:\path\to\jobs.db'; python scripts\seed_db.py

This script is safe for development: it removes the existing `jobs.db` file
before creating a fresh database with schema and sample rows.
"""
import os
import sqlite3
from werkzeug.security import generate_password_hash


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.environ.get('JOBS_DB', os.path.join(PROJECT_ROOT, 'jobs.db'))


SCHEMA_SQL = '''
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    is_employer INTEGER DEFAULT 0,
    email TEXT,
    avatar TEXT,
    about TEXT
);

CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id INTEGER,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    tags TEXT,
    salary TEXT,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (author_id) REFERENCES users(id)
);

CREATE TABLE responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER,
    user_id INTEGER,
    text TEXT,
    contact TEXT,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
'''


def main():
    if os.path.exists(DB_PATH):
        print(f'Removing existing DB: {DB_PATH}')
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Create schema
    for stmt in SCHEMA_SQL.strip().split(';'):
        s = stmt.strip()
        if not s:
            continue
        cur.execute(s)

    # Insert demo users
    pwd_hash = generate_password_hash('password123')
    users = [
        ('employer1', pwd_hash, 1, 'employer@example.com', 'Тестовый работодатель'),
        ('worker1', pwd_hash, 0, 'worker@example.com', 'Тестовый соискатель'),
    ]
    cur.executemany("INSERT INTO users (username, password, is_employer, email, about) VALUES (?, ?, ?, ?, ?)", users)
    conn.commit()

    # Grab user ids
    cur.execute("SELECT id FROM users WHERE username = ?", ('employer1',))
    employer_id = cur.fetchone()[0]
    cur.execute("SELECT id FROM users WHERE username = ?", ('worker1',))
    worker_id = cur.fetchone()[0]

    # Insert demo jobs
    jobs = [
        (employer_id, 'Бариста (подработка)', 'Требуется бариста на неполный рабочий день. Обучение бесплатно, гибкий график.', 'кафе,бариста,гибкий график', 'от 170 ₽/ч'),
        (employer_id, 'Курьер (самокат)', 'Курьерская доставка по району. Оплата за доставку + бонусы.', 'курьер,доставка,самокат', 'по договорённости'),
        (employer_id, 'Front-end разработчик (junior)', 'Ищем начинающего front-end разработчика. Знание HTML/CSS/JS; React/Vue приветствуются.', 'frontend,react,javascript', '50 000–80 000 ₽'),
        (employer_id, 'Python-разработчик (удалённо)', 'Разработка бэкенда на Flask/Django. Опыт 1-3 года. Тестирование и CI — плюс.', 'python,backend,flask', 'от 70 000 ₽'),
        (employer_id, 'Контент-менеджер', 'Наполнение сайта, работа с текстом и изображениями, базовая верстка.', 'контент,редактор,маркетинг', '30 000–45 000 ₽'),
    ]
    cur.executemany("INSERT INTO jobs (author_id, title, description, tags, salary) VALUES (?, ?, ?, ?, ?)", jobs)
    conn.commit()

    # Insert a couple of demo responses
    # Pick job ids (lowest id first inserted)
    cur.execute("SELECT id FROM jobs ORDER BY id ASC LIMIT 1")
    first_job_id = cur.fetchone()[0]
    cur.execute("SELECT id FROM jobs WHERE title LIKE ?", ('%Front-%',))
    front_job = cur.fetchone()
    front_job_id = front_job[0] if front_job else first_job_id

    responses = [
        (first_job_id, worker_id, 'Хочу откликнуться — есть опыт в общепите, могу работать по вечерам.', 'worker@example.com'),
        (front_job_id, worker_id, 'Есть базовые знания React, готов обучаться и работать неполный день.', 'worker@example.com'),
    ]
    cur.executemany("INSERT INTO responses (job_id, user_id, text, contact) VALUES (?, ?, ?, ?)", responses)
    conn.commit()

    print('Database created and seeded at:', DB_PATH)
    # Optional: show counts
    cur.execute('SELECT COUNT(*) FROM users')
    print('Users:', cur.fetchone()[0])
    cur.execute('SELECT COUNT(*) FROM jobs')
    print('Jobs:', cur.fetchone()[0])
    cur.execute('SELECT COUNT(*) FROM responses')
    print('Responses:', cur.fetchone()[0])

    conn.close()


if __name__ == '__main__':
    main()
