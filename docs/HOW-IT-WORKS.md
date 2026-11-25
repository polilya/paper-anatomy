# How the knowledge base works

## Folders
```
paperkb/
├── project.yaml        your project: question, relevance criteria, PDF folders, lab, focus keywords
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

## How categories, types and tags appear
- **Category** (device, material, method, biology, simulation, review…) — the primary kind of paper. It decides which extra "lens" a deep analysis fills: design rules for materials, process window for methods, a review map for reviews.
- **Object type** (device, layered device, material, cell model, model…) — what the paper builds or studies, and how it is taken apart.
- **Tags (topics)** — free keywords grouped in `domain.yaml` (materials, methods, properties, applications).

All three come from `domain.yaml`. A template gives the first version; during setup Claude proposes additions from
your first papers. Later, if a card needs a term that is not there, `kb.py check` reports `NEW-VOCAB` and Claude asks
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

## How data are visualised
| What | Where |
|---|---|
| Structure of each studied object (elements, links, environment) | mermaid graph on the paper page |
| Numbers per quantity across papers and years | `Quantity - <name>` pages (`notes/plots/plot_metric_*.png`); hollow markers = read from a figure; values in a different unit or as ranges are listed under "Not plotted" |
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
| contains | bibliography, category, tags, one-line summary, focus, relevance | + key findings with pages, object deconstruction, every test, numbers, lens, limitations |
| when | every new paper | only papers you choose |

Protocols (how exactly something was measured) are added only when you ask for a specific paper.
