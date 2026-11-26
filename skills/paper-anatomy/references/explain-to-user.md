# Explaining the base to someone new to AI tools

Keep it concrete and short; show, don't lecture. Offer this once after setup and whenever the user seems lost.

## In five sentences
1. Every paper gets a card: a small text file with what was done, numbers and the page each number comes from.
2. You decide which papers deserve a full read: I first make short cards for all, then ask.
3. From the cards I generate pages you can click through (Obsidian), an Excel file and plots — you never edit those by hand; your own notes go under "📝 My notes" and are kept.
   These pages are tables that compare papers. When you ask me a question about a topic, I write a **synthesis**: a short answer with conclusions, numbers and gaps, linked from the topic's page.
4. I can be wrong. Check a few numbers against the PDF page I give; "verified" means checked against the PDF, not "true".
5. The PDF text is sent to the AI model, so do not put confidential manuscripts in the inbox unless that is acceptable.

## What you can do (say this at first contact; adapt the examples to the user's field)
| stage | you do | you get |
|---|---|---|
| 0. start | send ~10 original papers closest to your work | what they have in common, then a few questions one at a time about what is your focus and what is not — so nothing unneeded is extracted |
| 1. collect | drop PDFs, say "add the new papers" | a short card per paper and a table; you choose which to read in depth |
| 2. take apart | "analyse 2, 5 and 7 in depth" | each studied object split into its **main parts** (3–7), how they are joined, how they behave in their environment, every number with its page. More detail later, only for the parts you care about |
| 3. ask | a question about several papers | a **synthesis**: a written answer, linked from the pages it draws on |

Kinds of synthesis that worked in the base this skill comes from (100 papers on soft neural interfaces):
- **An answer to one design question** — "Which surface treatment keeps the next layer on silicone in water?": 56 records from 29 papers grouped, outcome tally, key numbers, 8 numbered conclusions with sources, a checklist per interface of the student's own device, and what no paper has tested.
- **How a line of work developed** — "Shape-changing neural interfaces driven by swelling, 2015–2024": one table for 8 works, what was already known in 2015, what changed, what stayed unsolved.
- **A comparison for a decision** — "Stimulating vs recording devices": classification, three device architectures, what sets stimulating devices apart, link to the project, gaps, a draft paragraph for the thesis.
- **Mining reviews** — which papers the reviews in the base cite most and which of them are missing from the base.

Other questions of the same kind: "is my design new?", "which protocol should I use to measure X?", "what has
nobody tried for function F?", "which numbers are comparable for quantity Q?".

## Where to look
| You want | Open |
|---|---|
| everything at a glance | `notes/Index.md` |
| one paper | `notes/papers/<ID>.md` (figure, summary, structure graph, tests, numbers, protocols) |
| all papers on a tag / category / lab / journal | the link on the paper page → the hub page |
| how a part is made or joined in all papers | `Element - …`, `Link - …`, `Prep - …` hubs |
| numbers compared | `Quantity - …` pages (plot + table), `Property map` |
| what was tried for each function, what was not | `Function x solution` |
| how to measure something | `Protocols - …` pages |
| written answers: what holds, what it means for you, what is missing | `Index` → *Syntheses*; banner on top of a hub page |
| journals, where to publish | `Journals` |
| filter and sort yourself | `knowledge_base.xlsx` |

## Obsidian in one minute
Install Obsidian (free) → "Open folder as vault" → choose the knowledge base folder. Click links in blue to move
between pages; the graph view (left bar) shows how papers connect; search with Ctrl/Cmd+Shift+F.

## What to type to me
- "Add the new papers" — after dropping PDFs into the inbox.
- "Analyse 2, 5 and 7 in depth" — after I show the table.
- "Write out how Smith2024 measured the modulus."
- "What do my papers say about bonding silicone to hydrogel?" (→ a synthesis) · "Which topics have enough data for a synthesis?"
- "Compare the bending angle across papers." · "What has nobody tried yet?" · "Where should I publish this?"
