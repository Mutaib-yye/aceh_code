"""Stage 5: deduplicate NEW data against AcehX and itself.
  exact_dup  same match_key (case/diacritic/punctuation/Dutch-era-spelling insensitive) -> DUPLICATE_ACEHX / DUPLICATE_SELF
  near_dup   MinHash-LSH on char 5-grams, Jaccard >= 0.85, sentences >= 4 words        -> NEAR_DUP_REVIEW (flagged for a human, NOT auto-deleted)
Limit: this finds spelling/format variants, not paraphrases with the same meaning; those need a human or a multilingual
sentence-embedding model (not available offline here)."""
import os, pickle, collections
from datasketch import MinHash, MinHashLSH
from .common import *

NUM_PERM, THRESH, CACHE = 64, 0.85, ROOT / "data/deduplicated/.acehx_lsh.pkl"

def shingles(s, n=5):
    s = match_key(s).replace(" ", "_")
    return {s[i:i + n] for i in range(max(1, len(s) - n + 1))}

def mh(s):
    m = MinHash(num_perm=NUM_PERM)
    for g in shingles(s):
        m.update(g.encode())
    return m

def build_ref(path, cache=CACHE, rebuild=False):
    """Index of the reference corpus (AcehX): exact keys + LSH. Cached; delete the .pkl or pass rebuild=True after AcehX changes."""
    cache = str(cache)
    if os.path.exists(cache) and not rebuild and os.path.getmtime(cache) >= os.path.getmtime(path):
        return pickle.load(open(cache, "rb"))
    lsh, keys = MinHashLSH(threshold=THRESH, num_perm=NUM_PERM), {}
    for i, r in enumerate(read_jsonl(path)):
        if r["key"] in keys:
            continue                                      # first occurrence only
        keys[r["key"]] = f"{r['src_file']}:{r['line']}"
        if len(r["ace_raw"].split()) >= 4:
            lsh.insert(f"{i}|{keys[r['key']]}", mh(r["ace_raw"]))
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    pickle.dump((lsh, keys), open(cache, "wb"))
    return lsh, keys

def run(rows, ref_path=ROOT / "data/extracted/acehx.jsonl", ref=None):
    """Adds dedup / dedup_ref to each row. ref=(lsh, keys) can be passed in (the web app keeps it in memory).
    If AcehX is not available the ACEHX comparison is skipped and rows get dedup_checked_vs_acehx=False."""
    if ref is None and os.path.exists(ref_path):
        ref = build_ref(ref_path)
    lsh, ref_keys = ref if ref else (None, {})
    seen, out, c = {}, [], collections.Counter()
    for r in rows:
        k = key_hash(r["ace_raw"])
        r["dedup"], r["dedup_ref"], r["dedup_checked_vs_acehx"] = "unique", None, bool(ref)
        if k in ref_keys:
            r["dedup"], r["dedup_ref"] = "DUPLICATE_ACEHX", ref_keys[k]
        elif k in seen:
            r["dedup"], r["dedup_ref"] = "DUPLICATE_SELF", seen[k]
        else:
            seen[k] = r["id"]
            if lsh is not None and len(r["ace_raw"].split()) >= 4:
                hits = lsh.query(mh(r["ace_raw"]))
                if hits:
                    r["dedup"], r["dedup_ref"] = "NEAR_DUP_REVIEW", hits[0].split("|", 1)[1]
        c[r["dedup"]] += 1
        out.append(r)
    log("dedup", rows=len(out), vs_acehx=bool(ref), **dict(c))
    return out
