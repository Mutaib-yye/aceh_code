"""The Balai Bahasa Aceh dictionaries as word lookup + example-sentence candidates (personal / research use).

Books (all from Balai Bahasa Provinsi Aceh; copyrighted, so the extracted text stays in data/raw/kamus/books/, git-ignored):
  maritim   Kamus Kemaritiman Aceh-Indonesia (2021)        entries: headword /ipa/ pos meaning: example 'translation'
  budaya    Kamus Budaya Aceh-Indonesia (2022, 3 PDF parts) same layout
  bergambar Kamus Bergambar Aceh-Indonesia-Inggris (2023)  picture dictionary: Acehnese / Indonesian / English lines
    python -m acehid dict-build --maritim X.pdf --budaya A.pdf B.pdf C.pdf --bergambar Y.pdf
Extraction is automatic and NOT validated: the app labels every entry with its book and page. The example sentences that come with a
translation become CANDIDATES for the manual validation sheets (golden / parallel corpus); they are never trained on directly."""
import csv, json, re
from pathlib import Path
from .common import ROOT

OUT = ROOT / "data/raw/kamus/books"
TITLES = {"maritim": "Kamus Kemaritiman Aceh–Indonesia (2021)", "budaya": "Kamus Budaya Aceh–Indonesia (2022)",
          "bergambar": "Kamus Bergambar Aceh–Indonesia–Inggris (2023)"}
POS = r"(?:n|v|a|adv|num|pron|p|konj|prep|interj|ark|pel|lihat)"
HEAD = re.compile(r"^(?P<hw>[^\s/‘’“”:;()0-9][^/‘’“”:;()]{0,60}?)\s*/(?P<ipa>[^/]{1,40})/\s*(?P<rest>.*)$")
PAGE_HEAD = re.compile(r"^\s*(?:(\d{1,3})\s*\|\s*Kamus|Kamus [^|]+\|\s*(\d{1,3}))")
EXAMPLE = re.compile(r"([^‘’]{4,160}?)\s*[‘'](?P<ind>[^’']{3,200})[’']")


def extract_pdf(pdf, out_txt):
    """PDF text layer -> text with '##### PAGE <printed page or pdf page>' markers. Returns the number of pages."""
    import pymupdf
    doc = pymupdf.open(str(pdf)); out = []
    for i, page in enumerate(doc, 1):
        t = page.get_text()
        m = next((PAGE_HEAD.match(l) for l in t.splitlines()[:3] if PAGE_HEAD.match(l)), None) or next(
            (PAGE_HEAD.match(l) for l in t.splitlines()[-4:] if PAGE_HEAD.match(l)), None)
        printed = next((g for g in m.groups() if g), None) if m else None
        out.append(f"##### PAGE {printed or 'pdf' + str(i)}\n{t}")
    Path(out_txt).parent.mkdir(parents=True, exist_ok=True)
    Path(out_txt).write_text("\n".join(out), encoding="utf-8")
    return len(doc)


def _pages(txt):
    page, buf = None, []
    for line in txt.splitlines():
        m = re.match(r"^##### PAGE (\S+)$", line)
        if m:
            if page is not None: yield page, buf
            page, buf = m.group(1), []
        else:
            buf.append(line.strip())
    if page is not None: yield page, buf


def parse_entries(txt, book):
    """Dictionary entries: a headword line followed (same line or next) by its /pronunciation/. -> [{word, ipa, text, page, book}]."""
    entries = []
    for page, lines in _pages(txt):
        lines = [l.replace("﻿", "").strip() for l in lines if l.replace("﻿", "").strip()]
        # join "headword" + "/ipa/" split over two lines
        merged, i = [], 0
        while i < len(lines):
            if i + 1 < len(lines) and lines[i + 1].startswith("/") and not lines[i].startswith("/") and "/" not in lines[i]:
                merged.append(lines[i] + " " + lines[i + 1]); i += 2
            else:
                merged.append(lines[i]); i += 1
        cur = None
        for l in merged:
            m = HEAD.match(l)
            if m and len(m.group("hw").split()) <= 4:
                cur = {"word": m.group("hw").strip(), "ipa": m.group("ipa").strip(), "text": m.group("rest").strip(), "page": page, "book": book}
                entries.append(cur)
            elif cur is not None and not re.match(r"^(Kamus .*\|\s*\d+|\d+\s*\|\s*Kamus.*)$", l):
                cur["text"] += " " + l
    for e in entries:
        e["text"] = re.sub(r"\s+", " ", e["text"]).strip()
    return [e for e in entries if e["text"]]


def parse_triples(txt, book="bergambar"):
    """Picture dictionary: groups of three lines (Acehnese, Indonesian, English); 'a - b - c' lines are picture titles; a line in
    〔 〕 is the scientific name of the previous entry. Front matter (prose, long lines) is skipped."""
    out = []
    for page, lines in _pages(txt):
        if page.startswith("pdf") and page[3:].isdigit() and int(page[3:]) <= 8:
            continue
        lines = [l for l in lines if l and not re.match(r"^Kamus Bergambar.*\|\s*\w+\s*$", l)]
        buf = []
        for l in lines:
            if l.startswith("〔"):
                if out and not buf: out[-1]["latin"] = l.strip("〔〕 ")
                continue
            if len(re.findall(r"\s-\s", l)) == 2:
                a, i, e = [x.strip() for x in l.split(" - ")]
                out.append({"word": a, "ind": i, "eng": e, "page": page, "book": book, "title": True}); buf = []; continue
            if len(l) > 60 or l.endswith("."):          # prose, not a label
                buf = []; continue
            buf.append(l)
            if len(buf) == 3:
                out.append({"word": buf[0], "ind": buf[1], "eng": buf[2], "page": page, "book": book}); buf = []
    return out


DASH = re.compile(r"(?<!\w)(\w*)(?:[—–]|--)")


def example_candidates(entries):
    """'definition: Acehnese example ‘Indonesian translation’' inside an entry -> candidate pairs.
    The dash in the Acehnese example stands for the headword (an affix glued to it, as in meu—, is kept): it is filled in and marked
    'filled'. A dash in the Indonesian translation stands for the headword's meaning and cannot be filled: 'needs_human'.
    Every candidate still goes to a human translator + checker; nothing here is trained on directly."""
    rows = []
    for e in entries:
        for m in EXAMPLE.finditer(e["text"]):
            pre = re.split(r"[:;]|\s\d\s", m.group(1))[-1] if re.search(r"[:;]|\s\d\s", m.group(1)) else m.group(1)
            raw = re.sub(r"^[\s:;,\d.]+", "", pre).strip()
            ind = m.group("ind").strip()
            if "/" in raw or len(raw.split()) < 3 or len(ind.split()) < 2:
                continue
            ace = DASH.sub(lambda mm: mm.group(1) + e["word"], raw)
            status = "needs_human" if re.search(r"[—–]|--", ind) else ("filled" if ace != raw else "clean")
            rows.append({"ace": ace, "ind": ind, "ace_raw": raw, "headword": e["word"], "book": e["book"], "page": e["page"], "status": status})
    return rows


def build(maritim=None, budaya=None, bergambar=None, out=OUT):
    """PDFs -> text + entries.json + examples.csv under data/raw/kamus/books/. Returns counts."""
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    stats, entries, examples = {}, [], []
    def run(key, pdfs, kind):
        txts = []
        for n, pdf in enumerate(pdfs, 1):
            t = out / f"{key}_{n}.txt"; extract_pdf(pdf, t); txts.append(t.read_text(encoding="utf-8"))
        txt = "\n".join(txts)
        got = parse_entries(txt, key) if kind == "entries" else parse_triples(txt, key)
        stats[key] = len(got)
        return got
    if maritim:
        e = run("maritim", [maritim], "entries"); entries += e; examples += example_candidates(e)
    if budaya:
        e = run("budaya", budaya if isinstance(budaya, (list, tuple)) else [budaya], "entries"); entries += e; examples += example_candidates(e)
    if bergambar:
        entries += run("bergambar", [bergambar], "triples")
    json.dump(entries, open(out / "entries.json", "w", encoding="utf-8"), ensure_ascii=False)
    with open(out / "examples.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, ["ace", "ind", "ace_raw", "headword", "book", "page", "status"]); w.writeheader(); w.writerows(examples)
    import collections
    stats.update(examples=len(examples), by_status=dict(collections.Counter(r["status"] for r in examples)))
    return stats
