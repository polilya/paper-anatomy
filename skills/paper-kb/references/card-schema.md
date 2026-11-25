# Card schema (`records/<ID>.yaml`)

ID = first author surname + year, ASCII (`Smith2024`; collision → `Smith2024a`, `b`). YAML block style; quote strings
that contain `: `. Unknown fields are kept but not rendered (check warns). Missing information → `not reported`.

## Brief fields
| field | content |
|---|---|
| `id`, `status` | `brief` / `verified` (= numbers checked against the PDF with pages) |
| `file`, `sha`, `also_at`, `supplementary` | PDF path relative to `project.yaml → root`; SHA from ingest; duplicate copies; SI files `{file, sha, note}` |
| `doi`, `title`, `year`, `journal`, `authors` (`"Surname, Given"`), `corresponding`, `institution`, `country` | bibliography |
| `lab` | `"<PI surname> (<institution short>)"` — drives the *same_lab* relation |
| `category`, `object_type`, `topics` | from `domain.yaml` |
| `summary` | one line |
| `focus` | `{axes: [...], text: ...}` — what sets the paper apart; the only field in the user's language |
| `relevance`, `use_for` | high / medium / low for the user's question; how they will use it |
| `key_findings` | 2–5 bullets with numbers + pages |

## Deep fields
| field | content |
|---|---|
| `object` | `{name, purpose, scale}` |
| `elements`, `functions`, `links`, `interactions` | see `deconstruction.md` |
| `tests` | every test: `{name, level, type, target, object, method, conditions, result, page}`; `level`/`type` from `domain.yaml`; `object` = sample geometry and state; `target` = element id, link `a–b` or environment entity |
| `metrics` | `{quantity, value, unit, condition, page, from_figure}` — one number per item, unit exactly as in `domain.yaml → quantities` (convert, keep the original in `condition`); ranges → two items or text quantity |
| `protocols` | see `protocols.md` (only with permission) |
| `limitations` | what is weak or missing |
| `builds_on` | `[{id, what}]` — earlier paper in the base this one continues |
| `figure` | `{page, clip: [x0,y0,x1,y1]}` to choose the thumbnail, or `locked: true` |

## Lenses (extra field per category; `domain.yaml → lenses` says which is expected)
| lens | when | content |
|---|---|---|
| `design_rules` | material / synthesis papers | `[{variable, range, effect, page, points}]` — variable = normalised name reused across papers (`crosslinker content (mol%)`); `points: [{x, y, unit_x, unit_y}]` optional numbers for plots |
| `process_window` + `lab_compat` | method papers | `[{parameter, window, failure, page}]`; `lab_compat` = can the user's lab do it (from `project.yaml → lab`) |
| `review_map` | reviews | `{taxonomy, tables, consensus, open_questions, refs_to_add}` — classes of approaches, comparison tables with pages, consensus ranges with conditions, disagreements, papers worth adding |
| `transfer` | papers from a neighbouring field | `{applies: [...], caveats: [...]}` — what carries over to the user's project and why it may not |
| `bio` | biology | `{model, cell_type, culture, timepoints, readouts, controls, result, page}` |

## Illustrative fragment (invented paper, to show the shape only)
```yaml
id: Example2025
status: verified
category: device
object_type: device
topics: [silicone, minimally-invasive-surgery]
summary: Tendon-driven silicone catheter tip with an embedded force sensor; 90° bending at 2 N tendon force.
focus: {axes: [method], text: "Same bending as earlier designs, but with a sensor moulded into the tip."}
relevance: high
key_findings:
  - "Bending angle 90° at 2.0 N tendon force (p5)"
metrics:
  - {quantity: bending_angle, value: 90, unit: deg, condition: "2.0 N tendon force, in air", page: p5}
```
