# убедитесь, что в начале файла импортированы:
# from flask_wtf import FlaskForm
# from wtforms import StringField, PasswordField, BooleanField, SubmitField
# from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        password = form.password.data
        email = form.email.data.strip() if form.email.data else None
        is_employer = 1 if form.employer.data else 0
        try:
            execute_db("INSERT INTO users (username, password, is_employer, email) VALUES (?, ?, ?, ?)",
                       (username, generate_password_hash(password), is_employer, email))
        except sqlite3.IntegrityError:
            flash('Имя пользователя уже занято', 'danger')
            return redirect(url_for('register'))
        user = query_db("SELECT id, username, is_employer FROM users WHERE username = ?", (username,), one=True)
        session.clear()
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['is_employer'] = bool(user['is_employer'])
        flash('Регистрация прошла успешно', 'success')
        return redirect(url_for('index'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        password = form.password.data
        user = query_db("SELECT * FROM users WHERE username = ?", (username,), one=True)
        if not user or not check_password_hash(user['password'], password):
            flash('Неверный логин или пароль', 'danger')
            return redirect(url_for('login'))
        session.clear()
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['is_employer'] = bool(user['is_employer'])
        session.permanent = bool(form.remember.data)
        flash('Вход выполнен', 'success')
        return redirect(url_for('index'))
    return render_template('login.html', form=form)