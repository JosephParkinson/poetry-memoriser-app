import sqlite3
import hashlib
import random
import re

DB_PATH = "poetry_house.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    with open("schema.sql") as f:
        conn.executescript(f.read())
    conn.close()


# ── auth ──────────────────────────────────────────────────────────────────────

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(username, password):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, hash_password(password)),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def verify_user(username, password):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    if row and row["password_hash"] == hash_password(password):
        return dict(row)
    return None


# ── library (public) ──────────────────────────────────────────────────────────

LIBRARY_SHELVES = [
    ("Romantics",     "romantics"),
    ("Modernism",     "modernism"),
    ("Victorian",     "victorian"),
    ("Ancient",       "ancient"),
    ("Contemporary",  "contemporary"),
    ("Renaissance",   "renaissance"),
]


def get_shelf_books(period):
    conn = get_db()
    rows = conn.execute(
        """SELECT b.*, COUNT(bp.poem_id) as poem_count
           FROM books b
           LEFT JOIN book_poems bp ON b.id = bp.book_id
           WHERE lower(b.period) = lower(?) AND b.is_public = 1
           GROUP BY b.id ORDER BY b.title""",
        (period,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_poem(user_id, title, author_name, body, period=None, year_written=None):
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO poems
           (title, author_name, body, period, year_written,
            is_public_domain, is_public, created_by_user_id)
           VALUES (?, ?, ?, ?, ?, 0, 0, ?)""",
        (title, author_name or None, body, period or None,
         year_written or None, user_id),
    )
    poem_id = cur.lastrowid
    conn.commit()
    conn.close()
    return poem_id


def get_book(book_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_book_poems(book_id):
    conn = get_db()
    rows = conn.execute(
        """SELECT p.* FROM poems p
           JOIN book_poems bp ON p.id = bp.poem_id
           WHERE bp.book_id = ? ORDER BY bp.position""",
        (book_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_poem(poem_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM poems WHERE id = ?", (poem_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ── user books (shelf) ────────────────────────────────────────────────────────

def checkout_book(user_id, book_id):
    conn = get_db()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO user_books (user_id, book_id) VALUES (?, ?)",
            (user_id, book_id),
        )
        conn.commit()
    finally:
        conn.close()


def has_book(user_id, book_id):
    conn = get_db()
    row = conn.execute(
        "SELECT 1 FROM user_books WHERE user_id = ? AND book_id = ?",
        (user_id, book_id),
    ).fetchone()
    conn.close()
    return row is not None


def get_user_books(user_id):
    conn = get_db()
    rows = conn.execute(
        """SELECT b.*, COUNT(bp.poem_id) as poem_count
           FROM books b
           JOIN user_books ub ON b.id = ub.book_id
           LEFT JOIN book_poems bp ON b.id = bp.book_id
           WHERE ub.user_id = ?
           GROUP BY b.id ORDER BY ub.checked_out_at DESC""",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── notebook ──────────────────────────────────────────────────────────────────

def copy_to_notebook(user_id, poem_id):
    conn = get_db()
    conn.execute(
        """INSERT OR IGNORE INTO user_poems (user_id, poem_id, status, copied_to_notebook_at)
           VALUES (?, ?, 'notebook', CURRENT_TIMESTAMP)""",
        (user_id, poem_id),
    )
    conn.execute(
        "INSERT OR IGNORE INTO notebook_entries (user_id, poem_id) VALUES (?, ?)",
        (user_id, poem_id),
    )
    conn.commit()
    conn.close()


def get_notebook(user_id):
    conn = get_db()
    rows = conn.execute(
        """SELECT p.id, p.title, p.author_name, up.status, up.current_learning_mode,
                  ne.notes
           FROM poems p
           JOIN user_poems up ON p.id = up.poem_id AND up.user_id = ?
           LEFT JOIN notebook_entries ne ON ne.poem_id = p.id AND ne.user_id = ?
           WHERE up.status IN ('notebook','learning','completed')
           ORDER BY up.copied_to_notebook_at""",
        (user_id, user_id),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user_poem(user_id, poem_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM user_poems WHERE user_id = ? AND poem_id = ?",
        (user_id, poem_id),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_notebook_entry(user_id, poem_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM notebook_entries WHERE user_id = ? AND poem_id = ?",
        (user_id, poem_id),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def save_notes(user_id, poem_id, notes):
    conn = get_db()
    conn.execute(
        """UPDATE notebook_entries SET notes = ?, updated_at = CURRENT_TIMESTAMP
           WHERE user_id = ? AND poem_id = ?""",
        (notes, user_id, poem_id),
    )
    conn.commit()
    conn.close()


def set_learning_mode(user_id, poem_id, mode):
    conn = get_db()
    conn.execute(
        """UPDATE user_poems
           SET status = 'learning',
               current_learning_mode = ?,
               started_learning_at = COALESCE(started_learning_at, CURRENT_TIMESTAMP)
           WHERE user_id = ? AND poem_id = ?""",
        (mode, user_id, poem_id),
    )
    conn.commit()
    conn.close()


def complete_poem(user_id, poem_id):
    conn = get_db()
    conn.execute(
        """UPDATE user_poems SET status = 'completed', completed_at = CURRENT_TIMESTAMP
           WHERE user_id = ? AND poem_id = ?""",
        (user_id, poem_id),
    )
    conn.commit()
    conn.close()


def get_completed_poems(user_id):
    conn = get_db()
    rows = conn.execute(
        """SELECT p.title, p.author_name, up.completed_at, up.last_recited_at
           FROM poems p
           JOIN user_poems up ON p.id = up.poem_id AND up.user_id = ?
           WHERE up.status = 'completed'
           ORDER BY up.completed_at DESC""",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── recital ───────────────────────────────────────────────────────────────────

def save_recital_attempt(user_id, poem_id, attempt_text, score, passed):
    conn = get_db()
    poem = get_poem(poem_id)
    conn.execute(
        """INSERT INTO recital_attempts
           (user_id, poem_id, attempt_text, expected_text, score, passed)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_id, poem_id, attempt_text, poem["body"], score, int(passed)),
    )
    if passed:
        conn.execute(
            """UPDATE user_poems SET last_recited_at = CURRENT_TIMESTAMP
               WHERE user_id = ? AND poem_id = ?""",
            (user_id, poem_id),
        )
    conn.commit()
    conn.close()


# ── learning helpers ──────────────────────────────────────────────────────────

FILL_PERCENTS = {"fill_10": 10, "fill_25": 25, "fill_50": 50, "fill_100": 100}
STAGE_ORDER = ["reading", "notes", "fill_10", "fill_25", "fill_50", "fill_100"]

# user-facing names for the internal stage keys
STAGE_LABELS = {
    "reading": "reading",
    "notes": "notes",
    "fill_10": "10% hidden",
    "fill_25": "25% hidden",
    "fill_50": "50% hidden",
    "fill_100": "all hidden",
    "stanzas": "stanza by stanza",
}


def next_stage(current):
    try:
        idx = STAGE_ORDER.index(current)
        return STAGE_ORDER[idx + 1] if idx + 1 < len(STAGE_ORDER) else None
    except ValueError:
        return "reading"


def prepare_fill_tokens(body, percent, seed):
    """Return list of token dicts for fill-in-blanks rendering."""
    lines = body.split("\n")
    all_word_indices = []
    flat_tokens = []

    for line in lines:
        words = line.split(" ")
        first_on_line = True
        for w in words:
            if w:
                if not first_on_line:
                    flat_tokens.append({"type": "space", "_idx": -1})
                first_on_line = False
                idx = len(flat_tokens)
                flat_tokens.append({"type": "word", "text": w, "_idx": idx})
                if len(re.sub(r"[^\w]", "", w)) > 2:
                    all_word_indices.append(idx)
            else:
                flat_tokens.append({"type": "space", "_idx": -1})
        flat_tokens.append({"type": "newline", "_idx": -1})

    n_blanks = max(1, int(len(all_word_indices) * percent / 100))
    rng = random.Random(seed)
    blanked = set(rng.sample(all_word_indices, min(n_blanks, len(all_word_indices))))

    result = []
    blank_n = 0
    for tok in flat_tokens:
        if tok["type"] != "word":
            result.append({"type": tok["type"]})
        elif tok["_idx"] in blanked:
            word = tok["text"]
            result.append({
                "type": "blank",
                "n": blank_n,
                "word": word,
                "size": max(3, len(re.sub(r"[^\w]", "", word))),
            })
            blank_n += 1
        else:
            result.append({"type": "word", "text": tok["text"]})

    return result


def check_fill_answers(body, percent, seed, form):
    tokens = prepare_fill_tokens(body, percent, seed)
    blanks = {t["n"]: t["word"] for t in tokens if t["type"] == "blank"}
    correct = 0
    results = {}
    for n, expected in blanks.items():
        submitted = form.get(f"blank_{n}", "").strip()
        clean_e = re.sub(r"[^\w]", "", expected).lower()
        clean_s = re.sub(r"[^\w]", "", submitted).lower()
        ok = clean_s == clean_e
        results[n] = {"submitted": submitted, "expected": expected, "correct": ok}
        if ok:
            correct += 1
    score = correct / len(blanks) if blanks else 0
    return results, score


def prepare_recital_tokens(body):
    """Every word in the poem becomes a blank (for recital mode)."""
    result = []
    for line in body.split("\n"):
        if result:
            result.append({"type": "newline"})
        words = line.split(" ")
        first = True
        for word in words:
            if word:
                if not first:
                    result.append({"type": "space"})
                result.append({"type": "blank", "word": word})
                first = False
    return result


def score_recital(attempt, body):
    poem_words = re.findall(r"[a-zA-Z']+", body)
    expected = [w[0].lower() for w in poem_words]
    typed = [c.lower() for c in re.findall(r"[a-zA-Z]", attempt)]
    if not expected:
        return 0, False, 0, 0
    correct = sum(1 for a, e in zip(typed, expected) if a == e)
    score = correct / len(expected)
    return round(score * 100), score >= 0.9, correct, len(expected)


# ── stanza by stanza ────────────────────────────────────────────────────────────

# a stanza is learned through a gentle difficulty ramp (prepare_stanza_levels):
# read it, then progressively more words are hidden until you recite it in
# full. the hiding is nested (each level blanks a superset of the last) and its
# order is seeded by the stanza index, so every stanza is blanked differently.
STANZA_LEVELS = [
    {"key": "read",   "frac": 0.0,  "label": "read it through",
     "hint": "Read the whole stanza. Take your time, then start."},
    {"key": "some",   "frac": 0.4,  "label": "fill the gaps",
     "hint": "Type the first letter of each hidden word. 3 wrong tries fills it in for you."},
    {"key": "most",   "frac": 0.75, "label": "most words hidden",
     "hint": "More words are hidden — keep going."},
    {"key": "recite", "frac": 1.0,  "label": "recite it all",
     "hint": "The whole stanza, from memory."},
]


def split_stanzas(body):
    """Split a poem into stanzas on blank-line boundaries."""
    text = body.replace("\r\n", "\n").replace("\r", "\n")
    chunks = re.split(r"\n[ \t]*\n", text)
    return [c.strip("\n") for c in chunks if c.strip()]


def get_stanza_progress(user_id, poem_id):
    """Return the set of stanza indices this user has learned for this poem."""
    conn = get_db()
    rows = conn.execute(
        "SELECT stanza_index FROM stanza_progress WHERE user_id = ? AND poem_id = ?",
        (user_id, poem_id),
    ).fetchall()
    conn.close()
    return {r["stanza_index"] for r in rows}


def mark_stanza_learned(user_id, poem_id, stanza_index):
    conn = get_db()
    conn.execute(
        """INSERT INTO stanza_progress (user_id, poem_id, stanza_index)
           VALUES (?, ?, ?)
           ON CONFLICT(user_id, poem_id, stanza_index)
           DO UPDATE SET learned_at = CURRENT_TIMESTAMP""",
        (user_id, poem_id, stanza_index),
    )
    conn.commit()
    conn.close()


def _tokenize_stanza(stanza):
    """Flatten a stanza into render tokens, numbering the lettered words.

    Returns (tokens, order): tokens is the flat sequence (lettered/word/space/
    newline); order is the list of word indices that are eligible to be blanked
    (words containing a letter). Punctuation-only tokens are always shown.
    """
    tokens = []
    order = []
    widx = 0
    for li, line in enumerate(stanza.split("\n")):
        if li > 0:
            tokens.append({"type": "newline"})
        first = True
        for w in line.split(" "):
            if w == "":
                tokens.append({"type": "space"})
                continue
            if not first:
                tokens.append({"type": "space"})
            first = False
            if re.sub(r"[^a-zA-Z]", "", w):
                tokens.append({"type": "lettered", "text": w, "widx": widx})
                order.append(widx)
                widx += 1
            else:
                tokens.append({"type": "word", "text": w})
    return tokens, order


def _render_level(tokens, blanked):
    """Render flat tokens for one level, blanking the given set of word indices."""
    out = []
    for t in tokens:
        if t["type"] == "lettered":
            if t["widx"] in blanked:
                out.append({"type": "blank", "word": t["text"]})
            else:
                out.append({"type": "word", "text": t["text"]})
        elif t["type"] == "word":
            out.append({"type": "word", "text": t["text"]})
        else:
            out.append({"type": t["type"]})
    return out


def prepare_stanza_levels(stanza, seed):
    """Build the difficulty ramp for one stanza (see STANZA_LEVELS)."""
    tokens, order = _tokenize_stanza(stanza)
    n = len(order)
    shuffled = list(order)
    random.Random(seed).shuffle(shuffled)

    levels = []
    for spec in STANZA_LEVELS:
        k = int(round(n * spec["frac"]))
        blanked = set(shuffled[:k])
        levels.append({
            "key": spec["key"],
            "label": spec["label"],
            "hint": spec["hint"],
            "tokens": _render_level(tokens, blanked),
        })
    return levels
