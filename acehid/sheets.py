"""Human translation sheets: Acehnese sentences and words for speakers to translate, and the import of their answers.

The Indonesian side is written only by people. A row is accepted only when a translator AND a different checker have filled it in.
Machine output (including AI assistants) is never written into these sheets, because the model would learn the machine's mistakes.
"""
import collections, csv, json, random, re
from pathlib import Path
from .common import *
from . import langid
from .normalize import normalize

SENT_COLS = ["id", "acehnese", "indonesian", "translator", "checker", "verdict", "notes"]
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
   Checker: fill "verdict" with ok (you agree with the translation as it is) or fixed (you changed it, and say what in "notes").
   Rows marked ok go to the GOLDEN corpus (two people agree); every accepted row goes to the PARALLEL corpus.
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
    if not (ROOT / "data/extracted/acehx.jsonl").exists():          # a fresh clone has the corpus but not its index: build it
        from . import audit
        audit.run()
    for r in read_jsonl(ROOT / "data/extracted/acehx.jsonl"):
        yield r["src_file"], r["line"], " ".join(r["ace_raw"].split())


def _candidates(seed=0):
    """Unique Acehnese AcehX lines (4-25 words, language check = Acehnese) that we do not already use, in a seeded random order."""
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
    return cands, [c for c in cands if langid.classify(c[2])[0] == "ace"]


def make_sentence_sheet(out=OUT, n=200, seed=0):
    cands, ace = _candidates(seed)
    chosen = ace[:n]
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    with open(out / "sentences.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, SENT_COLS); w.writeheader()
        for i, (src, line, t) in enumerate(chosen, 1):
            w.writerow({"id": f"S{i:04d}", "acehnese": t, "indonesian": "", "translator": "", "checker": "", "verdict": "", "notes": f"{src}:{line}"})
    log("sentence-sheet", rows=len(chosen), candidates=len(cands))
    return len(chosen)


def _slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "person"


def make_packs(people=None, per_person=25, seed=0, out=OUT.parent / "packs", count=None):
    """One sheet of `per_person` (20-30) different AcehX sentences for each person, plus PACKS.md saying who checks whose pack.
    Nobody checks their own pack: pack i is checked by the owner of pack i-1 (the first by the last).
    Give `people` (names are put in the translator column) or just `count` (numbered packs with a BLANK translator column: each
    person writes their own name there, and the checker writes theirs)."""
    if people:
        people = [p.strip() for p in people if p.strip()]
        names = people
    else:
        if not count:
            raise ValueError("give the names, or --count for numbered packs")
        names = [f"Pack {i + 1}" for i in range(count)]
    if len(names) < 2:
        raise ValueError("need at least two people: every pack is checked by someone else")
    if not 20 <= per_person <= 30:
        raise ValueError("the prof's brief is 20-30 sentences per person")
    _, ace = _candidates(seed)
    need = per_person * len(names)
    if len(ace) < need:
        raise ValueError(f"only {len(ace)} usable sentences, {need} needed")
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    lines = ["# Translation packs", "", f"{per_person} sentences each. Translate your own pack, then check the pack named in the last column.", "",
             "| person | pack file | checks the pack of |", "|---|---|---|"]
    for i, who in enumerate(names):
        mine = ace[i * per_person:(i + 1) * per_person]
        fname = f"{i + 1:02d}_{_slug(who)}.csv"
        with open(out / fname, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, SENT_COLS); w.writeheader()
            for j, (src, line, t) in enumerate(mine, 1):
                w.writerow({"id": f"P{i + 1:02d}-{j:03d}", "acehnese": t, "indonesian": "", "translator": who if people else "", "checker": "", "verdict": "",
                            "notes": f"{src}:{line}"})
        lines.append(f"| {who} | {fname} | {names[(i - 1) % len(names)]} |")
    (out / "PACKS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "TRANSLATOR_GUIDE.txt").write_text(GUIDE, encoding="utf-8")
    log("packs", people=len(names), per_person=per_person)
    return {"people": len(names), "sentences": need, "dir": str(out)}


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
    """Accepted rows only: translator and checker are different people. `sentences` is one sheet or a list of sheets (the packs).
    Writes pairs.json = the PARALLEL corpus (every accepted row), golden.json = the GOLDEN corpus (accepted rows whose checker
    verdict is "ok": two people agree without edits; evaluation only, never trained on) and glossary.csv. Returns counts."""
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    stats = {"sentences_in": 0, "sentences_accepted": 0, "golden": 0, "words_in": 0, "words_accepted": 0}
    pairs, golden = [], []
    if sentences:
        import glob
        given = [sentences] if isinstance(sentences, (str, Path)) else list(sentences)
        files = [f for g in given for f in (sorted(glob.glob(str(g))) or [g])]       # Windows cmd does not expand 0*.csv itself
        for path in files:
            for r in csv.DictReader(open(path, encoding="utf-8-sig")):
                stats["sentences_in"] += 1
                if _accepted(r, "indonesian") and "?" not in r["indonesian"]:
                    row = {"id": r["id"], "ace": normalize(r["acehnese"])[0], "ind": r["indonesian"].strip(),
                           "source": "human (translator + independent checker)", "translator": r["translator"].strip(), "checker": r["checker"].strip()}
                    pairs.append(row)
                    if (r.get("verdict") or "").strip().lower() == "ok":
                        golden.append(row)
        stats["sentences_accepted"], stats["golden"] = len(pairs), len(golden)
        json.dump(pairs, open(outdir / "pairs.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        json.dump(golden, open(outdir / "golden.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
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
