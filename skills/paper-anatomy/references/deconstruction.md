# Object deconstruction

Every paper studies or builds something. Take it apart the same way in every field, so that papers become
comparable part by part: **elements**, **functions**, **links** between elements, **interactions** with the
environment, and how the elements were **made** (in detail only when that is the point).

## Depth: core first, detail on request
Do not split an object into dozens of sub-parts by default. A base where every card has 15 elements is hard to read
and expensive to build; most of those parts are never compared.

1. **Core (default).** `project.yaml → deconstruction.core` lists the 3–7 main parts of the user's kind of object
   (e.g. a catheter: shaft, tip, actuator, sensor; a thin-film electrode: substrate, conductor, insulation, electrode
   site; a hydrogel: network, crosslinker, filler). On every deep card record only these, with no `parent`; their
   links, their main interactions with the environment, the key preparation. A part outside the core goes into the
   `note` of the core part it belongs to (`note: "includes Ti 10 nm adhesion layer"`), not into a new element.
2. **Detail (only for parts in `deconstruction.expand`).** Inside an expanded part: sub-elements with `parent`, the
   links between them, their key preparation. The value says what to detail (`{conductor: [polymer, crosslinker,
   additive]}`).
3. **Ask, then expand.** Propose detail when (a) the first 3–5 deep cards of a new base are done, or (b) a paper's
   contribution lies inside a part that is not expanded (a new crosslinker inside "conductor", a new weld inside
   "tip"). Then record the contribution in `key_findings` and the part's `note`, and ask: "Do you want *conductor*
   in more detail (polymer, crosslinker, additive, how each is made)? That applies to new papers; re-reading the
   N verified cards that have a conductor costs about N deep analyses." Offer 2–3 concrete options taken from what
   the papers actually contain, and say which fits the user's question best. Write the answer into `expand`.
4. **Scope.** Interactions, tests and numbers outside `project.yaml → scope.in_focus` are not taken apart:
   `context` gets one line, `out_of_scope` nothing (`add-papers.md` step 4).
5. **No core yet** (old base, user skipped setup): after the first deep card propose a core from it and the user's
   question, ask, write it into `project.yaml`.

`kb.py check` warns about elements finer than the core (not in `core`, and not inside an expanded part).

## Fields
```yaml
object: {name: "tendon-driven catheter tip", purpose: "steer inside vessels", scale: "Ø 3 mm, 40 mm long"}
elements:
  - {id: E1, name: bending section, role: shaft, kind: structural, parent: null,
     material: "silicone, Shore 30A", geometry: "Ø 3 mm, 40 mm", props: "E = 1 MPa (p4)", page: p3,
     preparation: {method: injection moulding, key: false}}
  - {id: E2, name: tendon, role: transmission, kind: functional, material: "Dyneema Ø 0.2 mm", page: p3}
  - {id: E3, name: force sensor, role: sensor, kind: functional, material: "FBG fibre", page: p3,
     preparation: {method: in-mould sensor embedding, key: true, steps: [...], parameters: "...", page: p3}}
functions:
  - {id: F1, function: bend or steer, performed_by: [E1, E2], metric: "90° at 2 N (p5)", page: p5}
links:
  - {a: E2, b: E1, class: mechanical, method: knot / suture, transmits: force, outcome: works,
     numbers: [{quantity: force, value: 5, unit: N, condition: "pull-out", page: p6}], page: p3}
interactions:
  - {element: E1, entity: vessel wall, type: mechanical contact, requirement: "contact force < 0.5 N",
     tested: "silicone phantom", result: "max 0.3 N (p7)", page: p7}
```

- `kind`: `structural` (holds the shape / carries load), `functional` (does the job: senses, actuates, conducts), `both`.
- `parent`: builds a hierarchy (assembly → sub-assembly → part; film → network → polymer).
- `principle` (optional): the working principle of the element when it is not its material — e.g. `tendon-driven`, `magnetic`, `hydraulic`, `FBG sensing`. It becomes the column of the function × solution table and the solution variant in comparisons; without it the material class is used. **Keep it a short reusable label (1–4 words) shared across papers**; the detailed description goes into `note`. Free text written once is not a solution and is not compared.
- Tie numbers to what they measure: a metric with `function: F1` is compared by the solution of the elements performing F1 (function hubs, `Function - …` → *Results by solution*, `tables/function_results.csv`).
- `links.class`: mechanical · covalent · non-covalent · adhesive · thermal · electrical · fluidic · biological · other. `method` from `domain.yaml → link_methods`. `preparation` = surface treatment or extra step for this joint. `outcome`: works / partial (holds dry, fails wet; weaker than the alternative) / fails / not tested.
- `interactions.entity` from `domain.yaml → environment_entities`.
- Functions: short normalised phrases from `domain.yaml → functions`, so that the same function in two papers lands on the same hub row.

## When is preparation "key"?
`key: true` only if the way the element is made is **non-obvious or is what the authors present as their contribution**:
a new synthesis, an unusual deposition or patterning, a trick without which the element would not work, a process
with a narrow window. Then fill `steps`, `parameters`, `page` and the paper's `process_window`. Bought or standard parts
(commercial tube, glass slide, spin-coated PDMS, standard cell line) → one line, `key: false`. Unsure → ask the user.
The same rule for the `method` of a link.

## What the parts are, by object type
| type | elements | links | interactions |
|---|---|---|---|
| device / assembly | parts and sub-assemblies (shaft, tip, actuator, sensor, housing, connector) | crimp, weld, reflow, glue, overmould, wire bond, tubing fit | tissue, blood, operator, robot driver, imaging, sterilisation |
| layered device (stack) | layers bottom → top incl. carriers that are removed (`note: removed`) | how each layer holds to the one below (plasma + silane, co-curing, lamination, interpenetration) | medium, cells, tissue |
| material / composition | components (polymer, crosslinker, filler, dopant, solvent), phases, structure levels | covalent crosslink, H-bonds, ionic, π–π, entanglement, interpenetration | water/PBS, temperature, light, pH, cells |
| biological model | cell types, matrix, coating, scaffold, medium, stimulus/drug, organ/organism | integrin–ligand, cell–cell, receptor–ligand, adsorption | culture conditions, flow, stimulation, host/immune system |
| model / simulation | domains, materials of domains, interfaces, boundaries | tie, cohesive zone, contact with friction | loads, boundary conditions, fluid, temperature |

A paper can have more than one object (a new material and a device made from it): describe the main one under
`object`; elements of the second are fine in the same list with a `parent`.

## New terms
If a role, function, link method or environment entity is not in `domain.yaml`, first try an existing one. If none
fits, ask: "In Smith2024 the tendon is laser-welded to a ring — add `laser welding` (thermal) to link methods?"
Write the answer into `domain.yaml`.

## Columns per part
Different parts need different columns: a drive needs principle and numbers, a sensor range and placement, a layer
material and thickness. `domain.yaml → element_columns` sets them per role (`default` for the rest); available:
`principle, material, geometry, preparation, props, functions, numbers, note`. Columns empty in every row are hidden.

## What it gives (generated)
Hubs per element role, link method, environment entity, key preparation method and function; `Interfaces` (structure
map of roles and joints over all papers, tables by role pair and material pair); `Function x solution` (rows =
functions, columns = solution variants, cells = papers; empty cells = untried combinations); a mermaid structure graph
on every paper note; `target` on tests shows which parts were ever tested.
