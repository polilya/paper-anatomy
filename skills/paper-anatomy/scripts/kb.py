#!/usr/bin/env python3
"""
kb.py — engine of the paper-anatomy skill: a literature knowledge base built from PDFs.

Source of truth : <kb>/records/<ID>.yaml  (one card per paper) + <kb>/relations_manual.csv
Configuration   : <kb>/project.yaml (your project) + <kb>/domain.yaml (vocabularies of your field)
Generated       : <kb>/notes/** (Obsidian), <kb>/tables/*.csv, <kb>/knowledge_base.xlsx, <kb>/notes/plots/*.png

Commands
    kb.py init <dir> [--domain NAME]   create a new knowledge base (domain template: see templates/domains)
    kb.py ingest                       find PDFs that have no card yet; extract text + DOI
    kb.py stub <sha> [--id ID]         create a brief card with bibliography filled from OpenAlex/Crossref
    kb.py peek <sha|ID> <what>         read cached text: head | page:N | grep:REGEX | nums
    kb.py triage                       table of brief cards -> to ask the user which ones to analyse deeply
    kb.py candidates                   hub pages with enough evidence for a written synthesis (analysis/*.md)
    kb.py figures [--force]            thumbnails of Fig. 1 -> figures/<ID>.png
    kb.py journals [--offline]         fetch journal metadata (OpenAlex) and build the journal analysis
    kb.py check                        validate cards; NEW-VOCAB lines = terms not yet in domain.yaml
    kb.py build [--no-plots]           relations + tables + xlsx + plots + Obsidian notes (--no-plots: keep existing plots)
    kb.py graph                        colour groups and filter for the Obsidian graph view (.obsidian/graph.json)
    kb.py status                       counts
    kb.py all                          ingest + figures + build

The knowledge base folder is found from --kb, else the current folder or its parents (a folder with project.yaml
and domain.yaml), else ./paperkb.  Requirements: pymupdf pyyaml openpyxl matplotlib.
"""
import argparse, csv, datetime, hashlib, json, re, shutil, sys, time, unicodedata, urllib.parse, urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

import yaml

SKILL_DIR = Path(__file__).resolve().parent.parent
MARK = "<!-- MY NOTES: everything below this line is kept when the note is rebuilt -->"
VERSION = "0.3.0"

# ----------------------------------------------------------------------------- core vocabulary (same for every field)
STATUSES = ["brief", "verified"]
RELEVANCE = ["high", "medium", "low"]
LINK_CLASSES = ["mechanical", "covalent", "non-covalent", "adhesive", "thermal", "electrical", "fluidic",
                "biological", "other"]
OUTCOMES = ["works", "partial", "fails", "not tested"]
ELEMENT_KINDS = ["structural", "functional", "both"]
VALUE_TYPES = ["measured", "bound", "spec", "cited"]   # metric value: measured here / an upper or lower bound / datasheet / quoted from another paper
CATCH_ALL = {"other", "none", "unknown", "not-reported", "not reported"}

KEYS = {  # allowed keys of list items; check() warns about anything else
    "elements": {"id", "name", "role", "kind", "parent", "principle", "material", "geometry", "props", "preparation", "note", "page"},
    "preparation": {"method", "key", "steps", "parameters", "page"},
    "functions": {"id", "function", "performed_by", "metric", "note", "page"},
    "links": {"a", "b", "class", "method", "transmits", "preparation", "tested", "outcome", "numbers", "note", "page"},
    "interactions": {"element", "entity", "type", "requirement", "tested", "result", "note", "page"},
    "tests": {"name", "level", "type", "target", "object", "method", "conditions", "result", "page"},
    "metrics": {"quantity", "value", "unit", "condition", "from_figure", "function", "value_type", "n", "sd", "page"},
    "protocols": {"quantity", "name", "measures", "reference_state", "sample", "preparation", "environment",
                  "instrument", "procedure", "analysis", "result", "pitfalls", "missing", "our_setup", "pages"},
    "design_rules": {"variable", "range", "effect", "points", "page"},
    "process_window": {"parameter", "window", "failure", "page"},
    "builds_on": {"id", "what"},
}
PROTO_REQUIRED = ["measures", "sample", "environment", "instrument", "analysis", "result", "pages"]
REVIEW_KEYS = {"taxonomy", "tables", "consensus", "open_questions", "refs_to_add"}
TRANSFER_KEYS = {"applies", "caveats"}
TOP_KEYS = {"id", "status", "file", "sha", "also_at", "supplementary", "doi", "title", "year", "journal", "authors",
            "corresponding", "lab", "institution", "country", "category", "object_type", "topics", "summary", "focus",
            "relevance", "use_for", "key_findings", "limitations", "object", "elements", "functions", "links",
            "interactions", "tests", "metrics", "protocols", "design_rules", "process_window", "lab_compat",
            "review_map", "transfer", "bio", "builds_on", "lineage_name", "figure", "notes"}


# ----------------------------------------------------------------------------- small helpers
def sha10(p: Path) -> str:
    return hashlib.sha1(p.read_bytes()).hexdigest()[:10]


def slug(s) -> str:
    """File-name-safe tag (Obsidian forbids : / \\ ? * < > | " # ^ [ ])."""
    s = unicodedata.normalize("NFC", str(s))
    return re.sub(r"[:/\\?*<>|\"#^\[\]]", "-", s).strip()


def norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


def author_key(a: str) -> str:
    if "," in a:
        sur, given = a.split(",", 1)
    else:
        parts = a.split()
        sur, given = (parts[-1], " ".join(parts[:-1])) if parts else ("", "")
    return norm(sur) + "|" + norm(given)


def as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def cell(x) -> str:
    """One-line text for a table cell."""
    if x is None:
        return ""
    if isinstance(x, list):
        x = "; ".join(cell(i) for i in x)
    elif isinstance(x, dict):
        x = "; ".join(f"{k}: {cell(v)}" for k, v in x.items())
    return re.sub(r"\s+", " ", str(x)).replace("|", "\\|").strip()


def mdtable(head, rows) -> str:
    if not rows:
        return "_none_\n"
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(cell(c) for c in r) + " |" for r in rows]
    return "\n".join(out) + "\n"


def num(v):
    """Float from a metric value ('1.2e3', '35', '~40') or None for text / ranges."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    m = re.fullmatch(r"\s*[~≈]?\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*", str(v or ""))
    return float(m.group(1)) if m else None


def http_json(url, email=""):
    ua = "paper-anatomy/" + VERSION + (f" (mailto:{email})" if email else "")
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(1.5 * (attempt + 1))
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return None


# ----------------------------------------------------------------------------- knowledge base object
class KB:
    def __init__(self, d: Path):
        self.dir = d.resolve()
        self.project = yaml.safe_load((d / "project.yaml").read_text()) or {}
        self.domain = yaml.safe_load((d / "domain.yaml").read_text()) or {}
        self.root = (self.dir / str(self.project.get("root", ".."))).resolve()
        self.rec = d / "records"
        self.txt = d / "_cache" / "text"
        self.oa = d / "_cache" / "openalex"
        self.fig = d / "figures"
        self.notes = d / "notes"
        self.tab = d / "tables"
        self.email = self.project.get("contact_email", "")
        self.no_plots = False   # build --no-plots: keep the PNGs already drawn, draw nothing new

    # ---- domain vocabularies (all optional; missing = no check)
    def vocab(self, key):
        """Flat set of terms; a dict of lists (e.g. tags grouped by kind) is merged."""
        v = self.domain.get(key)
        if isinstance(v, dict):
            out = set()
            for x in v.values():
                out |= set(x) if isinstance(x, dict) else set(as_list(x))
            return out
        return set(as_list(v))

    def quantities(self):
        return self.domain.get("quantities") or {}

    def records(self):
        recs = {}
        for f in sorted(self.rec.glob("*.yaml")):
            try:
                r = yaml.safe_load(f.read_text()) or {}
            except yaml.YAMLError as e:  # one broken card must not stop the build
                print(f"SKIP {f.name}: YAML error — {str(e).splitlines()[0]}")
                continue
            r.setdefault("id", f.stem)
            recs[r["id"]] = r
        return recs

    def text(self, sha) -> str:
        p = self.txt / f"{sha}.txt"
        return p.read_text(errors="ignore") if p.exists() else ""

    def pdf_dirs(self):
        """Folders to scan (relative to root); none listed = the inbox of this base."""
        dirs = as_list(self.project.get("pdf_dirs"))
        return [self.root / p if not Path(p).is_absolute() else Path(p) for p in dirs] or [self.dir / "inbox"]


def find_kb(arg):
    if arg:
        return Path(arg)
    here = Path.cwd()
    for p in [here, *here.parents]:
        if (p / "project.yaml").exists() and (p / "domain.yaml").exists():
            return p
    if (here / "paperkb" / "project.yaml").exists():
        return here / "paperkb"
    sys.exit("No knowledge base found. Run `kb.py init <dir>` or pass --kb <dir>.")


# ----------------------------------------------------------------------------- init
def cmd_init(target: Path, domain: str):
    target.mkdir(parents=True, exist_ok=True)
    tpl = SKILL_DIR / "templates"
    dom = tpl / "domains" / f"{domain}.yaml"
    if not dom.exists():
        names = ", ".join(p.stem for p in (tpl / "domains").glob("*.yaml"))
        sys.exit(f"Unknown domain template '{domain}'. Available: {names}")
    for sub in ("records", "inbox", "figures", "notes", "tables", "_cache/text", "_cache/openalex"):
        (target / sub).mkdir(parents=True, exist_ok=True)
    for src, dst in ((tpl / "project.yaml", target / "project.yaml"), (dom, target / "domain.yaml")):
        if dst.exists():
            print(f"keep existing {dst.name}")
        else:
            shutil.copy(src, dst)
            print(f"created {dst}")
    man = target / "relations_manual.csv"
    if not man.exists():
        man.write_text("a,b,type,note\n")
    gi = target / ".gitignore"
    if not gi.exists():
        gi.write_text("_cache/\ninbox/*.pdf\n")
    print(f"\nKnowledge base ready in {target}. Put PDFs into {target / 'inbox'} (or list folders in project.yaml → pdf_dirs).")


# ----------------------------------------------------------------------------- ingest + text
def extract_text(kb, pdf: Path, sha: str) -> str:
    try:
        import pymupdf
    except ImportError:
        import fitz as pymupdf
    kb.txt.mkdir(parents=True, exist_ok=True)
    out = kb.txt / f"{sha}.txt"
    if not out.exists():
        doc = pymupdf.open(pdf)
        out.write_text("\n".join(f"\n=== page {i + 1} ===\n" + pg.get_text() for i, pg in enumerate(doc)))
    return out.read_text(errors="ignore")


def find_doi(text: str) -> str:
    """The paper's own DOI is normally the first one on pages 1–2."""
    head = text[: text.find("=== page 3 ===")] if "=== page 3 ===" in text else text[:20000]
    for m in re.finditer(r"10\.\d{4,9}/[^\s\"<>,;]+", head):
        d = m.group(0).rstrip(".)]")
        if "x0xx" not in d:
            return d
    return ""


def cmd_ingest(kb):
    recs = kb.records()
    known = {r.get("sha") for r in recs.values()}
    known |= {x.get("sha") for r in recs.values() for x in as_list(r.get("supplementary")) if isinstance(x, dict)}
    known_paths = {p for r in recs.values() for p in as_list(r.get("also_at")) if isinstance(p, str)}
    new, seen = [], set()
    for d in kb.pdf_dirs():
        if not d.exists():
            print(f"(folder not found: {d})")
            continue
        for pdf in sorted(d.rglob("*.pdf")):
            rel = str(pdf.relative_to(kb.root)) if pdf.is_relative_to(kb.root) else str(pdf)
            if rel in known_paths:
                continue
            h = sha10(pdf)
            if h in known or h in seen:
                continue
            seen.add(h)
            try:
                t = extract_text(kb, pdf, h)
            except Exception as e:
                print(f"ERR  {rel}: {e}")
                continue
            words = len(t.split())
            new.append({"sha": h, "file": rel, "doi": find_doi(t), "pages": t.count("=== page "),
                        "text_layer": "ok" if words > 200 else "MISSING (scan? needs OCR)",
                        "head": re.sub(r"\s+", " ", t[:300])})
    (kb.dir / "_cache" / "new_pdfs.json").write_text(json.dumps(new, indent=1, ensure_ascii=False))
    print(f"{len(new)} new PDF(s)")
    for n in new:
        print(f"- {n['sha']}  {n['file']}  doi={n['doi'] or '—'}  pages={n['pages']}  text={n['text_layer']}")
    if new:
        print("\nNext: `kb.py stub <sha>` for each (bibliography from OpenAlex), then fill the brief fields.")
    return new


def cmd_peek(kb, key, what):
    recs = kb.records()
    sha = recs[key]["sha"] if key in recs else key
    t = kb.text(sha)
    if not t:
        sys.exit(f"No cached text for {key}. Run ingest first.")
    if what == "head":
        print(t[:4000])
    elif what.startswith("page:"):
        n = int(what[5:])
        m = re.search(rf"=== page {n} ===(.*?)(?:\n=== page {n + 1} ===|\Z)", t, re.S)
        print(m.group(1) if m else "no such page")
    elif what.startswith("grep:"):
        rx = re.compile(what[5:], re.I)
        page = 0
        for line in t.splitlines():
            m = re.match(r"=== page (\d+) ===", line)
            if m:
                page = int(m.group(1))
            elif rx.search(line):
                print(f"p{page}: {line.strip()[:220]}")
    elif what == "nums":  # lines with a number followed by a unit-like token
        page = 0
        rx = re.compile(r"\d[\d.,]*\s?(?:[µumnkMG]?(?:Pa|m|S|Ω|ohm|F|V|A|g|L|s|Hz|N|J|W)\b|%|°C|wt|mol|mg|mL)")
        for line in t.splitlines():
            m = re.match(r"=== page (\d+) ===", line)
            if m:
                page = int(m.group(1))
            elif rx.search(line):
                print(f"p{page}: {line.strip()[:220]}")
    else:
        sys.exit("what = head | page:N | grep:REGEX | nums")


# ----------------------------------------------------------------------------- stub (bibliography from OpenAlex)
def openalex_work(kb, doi):
    cache = kb.oa / "works.json"
    data = json.loads(cache.read_text()) if cache.exists() else {}
    key = doi.lower()
    if key not in data:
        url = ("https://api.openalex.org/works/https://doi.org/" + urllib.parse.quote(doi, safe="/")
               + ("?mailto=" + kb.email if kb.email else ""))
        data[key] = http_json(url, kb.email)
        kb.oa.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(data, ensure_ascii=False))
    return data[key]


def new_id(kb, surname, year):
    base = re.sub(r"[^A-Za-z]", "", unicodedata.normalize("NFKD", surname).encode("ascii", "ignore").decode())
    base = (base[:1].upper() + base[1:]) or "Paper"
    rid = f"{base}{year or ''}"
    if not (kb.rec / f"{rid}.yaml").exists():
        return rid
    for s in "abcdefghijklmnopqrstuvwxyz":
        if not (kb.rec / f"{rid}{s}.yaml").exists():
            return rid + s
    return rid + "_x"


def cmd_stub(kb, sha, rid=None):
    newp = json.loads((kb.dir / "_cache" / "new_pdfs.json").read_text()) if (kb.dir / "_cache" / "new_pdfs.json").exists() else []
    entry = next((n for n in newp if n["sha"] == sha), None)
    if not entry:
        sys.exit(f"{sha} is not in the last ingest list.")
    w = openalex_work(kb, entry["doi"]) if entry["doi"] else None
    rec = {"id": None, "status": "brief", "file": entry["file"], "sha": sha, "doi": entry["doi"] or "not found"}
    if w:
        auth = []
        for a in w.get("authorships") or []:
            nm = (a.get("author") or {}).get("display_name") or ""
            parts = nm.split()
            auth.append(f"{parts[-1]}, {' '.join(parts[:-1])}" if len(parts) > 1 else nm)
        corr = [auth[i] for i, a in enumerate(w.get("authorships") or []) if a.get("is_corresponding") and i < len(auth)]
        src = ((w.get("primary_location") or {}).get("source") or {})
        inst = next(((a.get("institutions") or [{}])[0] for a in (w.get("authorships") or [])
                     if a.get("is_corresponding") and a.get("institutions")), {})
        rec.update({"title": w.get("title") or w.get("display_name"), "year": w.get("publication_year"),
                    "journal": src.get("display_name") or "", "authors": auth, "corresponding": corr,
                    "institution": inst.get("display_name", ""), "country": inst.get("country_code", "")})
        surname = auth[0].split(",")[0] if auth else "Paper"
    else:
        rec.update({"title": "", "year": None, "journal": "", "authors": [], "corresponding": []})
        surname = "Paper"
        print("No OpenAlex record — fill the bibliography from page 1 of the PDF.")
    # no bibliography -> placeholder ID; rename the file to Surname<Year>.yaml once page 1 is read
    rec["id"] = rid or (new_id(kb, surname, rec.get("year")) if w else f"New_{sha}")
    rec.update({"lab": "", "category": "", "object_type": "", "topics": [], "summary": "",
                "focus": {"text": ""}, "relevance": "", "key_findings": []})
    kb.rec.mkdir(exist_ok=True)
    out = kb.rec / f"{rec['id']}.yaml"
    if out.exists():
        sys.exit(f"{out.name} already exists — pass --id.")
    out.write_text(yaml.safe_dump(rec, sort_keys=False, allow_unicode=True, width=120))
    print(f"created {out.relative_to(kb.dir)}  ({rec.get('title') or 'no title'})")


# ----------------------------------------------------------------------------- figures
def _graphics_union(pg, y_max=None):
    import pymupdf
    H = pg.rect.height
    rects = [pymupdf.Rect(x["bbox"]) for x in pg.get_image_info()]
    rects += [d["rect"] for d in pg.get_drawings() if d["rect"].width > 3 and d["rect"].height > 3]
    rects = [q for q in rects if q.y0 > 0.05 * H and q.y1 < 0.97 * H and 50 < q.get_area() < 0.95 * pg.rect.get_area()
             and (y_max is None or q.y1 <= y_max + 3)]
    if not rects:
        return None
    u = pymupdf.Rect(rects[0])
    for q in rects[1:]:
        u |= q
    return u


def fig_path(kb, rid):
    """A hand-made figures/<ID>_manual.png always wins over the automatic thumbnail."""
    for ext in ("png", "jpg", "jpeg"):
        m = kb.fig / f"{rid}_manual.{ext}"
        if m.exists():
            return m
    return kb.fig / f"{rid}.png"


def make_thumb(kb, r, force=False):
    """Thumbnail of Fig. 1 (graphics above its caption) -> figures/<ID>.png, 900 px wide."""
    import pymupdf
    kb.fig.mkdir(exist_ok=True)
    if fig_path(kb, r["id"]).name != f"{r['id']}.png":
        return fig_path(kb, r["id"])
    out = kb.fig / f"{r['id']}.png"
    fcfg = r.get("figure") or {}
    if out.exists() and (fcfg.get("locked") or not force):
        return out
    pdf = kb.root / str(r.get("file", ""))
    if not r.get("file") or not pdf.exists():
        return None
    doc = pymupdf.open(pdf)
    page = clip = None
    if fcfg.get("page"):
        page = doc[int(fcfg["page"]) - 1]
        clip = pymupdf.Rect(fcfg["clip"]) if fcfg.get("clip") else page.rect
    else:
        for i in range(min(8, len(doc))):
            pg = doc[i]
            cap = next((pymupdf.Rect(b[:4]) for b in pg.get_text("blocks")
                        if re.match(r"\s*(fig\.?|figure)\s*1(?![0-9])\s*[.:|,\s]", b[4], re.I) and len(b[4]) > 25), None)
            if not cap:
                continue
            for u in (_graphics_union(pg, y_max=cap.y0), _graphics_union(pg)):
                if u is not None and u.get_area() > 0.10 * pg.rect.get_area():
                    page, clip = pg, u
                    break
            if page is not None:
                break
        if page is None:
            best = (0, None, None)
            for i in range(min(4, len(doc))):
                u = _graphics_union(doc[i])
                if u is not None and u.get_area() > max(best[0], 0.10 * doc[i].rect.get_area()):
                    best = (u.get_area(), doc[i], u)
            page, clip = best[1], best[2]
        if page is None:
            page = doc[0]
            clip = pymupdf.Rect(0, 0, page.rect.width, page.rect.height / 2)
    zoom = 900 / max(clip.width, 1)
    out.write_bytes(page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip, alpha=False).tobytes("png"))
    return out


def cmd_figures(kb, force=False):
    for r in kb.records().values():
        try:
            print(("ok   " if make_thumb(kb, r, force) else "MISS ") + r["id"])
        except Exception as e:  # never stop the batch for one bad PDF
            print("ERR ", r["id"], e)


# ----------------------------------------------------------------------------- check
def cmd_check(kb, quiet=False):
    recs = kb.records()
    warn, newv = [], []
    cats = set(kb.domain.get("categories") or [])
    tags = kb.vocab("tags")
    qty = kb.quantities()
    roles, ents = kb.vocab("element_roles"), kb.vocab("environment_entities")
    lmeth = set(kb.domain.get("link_methods") or {})
    funcs = kb.vocab("functions")
    pmeth = kb.vocab("preparation_methods")
    levels, ttypes = set(kb.domain.get("test_levels") or []), set(kb.domain.get("test_types") or [])
    otypes = set(kb.domain.get("object_types") or {})
    lens = kb.domain.get("lenses") or {}
    dois = defaultdict(list)

    def W(rid, msg):
        warn.append(f"{rid}: {msg}")

    def NV(rid, kind, term):
        newv.append((kind, str(term), rid))

    def items(r, sec):
        out = []
        for i, x in enumerate(as_list(r.get(sec))):
            if not isinstance(x, dict):
                W(r["id"], f"{sec}[{i}] is not a mapping")
                continue
            extra = set(x) - KEYS[sec]
            if extra:
                W(r["id"], f"{sec}[{i}] unknown keys {sorted(extra)}")
            out.append(x)
        return out

    for rid, r in recs.items():
        if set(r) - TOP_KEYS:
            W(rid, f"unknown top-level fields {sorted(set(r) - TOP_KEYS)} (allowed, but not rendered)")
        st = r.get("status")
        if st not in STATUSES:
            W(rid, f"status '{st}' not in {STATUSES}")
        for k in ("title", "year", "category", "summary", "relevance"):
            if not r.get(k):
                W(rid, f"missing {k}")
        if r.get("doi") and r["doi"] != "not found":
            dois[str(r["doi"]).lower()].append(rid)
        if cats and r.get("category") and r["category"] not in cats:
            NV(rid, "category", r["category"])
        if otypes and r.get("object_type") and r["object_type"] not in otypes:
            NV(rid, "object_type", r["object_type"])
        if r.get("relevance") and r["relevance"] not in RELEVANCE:
            W(rid, f"relevance '{r['relevance']}' not in {RELEVANCE}")
        for t in as_list(r.get("topics")):
            if tags and t not in tags:
                NV(rid, "tag", t)
        if r.get("file") and not (kb.root / str(r["file"])).exists():
            W(rid, f"PDF not found: {r['file']}")
        # ---- object deconstruction
        els = items(r, "elements")
        eids = [e.get("id") for e in els]
        if len(eids) != len(set(eids)):
            W(rid, "duplicate element ids")
        for e in els:
            if not e.get("id") or not e.get("name"):
                W(rid, "element without id or name")
            if e.get("parent") and e["parent"] not in eids:
                W(rid, f"element {e.get('id')}: parent '{e['parent']}' not found")
            if e.get("kind") and e["kind"] not in ELEMENT_KINDS:
                W(rid, f"element {e.get('id')}: kind '{e['kind']}' not in {ELEMENT_KINDS}")
            if roles and e.get("role") and e["role"] not in roles:
                NV(rid, "element_role", e["role"])
            p = e.get("preparation")
            if isinstance(p, dict):
                if set(p) - KEYS["preparation"]:
                    W(rid, f"element {e.get('id')}: preparation unknown keys {sorted(set(p) - KEYS['preparation'])}")
                if p.get("key") and pmeth and p.get("method") and p["method"] not in pmeth:
                    NV(rid, "preparation_method", p["method"])
                if p.get("key") and not p.get("page"):
                    W(rid, f"element {e.get('id')}: key preparation without page")
        for f in items(r, "functions"):
            if funcs and f.get("function") and f["function"] not in funcs:
                NV(rid, "function", f["function"])
            for pb in as_list(f.get("performed_by")):
                if pb not in eids:
                    W(rid, f"function '{f.get('function')}': performed_by '{pb}' not an element id")
        for l in items(r, "links"):
            for end in ("a", "b"):
                if l.get(end) not in eids:
                    W(rid, f"link {l.get('a')}–{l.get('b')}: '{l.get(end)}' not an element id")
            if l.get("class") not in LINK_CLASSES:
                W(rid, f"link {l.get('a')}–{l.get('b')}: class '{l.get('class')}' not in {LINK_CLASSES}")
            if lmeth and l.get("method") and l["method"] not in lmeth:
                NV(rid, "link_method", l["method"])
            if l.get("outcome") and l["outcome"] not in OUTCOMES:
                W(rid, f"link outcome '{l['outcome']}' not in {OUTCOMES}")
        for it in items(r, "interactions"):
            if it.get("element") and it["element"] not in eids:
                W(rid, f"interaction: element '{it['element']}' not found")
            if ents and it.get("entity") and it["entity"] not in ents:
                NV(rid, "environment_entity", it["entity"])
        # ---- tests, metrics, protocols, lenses
        tests = items(r, "tests")
        for t in tests:
            if levels and t.get("level") not in levels:
                W(rid, f"test '{t.get('name')}': level '{t.get('level')}' not in {sorted(levels)}")
            if ttypes and t.get("type") and t["type"] not in ttypes:
                NV(rid, "test_type", t["type"])
        for m in items(r, "metrics"):
            q = m.get("quantity")
            if qty and q not in qty:
                NV(rid, "quantity", q)
            elif qty and qty[q] != "text" and m.get("unit") != qty[q]:
                W(rid, f"metric {q}: unit '{m.get('unit')}' should be '{qty[q]}' (convert)")
            if not m.get("page"):
                W(rid, f"metric {q}: no page")
            if m.get("function") and not fn_of(r, m["function"]):
                W(rid, f"metric {q}: function '{m['function']}' is neither a function id nor a function of this card")
            if m.get("value_type") and m["value_type"] not in VALUE_TYPES:
                W(rid, f"metric {q}: value_type '{m['value_type']}' not in {VALUE_TYPES}")
        for p in items(r, "protocols"):
            miss = [k for k in PROTO_REQUIRED if not p.get(k)]
            if miss:
                W(rid, f"protocol '{p.get('name')}': missing {miss}")
        items(r, "design_rules"); items(r, "process_window"); items(r, "builds_on")
        if isinstance(r.get("review_map"), dict) and set(r["review_map"]) - REVIEW_KEYS:
            W(rid, f"review_map unknown keys {sorted(set(r['review_map']) - REVIEW_KEYS)}")
        if isinstance(r.get("transfer"), dict) and set(r["transfer"]) - TRANSFER_KEYS:
            W(rid, f"transfer unknown keys {sorted(set(r['transfer']) - TRANSFER_KEYS)}")
        if st == "verified":
            if not r.get("key_findings"):
                W(rid, "verified card without key_findings")
            if not tests and r.get("category") not in ("review",):
                W(rid, "verified card without tests")
            want = lens.get(r.get("category"))
            if want and not r.get(want):
                W(rid, f"verified {r.get('category')} card without its lens '{want}'")
            if r.get("object_type") and not els and r.get("category") not in ("review",):
                W(rid, "verified card with object_type but no elements (object deconstruction)")
    for d, ids in dois.items():
        if len(ids) > 1:
            warn.append(f"DUPLICATE DOI {d}: {ids}")
    grouped = defaultdict(set)   # (kind, term) -> cards using it
    for kind, term, rid in newv:
        grouped[(kind, term)].add(rid)
    nv = [f"NEW-VOCAB {k}: '{t}' — {len(ids)} card(s): {', '.join(sorted(ids)[:6])}{' …' if len(ids) > 6 else ''}"
          for (k, t), ids in sorted(grouped.items(), key=lambda x: (x[0][0], -len(x[1]), x[0][1]))]
    if not quiet:
        for w in warn + nv:
            print(w)
        print(f"\n{len(recs)} cards · {len(warn)} warnings · {len(nv)} new vocabulary terms")
        if nv:
            print("NEW-VOCAB: ask the user before adding these terms to domain.yaml (or rename them to existing terms).")
    return warn, nv


# ----------------------------------------------------------------------------- relations
def compute_relations(kb, recs):
    ids = sorted(recs)
    texts = {i: kb.text(recs[i].get("sha", "")).lower() for i in ids}
    ntexts = {i: norm(t) for i, t in texts.items()}
    rows = []
    for ai, a in enumerate(ids):
        A = recs[a]
        for b in ids[ai + 1:]:
            B = recs[b]
            if A.get("lab") and A.get("lab") == B.get("lab"):
                rows.append((a, b, "same_lab", A["lab"]))
            common = {author_key(x) for x in as_list(A.get("authors"))} & {author_key(x) for x in as_list(B.get("authors"))}
            if common:
                rows.append((a, b, "shared_author", "; ".join(x for x in as_list(B.get("authors")) if author_key(x) in common)))
        for b in ids:
            if b == a:
                continue
            doi = str(recs[b].get("doi") or "").lower()
            tn = norm(recs[b].get("title"))[:60]
            if (len(doi) > 8 and doi in texts[a] and doi != str(A.get("doi") or "").lower()) or (len(tn) >= 40 and tn in ntexts[a]):
                rows.append((a, b, "cites", ""))
    for b in ids:
        for x in as_list(recs[b].get("builds_on")):
            if isinstance(x, dict) and x.get("id") in recs:
                rows.append((x["id"], b, "follow_up", x.get("what", "")))
    man = kb.dir / "relations_manual.csv"
    if man.exists():
        for row in csv.DictReader(man.open()):
            if row.get("a") in recs and row.get("b") in recs:
                rows.append((row["a"], row["b"], row.get("type") or "manual", row.get("note") or ""))
    return rows


# ----------------------------------------------------------------------------- focus sources (for journals and overviews)
def focus_of(kb, r):
    """Paper focus from three sources: auto (card), folder (where the PDF lies), keywords (project.yaml)."""
    auto = r.get("category") or ""
    if r.get("object_type"):
        auto += f" / {r['object_type']}"
    folder = ""
    if r.get("file"):
        parent = Path(str(r["file"])).parent.name
        ignore = set(as_list(kb.project.get("folder_focus_ignore") or ["inbox"]))
        if parent and parent not in ignore:
            folder = (kb.project.get("folder_focus") or {}).get(parent, parent)
    hay = " ".join(str(x) for x in [r.get("title"), r.get("summary"), *as_list(r.get("topics"))]).lower()
    kws = [label for label, words in (kb.project.get("focus_keywords") or {}).items()
           if any(str(w).lower() in hay for w in as_list(words))]
    return auto, folder, kws


# ----------------------------------------------------------------------------- journals
def norm_issn(s):
    return re.sub(r"[^0-9X]", "", str(s or "").upper())


def load_ranks(kb):
    """Optional rank files in the kb folder: journal_ranks.csv (journal/issn, quartile, impact_factor, note)
    and/or a Scimago export scimagojr*.csv. Returns {key: {...}} keyed by ISSN and lower-case title."""
    ranks = {}
    p = kb.dir / "journal_ranks.csv"
    if p.exists():
        for row in csv.DictReader(p.open(encoding="utf-8-sig")):
            for k in [norm_issn(x) for x in str(row.get("issn", "")).split(",") if x.strip()] + [norm(row.get("journal"))]:
                if k:
                    ranks.setdefault(k, {}).update({x: row[x] for x in ("quartile", "impact_factor", "note") if row.get(x)})
    for sj in kb.dir.glob("scimagojr*.csv"):
        for row in csv.DictReader(sj.open(encoding="utf-8-sig"), delimiter=";"):
            info = {"quartile": row.get("SJR Best Quartile", ""), "sjr": row.get("SJR", "")}
            for k in [norm_issn(x) for x in str(row.get("Issn", "")).split(",")] + [norm(row.get("Title"))]:
                if k:
                    ranks.setdefault(k, {}).update({a: b for a, b in info.items() if b})
    return ranks


def journal_table(kb, recs, fetch=True):
    """One row per journal: papers in the base, years, focus, status (OA/DOAJ/APC), rank (OpenAlex, SJR, IF)."""
    srcache_p = kb.oa / "sources.json"
    srcache = json.loads(srcache_p.read_text()) if srcache_p.exists() else {}
    works = {}
    wc = kb.oa / "works.json"
    wcache = json.loads(wc.read_text()) if (wc.exists() and not fetch) else {}
    for r in recs.values():
        doi = str(r.get("doi") or "")
        if doi.startswith("10."):
            works[r["id"]] = openalex_work(kb, doi) if fetch else wcache.get(doi.lower())
    for w in works.values():
        sid = (((w or {}).get("primary_location") or {}).get("source") or {}).get("id")
        if sid and fetch and sid not in srcache:
            short = sid.rsplit("/", 1)[-1]
            srcache[sid] = http_json(f"https://api.openalex.org/sources/{short}" + (f"?mailto={kb.email}" if kb.email else ""), kb.email)
    kb.oa.mkdir(parents=True, exist_ok=True)
    srcache_p.write_text(json.dumps(srcache, ensure_ascii=False))
    ranks = load_ranks(kb)
    J = {}
    this_year = datetime.date.today().year
    recent = int(kb.project.get("recent_years", 3))
    for rid, r in recs.items():
        w = works.get(rid) or {}
        src = ((w.get("primary_location") or {}).get("source") or {})
        s = srcache.get(src.get("id")) or {}
        name = s.get("display_name") or src.get("display_name") or str(r.get("journal") or "").strip() or "(unknown)"
        j = J.setdefault(norm(name), {"journal": name, "papers": [], "years": [], "high": 0, "recent": 0,
                                      "auto": Counter(), "folder": Counter(), "keywords": Counter(), "cited": [],
                                      "src": s, "retracted": []})
        j["papers"].append(rid)
        if r.get("year"):
            j["years"].append(int(r["year"]))
            if int(r["year"]) >= this_year - recent + 1:
                j["recent"] += 1
        j["high"] += r.get("relevance") == "high"
        a, f, k = focus_of(kb, r)
        j["auto"][a or "?"] += 1
        if f:
            j["folder"][f] += 1
        for x in k:
            j["keywords"][x] += 1
        if w.get("cited_by_count") is not None:
            j["cited"].append(w["cited_by_count"])
        if w.get("is_retracted"):
            j["retracted"].append(rid)
    rows = []
    for j in J.values():
        s = j["src"]
        ss = s.get("summary_stats") or {}
        rk = {}
        for k in [norm_issn(x) for x in as_list(s.get("issn"))] + [norm(j["journal"])]:
            if k in ranks:
                rk = {**ranks[k], **rk}
        if s.get("type") == "repository":
            status = "preprint server / repository"
        elif s.get("is_in_doaj") or s.get("is_oa"):
            status = "fully open access" + (" (DOAJ)" if s.get("is_in_doaj") else "")
        elif s:
            status = "subscription or hybrid"
        else:
            status = "unknown (no DOI / not in OpenAlex)"
        ys = sorted(j["years"])
        rows.append({
            "journal": j["journal"], "n_papers": len(j["papers"]), "high_relevance": j["high"],
            "recent": j["recent"], "first_year": ys[0] if ys else "", "last_year": ys[-1] if ys else "",
            "years": ", ".join(f"{y}×{c}" if c > 1 else str(y) for y, c in sorted(Counter(ys).items())),
            "focus_auto": ", ".join(f"{k} ({v})" for k, v in j["auto"].most_common()),
            "focus_folder": ", ".join(f"{k} ({v})" for k, v in j["folder"].most_common()),
            "focus_keywords": ", ".join(f"{k} ({v})" for k, v in j["keywords"].most_common()),
            "publisher": s.get("host_organization_name") or "", "status": status,
            "apc_usd": s.get("apc_usd") or "", "issn_l": s.get("issn_l") or "",
            "openalex_2yr_mean_citedness": round(ss.get("2yr_mean_citedness"), 2) if ss.get("2yr_mean_citedness") else "",
            "openalex_h_index": ss.get("h_index") or "",
            "sjr_quartile": rk.get("quartile", ""), "sjr": rk.get("sjr", ""), "impact_factor": rk.get("impact_factor", ""),
            "median_citations_of_these_papers": sorted(j["cited"])[len(j["cited"]) // 2] if j["cited"] else "",
            "retracted_papers": ", ".join(j["retracted"]), "papers": ", ".join(sorted(j["papers"])),
        })
    rows.sort(key=lambda x: (-x["n_papers"], x["journal"]))
    return rows


def cmd_journals(kb, fetch=True):
    recs = kb.records()
    rows = journal_table(kb, recs, fetch)
    kb.tab.mkdir(exist_ok=True)
    write_csv(kb.tab / "journals.csv", rows)
    print(f"{len(rows)} journals from {len(recs)} cards → tables/journals.csv (notes/Journals.md on next build)")
    for r in rows[:15]:
        print(f"{r['n_papers']:>3}  {r['journal'][:50]:50}  {r['status'][:28]:28}  2yr={r['openalex_2yr_mean_citedness']}  Q={r['sjr_quartile']}")
    return rows


# ----------------------------------------------------------------------------- tables
def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: cell(v).replace("\\|", "|") if isinstance(v, (list, dict)) else v for k, v in r.items()})


def ename(r, eid):
    e = next((x for x in as_list(r.get("elements")) if isinstance(x, dict) and x.get("id") == eid), {})
    return e.get("name") or eid or ""


def build_tables(kb, recs):
    T = defaultdict(list)
    for rid, r in sorted(recs.items()):
        a, f, k = focus_of(kb, r)
        T["papers"].append({"id": rid, "status": r.get("status"), "year": r.get("year"), "journal": r.get("journal"),
                            "category": r.get("category"), "object_type": r.get("object_type"),
                            "relevance": r.get("relevance"), "topics": as_list(r.get("topics")), "lab": r.get("lab"),
                            "title": r.get("title"), "summary": r.get("summary"), "doi": r.get("doi"),
                            "focus_folder": f, "focus_keywords": k, "file": r.get("file")})
        for sec in ("tests", "metrics", "protocols", "design_rules", "process_window", "functions", "interactions"):
            for x in as_list(r.get(sec)):
                if isinstance(x, dict):
                    T[sec].append({"paper": rid, "year": r.get("year"), **x})
        for e in as_list(r.get("elements")):
            if isinstance(e, dict):
                p = e.get("preparation") or {}
                T["elements"].append({"paper": rid, **{k2: v for k2, v in e.items() if k2 != "preparation"},
                                      "prep_method": p.get("method") if isinstance(p, dict) else p,
                                      "prep_key": p.get("key") if isinstance(p, dict) else "",
                                      "prep_parameters": p.get("parameters") if isinstance(p, dict) else ""})
        for l in as_list(r.get("links")):
            if isinstance(l, dict):
                T["links"].append({"paper": rid, "a_name": ename(r, l.get("a")), "b_name": ename(r, l.get("b")), **l})
    T["relations"] = [{"a": a, "b": b, "type": t, "note": n} for a, b, t, n in compute_relations(kb, recs)]
    for name, rows in T.items():
        write_csv(kb.tab / f"{name}.csv", rows)
    return T


def build_xlsx(kb, T, journals):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font
    except ImportError:
        print("(openpyxl missing — no xlsx)")
        return
    wb = Workbook()
    wb.remove(wb.active)
    sheets = [("Papers", T.get("papers")), ("Journals", journals), ("Elements", T.get("elements")),
              ("Functions", T.get("functions")), ("Links", T.get("links")), ("Interactions", T.get("interactions")),
              ("Tests", T.get("tests")), ("Metrics", T.get("metrics")), ("Protocols", T.get("protocols")),
              ("Design rules", T.get("design_rules")), ("Process windows", T.get("process_window")),
              ("Relations", T.get("relations"))]
    for title, rows in sheets:
        if not rows:
            continue
        ws = wb.create_sheet(title)
        keys = list(dict.fromkeys(k for r in rows for k in r))
        ws.append(keys)
        for c in ws[1]:
            c.font = Font(bold=True)
        for r in rows:
            ws.append([cell(r.get(k)).replace("\\|", "|") if isinstance(r.get(k), (list, dict)) else r.get(k) for k in keys])
        ws.freeze_panes = "B2"
        ws.auto_filter.ref = ws.dimensions
        for col in ws.columns:
            width = min(60, max(10, max(len(str(c.value or "")) for c in col[:200]) + 2))
            ws.column_dimensions[col[0].column_letter].width = width
            for c in col[1:]:
                c.alignment = Alignment(wrap_text=width >= 60, vertical="top")
    if wb.sheetnames:  # an empty base has nothing to write
        wb.save(kb.dir / "knowledge_base.xlsx")


# ----------------------------------------------------------------------------- plots
def build_plots(kb, recs, journals):
    """PNG plots embedded in the notes. Only comparable points: same quantity, numeric value, the unit of domain.yaml.
    Value-by-year scatter plots are drawn only with `project.yaml → plots: {by_year: true}`: the year rarely explains
    a difference in a quantity; comparisons by solution variant are on the function pages (result_plot)."""
    by_year = bool((kb.project.get("plots") or {}).get("by_year"))
    if kb.no_plots:
        P = kb.notes / "plots"
        made = {"_skipped": {}}
        for q in kb.quantities():
            if by_year and (P / f"plot_metric_{slug(q)}.png").exists():
                made[("metric", q)] = f"plot_metric_{slug(q)}.png"
        for pair in as_list(kb.domain.get("plot_pairs")):
            if isinstance(pair, list) and len(pair) == 2 and (P / f"plot_map_{slug(pair[0])}_vs_{slug(pair[1])}.png").exists():
                made[("map", *pair)] = f"plot_map_{slug(pair[0])}_vs_{slug(pair[1])}.png"
        for k in ("journals_counts", "journals_years"):
            if (P / f"plot_{k}.png").exists():
                made[k] = f"plot_{k}.png"
        return made
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("(matplotlib missing — no plots)")
        return {}
    out = kb.notes / "plots"
    out.mkdir(parents=True, exist_ok=True)
    qty = kb.quantities()
    logq = set(as_list(kb.domain.get("log_quantities")))
    cats = sorted({r.get("category") or "?" for r in recs.values()})
    cmap = plt.get_cmap("tab10")
    color = {c: cmap(i % 10) for i, c in enumerate(cats)}
    made = {}
    pts = defaultdict(list)       # quantity -> [(year, value, id, category, from_figure, condition)]
    skipped = defaultdict(list)   # quantity -> [(id, reason)]
    for rid, r in recs.items():
        for m in as_list(r.get("metrics")):
            if not isinstance(m, dict) or m.get("quantity") not in qty or qty[m["quantity"]] == "text":
                continue
            q, v = m["quantity"], num(m.get("value"))
            if v is None:
                skipped[q].append((rid, f"value '{m.get('value')}' is not a single number"))
            elif m.get("unit") != qty[q]:
                skipped[q].append((rid, f"unit {m.get('unit')} ≠ {qty[q]}"))
            elif not r.get("year"):
                skipped[q].append((rid, "no year"))
            else:
                pts[q].append((int(r["year"]), v, rid, r.get("category") or "?", bool(m.get("from_figure")), m.get("condition", "")))
    for q, P in (pts.items() if by_year else []):
        fig, ax = plt.subplots(figsize=(7, 4.2))
        for c in cats:
            sub = [p for p in P if p[3] == c]
            if not sub:
                continue
            for hollow in (False, True):
                s2 = [p for p in sub if p[4] == hollow]
                if s2:
                    ax.scatter([p[0] for p in s2], [p[1] for p in s2], s=40, label=c if not hollow else None,
                               facecolors="none" if hollow else color[c], edgecolors=color[c], linewidths=1.2)
        for p in P:
            ax.annotate(p[2], (p[0], p[1]), fontsize=6, xytext=(3, 2), textcoords="offset points", alpha=0.8)
        vals = [p[1] for p in P if p[1] > 0]
        if q in logq or (vals and len(vals) == len(P) and max(vals) / min(vals) > 100):
            ax.set_yscale("log")
        ax.set_xlabel("Year")
        ax.set_ylabel(f"{q} ({qty[q]})")
        ax.set_title(f"{q} reported in the knowledge base (n = {len(P)})", fontsize=10)
        ax.legend(fontsize=7, frameon=False, title="category", title_fontsize=7)
        ax.grid(alpha=0.25)
        fig.text(0.01, 0.01, "Hollow markers: values read from figures. Conditions differ between papers — see table.",
                 fontsize=6, alpha=0.7)
        fig.tight_layout()
        name = f"plot_metric_{slug(q)}.png"
        fig.savefig(out / name, dpi=150)
        plt.close(fig)
        made[("metric", q)] = name
    # property maps (pairs from domain.yaml): one point per paper = first value of each quantity in that paper
    for pair in as_list(kb.domain.get("plot_pairs")):
        if not isinstance(pair, list) or len(pair) != 2:
            continue
        x, y = pair
        P = []
        for rid, r in recs.items():
            vx = next((num(m.get("value")) for m in as_list(r.get("metrics")) if isinstance(m, dict)
                       and m.get("quantity") == x and m.get("unit") == qty.get(x) and num(m.get("value")) is not None), None)
            vy = next((num(m.get("value")) for m in as_list(r.get("metrics")) if isinstance(m, dict)
                       and m.get("quantity") == y and m.get("unit") == qty.get(y) and num(m.get("value")) is not None), None)
            if vx is not None and vy is not None:
                P.append((vx, vy, rid, r.get("category") or "?"))
        if len(P) < 2:
            continue
        fig, ax = plt.subplots(figsize=(6, 5))
        for c in cats:
            s2 = [p for p in P if p[3] == c]
            if s2:
                ax.scatter([p[0] for p in s2], [p[1] for p in s2], s=40, color=color[c], label=c)
        for p in P:
            ax.annotate(p[2], (p[0], p[1]), fontsize=6, xytext=(3, 2), textcoords="offset points")
        for setter, q, vals in ((ax.set_xscale, x, [p[0] for p in P]), (ax.set_yscale, y, [p[1] for p in P])):
            if q in logq or (min(vals) > 0 and max(vals) / min(vals) > 100):
                setter("log")
        ax.set_xlabel(f"{x} ({qty.get(x)})")
        ax.set_ylabel(f"{y} ({qty.get(y)})")
        ax.set_title(f"{y} vs {x} (one point per paper, n = {len(P)})", fontsize=10)
        ax.legend(fontsize=7, frameon=False)
        ax.grid(alpha=0.25)
        fig.tight_layout()
        name = f"plot_map_{slug(x)}_vs_{slug(y)}.png"
        fig.savefig(out / name, dpi=150)
        plt.close(fig)
        made[("map", x, y)] = name
    # journals: papers per journal (stacked by category) and journal × year
    if journals:
        top = [j for j in journals if j["journal"] != "(unknown)"][:15]
        if top:
            byj = {j["journal"]: set(j["papers"].split(", ")) for j in top}
            fig, ax = plt.subplots(figsize=(7, 0.35 * len(top) + 1.2))
            left = [0] * len(top)
            for c in cats:
                vals = [sum(1 for p in byj[j["journal"]] if p in recs and (recs[p].get("category") or "?") == c) for j in top]
                if any(vals):
                    ax.barh(range(len(top)), vals, left=left, color=color[c], label=c)
                    left = [a + b for a, b in zip(left, vals)]
            ax.set_yticks(range(len(top)))
            ax.set_yticklabels([j["journal"][:45] for j in top], fontsize=7)
            ax.invert_yaxis()
            ax.set_xlabel("Papers in the knowledge base")
            ax.legend(fontsize=7, frameon=False, title="category", title_fontsize=7)
            ax.set_title("Most frequent journals", fontsize=10)
            fig.tight_layout()
            fig.savefig(out / "plot_journals_counts.png", dpi=150)
            plt.close(fig)
            made["journals_counts"] = "plot_journals_counts.png"
            years = sorted({int(recs[p]["year"]) for j in top for p in byj[j["journal"]] if p in recs and recs[p].get("year")})
            if years:
                import numpy as np
                M = np.zeros((len(top), len(years)))
                for i, j in enumerate(top):
                    for p in byj[j["journal"]]:
                        if p in recs and recs[p].get("year"):
                            M[i, years.index(int(recs[p]["year"]))] += 1
                fig, ax = plt.subplots(figsize=(max(5, 0.35 * len(years) + 3), 0.35 * len(top) + 1.4))
                im = ax.imshow(M, aspect="auto", cmap="Blues")
                ax.set_xticks(range(len(years)))
                ax.set_xticklabels(years, fontsize=7, rotation=90)
                ax.set_yticks(range(len(top)))
                ax.set_yticklabels([j["journal"][:45] for j in top], fontsize=7)
                for i in range(len(top)):
                    for k in range(len(years)):
                        if M[i, k]:
                            ax.text(k, i, int(M[i, k]), ha="center", va="center", fontsize=6,
                                    color="white" if M[i, k] > M.max() / 2 else "black")
                ax.set_title("Papers per journal and year", fontsize=10)
                fig.colorbar(im, ax=ax, shrink=0.6)
                fig.tight_layout()
                fig.savefig(out / "plot_journals_years.png", dpi=150)
                plt.close(fig)
                made["journals_years"] = "plot_journals_years.png"
    made["_skipped"] = skipped if by_year else {}
    return made


# ----------------------------------------------------------------------------- Obsidian notes
def write_note(path: Path, body: str):
    """Write a generated note; text below MARK in the old version (the user's notes) is preserved."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tail = "\n## 📝 My notes\n\n"
    if path.exists():
        old = path.read_text()
        if MARK in old:
            tail = old.split(MARK, 1)[1]
    path.write_text(body.rstrip() + "\n\n" + MARK + tail)


def L(kind, name):
    """Wiki link to a hub note, e.g. L('Topic', 'PDMS') -> [[Topic - PDMS|PDMS]]. Catch-all values ('other', 'none')
    stay plain text: a hub that collects everything unrelated would only add noise to the graph view."""
    if not name:
        return ""
    if str(name).strip().lower() in CATCH_ALL:
        return str(name)
    return f"[[{kind} - {slug(name)}|{name}]]"


# ----------------------------------------------------------------------------- hub pages as documents
FOLD_ROWS = 8   # longer tables go into a collapsed callout under the summary


def fold(title, text, collapsed=True):
    """Obsidian callout that hides a long table until clicked."""
    body = "\n".join("> " + x if x else ">" for x in text.rstrip().split("\n"))
    return f"> [!note]{'-' if collapsed else '+'} {title}\n{body}\n"


def full_table(title, head, rows):
    t = mdtable(head, rows)
    return fold(f"{title} ({len(rows)})", t) if len(rows) > FOLD_ROWS else t


def drop_empty(head, rows, keep):
    """Remove columns that are empty in every row, except the ones named in `keep`."""
    idx = [i for i, h in enumerate(head) if h in keep or any(cell(r[i]) for r in rows)]
    return [head[i] for i in idx], [[r[i] for i in idx] for r in rows]


def digest(recs, ids):
    """A few template sentences about a set of papers (written by the script, no model tokens):
    how many, which groups and years, at which level they were tested, which lines of work continue each other."""
    ids = sorted(i for i in set(ids) if i in recs)
    if not ids:
        return []
    years = sorted(int(recs[i]["year"]) for i in ids if recs[i].get("year"))
    labs = Counter(recs[i]["lab"] for i in ids if recs[i].get("lab"))
    high = sum(recs[i].get("relevance") == "high" for i in ids)
    s = (f"**{len(ids)} paper(s)**" + (f" from {len(labs)} group(s)" if labs else "")
         + (f", {years[0]}–{years[-1]}" if len(set(years)) > 1 else (f", {years[0]}" if years else ""))
         + (f"; {high} of high relevance" if high else "") + ".")
    top = [f"{L('Lab', k)} ({v})" for k, v in labs.most_common(3) if v > 1]
    if top:
        s += " Most papers: " + ", ".join(top) + "."
    out = [s]
    lv = Counter(t.get("level") for i in ids for t in as_list(recs[i].get("tests")) if isinstance(t, dict) and t.get("level"))
    ty = Counter(t.get("type") for i in ids for t in as_list(recs[i].get("tests")) if isinstance(t, dict) and t.get("type"))
    if lv:
        out.append("Tests: " + " · ".join(f"{k} {v}" for k, v in lv.most_common())
                   + (" — by type: " + ", ".join(f"{k} {v}" for k, v in ty.most_common(5)) if ty else "") + ".")
    else:
        out.append("No tests recorded on these cards (brief cards carry none).")
    chains = [f"[[{x['id']}]] → [[{i}]]" for i in ids for x in as_list(recs[i].get("builds_on"))
              if isinstance(x, dict) and x.get("id") in ids]
    if chains:
        out.append("Continues earlier work in this set: " + ", ".join(chains[:6]) + (" …" if len(chains) > 6 else "") + ".")
    return out


def key_numbers(kb, recs, ids, quantities=None, pairs=None):
    """Per quantity: n, minimum, median, maximum (with paper and page) over measured values; bounds, datasheet and
    cited values are counted apart because they are not the same kind of evidence. `pairs` = [(id, metric)] overrides."""
    qty = kb.quantities()
    if pairs is None:
        pairs = [(i, m) for i in ids for m in as_list(recs[i].get("metrics")) if isinstance(m, dict)]
    P, other = defaultdict(list), defaultdict(Counter)
    for i, m in pairs:
        q = m.get("quantity")
        if not q or (quantities and q not in quantities) or qty.get(q) == "text" or str(q).lower() in CATCH_ALL:
            continue
        v = num(m.get("value"))
        if v is None or m.get("unit") != qty.get(q):
            continue
        vt = m.get("value_type") or "measured"
        if vt == "measured":
            P[q].append((v, i, m.get("page")))
        else:
            other[q][vt] += 1
    rows = []
    for q in sorted(set(P) | set(other), key=lambda x: -len(P.get(x, []))):
        xs = sorted(P.get(q, []))
        ref = lambda x: f"{x[0]:g} ([[{x[1]}]] {x[2] or ''})".replace(" )", ")")
        rows.append([L("Quantity", q), qty.get(q), len({x[1] for x in xs}), ref(xs[0]) if xs else "",
                     f"{xs[len(xs) // 2][0]:g}" if xs else "", ref(xs[-1]) if xs else "",
                     ", ".join(f"{k} {v}" for k, v in other[q].items())])
    if not rows:
        return ""
    return mdtable(["quantity", "unit", "papers", "min", "median", "max", "not measured here"], rows)


def element_cells(kb, r, e):
    """Every element field that can be a column, as shown in a table."""
    p = e.get("preparation")
    if isinstance(p, dict) and p.get("key"):
        prep = "**" + L("Prep", p.get("method")) + "** (key) — " + cell(p.get("parameters"))
    else:
        prep = cell(p.get("method") if isinstance(p, dict) else p)
    fns = [f for f in as_list(r.get("functions")) if isinstance(f, dict) and e.get("id") in as_list(f.get("performed_by"))]
    keys = {f.get("id") for f in fns} | {f.get("function") for f in fns}
    nums = [f"{m.get('quantity')} {m.get('value')} {m.get('unit') or ''} ({m.get('page') or ''})".replace(" ()", "")
            for m in as_list(r.get("metrics")) if isinstance(m, dict) and m.get("function") in keys - {None}]
    return {"principle": e.get("principle"), "material": e.get("material"), "geometry": e.get("geometry"),
            "preparation": prep, "props": e.get("props"), "note": e.get("note"),
            "functions": ", ".join(L("Function", f.get("function")) for f in fns), "numbers": "; ".join(nums)}


def parts_section(kb, recs, xs, roles):
    """Summary, solutions, key numbers, gaps and the element table for a set of parts [(paper id, element)]."""
    ids = sorted({rid for rid, _ in xs})
    cols = element_columns(kb, roles)
    head = ["paper", "year", "element"] + [ELEMENT_HEAD.get(c, c) for c in cols] + ["page"]
    rows = [[f"[[{rid}]]", recs[rid].get("year"), e.get("name"),
             *[element_cells(kb, recs[rid], e).get(c, e.get(c)) for c in cols], e.get("page")]
            for rid, e in sorted(xs, key=lambda x: (-(recs[x[0]].get("year") or 0), x[0]))]
    head2, rows2 = drop_empty(head, rows, {"paper", "year", "element", "page"})
    var = Counter(variant(kb, e) for _, e in xs)
    eids = {(rid, e.get("id")) for rid, e in xs}
    fkeys = {(rid, k) for rid, e in xs for f in as_list(recs[rid].get("functions"))
             if isinstance(f, dict) and e.get("id") in as_list(f.get("performed_by")) for k in (f.get("id"), f.get("function")) if k}
    pairs = [(rid, m) for rid in ids for m in as_list(recs[rid].get("metrics")) if isinstance(m, dict) and (rid, m.get("function")) in fkeys]
    tested = Counter(t.get("type") or "?" for rid in ids for t in as_list(recs[rid].get("tests"))
                     if isinstance(t, dict) and (rid, t.get("target")) in eids)
    out = digest(recs, ids) + [""]
    shared = [(k, v) for k, v in var.most_common() if v > 1 and k not in roles]
    single = sum(v == 1 for k, v in var.items() if k not in roles)
    if shared or single:
        out += ["**Solutions:** " + ", ".join(f"{k} ({v})" for k, v in shared)
                + (("; " if shared else "") + f"{single} part(s) with a principle of their own (see the table)" if single else ""), ""]
    if tested:
        out += ["**Tested directly:** " + ", ".join(f"{k} {v}" for k, v in tested.most_common()), ""]
    nums = key_numbers(kb, recs, ids, pairs=pairs)
    if nums:
        out += ["## Key numbers", "Values tied to the functions these parts perform (`metrics → function` on the cards).", "", nums]
    empty = [h for h in head[3:-1] if h not in head2 and h != "numbers"]
    gaps = [f"not reported by any paper: {', '.join(empty)}"] if empty else []
    if not tested:
        gaps.append("no test targets these parts directly")
    if not pairs:
        gaps.append("no numbers tied to them yet (`function:` on the metrics)")
    if gaps:
        out += ["**Gaps:** " + "; ".join(gaps) + ".", ""]
    return out + [full_table("Every element", head2, rows2)]


def function_results(kb, recs):
    """Numbers tied to a function (`metrics → function`), labelled with the solution variant of the elements that
    perform it: {function: {quantity: [row]}}; also tables/function_results.csv (long format, ready for plots)."""
    out, flat = defaultdict(lambda: defaultdict(list)), []
    for rid, r in sorted(recs.items()):
        for m in as_list(r.get("metrics")):
            if not isinstance(m, dict) or not m.get("function") or not m.get("quantity"):
                continue
            f = fn_of(r, m["function"])
            if not f.get("function"):
                continue
            vs = sorted({variant(kb, elem(r, x)) for x in as_list(f.get("performed_by"))}) or ["?"]
            row = {"function": f["function"], "quantity": m["quantity"], "variant": " + ".join(vs), "paper": rid,
                   "year": r.get("year"), "value": m.get("value"), "unit": m.get("unit"),
                   "value_type": m.get("value_type") or "measured", "n": m.get("n"), "sd": m.get("sd"),
                   "condition": m.get("condition"), "page": m.get("page")}
            out[f["function"]][m["quantity"]].append(row)
            flat.append(row)
    write_csv(kb.tab / "function_results.csv", flat)
    return out


def result_rows(kb, fn, q, R):
    """One quantity of one function: a row per solution variant, best first, and a bar plot."""
    qty = kb.quantities()
    low = q in set(as_list(kb.domain.get("lower_is_better")))
    by = defaultdict(list)
    for x in R:
        by[x["variant"]].append(x)
    meas = {v: sorted(a for a in (num(x["value"]) for x in xs if x["value_type"] == "measured" and x["unit"] == qty.get(q)) if a is not None)
            for v, xs in by.items()}
    order = sorted(by, key=lambda v: (not meas[v], (median(meas[v]) if meas[v] else 0) * (1 if low else -1)))
    rows = [[v, " ".join(f"[[{p}]]" for p in sorted({x["paper"] for x in by[v]})), len(meas[v]),
             f"{median(meas[v]):g}" if meas[v] else "", f"{meas[v][0]:g}" if meas[v] else "", f"{meas[v][-1]:g}" if meas[v] else "",
             ", ".join(f"{k} {c}" for k, c in Counter(x["value_type"] for x in by[v] if x["value_type"] != "measured").items())]
            for v in order]
    out = [("Lower is better" if low else "Higher first (list the quantity in `domain.yaml → lower_is_better` if lower is better)")
           + f"; unit {qty.get(q, '?')}; statistics over measured values only.", "",
           mdtable(["solution", "papers", "measured", "median", "min", "max", "other values"], rows)]
    pic = result_plot(kb, fn, q, by, order, low)
    return out + ([f"![[{pic}]]"] if pic else []) + [""]


def result_section(kb, D, fn):
    if not D:
        return []
    out = ["## Results by solution"]
    for q, R in sorted(D.items()):
        out += [f"### {L('Quantity', q)}", *result_rows(kb, fn, q, R)]
    return out


def result_plot(kb, fn, q, by, order, low):
    """Bars = median of measured values per solution variant; dots = papers (hollow = bound / datasheet / cited)."""
    qty = kb.quantities()
    name = f"plot_result_{slug(fn)}_{slug(q)}.png".replace(" ", "_")
    path = kb.notes / "plots" / name
    pts = {v: [(num(x["value"]), x) for x in by[v] if x["unit"] == qty.get(q) and num(x["value"]) is not None] for v in order}
    if sum(any(x["value_type"] == "measured" for _, x in pts[v]) for v in order) < 2:
        return None
    if kb.no_plots:
        return name if path.exists() else None
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    fig, ax = plt.subplots(figsize=(max(5, 0.9 * len(order) + 2), 4))
    for i, v in enumerate(order):
        m = [a for a, x in pts[v] if x["value_type"] == "measured"]
        if m:
            ax.bar(i, median(m), width=0.6, color="#9ec5e8")
        for a, x in pts[v]:
            ax.scatter(i, a, s=28, zorder=3, edgecolors="#1f4e79", facecolors="none" if x["value_type"] != "measured" else "#1f4e79")
            ax.annotate(x["paper"], (i, a), fontsize=6, xytext=(4, 0), textcoords="offset points")
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([str(v)[:24] for v in order], rotation=30, ha="right", fontsize=7)
    ax.set_ylabel(f"{q} ({qty.get(q)})")
    ax.set_title(f"{fn}: {q} by solution", fontsize=10)
    ax.grid(axis="y", alpha=0.25)
    fig.text(0.01, 0.01, "Bar = median of measured values · filled = measured · hollow = bound / datasheet / cited"
             + (" · lower is better" if low else ""), fontsize=6, alpha=0.7)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return name


ELEMENT_HEAD = {"preparation": "made by", "props": "properties"}
DEFAULT_ELEMENT_COLUMNS = ["principle", "material", "geometry", "preparation", "props"]


def element_columns(kb, roles):
    """Columns for elements of these roles: `domain.yaml → element_columns` per role, else its `default`, else all of
    DEFAULT_ELEMENT_COLUMNS. Columns that stay empty in every row are dropped afterwards."""
    cfg = kb.domain.get("element_columns") or {}
    out = []
    for role in roles or [None]:
        for c in as_list(cfg.get(role) or cfg.get("default") or DEFAULT_ELEMENT_COLUMNS):
            if c not in out:
                out.append(c)
    return out


def mermaid(r):
    els = [e for e in as_list(r.get("elements")) if isinstance(e, dict) and e.get("id")]
    if not els:
        return ""
    sid = {e["id"]: f"e{i}" for i, e in enumerate(els)}

    def lab(s):
        return str(s).replace('"', "'").replace("\n", " ")[:80]

    out = ["```mermaid", "graph TD"]
    for e in els:
        mat = f"<br/><i>{lab(e['material'])}</i>" if e.get("material") and norm(e["material"]) not in norm(e.get("name")) else ""
        shape = ("([", "])") if e.get("kind") == "functional" else ("[", "]")
        out.append(f'  {sid[e["id"]]}{shape[0]}"{lab(e.get("name"))}{mat}"{shape[1]}')
    for e in els:
        if e.get("parent") in sid:
            out.append(f'  {sid[e["parent"]]} -.- {sid[e["id"]]}')
    for l in as_list(r.get("links")):
        if isinstance(l, dict) and l.get("a") in sid and l.get("b") in sid:
            out.append(f'  {sid[l["a"]]} ---|"{lab(l.get("method") or l.get("class"))}"| {sid[l["b"]]}')
    ents = {}
    for it in as_list(r.get("interactions")):
        if isinstance(it, dict) and it.get("entity"):
            n = ents.setdefault(it["entity"], f"x{len(ents)}")
            src = sid.get(it.get("element"))
            if src:
                out.append(f'  {src} -.->|"{lab(it.get("type") or "")}"| {n}')
    for name, n in ents.items():
        out.append(f'  {n}(("{lab(name)}"))')
    out.append("```")
    return "\n".join(out)


def paper_note(kb, r, rel_by):
    rid = r["id"]
    fp = fig_path(kb, rid)
    auth = as_list(r.get("authors"))
    a_txt = ", ".join(auth[:6]) + (" et al." if len(auth) > 6 else "")
    doi = str(r.get("doi") or "")
    tags = [slug(t).replace(" ", "-") for t in as_list(r.get("topics"))]
    fm = {"id": rid, "year": r.get("year"), "journal": r.get("journal"), "category": r.get("category"),
          "object_type": r.get("object_type"), "status": r.get("status"), "relevance": r.get("relevance"), "tags": tags}
    s = ["---", yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip(), "---",
         f"# {r.get('title') or rid}", ""]
    if fp.exists():
        s += [f"![[{fp.name}|600]]", ""]
    s += [f"**Authors:** {a_txt}  ",
          f"**Journal:** {L('Journal', r.get('journal'))} ({r.get('year')})" + (f" · [doi:{doi}](https://doi.org/{doi})" if doi.startswith("10.") else ""),
          f"**Lab:** {L('Lab', r.get('lab'))}  " if r.get("lab") else "",
          f"**Category:** {L('Category', r.get('category'))} · **Object:** {L('Object', r.get('object_type'))} · "
          f"**Status:** {r.get('status')} · **Relevance:** {r.get('relevance')}",
          "**Topics:** " + ", ".join(L("Topic", t) for t in as_list(r.get("topics"))), ""]
    if r.get("file"):
        s += [f"PDF: `{r['file']}`", ""]
    s += ["## Summary", str(r.get("summary") or ""), ""]
    fo = r.get("focus")
    if fo:
        s += ["## Focus", (", ".join(as_list(fo.get("axes"))) + " — " if isinstance(fo, dict) and fo.get("axes") else "")
              + (fo.get("text", "") if isinstance(fo, dict) else str(fo)), ""]
    if r.get("use_for"):
        s += [f"**Use for:** {r['use_for']}", ""]
    if r.get("key_findings"):
        s += ["## Key findings", *[f"- {x}" for x in as_list(r["key_findings"])], ""]
    if r.get("elements"):
        ob = r.get("object") or {}
        s += ["## Object deconstruction"]
        if ob:
            s += [f"**{ob.get('name', '')}** — {ob.get('purpose', '')}" + (f" (scale: {ob['scale']})" if ob.get("scale") else ""), ""]
        els = [e for e in as_list(r["elements"]) if isinstance(e, dict)]
        cols = element_columns(kb, [e.get("role") for e in els])
        head = ["id", "element", "role", "kind"] + [ELEMENT_HEAD.get(c, c) for c in cols] + ["page"]
        rows = [[e.get("id"), e.get("name"), L("Element", e.get("role")), e.get("kind"),
                 *[element_cells(kb, r, e).get(c, e.get(c)) for c in cols], e.get("page")] for e in els]
        s += [mermaid(r), "", "### Elements", mdtable(*drop_empty(head, rows, {"id", "element", "role", "page"}))]
        if r.get("functions"):
            s += ["### Functions", mdtable(["function", "performed by", "metric", "page"],
                                           [[L("Function", f.get("function")), ", ".join(ename(r, x) for x in as_list(f.get("performed_by"))),
                                             f.get("metric"), f.get("page")] for f in as_list(r["functions"]) if isinstance(f, dict)])]
        if r.get("links"):
            s += ["### Links between elements", mdtable(["between", "class", "method", "transmits", "outcome", "numbers", "page"],
                                                         [[f"{ename(r, l.get('a'))} — {ename(r, l.get('b'))}", l.get("class"),
                                                           L("Link", l.get("method")), l.get("transmits"), l.get("outcome"),
                                                           l.get("numbers"), l.get("page")] for l in as_list(r["links"]) if isinstance(l, dict)])]
        if r.get("interactions"):
            s += ["### Interactions with the environment", mdtable(["element", "with", "type", "requirement", "result", "page"],
                                                                   [[ename(r, i.get("element")), L("Environment", i.get("entity")), i.get("type"),
                                                                     i.get("requirement"), i.get("result"), i.get("page")]
                                                                    for i in as_list(r["interactions"]) if isinstance(i, dict)])]
    if r.get("tests"):
        s += ["## Tests performed", mdtable(["level", "type", "test", "target", "method", "conditions", "result", "page"],
                                            [[t.get("level"), t.get("type"), t.get("name"), t.get("target"), t.get("method"),
                                              t.get("conditions"), t.get("result"), t.get("page")] for t in as_list(r["tests"]) if isinstance(t, dict)])]
    if r.get("metrics"):
        s += ["## Metrics", mdtable(["quantity", "value", "unit", "condition", "page"],
                                    [[L("Quantity", m.get("quantity")), m.get("value"), m.get("unit"),
                                      (m.get("condition") or "") + (" (read from figure)" if m.get("from_figure") else ""), m.get("page")]
                                     for m in as_list(r["metrics"]) if isinstance(m, dict)])]
    for p in as_list(r.get("protocols")):
        if isinstance(p, dict):
            s += [f"## Protocol — {p.get('name')} ({L('Protocols', p.get('quantity'))})"]
            for k in ("measures", "reference_state", "sample", "preparation", "environment", "instrument", "procedure",
                      "analysis", "result", "pitfalls", "missing", "our_setup", "pages"):
                if p.get(k):
                    v = p[k]
                    s += [f"**{k.replace('_', ' ')}:**"] + ([f"1. {x}" for x in v] if isinstance(v, list) else [str(v)]) + [""]
    if r.get("design_rules"):
        s += ["## Design rules", mdtable(["variable", "range", "effect", "page"],
                                         [[L("Design rule", d.get("variable")), d.get("range"), d.get("effect"), d.get("page")]
                                          for d in as_list(r["design_rules"]) if isinstance(d, dict)])]
    if r.get("process_window"):
        s += ["## Process window", mdtable(["parameter", "window", "failure outside", "page"],
                                           [[d.get("parameter"), d.get("window"), d.get("failure"), d.get("page")]
                                            for d in as_list(r["process_window"]) if isinstance(d, dict)])]
        if r.get("lab_compat"):
            s += [f"**Lab compatibility:** {r['lab_compat']}", ""]
    if isinstance(r.get("review_map"), dict):
        s += ["## Review map"] + [f"**{k}:** {cell(v)}" for k, v in r["review_map"].items()] + [""]
    if isinstance(r.get("transfer"), dict):
        s += ["## What transfers to my project"] + [f"**{k}:** {cell(v)}" for k, v in r["transfer"].items()] + [""]
    if isinstance(r.get("bio"), dict):
        s += ["## Biology"] + [f"**{k}:** {cell(v)}" for k, v in r["bio"].items()] + [""]
    if r.get("limitations"):
        s += ["## Limitations", *[f"- {x}" for x in as_list(r["limitations"])], ""]
    rel = rel_by.get(rid) or []
    if rel:
        s += ["## Related papers", *[f"- [[{o}]] — {t}" + (f": {n}" if n else "") for o, t, n in rel], ""]
    return "\n".join(x for x in s if x is not None)


def papers_table(recs, ids):
    return full_table("All papers", ["paper", "year", "category", "relevance", "summary"],
                      [[f"[[{i}]]", recs[i].get("year"), recs[i].get("category"), recs[i].get("relevance"), recs[i].get("summary")]
                       for i in sorted(ids, key=lambda x: (-(recs[x].get("year") or 0), x))])


def elem(r, eid):
    return next((e for e in as_list(r.get("elements")) if isinstance(e, dict) and e.get("id") == eid), {})


def fn_of(r, key):
    """Function item of a card by its id (F1) or its name; a metric's `function` may use either."""
    return next((f for f in as_list(r.get("functions")) if isinstance(f, dict) and key in (f.get("id"), f.get("function"))), {})


def variant(kb, e):
    """Solution variant of an element: explicit `principle`, else a material tag of domain.yaml found in `material`,
    else the first word of the material, else its role."""
    if e.get("principle"):
        return str(e["principle"])
    mat = str(e.get("material") or "")
    if mat:
        nm = norm(mat)
        tags = sorted(as_list((kb.domain.get("tags") or {}).get("materials")), key=lambda t: -len(norm(t)))
        hit = next((t for t in tags if len(norm(t)) > 2 and norm(t) in nm), None)
        if hit:
            return hit
        return re.split(r"[\s,;/(]+", mat.strip())[0][:24] or "?"
    return str(e.get("role") or "?")


def heatmap(kb, name, rows, cols, M, title):
    """Count matrix as a PNG in notes/plots; returns the file name or None."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return None
    if not rows or not cols:
        return None
    if kb.no_plots:
        return name if (kb.notes / "plots" / name).exists() else None
    A = np.array(M, dtype=float)
    fig, ax = plt.subplots(figsize=(max(6, 0.55 * len(cols) + 3), 0.45 * len(rows) + 1.8))
    ax.imshow(A, aspect="auto", cmap="Blues")
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([str(c)[:22] for c in cols], rotation=45, ha="right", fontsize=7)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([str(r)[:40] for r in rows], fontsize=7)
    for i in range(A.shape[0]):
        for j in range(A.shape[1]):
            if A[i, j]:
                ax.text(j, i, int(A[i, j]), ha="center", va="center", fontsize=7,
                        color="white" if A[i, j] > A.max() / 2 else "black")
    ax.set_title(title + " — empty cells: not tried in this base", fontsize=9)
    fig.tight_layout()
    (kb.notes / "plots").mkdir(parents=True, exist_ok=True)
    fig.savefig(kb.notes / "plots" / name, dpi=150)
    plt.close(fig)
    return name


def structure_map(kb, recs, pairs_role):
    """Network of element roles over all papers: node size = how many elements have the role,
    edge width = how many links join the two roles, edge label = most used method."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import networkx as nx
    except ImportError:
        return None
    G = nx.Graph()
    size = Counter(str(e.get("role") or "?") for r in recs.values() for e in as_list(r.get("elements")) if isinstance(e, dict))
    for (a, b), xs in pairs_role.items():
        m = Counter(str(l.get("method") or l.get("class")) for _, l in xs).most_common(1)[0][0]
        G.add_edge(a, b, w=len(xs), label=f"{m} ({len(xs)})")
    if G.number_of_nodes() < 2:
        return None
    if kb.no_plots:
        return "plot_structure_map.png" if (kb.notes / "plots" / "plot_structure_map.png").exists() else None
    pos = nx.kamada_kawai_layout(G)
    fig, ax = plt.subplots(figsize=(8, 6.5))
    ws = [G[u][v]["w"] for u, v in G.edges()]
    nx.draw_networkx_edges(G, pos, ax=ax, width=[1 + 4 * w / max(ws) for w in ws], edge_color="#8aa", alpha=0.8)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=[300 + 60 * size.get(n, 1) for n in G.nodes()],
                           node_color="#4a7fb5", alpha=0.9)
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=8, font_color="black",
                            labels={n: f"{n}\n({size.get(n, 0)})" for n in G.nodes()})
    nx.draw_networkx_edge_labels(G, pos, ax=ax, font_size=6,
                                 edge_labels={(u, v): G[u][v]["label"] for u, v in G.edges() if G[u][v]["w"] >= 2})
    ax.set_title("Structure map: element roles and how they are joined (all papers)\n"
                 "node = role (number of elements) · edge = links between roles · label = most used method (count)", fontsize=9)
    ax.axis("off")
    fig.tight_layout()
    (kb.notes / "plots").mkdir(parents=True, exist_ok=True)
    fig.savefig(kb.notes / "plots" / "plot_structure_map.png", dpi=150)
    plt.close(fig)
    return "plot_structure_map.png"


def build_notes(kb, recs, T, journals, plots):
    N = kb.notes
    rel_by = defaultdict(list)
    for x in T["relations"]:
        rel_by[x["a"]].append((x["b"], x["type"], x["note"]))
        rel_by[x["b"]].append((x["a"], x["type"], x["note"]))
    for rid, r in recs.items():
        write_note(N / "papers" / f"{rid}.md", paper_note(kb, r, rel_by))
    hubs = defaultdict(lambda: defaultdict(set))   # kind -> name -> {ids}
    for rid, r in recs.items():
        for t in as_list(r.get("topics")):
            hubs["Topic"][t].add(rid)
        for k, kind in (("category", "Category"), ("lab", "Lab"), ("journal", "Journal"), ("object_type", "Object")):
            if r.get(k):
                hubs[kind][r[k]].add(rid)
    qty = kb.quantities()
    for kind, names in hubs.items():
        for name, ids in names.items():
            body = [f"# {kind}: {name}", "", *digest(recs, ids), ""]
            if kind == "Journal":
                j = next((x for x in journals if norm(x["journal"]) == norm(name)), None)
                if j:
                    body += [mdtable(["status", "publisher", "APC (USD)", "OpenAlex 2-yr mean citedness", "h-index", "SJR quartile", "IF"],
                                     [[j["status"], j["publisher"], j["apc_usd"], j["openalex_2yr_mean_citedness"],
                                       j["openalex_h_index"], j["sjr_quartile"], j["impact_factor"]]]), ""]
            nums = key_numbers(kb, recs, ids)
            if nums:
                body += ["## Key numbers", "Measured values reported by these papers. Conditions differ — open a quantity before comparing.", "", nums]
            body += ["## Papers", papers_table(recs, ids)]
            write_note(N / "hubs" / kind.lower() / f"{kind} - {slug(name)}.md", "\n".join(body))
    # deconstruction hubs: element role, link method, environment entity, key preparation method, function
    el_by, ln_by, env_by, prep_by, fn_by = (defaultdict(list) for _ in range(5))
    for rid, r in recs.items():
        for e in as_list(r.get("elements")):
            if not isinstance(e, dict):
                continue
            if e.get("role"):
                el_by[e["role"]].append((rid, e))
            p = e.get("preparation")
            if isinstance(p, dict) and p.get("key") and p.get("method"):
                prep_by[p["method"]].append((rid, e, p))
        for l in as_list(r.get("links")):
            if isinstance(l, dict) and (l.get("method") or l.get("class")):
                ln_by[l.get("method") or l.get("class")].append((rid, l))
        for it in as_list(r.get("interactions")):
            if isinstance(it, dict) and it.get("entity"):
                env_by[it["entity"]].append((rid, it))
        for f in as_list(r.get("functions")):
            if isinstance(f, dict) and f.get("function"):
                fn_by[f["function"]].append((rid, f))
    for role, xs in el_by.items():
        write_note(N / "hubs" / "element" / f"Element - {slug(role)}.md", "\n".join(
            [f"# Element role: {role}", "", f"How {len(xs)} element(s) in {len({x[0] for x in xs})} paper(s) implement this role.", ""]
            + parts_section(kb, recs, xs, [role])))
    for meth, xs in ln_by.items():
        oc = Counter(l.get("outcome") or "not stated" for _, l in xs)
        cls = Counter(l.get("class") for _, l in xs).most_common(1)[0][0]
        write_note(N / "hubs" / "link" / f"Link - {slug(meth)}.md", "\n".join([
            f"# Link method: {meth}", "", f"Class: **{cls}** · used {len(xs)}× · outcomes: " + ", ".join(f"{k} {v}" for k, v in oc.items()), "",
            *digest(recs, [x[0] for x in xs]), "",
            full_table("Every joint", ["paper", "joins", "materials", "transmits", "preparation", "outcome", "numbers", "page"],
                    [[f"[[{rid}]]", f"{ename(recs[rid], l.get('a'))} — {ename(recs[rid], l.get('b'))}",
                      " / ".join(str(next((e.get("material") for e in as_list(recs[rid].get("elements")) if isinstance(e, dict) and e.get("id") == k), "") or "")
                                 for k in (l.get("a"), l.get("b"))),
                      l.get("transmits"), l.get("preparation"), l.get("outcome"), l.get("numbers"), l.get("page")]
                     for rid, l in sorted(xs, key=lambda x: x[0])])]))
    for ent, xs in env_by.items():
        write_note(N / "hubs" / "environment" / f"Environment - {slug(ent)}.md", "\n".join([
            f"# Environment: {ent}", "", "What devices/materials in the base do with it, what is required and what was measured.", "",
            *digest(recs, [x[0] for x in xs]), "",
            full_table("Every interaction", ["paper", "element", "type", "requirement", "tested", "result", "page"],
                    [[f"[[{rid}]]", ename(recs[rid], it.get("element")), it.get("type"), it.get("requirement"),
                      it.get("tested"), it.get("result"), it.get("page")] for rid, it in sorted(xs, key=lambda x: x[0])])]))
    for meth, xs in prep_by.items():
        pw = [(rid, w) for rid in {x[0] for x in xs} for w in as_list(recs[rid].get("process_window")) if isinstance(w, dict)]
        write_note(N / "hubs" / "preparation" / f"Prep - {slug(meth)}.md", "\n".join([
            f"# Key preparation method: {meth}", "", "Only preparations marked `key: true` (non-obvious or the focus of the authors).", "",
            *digest(recs, [x[0] for x in xs]), "",
            full_table("Every preparation", ["paper", "element", "material", "parameters", "steps", "page"],
                    [[f"[[{rid}]]", e.get("name"), e.get("material"), p.get("parameters"), len(as_list(p.get("steps"))), p.get("page")]
                     for rid, e, p in sorted(xs, key=lambda x: x[0])]),
            "## Process windows reported by these papers",
            mdtable(["paper", "parameter", "window", "failure outside", "page"],
                    [[f"[[{rid}]]", w.get("parameter"), w.get("window"), w.get("failure"), w.get("page")] for rid, w in pw])]))
    results = function_results(kb, recs)
    for fn, xs in fn_by.items():
        var = Counter(variant(kb, elem(recs[rid], x)) for rid, f in xs for x in as_list(f.get("performed_by")))
        write_note(N / "hubs" / "function" / f"Function - {slug(fn)}.md", "\n".join([
            f"# Function: {fn}", "", *digest(recs, [x[0] for x in xs]), "",
            "**Solutions:** " + ", ".join(f"{k} ({v})" for k, v in var.most_common()), "",
            *result_section(kb, results.get(fn, {}), fn),
            full_table("Every paper", ["paper", "solution (element)", "role", "material", "metric", "page"],
                                            [[f"[[{rid}]]", ", ".join(ename(recs[rid], x) for x in as_list(f.get("performed_by"))),
                                              ", ".join(str(next((e.get("role") for e in as_list(recs[rid].get("elements")) if isinstance(e, dict) and e.get("id") == x), "")) for x in as_list(f.get("performed_by"))),
                                              ", ".join(str(next((e.get("material") for e in as_list(recs[rid].get("elements")) if isinstance(e, dict) and e.get("id") == x), "")) for x in as_list(f.get("performed_by"))),
                                              f.get("metric"), f.get("page")] for rid, f in sorted(xs, key=lambda x: x[0])])]))
    # morphological table: function × solution variant (principle / material class) → papers
    if fn_by:
        cells = defaultdict(lambda: defaultdict(set))   # function -> variant -> {ids}
        for fn, xs in fn_by.items():
            for rid, f in xs:
                for x in as_list(f.get("performed_by")):
                    cells[fn][variant(kb, elem(recs[rid], x))].add(rid)
        vcount = Counter(v for fn in cells for v, ids in cells[fn].items() for _ in ids)
        cols = [v for v, _ in vcount.most_common(14)]
        fns = sorted(cells, key=lambda f: -sum(len(i) for i in cells[f].values()))
        rows = []
        for fn in fns:
            row = [L("Function", fn)]
            for v in cols:
                ids = sorted(cells[fn].get(v, []))
                row.append(" ".join(f"[[{i}]]" for i in ids) if len(ids) <= 3 else f"**{len(ids)}** papers")
            other = [f"{v} ({len(i)})" for v, i in cells[fn].items() if v not in cols]
            rows.append(row + [", ".join(other)])
        heat = heatmap(kb, "plot_function_solution.png", [str(f) for f in fns], cols,
                       [[len(cells[f].get(v, [])) for v in cols] for f in fns], "Function × solution variant (papers)")
        write_note(N / "Function x solution.md", "\n".join([
            "# Function × solution (morphological table)", "",
            "Rows: what the objects must do. Columns: solution variants — the element's `principle` if given, otherwise the material "
            "class recognised from the tags of `domain.yaml`, otherwise the first word of the material. Cells: papers. "
            "**Empty cells are combinations nobody in the base has tried** (or that make no sense) — candidates for gaps.", ""]
            + ([f"![[{heat}]]", ""] if heat else []) + [mdtable(["function"] + cols + ["other variants"], rows)]))
    # interfaces: which parts are joined to which, by what, and did it hold (aggregated over all papers)
    pairs_role, pairs_var = defaultdict(list), defaultdict(list)
    for rid, r in recs.items():
        for l in as_list(r.get("links")):
            if not isinstance(l, dict):
                continue
            a, b = elem(r, l.get("a")), elem(r, l.get("b"))
            ra, rb = sorted([str(a.get("role") or "?"), str(b.get("role") or "?")])
            pairs_role[(ra, rb)].append((rid, l))
            va, vb = sorted([variant(kb, a), variant(kb, b)])
            pairs_var[(va, vb)].append((rid, l))
    if pairs_role:
        def summary(xs):
            m = Counter(str(l.get("method") or l.get("class")) for _, l in xs)
            o = Counter(str(l.get("outcome") or "not stated") for _, l in xs)
            return (", ".join(f"{L('Link', k)} ({v})" for k, v in m.most_common()),
                    ", ".join(f"{k} {v}" for k, v in o.most_common()),
                    " ".join(f"[[{i}]]" for i in sorted({x[0] for x in xs})))
        smap = structure_map(kb, recs, pairs_role)
        write_note(N / "Interfaces.md", "\n".join([
            "# Interfaces — what is joined to what, and how", "",
            "Aggregated over all papers: every link between two elements. By role (which parts meet) and by material / principle "
            "(which materials meet). Open a link method for the per-paper details, preparation and numbers.", ""]
            + ([f"![[{smap}]]", ""] if smap else [])
            + ["## By element role", mdtable(["element A", "element B", "links", "methods (count)", "outcomes", "papers"],
                                             [[L("Element", a), L("Element", b), len(xs), *summary(xs)]
                                              for (a, b), xs in sorted(pairs_role.items(), key=lambda x: -len(x[1]))]),
               "## By material / principle", mdtable(["A", "B", "links", "methods (count)", "outcomes", "papers"],
                                                     [[a, b, len(xs), *summary(xs)]
                                                      for (a, b), xs in sorted(pairs_var.items(), key=lambda x: -len(x[1]))])]))
    # quantities: plot + table; protocols per quantity
    met_by = defaultdict(list)
    for rid, r in recs.items():
        for m in as_list(r.get("metrics")):
            if isinstance(m, dict) and m.get("quantity"):
                met_by[m["quantity"]].append((rid, m))
    skipped = plots.get("_skipped", {})
    for q, xs in met_by.items():
        body = [f"# Quantity: {q}", "", f"Unit in this base: **{qty.get(q, '?')}**", "", *digest(recs, [x[0] for x in xs]), ""]
        nums = key_numbers(kb, recs, [], pairs=xs)
        if nums:
            body += ["## Key numbers", nums]
        nocond = sorted({rid for rid, m in xs if not m.get("condition")})
        if nocond:
            body += [f"Values without a condition (hard to compare): " + " ".join(f"[[{i}]]" for i in nocond), ""]
        by_fn = [(fn, R) for fn, D in results.items() for qq, R in D.items() if qq == q]
        for fn, R in by_fn:
            body += [f"## By solution — {L('Function', fn)}", *result_rows(kb, fn, q, R)]
        if ("metric", q) in plots:
            body += [f"![[{plots[('metric', q)]}]]", ""]
        body += [full_table("Every value", ["paper", "year", "value", "unit", "type", "condition", "page"],
                            [[f"[[{rid}]]", recs[rid].get("year"), m.get("value"), m.get("unit"), m.get("value_type") or "",
                              (m.get("condition") or "") + (" (from figure)" if m.get("from_figure") else ""), m.get("page")]
                             for rid, m in sorted(xs, key=lambda x: -(recs[x[0]].get("year") or 0))])]
        if skipped.get(q):
            body += ["## Not plotted", mdtable(["paper", "reason"], [[f"[[{a}]]", b] for a, b in skipped[q]])]
        write_note(N / "hubs" / "quantity" / f"Quantity - {slug(q)}.md", "\n".join(body))
    pr_by = defaultdict(list)
    for rid, r in recs.items():
        for p in as_list(r.get("protocols")):
            if isinstance(p, dict) and p.get("quantity"):
                pr_by[p["quantity"]].append((rid, p))
    checklists = kb.domain.get("protocol_checklists") or {}
    for q in set(pr_by) | set(checklists):
        xs = pr_by.get(q, [])
        body = [f"# Protocols: {q}", "", "## What our own protocol must fix (checklist)",
                *[f"- [ ] {c}" for c in as_list(checklists.get(q))], "",
                "## Comparison", mdtable(["paper", "name", "measures", "reference state", "sample", "environment", "instrument", "result", "pitfalls"],
                                         [[f"[[{rid}]]", p.get("name"), p.get("measures"), p.get("reference_state"), p.get("sample"),
                                           p.get("environment"), p.get("instrument"), p.get("result"), p.get("pitfalls")] for rid, p in xs])]
        write_note(N / "hubs" / "protocols" / f"Protocols - {slug(q)}.md", "\n".join(body))
    # design rules, process windows, review map
    dr = defaultdict(list)
    for rid, r in recs.items():
        for d in as_list(r.get("design_rules")):
            if isinstance(d, dict) and d.get("variable"):
                dr[d["variable"]].append((rid, d))
    for v, xs in dr.items():
        write_note(N / "hubs" / "design_rule" / f"Design rule - {slug(v)}.md", "\n".join([
            f"# Design rule: {v}", "", *digest(recs, [x[0] for x in xs]), "",
            full_table("Every paper", ["paper", "range studied", "effect", "page"],
                                              [[f"[[{rid}]]", d.get("range"), d.get("effect"), d.get("page")] for rid, d in xs])]))
    write_note(N / "Design rules.md", "\n".join(["# Design rules", "", mdtable(["variable", "papers"],
               [[L("Design rule", v), " ".join(f"[[{rid}]]" for rid, _ in xs)] for v, xs in sorted(dr.items())])]))
    write_note(N / "Process windows.md", "\n".join(["# Process windows", "", mdtable(["paper", "parameter", "window", "failure outside", "page"],
               [[f"[[{rid}]]", w.get("parameter"), w.get("window"), w.get("failure"), w.get("page")]
                for rid, r in sorted(recs.items()) for w in as_list(r.get("process_window")) if isinstance(w, dict)])]))
    rv = [(rid, r["review_map"]) for rid, r in sorted(recs.items()) if isinstance(r.get("review_map"), dict)]
    write_note(N / "Review map.md", "\n".join(["# Review map", ""] + [
        f"## [[{rid}]]\n" + "\n".join(f"**{k}:** {cell(v)}" for k, v in m.items()) + "\n" for rid, m in rv]))
    maps = [v for k, v in plots.items() if isinstance(k, tuple) and k[0] == "map"]
    write_note(N / "Property map.md", "\n".join(["# Property maps", "",
               "One point per paper (first reported value of each quantity). Pairs are set in `domain.yaml → plot_pairs`. "
               "Conditions differ between papers — check the quantity pages before drawing conclusions.", ""]
               + [f"![[{m}]]" for m in maps] + ([] if maps else ["_No pair with ≥ 2 papers yet._"])))
    build_journal_note(kb, recs, journals, plots)
    build_anatomy(kb, recs)
    H, syns = hub_evidence(recs), load_syntheses(kb)
    link_syntheses(kb, recs, H, syns)
    build_index(kb, recs, T, hubs, el_by, ln_by, env_by, prep_by, met_by, pr_by, synthesis_lines(H, syns))


def build_journal_note(kb, recs, journals, plots):
    recent = int(kb.project.get("recent_years", 3))
    s = ["# Journals", "",
         f"{len(journals)} journals · {len(recs)} papers. Status and rank from OpenAlex (2-year mean citedness ≈ impact-factor-like; "
         "h-index of the journal). SJR quartile / impact factor only if you put `journal_ranks.csv` or a Scimago export into the knowledge base folder.",
         "", "Focus of the papers comes from three sources: **auto** = category / object type on the card; **folder** = folder of the PDF; "
         "**keywords** = `project.yaml → focus_keywords`.", ""]
    if "journals_counts" in plots:
        s += [f"![[{plots['journals_counts']}]]", ""]
    if "journals_years" in plots:
        s += [f"![[{plots['journals_years']}]]", ""]
    s += ["## All journals", mdtable(["journal", "papers", "high rel.", f"last {recent} y", "years", "status", "APC USD",
                                      "2-yr citedness", "h", "SJR Q", "IF", "focus (auto)", "focus (folder)", "focus (keywords)"],
                                     [[L("Journal", j["journal"]), j["n_papers"], j["high_relevance"], j["recent"], j["years"], j["status"],
                                       j["apc_usd"], j["openalex_2yr_mean_citedness"], j["openalex_h_index"], j["sjr_quartile"],
                                       j["impact_factor"], j["focus_auto"], j["focus_folder"], j["focus_keywords"]] for j in journals])]
    cand = [j for j in journals if (j["high_relevance"] or j["recent"]) and "preprint" not in j["status"] and j["journal"] != "(unknown)"]
    cand.sort(key=lambda j: (-j["high_relevance"], -j["recent"], -(float(j["openalex_2yr_mean_citedness"] or 0))))
    s += ["", "## Where to submit — shortlist",
          f"Journals that published **high-relevance** papers of this base or papers from the last {recent} years. "
          "Frequency reflects how *you* collected papers, not the whole market; read it as 'where my topic already appears'.", "",
          mdtable(["journal", "high rel.", "recent", "status", "APC USD", "2-yr citedness", "SJR Q", "main focus"],
                  [[L("Journal", j["journal"]), j["high_relevance"], j["recent"], j["status"], j["apc_usd"],
                    j["openalex_2yr_mean_citedness"], j["sjr_quartile"], j["focus_auto"].split(",")[0]] for j in cand[:20]])]
    retr = [j for j in journals if j["retracted_papers"]]
    if retr:
        s += ["", "## ⚠ Retracted papers in the base", *[f"- {j['retracted_papers']} ({j['journal']})" for j in retr]]
    write_note(kb.notes / "Journals.md", "\n".join(s))


def build_index(kb, recs, T, hubs, el_by, ln_by, env_by, prep_by, met_by, pr_by, syn_lines=()):
    st = Counter(r.get("status") for r in recs.values())
    s = [f"# {kb.project.get('title') or 'Knowledge base'}", "",
         str(kb.project.get("question") or ""), "",
         f"**{len(recs)} papers** · verified {st.get('verified', 0)} · brief {st.get('brief', 0)} · "
         f"{len(T.get('tests', []))} tests · {len(T.get('metrics', []))} numbers · {len(T.get('protocols', []))} protocols", "",
         *syn_lines,
         "## Overviews", "- [[Interfaces]] · [[Function x solution]] · [[Property map]] · [[Journals]] · [[Design rules]] · [[Process windows]] · [[Review map]]", ""]
    for title, kind, d in (("Categories", "Category", hubs.get("Category", {})), ("Object types", "Object", hubs.get("Object", {})),
                           ("Topics", "Topic", hubs.get("Topic", {})), ("Labs", "Lab", hubs.get("Lab", {}))):
        if d:
            s += [f"## {title}", " · ".join(f"{L(kind, k)} ({len(v)})" for k, v in sorted(d.items(), key=lambda x: (-len(x[1]), str(x[0])))), ""]
    for title, kind, d in (("Element roles", "Element", el_by), ("Link methods", "Link", ln_by), ("Environment", "Environment", env_by),
                           ("Key preparation methods", "Prep", prep_by), ("Quantities", "Quantity", met_by), ("Protocols", "Protocols", pr_by)):
        if d:
            s += [f"## {title}", " · ".join(f"{L(kind, k)} ({len(v)})" for k, v in sorted(d.items(), key=lambda x: (-len(x[1]), str(x[0])))), ""]
    s += ["## All papers", mdtable(["paper", "year", "journal", "category", "status", "relevance", "summary"],
                                   [[f"[[{rid}]]", r.get("year"), r.get("journal"), r.get("category"), r.get("status"),
                                     r.get("relevance"), r.get("summary")] for rid, r in sorted(recs.items(), key=lambda x: (-(x[1].get("year") or 0), x[0]))])]
    write_note(kb.notes / "Index.md", "\n".join(s))


# ----------------------------------------------------------------------------- anatomy: the object as a graph of parts
# `domain.yaml → anatomy` describes the studied object once: its parts (nodes), which part acts on which (edges) and
# optional names for solution variants. Build then writes notes/anatomy/: an overview page and three folders whose
# pages link to each other the way the object is built — parts ↔ parts, part → solutions → papers, method → parts.
# File names are short (`short:`), so the Obsidian graph stays readable; the full name is the page title.
ANATOMY_DIRS = {"node": "1 Parts", "solution": "2 Solutions", "method": "3 Methods"}


def anatomy_cfg(kb):
    a = kb.domain.get("anatomy") or {}
    nodes = []
    for n in as_list(a.get("nodes")):
        if isinstance(n, dict) and n.get("id"):
            nodes.append({**n, "short": str(n.get("short") or n.get("title") or n["id"])[:30]})
    return nodes, [tuple(e) for e in as_list(a.get("edges")) if isinstance(e, list) and len(e) == 2], a.get("solutions") or {}


def anatomy_names(nodes, sols, methods):
    """Short file names, unique across the three layers (Obsidian links by file name). sols = {key: label}."""
    used, out = {}, {}
    for layer, items in (("node", [(n["id"], n["short"]) for n in nodes]), ("solution", sols.items()), ("method", [(m, m) for m in methods])):
        for k, label in items:
            base = slug(label)
            name = base if base.lower() not in used else f"{base} ({layer})"
            if base.lower() in used:
                print(f"anatomy: '{base}' is used by a {used[base.lower()]} and a {layer} — the {layer} page is '{name}'")
            used.setdefault(base.lower(), layer)
            out[(layer, k)] = name
    return out


def build_anatomy(kb, recs):
    nodes, edges, sol_cfg = anatomy_cfg(kb)
    if not nodes:
        return False
    A = kb.notes / "anatomy"
    for p in A.rglob("*.md") if A.exists() else []:   # drop generated pages of renamed parts, unless the user wrote notes in them
        t = p.read_text()
        if MARK in t and not t.split(MARK, 1)[1].replace("## 📝 My notes", "").strip():
            p.unlink()
    requested = {str(x) for x in as_list(kb.project.get("focus_requested"))}
    ids_of = {n["id"]: set() for n in nodes}
    parts_of = {n["id"]: [] for n in nodes}
    sols = defaultdict(lambda: {"nodes": set(), "papers": set()})
    for rid, r in recs.items():
        topics = set(as_list(r.get("topics")))
        fn_names = {f.get("function") for f in as_list(r.get("functions")) if isinstance(f, dict)}
        for n in nodes:
            roles = set(as_list(n.get("roles")))
            els = [e for e in as_list(r.get("elements")) if isinstance(e, dict) and e.get("role") in roles]
            parts_of[n["id"]] += [(rid, e) for e in els]
            if els or topics & set(as_list(n.get("topics"))) or fn_names & set(as_list(n.get("functions"))):
                ids_of[n["id"]].add(rid)
            for e in els:   # a solution = the variant of a part (principle / material class), unless it is just the role
                v = variant(kb, e)
                if v != e.get("role"):
                    sols[v]["nodes"].add(n["id"])
                    sols[v]["papers"].add(rid)
        for t in topics:   # tags listed under anatomy.solutions are solutions too (classification facets)
            c = sol_cfg.get(t)
            if isinstance(c, dict):
                sols[t]["nodes"] |= set(as_list(c.get("nodes")))
                sols[t]["papers"].add(rid)
    # a principle written once as free text is a description, not a solution: keep variants shared by ≥ 2 papers
    sols = {k: v for k, v in sols.items() if v["papers"] and (k in sol_cfg or len(v["papers"]) >= 2)}
    tests_by = defaultdict(lambda: {"papers": set(), "nodes": Counter(), "levels": Counter()})
    role_node = {role: n["id"] for n in nodes for role in as_list(n.get("roles"))}
    for rid, r in recs.items():
        for t in as_list(r.get("tests")):
            if isinstance(t, dict) and t.get("type") and str(t["type"]).lower() not in CATCH_ALL:
                m = tests_by[t["type"]]
                m["papers"].add(rid)
                m["levels"][t.get("level") or "?"] += 1
                nid = role_node.get(elem(r, t.get("target")).get("role"))
                if nid:
                    m["nodes"][nid] += 1
    label = lambda k: (sol_cfg.get(k) or {}).get("short") if isinstance(sol_cfg.get(k), dict) else None
    names = anatomy_names(nodes, {k: label(k) or str(k)[:30] for k in sols}, list(tests_by))
    lk = lambda layer, k: f"[[{names[(layer, k)]}]]"
    title = {n["id"]: n.get("title") or n["short"] for n in nodes}
    nb = defaultdict(set)
    for a, b in edges:
        nb[a].add(b)
        nb[b].add(a)
    for n in nodes:
        nid = n["id"]
        mine = sorted((k for k, v in sols.items() if nid in v["nodes"]), key=lambda k: -len(sols[k]["papers"]))
        body = [f"# {title[nid]}", "", ("★ asked for by the user" if nid in requested else "◆ suggested from the papers") + f" · part of [[Anatomy]]", ""]
        if n.get("about"):
            body += [str(n["about"]), ""]
        if n.get("focus"):
            body += ["**What to look at:** " + "; ".join(as_list(n["focus"])) + ".", ""]
        if nb[nid]:
            body += ["**Connected parts:** " + " · ".join(lk("node", x) for x in sorted(nb[nid]) if ("node", x) in names), ""]
        if mine:
            body += ["**Solutions:** " + " · ".join(f"{lk('solution', k)} ({len(sols[k]['papers'])})" for k in mine), ""]
        meth = [(k, m["nodes"][nid]) for k, m in tests_by.items() if m["nodes"][nid]]
        if meth:
            body += ["**Tested by:** " + " · ".join(f"{lk('method', k)} ({c})" for k, c in sorted(meth, key=lambda x: -x[1])), ""]
        ids = sorted(ids_of[nid])
        if parts_of[nid]:
            body += parts_section(kb, recs, parts_of[nid], as_list(n.get("roles")))
        else:
            body += digest(recs, ids) + [""]
        nums = key_numbers(kb, recs, ids, quantities=set(as_list(n.get("quantities")))) if n.get("quantities") else ""
        if nums:
            body += ["## Numbers of this part (all papers that touch it)", nums]
        if ids:
            body += ["## Papers", papers_table(recs, ids)]
        write_note(A / ANATOMY_DIRS["node"] / f"{names[('node', nid)]}.md", "\n".join(body))
    for k, v in sols.items():
        ids = sorted(v["papers"])
        quant = {q for nid in v["nodes"] for n in nodes if n["id"] == nid for q in as_list(n.get("quantities"))}
        co = Counter(o for o, w in sols.items() if o != k for i in ids if i in w["papers"])
        body = [f"# {label(k) + ' — ' if label(k) else ''}{k}", "", "Solution for: " + " · ".join(lk("node", x) for x in sorted(v["nodes"]) if ("node", x) in names), "",
                *digest(recs, ids), ""]
        if co:
            body += ["**Used together with:** " + " · ".join(f"{lk('solution', o)} ({c})" for o, c in co.most_common(8)), ""]
        nums = key_numbers(kb, recs, ids, quantities=quant) if quant else ""
        if nums:
            body += ["## Numbers reported by these papers", "Not all of them describe this solution alone — open the paper before comparing.", "", nums]
        body += ["## Papers", papers_table(recs, ids)]
        write_note(A / ANATOMY_DIRS["solution"] / f"{names[('solution', k)]}.md", "\n".join(body))
    for k, m in tests_by.items():
        ids = sorted(m["papers"])
        body = [f"# Method: {k}", "", "Tests of this type on the cards (`tests → type`).", "",
                "**Parts tested:** " + (" · ".join(f"{lk('node', x)} ({c})" for x, c in m["nodes"].most_common() if ("node", x) in names) or "none linked"),
                "", "**Levels:** " + ", ".join(f"{a} {b}" for a, b in m["levels"].most_common()), "",
                *digest(recs, ids), "",
                full_table("Every test", ["paper", "test", "target", "method", "result", "page"],
                           [[f"[[{rid}]]", t.get("name"), ename(recs[rid], t.get("target")), t.get("method"), t.get("result"), t.get("page")]
                            for rid in ids for t in as_list(recs[rid].get("tests")) if isinstance(t, dict) and t.get("type") == k])]
        write_note(A / ANATOMY_DIRS["method"] / f"{names[('method', k)]}.md", "\n".join(body))
    sid = {n["id"]: f"n{i}" for i, n in enumerate(nodes)}
    chart = ["```mermaid", "graph LR"] + [f'  {sid[n["id"]]}["{"★" if n["id"] in requested else "◆"} {title[n["id"]]}"]' for n in nodes]
    chart += [f"  {sid[a]} --- {sid[b]}" for a, b in edges if a in sid and b in sid] + ["```"]
    rows = [["★" if n["id"] in requested else "◆", lk("node", n["id"]), len(ids_of[n["id"]]),
             ", ".join(f"{names[('solution', k)]} ({len(sols[k]['papers'])})" for k in
                       sorted((k for k, v in sols.items() if n["id"] in v["nodes"]), key=lambda k: -len(sols[k]["papers"]))[:4]),
             "; ".join(as_list(n.get("focus")))] for n in nodes]
    write_note(A / "Anatomy.md", "\n".join([
        f"# Anatomy — {(kb.domain.get('anatomy') or {}).get('object') or kb.project.get('title') or 'the studied object'}", "",
        "The object taken apart into its parts, how they connect, which solutions the papers use for each part and how the "
        "parts are tested. ★ = part you asked to focus on (`project.yaml → focus_requested`); ◆ = part suggested from the papers. "
        "Parts and connections are defined in `domain.yaml → anatomy`.", "", *chart, "",
        mdtable(["", "part", "papers", "main solutions", "what to look at"], rows),
        "## Methods", " · ".join(f"{lk('method', k)} ({len(m['papers'])})" for k, m in sorted(tests_by.items(), key=lambda x: -len(x[1]["papers"]))), "",
        "Graph view: run `kb.py graph` once to colour parts, solutions, methods and papers and to hide the navigation pages."]))
    return True


def cmd_graph(kb):
    """Colour groups + filter for Obsidian's graph view: parts / solutions / methods / papers, navigation pages hidden.
    Writes <vault>/.obsidian/graph.json (vault = nearest folder up from the base that has .obsidian, else the base)."""
    vault = next((p for p in [kb.dir, *kb.dir.parents] if (p / ".obsidian").is_dir()), kb.dir)
    rel = lambda p: str(p.relative_to(vault)).replace("\\", "/") if p != vault else ""
    A, P = kb.notes / "anatomy", kb.notes / "papers"
    q = lambda p: f'path:"{rel(p)}"'
    groups = [(A / ANATOMY_DIRS["node"], 0xE8590C), (A / ANATOMY_DIRS["solution"], 0xF59F00),
              (A / ANATOMY_DIRS["method"], 0x9C36B5), (P, 0x1C7ED6)]
    gp = vault / ".obsidian" / "graph.json"
    cfg = json.loads(gp.read_text()) if gp.exists() else {}
    if gp.exists():
        shutil.copy(gp, gp.with_suffix(".json.bak"))
    show = [q(p) for p, _ in groups if p.exists()]
    cfg.update({"search": " OR ".join(show), "showTags": False, "showAttachments": False, "hideUnresolved": True,
                "colorGroups": [{"query": q(p), "color": {"a": 1, "rgb": c}} for p, c in groups if p.exists()]})
    gp.parent.mkdir(parents=True, exist_ok=True)
    gp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    had = gp.with_suffix(".json.bak").exists()
    print(f"wrote {gp}" + (" (previous version: graph.json.bak)" if had else "") + ". Groups: parts orange, solutions yellow, methods purple, papers blue."
          + ("" if A.exists() else " No anatomy layer yet — add domain.yaml → anatomy and run build; only papers are shown now.")
          + " Reopen the graph view in Obsidian to see it.")


# ----------------------------------------------------------------------------- syntheses: hub pages → written answers
# A hub page is one of three levels: a LIST (topic, lab, journal… — cards only carry a tag there), a COMPARISON
# (element / link / quantity… — cards carry outcomes, numbers, conditions) and, on top of a comparison, a SYNTHESIS:
# a written answer to one question in analysis/*.md (frontmatter `type: synthesis`). See references/synthesis.md.
INDEX_KINDS = {"Topic", "Category", "Lab", "Journal", "Object"}
JUDGED = {"works", "partial", "fails"}


def hub_evidence(recs):
    """Every hub note → kind, papers, records, records with a judgement (outcome / result / props / effect), records with numbers."""
    H = {}
    hasnum = lambda x: bool(re.search(r"\d", str(x or "")))

    def add(kind, name, rid, judged=False, number=False):
        note = f"{kind} - {slug(name)}"
        h = H.setdefault(note, {"note": note, "kind": kind, "papers": set(), "records": 0, "judged": 0, "numbers": 0})
        h["papers"].add(rid)
        h["records"] += 1
        h["judged"] += bool(judged)
        h["numbers"] += bool(number)

    for rid, r in recs.items():
        for t in as_list(r.get("topics")):
            add("Topic", t, rid)
        for k, kind in (("category", "Category"), ("lab", "Lab"), ("journal", "Journal"), ("object_type", "Object")):
            if r.get(k):
                add(kind, r[k], rid)
        for e in as_list(r.get("elements")):
            if not isinstance(e, dict):
                continue
            if e.get("role"):
                add("Element", e["role"], rid, e.get("props"), hasnum(e.get("props")))
            p = e.get("preparation")
            if isinstance(p, dict) and p.get("key") and p.get("method"):
                add("Prep", p["method"], rid, p.get("parameters"), hasnum(p.get("parameters")))
        for l in as_list(r.get("links")):
            if isinstance(l, dict) and (l.get("method") or l.get("class")):
                add("Link", l.get("method") or l.get("class"), rid, l.get("outcome") in JUDGED, bool(l.get("numbers")))
        for it in as_list(r.get("interactions")):
            if isinstance(it, dict) and it.get("entity"):
                add("Environment", it["entity"], rid, it.get("result"), hasnum(it.get("result")))
        for f in as_list(r.get("functions")):
            if isinstance(f, dict) and f.get("function"):
                add("Function", f["function"], rid, f.get("metric"), hasnum(f.get("metric")))
        for m in as_list(r.get("metrics")):
            if isinstance(m, dict) and m.get("quantity"):
                add("Quantity", m["quantity"], rid, m.get("condition"), True)   # a value without its condition is not comparable
        for p in as_list(r.get("protocols")):
            if isinstance(p, dict) and p.get("quantity"):
                add("Protocols", p["quantity"], rid, p.get("result"), hasnum(p.get("result")))
        for d in as_list(r.get("design_rules")):
            if isinstance(d, dict) and d.get("variable"):
                add("Design rule", d["variable"], rid, d.get("effect"), hasnum(d.get("range")))
    return H


def load_syntheses(kb):
    """Written syntheses: analysis/**/*.md whose YAML frontmatter has `type: synthesis` and `hubs: [<hub note>, …]`."""
    out = []
    for f in sorted((kb.dir / "analysis").glob("**/*.md")):
        t = f.read_text(errors="ignore")
        if not t.startswith("---"):
            continue
        try:
            fm = yaml.safe_load(t.split("---", 2)[1]) or {}
        except (yaml.YAMLError, IndexError) as e:
            print(f"SKIP {f.name}: frontmatter — {str(e).splitlines()[0]}")
            continue
        if not isinstance(fm, dict) or fm.get("type") != "synthesis":
            continue
        h1 = re.search(r"^# (.+)$", t, re.M)
        out.append({"stem": f.stem, "title": h1.group(1).strip() if h1 else f.stem, "question": fm.get("question") or "",
                    "date": str(fm.get("date") or ""), "hubs": [str(h) for h in as_list(fm.get("hubs") or fm.get("hub"))],
                    "papers": {str(p) for p in as_list(fm.get("papers"))}})
    return out


def min_papers(kb):
    return int((kb.project.get("synthesis") or {}).get("min_papers", 4))


def is_candidate(kb, h):
    catch_all = h["note"].split(" - ", 1)[1].lower() in {"other", "none", "unknown", "not-reported"}
    return h["kind"] not in INDEX_KINDS and not catch_all and len(h["papers"]) >= min_papers(kb) and h["judged"] >= 2


def link_syntheses(kb, recs, H, syns):
    """Put a banner under the title of each hub note: its synthesis (and whether papers were added since), or a hint
    that the hub has enough evidence for one."""
    paths = {p.stem: p for p in kb.notes.rglob("*.md")}
    by_hub = defaultdict(list)
    for s in syns:
        for h in s["hubs"]:
            by_hub[h].append(s)
            if h not in paths:
                print(f"synthesis {s['stem']}: hub '{h}' not found among the notes (spelling? e.g. 'Link - silane')")
    for note, p in paths.items():
        h = H.get(note)
        lines = []
        for s in by_hub.get(note, []):
            new = sorted(h["papers"] - s["papers"]) if h else []
            lines.append(f"> [!summary] Synthesis: [[{s['stem']}|{s['title']}]]" + (f" — *{s['question']}*" if s["question"] else "")
                         + f" ({s['date']}, {len(s['papers'])} papers)")
            if new and s["papers"]:
                lines.append(f"> ⚠ {len(new)} paper(s) added to this hub since: " + " ".join(f"[[{i}]]" for i in new[:10]) + (" …" if len(new) > 10 else ""))
        if not lines and h and is_candidate(kb, h):
            lines.append(f"> [!tip] {len(h['papers'])} papers, {h['judged']} records with an outcome, result or condition, {h['numbers']} with numbers — "
                         f"enough for a written synthesis. Ask Claude a question about it, e.g. *\"write a synthesis for {note}: …?\"*")
        if lines:
            t = p.read_text().split("\n", 1)
            p.write_text(t[0] + "\n\n" + "\n".join(lines) + "\n" + (t[1] if len(t) > 1 else ""))


def synthesis_lines(H, syns):
    if not syns:
        return []
    rows = []
    for s in syns:
        new = set().union(*[H[h]["papers"] for h in s["hubs"] if h in H]) - s["papers"] if s["papers"] else set()
        rows.append([f"[[{s['stem']}|{s['title']}]]", s["question"], s["date"], " · ".join(f"[[{h}]]" for h in s["hubs"]),
                     len(s["papers"]), f"⚠ {len(new)} new paper(s)" if new else "up to date"])
    return ["## Syntheses — written answers", mdtable(["synthesis", "question", "date", "hubs", "papers", "status"], rows), ""]


def cmd_candidates(kb):
    recs = kb.records()
    H, syns = hub_evidence(recs), load_syntheses(kb)
    covered = defaultdict(list)
    for s in syns:
        for h in s["hubs"]:
            covered[h].append(s)
    rows = []
    for note, h in H.items():
        if not is_candidate(kb, h):
            continue
        high = sum(recs[i].get("relevance") == "high" for i in h["papers"])
        st = "none"
        if covered.get(note):
            new = h["papers"] - set().union(*[s["papers"] for s in covered[note]])
            st = f"{len(new)} new paper(s) since" if new else "up to date"
        rows.append({"hub": note, "kind": h["kind"], "papers": len(h["papers"]), "high_relevance": high,
                     "records": h["records"], "judged": h["judged"], "numbers": h["numbers"], "synthesis": st})
    rows.sort(key=lambda x: (x["synthesis"] == "up to date", -x["high_relevance"], -(x["judged"] + x["numbers"]), -x["papers"]))
    write_csv(kb.tab / "synthesis_candidates.csv", rows)
    print(mdtable(["#", "hub", "papers", "high rel.", "records", "judged", "numbers", "synthesis"],
                  [[i + 1, x["hub"], x["papers"], x["high_relevance"], x["records"], x["judged"], x["numbers"], x["synthesis"]]
                   for i, x in enumerate(rows)]))
    lists = sum(h["kind"] in INDEX_KINDS for h in H.values())
    print(f"{len(rows)} hub(s) with ≥ {min_papers(kb)} papers and ≥ 2 judged records. {lists} list hubs (topics, labs, journals…) "
          "are not candidates: they hold tags only. Propose at most 3 to the user, as questions tied to their project; "
          "write nothing without an answer (references/synthesis.md).")


def cmd_build(kb):
    recs = kb.records()
    T = build_tables(kb, recs)
    jp = kb.tab / "journals.csv"
    journals = journal_table(kb, recs, fetch=False) if recs else []
    if journals:
        write_csv(jp, journals)
    plots = build_plots(kb, recs, journals)
    build_xlsx(kb, T, journals)
    build_notes(kb, recs, T, journals, plots)
    warn, newv = cmd_check(kb, quiet=True)
    print(f"built {len(recs)} papers → notes/, tables/, knowledge_base.xlsx · check: {len(warn)} warnings, {len(newv)} new terms")


def cmd_triage(kb):
    recs = kb.records()
    rows = []
    for rid, r in recs.items():
        if r.get("status") != "brief":
            continue
        t = kb.text(r.get("sha", ""))
        rows.append({"id": rid, "year": r.get("year"), "journal": r.get("journal"), "category": r.get("category"),
                     "object_type": r.get("object_type"), "relevance": r.get("relevance"),
                     "pages": t.count("=== page ") or "?", "SI": "yes" if r.get("supplementary") else "no",
                     "summary": r.get("summary")})
    order = {"high": 0, "medium": 1, "low": 2}
    rows.sort(key=lambda x: (order.get(x["relevance"], 3), -(x["year"] or 0)))
    write_csv(kb.tab / "triage.csv", rows)
    print(mdtable(["#", "id", "year", "category", "relevance", "pages", "SI", "summary"],
                  [[i + 1, x["id"], x["year"], x["category"], x["relevance"], x["pages"], x["SI"], x["summary"]] for i, x in enumerate(rows)]))
    print(f"{len(rows)} brief card(s). Ask the user which ones to analyse in depth — do not start without an answer.")


def cmd_status(kb):
    recs = kb.records()
    st = Counter(r.get("status") for r in recs.values())
    print(f"{kb.dir}\n{len(recs)} cards: " + ", ".join(f"{k} {v}" for k, v in st.items()))
    print("categories: " + ", ".join(f"{k} {v}" for k, v in Counter(r.get("category") for r in recs.values()).most_common()))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd")
    ap.add_argument("args", nargs="*")
    ap.add_argument("--kb")
    ap.add_argument("--domain", default="_template")
    ap.add_argument("--id")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--no-plots", action="store_true")
    a = ap.parse_args()
    if a.cmd == "init":
        if not a.args:
            sys.exit("usage: kb.py init <dir> [--domain NAME]")
        return cmd_init(Path(a.args[0]), a.domain)
    kb = KB(find_kb(a.kb))
    if a.cmd == "ingest":
        cmd_ingest(kb)
    elif a.cmd == "stub":
        for s in a.args:
            cmd_stub(kb, s, a.id)
    elif a.cmd == "peek":
        cmd_peek(kb, a.args[0], a.args[1] if len(a.args) > 1 else "head")
    elif a.cmd == "triage":
        cmd_triage(kb)
    elif a.cmd == "candidates":
        cmd_candidates(kb)
    elif a.cmd == "figures":
        cmd_figures(kb, a.force)
    elif a.cmd == "journals":
        cmd_journals(kb, fetch=not a.offline)
    elif a.cmd == "check":
        warn, _ = cmd_check(kb)
        sys.exit(1 if warn else 0)
    elif a.cmd == "build":
        kb.no_plots = a.no_plots
        cmd_build(kb)
    elif a.cmd == "graph":
        cmd_graph(kb)
    elif a.cmd == "status":
        cmd_status(kb)
    elif a.cmd == "all":
        cmd_ingest(kb); cmd_figures(kb); cmd_build(kb)
    else:
        sys.exit(f"unknown command {a.cmd}\n\n{__doc__}")


if __name__ == "__main__":
    main()
