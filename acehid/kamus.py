"""Personal lookup in the Kamus Budaya Aceh-Indonesia (Balai Bahasa Provinsi Aceh, 2022).

The book is copyrighted. Its text is kept only in data/raw/kamus/ (git-ignored) on the computer that built it, and it is not
used for training data or shipped with the app. Build the local text once from your copy of the PDF, then look words up:

    python -m acehid kamus-build "Kamus Budaya Aceh-Indonesia.pdf"
    python -m acehid kamus ampu

Each hit shows the PDF page number, so you can check the entry in the book itself (the PDF text layer is not always clean).
"""
import re
from pathlib import Path
from .common import ROOT, strip_diacritics
from .normalize import normalize

TEXT = ROOT / "data/raw/kamus/kamus_budaya.txt"
PAGE = re.compile(r"^##### PAGE (\d+)$")

def fold(s):
    """Lower case, no accents: ampéh, ampeh and AMPEH all match."""
    return strip_diacritics(s).lower().strip()

def build(pdf, out=TEXT):
    import pymupdf
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(str(pdf))
    with open(out, "w", encoding="utf-8") as f:
        for i, page in enumerate(doc, 1):
            f.write(f"##### PAGE {i}\n{page.get_text()}\n")
    return doc.page_count, out

def _lines(path):
    """(pdf_page, line) for every text line of the built book."""
    page = 0
    with open(path, encoding="utf-8") as f:
        for raw in f:
            raw = raw.rstrip("\n")
            m = PAGE.match(raw)
            if m:
                page = int(m.group(1))
            else:
                yield page, raw

def lookup(word, path=TEXT, context=6, limit=10):
    """-> [(pdf_page, entry_text)] for lines that start with the word (accents and case ignored).
    The entry is the matching line and the few lines after it on the same page."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found: run `python -m acehid kamus-build <PDF>` first")
    key = fold(word)
    if not key:
        return []
    head = re.compile(re.escape(key) + r"(?!\w)")
    lines = list(_lines(path))
    hits = []
    for i, (page, line) in enumerate(lines):
        if not head.match(fold(line)):
            continue
        if i and fold(lines[i - 1][1]) == key:            # the book prints a headword alone, then again with its entry: count it once
            continue
        seg = []
        for j in range(i, min(i + context, len(lines))):
            if lines[j][0] != page:
                break
            seg.append(lines[j][1])
        hits.append((page, " ".join(" ".join(seg).split())))
        if len(hits) == limit:
            break
    return hits

def show(word, path=TEXT):
    word = word.strip()
    found = False
    for w in dict.fromkeys([word, normalize(word)[0]]):           # as typed, then in the training spelling (dj->j, ö->o)
        for page, text in lookup(w, path):
            found = True
            print(f"[pdf page {page}] {text}")
        if found:
            break
    if not found:
        print(f"'{word}' does not start any line of the book. Try another spelling "
              "(the book writes é, è, ô, and Dutch spellings such as dj, tj, nj).")
