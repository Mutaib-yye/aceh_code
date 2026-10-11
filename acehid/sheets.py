"""Human translation sheets: Acehnese sentences and words for speakers to translate, and the import of their answers.

The Indonesian side is written only by people. A row is accepted only when a translator AND a different checker have filled it in.
Machine output (including AI assistants) is never written into these sheets, because the model would learn the machine's mistakes.
"""
import collections, csv, json, random, re
from pathlib import Path
from .common import *
from . import langid
from .normalize import normalize

SENT_COLS = ["id", "acehnese", "indonesian", "translator", "checker", "notes"]
WORD_COLS = ["id", "acehnese_word", "example_acehnese", "indonesian_meaning", "translator", "checker", "notes"]
MIN_WORDS, MAX_WORDS = 4, 25
OUT = ROOT / "data/human/sheets"
GUIDE = """TRANSLATOR GUIDE (Acehnese -> Indonesian)

1. Translate the Acehnese sentence into standard Indonesian, keeping the meaning. Do not add or leave out information.
2. Keep names, titles (Teungku, Cut, Po, Habib) and places as they are.
3. If you are not sure of a word, write "?" in the cell and add a note. Never guess.
4. Do NOT use Google Translate, ChatGPT or any other machine translation. Only your own knowledge.
5. Every row needs TWO people: the translator fills "translator" and "indonesian"; a DIFFERENT person fills "checker" after reading it.
   The checker can change the Indonesian, and must say so in "notes".
6. Do not change the Acehnese text, even if the spelling looks wrong. Save as CSV (UTF-8).
7. Word sheet: give the Indonesian meaning for the Acehnese word, as used in the example sentence.
"""


def _existing_sides():
    """Every Acehnese and Indonesian sentence we already use (train, validation, test, hikayat, FLORES, NusaX), normalised for comparison."""
    keys = set()
    for f in (ROOT / "data/final").rglob("*.json"):
        if f.name in ("manifest.json", "README.json", "atlas.json", "atlas_master.json", "stats.json", "atlas_nusax.json"):
            continue
        try:
            rows = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        for r in rows if isinstance(rows, list) else []:
            if isinstance(r, dict):
                for k in ("ace", "ind"):
                    if r.get(k):
                        keys.add(match_key(r[k]))
    return keys


def _acehx_lines():
    for r in read_jsonl(ROOT / "data/extracted/acehx.jsonl"):
        yield r["src_file"], r["line"], " ".join(r["ace_raw"].split())


def make_sentence_sheet(out=OUT, n=200, seed=0):
    seen = _existing_sides()
    cands = []
    for src, line, t in _acehx_lines():
        if not (MIN_WORDS <= len(t.split()) <= MAX_WORDS):
            continue
        k = match_key(t)
        if k in seen:
            continue
        seen.add(k)
        cands.append((src, line, t))
    random.Random(seed).shuffle(cands)
    chosen = [c for c in cands if langid.classify(c[2])[0] == "ace"][:n]
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    with open(out / "sentences.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, SENT_COLS); w.writeheader()
        for i, (src, line, t) in enumerate(chosen, 1):
            w.writerow({"id": f"S{i:04d}", "acehnese": t, "indonesian": "", "translator": "", "checker": "", "notes": f"{src}:{line}"})
    log("sentence-sheet", rows=len(chosen), candidates=len(cands))
    return len(chosen)


def make_word_sheet(out=OUT, n=300):
    lines = list(_acehx_lines())
    indonesian = set()
    for f in ("train", "validation", "test"):
        p = ROOT / f"data/final/nusax/{f}.json"
        for r in (json.load(open(p, encoding="utf-8")) if p.exists() else []):
            indonesian.update(re.findall(r"[^\W\d_]+", r["ind"].lower()))
    counts = collections.Counter()
    for _, _, t in lines:
        counts.update(w for w in re.findall(r"[^\W\d_]+", t.lower()) if len(w) >= 3 and w not in indonesian)
    top = [w for w, _ in counts.most_common(n * 2) if not re.search(r"\d", w)][:n]
    example = {}
    for _, _, t in lines:
        if len(t.split()) > 14:
            continue
        for w in re.findall(r"[^\W\d_]+", t.lower()):
            if w in top and w not in example:
                example[w] = t
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    with open(out / "words.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, WORD_COLS); w.writeheader()
        for i, word in enumerate(top, 1):
            w.writerow({"id": f"W{i:04d}", "acehnese_word": word, "example_acehnese": example.get(word, ""),
                        "indonesian_meaning": "", "translator": "", "checker": "", "notes": f"{counts[word]} occurrences in AcehX"})
    (out / "TRANSLATOR_GUIDE.txt").write_text(GUIDE, encoding="utf-8")
    log("word-sheet", rows=len(top))
    return len(top)


def _accepted(r, field):
    filled = r.get(field, "").strip() and r.get("translator", "").strip() and r.get("checker", "").strip()
    return bool(filled) and r["translator"].strip().lower() != r["checker"].strip().lower()


def import_sheets(sentences=None, words=None, outdir=ROOT / "data/human"):
    """Accepted rows only: translator and checker are different people. Returns counts; writes pairs.json and glossary.csv."""
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    stats = {"sentences_in": 0, "sentences_accepted": 0, "words_in": 0, "words_accepted": 0}
    pairs = []
    if sentences:
        for r in csv.DictReader(open(sentences, encoding="utf-8-sig")):
            stats["sentences_in"] += 1
            if _accepted(r, "indonesian") and "?" not in r["indonesian"]:
                pairs.append({"id": r["id"], "ace": normalize(r["acehnese"])[0], "ind": r["indonesian"].strip(),
                              "source": "human (translator + independent checker)"})
        stats["sentences_accepted"] = len(pairs)
        json.dump(pairs, open(outdir / "pairs.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    gloss = []
    if words:
        for r in csv.DictReader(open(words, encoding="utf-8-sig")):
            stats["words_in"] += 1
            if _accepted(r, "indonesian_meaning") and "?" not in r["indonesian_meaning"]:
                gloss.append({"acehnese_word": r["acehnese_word"], "indonesian": r["indonesian_meaning"].strip(), "id": r["id"]})
        stats["words_accepted"] = len(gloss)
        with open(outdir / "glossary.csv", "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, ["id", "acehnese_word", "indonesian"]); w.writeheader(); w.writerows(gloss)
    log("import-sheets", **stats)
    return stats
