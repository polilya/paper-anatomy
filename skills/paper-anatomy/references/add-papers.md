# Adding papers: brief → triage → deep (with permission)

## Step 1 — find new PDFs
`kb.py ingest`. Duplicates (same SHA, or same DOI as an existing card) do not get a new card: add the path to
`also_at` of the existing card. Supplementary files (SI) go into `supplementary: [{file, sha, note}]` of their paper.
`text=MISSING` → scanned PDF; tell the user (needs OCR) and skip it.

## Step 2 — brief cards (all new papers)
`kb.py stub <sha> …` fills bibliography from OpenAlex. Check it against page 1 (title, year, surname particles like
"della", "van der") — fix if wrong. No DOI / not in OpenAlex → the card is `New_<sha>.yaml`: fill the bibliography from
page 1, then rename the file and `id` to `<Surname><Year>`.
Read only what is needed: `kb.py peek <sha> head` (title, abstract, intro) and, if unclear, `grep:` for methods
keywords. Fill:
- `category` (from `domain.yaml → categories`), `object_type`, `topics` (existing tags first)
- `summary` — one line: what they did and the main result
- `focus.text` — 2–4 sentences: what sets this paper apart (new material? record number? simpler method? new application?); `focus.axes` optional
- `relevance` — high / medium / low against `project.yaml → relevance_criteria`, and `use_for` if obvious
- `lab` — `"<PI surname> (<institution short>)"`, reuse existing strings
- `key_findings` — 2–5 bullets with numbers and pages if they are in the abstract
- `status: brief`

## Step 3 — triage and STOP
`kb.py check`, `kb.py build`, `kb.py triage`. Show the user the table, adding a column **recommendation**
(deep / keep brief) with a reason of 3–6 words (e.g. "same system as ours, has protocols", "review — mine references",
"off-topic"). Give a rough cost: deep analysis reads the whole paper (+ SI); ~10–20 min of work per paper.
Ask: "Which ones should I analyse in depth?" — and wait. Accept "all high", numbers, IDs, or "none".

## Step 4 — deep analysis (only chosen papers) → `status: verified`
Follow `card-schema.md` (all fields) and `deconstruction.md` (object). Order:
1. Read methods, results, figure captions, tables; SI if present (`peek page:N`, `grep:`).
2. `key_findings` with pages; `limitations` (incl. "SI not read" if SI is missing).
3. Object deconstruction: `object`, `elements` (+ `preparation`, detailed only when `key: true`), `functions`, `links`, `interactions`.
   For every link and interaction record the **outcome and its evidence** (what was shown, numbers, conditions) — this is what later makes hubs comparable and syntheses possible (`synthesis.md`).
4. `tests` — every test, with `level`, `type`, `target` (element id / link `a–b` / environment entity).
5. `metrics` — numbers in the unit of `domain.yaml → quantities` (convert; write the original in `condition`).
6. The lens of the category (`design_rules`, `process_window` + `lab_compat`, `review_map`, `transfer`, `bio`).
7. `builds_on` if it continues another paper in the base; loose links → `relations_manual.csv` (`a,b,type,note`).
8. `kb.py check` → fix; NEW-VOCAB → map or ask; `kb.py figures`, `kb.py build`.

Protocols (how exactly something was measured) are a separate permission: `protocols.md`.

## Step 5 — report and propose syntheses
3–6 lines: what was added, what is high relevance and why, warnings left, where to look (`notes/Index.md`,
the paper notes, `knowledge_base.xlsx`).
Then `kb.py candidates`: if hubs touched by this batch qualify (or an existing synthesis now has new papers), propose
at most 3 syntheses as questions tied to the user's project, and stop (`synthesis.md`).
