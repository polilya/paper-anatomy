---
name: paper-anatomy
description: Build and use a cited knowledge base from a researcher's PDF papers on one topic (biomedical engineering, materials/chemistry, biology, mechanics and similar). Use when the user wants to set up a literature database, add or analyse papers ("add these papers", "process my inbox"), deconstruct what papers build or study into parts, functions, links and environment, extract how something was measured, compare reported numbers, find gaps, see which journals publish the topic or choose where to submit, or asks what their papers say about something.
---

# paper-anatomy — literature knowledge base from PDFs

Turns a folder of PDFs into one YAML card per paper (every number with its page), and builds from the cards:
Obsidian notes with hub pages, an Excel workbook, CSV tables, plots of reported numbers and a journal analysis.

Engine: `python3 ${CLAUDE_SKILL_DIR}/scripts/kb.py <command>` (below: `kb.py`). Run it from inside the knowledge
base folder or pass `--kb <dir>`. Dependencies: `pip install pymupdf pyyaml openpyxl matplotlib` (install only after
asking the user, if `kb.py` reports them missing).

## Rules (always)
1. **Never invent.** Every number, parameter and claim on a card comes from the PDF (or its SI) with a page (`p5`, `SI p3`). Not stated → `not reported`. Values read from a plot → `from_figure: true`.
2. **Brief first, deep only with permission.** New papers get brief cards. Then run `kb.py triage`, show the table with your recommendation per paper, and **stop**. Deep analysis and protocol extraction start only for the papers the user names.
3. **Ask before costly or outward steps**: deep analysis of many papers, mining review reference lists, downloading PDFs, installing packages, changing the schema. Say what and how much, then wait.
4. **Vocabulary grows only with consent.** `kb.py check` prints `NEW-VOCAB` for terms missing from `domain.yaml`. Map them to an existing term or ask the user ("add `laser welding` as a thermal link method?") before editing `domain.yaml`.
5. **Cards are the source of truth.** Never hand-edit generated files (`notes/`, `tables/`, `knowledge_base.xlsx`). Text below `📝 My notes` in any note belongs to the user and survives rebuilds.
6. **Language**: cards in English, except `focus.text`, written in `project.yaml → focus_language`. Talk to the user in their language. All plot text in English.
7. **Privacy**: on first use, tell the user once that PDF text is sent to the AI model; unpublished manuscripts or confidential reports should not go into the inbox unless they accept that.
8. **Tables are not conclusions.** Generated hubs compare; conclusions go into syntheses (`analysis/*.md`) that answer one agreed question. After a deep batch run `kb.py candidates` and propose at most 3; write only on the user's answer.
9. Finish every task with `kb.py check` (fix warnings that are yours) and `kb.py build`, then report in a few lines what changed and where to look.

## What the user wants → what to read
| Situation / request | Read first |
|---|---|
| No `project.yaml` + `domain.yaml` found, or "set up a database on X" | `references/setup.md` |
| "Add / process these papers", PDFs in the inbox | `references/add-papers.md` |
| Deep analysis of chosen papers (verified cards) | `references/card-schema.md`, `references/deconstruction.md` |
| "How did they measure X", "write out the method", "build our protocol" | `references/protocols.md` |
| Questions to the base: compare, gaps, "what do my papers say about…" | `references/analysis-recipes.md` |
| "Summarise / review X", a question needing ≥ 4 papers, after a deep batch, or "why are my hub pages only tables?" | `references/synthesis.md` |
| Journals, ranks, "where should I publish" | `references/journals.md` |
| "Show me the parts of the object", "which solution works best for X", graph view is cluttered | `references/anatomy.md` |
| User new to AI tools, or asks how the base works / how to navigate it | `references/explain-to-user.md` |

## Commands
| Command | Does |
|---|---|
| `kb.py init <dir> --domain <template>` | new base; templates: `biomedical-devices`, `materials-chemistry`, `biology`, `mechanics-modelling`, `_template` |
| `kb.py ingest` | finds PDFs without a card (SHA dedup), caches text, finds DOI, flags scans without text |
| `kb.py stub <sha>…` | creates a brief card with bibliography from OpenAlex (title, authors, year, journal, corresponding) |
| `kb.py peek <sha or ID> head / page:N / grep:REGEX / nums` | read the cached text selectively (cheaper than reading the PDF) |
| `kb.py triage` | table of brief cards → ask which to analyse in depth |
| `kb.py candidates` | comparison hubs with enough outcomes and numbers for a written synthesis; flags syntheses with new papers |
| `kb.py figures` | thumbnail of Fig. 1 per paper (`figures/<ID>_manual.png` from the user always wins) |
| `kb.py journals` | fetch journal metadata (status, APC, citedness) → journal analysis |
| `kb.py check` / `build` / `status` / `all` | validate / generate everything / counts / ingest+figures+build |
| `kb.py build --no-plots` | fast rebuild after one paper: keeps the PNGs already drawn |
| `kb.py graph` | colour groups + filter for the Obsidian graph view (parts, solutions, methods, papers); ask before running, it rewrites `.obsidian/graph.json` (backup kept) |

## Session start
Run `kb.py status`. If no base is found and the user wants one → setup. If the user only asks a question, answer
from the cards and notes (`tables/*.csv` are the fastest way to search), citing `[[ID]]` and pages.
