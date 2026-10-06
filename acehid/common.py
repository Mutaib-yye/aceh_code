"""Shared helpers. Every stage reads/writes JSONL so any stage can be inspected or re-run alone."""
import json, re, unicodedata, hashlib, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def read_jsonl(p):
    with open(p, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def write_jsonl(p, rows):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(p, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n"); n += 1
    return n

def log(stage, **kw):
    print(f"[{stage}] " + " ".join(f"{k}={v}" for k, v in kw.items()), file=sys.stderr)

def strip_diacritics(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def match_key(s):
    """Aggressive key for duplicate detection: case, diacritics, punctuation, spacing all ignored."""
    s = strip_diacritics(s.lower())
    # fold Dutch-era spelling so "njang djipeugot" matches "nyang jipeugot"
    s = re.sub(r"\bdj(?=\w)", "j", s); s = re.sub(r"\btj(?=\w)", "c", s); s = re.sub(r"\bnj(?=[aeiou])", "ny", s)
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def key_hash(s):
    return hashlib.sha1(match_key(s).encode("utf-8")).hexdigest()
