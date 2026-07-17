CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    author_name TEXT,
    period TEXT,
    movement TEXT,
    source TEXT,
    is_public INTEGER NOT NULL DEFAULT 1,
    created_by_user_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS poems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author_name TEXT,
    body TEXT NOT NULL,
    period TEXT,
    movement TEXT,
    year_written INTEGER,
    source TEXT,
    is_public_domain INTEGER NOT NULL DEFAULT 1,
    is_public INTEGER NOT NULL DEFAULT 1,
    created_by_user_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS book_poems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    poem_id INTEGER NOT NULL,
    position INTEGER,
    FOREIGN KEY (book_id) REFERENCES books(id),
    FOREIGN KEY (poem_id) REFERENCES poems(id),
    UNIQUE(book_id, poem_id)
);

CREATE TABLE IF NOT EXISTS user_books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    book_id INTEGER NOT NULL,
    checked_out_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'on_shelf',
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (book_id) REFERENCES books(id),
    UNIQUE(user_id, book_id)
);

CREATE TABLE IF NOT EXISTS user_poems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    poem_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'available',
    copied_to_notebook_at TEXT,
    started_learning_at TEXT,
    completed_at TEXT,
    last_recited_at TEXT,
    next_review_at TEXT,
    current_learning_mode TEXT,
    current_chunk_start INTEGER,
    current_chunk_end INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (poem_id) REFERENCES poems(id),
    UNIQUE(user_id, poem_id)
);

CREATE TABLE IF NOT EXISTS notebook_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    poem_id INTEGER NOT NULL,
    notes TEXT,
    copied_text TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (poem_id) REFERENCES poems(id),
    UNIQUE(user_id, poem_id)
);

CREATE TABLE IF NOT EXISTS stanza_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    poem_id INTEGER NOT NULL,
    stanza_index INTEGER NOT NULL,
    learned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (poem_id) REFERENCES poems(id),
    UNIQUE(user_id, poem_id, stanza_index)
);

CREATE TABLE IF NOT EXISTS recital_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    poem_id INTEGER NOT NULL,
    attempt_text TEXT NOT NULL,
    expected_text TEXT NOT NULL,
    score REAL,
    passed INTEGER NOT NULL DEFAULT 0,
    attempted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (poem_id) REFERENCES poems(id)
);
