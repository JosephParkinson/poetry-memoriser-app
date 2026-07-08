# CLAUDE.md — The Poetry House

Working notes for this repo. See the memory index for stack/architecture details.

## Writing & UI copy — keep it plain (important)

Keep the retro terminal / text-adventure **look**: ASCII art, monospace, dark
theme, lowercase functional labels, the house/rooms structure that already exists.

Do NOT write whimsical, poetic, or twee prose. No decorative theme names, no
metaphor-laden flavour text, no purple instructional copy. The user dislikes it.

- Bad:  "climb the winding stair", "let the shape settle behind your eyes",
        "the whole poem is yours", "stanza sealed — climb on"
- Good: "learn one stanza at a time", "read it through, then recite",
        "3 / 7 stanzas learned", "stanza 2 learned"

Name features for what they do ("stanza by stanza"), not with decorative themes.
Match the register of the existing copy, e.g. the study/recital pages:
"type the first letter of each word. no clicking needed."

Terse, functional, lowercase.

## Learning UX — keep the user in flow

Memorising should feel like flow, not boredom or frustration. When building or
tuning learning drills:

- Ramp difficulty gradually. Never jump from "read it" straight to "recite the
  whole thing" — scaffold the steps in between.
- Provide safety nets so the user can't get stuck. e.g. the recite engine
  auto-fills a word after 3 wrong keystrokes.
- Let the user keep momentum (auto-advance between steps rather than making them
  click through).
