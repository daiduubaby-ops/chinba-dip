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
    # users table for authentication (name, age, password_hash)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        age INTEGER NOT NULL,
        password_hash TEXT NOT NULL
    )
    ''')
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
