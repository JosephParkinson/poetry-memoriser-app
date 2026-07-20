(function () {
  var STAGES = [
    { frac: 0 }, // Read
    { frac: 0.1 },
    { frac: 0.25 },
    { frac: 0.5 },
    { frac: 0.75 },
    { frac: 1 }, // 100%: all words hidden, underlines shown
    { flow: true, bare: true }, // Flow: first two words of each line cue the rest, no underlines
    { frac: 1, bare: true }, // Recite: all hidden, no underlines
  ];
  var words = Array.from(document.querySelectorAll("#poem .w"));
  var stageBtns = Array.from(document.querySelectorAll(".stage-row button"));
  var poemEl = document.getElementById("poem");
  var controls = document.getElementById("controls");
  var retryBtn = document.getElementById("retry-btn");
  var nextBtn = document.getElementById("next-btn");
  var keyInput = document.getElementById("key-catcher");

  var cur = 0; // current stage index
  var blanks = []; // hidden words this attempt, in poem order
  var at = 0; // position within blanks
  var wrong = 0; // wrong keystrokes on the current blank
  var missed = []; // words auto-revealed this attempt
  var lastMissed = []; // words missed on the finished attempt (for Retry)
  var finished = true;
  var flowRevealAfter = {}; // Flow stage: blanks index -> rest-of-line words to reveal

  function shuffle(a) {
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = a[i];
      a[i] = a[j];
      a[j] = t;
    }
    return a;
  }

  function firstAlpha(word) {
    var m = word.match(/[a-zA-Z]/);
    return m ? m[0].toLowerCase() : null;
  }

  // group the words in poem order into per-line arrays, split on <br>
  function computeLines() {
    var lines = [];
    var current = [];
    Array.from(poemEl.childNodes).forEach(function (node) {
      if (node.nodeType === 1 && node.tagName === "BR") {
        lines.push(current);
        current = [];
      } else if (node.nodeType === 1 && node.classList.contains("w")) {
        current.push(node);
      }
    });
    lines.push(current);
    return lines.filter(function (line) {
      return line.length > 0;
    });
  }

  // Flow stage: only the first two words of each line are typed; the rest
  // of the line reveals once those are done, chaining line to line.
  function setupFlow() {
    computeLines().forEach(function (line) {
      var cue = line.slice(0, 2);
      var rest = line.slice(2);
      blanks = blanks.concat(cue);
      if (rest.length) {
        flowRevealAfter[blanks.length - 1] = rest;
      }
    });
    words.forEach(function (w) {
      w.classList.add("blank-slot");
    });
  }

  // start (or restart) a stage. `force` lists words that must be hidden —
  // used by Retry so anything missed last time is asked again.
  function setStage(i, force) {
    cur = i;
    var st = STAGES[i];
    stageBtns.forEach(function (b, j) {
      b.classList.toggle("current", j === i);
    });
    poemEl.classList.toggle("no-underlines", !!st.bare);
    words.forEach(function (w) {
      w.className = "w";
    });
    controls.style.display = "none";
    blanks = [];
    at = 0;
    wrong = 0;
    missed = [];
    flowRevealAfter = {};

    if (st.frac === 0) {
      finished = true;
      retryBtn.style.display = "none";
      controls.style.display = "block";
      keyInput.blur();
      return;
    }

    if (st.flow) {
      setupFlow();
      finished = false;
      activate(0);
      keyInput.focus();
      return;
    }

    var k = Math.max(1, Math.round(words.length * st.frac));
    var chosen = [];
    (force || []).forEach(function (w) {
      if (chosen.indexOf(w) === -1) chosen.push(w);
    });
    shuffle(words.slice()).forEach(function (w) {
      if (chosen.length < k && chosen.indexOf(w) === -1) chosen.push(w);
    });
    blanks = words.filter(function (w) {
      return chosen.indexOf(w) !== -1;
    });
    blanks.forEach(function (w) {
      w.classList.add("blank-slot");
    });
    finished = false;
    activate(0);
    // focusing the invisible input opens the on-screen keyboard on mobile
    keyInput.focus();
  }

  function activate(i) {
    blanks.forEach(function (b) {
      b.classList.remove("active");
    });
    if (i < blanks.length) {
      wrong = 0;
      blanks[i].classList.add("active");
      blanks[i].scrollIntoView({ block: "nearest" });
    } else {
      finished = true;
      lastMissed = missed.slice();
      retryBtn.style.display = "";
      controls.style.display = "block";
      keyInput.blur();
    }
  }

  // move past the blank just completed (at), revealing any Flow rest-of-line
  // words that were waiting on it, then activate the next blank
  function advance() {
    var done = at;
    at++;
    if (flowRevealAfter[done]) {
      flowRevealAfter[done].forEach(function (w) {
        w.classList.add("filled");
      });
    }
    activate(at);
  }

  function handleChar(ch) {
    if (finished) return;

    var blank = blanks[at];
    var expected = firstAlpha(blank.textContent);
    if (!expected) {
      advance();
      return;
    }

    if (ch.toLowerCase() === expected) {
      blank.classList.remove("active", "flash-wrong");
      blank.classList.add("filled");
      advance();
    } else {
      wrong++;
      clearTimeout(blank.wrongTimer);
      blank.classList.add("flash-wrong");
      blank.wrongTimer = setTimeout(function () {
        blank.classList.remove("flash-wrong");
      }, 300);
      if (wrong >= 3) {
        // 3 wrong tries: fill it in and move on so the user can't get stuck
        blank.classList.remove("active", "flash-wrong");
        blank.classList.add("revealed");
        missed.push(blank);
        advance();
      }
    }
  }

  document.addEventListener("keydown", function (e) {
    if (finished) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key.length !== 1) return;
    handleChar(e.key);
    e.preventDefault();
  });

  // mobile soft keyboards type into the invisible input instead of firing
  // usable keydown events. Desktop keydown preventDefaults before the
  // character reaches the input, so each keystroke is handled exactly once.
  keyInput.addEventListener("input", function () {
    var v = this.value;
    this.value = "";
    if (v) handleChar(v.charAt(v.length - 1));
  });

  // tapping the poem brings the keyboard back if it was dismissed
  poemEl.addEventListener("click", function () {
    if (!finished) keyInput.focus();
  });

  stageBtns.forEach(function (b, i) {
    b.addEventListener("click", function () {
      this.blur();
      setStage(i);
    });
  });

  retryBtn.addEventListener("click", function () {
    this.blur();
    setStage(cur, lastMissed);
  });

  nextBtn.addEventListener("click", function () {
    this.blur();
    if (cur === STAGES.length - 1) {
      document.getElementById("done-form").submit();
    } else {
      setStage(cur + 1);
    }
  });

  setStage(0);
})();
