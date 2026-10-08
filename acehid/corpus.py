"""Build the fine-tuning set: data/final/combined/{train,validation,test_*}.json + manifest.json

Sources (only human-translated pairs; machine drafts never enter training):
  NusaX-MT   train -> train | valid -> validation | test -> test_nusax          (CC-BY-SA 4.0)
  FLORES-200 dev   -> train, except a fixed 200-sentence slice (1/4 if smaller) -> validation    (CC-BY-SA 4.0)
             devtest -> test_flores
  Hikayat    data/final/hikayat/<book>/{train,validation,test}.json (page-block split by `hikayat-pairs`) -> same roles
  --extra    reviewed pair files [{ace, ind}] -> train  (e.g. reviewed hikayat pairs from `export`)
  --extra-test name=path  -> an extra test set (e.g. hikayat test split)

Leak control (a test score is only honest if the model never saw those sentences):
  1. exact: a training pair is dropped if its Acehnese OR Indonesian side matches any validation/test sentence (match_key)
  2. near:  dropped if its Acehnese side is >= NEAR% similar (rapidfuzz ratio on match_key) to a validation/test sentence
  3. duplicate training pairs are collapsed
Every drop is counted in manifest.json."""
import json, hashlib, datetime
from pathlib import Path
from .common import *

NEAR = 90
FLORES_VALID = 200
LICENSES = {"nusax": "CC-BY-SA-4.0 (NusaX-MT)", "flores": "CC-BY-SA-4.0 (FLORES-200)"}

def _load(p):
    return [{"ace": r["ace"], "ind": r["ind"]} for r in json.load(open(p, encoding="utf-8"))]

def _tag(rows, src):
    return [{**r, "src": src} for r in rows]

def _held_out(rows, n):
    """Deterministic slice that does not depend on file order: the n rows with the smallest hash of their text."""
    order = sorted(range(len(rows)), key=lambda i: hashlib.sha1(match_key(rows[i]["ace"]).encode()).hexdigest())
    pick = set(order[:n])
    return [r for i, r in enumerate(rows) if i not in pick], [r for i, r in enumerate(rows) if i in pick]

def remove_leaks(train, held, near=NEAR):
    """-> (clean_train, stats). `held` = every validation+test row."""
    keys = {match_key(r["ace"]) for r in held} | {match_key(r["ind"]) for r in held}
    stats = {"exact_leak": 0, "near_leak": 0, "dup_in_train": 0}
    kept, seen = [], set()
    for r in train:
        ka, ki = match_key(r["ace"]), match_key(r["ind"])
        if ka in keys or ki in keys:
            stats["exact_leak"] += 1
        elif (ka, ki) in seen:
            stats["dup_in_train"] += 1
        else:
            seen.add((ka, ki)); kept.append(r)
    if near and kept and held:
        from rapidfuzz import process, fuzz
        held_keys = [match_key(r["ace"]) for r in held]
        sim = process.cdist([match_key(r["ace"]) for r in kept], held_keys, scorer=fuzz.ratio, score_cutoff=near, workers=-1)
        bad = set((sim.max(axis=1) >= near).nonzero()[0].tolist())
        stats["near_leak"] = len(bad)
        kept = [r for i, r in enumerate(kept) if i not in bad]
    return kept, stats

def quran_pairs(qdir="data/raw/external/quran", ace_ed="ace-tgkhmahjiddinju", ind_ed="ind-indonesianislam", max_words=60):
    """Verse pairs: Acehnese (free rhyming translation by Tgk. Mahjiddin Jusuf) x Indonesian (Kemenag). Training only, off by default.
    Kept only when both sides are 3..max_words words with a length ratio 0.5-2 (the Acehnese is free verse, so long verses drift)."""
    from .normalize import normalize
    d = ROOT / qdir
    ace = {(v["chapter"], v["verse"]): v["text"] for v in json.load(open(d / f"{ace_ed}.json", encoding="utf-8"))["quran"]}
    ind = {(v["chapter"], v["verse"]): v["text"] for v in json.load(open(d / f"{ind_ed}.json", encoding="utf-8"))["quran"]}
    out = []
    for k in sorted(ace.keys() & ind.keys()):
        a, b = " ".join(ace[k].split()), " ".join(ind[k].split())
        na, nb = len(a.split()), len(b.split())
        if 3 <= na <= max_words and 3 <= nb <= max_words and 0.5 <= na / nb <= 2:
            out.append({"ace": normalize(a)[0], "ind": b})
    return out

def build(outdir="data/final/combined", extra=(), extra_test=(), flores_dir="data/final/flores", nusax_dir="data/final/nusax",
          hikayat_dir="data/final/hikayat", quran=False, near=NEAR):
    nusax, flores, out = ROOT / nusax_dir, ROOT / flores_dir, ROOT / outdir
    train = _tag(_load(nusax / "train.json"), "nusax")
    valid = _tag(_load(nusax / "validation.json"), "nusax")
    tests = {"nusax": _tag(_load(nusax / "test.json"), "nusax")}
    sources = ["nusax"]
    if (flores / "dev.json").exists():
        fd = _load(flores / "dev.json")
        f_train, f_valid = _held_out(fd, min(FLORES_VALID, len(fd) // 4))
        train += _tag(f_train, "flores"); valid += _tag(f_valid, "flores"); sources.append("flores")
    if (flores / "devtest.json").exists():
        tests["flores"] = _tag(_load(flores / "devtest.json"), "flores")
    for book in sorted((ROOT / hikayat_dir).glob("*/train.json")):      # bilingual hikayat books (python -m acehid hikayat-pairs)
        d = book.parent
        train += _tag(_load(d / "train.json"), "hikayat"); valid += _tag(_load(d / "validation.json"), "hikayat")
        tests.setdefault("hikayat", []).extend(_tag(_load(d / "test.json"), "hikayat"))
        sources.append(f"hikayat:{d.name}")
    if quran:
        train += _tag(quran_pairs(), "quran"); sources.append("quran")
    for p in extra:
        train += _tag(_load(p), Path(p).stem)
    for spec in extra_test:
        name, p = spec.split("=", 1)
        tests[name] = _tag(_load(p), name)
    held = valid + [r for t in tests.values() for r in t]
    n_before = len(train)
    train, stats = remove_leaks(train, held, near)
    out.mkdir(parents=True, exist_ok=True)
    def dump(name, rows):
        json.dump([{"ace": r["ace"], "ind": r["ind"], "src": r["src"]} for r in rows], open(out / name, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    dump("train.json", train); dump("validation.json", valid)
    for k, rows in tests.items():
        dump(f"test_{k}.json", rows)
    count = lambda rows: {s: sum(r["src"] == s for r in rows) for s in sorted({r["src"] for r in rows})}
    manifest = {"created": datetime.date.today().isoformat(), "sources": sources + [Path(p).stem for p in extra],
                "license": "CC-BY-SA-4.0 (share-alike: NusaX-MT + FLORES-200)" + (" + hikayat: Depdikbud publication, confirm reuse terms" if any(s.startswith("hikayat") for s in sources) else "") + (" + Quran translation (c) Tgk. Mahjiddin Jusuf: research use, ask Andrie" if quran else "") + (" + extra files: check their licenses" if extra else ""),
                "train": {"file": "train.json", "n": len(train), "by_source": count(train), "before_leak_removal": n_before, **stats},
                "validation": {"file": "validation.json", "n": len(valid), "by_source": count(valid)},
                "tests": {k: {"file": f"test_{k}.json", "n": len(v)} for k, v in tests.items()},
                "near_threshold": near}
    json.dump(manifest, open(out / "manifest.json", "w", encoding="utf-8"), indent=1)
    log("build-train", train=len(train), validation=len(valid), **{f"test_{k}": len(v) for k, v in tests.items()}, **stats)
    return manifest
