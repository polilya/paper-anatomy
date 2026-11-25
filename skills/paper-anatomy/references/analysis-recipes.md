# Asking the knowledge base

Answer from cards and generated tables, not from memory. Cite every statement as `[[ID]]` + page. Say how many
papers support it and whether they are verified or only brief. If the base cannot answer, say so and name which
papers would need deep analysis.

Fast sources: `tables/papers.csv`, `metrics.csv`, `tests.csv`, `elements.csv`, `links.csv`, `interactions.csv`,
`protocols.csv`, `journals.csv`, `relations.csv` (pandas or grep), then the cards themselves.

| Question | Recipe |
|---|---|
| "Compare X across papers" | `metrics.csv` filtered by quantity; group by condition (state, medium, temperature, size) — never rank values measured under different conditions; point to `Quantity - X` page and its plot |
| "What has been tried for function F?" | `Function x solution.md` row F; hubs of the element roles in it |
| "Where are the gaps?" | empty cells in `Function x solution`; link methods with only `not tested`; environment entities never tested (`tests.target`); quantities reported by < 3 papers; combinations of tags with no paper |
| "How do people join A to B?" / "what is the structure of these devices?" | `Interfaces.md` (structure map, tables by role pair and material pair); `Link - <method>` hubs with outcomes and numbers; `links.csv` |
| "Which materials are used for component X, with what properties?" | `Element - <role>` hub (material, dimensions, how made, properties with pages); `elements.csv` |
| "Who works on this?" | `Lab - …` hubs, `relations.csv` (same_lab, shared_author, follow_up) |
| "What should I read next?" | `review_map.refs_to_add` on review cards; cited-but-missing papers (search the cached texts for DOIs not in the base) — ask before fetching anything |
| "Write a short review of topic T" | cards with topic T, grouped by object type / approach; one paragraph per group with numbers + pages; a table; open questions. Save as `analysis/<date>_<topic>.md` in the base folder, not inside `notes/` |
| "Is my design new?" | deconstruct the user's design like a card (elements, links, functions) and compare element by element with the hubs |
| "Trends over time" | `Quantity - X` plots (year on the x axis), topic counts by year from `papers.csv` |

Plots for a specific question: write a short script into `analysis/` reading `tables/*.csv` (matplotlib, all text in
English, only comparable points, one point = one paper with page).
