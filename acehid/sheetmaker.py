"""One self-contained web page (no server, no internet) in which each student makes their OWN sheet of 25 AcehX sentences.

The student types name + student number (NPM). The NPM picks one of ~2,400 disjoint blocks of 25 sentences (FNV-1a hash mod
blocks), so different students get different sentences without any coordination. They translate in the page (or in Excel),
download a CSV in the format `import-sheets` reads, swap files with a friend, and the friend checks it in the page's second tab.
    python -m acehid sheet-maker      -> tools/AcehX_sheet_maker.html   (share this one file)
The pool is the same one `make-packs` draws from: AcehX lines of 4-25 words, language check = Acehnese, not already in our data."""
import json
from pathlib import Path
from .common import ROOT
from . import sheets

PER = 25
TEMPLATE = Path(__file__).with_name("sheetmaker_template.html")


def fnv1a(s):
    h = 0x811c9dc5
    for ch in s:
        h ^= ord(ch)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def pool():
    """[(source file, line number, sentence)] in a fixed order (file, line)."""
    _, ace = sheets._candidates(0)
    return sorted(ace, key=lambda r: (r[0], r[1]))


def block_of(npm, n_sentences):
    """Index of the 25-sentence block this student number gets (the same rule as the page's JavaScript)."""
    return fnv1a("".join(npm.split())) % (n_sentences // PER)


def build(out=None):
    out = Path(out) if out else ROOT / "tools/AcehX_sheet_maker.html"
    p = pool()
    files = sorted({f for f, _, _ in p})
    rows = [[files.index(f), l, t] for f, l, t in p]
    html = (TEMPLATE.read_text(encoding="utf-8").replace("/*POOL*/[]", json.dumps(rows, ensure_ascii=False, separators=(",", ":")))
            .replace("/*FILES*/[]", json.dumps(files)))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return {"sentences": len(p), "blocks": len(p) // PER, "file": str(out), "mb": round(out.stat().st_size / 1e6, 1)}
