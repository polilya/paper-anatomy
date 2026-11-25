# Journal analysis

`kb.py journals` → OpenAlex (free, no key) for every card with a DOI; cached in `_cache/openalex/`. Then `kb.py build`
writes `notes/Journals.md`, `Journal - <name>` hubs, `tables/journals.csv`, the Excel sheet *Journals* and two plots.

## What is collected
- per journal: papers in the base, high-relevance papers, papers in the last `recent_years`, years, publisher;
- **status**: fully open access (and in DOAJ) / subscription or hybrid / preprint server; APC in USD;
- **rank**: OpenAlex 2-year mean citedness (impact-factor-like) and h-index of the journal; SJR quartile and impact
  factor only from files the user adds to the base folder: `journal_ranks.csv` (`journal, issn, quartile, impact_factor, note`)
  or a Scimago export `scimagojr*.csv` (downloaded by the user from scimagojr.com). Impact factor (Clarivate) is not
  free — never guess it;
- **focus** of the papers in the journal from three sources, always labelled: *auto* (category / object type on the
  card), *folder* (folder of the PDF, renamed by `project.yaml → folder_focus`), *keywords* (`project.yaml → focus_keywords`);
- retracted papers (OpenAlex flag) → warning on the page.

## "Where should I publish?"
1. Start from the shortlist on `Journals.md` (journals with high-relevance or recent papers of the base).
2. Ask the user what the paper is (type: device / material / method / biology / model; main result; audience) and their constraints (OA required? APC budget? deadline?).
3. Match by the focus columns: journals that print papers of the same type and object, recently.
4. Report 3–5 candidates in a table: why it fits ([[ID]] examples of similar papers in that journal), status, APC, citedness, quartile if known.
5. Caveat every time: the base reflects how the user collected papers, not the whole field. Optional check (ask first): an OpenAlex search for the topic keywords to see how many papers each candidate journal published on it in the last 3 years.
