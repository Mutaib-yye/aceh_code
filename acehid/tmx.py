"""OPUS/Uplug TMX export (ace-id.tmx, Wikipedia text) -> filtered pairs for training: data/final/wikipedia/pairs.json.

Wikipedia text is CC-BY-SA 4.0 (share-alike, attribution to the Wikipedia authors). Filters: citation marks [1] removed,
4-60 words per side, word-count ratio 0.6-1.7 (bad alignments), Acehnese side must pass the language check, ace != ind.
Caveat: some Acehnese Wikipedia articles are themselves translated from Indonesian, so spelling and wording can lean Indonesian."""
import re, html, json
from pathlib import Path
from .common import ROOT, log
from . import langid
from .normalize import normalize

def read_tmx(path):
    t = Path(path).read_text(encoding="utf-8")
    for tu in re.findall(r"<tu>(.*?)</tu>", t, re.S):
        a = re.search(r'xml:lang="ace"><seg>(.*?)</seg>', tu, re.S); i = re.search(r'xml:lang="id"><seg>(.*?)</seg>', tu, re.S)
        if a and i:
            yield html.unescape(a.group(1)), html.unescape(i.group(1))

def clean(s):
    return " ".join(re.sub(r"\[\d+\]", " ", s).split())

def run(path, out=ROOT / "data/final/wikipedia/pairs.json"):
    rows, seen, n = [], set(), 0
    for a, i in read_tmx(path):
        n += 1
        a, i = normalize(clean(a))[0], clean(i)
        la, li = len(a.split()), len(i.split())
        if not (4 <= la <= 60 and 4 <= li <= 60) or not 0.6 <= li / la <= 1.7 or a.lower() == i.lower() or a in seen:
            continue
        if langid.classify(a)[0] != "ace":
            continue
        seen.add(a); rows.append({"ace": a, "ind": i, "source": "wikipedia (OPUS, CC-BY-SA 4.0)"})
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(rows, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log("import-tmx", read=n, kept=len(rows))
    return {"read": n, "kept": len(rows), "out": str(out)}
