# Setup of a new knowledge base

Goal: a base whose vocabularies fit the user's field, so hubs and plots make sense from the first papers.

## 1. Short interview (one message, numbered questions; accept short answers)
1. Topic and research question in 1–3 sentences.
2. What do the papers mostly study or build? (devices / materials / biological systems / models / methods — several allowed)
3. If they build objects: is it a stack of layers, an assembly of parts, a composition, a model system? What does the object interact with (tissue, fluid, operator, imaging, cells…)?
4. Which connections between parts matter to you (mechanical, chemical bonds, adhesive, welding, electrical, fluidic, biological)?
5. Which quantities do you compare across papers (with units if you know them)?
6. Where are the PDFs (folders)? Do folder names mean something (topics)? Any keywords that define your sub-topics?
7. Your lab: key equipment and constraints (what you cannot do).
8. Language for the short "focus" note on each card.

Then say in 3–5 lines how you understood the field, which template you will start from and why. Wait for "ok".
Write the parts and aspects the user asked to focus on into `project.yaml → focus_requested` (ids of anatomy parts, see step 3) — they are shown with ★ later and must not get lost after the interview.

## 2. Create
- Location: a folder `paperkb/` inside the user's project folder unless they want another one.
- `kb.py init <dir> --domain <closest template>`; mixed fields → the closest one, merged by hand with parts of another.
- Fill `project.yaml` from the answers (`title`, `question`, `relevance_criteria`, `pdf_dirs`, `folder_focus`, `focus_keywords`, `lab`, `focus_language`). `root` = the folder that the PDF paths are relative to.

## 3. Calibrate the domain on 10–15 typical papers
1. `kb.py ingest`, `kb.py stub <sha>` for 10–15 papers the user calls typical (or a spread across folders).
2. Brief cards for them (see `add-papers.md`).
3. `kb.py check` → collect `NEW-VOCAB` terms. Propose ONE diff for `domain.yaml`: categories, object types, tags, element roles, functions, link methods, environment entities, quantities + SI units, plot pairs, protocol checklists. Show it as a short list, ask, then write.
   In the same diff propose `anatomy` (`references/anatomy.md`): the parts of the object, how they connect and what to look at in each; mark which parts the user asked for and **which you suggest** in addition, and why. Also `element_columns` per role.
4. `kb.py build`, open `notes/Index.md`, explain what was generated (`explain-to-user.md`).

## 4. Hand over
Tell the user how to: add PDFs (drop into the inbox, say "add new papers"); ask for deep analysis; open the
vault in Obsidian (File → Open folder as vault → the `paperkb` folder or the whole project); find Excel and plots.
