# Script: `deidara-fluxo.svg`

[Português](deidara-fluxo.md) | **English**

| | |
|---|---|
| Files | `assets/deidara-fluxo.svg` (pt-BR) and `assets/deidara-fluxo-en.svg` |
| Where | `README.md` / `README.en.md`, "How it works inside" section, before the parts table |
| Canvas | 1280 × 640, background `#0B1220`, 32 px grid in `#1E2A44` |
| Length | 36 s loop, 5 steps |
| `aria-label` / `alt` (pt) | Como o Deidara funciona: receita, catálogo, esboço, validar, protótipo, aceite e gerar |
| `aria-label` / `alt` (en) | How Deidara works: recipe, catalog, draft, validate, prototype, approval and generate |
| Vegapunk counterpart | `vegapunk-sonar.svg` (31 s, 4 steps, progress strip, one caption at a time) |

## The idea in one sentence

Vegapunk's sonar shows the search hopping from hit to hit and leaving behind
what does not fit. Deidara's flow shows **the clay taking shape**: in the
centre, a lump of clay (the `argila.json`) gains one piece at a time, and only
what has a known origin sticks. What was guessed hits it and falls, like
Vegapunk's grey echo. Then the clay becomes a sculpture (the prototype), gets
the "yes" and explodes into the project.

## Timeline

Comment at the top of the `<style>` in both SVGs (kept in Portuguese in both
files, as in Vegapunk):

```css
/* Linha do tempo: 36 s. 1 Você pede 0–4.5 · 2 A estrutura volta 4.5–11 · 3 A argila toma forma 11–21 · 4 O gestor decide 21–28 · 5 Katsu! 28–36 */
```

| Step | Time | Deidara stages (the 7 boxes of the current flow) | Commands | Teaches |
|---|---|---|---|---|
| 1 · You ask | 0–4.5 s | (Understand) | `novo` | the request is in plain language, with KPIs, breakdowns and where each piece of data lives |
| 2 · The structure comes back | 4.5–11 s | 1 Recipe · 2 Catalog | `receita`, `catalogar` | Deidara connects to nothing; only structure comes back |
| 3 · The clay takes shape | 11–21 s | 3 Draft · 4 Validate | `esbocar`, `padroes`, `confirmar`, `validar` | names only from the catalog, functions only from the dictionary, links only with proof or a person |
| 4 · The manager decides | 21–28 s | 5 Prototype · 6 Approval | `prototipar`, `aprovar` | fictional prototype, explicit approval, and the approval locks the spec |
| 5 · Katsu! | 28–36 s | 7 Katsu! | `gerar` | what comes out, and what is still a person's job |

## Fixed elements (all the time)

- **Progress strip at the top** (y 24–60), like the sonar's: five numbered
  labels side by side and a 4 px segment under each. Only the current step's
  label shows as large text in the middle of the strip (it swaps with an 8 px
  rise); finished steps' segments turn light (`#F1F5F9`), pending ones stay
  `#334155`.
- **Caption at the bottom** (y 590), one at a time, Inter 20 px, `#CBD5E1`.
- **The clay in the centre** (x 640, y 330): from step 1 on, a rounded amber
  lump with an irregular edge (a `path` with soft corners), labelled
  `argila.json` in JetBrains Mono. It changes shape at each step.

**Fixed strip text.**

| # | pt-BR | en |
|---|---|---|
| 1 | 1 · Você pede | 1 · You ask |
| 2 | 2 · A estrutura volta | 2 · The structure comes back |
| 3 | 3 · A argila toma forma | 3 · The clay takes shape |
| 4 | 4 · O gestor decide | 4 · The manager decides |
| 5 | 5 · Katsu! | 5 · Katsu! |

---

## Step 1 · You ask (0–4.5 s)

**Teaches.** It starts with a conversation, not a form: who it is for, which
KPIs, which breakdowns, where each piece of data lives. Deidara picks out what
matters in the request.

**What appears.** A wide speech bubble in the centre with the request.
Keywords highlighted one by one. Under the bubble, six small tags are born
from the words. At the end of the step, the tags fly to the centre and become
the clay.

**On-screen text.**

| Element | pt-BR | en |
|---|---|---|
| request | Desligamentos por **motivo** e **cargo**, com a **meta de turnover** por **empresa**. O ERP é SQL Server; a meta vem de uma planilha do RH. | Terminations by **reason** and **role**, with the **turnover target** by **company**. The ERP is SQL Server; the target comes from an HR spreadsheet. |
| tags | indicador · corte · corte · meta · fonte: SQL Server · fonte: Excel | KPI · breakdown · breakdown · target · source: SQL Server · source: Excel |
| clay (born) | `argila.json` | `argila.json` |
| caption (1.6–4.0 s) | O Deidara lê o pedido e separa o que importa. | Deidara reads the request and picks out what matters. |

**Motion.**

| Mark | What happens |
|---|---|
| 0.0–0.35 s | the bubble rises 10 px into view |
| 0.4–1.4 s | the bold words get a `rgba(241,245,249,.16)` background, 0.2 s apart |
| 1.0–1.6 s | the six tags appear with scale 0.7 → 1, 0.1 s apart, coloured by type (KPI and target in amber, breakdowns in orange, sources in blue) |
| 1.6 s | the caption enters |
| 4.0–4.5 s | the bubble fades; the tags shrink to 0.6 and fly to the centre (`cubic-bezier(.5,0,.7,1)`); where they land, the clay is born with scale 0.6 → 1.12 → 1 |

---

## Step 2 · The structure comes back (4.5–11 s)

**Teaches.** The recipe goes to the source, someone with access runs it, and
only the structure comes back. Real data stays on the other side. Each source
becomes a catalog.

**What appears.**

- On the left, the blue "AT YOUR SOURCE" band (x 0–240), with the dashed wall
  on its right edge, and two icons: database (ERP) and spreadsheet (Targets).
  It is the same band as in the current flow, now vertical.
- The clay sends two recipes to the left: small cards with the file name and a
  language tag.
- Back come tokens with table and column names. They do not go to the clay
  yet: they form two **catalogs** (cards with a blue header) to the left of
  the clay, one per source.
- A data token (a record row) tries to come back with them and is stopped by
  the wall: it goes grey and falls. It is this step's grey echo.

**On-screen text.**

| Element | pt-BR | en |
|---|---|---|
| band | NA SUA FONTE | AT YOUR SOURCE |
| under the band | o Deidara não se conecta a nada | Deidara connects to nothing |
| recipes | `receita_sql.sql` · SQL / `receita_m.pq` · M | same |
| who runs it | quem tem acesso roda e cola o resultado | someone with access runs it and pastes the result |
| catalog 1 | `catalogos/erp.json` · F_DESLIGAMENTO · F_FUNCIONARIO · F_CARGO · F_MOTIVO_DESLIGAMENTO · N_EMPRESA | same |
| catalog 2 | `catalogos/metas.json` · Metas | same |
| blocked token | 1043 · Ana S. · 12/03/2024 | same |
| blocked label | dado não sai da fonte | data never leaves the source |
| caption A (5.5–7.8 s) | A receita vai até onde os dados estão. | The recipe goes where the data lives. |
| caption B (8.0–10.6 s) | Só a estrutura volta: tabelas, colunas, tipos e chaves. | Only the structure comes back: tables, columns, types and keys. |

**Motion.**

| Mark | What happens |
|---|---|
| 4.5–5.1 s | the band slides in from the left; the wall draws top to bottom |
| 5.1–6.3 s | the two recipes leave the clay and slide to the icons, one after the other (0.3 s), and are "swallowed" (scale 1 → 0) |
| 6.0 s | each icon pulses once; "someone with access runs it and pastes the result" appears under the band and stays until 10.6 s |
| 6.8–8.6 s | the tokens cross the wall to the right, 0.25 s apart, with a blue trail, and stack into the two catalogs |
| 7.4 s | the data token leaves with them, hits the wall, bounces back 6 px, loses its colour and drops 30 px; the label appears and fades at 9.4 s |
| 8.6 s | the catalog headers light up (`#60A5FA` border with a 4 px glow) |
| 10.6–11.0 s | the source band dims to 35% and stays that way to the end (the source is still there, but the scene moves on) |

---

## Step 3 · The clay takes shape (11–21 s)

**Teaches.** The draft builds itself from the request and the catalogs, but
everything that enters the clay has an origin: a name from the catalog, a
function from the dictionary, a measure from a pattern, a link that is proven
or confirmed by a person. Anything without an origin is refused, and
`validar` says what exists instead.

**What appears.** The central step, Deidara's "sonar".

- The clay grows and the pieces stick around it, like nodes on a map: tables
  (facts in amber, dimensions in light orange) and the calendar.
- Lines link the tables. The ERP ones are solid and green, with a "database
  FK" badge. The `fMetas → dEmpresa` link (across sources) arrives dashed and
  amber, labelled "TO CONFIRM"; then a person confirms it and it turns solid
  and green.
- From a corner, the `turnover` pattern's measure chain enters in a queue and
  sticks under the clay: Qtd Desligamento → Headcount → HC Médio → Turnover.
- Two intruders try to stick and fall as a grey echo: a guessed column name and
  a DAX function that does not exist. Beside each one, the fix that `validar`
  suggests.
- Final badge: "validate: 0 errors".

**On-screen text.**

| Element | pt-BR | en |
|---|---|---|
| tables | fDesligamento · dMotivoDesligamento · dCargo · dFuncionario · dEmpresa · fMetas · Calendário | same (they are generated names) |
| ERP link badge | FK do banco | database FK |
| cross-source link, before | fMetas → dEmpresa · A CONFIRMAR | fMetas → dEmpresa · TO CONFIRM |
| cross-source link, after | confirmada por Ana (RH) | confirmed by Ana (HR) |
| measure chain | Qtd Desligamento → Headcount (estoque na data) → HC Médio → Turnover | Qtd Desligamento → Headcount (stock at date) → HC Médio → Turnover |
| chain label | padrão: turnover | pattern: turnover |
| intruder 1 | `dFuncionario[DATA_DEMISSAO]` | same |
| fix 1 | não está no catálogo · existe: DATADESLIGAMENTO em F_DESLIGAMENTO | not in the catalog · exists: DATADESLIGAMENTO in F_DESLIGAMENTO |
| intruder 2 | `CALCULA_TURNOVER()` | same |
| fix 2 | não está no dicionário · use DIVIDE com o padrão turnover | not in the dictionary · use DIVIDE with the turnover pattern |
| final badge | validar: 0 erros | validate: 0 errors |
| caption A (11.6–15.8 s) | Nome só do catálogo. Função só do dicionário. | Names only from the catalog. Functions only from the dictionary. |
| caption B (16.0–20.6 s) | Ligação só com prova, ou confirmada por quem conhece o dado. | Links only with proof, or confirmed by someone who knows the data. |

**Motion.**

| Mark | What happens |
|---|---|
| 11.0 s | the catalogs break into tokens that go to the clay; the clay grows (scale 1 → 1.3) and changes shape (the `path` goes from a lump to an oval with bumps) |
| 11.6 s | first pulse: a light ring leaves the clay and expands (scale 0.02 → 1, opacity 0.9 → 0, 1.4 s, linear), like Vegapunk's sonar |
| 12.2–13.8 s | the seven tables light up around it, one every 0.25 s, each with scale 0.6 → 1.12 → 1 |
| 13.0 s | intruder 1 enters from the right, touches the clay, shakes, goes grey and drops 30 px; the fix appears beside it and stays until 15.6 s |
| 13.8–14.8 s | the ERP links draw from the many side to the one side (`stroke-dashoffset`), 0.2 s apart; the "database FK" badge appears on the first |
| 14.8 s | second pulse, leaving from `dEmpresa` (the latest hit, as in the sonar) |
| 15.2 s | the `fMetas → dEmpresa` link draws dashed in amber with "TO CONFIRM" |
| 16.4 s | a small person card ("Ana (HR)") touches the link; it turns solid and green, and the label changes to "confirmed by Ana (HR)" |
| 17.2–18.6 s | the four measures queue in from the left and stick under the clay, joined by thin arrows, 0.35 s apart |
| 18.2 s | intruder 2 tries to stick to the measure queue and falls like the first; the fix stays until 20.2 s |
| 19.4 s | the "validate: 0 errors" badge pops on the clay (scale 0.6 → 1.1 → 1, green) |
| 20.6–21.0 s | the grey echoes fade; tables and links shrink into the clay |

---

## Step 4 · The manager decides (21–28 s)

**Teaches.** The clay becomes a sculpture: a prototype with fictional
numbers, an explanation on each visual and a tab to approve. Approval belongs
to a person and is recorded with the code of the clay and the catalogs.
Changed afterwards? New prototype, new "yes".

**What appears.**

- The clay turns into a miniature report page (in the `faixa-de-kpis`
  template), 420 × 240, with the "fictional numbers" strip at the top.
- An ⓘ opens and closes on a card.
- The "Para aprovar" tab with three ✓ and the APPROVED stamp.
- A padlock closes over the miniature with the approval code.
- A dashed loop-back arrow leaves the padlock and returns to the clay, with
  the warning of what happens if anything changes. It is the same loop-back
  arrow as in the current flow.

**On-screen text.**

| Element | pt-BR | en |
|---|---|---|
| file | `argila.prototipo.html` | same |
| strip | números fictícios | fictional numbers |
| ⓘ tooltip | o que o número significa | what the number means |
| tab | Para aprovar | Para aprovar (real tab, in pt-BR) |
| checklist | ✓ indicadores · ✓ cortes · ✓ pendências | ✓ KPIs · ✓ breakdowns · ✓ open items |
| stamp | APROVADO | APPROVED |
| command | `aprovar --por "Gestor de RH"` | same |
| code | aceite 7F3A·C21E | approval 7F3A·C21E |
| loop-back arrow | mudou depois do aceite? novo protótipo, novo "sim" | changed after approval? new prototype, new "yes" |
| caption (22.0–27.6 s) | O gestor aprova o que vai ver, antes de existir. | The manager approves what they will see, before it exists. |

**Motion.**

| Mark | What happens |
|---|---|
| 21.0–21.8 s | the clay flattens and splits into rectangles that become the page (rail, title, three cards, bars); the numbers count from 0 |
| 22.0 s | the caption enters |
| 22.8 s | the ⓘ opens (scale 0.92 → 1), stays 1.2 s and closes |
| 24.2 s | the page slides left and the "Para aprovar" tab appears |
| 24.6–25.5 s | the three green ✓, 0.3 s apart |
| 25.8 s | the APPROVED stamp drops (`stamp`: −10° rotation, scale 1.6 → 1) and the command appears below in JetBrains Mono |
| 26.3 s | the padlock closes (the shackle drops 6 px) and the code appears |
| 26.8 s | the loop-back arrow draws from the padlock to the clay, dashed in grey, with the warning; it stays until 27.6 s |
| 27.6–28.0 s | the arrow and the caption fade; the miniature returns to the centre and shrinks |

---

## Step 5 · Katsu! (28–36 s)

**Teaches.** Only now does the project exist: `.pbip` with TMDL and PBIR, the
sources' SQL and the sign-off documentation. And what is still a person's job
is written down, like the gap in Vegapunk's sonar.

**What appears.**

- The miniature turns into the "Katsu!" burst and explodes.
- Out of the explosion come three delivery cards side by side (like the two
  final cards in the sonar), each with a green badge.
- Below, an amber box with what is left to do.
- Last, the closing line.

**On-screen text.**

| Element | pt-BR | en |
|---|---|---|
| explosion | Katsu! | Katsu! |
| command | `gerar argila.json -o C:/paineis/turnover` | same |
| card 1, title | Projeto Power BI | Power BI project |
| card 1, lines | `Painel.pbip` · TMDL + PBIR · abre no Desktop, salva como .pbix | `Painel.pbip` · TMDL + PBIR · opens in Desktop, saves as .pbix |
| card 1, badge | 24 de 24 JSON válidos | 24 of 24 JSON valid |
| card 2, title | SQL das fontes | Source SQL |
| card 2, lines | `01_views.sql` · `02_conferencia.sql` · `03_qualidade.sql` | same |
| card 2, badge | qualidade: tudo tem que dar zero | quality: everything must be zero |
| card 3, title | Para homologar | For sign-off |
| card 3, lines | `HOMOLOGACAO.md` · `LEIA-ME.md` · `dicionario_indicadores.md` | same |
| card 3, badge | quem faz o quê | who does what |
| what is left | Falta você: depois da primeira atualização, conferir 5 números com a fonte. | Still on you: after the first refresh, check 5 numbers against the source. |
| closing line | Molda com o que existe. Mostra antes. Explode depois do "sim". | Shapes with what exists. Shows first. Explodes after the "yes". |
| caption (29.2–33.0 s) | O projeto completo, só depois do aceite. | The complete project, only after approval. |

The "Still on you" box repeats the README line ("after the first refresh,
check these five numbers against the source") and sits where Vegapunk's sonar
shows "Falta você preencher".

**Motion.**

| Mark | What happens |
|---|---|
| 28.0–28.6 s | the miniature turns into the eight-point burst (scale 0.2 → 1, "Katsu!" in Poppins 800); the command appears below |
| 28.6–29.2 s | the burst swells (1 → 1.25) and explodes into 16 particles; the amber background glow doubles for 0.4 s |
| 29.2 s | the caption enters |
| 29.4–30.4 s | the three cards rise 40 px out of the particles, 0.3 s apart |
| 30.6–31.5 s | the three green badges pop (scale 0.6 → 1.1 → 1), 0.3 s apart |
| 32.0 s | the "Still on you" box rises into view |
| 33.0 s | the caption leaves; the closing line takes its place |
| 33.0–35.5 s | every segment of the progress strip is light |
| 35.5–36.0 s | everything fades (opacity 1 → 0), source band included, and the loop goes back to step 1 |

---

## Reduced motion

With `prefers-reduced-motion: reduce`, the screen shows a still frame that
sums up the five steps: the progress strip with all five segments light, the
"AT YOUR SOURCE" band on the left, the clay with the tables and links (the
`fMetas → dEmpresa` one already confirmed), the APPROVED stamp and the three
delivery cards. It is the current static flow's content, rearranged; nothing
is lost.

## Mistakes to avoid

- Showing Deidara "connecting to" or "reading" the database: the arrow to the
  source is always a recipe carried by a person.
- Showing the cross-source link turning green by itself: it only changes when
  the person arrives.
- Writing the proof by hand: if step 3 shows a proof instead of the
  confirmation, it comes from a pasted result (`provar --de resultado.txt`),
  with percentages, never rows.
- Treating turnover as a headcount of records: the measure chain shows
  Headcount as stock at date and HC Médio in the denominator (rule 4 in
  `SKILL.md`).
- Changing the order: Katsu! never before APPROVED.
