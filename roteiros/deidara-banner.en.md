# Script: `deidara-banner.svg`

[Português](deidara-banner.md) | **English**

| | |
|---|---|
| Files | `assets/deidara-banner.svg` (pt-BR) and `assets/deidara-banner-en.svg` |
| Where | top of `README.md` / `README.en.md`, right after the badges |
| Canvas | 1280 × 640, background `#0B1220`, 32 px grid in `#1E2A44` |
| Length | 48 s loop, 6 scenes |
| `aria-label` / `alt` (pt) | Deidara: do pedido ao painel Power BI, com protótipo aprovado antes do projeto |
| `aria-label` / `alt` (en) | Deidara: from request to Power BI report, with an approved prototype before the project |
| Vegapunk counterpart | `vegapunk-banner.svg` (48 s, 6 scenes, same arc) |

## The idea in one sentence

Power BI reports usually go wrong in two ways: someone guesses a column name,
and someone builds the whole report before the manager sees it. The banner
shows both mistakes, then Deidara fixing each one (the sources' real
structure; a prototype approved before the project), the explosion that
generates the project and the numbers that prove it.

## Timeline

Comment at the top of the `<style>` in both SVGs (kept in Portuguese in both
files, as in Vegapunk's English banner):

```css
/* Linha do tempo: 48 s. Cena 1 0–7 · Cena 2 7–13 · Cena 3 13–23 · Cena 4 23–35 · Cena 5 35–43 · Cena 6 43–48 */
```

| Scene | Time | Name | Teaches |
|---|---|---|---|
| 1 | 0–7 s | The two mistakes | guessing names and building before showing are expensive |
| 2 | 7–13 s | The request | one request holds two questions: what the sources have and what the manager wants to see |
| 3 | 13–23 s | The structure comes back | Deidara connects to nothing: the recipe goes out, only structure comes back, and every name comes from the catalog |
| 4 | 23–35 s | The sculpture | the manager approves a prototype with fictional numbers before any project exists |
| 5 | 35–43 s | Katsu! | after the "yes", the complete project comes out, and the numbers are measured |
| 6 | 43–48 s | Sign-off | the name and the three promises |

Thread across scenes: the request splits into two chips, **structure** (blue,
`#60A5FA`) and **report** (orange, `#FB923C`). They rise to the top corners,
each one lights up in its own scene (3 and 4) and they join again in scene 6,
just like Vegapunk's "query" and "formula" chips.

---

## Scene 1 · The two mistakes (0–7 s)

**Teaches.** The two defects Deidara exists to prevent. The left one is
technical (a made-up name); the right one is about process (building before
approval). Together they make the viewer think "I've been there".

**What appears.** Split screen down the middle, as in Vegapunk.

- Left (background `rgba(96,165,250,.04)`, right border `#1E2A44`): a
  548 × 220 editor card, header "Power BI · measure" with a blue dot. A line
  of DAX is typed into it in JetBrains Mono 22 px:
  `Turnover = DIVIDE([Desligamentos], COUNTROWS(Funcionarios))`.
- Right (background `rgba(251,146,60,.05)`): a card of the same size, header
  "Meeting · finished report" with an orange dot, showing a thumbnail of a
  finished report (three cards and a bar chart, numbers not legible). Under the
  thumbnail, a speech bubble from the manager.

**On-screen text.**

| Element | pt-BR | en |
|---|---|---|
| left header | Power BI · medida | Power BI · measure |
| code | `Turnover = DIVIDE([Desligamentos], COUNTROWS(Funcionarios))` | same (it is code) |
| left error | Funcionarios não existe no modelo | Funcionarios is not in the model |
| right header | Reunião · painel pronto | Meeting · finished report |
| manager's bubble | Não era isso que eu pedi. | That's not what I asked for. |
| stamp | REFAZER | REDO |
| caption (5.5–6.9 s) | Adivinhar o nome da **tabela**. Construir antes de **mostrar**. | Guess the **table** name. Build before you **show**. |

**Motion.**

| Mark | What happens |
|---|---|
| 0.3 s | typing starts on the left, `steps()` with one step per character, blinking cursor (`blink`, 1 s) |
| 1.6 s | typing reaches `Funcionarios`; the word turns red (`#F87171`) and shakes 4 px side to side for 0.5 s |
| 1.8 s | the error badge rises 8 px and appears under the word (background `#3A1420`, border `#F87171`, alert icon) |
| 2.4 s | on the right, the report thumbnail rises into view; the bars grow from the left (`scaleX`) |
| 3.4 s | the manager's bubble appears with a slight scale (0.92 → 1) |
| 3.9 s | a red stamp rotated −10° drops onto the thumbnail from scale 1.6 to 1 |
| 5.5 s | the caption rises 10 px into view |
| 6.6–7.0 s | both halves slide towards the centre at scale 0.9 and fade, as in Vegapunk; the caption fades with them |

---

## Scene 2 · The request (7–13 s)

**Teaches.** The user describes the report in plain language, the way they
would tell a colleague. Deidara reads it and separates two different
questions.

**What appears.**

- The mascot (a geometric clay bird in amber and orange) enters from the right
  and stays in the bottom-right corner until scene 6.
- A large speech bubble in the centre, labelled "you", with the request.
- The request's keywords get a light background one after another.
- The bubble dissolves and the words become two chips side by side in the
  middle of the screen.

**On-screen text.**

| Element | pt-BR | en |
|---|---|---|
| bubble label | você | you |
| request | Quero os desligamentos por motivo e cargo, com a meta de turnover por empresa. | I want terminations by reason and role, with the turnover target by company. |
| highlighted words | desligamentos · motivo · cargo · meta de turnover · empresa | terminations · reason · role · turnover target · company |
| blue chip | estrutura · o que existe nas fontes | structure · what the sources have |
| orange chip | painel · o que o gestor quer ver | report · what the manager wants to see |
| caption (10.5–12.9 s) | Um pedido, duas perguntas. O Deidara responde cada uma. | One request, two questions. Deidara answers each one. |

**Motion.**

| Mark | What happens |
|---|---|
| 7.0 s | the background grid fades in (opacity 0 → 1 over 0.8 s) and stays until 47.5 s |
| 7.3 s | the bubble appears with scale 0.92 → 1 |
| 7.4 s | the mascot enters from the right (`translateX(120%)` → 0, curve `cubic-bezier(.2,.8,.2,1)`) |
| 7.9–9.1 s | the five words light up in sequence, 0.3 s apart |
| 10.0 s | the bubble fades; the two chips are born joined in the centre (one with a rounded left edge, the other with a rounded right edge, forming a single pill) and move 90 px apart |
| 10.5 s | the caption enters |
| 13.0–13.3 s | the caption leaves; the chips rise to the top corners (blue at x 56, orange at x 874, y 48) |

---

## Scene 3 · The structure comes back (13–23 s)

**Teaches.** Deidara connects to no source. It hands over a recipe, someone
with access runs it and pastes the result, and only the structure comes back:
no data rows. Every name in the report comes from that catalog, and the
friendly name is written on top of the real one.

**What appears.** The **structure** chip lights up in its corner (opacity 1);
the **report** chip stays at 30%.

- On the left, a vertical blue band titled "YOUR SOURCE" with two icons:
  database (ERP · SQL Server) and spreadsheet (Targets · Excel). A dashed line
  separates the band from the rest of the screen, like a wall.
- A `receita_sql.sql` file card crosses the wall from right to left. The
  file's first line is a comment with the instruction.
- A queue of small "tokens" in JetBrains Mono comes back through the wall,
  left to right: table names, column names and types.
- One different token, grey, with a table-row icon and the text of a record
  ("data row"), tries to cross and hits the wall: it stops, goes grey and
  drops to the floor of the band.
- On the right, the tokens slot into a catalog table with two columns: "at the
  source" (real name) and "in the report" (friendly name).
- At the bottom corner of the table, a fixed counter.

**On-screen text.**

| Element | pt-BR | en |
|---|---|---|
| band title | SUA FONTE | YOUR SOURCE |
| band subtitle | o Deidara não se conecta a nada | Deidara connects to nothing |
| icons | ERP · SQL Server / Metas · Excel | ERP · SQL Server / Targets · Excel |
| recipe's 1st line | `-- rode no SSMS e cole a grade` | `-- run in SSMS and paste the grid` |
| tokens that cross | `F_DESLIGAMENTO` · `DATADESLIGAMENTO date` · `F_CARGO` · `CODCARGO int` · `Metas` | same (they are source names) |
| blocked token | 1043 · Ana S. · 12/03/2024 | same |
| blocked token label | fica na fonte | stays at the source |
| catalog headers | na fonte · no painel | at the source · in the report |
| catalog rows | `F_DESLIGAMENTO` → fDesligamento · `DATADESLIGAMENTO` → Data de desligamento · `CODCARGO` → Cód. Cargo · `Metas` → fMetas | same (see the note below) |
| counter | linhas de dado: 0 | data rows: 0 |
| table badge | nomes reais do catálogo | real names from the catalog |
| caption (19.5–22.8 s) | A receita vai. Só a estrutura volta. | The recipe goes out. Only the structure comes back. |

The friendly names stay in Portuguese in the English SVG too: they are the
names Deidara actually generates, and the English README says the report comes
out in pt-BR.

**Motion.**

| Mark | What happens |
|---|---|
| 13.3 s | the "YOUR SOURCE" band slides in from the left (−40 px → 0); the dashed wall draws top to bottom (`stroke-dashoffset`) |
| 14.2 s | the `receita_sql.sql` card enters from the right and slides to the wall over 1.2 s |
| 15.4 s | the card crosses the wall and shrinks into the ERP icon; the icon pulses once (scale 1 → 1.08 → 1) |
| 16.0–17.6 s | five tokens cross the wall to the right, 0.3 s apart, each with a short blue trail |
| 16.9 s | the grey token leaves with them, hits the wall, bounces back 6 px, loses its colour and drops 30 px; the "stays at the source" label appears beside it and fades at 18.5 s |
| 17.6–18.8 s | the catalog rows slide in from the left (−12 px → 0), 0.3 s apart; in the "in the report" column, the friendly name is typed |
| 18.9 s | the "real names from the catalog" badge pops (scale 0.6 → 1.1 → 1) |
| 18.9 s | the "data rows: 0" counter gets a green background for 1 s and goes back |
| 19.5 s | the caption enters |
| 22.4–23.0 s | everything in the scene rises 16 px and fades; the **structure** chip goes back to 30% |

---

## Scene 4 · The sculpture (23–35 s)

**Teaches.** Before any project, the manager sees the report as it will look,
with fictional numbers, understands each number (ⓘ) and approves in a
dedicated tab. The approval is recorded and locks the spec: change anything
afterwards and Deidara refuses to generate.

**What appears.** The **report** chip lights up in its corner; the
**structure** chip stays at 30%.

- A stylised browser window (bar with three dots and the file name
  `argila.prototipo.html`), 900 × 420, centred.
- Inside, a page in the `faixa-de-kpis` template: icon rail on the left,
  "Visão geral" title with the page's question below it, a row of three cards,
  a bar chart by reason and a table by role with the bar-against-target inside
  the cell.
- A strip at the top of the window, visible throughout this scene: "fictional
  numbers".
- An ⓘ in the corner of the Turnover card opens a tooltip.
- The window switches to the "Para aprovar" tab: a three-item checklist and a
  decision field.
- The APPROVED stamp drops onto the window, with the approval code below it.
- Last, a "ghost": a change made after approval, refused.

**On-screen text.**

| Element | pt-BR | en |
|---|---|---|
| window bar | `argila.prototipo.html` | same |
| warning strip | números fictícios | fictional numbers |
| tabs | Visão geral · Turnover · Modelo de dados · Pendências · Para aprovar | same (the real tabs are in pt-BR) |
| page title | Visão geral | same |
| page question | Onde o turnover passou da meta? | same |
| cards | Turnover 2,1% (meta 1,8%) · Desligamentos 148 · HC Médio 7.040 | same (the prototype is in pt-BR) |
| bars | Motivo A … Motivo E | same |
| ⓘ tooltip | Turnover = desligamentos do período ÷ headcount médio. Menor é melhor. | Turnover = terminations in the period ÷ average headcount. Lower is better. |
| checklist | ✓ os indicadores dizem o que eu preciso · ✓ os cortes estão certos · ✓ as pendências foram decididas | ✓ the KPIs say what I need · ✓ the breakdowns are right · ✓ the open items are decided |
| manager | Aprovo. | Approved. |
| stamp | APROVADO | APPROVED |
| approval code | aceite 7F3A·C21E · argila + catálogos | approval 7F3A·C21E · spec + catalogs |
| ghost | `"cor": "#FF0000"` em fMetas, depois do aceite | `"cor": "#FF0000"` on fMetas, after approval |
| ghost refusal | gerar recusa: mudou depois do aceite. Novo protótipo, novo "sim". | generate refuses: changed after approval. New prototype, new "yes". |
| caption (31.0–34.8 s) | Primeiro a escultura. O gestor decide. | Sculpture first. The manager decides. |

The ⓘ tooltip and the checklist are translated in the English SVG because
they explain the scene to the reader; the texts that belong to the prototype
(tabs, titles, numbers) stay in pt-BR, like the real prototype.

**Motion.**

| Mark | What happens |
|---|---|
| 23.0 s | the window rises 16 px into view; the "fictional numbers" strip flashes once |
| 23.4–24.6 s | the page background draws itself: rail, title, panels (opacity in sequence, 0.2 s apart) |
| 24.6–25.6 s | the cards drop 30 px into place, one every 0.3 s; the numbers count from 0 to their value (CSS counter with `@property`, as in Vegapunk) |
| 25.2 s | the bars grow from the left; the table's target bars grow and the target line appears on top |
| 26.4 s | the cursor moves to the ⓘ; the tooltip opens with scale 0.92 → 1 and stays 2 s |
| 28.4 s | the tooltip closes; the "Para aprovar" tab gets underlined and the window content slides left |
| 28.8–29.7 s | the three checklist items get a green ✓, 0.3 s apart |
| 30.0 s | the "Approved." bubble appears beside the window |
| 30.4 s | the APPROVED stamp drops rotated −10°, from scale 1.6 to 1 (the `stamp` the current banner already has) |
| 30.8 s | the approval code appears under the stamp with a padlock closing |
| 31.0 s | the caption enters |
| 32.0 s | the ghost enters from the right, in light red, and touches the padlock |
| 32.4 s | the padlock shakes 4 px; the ghost goes grey and the refusal appears below it |
| 33.8 s | the ghost leaves to the right |
| 34.4–35.0 s | the window and the caption rise 16 px and fade; the **report** chip goes back to 30% |

---

## Scene 5 · Katsu! (35–43 s)

**Teaches.** Only after approval does Deidara generate the real Power BI
project, plus everything the team needs for sign-off. And what the README says
was measured.

**What appears.** Two moments.

1. **The explosion (35.0–38.6 s).** The eight-point burst from the current
   banner, with "Katsu!" in the middle, is born in the centre, grows and
   explodes into amber and orange particles. Out of the particles comes a file
   tree in JetBrains Mono on the left, and a Power BI Desktop icon on the right
   with a `.pbip → .pbix` arrow.
2. **The numbers (38.6–43.0 s).** Four panels, as in Vegapunk's scene 5, each
   with a large number counting from 0 to its value, the label and a thin bar
   below it.

**On-screen text.**

| Element | pt-BR | en |
|---|---|---|
| explosion | Katsu! | Katsu! |
| tree | `Painel.pbip` · `Painel.SemanticModel/` (TMDL) · `Painel.Report/` (PBIR) · `sql/erp/01_views.sql` · `sql/erp/02_conferencia.sql` · `sql/erp/03_qualidade.sql` · `HOMOLOGACAO.md` · `LEIA-ME.md` · `docs/dicionario_indicadores.md` | same (they are file names) |
| arrow | abre no Desktop, salva como .pbix | opens in Desktop, saves as .pbix |
| panel 1 | **24 de 24** · arquivos JSON do projeto conferidos contra os schemas da Microsoft | **24 of 24** · project JSON files checked against Microsoft's schemas |
| panel 2 | **11** · modelos de layout, do protótipo ao .pbip | **11** · layout templates, from prototype to .pbip |
| panel 3 | **31** · técnicas de visual geradas prontas | **31** · visual techniques generated ready to use |
| panel 4 | **0** · linhas de dado que as receitas devolvem | **0** · data rows the recipes return |
| note (40.6–42.8 s) | Medido no exemplo do repositório: um ERP fictício em SQL Server e uma planilha de metas. | Measured on the repository example: a fictional SQL Server ERP and a targets spreadsheet. |

**Where the numbers come from.** The README "Results" table. Before generating
the SVG, check whether any of them changed (the test count changes every
release, so it was left out; the four above change rarely). Panel 4 counts
down, from any number to 0, so the zero gets noticed.

**Motion.**

| Mark | What happens |
|---|---|
| 35.0 s | the burst is born in the centre (scale 0.2 → 1) with "Katsu!" in Poppins 800 |
| 35.6 s | the burst swells (1 → 1.25) and explodes: 16 particles fly outward with `cubic-bezier(.2,.8,.2,1)` and fade in 0.8 s; the amber background glow doubles for 0.4 s |
| 36.2–37.8 s | the tree lines appear top to bottom, 0.15 s apart, indented by folder |
| 37.0 s | the Desktop icon and the arrow enter from the right |
| 38.4–38.6 s | the tree and the icon blur (`blur(8px)`) and fade, like Vegapunk's scene transition |
| 38.6–40.4 s | the four panels rise 40 px, 0.3 s apart; the numbers count with `cubic-bezier(.15,.7,.3,1)`; the thin bars grow when the number stops |
| 40.6 s | the note appears below |
| 42.4–43.0 s | panels and note blur and fade |

---

## Scene 6 · Sign-off (43–48 s)

**Teaches.** Name, promise and where Deidara runs. It is the frame that sticks
in memory and the one shown to people with reduced motion.

**What appears.** The current banner's final drawing, redone with the
embedded fonts: a large "Deidara" in the centre, the subtitle, the three amber
pills and a footer line. The **structure** and **report** chips come down from
the corners and join into a single pill above the name. The mascot stays in
its corner.

**On-screen text.**

| Element | pt-BR | en |
|---|---|---|
| joined chips | estrutura · painel | structure · report |
| name | DEIDARA | DEIDARA |
| subtitle | primeiro a escultura. depois, a explosão. | sculpture first. then, the explosion. |
| pills | Só estrutura, nunca dado · Nenhum nome adivinhado · .pbip pronto para o Desktop | Structure only, never data · No guessed names · .pbip ready for Desktop |
| footer | Claude Code · Power BI .pbip (TMDL + PBIR) · SQL Server · Excel · MIT | same |

The subtitle is the README's closing line ("primeiro a escultura. depois, a
explosão."), so the banner and the README footer close on the same idea.

**Motion.**

| Mark | What happens |
|---|---|
| 43.0 s | the chips come down from the corners with a spring (`cubic-bezier(.3,1.4,.5,1)`) and join at x 320 / 610, y 140 |
| 43.6 s | "DEIDARA" appears with scale 0.92 → 1 and letter spacing .18em → .06em |
| 44.0 s | the subtitle rises 10 px |
| 44.3 s | the three pills rise 10 px, 0.15 s apart |
| 44.6 s | the footer appears |
| 47.5–48.0 s | everything fades together (opacity 1 → 0), mascot and grid included, and the loop goes back to scene 1 |

---

## Reduced motion

With `prefers-reduced-motion: reduce`, no animation runs and the screen shows
scene 6 still, with the chips already joined. It is the same content as the
current banner, so nothing is lost for people who do not see the motion.

## Mistakes to avoid

- Promising a `.pbix` generated directly: Deidara delivers the `.pbip`; the
  `.pbix` comes out of Desktop (rule 7 in `SKILL.md`). The arrow in scene 5
  says so.
- Showing a real number or a real person's name: everything comes from the
  fictional example.
- Putting the explosion before approval: the order (sculpture → "yes" →
  Katsu!) is the message.
- Leaving explanatory text in Portuguese in the English SVG. Only the names
  Deidara generates stay in pt-BR (friendly names, prototype tabs and titles).
