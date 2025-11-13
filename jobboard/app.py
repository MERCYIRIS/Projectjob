from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3, os, hashlib

app = Flask(__name__)
app.secret_key = 'supersecretkeychangeit'

DB_PATH = "jobs.db"

def init_db():
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_employer INTEGER DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_id INTEGER,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            FOREIGN KEY (author_id) REFERENCES users(id)
        )''')
        conn.commit()
        conn.close()
init_db()

def hash_pwd(password):
    return hashlib.sha256(password.encode()).hexdigest()

def db():
    return sqlite3.connect(DB_PATH)

@app.route('/')
def index():
    search = request.args.get('q', '').strip()
    conn = db()
    c = conn.cursor()
    if search:
        c.execute("SELECT jobs.id, jobs.title, jobs.description, users.username FROM jobs LEFT JOIN users ON jobs.author_id=users.id WHERE jobs.title LIKE ? OR jobs.description LIKE ? ORDER BY jobs.id DESC", (f"%{search}%", f"%{search}%"))
    else:
        c.execute("SELECT jobs.id, jobs.title, jobs.description, users.username FROM jobs LEFT JOIN users ON jobs.author_id=users.id ORDER BY jobs.id DESC")
    jobs = c.fetchall()
    conn.close()
    return render_template('index.html', jobs=jobs, search=search)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = hash_pwd(request.form['password'])
        is_emp = 1 if 'employer' in request.form else 0
        conn = db()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password, is_employer) VALUES (?, ?, ?)", (username, password, is_emp))
            conn.commit()
            flash('Регистрация успешна! Теперь войдите.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Логин уже занят', 'danger')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = hash_pwd(request.form['password'])
        conn = db()
        c = conn.cursor()
        c.execute("SELECT id, is_employer FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            session['is_employer'] = bool(user[1])
            session['username'] = username
            flash('Вход выполнен', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверные данные для входа', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из аккаунта', 'info')
    return redirect(url_for('index'))

@app.route('/add', methods=['GET', 'POST'])
def add_job():
    if not session.get('user_id') or not session.get('is_employer'):
        flash('Вакансии могут размещать только работодатели. Зарегистрируйтесь или войдите как работодатель.', 'warning')
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        conn = db()
        c = conn.cursor()
        c.execute("INSERT INTO jobs (author_id, title, description) VALUES (?, ?, ?)", (session['user_id'], title, description))
        conn.commit()
        conn.close()
        flash('Вакансия добавлена!', 'success')
        return redirect(url_for('index'))
    return render_template('add_job.html')

@app.route('/delete/<int:job_id>')
def delete_job(job_id):
    if not session.get('user_id'):
        flash('Вы должны войти', 'danger')
        return redirect(url_for('login'))
    conn = db()
    c = conn.cursor()
    c.execute("SELECT author_id FROM jobs WHERE id=?", (job_id,))
    job = c.fetchone()
    if job and job[0] == session['user_id']:
        c.execute("DELETE FROM jobs WHERE id=?", (job_id,))
        conn.commit()
        flash('Вакансия удалена', 'info')
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)