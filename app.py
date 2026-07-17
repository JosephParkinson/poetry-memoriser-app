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


@app.route("/interior")
@login_required
def interior():
    return render_template("interior.html")


# ── library ───────────────────────────────────────────────────────────────────

@app.route("/library")
def library():
    return render_template("library.html", shelves=db.LIBRARY_SHELVES)


@app.route("/library/shelf/<period>")
def library_shelf(period):
    books = db.get_shelf_books(period)
    label = next((s[0] for s in db.LIBRARY_SHELVES if s[1] == period), period.title())
    return render_template("library_shelf.html", books=books, period=period, label=label)


@app.route("/library/book/<int:book_id>")
def library_book(book_id):
    book = db.get_book(book_id)
    if not book:
        return redirect(url_for("library"))
    poems = db.get_book_poems(book_id)
    checked_out = session.get("user_id") and db.has_book(session["user_id"], book_id)
    return render_template("library_book.html", book=book, poems=poems,
                           checked_out=checked_out)


@app.route("/library/book/<int:book_id>/checkout", methods=["POST"])
@login_required
def checkout(book_id):
    db.checkout_book(session["user_id"], book_id)
    return redirect(url_for("library_book", book_id=book_id))


# ── home shelf ────────────────────────────────────────────────────────────────

@app.route("/home/shelf")
@login_required
def home_shelf():
    books = db.get_user_books(session["user_id"])
    return render_template("home_shelf.html", books=books)


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
            return redirect(url_for("notebook_poem", poem_id=poem_id))
    return render_template("add_poem.html")


@app.route("/home/book/<int:book_id>")
@login_required
def home_book(book_id):
    if not db.has_book(session["user_id"], book_id):
        return redirect(url_for("home_shelf"))
    book = db.get_book(book_id)
    poems = db.get_book_poems(book_id)
    user_id = session["user_id"]
    in_notebook = {db.get_user_poem(user_id, p["id"]) is not None for p in poems}
    return render_template("home_book.html", book=book, poems=poems,
                           in_notebook=in_notebook)


@app.route("/home/poem/<int:poem_id>/copy", methods=["POST"])
@login_required
def copy_to_notebook(poem_id):
    db.copy_to_notebook(session["user_id"], poem_id)
    return redirect(safe_next(url_for("notebook")))


# ── notebook ──────────────────────────────────────────────────────────────────

@app.route("/notebook")
@login_required
def notebook():
    entries = db.get_notebook(session["user_id"])
    return render_template("notebook.html", entries=entries,
                           stage_labels=db.STAGE_LABELS)


@app.route("/notebook/<int:poem_id>", methods=["GET", "POST"])
@login_required
def notebook_poem(poem_id):
    poem = db.get_poem(poem_id)
    if not poem:
        return redirect(url_for("notebook"))
    user_id = session["user_id"]
    if request.method == "POST":
        db.save_notes(user_id, poem_id, request.form.get("notes", ""))
        return redirect(safe_next(url_for("notebook_poem", poem_id=poem_id)))
    entry = db.get_notebook_entry(user_id, poem_id)
    up = db.get_user_poem(user_id, poem_id)
    return render_template("notebook_poem.html", poem=poem, entry=entry, up=up)


# ── learn ─────────────────────────────────────────────────────────────────────

@app.route("/learn/<int:poem_id>", methods=["GET", "POST"])
@login_required
def learn(poem_id):
    poem = db.get_poem(poem_id)
    if not poem:
        return redirect(url_for("notebook"))
    user_id = session["user_id"]
    up = db.get_user_poem(user_id, poem_id)
    if not up:
        return redirect(url_for("notebook"))

    mode = request.args.get("mode", up.get("current_learning_mode") or "reading")
    if mode == "stanzas":
        return redirect(url_for("learn_stanzas", poem_id=poem_id))

    if request.method == "POST":
        # client has confirmed all blanks completed correctly
        nxt = db.next_stage(mode)
        if nxt:
            db.set_learning_mode(user_id, poem_id, nxt)
            return redirect(url_for("learn", poem_id=poem_id, mode=nxt))
        else:
            return redirect(url_for("recital", poem_id=poem_id))

    db.set_learning_mode(user_id, poem_id, mode)
    tokens = None
    if mode in db.FILL_PERCENTS:
        tokens = db.prepare_fill_tokens(poem["body"], db.FILL_PERCENTS[mode], seed=poem_id)

    entry = db.get_notebook_entry(user_id, poem_id)
    return render_template(
        "learn.html",
        poem=poem,
        mode=mode,
        tokens=tokens,
        next_mode=db.next_stage(mode),
        entry=entry,
        stages=db.STAGE_ORDER,
        stage_labels=db.STAGE_LABELS,
    )


# ── stanza by stanza ────────────────────────────────────────────────────────────

@app.route("/learn/<int:poem_id>/stanzas")
@login_required
def learn_stanzas(poem_id):
    poem = db.get_poem(poem_id)
    if not poem:
        return redirect(url_for("notebook"))
    user_id = session["user_id"]
    if not db.get_user_poem(user_id, poem_id):
        return redirect(url_for("notebook"))

    db.set_learning_mode(user_id, poem_id, "stanzas")
    stanzas = db.split_stanzas(poem["body"])
    learned = db.get_stanza_progress(user_id, poem_id)

    steps = []
    for i, stanza in enumerate(stanzas):
        steps.append({
            "index": i,
            "label": i + 1,
            "preview": stanza.split("\n", 1)[0],
            "learned": i in learned,
        })
    next_index = next((i for i in range(len(stanzas)) if i not in learned), None)

    return render_template(
        "learn_stanzas.html",
        poem=poem,
        steps=steps,
        total=len(stanzas),
        learned_count=len(learned),
        next_index=next_index,
        just_learned=request.args.get("learned", type=int),
    )


@app.route("/learn/<int:poem_id>/stanza/<int:idx>", methods=["GET", "POST"])
@login_required
def learn_stanza(poem_id, idx):
    poem = db.get_poem(poem_id)
    if not poem:
        return redirect(url_for("notebook"))
    user_id = session["user_id"]
    if not db.get_user_poem(user_id, poem_id):
        return redirect(url_for("notebook"))

    stanzas = db.split_stanzas(poem["body"])
    if idx < 0 or idx >= len(stanzas):
        return redirect(url_for("learn_stanzas", poem_id=poem_id))

    if request.method == "POST":
        # client has confirmed the whole stanza was recited correctly
        db.mark_stanza_learned(user_id, poem_id, idx)
        return redirect(url_for("learn_stanzas", poem_id=poem_id, learned=idx))

    stanza = stanzas[idx]
    return render_template(
        "learn_stanza.html",
        poem=poem,
        idx=idx,
        label=idx + 1,
        total=len(stanzas),
        levels=db.prepare_stanza_levels(stanza, seed=idx),
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

    tokens = db.prepare_recital_tokens(poem["body"])
    return render_template("recital.html", poem=poem, tokens=tokens)


@app.route("/recital/<int:poem_id>/aloud")
@login_required
def recital_aloud(poem_id):
    poem = db.get_poem(poem_id)
    if not poem:
        return redirect(url_for("recital_pick"))
    return render_template("recital_aloud.html", poem=poem)


# ── archive ───────────────────────────────────────────────────────────────────

@app.route("/archive")
@login_required
def archive():
    completed = db.get_completed_poems(session["user_id"])
    return render_template("archive.html", completed=completed)


if __name__ == "__main__":
    app.run(debug=True)
