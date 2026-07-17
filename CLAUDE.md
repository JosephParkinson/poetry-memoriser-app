# CLAUDE.md — The Poetry House

Working notes for this repo. See the memory index for stack/architecture details.

## Design & UI copy — plain classic HTML (important)

The look (since the db-implementation branch): a plain, classic, pre-2005 website —
think Wikipedia or the Stanford Encyclopedia of Philosophy, but dark: near-black
background (#181818), light grey serif text (Georgia/Times), plain lists, tables,
and forms. Links are the same colour as body text, indicated by underline only —
no blue, no visited colour.
Structure: nav has only Home and My Account (Log In when logged out).
Home = search bar (by author or title) + Browse link to All Poems.
My Account = Favourites (internally still the `notebook` routes/tables)
and Completed Poems (internally `archive`), plus log out.

Hard rules — the user will be very upset if these are broken:

- NO ASCII art: no logos, floor plans, book spines, or `#`-style progress bars.
- NO rounded corners, drop shadows, gradients, or web fonts.
- NO animations, transitions, fades, or smooth scrolling.
- NO hover effects — links must not change appearance on hover.
- If it wasn't on the web before 2005, it doesn't go in.

Do NOT write whimsical, poetic, or twee prose. No decorative theme names, no
metaphor-laden flavour text, no purple instructional copy. The user dislikes it.

- Bad:  "climb the winding stair", "let the shape settle behind your eyes",
        "the whole poem is yours", "stanza sealed — climb on"
- Good: "Learn one stanza at a time.", "Type the first letter of each word.",
        "3 / 7 stanzas learned.", "Stanza 2 learned."

Name features for what they do ("stanza by stanza"), not with decorative themes.
Terse, functional, plain sentence case.

## Learning UX — keep the user in flow

Memorising should feel like flow, not boredom or frustration. When building or
tuning learning drills:

- Ramp difficulty gradually. Never jump from "read it" straight to "recite the
  whole thing" — scaffold the steps in between.
- Provide safety nets so the user can't get stuck. e.g. the recite engine
  auto-fills a word after 3 wrong keystrokes.
- Do NOT auto-advance between stages (changed 2026-07-17: the user asked for
  explicit control). After each exercise show Retry and Next buttons; Retry
  re-hides any word missed on the previous attempt.
- Learning is part-by-part only (stanzas, or 4-line groups): stage buttons
  Read / 10% / 25% / 50% / 75% / 100% / Recite on each part. The whole-poem
  stage flow was removed.
