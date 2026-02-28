import os
import sqlite3

def init_db(path=None):
    if path is None:
        path = os.path.join('instance', 'database.db')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    # if an existing users table exists but doesn't match the new schema, replace it
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if cur.fetchone() is not None:
        cur.execute("PRAGMA table_info(users)")
        existing_cols = [r[1] for r in cur.fetchall()]
        expected = ['id', 'name', 'age', 'password_hash']
        if existing_cols != expected:
            # drop the old users table and recreate the updated one
            cur.execute('DROP TABLE IF EXISTS users')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT
    )
    ''')
    # books table for listing
    cur.execute('''
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT,
        description TEXT,
        image TEXT
    )
    ''')
    # book_pages table stores uploaded page images for a book in display order
    cur.execute('''
    CREATE TABLE IF NOT EXISTS book_pages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        page_number INTEGER NOT NULL,
        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
    )
    ''')
    # If the books table exists but doesn't have an image column, add it
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='books'")
    if cur.fetchone() is not None:
        cur.execute("PRAGMA table_info(books)")
        cols = [r[1] for r in cur.fetchall()]
        if 'image' not in cols:
            try:
                cur.execute('ALTER TABLE books ADD COLUMN image TEXT')
            except Exception:
                pass
    # users table for authentication (name, age, password_hash)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        age INTEGER NOT NULL,
        password_hash TEXT NOT NULL
    )
    ''')
    # reading_sessions table tracks when a user starts and stops reading a book
    cur.execute('''
    CREATE TABLE IF NOT EXISTS reading_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        book_id INTEGER NOT NULL,
        started_at INTEGER NOT NULL,
        ended_at INTEGER,
        duration_seconds INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE
    )
    ''')
    # Ensure existing databases that predate these columns get migrated.
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reading_sessions'")
    if cur.fetchone() is not None:
        cur.execute("PRAGMA table_info(reading_sessions)")
        existing_cols = [r[1] for r in cur.fetchall()]
        # add any missing columns using ALTER TABLE (SQLite supports ADD COLUMN)
        if 'started_at' not in existing_cols:
            try:
                cur.execute('ALTER TABLE reading_sessions ADD COLUMN started_at INTEGER')
            except Exception:
                pass
        if 'ended_at' not in existing_cols:
            try:
                cur.execute('ALTER TABLE reading_sessions ADD COLUMN ended_at INTEGER')
            except Exception:
                pass
        if 'duration_seconds' not in existing_cols:
            try:
                cur.execute('ALTER TABLE reading_sessions ADD COLUMN duration_seconds INTEGER')
            except Exception:
                pass
        # If older schema used different column names, copy values across so existing data remains usable.
        # older names seen in some databases: start_time, end_time
        if 'start_time' in existing_cols and 'started_at' in existing_cols:
            try:
                cur.execute('UPDATE reading_sessions SET started_at = start_time WHERE started_at IS NULL')
            except Exception:
                pass
        if 'end_time' in existing_cols and 'ended_at' in existing_cols:
            try:
                cur.execute('UPDATE reading_sessions SET ended_at = end_time WHERE ended_at IS NULL')
            except Exception:
                pass
    # insert sample data if table empty
    cur.execute('SELECT COUNT(*) FROM notes')
    if cur.fetchone()[0] == 0:
        cur.executemany('INSERT INTO notes (title, content) VALUES (?, ?)', [
            ('Welcome', 'This is a sample note.'),
            ('Another note', 'You can add and delete notes.')
        ])
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print('Initialized database at instance/database.db')
