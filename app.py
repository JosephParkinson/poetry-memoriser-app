from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

POEMS = [
    {
        "id": 1,
        "title": "The Road Not Taken",
        "author": "Robert Frost",
        "text": (
            "Two roads diverged in a yellow wood,\n"
            "And sorry I could not travel both\n"
            "And be one traveler, long I stood\n"
            "And looked down one as far as I could\n"
            "To where it bent in the undergrowth;\n"
            "\n"
            "Then took the other, as just as fair,\n"
            "And having perhaps the better claim,\n"
            "Because it was grassy and wanted wear;\n"
            "Though as for that the passing there\n"
            "Had worn them really about the same,\n"
            "\n"
            "And both that morning equally lay\n"
            "In leaves no step had trodden black.\n"
            "Oh, I kept the first for another day!\n"
            "Yet knowing how way leads on to way,\n"
            "I doubted if I should ever come back.\n"
            "\n"
            "I shall be telling this with a sigh\n"
            "Somewhere ages and ages hence:\n"
            "Two roads diverged in a wood, and I—\n"
            "I took the one less traveled by,\n"
            "And that has made all the difference."
        ),
    },
    {
        "id": 2,
        "title": "She Walks in Beauty",
        "author": "Lord Byron",
        "text": (
            "She walks in beauty, like the night\n"
            "Of cloudless climes and starry skies;\n"
            "And all that's best of dark and bright\n"
            "Meet in her aspect and her eyes;\n"
            "Thus mellowed to that tender light\n"
            "Which heaven to gaudy day denies.\n"
            "\n"
            "One shade the more, one ray the less,\n"
            "Had half impaired the nameless grace\n"
            "Which waves in every raven tress,\n"
            "Or softly lightens o'er her face;\n"
            "Where thoughts serenely sweet express,\n"
            "How pure, how dear their dwelling place.\n"
            "\n"
            "And on that cheek, and o'er that brow,\n"
            "So soft, so calm, yet eloquent,\n"
            "The smiles that win, the tints that glow,\n"
            "But tell of days in goodness spent,\n"
            "A mind at peace with all below,\n"
            "A heart whose love is innocent!"
        ),
    },
    {
        "id": 3,
        "title": "Ozymandias",
        "author": "Percy Bysshe Shelley",
        "text": (
            "I met a traveller from an antique land,\n"
            "Who said: Two vast and trunkless legs of stone\n"
            "Stand in the desert. Near them, on the sand,\n"
            "Half sunk, a shattered visage lies, whose frown,\n"
            "And wrinkled lip, and sneer of cold command,\n"
            "Tell that its sculptor well those passions read\n"
            "Which yet survive, stamped on these lifeless things,\n"
            "The hand that mocked them and the heart that fed;\n"
            "And on the pedestal these words appear:\n"
            "'My name is Ozymandias, king of kings:\n"
            "Look on my works, ye Mighty, and despair!'\n"
            "Nothing beside remains. Round the decay\n"
            "Of that colossal wreck, boundless and bare\n"
            "The lone and level sands stretch far away."
        ),
    },
]

ARCHIVE = [
    {"title": "Sonnet 18", "author": "William Shakespeare", "completed": "2024-01-15"},
    {
        "title": "Do Not Go Gentle into That Good Night",
        "author": "Dylan Thomas",
        "completed": "2024-02-03",
    },
]


def make_book(title, width=18):
    inner = width - 2
    text_w = inner - 2
    words = title.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if len(test) <= text_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    border = "+" + "-" * inner + "+"
    empty  = "|" + " " * inner + "|"
    rows   = ["|" + " " + ln.ljust(text_w) + " " + "|" for ln in lines]
    return "\n".join([border, empty] + rows + [empty, border])


def first_letters_only(text):
    lines = text.split("\n")
    result = []
    for line in lines:
        if line.strip() == "":
            result.append("")
        else:
            words = line.split(" ")
            abbreviated = " ".join((w[0] + "." if w else "") for w in words if w)
            result.append(abbreviated)
    return "\n".join(result)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/interior")
def interior():
    return render_template("interior.html")


@app.route("/library")
def library():
    return render_template("library.html", poems=POEMS)


@app.route("/library/add", methods=["POST"])
def add_poem():
    # Placeholder: form submission acknowledged but not saved yet
    return redirect(url_for("library"))


@app.route("/study")
@app.route("/study/<int:poem_id>")
def study(poem_id=1):
    poem = next((p for p in POEMS if p["id"] == poem_id), POEMS[0])
    mode = request.args.get("mode", "full")

    if mode == "hidden":
        display_text = None
    elif mode == "first_letters":
        display_text = first_letters_only(poem["text"])
    else:
        display_text = poem["text"]

    books = [{"id": p["id"], "art": make_book(p["title"])} for p in POEMS]
    return render_template("study.html", poem=poem, mode=mode,
                           display_text=display_text, books=books)


@app.route("/recital")
@app.route("/recital/<int:poem_id>")
def recital(poem_id=1):
    poem = next((p for p in POEMS if p["id"] == poem_id), POEMS[0])
    return render_template("recital.html", poem=poem)


@app.route("/archive")
def archive():
    return render_template("archive.html", completed=ARCHIVE)


if __name__ == "__main__":
    app.run(debug=True)
