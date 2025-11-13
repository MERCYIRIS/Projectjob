from flask import Flask, render_template, request, redirect
import sqlite3, os

app = Flask(__name__)

DB_PATH = "jobs.db"

def init_db():
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

init_db()

@app.route('/', methods=['GET', 'POST'])
def index():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'POST':
        title = request.form['title'].strip()
        description = request.form['description'].strip()
        if title and description:
            c.execute('INSERT INTO jobs (title, description) VALUES (?, ?)', (title, description))
            conn.commit()
    c.execute('SELECT * FROM jobs ORDER BY id DESC')
    jobs = c.fetchall()
    conn.close()
    return render_template('index.html', jobs=jobs)

if __name__ == '__main__':
    app.run(debug=True)