"""Stage 1: load AcehX .txt files -> data/extracted/acehx.jsonl and write reports/acehx_audit.md"""
import re, collections, glob, os
from .common import *
from . import langid

def run(raw="data/raw/acehx", out="data/extracted/acehx.jsonl", report="reports/acehx_audit.md"):
    data = []
    for f in sorted(glob.glob(str(ROOT / raw / "*.txt"))):
        name = os.path.basename(f)
        for i, line in enumerate(open(f, encoding="utf-8").read().replace("\r", "").split("\n"), 1):
            t = line.strip()
            if t:
                data.append({"src_file": name, "line": i, "ace_raw": t, "key": key_hash(t)})
    write_jsonl(ROOT / out, data)
    cnt = collections.Counter(r["key"] for r in data)
    per_file = collections.Counter(r["src_file"] for r in data)
    files_by_key = collections.defaultdict(set)
    for r in data:
        files_by_key[r["key"]].add(r["src_file"])
    diac = collections.Counter(c for r in data for c in r["ace_raw"] if ord(c) > 127 and c.isalpha() and not '؀' <= c <= 'ۿ')
    old = {f: sum(bool(re.search(r"\b(dj|tj|nj)\w*", r["ace_raw"].lower())) for r in data if r["src_file"] == f) for f in per_file}
    langs = collections.Counter(langid.classify(r["ace_raw"])[0] for r in data if len(r["ace_raw"].split()) >= 3)
    arabic = sum(bool(re.search(r"[؀-ۿ]", r["ace_raw"])) for r in data)
    short = sum(len(r["ace_raw"].split()) < 3 for r in data)
    long_ = sum(len(r["ace_raw"].split()) > 60 for r in data)
    rep = ["# AcehX audit\n", f"- files: {len(per_file)}", f"- non-empty lines: {len(data)}",
           f"- unique after match_key (case/diacritic/punct/old-spelling insensitive): {len(cnt)}",
           f"- duplicate lines: {len(data)-len(cnt)} ({(len(data)-len(cnt))/len(data):.1%})",
           f"- keys shared across >1 file: {sum(len(v)>1 for v in files_by_key.values())}",
           f"- Arabic-script lines: {arabic}",
           f"- language check (char n-gram model, lines >= 3 words): {dict(langs)}  (ind = Indonesian, mixed = code-mixed/unsure)",
           f"- lines <3 words: {short}; lines >60 words: {long_}",
           "\n## Lines per file (and old-style spellings dj/tj/nj)"]
    rep += [f"- {f}: {n} lines, {old[f]} with dj/tj/nj" for f, n in sorted(per_file.items())]
    rep += ["\n## Non-ASCII letters", ", ".join(f"{c}:{n}" for c, n in diac.most_common(20)), "\n## Most repeated lines"]
    rep += [f"- x{n}: {next(r['ace_raw'] for r in data if r['key']==k)[:100]}" for k, n in cnt.most_common(8)]
    rep += ["\n**Note:** this corpus has NO Indonesian side (monolingual). Confirm with Andrie whether pairs exist."]
    os.makedirs(ROOT / "reports", exist_ok=True)
    open(ROOT / report, "w", encoding="utf-8").write("\n".join(rep) + "\n")
    log("audit", lines=len(data), unique=len(cnt))
    return data
