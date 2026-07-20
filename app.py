import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
import db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-change-in-production")

db.init_db()


# ── auth helpers ──────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def safe_next(fallback):
    """Return the form's 'next' URL only if it is a local path."""
    nxt = request.form.get("next", "")
    if nxt.startswith("/") and not nxt.startswith("//"):
        return nxt
    return fallback


def sorted_by_request(items, columns):
    """Sort a list of dicts by the request's ?sort= and ?dir= params.

    columns maps a sort key from the URL to the dict field to sort on.
    Returns (items, sort, direction); sort is None if no valid sort asked.
    """
    sort = request.args.get("sort")
    direction = request.args.get("dir", "asc")
    if direction not in ("asc", "desc"):
        direction = "asc"
    if sort not in columns:
        return items, None, direction
    field = columns[sort]

    def key(item):
        v = item.get(field)
        if v is None:
            # rows with no value sort after the rest
            return (1, 0, "")
        if isinstance(v, str):
            return (0, 0, v.lower())
        return (0, v, "")

    items = sorted(items, key=key, reverse=(direction == "desc"))
    return items, sort, direction


# ── auth routes ───────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = db.verify_user(request.form["username"], request.form["password"])
        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("index"))
        flash("Invalid username or password.")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        if not username or not password:
            flash("Username and password required.")
        elif db.create_user(username, password):
            user = db.verify_user(username, password)
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("index"))
        else:
            flash("Username already taken.")
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ── main pages ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/account")
@login_required
def account():
    return render_template("account.html")


# ── all poems ─────────────────────────────────────────────────────────────────

@app.route("/library")
def library():
    q = request.args.get("q", "").strip()
    poems = db.get_all_poems(search=q or None)
    poems, sort, direction = sorted_by_request(poems, {
        "title": "title", "author": "author_name",
        "year": "year_written", "lines": "line_count"})
    in_notebook = set()
    if session.get("user_id"):
        in_notebook = {e["id"] for e in db.get_notebook(session["user_id"])}
    return render_template("library.html", poems=poems, in_notebook=in_notebook,
                           q=q, sort=sort, dir=direction)


def can_view_poem(poem):
    """A poem is viewable if it is public or the viewer added it."""
    if not poem:
        return False
    return bool(poem["is_public"]
                or poem["created_by_user_id"] == session.get("user_id"))


@app.route("/library/poem/<int:poem_id>")
def library_poem(poem_id):
    poem = db.get_poem(poem_id)
    if not can_view_poem(poem):
        return redirect(url_for("library"))
    in_notebook = bool(
        session.get("user_id")
        and db.get_user_poem(session["user_id"], poem_id)
    )
    return render_template("library_poem.html", poem=poem, in_notebook=in_notebook)


@app.route("/poem/add", methods=["GET", "POST"])
@login_required
def add_poem():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        if not title or not body:
            flash("Title and poem text are required.")
        else:
            poem_id = db.create_poem(
                user_id=session["user_id"],
                title=title,
                author_name=request.form.get("author_name", "").strip(),
                body=body,
                period=request.form.get("period", "").strip(),
                year_written=request.form.get("year_written", "").strip() or None,
            )
            db.copy_to_notebook(session["user_id"], poem_id)
            return redirect(url_for("library_poem", poem_id=poem_id))
    return render_template("add_poem.html")


@app.route("/home/poem/<int:poem_id>/copy", methods=["POST"])
@login_required
def copy_to_notebook(poem_id):
    poem = db.get_poem(poem_id)
    if not can_view_poem(poem):
        return redirect(url_for("library"))
    db.copy_to_notebook(session["user_id"], poem_id)
    return redirect(safe_next(url_for("notebook")))


@app.route("/home/poem/<int:poem_id>/remove", methods=["POST"])
@login_required
def remove_from_notebook(poem_id):
    db.remove_from_notebook(session["user_id"], poem_id)
    return redirect(safe_next(url_for("notebook")))


# ── notebook ──────────────────────────────────────────────────────────────────

@app.route("/notebook")
@login_required
def notebook():
    entries = db.get_notebook(session["user_id"])
    entries, sort, direction = sorted_by_request(entries, {
        "title": "title", "author": "author_name", "year": "year_written",
        "lines": "line_count", "status": "status"})
    return render_template("notebook.html", entries=entries,
                           stage_labels=db.STAGE_LABELS,
                           sort=sort, dir=direction)


# ── learn (part by part) ──────────────────────────────────────────────────────

@app.route("/learn/<int:poem_id>/stanzas")
@login_required
def learn_stanzas(poem_id):
    poem = db.get_poem(poem_id)
    if not can_view_poem(poem):
        return redirect(url_for("library"))
    user_id = session["user_id"]

    # learning a poem adds it to your favourites (no-op if already there)
    db.copy_to_notebook(user_id, poem_id)
    db.set_learning_mode(user_id, poem_id, "stanzas")
    chunks = db.split_chunks(poem["body"])
    learned = {i for i in db.get_stanza_progress(user_id, poem_id)
               if i < len(chunks)}

    steps = []
    for i, chunk in enumerate(chunks):
        steps.append({
            "index": i,
            "label": i + 1,
            "title": chunk["title"],
            "preview": chunk["text"].split("\n", 1)[0],
            "learned": i in learned,
        })
    next_index = next((i for i in range(len(chunks)) if i not in learned), None)

    just_learned = request.args.get("learned", type=int)
    if just_learned is not None and not (0 <= just_learned < len(chunks)):
        just_learned = None

    return render_template(
        "learn_stanzas.html",
        poem=poem,
        steps=steps,
        total=len(chunks),
        learned_count=len(learned),
        next_index=next_index,
        just_learned=just_learned,
    )


@app.route("/learn/<int:poem_id>/stanza/<int:idx>", methods=["GET", "POST"])
@login_required
def learn_stanza(poem_id, idx):
    poem = db.get_poem(poem_id)
    if not can_view_poem(poem):
        return redirect(url_for("library"))
    user_id = session["user_id"]
    db.copy_to_notebook(user_id, poem_id)

    chunks = db.split_chunks(poem["body"])
    if idx < 0 or idx >= len(chunks):
        return redirect(url_for("learn_stanzas", poem_id=poem_id))

    if request.method == "POST":
        # client has confirmed the whole part was recited correctly
        db.mark_stanza_learned(user_id, poem_id, idx)
        return redirect(url_for("learn_stanzas", poem_id=poem_id, learned=idx))

    chunk = chunks[idx]
    tokens, order = db.tokenize_stanza(chunk["text"])
    return render_template(
        "learn_stanza.html",
        poem=poem,
        idx=idx,
        label=idx + 1,
        total=len(chunks),
        title=chunk["title"],
        tokens=tokens,
    )


# ── recital ───────────────────────────────────────────────────────────────────

@app.route("/recital")
@login_required
def recital_pick():
    entries = [e for e in db.get_notebook(session["user_id"])
               if e["status"] in ("learning", "completed")]
    return render_template("recital_pick.html", entries=entries)


@app.route("/recital/<int:poem_id>", methods=["GET", "POST"])
@login_required
def recital(poem_id):
    poem = db.get_poem(poem_id)
    if not poem:
        return redirect(url_for("recital_pick"))
    user_id = session["user_id"]

    if request.method == "POST":
        # client confirmed every word typed correctly
        db.complete_poem(user_id, poem_id)
        db.save_recital_attempt(user_id, poem_id, "", 1.0, True)
        return redirect(url_for("archive"))

    tokens, order = db.tokenize_stanza(poem["body"])
    return render_template("recital.html", poem=poem, tokens=tokens)


@app.route("/recital/<int:poem_id>/aloud")
@login_required
def recital_aloud(poem_id):
    poem = db.get_poem(poem_id)
    if not poem:
        return redirect(url_for("recital_pick"))
    return render_template(
        "recital_aloud.html",
        poem=poem,
        text=poem["body"],
        part_title=None,
        mark_action=None,
        back_url=url_for("recital", poem_id=poem_id),
        back_label="Back to the recital",
    )


@app.route("/learn/<int:poem_id>/stanza/<int:idx>/aloud")
@login_required
def learn_stanza_aloud(poem_id, idx):
    poem = db.get_poem(poem_id)
    if not can_view_poem(poem):
        return redirect(url_for("library"))
    chunks = db.split_chunks(poem["body"])
    if idx < 0 or idx >= len(chunks):
        return redirect(url_for("learn_stanzas", poem_id=poem_id))
    chunk = chunks[idx]
    return render_template(
        "recital_aloud.html",
        poem=poem,
        text=chunk["text"],
        part_title=chunk["title"],
        mark_action=url_for("learn_stanza", poem_id=poem_id, idx=idx),
        back_url=url_for("learn_stanza", poem_id=poem_id, idx=idx),
        back_label="Back to " + chunk["title"].lower(),
    )


# ── archive ───────────────────────────────────────────────────────────────────

@app.route("/archive")
@login_required
def archive():
    completed = db.get_completed_poems(session["user_id"])
    completed, sort, direction = sorted_by_request(completed, {
        "date": "completed_at", "title": "title", "author": "author_name"})
    return render_template("archive.html", completed=completed,
                           sort=sort, dir=direction)


if __name__ == "__main__":
    app.run(debug=True)
