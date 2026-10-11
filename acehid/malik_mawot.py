"""Hikayat Malik Mawot (Inayati, UIN Ar-Raniry thesis, 2017): verse edition where every Acehnese line is followed by its Indonesian
translation, each ending in "/". Pairs are written to data/human/malik_mawot_pairs.json (git-ignored: a copyrighted thesis, use
with the author's/professor's permission) and can be trained on with `build-train --extra data/human/malik_mawot_pairs.json`.
Every pair is checked: word similarity between the lines (bilingual.similarity), Acehnese side must pass the language check."""
import re, json
from pathlib import Path
from .common import ROOT, log
from . import bilingual, langid
from .normalize import normalize

START = "Tango keu kisah haba mawot"          # first verse line of the poem
MIN_SIM = 0.15

def segments(pdf):
    import pymupdf
    pages = [p.get_text() for p in pymupdf.open(str(pdf))]
    first = next(i for i, t in enumerate(pages) if START in " ".join(t.split()))
    end = next(i for i, t in enumerate(pages) if i > first and re.search(r"^BAB IV", t, re.M))
    txt = []
    for t in pages[first:end]:
        lines = t.split("\n")
        cut = next((k for k, l in enumerate(lines) if re.match(r"\s*_{5,}", l)), len(lines))   # footnotes sit under a rule
        txt.append(" ".join(l for l in lines[:cut] if l.strip() and not re.fullmatch(r"\s*\d{1,3}\s*", l)))
    s = re.sub(r"\[\d+\]", " ", " ".join(txt))                                                 # stanza marks like [8]
    segs = [" ".join(re.sub(r"(?<=[A-Za-zéèôöë\-])\d{1,3}\b", "", x).split()) for x in re.split(r"/+", s)]   # footnote digits
    segs = [x for x in segs if x]
    return segs[next(k for k, x in enumerate(segs) if x.startswith(START)):]

def pair_up(segs):
    pairs, i = [], 0
    while i + 1 < len(segs):
        a, b = segs[i], segs[i + 1]
        if 2 <= len(a.split()) <= 40 and bilingual.similarity(a, b) > MIN_SIM and not re.search(r"\d|Teks|_", a + b) \
                and langid.classify(a)[0] == "ace":
            pairs.append({"ace": normalize(a)[0], "ind": b, "source": "Hikayat Malik Mawot (Inayati 2017)"}); i += 2
        else:
            i += 1                                                    # resync: drop the stray segment
    return pairs

def run(pdf, out=ROOT / "data/human/malik_mawot_pairs.json"):
    segs = segments(pdf); pairs = pair_up(segs)
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(pairs, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log("malik-mawot", segments=len(segs), pairs=len(pairs))
    return {"segments": len(segs), "pairs": len(pairs), "out": str(out)}
