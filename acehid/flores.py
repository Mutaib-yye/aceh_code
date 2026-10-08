"""FLORES-200 / FLORES+ Acehnese (ace_Latn) <-> Indonesian (ind_Latn) -> data/final/flores/{dev,devtest}.json

FLORES is professionally translated, sentence-aligned Wikipedia-style text (dev 997 + devtest 1012 sentences; the third split is hidden).
License CC-BY-SA 4.0 (same as NusaX). Use: dev -> training (+ a held-out slice for model selection), devtest -> TEST ONLY.
Benchmarks built on FLORES sentences (Belebele, SIB-200) must never be added to training: they would leak the devtest set.

Input: the original flores200_dataset.tar(.gz), a .zip, or a folder. Recognised file names (any folder depth):
  ace_Latn.dev / ace_Latn.devtest        (FLORES-200: flores200_dataset/{dev,devtest}/<lang>.<split>)
  dev.ace_Latn / devtest.ace_Latn        (FLORES+ text files)
  {dev,devtest}/ace_Latn[.txt]           (FLORES+ folder layout)
"""
import json, re, tarfile, zipfile, datetime
from pathlib import Path
from .common import *
from .normalize import normalize

LANGS = {"ace_Latn": "ace", "ind_Latn": "ind"}
LICENSE = "CC-BY-SA-4.0 (FLORES-200, NLLB Team et al. 2022, https://github.com/facebookresearch/flores)"
_NAME = re.compile(r"(?:^|[./])(?P<a>dev|devtest)\.(?P<l1>ace_Latn|ind_Latn)$|(?:^|/)(?P<l2>ace_Latn|ind_Latn)\.(?P<b>dev|devtest)$"
                   r"|(?:^|/)(?P<c>dev|devtest)/(?P<l3>ace_Latn|ind_Latn)(?:\.txt)?$")

def _classify(member):
    m = _NAME.search(member.replace("\\", "/"))
    if not m:
        return None
    split = m["a"] or m["b"] or m["c"]
    lang = m["l1"] or m["l2"] or m["l3"]
    return split, LANGS[lang]

def read_files(path):
    """{(split, 'ace'|'ind'): [lines]} from a tar/zip/folder. Raises if a split is missing a side."""
    path = Path(path).expanduser()
    found = {}
    if path.is_dir():
        for f in path.rglob("*"):
            k = f.is_file() and _classify(str(f.relative_to(path)))
            if k:
                found[k] = f.read_text(encoding="utf-8").splitlines()
    elif zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                k = _classify(n)
                if k:
                    found[k] = z.read(n).decode("utf-8").splitlines()
    elif tarfile.is_tarfile(path):
        with tarfile.open(path) as t:
            for m in t:
                k = m.isfile() and _classify(m.name)
                if k:
                    found[k] = t.extractfile(m).read().decode("utf-8").splitlines()
    else:
        raise ValueError(f"{path}: not a folder, .zip or .tar")
    splits = sorted({s for s, _ in found})
    if not splits:
        raise ValueError(f"{path}: no ace_Latn/ind_Latn dev/devtest files found")
    for s in splits:
        if (s, "ace") not in found or (s, "ind") not in found:
            raise ValueError(f"{path}: split {s!r} has only one language side")
        if len(found[(s, "ace")]) != len(found[(s, "ind")]):
            raise ValueError(f"{path}: split {s!r} is not aligned ({len(found[(s, 'ace')])} ace vs {len(found[(s, 'ind')])} ind lines)")
    return found

def run(path, outdir="data/final/flores"):
    found = read_files(path)
    out = ROOT / outdir; out.mkdir(parents=True, exist_ok=True)
    sizes = {}
    for split in sorted({s for s, _ in found}):
        pairs = []
        for i, (a, b) in enumerate(zip(found[(split, "ace")], found[(split, "ind")])):
            a, b = " ".join(a.split()), " ".join(b.split())
            if a and b:
                pairs.append({"ace": normalize(a)[0], "ind": b, "id": f"FLORES_{split}_{i:04d}"})
        json.dump(pairs, open(out / f"{split}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        sizes[split] = len(pairs)
    json.dump({"source": "FLORES-200", "license": LICENSE, "created": datetime.date.today().isoformat(), "pairs": sizes,
               "use": {"dev": "training (minus a held-out validation slice)", "devtest": "test only"}},
              open(out / "README.json", "w", encoding="utf-8"), indent=1)
    log("flores", **sizes)
    return sizes
