import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import time
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, instance_relative_config=True)
# secret key for session management; in production set via environment
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key')
# admin password (can be set via environment ADMIN_PASSWORD)
# default admin password requested by user
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', '0247790208')
# ensure the instance folder exists (where the sqlite DB will live)
os.makedirs(app.instance_path, exist_ok=True)


def get_db_connection():
    db_path = os.path.join(app.instance_path, 'database.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _reading_table_columns(conn):
    """Return a dict of column info for reading_sessions: name -> {notnull, dflt_value}
    Falls back to an empty dict if the table doesn't exist or PRAGMA fails."""
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(reading_sessions)")
        cols = {}
        for r in cur.fetchall():
            # PRAGMA returns: cid, name, type, notnull, dflt_value, pk
            name = r[1]
            notnull = bool(r[3])
            dflt = r[4]
            cols[name] = {'notnull': notnull, 'dflt': dflt}
        return cols
    except Exception:
        return {}


def ensure_reading_sessions_schema():
    """Ensure the reading_sessions table has the expected columns (started_at, ended_at, duration_seconds).
    If older columns (start_time, end_time) exist, copy their values into the new columns.
    This makes the app tolerant of older database schemas that used different column names.
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reading_sessions'")
        if cur.fetchone() is None:
            # no table yet; nothing to migrate here
            conn.close()
            return
        cur.execute("PRAGMA table_info(reading_sessions)")
        existing = [r[1] for r in cur.fetchall()]

        # Add missing columns (SQLite supports ADD COLUMN)
        if 'started_at' not in existing:
            try:
                cur.execute('ALTER TABLE reading_sessions ADD COLUMN started_at INTEGER')
            except Exception:
                pass
        if 'ended_at' not in existing:
            try:
                cur.execute('ALTER TABLE reading_sessions ADD COLUMN ended_at INTEGER')
            except Exception:
                pass
        if 'duration_seconds' not in existing:
            try:
                cur.execute('ALTER TABLE reading_sessions ADD COLUMN duration_seconds INTEGER')
            except Exception:
                pass

        # If older column names exist, copy values across.
        # Use UPDATE ... WHERE ... to avoid overwriting existing migrated values.
        if 'start_time' in existing:
            try:
                cur.execute('UPDATE reading_sessions SET started_at = start_time WHERE started_at IS NULL')
            except Exception:
                pass
        if 'end_time' in existing:
            try:
                cur.execute('UPDATE reading_sessions SET ended_at = end_time WHERE ended_at IS NULL')
            except Exception:
                pass

        conn.commit()
    except Exception:
        try:
            if conn:
                conn.rollback()
        except Exception:
            pass
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


# Ensure DB schema is compatible on startup (helps for existing older DBs)
try:
    ensure_reading_sessions_schema()
except Exception:
    # avoid crashing the import if migrations fail for any reason
    pass


@app.template_filter('datetimeformat')
def datetimeformat(value):
    """Format an integer epoch timestamp into a readable string."""
    try:
        import datetime
        if value is None:
            return ''
        return datetime.datetime.fromtimestamp(int(value)).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return str(value)


@app.route('/')
def index():
    # Landing page
    return render_template('index.html')


@app.route('/books')
def books():
    # show list of books from the DB
    conn = get_db_connection()
    # include the image column so templates can show uploaded covers
    rows = conn.execute('SELECT id, title, author, description, image FROM books ORDER BY id DESC').fetchall()
    books = [dict(r) for r in rows]
    conn.close()
    return render_template('books.html', books=books)


@app.route('/books/<int:book_id>')
def book_detail(book_id):
    """Show a single book's details on its own page."""
    conn = get_db_connection()
    row = conn.execute('SELECT id, title, author, description, image FROM books WHERE id = ?', (book_id,)).fetchone()
    conn.close()
    if row is None:
        flash('Book not found.')
        return redirect(url_for('books'))
    book = dict(row)
    return render_template('book_detail.html', book=book)
@app.route('/books/<int:book_id>/read')
def book_read(book_id):
    """Reader view: load book and its pages and render the reader template."""
    conn = get_db_connection()
    row = conn.execute('SELECT id, title, author, description FROM books WHERE id = ?', (book_id,)).fetchone()
    conn.close()
    if row is None:
        flash('Book not found.')
        return redirect(url_for('books'))
    book = dict(row)
    # load page URLs to pass into the template for immediate rendering
    conn = get_db_connection()
    rows = conn.execute('SELECT filename FROM book_pages WHERE book_id = ? ORDER BY page_number ASC', (book_id,)).fetchall()
    conn.close()
    files = [r['filename'] for r in rows]
    urls = [url_for('static', filename=f'uploads/{book_id}/{fn}') for fn in files]
    return render_template('book_read.html', book=book, pages=urls)


@app.route('/books/<int:book_id>/pages')
def book_pages(book_id):
    """Return JSON list of page image URLs for the reader JS."""
    conn = get_db_connection()
    rows = conn.execute('SELECT filename FROM book_pages WHERE book_id = ? ORDER BY page_number ASC', (book_id,)).fetchall()
    conn.close()
    files = [r['filename'] for r in rows]
    # construct URLs relative to /static/uploads/<book_id>/filename
    urls = [url_for('static', filename=f'uploads/{book_id}/{fn}') for fn in files]
    from flask import jsonify
    return jsonify({'pages': urls})


# -- Admin routes to manage books (simple, no separate admin user for demo) --
@app.route('/admin/books')
def admin_books():
    # require admin password/session
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    conn = get_db_connection()
    # include image column so admin list can reflect uploaded covers (if desired later)
    rows = conn.execute('SELECT id, title, author, description, image FROM books ORDER BY id DESC').fetchall()
    books = [dict(r) for r in rows]
    conn.close()
    return render_template('admin_books.html', books=books)


@app.route('/admin/books/<int:book_id>/pages', methods=['GET', 'POST'])
def admin_book_pages(book_id):
    # only accessible to admin
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    row = conn.execute('SELECT id, title FROM books WHERE id = ?', (book_id,)).fetchone()
    if row is None:
        conn.close()
        flash('Book not found.')
        return redirect(url_for('admin_books'))

    if request.method == 'POST':
        # allow uploading additional pages and reordering isn't implemented here
        pages = request.files.getlist('pages')
        if pages:
            uploads_dir = os.path.join(app.static_folder, 'uploads')
            book_dir = os.path.join(uploads_dir, str(book_id))
            os.makedirs(book_dir, exist_ok=True)
            cur = conn.cursor()
            # determine next page number
            cur.execute('SELECT COALESCE(MAX(page_number), 0) FROM book_pages WHERE book_id = ?', (book_id,))
            start = cur.fetchone()[0] or 0
            pnum = start + 1
            for p in pages:
                if p and p.filename:
                    safe_name = os.path.basename(p.filename)
                    name = f"{pnum:03d}_{safe_name}"
                    path = os.path.join(book_dir, name)
                    p.save(path)
                    cur.execute('INSERT INTO book_pages (book_id, filename, page_number) VALUES (?, ?, ?)', (book_id, name, pnum))
                    pnum += 1
            conn.commit()
        conn.close()
        return redirect(url_for('admin_book_pages', book_id=book_id))

    rows = conn.execute('SELECT id, filename, page_number FROM book_pages WHERE book_id = ? ORDER BY page_number ASC', (book_id,)).fetchall()
    pages = [dict(r) for r in rows]
    conn.close()
    return render_template('admin_book_pages.html', book=dict(row), pages=pages)


@app.route('/admin/books/<int:book_id>/pages/delete/<int:page_id>', methods=['POST'])
def admin_book_page_delete(book_id, page_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    conn = get_db_connection()
    cur = conn.cursor()
    row = cur.execute('SELECT filename FROM book_pages WHERE id = ? AND book_id = ?', (page_id, book_id)).fetchone()
    if row is None:
        conn.close()
        flash('Page not found.')
        return redirect(url_for('admin_book_pages', book_id=book_id))
    filename = row['filename']
    # delete file from disk if exists
    file_path = os.path.join(app.static_folder, 'uploads', str(book_id), filename)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass
    cur.execute('DELETE FROM book_pages WHERE id = ? AND book_id = ?', (page_id, book_id))
    conn.commit()
    conn.close()
    flash('Page deleted.')
    return redirect(url_for('admin_book_pages', book_id=book_id))


@app.route('/admin/books/<int:book_id>/pages/move/<int:page_id>', methods=['POST'])
def admin_book_page_move(book_id, page_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    direction = request.form.get('direction')
    if direction not in ('up','down'):
        flash('Invalid move direction.')
        return redirect(url_for('admin_book_pages', book_id=book_id))
    conn = get_db_connection()
    cur = conn.cursor()
    row = cur.execute('SELECT id, page_number FROM book_pages WHERE id = ? AND book_id = ?', (page_id, book_id)).fetchone()
    if row is None:
        conn.close()
        flash('Page not found.')
        return redirect(url_for('admin_book_pages', book_id=book_id))
    cur_num = row['page_number']
    if direction == 'up':
        # find page with page_number immediately less than current
        other = cur.execute('SELECT id, page_number FROM book_pages WHERE book_id = ? AND page_number < ? ORDER BY page_number DESC LIMIT 1', (book_id, cur_num)).fetchone()
    else:
        other = cur.execute('SELECT id, page_number FROM book_pages WHERE book_id = ? AND page_number > ? ORDER BY page_number ASC LIMIT 1', (book_id, cur_num)).fetchone()
    if other is None:
        conn.close()
        flash('Cannot move further.')
        return redirect(url_for('admin_book_pages', book_id=book_id))
    # swap page_number values
    try:
        cur.execute('UPDATE book_pages SET page_number = ? WHERE id = ?', (-1, page_id))
        cur.execute('UPDATE book_pages SET page_number = ? WHERE id = ?', (cur_num, other['id']))
        cur.execute('UPDATE book_pages SET page_number = ? WHERE id = ?', (other['page_number'], page_id))
        conn.commit()
    except Exception:
        conn.rollback()
    conn.close()
    return redirect(url_for('admin_book_pages', book_id=book_id))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        pw = request.form.get('password', '')
        if pw == ADMIN_PASSWORD:
            session['is_admin'] = True
            flash('Admin signed in.')
            return redirect(url_for('admin_books'))
        else:
            flash('Invalid admin password.')
            return redirect(url_for('admin_login'))
    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    flash('Admin logged out.')
    return redirect(url_for('index'))


@app.route('/admin/books/add', methods=['POST'])
def admin_books_add():
    title = request.form.get('title', '').strip()
    author = request.form.get('author', '').strip()
    description = request.form.get('description', '').strip()
    image_file = request.files.get('image')
    image_filename = None
    if image_file and image_file.filename:
        uploads_dir = os.path.join(app.static_folder, 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        # simple filename sanitization
        fname = os.path.basename(image_file.filename)
        image_filename = fname
        image_path = os.path.join(uploads_dir, image_filename)
        image_file.save(image_path)

    # handle multiple page uploads (PNG expected)
    pages = request.files.getlist('pages')

    if title:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO books (title, author, description, image) VALUES (?, ?, ?, ?)', (title, author, description, image_filename))
        book_id = cur.lastrowid
        # save page records after creating book
        uploads_dir = os.path.join(app.static_folder, 'uploads')
        book_dir = os.path.join(uploads_dir, str(book_id))
        if pages:
            os.makedirs(book_dir, exist_ok=True)
            page_num = 1
            for p in pages:
                if p and p.filename:
                    # keep original filename but prefix with page number to avoid collisions
                    safe_name = os.path.basename(p.filename)
                    # ensure png extension
                    name = f"{page_num:03d}_{safe_name}"
                    path = os.path.join(book_dir, name)
                    p.save(path)
                    cur.execute('INSERT INTO book_pages (book_id, filename, page_number) VALUES (?, ?, ?)', (book_id, name, page_num))
                    page_num += 1
        conn.commit()
        conn.close()
    return redirect(url_for('admin_books'))


@app.route('/admin/books/delete/<int:book_id>', methods=['POST'])
def admin_books_delete(book_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM books WHERE id = ?', (book_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_books'))


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


@app.route('/reading/start', methods=['POST'])
def reading_start():
    """Start a reading session for the current user and book.
    Expects JSON: {"book_id": <int>} Returns JSON {session_id, started_at}
    """
    if not session.get('user_id'):
        return jsonify({'error': 'authentication required'}), 401
    data = request.get_json() or {}
    book_id = data.get('book_id')
    if not book_id:
        return jsonify({'error': 'book_id required'}), 400
    started_at = int(time.time())
    conn = get_db_connection()
    cur = conn.cursor()
    # Some older databases used column names start_time / end_time and may have NOT NULL constraints.
    # To be tolerant, detect existing columns and include start_time if present so INSERT doesn't fail.
    try:
        cur.execute("PRAGMA table_info(reading_sessions)")
        existing = [r[1] for r in cur.fetchall()]
    except Exception:
        existing = []

    cols = ['user_id', 'book_id', 'started_at']
    placeholders = ['?', '?', '?']
    vals = [session['user_id'], book_id, started_at]
    if 'start_time' in existing:
        cols.append('start_time')
        placeholders.append('?')
        vals.append(started_at)

    sql = f"INSERT INTO reading_sessions ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
    cur.execute(sql, tuple(vals))
    session_id = cur.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'session_id': session_id, 'started_at': started_at})


@app.route('/reading/stop', methods=['POST'])
def reading_stop():
    """Stop a reading session. Expects JSON: {"session_id": <int>} Returns JSON with duration."""
    if not session.get('user_id'):
        return jsonify({'error': 'authentication required'}), 401
    data = request.get_json() or {}
    session_id = data.get('session_id')
    if not session_id:
        return jsonify({'error': 'session_id required'}), 400
    ended_at = int(time.time())
    conn = get_db_connection()
    cur = conn.cursor()
    row = cur.execute('SELECT id, user_id, started_at, ended_at FROM reading_sessions WHERE id = ?', (session_id,)).fetchone()
    if row is None:
        conn.close()
        return jsonify({'error': 'session not found'}), 404
    if row['user_id'] != session['user_id']:
        conn.close()
        return jsonify({'error': 'forbidden'}), 403
    if row['ended_at'] is not None:
        conn.close()
        return jsonify({'error': 'already stopped'}), 400
    duration = ended_at - row['started_at']
    cur.execute('UPDATE reading_sessions SET ended_at = ?, duration_seconds = ? WHERE id = ?', (ended_at, duration, session_id))
    conn.commit()
    conn.close()
    return jsonify({'session_id': session_id, 'ended_at': ended_at, 'duration_seconds': duration})


@app.route('/profile')
def profile():
    if not session.get('user_id'):
        flash('Please log in to view your profile.')
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = get_db_connection()
    # Select only the most recent session per book so the same book doesn't appear multiple times
    rows = conn.execute('''
        SELECT rs.id, rs.book_id, rs.started_at, rs.ended_at, rs.duration_seconds, b.title, b.image as image
        FROM reading_sessions rs
        JOIN (
            SELECT book_id, MAX(started_at) AS max_started
            FROM reading_sessions
            WHERE user_id = ?
            GROUP BY book_id
        ) m ON rs.book_id = m.book_id AND rs.started_at = m.max_started
        LEFT JOIN books b ON b.id = rs.book_id
        WHERE rs.user_id = ?
        ORDER BY rs.started_at DESC
    ''', (user_id, user_id)).fetchall()
    sessions = [dict(r) for r in rows]
    agg = conn.execute('''
        SELECT b.id as book_id, b.title, b.image as image, COALESCE(SUM(rs.duration_seconds),0) as total_seconds
        FROM books b
        LEFT JOIN reading_sessions rs ON rs.book_id = b.id AND rs.user_id = ?
        GROUP BY b.id, b.title
        HAVING total_seconds > 0
        ORDER BY total_seconds DESC
    ''', (user_id,)).fetchall()
    totals = [dict(r) for r in agg]
    total_overall = sum(r['total_seconds'] for r in totals) if totals else 0
    conn.close()
    return render_template('profile.html', sessions=sessions, totals=totals, total_overall=total_overall)


if __name__ == '__main__':
    # simple development server
    app.run(debug=True)
