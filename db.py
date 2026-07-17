import sqlite3
import hashlib
import os
import re

from werkzeug.security import generate_password_hash, check_password_hash

# resolve paths against this file, not the working directory, so the app
# finds its database no matter where the server is started from.
# POETRY_DB_PATH overrides the database location (used in deployment).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("POETRY_DB_PATH",
                         os.path.join(BASE_DIR, "poetry_house.db"))


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    with open(os.path.join(BASE_DIR, "schema.sql")) as f:
        conn.executescript(f.read())
    conn.close()


# ── auth ──────────────────────────────────────────────────────────────────────

def create_user(username, password):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
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
    if not row:
        conn.close()
        return None
    stored = row["password_hash"]
    if "$" in stored:
        ok = check_password_hash(stored, password)
    else:
        # account from before salted hashing: check the legacy unsalted
        # sha256 hash, and upgrade it to a salted one on success.
        ok = stored == hashlib.sha256(password.encode()).hexdigest()
        if ok:
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (generate_password_hash(password), row["id"]),
            )
            conn.commit()
    conn.close()
    return dict(row) if ok else None


# ── all poems (public) ────────────────────────────────────────────────────────

def get_all_poems(search=None):
    """Every public poem, with a line count, for the All Poems page.

    With search, only poems whose title or author contains that text.
    """
    conn = get_db()
    sql = """SELECT id, title, author_name, year_written, body
             FROM poems WHERE is_public = 1"""
    params = []
    if search:
        sql += " AND (title LIKE ? OR author_name LIKE ?)"
        params = ["%" + search + "%"] * 2
    sql += " ORDER BY author_name, year_written, title"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    poems = []
    for r in rows:
        p = dict(r)
        body = p.pop("body")
        p["line_count"] = sum(1 for ln in body.splitlines() if ln.strip())
        poems.append(p)
    return poems


def create_poem(user_id, title, author_name, body, period=None, year_written=None):
    conn = get_db()
    cur = conn.execute(
        """INSERT INTO poems
           (title, author_name, body, period, year_written,
            is_public_domain, is_public, created_by_user_id)
           VALUES (?, ?, ?, ?, ?, 0, 1, ?)""",
        (title, author_name or None, body, period or None,
         year_written or None, user_id),
    )
    poem_id = cur.lastrowid
    conn.commit()
    conn.close()
    return poem_id


def get_poem(poem_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM poems WHERE id = ?", (poem_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


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


def remove_from_notebook(user_id, poem_id):
    """Remove a poem from the user's favourites.

    Learning progress (stanza_progress, recital history) is kept, so adding
    the poem back restores it.
    """
    conn = get_db()
    conn.execute(
        "DELETE FROM user_poems WHERE user_id = ? AND poem_id = ?",
        (user_id, poem_id),
    )
    conn.execute(
        "DELETE FROM notebook_entries WHERE user_id = ? AND poem_id = ?",
        (user_id, poem_id),
    )
    conn.commit()
    conn.close()


def get_notebook(user_id):
    conn = get_db()
    rows = conn.execute(
        """SELECT p.id, p.title, p.author_name, p.year_written, p.body,
                  up.status, up.current_learning_mode, ne.notes
           FROM poems p
           JOIN user_poems up ON p.id = up.poem_id AND up.user_id = ?
           LEFT JOIN notebook_entries ne ON ne.poem_id = p.id AND ne.user_id = ?
           WHERE up.status IN ('notebook','learning','completed')
           ORDER BY up.copied_to_notebook_at""",
        (user_id, user_id),
    ).fetchall()
    conn.close()
    entries = []
    for r in rows:
        e = dict(r)
        body = e.pop("body")
        e["line_count"] = sum(1 for ln in body.splitlines() if ln.strip())
        entries.append(e)
    return entries


def get_user_poem(user_id, poem_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM user_poems WHERE user_id = ? AND poem_id = ?",
        (user_id, poem_id),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


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

# user-facing names for the stored learning-mode keys. Only 'stanzas' is set
# by the current code; the fill_* / reading / notes keys remain so poems
# learned under the old whole-poem stages still display sensibly.
STAGE_LABELS = {
    "reading": "reading",
    "notes": "notes",
    "fill_10": "10% hidden",
    "fill_25": "25% hidden",
    "fill_50": "50% hidden",
    "fill_100": "all hidden",
    "stanzas": "in parts",
}


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


# ── learn in parts ────────────────────────────────────────────────────────────

def split_stanzas(body):
    """Split a poem into stanzas on blank-line boundaries."""
    text = body.replace("\r\n", "\n").replace("\r", "\n")
    chunks = re.split(r"\n[ \t]*\n", text)
    return [c.strip("\n") for c in chunks if c.strip()]


CHUNK_LINES = 4


def split_chunks(body):
    """Split a poem into learnable parts, one per stanza.

    A poem with no stanza breaks (and more than CHUNK_LINES + 2 lines) is
    split into groups of CHUNK_LINES lines instead, so long unbroken poems
    can still be learned in pieces.
    Returns a list of {"text", "title"} dicts.
    """
    stanzas = split_stanzas(body)
    if len(stanzas) == 1:
        lines = stanzas[0].split("\n")
        if len(lines) > CHUNK_LINES + 2:
            groups = [lines[i:i + CHUNK_LINES]
                      for i in range(0, len(lines), CHUNK_LINES)]
            # avoid a trailing one-line part
            if len(groups[-1]) == 1:
                groups[-2].extend(groups.pop())
            chunks = []
            start = 1
            for g in groups:
                chunks.append({"text": "\n".join(g),
                               "title": "Lines %d–%d" % (start, start + len(g) - 1)})
                start += len(g)
            return chunks
    return [{"text": s, "title": "Stanza %d" % (i + 1)}
            for i, s in enumerate(stanzas)]


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


def tokenize_stanza(stanza):
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


