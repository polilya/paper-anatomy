# Measurement protocols (`protocols`) — only on request

Trigger: the user calls a paper relevant for methods ("write out the method", "how did they measure X", "we want to
repeat this"). Purpose: record HOW a quantity was measured, detailed enough to rebuild the experiment, and compare
papers on the hub page `Protocols - <quantity>`.

## Fields (one item per distinct measurement)
| key | content |
|---|---|
| `quantity` | the measured quantity (same names as hub pages; e.g. mechanics, swelling, conductivity, viability, force) |
| `name` | short name, e.g. "tensile modulus of swollen film" |
| `measures` | exact definition with formula/symbol (e.g. "Q = m_swollen / m_dry") |
| `reference_state` | reference for ratios and thicknesses; how it was produced |
| `sample` | material and state, geometry, how dimensions were measured, free-standing or bonded, n |
| `preparation` | history before the test (curing, washing, drying, conditioning, sterilisation, passage) |
| `environment` | medium, temperature, immersed / in air, time to equilibrium and criterion |
| `instrument` | model and settings |
| `procedure` | ordered list of steps as done in the paper |
| `analysis` | formula, model, fit range, corrections, statistics |
| `result` | numbers with ± and n, SI units |
| `pitfalls` | what can bias the number; questionable choices |
| `missing` | what is needed to reproduce but not given (incl. "SI not read") |
| `our_setup` | can the user's lab do it (`project.yaml → lab`), what to change |
| `pages` | `p3, p9, SI p5` |

## Algorithm
1. Find every place the quantity appears: methods, results, captions, tables, SI. Use `kb.py peek <ID> grep:<instrument|unit|keyword>`.
2. One item per distinct measurement (dry vs wet measured differently = two items). Anything not stated → `not reported`.
3. Answer the checklist of `domain.yaml → protocol_checklists[<quantity>]` (shown on the hub page).
4. Critique in `pitfalls`; map to the user's lab in `our_setup`.
5. `kb.py check` (missing required keys are flagged), `kb.py build`.
6. "Build our protocol for X": read `notes/hubs/protocols/Protocols - X.md`, write a proposal under its `📝 My notes`
   — which choices from which papers ([[ID]] + page), why, open questions.
