# Syntheses — from hub tables to written answers

`kb.py build` generates hundreds of hub pages. They are tables: they show **what** the papers report, side by side,
but they do not say **what follows**. That is the job of a synthesis: a short written answer to one question,
based on one or more hubs and saved in `analysis/`. Without syntheses a large base is a pile of dry tables.

## Three levels of a hub page
| level | hubs | what the cards give it | what the page can be |
|---|---|---|---|
| 1. list | Topic, Category, Lab, Journal, Object | only a tag | a list of papers with one-line summaries |
| 2. comparison | Element, Link, Environment, Function, Prep, Quantity, Protocols, Design rule | records with outcome (works / partial / fails), evidence, numbers, conditions, pages | a comparison table; a synthesis is possible |
| 3. synthesis | any comparison hub with enough evidence | written in `analysis/` from level 2 | an answer: what holds, under which conditions, what it means for the user, what is missing |

A hub stays a list when the cards only *mention* the thing (a material tag). It becomes comparable when deep cards
record, for each occurrence, **whether it worked, the evidence, the numbers and the conditions**. So the quality
of syntheses is decided during deep analysis: fill `links.outcome` + `tested`, `elements.props` with conditions,
`interactions.result`, `metrics.condition`. An `outcome: works` with no evidence is weak; say what was shown.

A list hub (e.g. a material tag) can still get a synthesis, but only through a question that turns it into a
comparison ("how is this material bonded to its neighbours, and does it hold in water?" → Link and Element hubs).

## When to write one
- **The user asks** a question that needs several papers ("what do my papers say about X", "which Y works best",
  "summarise Z"). Write a synthesis, not a chat answer, if it needs ≥ 4 papers or the user will come back to it.
- **After a batch of deep analysis**: run `kb.py candidates`. It ranks comparison hubs by papers of high relevance
  and by records with outcomes and numbers, and marks hubs whose synthesis has new papers since. Propose **at most 3**,
  phrased as questions tied to `project.yaml → question`, with the cost (reads the hub tables and cards, not PDFs).
  **Stop and wait.** Never write syntheses for every hub.
- **Not enough evidence** (fewer than `project.yaml → synthesis.min_papers`, default 4, or almost no outcomes/numbers):
  do not write a paraphrase of the table. Say what is missing and offer the cheapest fix: deep analysis of the brief
  papers in that hub, or filling outcomes on the existing cards.

## Before writing
1. **Agree the question** in one sentence with the user. A question, not a noun: not "silicone", but "which surface
   treatment keeps a hydrogel bonded to silicone in water?". If the user's own design is involved, ask which part
   of it the question is about.
2. **Pick the sources**: the hub(s) the question lives in, plus neighbouring hubs (`Interfaces`, `Quantity - …`,
   `Protocols - …`). Read the hub tables and the verified cards; open a PDF only to check a number or a recipe.
3. **Normalise names** before counting: the same agent, material or method under two names (trade name vs chemical
   name, abbreviation vs full name) is one row. Say in the text that you merged them and why.

## Structure (save as `analysis/<YYYY-MM-DD>_<short-topic>.md`)
```markdown
---
type: synthesis
question: "<the agreed question>"
hubs: [Link - plasma, Element - insulation]   # exact hub note names; the build links the synthesis into them
papers: [Smith2024, Lee2019, ...]              # every paper used; the build flags papers added to the hubs later
date: YYYY-MM-DD
---
# <Title — the answer in a few words, or the question>

*Date. Sources: which hubs / fields, how many records in how many papers. Links to the hub pages.*

## 1. What was collected
Table: groups of approaches → number of records → examples. Tally of outcomes (works / partial / fails / not tested).
One sentence on bias: papers report the route that worked, so "fails" is rare; real failures show only where
authors compared variants or something broke during the work.

## 2. Key numbers
Table: what · value · condition · source (`[[ID]]` p.). Only comparable values side by side; values read from
figures marked as such; secondary sources (a review quoting a paper) marked "not checked against the PDF".

## 3. Conclusions
Numbered. Each: **one-sentence claim in bold**, then the evidence with `[[ID]]` and pages, and the conditions under
which it holds. Separate clearly: shown in a paper · shown only qualitatively · inferred by analogy (say so) ·
never tested in the base. Include contradictions and conditions where an approach fails.

## 4. What this means for <the user's project>
Only if the user's design or question is known. Table per part / interface / decision of their design:
what the base gives · status (recipe with parameters / partial / no data) · what to do next.
Otherwise a short "Implications" list.

## 5. Gaps and candidate papers
What the base cannot answer; which papers or SI would close it. Candidates are **not added** — ask before fetching.
```
The body is written in `project.yaml → focus_language` (the user's language); hub names, IDs and units stay as
they are; plots (if any, in `analysis/`) have all text in English.

## Rules
- Every number and every claim about a paper carries `[[ID]]` and a page. Claims from brief cards are marked "(brief card)".
- Do not invent consensus: "3 of 5 papers" is better than "usually".
- A synthesis interprets; the cards stay the source of truth. If you find an error in a card while writing, fix the card, rebuild, then continue.
- Keep it short: 1–2 screens. Tables for numbers, prose only for conclusions.
- After saving: `kb.py build`. The synthesis appears in `Index` (section *Syntheses*) and as a banner on top of each hub in `hubs:`.
  Hubs with enough evidence and no synthesis show a hint banner instead.

## Updating
`kb.py candidates` and the hub banner show "N new paper(s) since". To update: read only the new papers' records in
the hub, change the conclusions they affect, add them to `papers:`, set the new `date`. Keep the user's text below
`📝 My notes` (the build never rewrites files in `analysis/`; edit them in place).
