# Quickstart — for people who have never used an AI assistant for this

About 10 minutes. You need: a computer (macOS, Windows or Linux), your PDFs, and a paid Claude plan (Pro or higher)
that includes Claude Code. Which plan, model and pace suit you: [RECOMMENDATIONS.md](RECOMMENDATIONS.md).

## 1. Install the Claude desktop app
Download it from claude.ai/download, sign in. Open the **Code** tab — this is where Claude can work with files on your computer.

## 2. Open your project folder
In the Code tab choose the folder where your papers are (or will be). Claude only sees this folder.

## 3. Install paper-anatomy
Type into the chat box exactly:
```
/plugin marketplace add polilya/paper-anatomy
```
then
```
/plugin install paper-anatomy@paper-anatomy
```
(If plugins are not available to you, ask Claude: "Install the paper-anatomy skill from github.com/polilya/paper-anatomy into this project" — it will copy the folder.)

## 4. Set up your base
Write: **"Set up a paper database for my topic."** Claude first tells you in a few lines what you can do with the base
(cards → taking papers apart → written syntheses, with examples) and asks for **about 10 original research papers closest
to your work** (not reviews) — give a folder or drop the files. It reads them, tells you what it sees in them (what is
studied, what they share, how they differ), then asks **one question at a time** about what is your focus and what is
not: which parts of the object you design, which numbers you compare, which side topics to skip. Answer in a few words
each; "skip" is fine. Then it creates a folder `paperkb/` with an `inbox/` inside, and your 10 papers become the first cards.

When Claude asks to install Python packages or to run a command, read what it says and allow it if it matches.

## 5. Add papers
Copy PDFs into `paperkb/inbox/` (or tell Claude where your folders are). Write **"Add the new papers."**
Claude makes a short card for each and shows a table like:

| # | id | year | relevance | recommendation |
|---|---|---|---|---|
| 1 | Smith2024 | 2024 | high | deep — same device class as yours |
| 2 | Lee2019 | 2019 | low | keep brief — off-topic |

Answer with the numbers you want analysed in depth, e.g. **"1 and 4"**. Nothing deep happens without your answer.

## 6. Look at the result
- Install **Obsidian** (free, obsidian.md) → *Open folder as vault* → choose `paperkb`. Start at `notes/Index.md`; click any blue link.
- Or open `paperkb/knowledge_base.xlsx` in Excel.

## 7. Check Claude's work
Open two or three cards and compare a few numbers with the PDF page written next to them. If something is wrong,
tell Claude: "In Smith2024 the modulus is on p6 and it is 1.2 MPa, fix it." Errors are rare but possible.

## What to say next
"Compare X across papers" · "How did they measure Y in Smith2024?" · "What has nobody tried yet?" ·
"Which journals publish this and where should I submit?" · "Explain how this base works."
