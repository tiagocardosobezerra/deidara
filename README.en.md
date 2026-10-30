# Deidara

[Português](README.md) | **English**

**Describe the report in plain language. Get a prototype for the manager to approve and, after the "yes", the complete Power BI project.**

![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![No dependencies](https://img.shields.io/badge/dependencies-none-2ea44f?style=flat-square)
![Power BI .pbip](https://img.shields.io/badge/Power%20BI-.pbip%20(TMDL%20%2B%20PBIR)-F2C811?style=flat-square&logo=powerbi&logoColor=black)
![Tests](https://img.shields.io/badge/tests-146%20passing-2ea44f?style=flat-square)
![MIT](https://img.shields.io/badge/license-MIT-blue?style=flat-square)

<img width="100%" alt="Deidara: from request to Power BI report, with an approved prototype before the project" src="assets/deidara-banner-en-animado.svg" />

Deidara is a Claude Code skill for KPI and reporting teams. It turns a request ("turnover by reason and role, with a target per company") into a real Power BI report without connecting to any source and without guessing any name: someone with access to the data runs a **recipe** (a SQL, DAX or Power Query query), pastes the result, and only the **structure** comes back. The manager approves a prototype with fictional numbers before anything goes to production.

> Deidara speaks Brazilian Portuguese: commands, messages, the prototype and the generated documentation are in pt-BR (`dd/MM/yyyy`, `1.234.567,89`). The command names below are the real ones.

## What it does for you

* **Discovers the structure of any source, without access to it.** SQL Server, an existing Power BI model, Excel, SharePoint, CSV or an API: the recipe returns tables, columns, types, keys and relationships. Not a single data row.
* **Drafts the first version on its own.** From the request, it picks the tables, separates facts from dimensions, creates the calendar, one chart per requested breakdown and friendly column names.
* **Suggests relationships, never creates them on its own.** When tables are not related, it suggests a link with the evidence (name, key, type, synonyms) and measures the candidate at the source with a proof recipe that only returns percentages. A person confirms it.
* **Never guesses names or functions.** Every name comes from the source catalog; every DAX function, from the dictionary. `validar` rejects anything else and says what exists: similar measures, catalog columns missing from the model and the exact snippet to add.
* **Understands real KPIs.** Headcount is a stock at a date, not a count of records; turnover uses the average headcount; targets have polarity and color. It warns when a slicer does not filter a measure or shows the current value instead of the historical one.
* **Eleven layout templates from award-winning dashboards, with their formatting.** Page rail, KPI strip or column, scrolling sections, clickable KPIs, a long story page, executive, central map, root cause, side table and teams: Deidara draws each page's background (panels, title, navigation) and places native visuals on top, in the prototype and in the `.pbip` (`deidara.py modelos`).
* **Designs with intent.** Layouts that start from the decision, color with meaning and checked contrast, native visual techniques (`deidara.py visuais`) and the bar-versus-target inside the table, generated as an SVG measure that follows every rule.
* **Shows before it builds.** The HTML prototype has consistent fictional numbers, an ⓘ on every visual explaining the number and a "Para aprovar" (for approval) tab with a checklist, comments and an approval summary with a code.
* **Delivers ready for sign-off.** A `.pbip` project (opens in Power BI Desktop, which saves it as `.pbix`), SQL views, total reconciliation (including headcount at each month end), data quality checks, a sign-off sheet and a KPI dictionary.
* **Keeps what the team approves on the Memory Card.** Each report and KPI is saved with a version, the reason for each change and the official definition, in a team repository.

## What it looks like

> **You:** I want a report of terminations by reason and role, with the turnover target per company
>
> **Claude (with Deidara):** creates the report folder and sends one recipe per source. With the results pasted, it drafts the model, asks only what changes the report ("does the target come from the HR spreadsheet, using the same company code as the ERP?") and shows the prototype: "Do you approve this prototype so I can generate the Power BI project?"
>
> **Manager:** approved.
>
> **Claude:** generates the project, a README with who does what and the sign-off sheet. "After the first refresh, check these five numbers against the source."

No "I think the column is called HIRE_DATE". If the name did not come from the catalog, it does not go into the report.

## Results

Measured on the repository example (a fictional ERP on SQL Server and a targets spreadsheet in Excel).

| What | Result |
|---|---|
| Automated tests | **117 passing** |
| JSON files of the generated project checked against Microsoft's official schemas | **24 of 24** |
| Tutorial, from scratch to project, run command by command | **15 minutes** |
| Functions in the dictionary (DAX / Power Query) | **462 / 667** |
| Ready-made KPI patterns (rate, stock, year-to-date, full turnover...) | **17** |
| Cataloged visual techniques (target in a table, ranking, root cause, status...) | **46**: 41 generated ready to use (3 with an AppSource visual) and 5 custom visuals described (Chord, Word Cloud, Violin Plot, Gantt, Play Axis) |
| Layout templates, from prototype to `.pbip` | **11** |
| Data rows returned by the recipes | **0** |

## Get started in 3 steps

You need Python 3.8+ (standard library only, nothing to install) and Power BI Desktop to open the generated project. Commands run **from the skill folder**; on Windows, use `python` (or `py`) instead of `python3` if that is your setup.

### 1. Install

```bash
git clone https://github.com/tiagocardosobezerra/deidara.git ~/.claude/skills/deidara
```

```powershell
git clone https://github.com/tiagocardosobezerra/deidara.git "$env:USERPROFILE\.claude\skills\deidara"
```

On claude.ai, upload the skill zip (see [COMO-INSTALAR.md](COMO-INSTALAR.md)).

### 2. Ask for the report

Open Claude Code and describe the report: who it is for, which decision it supports, which KPIs and where each piece of data comes from. Claude creates the report folder and hands over one recipe per source. Each recipe's header explains how to run it and what to copy.

### 3. Approve and generate

After you paste the results, Claude drafts, validates and shows the prototype. With the manager's "yes", it generates the `.pbip` project. Open it in Power BI Desktop, refresh, fill in `HOMOLOGACAO.md` (the sign-off sheet) and save as `.pbix`.

Want to see everything from the inside first? Take the [15-minute tutorial](referencias/tutorial.md) (in Portuguese) with the repository example.

## Going further

### The commands

Day to day, Claude runs the commands. They also work straight from the terminal:

```bash
python3 deidara.py novo meu --projeto "Turnover RH"            # folder with recipes and a checklist
python3 deidara.py catalogar --de meu/colado/erp.txt --fonte erp -o meu/catalogos/erp.json
python3 deidara.py esbocar meu --pedido "desligamentos por motivo e cargo"
python3 deidara.py confirmar meu/argila.json --ligacao "fMetas->dEmpresa" --por "Ana (RH)"
python3 deidara.py padroes turnover
python3 deidara.py validar meu/argila.json
python3 deidara.py prototipar meu/argila.json
python3 deidara.py aprovar meu/argila.json --por "Gestor de RH"
python3 deidara.py gerar meu/argila.json -o C:/paineis/turnover
python3 deidara.py gerar meu/argila.json -o C:/paineis/demo --demo   # fictional data: opens and calculates with no database
python3 deidara.py situacao meu/argila.json                     # where am I and what's next
```

With no arguments, `python3 deidara.py` shows the full walkthrough.

### What gets generated

| Output | What for |
|---|---|
| `Report.pbip` + `.SemanticModel` (TMDL) + `.Report` (PBIR) | opens in Power BI Desktop, which saves it as `.pbix` |
| `sql/<source>/01_views.sql` | a view layer (`bi.vw_*`) for SQL Server sources |
| `sql/<source>/02_conferencia.sql` | each KPI's total in the database (overall, per year and stock per month end) |
| `sql/<source>/03_qualidade.sql` | duplicate keys, orphans and dates outside the calendar (all must be zero) |
| `HOMOLOGACAO.md` | what to check before publishing, with where to read each number in the report |
| `LEIA-ME.md` | who does what (DBA, analyst, KPI owner) and what to do if something goes wrong |
| `docs/dicionario_indicadores.md` | definition, formula, origin, proof of each relationship and change history |

Sources other than SQL Server (Excel, SharePoint, APIs...) come in through **the same Power Query query** the team already uses: Deidara only adds selection, names, types and keys.

### Why .pbip and not .pbix directly

`.pbix` is a closed binary: the model is stored in an internal format only Power BI Desktop writes. `.pbip` is Microsoft's official text format for the same content. Desktop opens it and saves it as `.pbix` in one click, and the `.pbip` can be versioned in git. Details in [`referencias/powerbi.md`](referencias/powerbi.md).

### Function dictionary and KPI patterns

462 DAX and 667 Power Query functions, with category, signature and a link to the official documentation; the most used ones with a description and KPI usage in Portuguese (`deidara.py funcoes buscar "ano anterior"`). Patterns say how and where to build each KPI: measure, visual calculation, calculation group, Power Query or SQL view (`deidara.py padroes`). Guide in [`referencias/metricas.md`](referencias/metricas.md).

### Design and visuals

The principles in [`referencias/design.md`](referencias/design.md): start from the decision, one page per question, color only with meaning (and never as the only cue), contrast checked by `validar`. Native visual techniques (button slicer as a segmented control, clickable KPI cards, top and bottom in one table, Pareto, decomposition tree, fishbone, jitter plot, impact ranking, star and progress map markers, 3D map columns, guided tour, period slicer via calculation group, drillthrough, tooltip page) are in `deidara.py visuais`. Measures that draw inside a table follow [`referencias/svg.md`](referencias/svg.md); Deidara generates the bar-versus-target ready to use (`"tipo": "svg_barra_meta"`).

### Layout templates

Put `"modelo": "faixa-de-kpis"` in `argila.json` (it is what `esbocar` writes) and the report gets the structure of a real dashboard: a drawn page background with panels, the page title and question, page navigation and transparent native visuals on top. There are eleven, taken from the structure and formatting of Power BI Design Files dashboards: `faixa-de-kpis`, `coluna-de-kpis`, `secoes-com-rolagem`, `trilho-escuro`, `kpis-clicaveis`, `historia-longa`, `executivo`, `mapa-central`, `causa-raiz`, `tabela-lateral` and `equipes`. They come with the button slicer, the new card, decomposition tree, scatter, area, map, ranking measures (position, Pareto, top and bottom) and status, arrow and badge SVGs, plus the palettes of his themes. Guide in [`referencias/modelos.md`](referencias/modelos.md).

### Memory Card: the team's reports

The card is a private team repository (`memory-card`), and Deidara uses its `deidara/` section. Before creating a KPI, search (`memory-card buscar`); after approval, save (`memory-card enviar`, with a preview and only after your "yes"). A definition marked **official** cannot be rewritten by a report, and `memory-card conferir` warns when a source changes. Source structure never goes to the card. Full guide in [`referencias/memory-card.md`](referencias/memory-card.md).

## How it works inside

<img width="100%" alt="How Deidara works: recipe, catalog, draft, validate, prototype, approval and generate" src="assets/deidara-fluxo-en-animado.svg" />

| Piece | What it does |
|---|---|
| **Recipes** | the SQL, DAX and Power Query queries a person runs where the data lives (`deidara.py receita`) |
| **Catalog** | each source's structure, from the pasted result (`catalogar`) |
| **Discovery** | finds the tables for a request, suggests relationships with evidence and reads the proof (`buscar`, `relacionar`, `provar`) |
| **Argila** (clay) | the report specification (`argila.json`): model, measures, targets, pages and visuals, checked against the catalog and the dictionary |
| **Draft** | the first `argila.json`, from the request (`esbocar`) |
| **Sculpture** | the HTML prototype for the manager to approve (`prototipar`, `aprovar`) |
| **Katsu!** | generation of the Power BI project, SQL and documentation (`gerar`) |
| **Memory Card** | saves, versions, searches and checks the team's reports and KPIs |

To check the installation at any time:

```bash
python3 deidara.py status
python3 -m unittest discover -s testes
```

## Repository structure

```
deidara/
├── SKILL.md               # What Claude reads: rules, flow and how to lead
├── README.md              # README in Portuguese
├── README.en.md           # This file
├── COMO-INSTALAR.md       # Install, check and update
├── AVISO.md               # Third-party data and privacy
├── LICENCAS-DE-TERCEIROS.md  # Power BI Design Files MIT license and credits
├── LICENSE                # MIT License
├── deidara.py             # Deidara himself: entry point that calls each technique (all commands)
├── kibaku_nendo/          # Explosive clay: the engine that reads and validates the spec, and the flow commands
├── tecnicas/              # Deidara's techniques, one per step of the flow:
│   ├── luneta/            #   scope eye: recipes, catalog, discovery and proof (sees the source without touching it)
│   ├── te_no_kuchi.py     #   hand mouths: drafts argila.json from the request
│   ├── c1/                #   small figures: the HTML prototype and the guided tour
│   ├── bunshin/           #   clay clone: fictitious numbers and demo project
│   ├── katsu.py           #   "Katsu!": the sign-off and the approved snapshot
│   ├── c3/                #   the big work: TMDL, PBIR, SQL views and documentation
│   ├── arte/              #   "art is an explosion": layout models and visual placement
│   ├── sasori.py          #   eternal art: function dictionary and checked patterns
│   └── memory_card.py     #   the team's memory card
├── dicionario/            # DAX and Power Query functions, KPI patterns, visual techniques and synonyms
├── referencias/           # Guides: flow, sources, discovery, argila.json, metrics, design, SVG, Memory Card, Power BI and tutorial
├── exemplos/aurora/       # Complete fictional example, from pasted result to generated project
├── ferramentas/           # .pbip validator, skill packager and free-text topic grouper
├── assets/                # README images
└── testes/                # Test suite
```

## Credits

**Creator:** Tiago Cardoso Bezerra | [tiagocardosobezerra](https://github.com/tiagocardosobezerra)

Named after Deidara, the Naruto artist who shapes clay and makes it explode: here, the clay is the report specification, the sculpture is the prototype and the explosion is the complete project, only after the "yes".

Function names, categories, signatures and links in the dictionary come from Microsoft's official reference (Microsoft Learn); the Portuguese descriptions and usage notes were written for Deidara.

## Acknowledgements

* My wife **Júlia** and my children **Arthur** and **Dante**, the safe harbor where I find peace, inspiration and the lightness I need every day.
* **Bruna Cardoso Bezerra** | [brunacbezerra](https://github.com/brunacbezerra), for teaching me everything I know about Claude Code.
* **Sajjad Ahmadi** | [Dashboard-Design](https://github.com/Dashboard-Design), for sharing in [Power BI Design Files](https://github.com/Dashboard-Design/Power-BI-Design-Files) the dashboards, visual techniques and design and DAX SVG practices that became Deidara's layout templates, techniques, palettes, root cause visuals and tour (MIT license; see [`LICENCAS-DE-TERCEIROS.md`](LICENCAS-DE-TERCEIROS.md)).
* **You**, for using Deidara!

## Third-party data notice

This repository ships only the engine and a fictional example: no metadata from any real system. By cataloging your sources, you confirm you have legitimate access to them and agree to keep catalogs and approvals out of public repositories. Details in [`AVISO.md`](AVISO.md).

## License

MIT License, see [LICENSE](LICENSE) for details.

---

<p align="center"><strong>Deidara</strong>, sculpture first. then, the explosion.</p>
