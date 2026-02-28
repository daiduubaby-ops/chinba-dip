import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, instance_relative_config=True)
# secret key for session management; in production set via environment
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key')
# ensure the instance folder exists (where the sqlite DB will live)
os.makedirs(app.instance_path, exist_ok=True)


def get_db_connection():
    db_path = os.path.join(app.instance_path, 'database.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def index():
    # Landing page
    return render_template('index.html')


@app.route('/books')
def books():
    # try to read a books table; if it doesn't exist, return placeholder list
    conn = get_db_connection()
    try:
        rows = conn.execute('SELECT id, title, author, description FROM books ORDER BY id DESC').fetchall()
        books = [dict(r) for r in rows]
    except Exception:
        # fallback: show some sample books
        books = [
            { 'id': 1, 'title': 'The Little Red Hen', 'author': 'Traditional', 'description': 'A story about hard work and friendship.' },
            { 'id': 2, 'title': 'The Very Hungry Caterpillar', 'author': 'Eric Carle', 'description': 'A caterpillar eats his way to becoming a butterfly.' }
        ]
    finally:
        conn.close()
    return render_template('books.html', books=books )


@app.route('/add', methods=['POST'])
def add():
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    if title:
        conn = get_db_connection()
        conn.execute('INSERT INTO notes (title, content) VALUES (?, ?)', (title, content))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))


@app.route('/delete/<int:note_id>', methods=['POST'])
def delete(note_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM notes WHERE id = ?', (note_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        age = request.form.get('age', '').strip()
        password = request.form.get('password', '')

        if not name or not age or not password:
            flash('Please fill out all required fields.')
            return redirect(url_for('register'))

        try:
            age_int = int(age)
        except ValueError:
            flash('Age must be a number.')
            return redirect(url_for('register'))

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id FROM users WHERE name = ?', (name,))
        if cur.fetchone() is not None:
            conn.close()
            flash('A user with that name already exists.')
            return redirect(url_for('register'))

        pw_hash = generate_password_hash(password)
        cur.execute('INSERT INTO users (name, age, password_hash) VALUES (?, ?, ?)', (name, age_int, pw_hash))
        conn.commit()
        conn.close()
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # login: accept name and password (age is provided only during registration)
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '')
        if not name or not password:
            flash('Please provide name and password.')
            return redirect(url_for('login'))

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id, name, age, password_hash FROM users WHERE name = ?', (name,))
        row = cur.fetchone()
        if row is None:
            # keep the user on the login page and show a message instead of forcing a redirect
            conn.close()
            flash('No account found with that name. Please register or check the name.')
            return redirect(url_for('login'))

        stored_hash = row['password_hash']
        if not check_password_hash(stored_hash, password):
            conn.close()
            flash('Invalid name or password.')
            return redirect(url_for('login'))

        user_id = row['id']
        user_age = row['age']
        conn.close()
        session.clear()
        session['user_id'] = user_id
        session['username'] = name
        session['age'] = user_age
        flash('Welcome, {}!'.format(name))
        return redirect(url_for('index'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('index'))


if __name__ == '__main__':
    # simple development server
    app.run(debug=True)
