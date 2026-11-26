# How the knowledge base works

## Folders
```
paperkb/
├── project.yaml        your project: question, scope (in focus / context / out), core parts, relevance criteria, PDF folders, lab
├── domain.yaml         vocabularies of your field: categories, tags, element roles, link methods, quantities + units
├── records/            ONE CARD PER PAPER — the only thing that is edited (by Claude or by you)
├── inbox/              drop PDFs here (or list your own folders in project.yaml)
├── relations_manual.csv  links between papers you add by hand
├── figures/            thumbnail of Fig. 1 per paper (put <ID>_manual.png to replace it)
├── notes/              GENERATED Obsidian pages (your text under "📝 My notes" is kept)
├── tables/             GENERATED CSV tables
├── knowledge_base.xlsx GENERATED Excel workbook
└── _cache/             extracted PDF text, OpenAlex data
```
Everything generated is rebuilt by `kb.py build` from the cards. Delete it and rebuild — nothing is lost.

## How it starts: your papers first
Setup does not begin with a questionnaire. You give about 10 original papers closest to your work; Claude reads them
(`kb.py survey`: abstract, figure captions, method headings, shared terms and units), tells you what they have in
common and how they differ, then asks one question at a time — each with options taken from those papers — to find
what is your focus. The answers become `project.yaml → scope` (`in_focus` extracted in full, `context` in one line,
`out_of_scope` skipped), the core parts of the object and the relevance criteria. The 10 papers become the first cards.

## How categories, types and tags appear
- **Category** (device, material, method, biology, simulation, review…) — the primary kind of paper. It decides which extra "lens" a deep analysis fills: design rules for materials, process window for methods, a review map for reviews.
- **Object type** (device, layered device, material, cell model, model…) — what the paper builds or studies, and how it is taken apart.
- **Tags (topics)** — free keywords grouped in `domain.yaml` (materials, methods, properties, applications).

All three come from `domain.yaml`. A template gives the first version; during setup Claude proposes additions from
your seed papers and drops terms outside your scope. Later, if a card needs a term that is not there, `kb.py check` reports `NEW-VOCAB` and Claude asks
you before adding it. So vocabularies stay small and consistent, and hubs do not fragment into near-duplicates.

## How to navigate
Start at **`notes/Index.md`**: counts, links to all overview pages and to every hub.

From a **paper page** you can jump to:
| link | leads to |
|---|---|
| journal, lab, category, object type, each tag | a hub listing every paper with it |
| each element role (e.g. *shaft*, *crosslinker*) | all implementations of that role across papers: material, geometry, how made, properties |
| each link method (e.g. *laser welding*, *hydrogen bonding*) | every place it was used, on which materials, whether it held, with numbers |
| each environment entity (e.g. *vessel wall*, *PBS 37 °C*) | requirements and measurements across papers |
| each key preparation method | parameters and process windows across papers |
| each quantity | plot over years + table with conditions and pages |
| each protocol | side-by-side comparison of how papers measured it + a checklist for your own protocol |
| related papers | same lab, shared authors, citations, follow-ups |

**Overview pages**: `Interfaces` (structure map + which components and materials are joined, how), `Function x solution`,
`Property map`, `Design rules`, `Process windows`, `Review map`, `Journals`.

In Obsidian also use the **graph view** (papers and hubs as a network), **search**, and the **tags** pane.

## Lists, comparisons and syntheses
Not every hub page is equally rich, and that is by design:

| level | pages | why it looks like this |
|---|---|---|
| **list** | Topic, Category, Lab, Journal, Object | the cards only carry a tag here, so the page lists papers with a one-line summary |
| **comparison** | Element, Link, Environment, Function, Prep, Quantity, Protocols, Design rule | deep cards record for each occurrence whether it worked, the evidence, numbers and conditions, so the page is a comparison table |
| **synthesis** | `analysis/*.md`, linked from the hubs and from `Index` | a short written answer to one question: what was collected, key numbers, numbered conclusions with sources, what it means for your project, gaps |

Syntheses are written by Claude only when you ask a question ("what do my papers say about bonding silicone to
hydrogel?") or accept one of up to three proposals after a batch of deep analysis (`kb.py candidates` ranks the hubs
with enough evidence). A hub that has enough evidence but no synthesis shows a hint banner; a synthesis whose hubs
received new papers is flagged *N new paper(s) since*. To turn a list (e.g. a material tag) into an analysis, ask a
question about it: the answer is built from the comparison hubs the tag touches.

## How data are visualised
| What | Where |
|---|---|
| Structure of each studied object (elements, links, environment) | mermaid graph on the paper page |
| Numbers per quantity across papers | `Quantity - <name>` pages: summary, min / median / max with paper and page, every value folded below; value-by-year plots only with `project.yaml → plots: {by_year: true}` |
| Which solution performs best | `Function - <name>` → *Results by solution*: table and bar plot per quantity (metrics tied with `function:`) |
| The object as parts, solutions and test methods | `notes/anatomy/` from `domain.yaml → anatomy`; `kb.py graph` colours the graph view |
| Property vs property (e.g. stiffness vs conductivity) | `Property map` — pairs set in `domain.yaml → plot_pairs` |
| Journals: counts by category, journal × year | `Journals` page |
| Which components meet which, how they are joined (all papers) | `Interfaces` — structure map (`plot_structure_map.png`) + tables by role and by material pair |
| What was tried for each function | `Function x solution` — heatmap + table; columns are solution variants (the element's `principle`, else its material class) |
| Everything as sortable tables | `knowledge_base.xlsx` (sheets: Papers, Journals, Elements, Functions, Links, Interactions, Tests, Metrics, Protocols, Design rules, Process windows, Relations) |

Only comparable numbers are plotted: same quantity, single numeric value, unit of `domain.yaml`. Conditions still
differ between papers (dry/wet, temperature, size) — always read the table next to the plot.

## Brief and deep cards
| | brief | verified (deep) |
|---|---|---|
| reads | title, abstract, introduction | the whole paper and SI |
| contains | bibliography, category, tags, one-line summary, focus, relevance | + key findings with pages, object deconstruction (the core parts set in `project.yaml → deconstruction`; finer detail only for parts you chose to expand), every test, numbers, lens, limitations |
| when | every new paper | only papers you choose |

Protocols (how exactly something was measured) are added only when you ask for a specific paper.
