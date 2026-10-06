"""Stage 7: QC gates + Atlas JSON export + source-level train/validation/test split.

Atlas master schema = section 17 of Andrie's project plan (UNCONFIRMED: ask him for the real Atlas schema; only `to_atlas_record` needs to change).
  {"id","source":{"title","type","page","license"},"language":{"source":"ace","target":"ind"},
   "text":{"ace_raw","ace_normalized","ind_raw","ind_normalized"},
   "processing":{"screening","deduplication","translation","norm_rules"},"quality"}
"""
import json, datetime, collections, csv, re
from .common import *

STATUS_QUALITY = {"human_translated": "high", "human_validated": "high", "reviewed": "medium", "machine_draft": "low"}

def qc(r):
    a, b = len(r["ace_normalized"].split()), len(r.get("ind_raw", "").split())
    if not b:
        return "no_translation"
    if not (0.4 <= b / max(a, 1) <= 2.5):
        return "bad_length_ratio"
    if r["ace_normalized"].strip().lower() == r["ind_raw"].strip().lower():
        return "identical_to_source"       # untranslated copy
    return None

def to_atlas_record(r, source_type="hikayat"):
    return {"id": r["id"],
            "source": {"title": r["title"], "type": source_type, "page": r.get("page"), "license": r.get("license", "UNKNOWN")},
            "language": {"source": "ace", "target": "ind"},
            "text": {"ace_raw": r["ace_raw"], "ace_normalized": r["ace_normalized"], "ind_raw": r["ind_raw"],
                     "ind_normalized": r.get("ind_normalized", r["ind_raw"])},
            "processing": {"screening": "passed", "deduplication": "unique", "translation": r["translation_status"],
                           "norm_rules": r.get("norm_rules", []), "tags": r.get("tags", [])},
            "quality": STATUS_QUALITY.get(r["translation_status"], "low")}

def split_by_source(rows):
    """Whole sources go to one split so near-identical text cannot leak across splits."""
    by = collections.defaultdict(list)
    for r in rows:
        by[r["source_id"]].append(r)
    total = len(rows); tgt = {"train": .8 * total, "validation": .1 * total, "test": .1 * total}
    got = collections.Counter(); out = {k: [] for k in tgt}
    if len(by) < 3:
        log("split", warning=f"only {len(by)} source(s): cannot split by source without leaving splits empty; all trainable rows go to train")
        out["train"] = list(rows)
        return out
    for sid in sorted(by, key=lambda k: -len(by[k])):
        name = max(tgt, key=lambda k: tgt[k] - got[k]); out[name] += by[sid]; got[name] += len(by[sid])
    return out

def export(rows, version="ace-id-v0.1", outdir="data/final", include_drafts=False, source_type="hikayat", prefix=""):
    """rows: translated rows. Writes {prefix}atlas_master.json and {prefix}{train,validation,test}.json. Returns stats."""
    good, bad = [], collections.Counter()
    for r in rows:
        if r.get("screening") != "KEEP" or r.get("dedup") != "unique":
            bad["not_keep_or_not_unique"] += 1; continue
        why = qc(r) if "ind_raw" in r else "no_translation"
        if why:
            bad[why] += 1; continue
        good.append(r)
    master = [to_atlas_record(r, source_type) for r in good]
    out = ROOT / outdir; out.mkdir(parents=True, exist_ok=True)
    json.dump({"version": version, "created": datetime.date.today().isoformat(), "n_pairs": len(master), "data": master},
              open(out / f"{prefix}atlas_master.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    trainable = [r for r in good if include_drafts or STATUS_QUALITY.get(r["translation_status"]) != "low"]
    sizes = {}
    for name, rs in split_by_source(trainable).items():
        json.dump([{"ace": r["ace_normalized"], "ind": r["ind_raw"]} for r in rs], open(out / f"{prefix}{name}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        sizes[name] = len(rs)
    stats = {"atlas_records": len(master), "trainable": len(trainable), "splits": sizes, "rejected": dict(bad)}
    log("export", **{k: v for k, v in stats.items() if k != "splits"}, splits=sizes)
    return stats
