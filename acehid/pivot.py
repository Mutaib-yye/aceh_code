"""NLLB-Seed Acehnese <-> English  ->  Acehnese <-> Indonesian training pairs (pivot through English).

The Acehnese side is the human translation from NLLB-Seed. The Indonesian side is MACHINE output: NLLB-200 English -> Indonesian,
a high-resource direction that is far more reliable than Acehnese -> Indonesian. Pairs are labelled "machine target" and are
filtered by length ratio and the language check. The base NLLB model has probably seen this Seed data already, so the gain is
uncertain: judge it by training with and without it (USE_SEED_PIVOT in the Colab notebook) and comparing the held-out scores."""
import re, json
from pathlib import Path
from .common import ROOT, log
from . import langid
from .normalize import normalize

SEED = ROOT / "data/seed"
SOURCE = "NLLB-Seed (Acehnese: human; Indonesian: NLLB-200 machine translation of the English)"

def load_seed(d=SEED):
    ace = Path(d, "ace_Latn").read_text(encoding="utf-8").splitlines()
    eng = Path(d, "eng_Latn").read_text(encoding="utf-8").splitlines()
    return list(zip((a.strip() for a in ace), (e.strip() for e in eng)))

def candidates(rows):
    out, seen = [], set()
    for a, e in rows:
        a = normalize(a)[0]
        la, le = len(a.split()), len(e.split())
        if not (4 <= la <= 60 and 4 <= le <= 60) or not 0.5 <= la / le <= 2.0 or "http" in a or a in seen:
            continue
        if langid.classify(a)[0] != "ace":
            continue
        seen.add(a); out.append((a, e))
    return out

def translate_en_id(sents, base="facebook/nllb-200-distilled-600M", batch=32):
    import torch
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(base, src_lang="eng_Latn")
    model = AutoModelForSeq2SeqLM.from_pretrained(base).to(dev).eval()
    bos, out = tok.convert_tokens_to_ids("ind_Latn"), []
    order = sorted(range(len(sents)), key=lambda i: len(sents[i]))
    res = {}
    for b in range(0, len(order), batch):
        idx = order[b:b + batch]
        enc = tok([sents[i] for i in idx], return_tensors="pt", padding=True, truncation=True, max_length=200).to(dev)
        with torch.inference_mode():
            gen = model.generate(**enc, forced_bos_token_id=bos, num_beams=4, max_new_tokens=256)
        res.update(zip(idx, tok.batch_decode(gen, skip_special_tokens=True)))
    return [res[i] for i in range(len(sents))]

def run(seed_dir=SEED, out=ROOT / "data/final/seed_pivot/pairs.json", translate=translate_en_id, limit=None):
    cands = candidates(load_seed(seed_dir))[:limit]
    ind = translate([e for _, e in cands])
    rows = []
    for (a, e), i in zip(cands, ind):
        i = " ".join(i.split())
        if not i or i.lower() == e.lower() or not 0.5 <= len(a.split()) / max(len(i.split()), 1) <= 2.0:
            continue
        rows.append({"ace": a, "ind": i, "source": SOURCE})
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(rows, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log("seed-pivot", seed=len(cands), kept=len(rows))
    return {"candidates": len(cands), "kept": len(rows), "out": str(out)}
