"""NusaX-MT (IndoNLP/nusax, datasets/mt) -> Atlas format. The only human-translated Aceh<->Indonesian pairs we have (1,000).
License: dataset CC-BY-SA 4.0 (share-alike!) - keep it in its own files, never mixed into other sources' files.
Original splits are preserved (train 500 / valid 100 / test 400); valid+test are the EVALUATION set and must stay out of training."""
import csv, json, datetime
from .common import *
from .normalize import normalize
from . import export as ex

SPLITS = {"train": "train", "valid": "validation", "test": "test"}
LICENSE = "CC-BY-SA-4.0 (NusaX-MT, Winata et al. 2023, https://github.com/IndoNLP/nusax)"

def rows(split):
    for i, r in enumerate(csv.DictReader(open(ROOT / f"data/raw/external/nusax/{split}.csv", encoding="utf-8"))):
        ace = " ".join(r["acehnese"].split()); ind = " ".join(r["indonesian"].split())
        norm, rules = normalize(ace)
        yield {"id": f"NUSAX_{split}_{i:04d}", "source_id": "NUSAX", "title": "NusaX-MT", "license": LICENSE, "page": None,
               "ace_raw": ace, "ace_normalized": norm, "norm_rules": rules, "ind_raw": ind, "translation_status": "human_translated",
               "screening": "KEEP", "dedup": "unique", "tags": [f"nusax_{split}"]}

def run(outdir="data/final/nusax"):
    out = ROOT / outdir; out.mkdir(parents=True, exist_ok=True)
    allrows, sizes = [], {}
    for sp, name in SPLITS.items():
        rs = list(rows(sp)); allrows += rs; sizes[name] = len(rs)
        json.dump([{"ace": r["ace_normalized"], "ind": r["ind_raw"]} for r in rs], open(out / f"{name}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    master = [ex.to_atlas_record(r, "benchmark_parallel") for r in allrows]
    json.dump({"version": "nusax-mt-1.0", "created": datetime.date.today().isoformat(), "license": LICENSE, "n_pairs": len(master), "data": master},
              open(out / "atlas_nusax.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log("nusax", pairs=len(master), **sizes)
    return allrows
