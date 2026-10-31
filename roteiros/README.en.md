# Scripts for the README animations

[Português](README.md) | **English**

This folder holds the script for each animated SVG in `assets/`. The script
comes before the drawing: it says what each scene teaches, how long it lasts,
what appears, the exact on-screen text (in pt-BR and in English) and how each
element enters and leaves. Whoever draws or fixes an SVG starts here; whoever
changes the product (a command, a number, a name) checks here whether a scene
went stale.

| Animation | Script | Where it appears | Length | Question it answers |
|---|---|---|---|---|
| `deidara-banner.svg` / `-en.svg` | [deidara-banner.en.md](deidara-banner.en.md) | top of the README, right after the badges | 48 s, 6 scenes | why Deidara exists and what it delivers |
| `deidara-fluxo.svg` / `-en.svg` | [deidara-fluxo.en.md](deidara-fluxo.en.md) | "How it works inside" section, before the parts table | 36 s, 5 steps | how a request becomes a Power BI project without guessing anything |

Both animations replace the current SVGs, which today are almost static
(they only pulse). File names and the README `alt` text stay the same.

## The pattern taken from Vegapunk

Vegapunk (the sister repository, `assets/vegapunk-banner.svg` and
`assets/vegapunk-sonar.svg`) has no separate script document: the script is
tucked inside the SVG itself, in a timeline comment
(`/* Linha do tempo: 48 s. Cena 1 0–7 · Cena 2 7–13 ... */`) and one
`/* Cena N */` block per scene. The scripts in this folder spell out in full
what those SVGs do, and Deidara's SVGs must carry the same timeline comment, so
the script and the file can be checked against each other.

Rules taken from Vegapunk's SVGs, which apply to both animations:

1. **One loop, no JavaScript.** One duration for everything (48 s in the
   banner, 31 s in Vegapunk's sonar), and each element has its `@keyframes`
   as percentages of that loop. The scripts give times in seconds; to convert,
   `% = second ÷ length × 100` (in the 48 s banner, 1 s = 2.0833%; in the
   36 s flow, 1 s = 2.7778%).
2. **A narrative arc.** The banner goes from pain to product: (1) what goes
   wrong today, (2) the user's request, (3 and 4) what the product does with
   each part of the request, (5) the measured numbers, (6) the sign-off. The
   "how it works" animation is a numbered walkthrough with a progress strip at
   the top.
3. **A thread across scenes.** In Vegapunk, the request splits into two
   "chips" (query and formula) that rise to the corners, light up when the
   scene is theirs and come back together at the end. Deidara uses the same
   device with the chips **structure** and **report**.
4. **One caption at a time.** One short sentence at the bottom, entering after
   the image and leaving before the next scene. Never two captions on screen.
5. **The wrong thing is shown and discarded, never hidden.** Vegapunk shows the
   made-up function (`CALCULA_BONUS`) turning into a gap and the irrelevant
   hits as a grey echo left behind. Deidara shows the guessed name refused by
   `validar` and the change after approval refused by `gerar`.
6. **Fictional, plausible example, with the example's real names.** Names come
   from the tutorial (`fDesligamento`, `dCargo`, `fMetas->dEmpresa`,
   `Headcount`, `HC Médio`, `Turnover`). No real data.
7. **A number only with where it was measured.** Vegapunk's results scene ends
   with "Measured on requests the engine had never seen." In Deidara, numbers
   come from the README "Results" table and carry a note on where they were
   measured.
8. **The end joins the start.** Everything fades between 98.958% and 100% of
   the loop (the last 0.5 s), and the first scene starts from zero with no
   jump.
9. **Self-contained.** Fonts embedded in base64 (Vegapunk uses Inter, Poppins
   and JetBrains Mono), no external image or link: GitHub serves the SVG as an
   image and blocks anything from outside. The animated content lives in a
   1280 × 640 `<foreignObject>` with HTML and CSS.
10. **Pausable.** Every animated class reads `animation-delay: var(--d, 0s)`
    and `animation-play-state: var(--ps, running)`, as in Vegapunk, to pause or
    freeze a frame during review.
11. **Two languages, one timeline.** The `-en.svg` file has exactly the same
    timings and positions; only the text changes. All interface text is
    translated; table, column, command and file names stay as they are.
    (Vegapunk's English banner let "JOIN provado" slip through in Portuguese:
    the scripts here list every text in both languages so that does not happen
    again.)
12. **Its own accessible label.** Each SVG has `role="img"` and an
    `aria-label` equal to the README `alt`. (Vegapunk's sonar reused the
    banner's label; here each one has its own.)

## What Deidara adds

- **Reduced motion.** Deidara's current SVGs already honour
  `@media (prefers-reduced-motion: reduce)`, and that stays. With reduced
  motion, each animation shows a still final frame that explains itself
  (described at the end of each script).
- **Deidara's palette, not Vegapunk's.** Background `#0B1220` with a `#1E2A44`
  grid and the amber glow of the current banner, as in both projects. Colours
  with a fixed meaning:

| Colour | Hex | Means |
|---|---|---|
| blue | `#60A5FA` | the source and the structure (recipe, catalog) |
| amber | `#F59E0B` | the clay (spec, draft, validation) |
| orange | `#FB923C` | the sculpture (prototype) and the explosion (Katsu!) |
| green | `#34D399` | approval, proof, finished delivery |
| red | `#F87171` | error: guessed name, change without approval |
| grey | `#475569` / `#94A3B8` | what was discarded, supporting text |
| text | `#E2E8F0` | main text |

  Colour is never the only cue: every state also has a word or an icon (✓, ✕,
  "TO CONFIRM", "APPROVED"), as `referencias/design.md` requires.
- **Typography.** Inter for text, Poppins 800 for the name "DEIDARA" and
  "Katsu!", JetBrains Mono for code, file names and commands. Embedded, as in
  Vegapunk (Deidara's current SVGs use system fonts, so text width changes from
  machine to machine).
- **No character art.** Vegapunk has its own illustration. Deidara uses an
  original symbol instead of drawing the Naruto character: the eight-point
  burst from the current banner ("Katsu!") and a simple geometric clay bird,
  made of polygons, as the mascot.

## How to check an SVG against its script

1. The SVG's timeline comment has the same scenes and the same seconds as the
   script.
2. Every text in the "On-screen text" column appears in the pt-BR SVG, and the
   translation on the same row appears in the `-en.svg`.
3. Pausing at each mark (`--ps: paused` and a negative `--d` for the chosen
   second), the frame matches the "What appears" column.
4. No element stays on screen after the exit time written in the script.
5. The numbers in the results scene match the README "Results" table on the
   day the SVG is generated.

## Other possible animations

Vegapunk has two animations, and the two here cover the same places in the
README. If a third one is worth it, the strongest candidates are:

- **`deidara-modelos.svg`**, in the "Layout templates" section: the same
  example page (a Turnover card, bars by reason, a table) re-fitting itself
  into each of the eleven templates, one every 2.5 s, with the template name
  (`faixa-de-kpis`, `executivo`, `causa-raiz`...) and the "Good for" line from
  the table in `referencias/modelos.md`. It shows at a glance what the table
  takes eleven rows to say.
- **`deidara-escultura.svg`**, near the tutorial: only the prototype, large,
  with the ⓘ opening, the "Para aprovar" tab, the comments and the "Copiar
  resumo do aceite" button. Today this appears in short form in scene 4 of the
  banner; it earns its own SVG if the prototype becomes the README's main
  argument.

Neither has a script yet: they only go in if the repository owner wants them.
