"""Evaluate a translation provider on NusaX-MT valid+test (human-translated Aceh->Indonesian) with sacreBLEU: chrF, BLEU, TER.
Outputs are cached per (provider/model tag, sentence) in data/eval/cache/, so re-runs are free and interrupted runs resume.
NusaX is modern review/social-media text; scores do NOT predict quality on literary hikayat."""
import csv, json, os, hashlib
import sacrebleu
from .common import *
from .translate import Translator

CACHE_DIR = ROOT / "data/eval/cache"

def load(split):
    return [(r["acehnese"], r["indonesian"]) for r in csv.DictReader(open(ROOT / f"data/raw/external/nusax/{split}.csv", encoding="utf-8"))]

def _cache_path(tag):
    return CACHE_DIR / (hashlib.sha1(tag.encode()).hexdigest()[:12] + ".jsonl")

def evaluate(tr: Translator, splits=("valid", "test"), limit=None):
    cache_p = _cache_path(tr.tag); CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = {r["ace"]: r["ind"] for r in read_jsonl(cache_p)} if cache_p.exists() else {}
    res = {"system": tr.tag}
    for sp in splits:
        pairs = load(sp)[:limit]
        todo = [a for a, _ in pairs if a not in cache]
        for b in range(0, len(todo), 20):
            chunk = todo[b:b + 20]
            for a, x in zip(chunk, tr.translate(chunk)):
                cache[a] = x["ind"]
            write_jsonl(cache_p, [{"ace": a, "ind": i} for a, i in cache.items()])
        hyp = [cache[a] for a, _ in pairs]; ref = [r for _, r in pairs]
        res[sp] = {"n": len(pairs), "chrF": round(sacrebleu.corpus_chrf(hyp, [ref]).score, 2),
                   "BLEU": round(sacrebleu.corpus_bleu(hyp, [ref]).score, 2), "TER": round(sacrebleu.corpus_ter(hyp, [ref]).score, 2)}
    return res

def write_report(results, path="reports/eval_nusax.md"):
    rows = ["# NusaX-MT evaluation (Acehnese -> Indonesian)\n",
            "Human reference translations; sacreBLEU (chrF, BLEU: higher is better, TER: lower is better).",
            "NusaX is modern review-style text, so these numbers do **not** predict quality on literary hikayat.\n",
            "| system | split | n | chrF | BLEU | TER |", "|---|---|---|---|---|---|"]
    for r in results:
        for sp in ("valid", "test"):
            if sp in r:
                m = r[sp]; rows.append(f"| {r['system']} | {sp} | {m['n']} | {m['chrF']} | {m['BLEU']} | {m['TER']} |")
    open(ROOT / path, "w", encoding="utf-8").write("\n".join(rows) + "\n")
    return "\n".join(rows)
