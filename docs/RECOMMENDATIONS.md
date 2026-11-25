# Recommendations: plan, model, effort, tools, pace

Practical advice from building a 100-paper base. Usage limits change often — check
[Anthropic's current plan pages](https://support.claude.com/en/articles/8324991-about-claude-s-pro-plan-usage) and measure on
your own papers (see *Calibrate* below) instead of trusting any fixed number.

## Which subscription
paper-kb needs **Claude Code** (terminal, desktop app *Code* tab or IDE), which comes with the paid plans.

| Plan | Good for |
|---|---|
| **Pro** | trying paper-kb; a base of a few dozen papers; brief cards for everything + deep analysis of the key papers only, spread over days |

How limits work (as of late 2026): paid plans have a **rolling 5-hour session limit** and a **weekly limit**; both apply,
and Claude Code, the web chat and the desktop app share the same allowance. Max 5x and 20x give roughly 5× and 20× the
Pro allowance per session.

## Which model and effort for which step
Choose the model and the effort level in Claude Code's model menu (`/model` in the terminal; the model picker in the desktop app).

| Step | Model | Effort | Why |
|---|---|---|---|
| Setup (interview, vocabularies) | Opus | high | sets the structure of everything that follows |
| Brief cards for many papers | Sonnet | medium (low is fine for clearly on-topic batches) | reads only page 1–2; volume matters |
| Deep analysis (verified card, object deconstruction) | Opus | high | page-exact numbers, judgement on what is "key" |
| Protocol extraction | Opus | high | details hidden in SI and captions |
| Syntheses, gaps, "is my design new?", where to publish | Opus | high or xhigh | cross-paper reasoning |
| `kb.py build`, `check`, `journals` | any | low | scripts do the work |

## How many papers per session
Rough sizes, measured on 93 papers of the example base: a 10-page paper ≈ 48,000 characters ≈ **12,000 tokens** of
text; a finished deep card ≈ 2,500 tokens.

| Task | What Claude reads | Relative cost |
|---|---|---|
| Brief card | title, abstract, introduction (~1–3k tokens of paper text) | 1× |
| Deep card | whole paper (~12k tokens for 10 pages) + SI, several look-ups, writing the card, check/build | ~10–20× a brief card |
| Protocols for one paper | targeted searches in methods, captions, SI | ~3–5× a brief card |

**Starting point to calibrate, not a promise:** on Pro, plan one batch of brief cards (≈ 20–30 papers) *or* a handful of
deep cards (≈ 3–6 ten-page papers) per 5-hour window; on Max 5x about five times that. Long papers, theses and SI
scale it up.

### Calibrate on your own papers
1. Note your usage (`/usage` in Claude Code, or the usage page of your claude.ai account).
2. Add 5 papers as brief cards → note usage again. Then 1 deep card → note again.
3. Divide your allowance by these two numbers — that is your real pace. Write it into `project.yaml` as a comment for later.

### Save tokens
- **Brief first** (built into the skill) — never deep-read papers you will not use.
- **One deep paper per conversation, or a few**: start a fresh conversation (`/clear`) between deep analyses; a long conversation re-reads its whole history at every step.
- Let the scripts work: `kb.py peek … grep:` reads only the relevant lines; `kb.py stub` fetches bibliography without reading the PDF.
- Put SI next to the paper only when you need its numbers.
- Batch brief cards when your 5-hour window is fresh; leave syntheses for a window of their own.

## Tools around paper-kb
| Tool | Role | Notes |
|---|---|---|
| **Obsidian** (free) | read and navigate the base | Recommended: local Markdown files, links between pages, graph view, search, frontmatter for the Dataview plugin. Open the knowledge base folder as a vault |
| **Zotero** (free) | collect PDFs and references | Point `project.yaml → pdf_dirs` to your Zotero storage folder (e.g. `~/Zotero/storage`) — sub-folders are scanned; use Better BibTeX for citations in your writing |
| **Excel / LibreOffice** | filter and sort | `knowledge_base.xlsx`, one sheet per table |
| **VS Code / any text editor** | edit cards by hand | cards are plain YAML; run `kb.py check` after editing |
| **OCR tool** (Acrobat, `ocrmypdf`) | scanned PDFs | `ingest` flags PDFs without a text layer |

## Folder habits that pay off
- Folders by sub-topic (`reviews/`, `devices/`, `materials/`) — the folder becomes a focus label in the journal analysis.
- SI file named like the paper + `_SI`.
- Your own conclusions go under `📝 My notes` on generated pages, or into `analysis/` — never into `notes/` files above the marker (they are regenerated).
