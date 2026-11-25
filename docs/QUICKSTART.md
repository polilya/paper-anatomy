# Quickstart — for people who have never used an AI assistant for this

About 10 minutes. You need: a computer (macOS, Windows or Linux), your PDFs, and a Claude account with access to Claude Code.

## 1. Install the Claude desktop app
Download it from claude.ai/download, sign in. Open the **Code** tab — this is where Claude can work with files on your computer.

## 2. Open your project folder
In the Code tab choose the folder where your papers are (or will be). Claude only sees this folder.

## 3. Install paper-kb
Type into the chat box exactly:
```
/plugin marketplace add polilya/paper-kb
```
then
```
/plugin install paper-kb@paper-kb
```
(If plugins are not available to you, ask Claude: "Install the paper-kb skill from github.com/polilya/paper-kb into this project" — it will copy the folder.)

## 4. Set up your base
Write: **"Set up a paper database for my topic."** Claude asks about 8 short questions (your topic, what the papers
study, which numbers you compare, where the PDFs are, your lab). Answer in a few words each. It creates a folder
`paperkb/` with an `inbox/` inside.

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
