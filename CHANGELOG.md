# Changelog

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
