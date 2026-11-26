# Anatomy — the object as parts, solutions and test methods

Hub pages are organised by card field (element role, link method, quantity…). The anatomy layer is organised by the
**object itself**: which parts it has, which part acts on which, which solutions the papers use for each part, which
numbers they reach and how each part is tested. It is also what the Obsidian graph view should show.

## Configure (`domain.yaml → anatomy`)
```yaml
anatomy:
  object: "endovascular robot"
  nodes:
    - id: gw-drive                 # stable id, used in edges and project.yaml → focus_requested
      short: Guidewire drive       # file name = label in the graph; ≤ 20 characters, unique
      title: "Guidewire drive (slave)"
      about: "Advances and rotates the guidewire; its accuracy decides branch selection."
      roles: [guidewire-drive]     # element roles that belong to this part
      functions: [advance or retract guidewire]   # papers with this function count for the part
      topics: [S-guidewire-axial]  # papers with this tag count for the part
      quantities: [translation_error, rotation_error]   # numbers shown on the part page
      focus: [drive principle, slip, how accuracy was measured]   # what to look at in each paper
  edges: [[master, link], [link, gw-drive]]   # which part acts on which (drawn and linked)
  solutions:                       # optional names for solution variants
    S-drive-friction-rollers: {short: Rollers, nodes: [clamp]}   # a topic tag as a solution of a part
    friction rollers: {short: Rollers}                            # or an element principle
```
Solutions come from element `principle` (or material class) of the part's roles when **≥ 2 papers share it**, and
from tags listed under `solutions`. Free-text principles used once stay in the element table, not in the graph.

`project.yaml → focus_requested: [gw-drive, sensing]` — the parts the user asked for (★). Every other part is ◆:
proposed by Claude from the papers. During setup, propose ◆ parts the user did not name (a safety unit, a sterile
barrier, the operator, the imaging) and say in one line why each matters.

## What build writes
- `notes/anatomy/Anatomy.md` — mermaid scheme of parts and edges, table: part, papers, main solutions, what to look at.
- `1 Parts/<short>.md` — about, focus, connected parts, solutions, tested by, summary, key numbers, gaps, elements with the columns of `element_columns`, papers.
- `2 Solutions/<short>.md` — parts it serves, summary, solutions used together with it, numbers, papers.
- `3 Methods/<test type>.md` — parts tested (via `tests → target`), levels, every test.

## Graph view
`kb.py graph` writes `.obsidian/graph.json` in the vault (backup `graph.json.bak`): parts orange, solutions yellow,
methods purple, papers blue; navigation pages (journals, labs, quantities, overviews) hidden. Ask before running it
when the user has tuned the graph view themselves.

## Comparing solutions
Tie numbers to functions on the cards (`metrics: - {quantity: translation_error, value: 0.2, unit: mm, function: F1,
value_type: measured, …}`). Then each function hub gets *Results by solution*: per quantity a row per solution variant
(median / min / max of measured values, bounds and datasheet values counted apart) and a bar plot, best first
(`domain.yaml → lower_is_better`). Long format for own plots: `tables/function_results.csv`.
