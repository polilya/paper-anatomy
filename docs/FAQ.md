# FAQ — limits, privacy, honest use

**Can I trust the numbers?**
Each number has a page so that you can check it in seconds. "verified" means it was checked against the PDF, not
that it is true. Spot-check a few numbers per paper, especially values read from plots (marked "from figure").

**Does Claude invent things?**
The skill forbids it: anything not in the paper is written as `not reported`. Mistakes are still possible (wrong
page, wrong unit conversion, misread figure). `kb.py check` catches structural errors, not wrong content.

**Where does my data go?**
The text of the PDFs you add is sent to the AI model to be read. Do not put unpublished manuscripts, patents in
preparation or confidential reports in the inbox unless your institution allows that. Bibliographic lookups go to
OpenAlex (open scholarly database) by DOI.

**Can I share my base?**
The cards are your summaries plus short factual extracts with page references; sharing them is generally fine.
Do not share the PDFs themselves (copyright) — the `.gitignore` of a new base excludes the inbox and the cache.

**How much does it cost?**
Brief cards are cheap; deep analysis reads the whole paper and costs more. That is why deep analysis runs only on
papers you choose.

**Scanned PDFs?**
They have no text layer; `ingest` flags them. Run OCR first (e.g. in Acrobat, or `ocrmypdf`), then add them again.

**Supplementary information?**
Put SI files next to the paper and tell Claude; they are attached to the paper's card, not added as new papers.

**I don't use Obsidian.**
Use `knowledge_base.xlsx`, or read the Markdown pages in any editor.

**Can I edit cards myself?**
Yes — they are plain text (YAML). Run `kb.py check` and `kb.py build` afterwards, or ask Claude to.

**My field is not covered by a template.**
Start from `_template`; setup builds the vocabularies from your first papers. Consider contributing the result as a
new template (pull request).

**Journal impact factor?**
Impact factors are proprietary (Clarivate). paper-anatomy shows OpenAlex citedness and h-index, and the SJR quartile if you
download the free Scimago table into the base folder (`scimagojr*.csv`).
