#!/usr/bin/env python3
# app.py - основной файл проекта JobBoard с Flask-WTF, CSRF и сбросом пароля

import os
import sqlite3
from datetime import timedelta
from flask import (Flask, g, render_template, request, redirect,
                   url_for, session, flash, jsonify, abort, current_app)
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Email, Optional, EqualTo

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'jobs.db')

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'change-this-secret')
app.permanent_session_lifetime = timedelta(days=30)
app.config['DATABASE'] = DB_PATH
# Flask-WTF CSRF uses app.secret_key by default

# serializer for tokens
serializer = URLSafeTimedSerializer(app.secret_key)

# ---------- Database helpers ----------
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    # Создаём БД и минимальные данные только если файла ещё нет
    if not os.path.exists(app.config['DATABASE']):
        conn = sqlite3.connect(app.config['DATABASE'])
        c = conn.cursor()
        c.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_employer INTEGER DEFAULT 0,
                email TEXT,
                avatar TEXT,
                about TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author_id INTEGER,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                tags TEXT,
                salary TEXT,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (author_id) REFERENCES users(id)
            )
        ''')
        c.execute('''
            CREATE TABLE responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER,
                user_id INTEGER,
                text TEXT,
                contact TEXT,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()
        # Добавим тестовые записи для удобства
        try:
            from werkzeug.security import generate_password_hash
            pwd_hash = generate_password_hash('password123')
            c.execute("INSERT INTO users (username, password, is_employer, email, about) VALUES (?, ?, ?, ?, ?)",
                      ('employer1', pwd_hash, 1, 'employer@example.com', 'Тестовый работодатель'))
            employer_id = c.lastrowid
            c.execute("INSERT INTO users (username, password, is_employer, email, about) VALUES (?, ?, ?, ?, ?)",
                      ('worker1', pwd_hash, 0, 'worker@example.com', 'Тестовый соискатель'))
            worker_id = c.lastrowid
            c.execute("INSERT INTO jobs (author_id, title, description, tags, salary) VALUES (?, ?, ?, ?, ?)",
                      (employer_id, 'Бариста (подработка)', 'Требуется бариста на неполный рабочий день. Обучение бесплатно, гибкий график.', 'кафе,бариста', 'от 170 ₽/ч'))
            job1_id = c.lastrowid
            c.execute("INSERT INTO jobs (author_id, title, description, tags, salary) VALUES (?, ?, ?, ?, ?)",
                      (employer_id, 'Курьер (самокат)', 'Курьерская доставка по району. Оплата за доставку + бонусы.', 'курьер,доставка', 'по договорённости'))
            job2_id = c.lastrowid
            c.execute("INSERT INTO responses (job_id, user_id, text, contact) VALUES (?, ?, ?, ?)",
                      (job1_id, worker_id, 'Есть опыт, могу по вечерам.', 'worker@example.com'))
            # Дополнительные демо-вакансии для более полного наполнения БД
            c.execute("INSERT INTO jobs (author_id, title, description, tags, salary) VALUES (?, ?, ?, ?, ?)",
                      (employer_id, 'Front-end разработчик (junior)',
                       'Ищем начинающего front-end разработчика. Знание HTML/CSS/JS; React/Vue приветствуются.',
                       'frontend,react,javascript', '50 000–80 000 ₽'))
            job3_id = c.lastrowid
            c.execute("INSERT INTO jobs (author_id, title, description, tags, salary) VALUES (?, ?, ?, ?, ?)",
                      (employer_id, 'Python-разработчик (удалённо)',
                       'Разработка бэкенда на Flask/Django. Опыт 1-3 года. Тестирование и CI — плюс.',
                       'python,backend,flask', 'от 70 000 ₽'))
            job4_id = c.lastrowid
            c.execute("INSERT INTO jobs (author_id, title, description, tags, salary) VALUES (?, ?, ?, ?, ?)",
                      (employer_id, 'Контент-менеджер',
                       'Наполнение сайта, работа с текстом и изображениями, базовая верстка.',
                       'контент,редактор,маркетинг', '30 000–45 000 ₽'))
            job5_id = c.lastrowid
            # Пример отклика на одну из новых вакансий
            c.execute("INSERT INTO responses (job_id, user_id, text, contact) VALUES (?, ?, ?, ?)",
                      (job3_id, worker_id, 'Есть базовые знания React, готов обучаться и работать неполный день.', 'worker@example.com'))
            conn.commit()
        except Exception:
            conn.rollback()
        finally:
            conn.close()

init_db()

# ---------- Utility DB functions ----------
def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    conn = get_db()
    cur = conn.execute(query, args)
    conn.commit()
    return cur

def current_user():
    if 'user_id' in session:
        return query_db('SELECT * FROM users WHERE id = ?', (session['user_id'],), one=True)
    return None

# ---------- Forms ----------
class RegistrationForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired(), Length(min=3, max=32)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    email = StringField('Email (опционально)', validators=[Optional(), Email()])
    employer = BooleanField('Я работодатель')
    submit = SubmitField('Зарегистрироваться')

class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')

class RequestResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Отправить ссылку для сброса')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Новый пароль', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Сохранить пароль')

# ---------- Email / token helpers ----------
def generate_token(email: str):
    return serializer.dumps(email, salt='password-reset-salt')

def confirm_token(token: str, expiration=3600):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=expiration)
    except SignatureExpired:
        return None  # token expired
    except BadSignature:
        return None  # invalid token
    return email

def send_reset_email(email: str, token: str):
    # Для разработки: печатаем ссылку в консоль; позже можно подключить SMTP
    reset_url = url_for('reset_password', token=token, _external=True)
    print(f'[Password reset] To: {email}\nReset link: {reset_url}')
    # Также показываем пользователю краткое уведомление
    flash('Письмо со ссылкой для сброса пароля отправлено (проверьте консоль сервера)', 'info')

# ---------- Context processor ----------
@app.context_processor
def inject_user():
    return {'user': current_user()}

# ---------- Routes ----------
@app.route('/')
def index():
    q = request.args.get('q', '').strip()
    if q:
        like = f'%{q}%'
        jobs = query_db(
            "SELECT jobs.*, users.username as author FROM jobs LEFT JOIN users ON jobs.author_id = users.id "
            "WHERE jobs.title LIKE ? OR jobs.description LIKE ? ORDER BY jobs.created DESC",
            (like, like)
        )
    else:
        jobs = query_db(
            "SELECT jobs.*, users.username as author FROM jobs LEFT JOIN users ON jobs.author_id = users.id ORDER BY jobs.created DESC"
        )
    return render_template('index.html', jobs=jobs, search=q)

# Registration / Login / Logout
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        password = form.password.data
        is_employer = 1 if form.employer.data else 0
        email = form.email.data.strip() if form.email.data else None

        try:
            execute_db(
                "INSERT INTO users (username, password, is_employer, email) VALUES (?, ?, ?, ?)",
                (username, generate_password_hash(password), is_employer, email)
            )
        except sqlite3.IntegrityError:
            flash('Имя пользователя уже занято', 'danger')
            return redirect(url_for('register'))

        user = query_db("SELECT id, username, is_employer FROM users WHERE username = ?", (username,), one=True)
        session.clear()
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['is_employer'] = bool(user['is_employer'])
        flash('Регистрация успешна. Вы вошли в систему.', 'success')
        return redirect(url_for('index'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        password = form.password.data
        remember = form.remember.data

        user = query_db("SELECT id, username, password, is_employer FROM users WHERE username = ?", (username,), one=True)
        if user is None or not check_password_hash(user['password'], password):
            flash('Неверный логин или пароль', 'danger')
            return redirect(url_for('login'))

        session.clear()
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['is_employer'] = bool(user['is_employer'])
        session.permanent = bool(remember)
        flash('Вход выполнен', 'success')
        return redirect(url_for('index'))
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из аккаунта', 'info')
    return redirect(url_for('index'))

# Password reset: request
@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    form = RequestResetForm()
    if form.validate_on_submit():
        email = form.email.data.strip()
        user = query_db("SELECT * FROM users WHERE email = ?", (email,), one=True)
        if user:
            token = generate_token(email)
            send_reset_email(email, token)
        else:
            # Не выдаём информацию о наличии почты — но для удобства разработки можно сообщить
            flash('Пользователь с таким email не найден', 'warning')
            return redirect(url_for('reset_password_request'))

        return redirect(url_for('login'))
    return render_template('reset_request.html', form=form)

# Password reset: set new password
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = confirm_token(token)
    if not email:
        flash('Ссылка недействительна или истекла', 'danger')
        return redirect(url_for('reset_password_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        new_password = form.password.data
        user = query_db("SELECT * FROM users WHERE email = ?", (email,), one=True)
        if not user:
            flash('Пользователь не найден', 'danger')
            return redirect(url_for('register'))
        execute_db("UPDATE users SET password = ? WHERE id = ?", (generate_password_hash(new_password), user['id']))
        flash('Пароль успешно изменён. Войдите с новым паролем.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)

# The rest of routes (jobs, add, job_detail, respond, delete, profile, api) remain same as before
# For brevity, include simplified versions here (you can keep your existing implementations)

@app.route('/add', methods=['GET', 'POST'])
def add_job():
    user = current_user()
    if not user or not user['is_employer']:
        flash('Только зарегистрированный работодатель может добавлять вакансии', 'warning')
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        tags = request.form.get('tags', '').strip()
        salary = request.form.get('salary', '').strip()
        if not title or not description:
            flash('Заполните обязательные поля', 'danger')
            return redirect(url_for('add_job'))
        execute_db("INSERT INTO jobs (author_id, title, description, tags, salary) VALUES (?, ?, ?, ?, ?)",
                   (user['id'], title, description, tags, salary))
        flash('Вакансия опубликована', 'success')
        return redirect(url_for('index'))
    return render_template('add_job.html')

@app.route('/job/<int:job_id>', methods=['GET'])
def job_detail(job_id):
    job = query_db("SELECT jobs.*, users.username AS author, users.avatar AS author_avatar, users.id AS author_id "
                   "FROM jobs LEFT JOIN users ON jobs.author_id = users.id WHERE jobs.id = ?", (job_id,), one=True)
    if not job:
        abort(404)
    responses = query_db("SELECT responses.*, users.username as user_name FROM responses LEFT JOIN users ON responses.user_id = users.id WHERE job_id = ? ORDER BY responses.created DESC", (job_id,))
    return render_template('job_detail.html', job=job, responses=responses)

@app.route('/respond/<int:job_id>', methods=['POST'])
def respond(job_id):
    user = current_user()
    text = request.form.get('text', '').strip()
    contact = request.form.get('contact', '').strip() or None
    if not user:
        flash('Войдите, чтобы откликнуться', 'warning')
        return redirect(url_for('login'))
    if not text:
        flash('Напишите сообщение с откликом', 'danger')
        return redirect(url_for('job_detail', job_id=job_id))
    execute_db("INSERT INTO responses (job_id, user_id, text, contact) VALUES (?, ?, ?, ?)",
               (job_id, user['id'], text, contact))
    flash('Отклик отправлен', 'success')
    return redirect(url_for('job_detail', job_id=job_id))

@app.route('/delete/<int:job_id>', methods=['POST'])
def delete_job(job_id):
    user = current_user()
    if not user:
        flash('Войдите', 'danger')
        return redirect(url_for('login'))
    job = query_db("SELECT * FROM jobs WHERE id = ?", (job_id,), one=True)
    if not job:
        flash('Вакансия не найдена', 'danger')
        return redirect(url_for('index'))
    if job['author_id'] != user['id']:
        flash('Нет прав удалять эту вакансию', 'danger')
        return redirect(url_for('index'))
    execute_db("DELETE FROM jobs WHERE id = ?", (job_id,))
    execute_db("DELETE FROM responses WHERE job_id = ?", (job_id,))
    flash('Вакансия удалена', 'info')
    return redirect(url_for('index'))

@app.route('/del_response/<int:resp_id>', methods=['POST'])
def del_response(resp_id):
    user = current_user()
    if not user:
        flash('Войдите', 'danger')
        return redirect(url_for('login'))
    resp = query_db("SELECT responses.*, jobs.author_id FROM responses JOIN jobs ON responses.job_id = jobs.id WHERE responses.id = ?", (resp_id,), one=True)
    if not resp:
        flash('Отклик не найден', 'danger')
        return redirect(url_for('index'))
    # разрешаем удалить, если отклик написал текущий пользователь, или текущий пользователь — автор вакансии
    if resp['user_id'] == user['id'] or resp['author_id'] == user['id']:
        execute_db("DELETE FROM responses WHERE id = ?", (resp_id,))
        flash('Отклик удалён', 'info')
        return redirect(request.referrer or url_for('index'))
    flash('Нет прав удалять отклик', 'danger')
    return redirect(url_for('index'))

@app.route('/profile/<username>', methods=['GET', 'POST'])
def profile(username):
    user = current_user()
    profile_user = query_db('SELECT * FROM users WHERE username = ?', (username,), one=True)
    if not profile_user:
        abort(404)
    if request.method == 'POST':
        if not user or user['id'] != profile_user['id']:
            flash('Нет прав редактировать профиль', 'danger')
            return redirect(url_for('profile', username=username))
        about = request.form.get('about', '').strip()
        avatar = request.form.get('avatar', '').strip() or None
        execute_db("UPDATE users SET about = ?, avatar = ? WHERE id = ?", (about, avatar, user['id']))
        flash('Профиль обновлён', 'success')
        return redirect(url_for('profile', username=username))
    # responses by this user
    responses = query_db("SELECT responses.*, jobs.title as job_title FROM responses LEFT JOIN jobs ON responses.job_id = jobs.id WHERE responses.user_id = ? ORDER BY responses.created DESC", (profile_user['id'],))
    jobs = query_db("SELECT * FROM jobs WHERE author_id = ? ORDER BY created DESC", (profile_user['id'],))
    return render_template('profile.html', profile=profile_user, responses=responses, jobs=jobs)

# API
@app.route('/api/jobs')
def api_jobs():
    jobs = query_db("SELECT jobs.id, title, description, tags, salary, created, users.username as author FROM jobs LEFT JOIN users ON jobs.author_id = users.id ORDER BY jobs.created DESC")
    out = [dict(j) for j in jobs]
    return jsonify(out)

# ---------- Run ----------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)