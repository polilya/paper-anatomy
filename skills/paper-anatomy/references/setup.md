# Setup of a new knowledge base

Goal: a base that records what the user needs and skips what they do not. The user's focus is found from their own
papers, not from a blank questionnaire: first read ~10 papers they chose, then ask questions built on what was read.

## 0. First message: what the base can do + ask for 10 seed papers
In the user's language, about 10 lines, using `explain-to-user.md` → *What you can do*:
1. What they get: (1) short cards for all papers, they pick which to read in depth; (2) deep analysis takes the
   studied object apart into its **main parts** first, finer detail later and only where their focus is; (3) then
   questions → **written syntheses** (an answer with numbers and sources, how a line of work developed, a comparison
   for a design decision, a checklist for their own design, gaps). 2–3 examples for their field if you can guess it.
2. The request: **"Send me about 10 original research papers closest to your work — the ones you would cite first.
   Not reviews (reviews come later, as a source of references). I read them first, tell you what I see in them,
   then ask a few questions one by one to find out what is your focus and what is not."** A folder path or files in
   the chat are both fine. One sentence about their topic is welcome, not required.
3. Privacy, once (SKILL.md rule 8): the text of these PDFs is sent to the AI model.

Fewer than 10 is fine (≥ 5 gives a useful picture; with 1–4 say the picture will be rough). More than 15: take the
15 the user calls most typical, the rest go through the normal "add papers" route later.

## 1. Read the seed papers (cheap first pass)
`kb.py survey <folder or files>` (no base needed). Per paper: title, DOI, abstract, figure captions, method
headings, a "possible REVIEW" flag; across the set: phrases, words and units shared by ≥ 30 % of the papers.
Read that output. Open a paper further (`page`-level reading of its methods or Fig. 1) only where the survey leaves
the object or the method unclear. Do not write cards yet. Cost: about one brief card per paper.
- Reviews among them: say which, ask whether to replace them by original papers or keep them as context only.
- Scans without text: name them; they need OCR.

## 2. Portrait of the set (one message, ~12 lines, user's language)
What you understood, so the user can correct it before anything is built:
- **Common object**: what these papers build or study, in one sentence, and its main parts as they appear across
  the set (e.g. "a soft electrode array: substrate, conductor, insulation, contact to the tissue").
- **What is done with it**: made / characterised / tested in vitro / in vivo / modelled — with counts ("7 of 10 test in vivo").
- **Shared methods and quantities**: the measurements most papers report, with units (from the survey).
- **How they differ**: 2–4 groups (e.g. "hydrogel conductors (3), conductive elastomers (4), coated metal (2)"),
  each with paper numbers from the survey.
- **Outliers**: papers that do not fit the common picture.
End with: "Now a few short questions, one at a time, to find out what matters to you."

## 3. Focus questions — ONE per message
Each question is built on the portrait, offers 2–4 concrete options taken from the papers (with paper numbers) plus
"something else", and states in a few words what the answer changes ("…so I do not extract X from every paper").
Wait for the answer, write it down, then ask the next. Skip a question when earlier answers already settle it;
confirm instead of asking when the papers make the answer obvious. Usually 5–7 questions; stop when the scope is
clear. The user may answer "skip" — then use the default in brackets.

Ask in this order, adapting the wording to the field:
1. **Your work.** "These papers mostly <build / test / model> <object>. Which is closest to what you do: <option from
   group A>, <option from group B>, <modelling of …>, something else?" → `question`, `title`.
2. **Core parts.** "Across the papers the object has these parts: A, B, C, D, E. Which ones do you design or choose
   yourself (in focus), which only matter as context (one line per paper), which can I ignore?" → `deconstruction.core`
   = the in-focus parts (3–7), plus a part for the context ones if needed; context and ignored → `scope`.
   [default: the parts present in most papers]
3. **Connections and conditions.** "Papers N, M test <bonding / delamination / swelling / sterilisation / in vivo
   durability>. Which of these questions are yours?" → `scope`, later `links` and `interactions` detail.
4. **Numbers to compare.** "The quantities most papers report: <list with units>. Which do you want side by side?
   Any that you need and no paper here reports?" → `scope.in_focus`, and the quantities kept in `domain.yaml`.
5. **What to skip.** Name concrete side topics found in the set ("Paper 6 spends half its length on the surgical
   procedure, paper 9 on signal processing"): "keep as context or skip?" → `scope.out_of_scope`. [default: context]
6. **Relevance.** Propose high / medium / low criteria in one line each, from the answers so far → "ok or change?"
   → `relevance_criteria`.
7. **Practical facts** (may go in one message, these are not about focus): where the rest of the PDFs are and what the
   folder names mean; lab equipment and constraints; language of the focus note on each card.

Summary (≤ 8 lines): the question, the core parts, in focus / context / out of scope, the quantities, the template you
will start from and why. Wait for "ok".

## 4. Create
- Location: a folder `paperkb/` inside the user's project folder unless they want another one.
- `kb.py init <dir> --domain <closest template>`; mixed fields → the closest one, merged by hand with parts of another.
- Fill `project.yaml` from the answers: `title`, `question`, `relevance_criteria`, `scope`, `deconstruction.core`
  (`expand` stays empty), `pdf_dirs`, `folder_focus`, `focus_keywords`, `lab`, `focus_language`. `root` = the folder
  that the PDF paths are relative to. Put the seed papers where `pdf_dirs` (or the inbox) will find them.

## 5. Calibrate the domain on the seed papers
1. `kb.py ingest`, `kb.py stub <sha>` for the seed papers (they are already read: the brief cards are quick).
2. Brief cards for them (`add-papers.md`), relevance against the agreed criteria.
3. `kb.py check` → collect `NEW-VOCAB` terms. Propose ONE diff for `domain.yaml`: categories, object types, tags,
   element roles (= the core parts), functions, link methods, environment entities, quantities + SI units (those in
   focus), plot pairs, protocol checklists. Remove template terms that are out of scope. Show it as a short list, ask, then write.
   In the same diff propose `anatomy` (`references/anatomy.md`): its nodes are the core parts, plus parts you
   **suggest** in addition (◆, one line why each matters); set `project.yaml → focus_requested` (★) to the parts
   the user put in focus (step 3, question 2). Also `element_columns` per role.
4. `kb.py build`, open `notes/Index.md`, explain what was generated (`explain-to-user.md`).
5. Propose deep analysis for the 3–5 seed papers closest to the agreed question; stop and wait (`add-papers.md` step 3).

## 6. Hand over
Tell the user how to: add PDFs (drop into the inbox, say "add new papers"); ask for deep analysis; open the
vault in Obsidian (File → Open folder as vault → the `paperkb` folder or the whole project); find Excel and plots.
Remind them in one line what comes after the cards: "once a few papers are analysed in depth, ask me questions —
I write syntheses (see the examples I gave), and I will ask you which parts to detail further". The scope can be
changed any time ("add X to my focus", "stop extracting Y").
