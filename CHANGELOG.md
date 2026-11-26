# Changelog

## 0.3.0 — 2026-11-25
Start simple, detail where the user's focus is.
- First contact: before the setup interview Claude says what the base can do — cards, taking papers apart, written syntheses — with examples of syntheses from the original base (`explain-to-user.md` → *What you can do*).
- Setup starts from the user's own papers: Claude asks for ~10 original research papers closest to their work, reads them (`kb.py survey`: abstract, figure captions, method headings; terms and units shared across the set), writes a portrait of the set (common object, what is done with it, shared methods and quantities, groups, outliers), then asks focus questions **one at a time**, each with options taken from the papers. The answers go to `project.yaml → scope` (`in_focus` / `context` / `out_of_scope`), `deconstruction.core` and `relevance_criteria`; the seed papers become the first brief cards and calibrate `domain.yaml`.
- Brief and deep analysis respect `scope`: context in one line, out-of-scope not extracted.
- Coarse-first deconstruction: `project.yaml → deconstruction.core` (3–7 main parts, set at setup) and `expand` (parts detailed on the user's request). Claude asks about detail after the first 3–5 deep cards, or when a paper's contribution lies inside a part not yet expanded. `kb.py check` warns about elements finer than the core.

## 0.2.0 — 2026-11-25
Syntheses: from hub tables to written answers.
- New reference `synthesis.md`: three levels of a hub page (list → comparison → synthesis), when to write a synthesis, agreeing the question, a fixed structure (collected · key numbers · conclusions with sources · meaning for the project · gaps), updating.
- `kb.py candidates`: ranks comparison hubs by high-relevance papers and records with outcomes and numbers; flags syntheses with new papers.
- `kb.py build`: syntheses in `analysis/*.md` (frontmatter `type: synthesis`, `hubs`, `papers`) appear in `Index` and as a banner on their hubs, with "N new paper(s) since"; qualifying hubs without one get a hint banner.
- Deep analysis now asks for the outcome **and its evidence** on every link and interaction; after a deep batch up to three syntheses are proposed.
- `project.yaml → synthesis.min_papers` (default 4).

## 0.1.0 — 2026-11-25
First version, generalised from an MSc literature database (soft bioelectronics, TU/e).
- Engine `kb.py`: init, ingest (SHA dedup, DOI, scan detection), stub (bibliography from OpenAlex), peek, triage, figures, check (incl. NEW-VOCAB), build, journals, status.
- Card schema: brief / verified, object deconstruction (elements, functions, links, interactions, key preparation), tests, metrics, protocols, lenses.
- Generated: Obsidian notes and hubs, mermaid structure graphs, function × solution table, plots per quantity and property maps, journal analysis with shortlist, Excel workbook, CSV tables.
- Field templates: biomedical-devices, materials-chemistry, biology, mechanics-modelling, _template.
- Docs: README, QUICKSTART for newcomers, HOW-IT-WORKS, FAQ.

Planned: demo knowledge base on open-access papers, screenshots/GIF, evals, OCR hint, design-rule plots from `points`.
