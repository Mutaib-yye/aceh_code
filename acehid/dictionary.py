"""Word lookup in the Kamus Aceh-Indonesia (1985) list that Andrie shared (A-L only, extracted automatically, not fully validated).

The list is unvalidated and copyrighted, so it is not training data and the app shows every entry with its page and validation
status. It lives in the project's one fixed place, data/glossary/ (space/core.py ensure_glossary() downloads it from the repo when
missing); the copy committed as data/kamus_aceh_indonesia_1985.csv and data/raw/kamus/ are also accepted. Lookup is a separate tool from sentence translation."""
import csv, re, bisect
from pathlib import Path
from .common import ROOT, strip_diacritics

NAME = "kamus_aceh_indonesia_1985.csv"
CSV = ROOT / "data/glossary" / NAME
FALLBACKS = (ROOT / "data" / NAME, ROOT / "data/raw/kamus" / NAME)

def fold(s):
    """Lower case, no accents, no apostrophes: 'ab, ab and AB all match."""
    return re.sub(r"['’`´]", "", strip_diacritics(s).lower()).strip()

def _status(source):
    s = source.lower()
    return "unverified-crossref" if "rujuk_silang" in s else ("unverified" if "belum" in s or "bukan validasi" in s else "unknown")

class Dictionary:
    def __init__(self, path=CSV):
        self.path, self.entries, self.by_key, self.keys = Path(path), [], {}, []
        if not self.path.exists() and Path(path) == CSV:
            self.path = next((f for f in FALLBACKS if f.exists()), self.path)
        if self.path.exists():
            self._load()

    def _load(self):
        with open(self.path, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                heads = [h.strip() for h in re.split(r"[,\n]", r.get("target") or r.get("input") or "") if h.strip()]
                meaning = " ".join((r.get("translate_ind") or "").split())
                page = re.search(r"hlm\. (\d+)", r.get("source", ""))
                if not heads or not meaning:
                    continue
                e = {"word": heads[0], "variants": heads[1:], "meaning": meaning, "page": int(page.group(1)) if page else None,
                     "status": _status(r.get("source", ""))}
                self.entries.append(e)
                for h in heads:
                    self.by_key.setdefault(fold(h), []).append(e)
        self.keys = sorted(self.by_key)

    @property
    def loaded(self):
        return bool(self.entries)

    def lookup(self, word):
        """Exact matches for one word (accents, case and apostrophes ignored), duplicates removed. [] when absent."""
        seen, out = set(), []
        for e in self.by_key.get(fold(word), []):
            if id(e) not in seen:
                seen.add(id(e)); out.append(e)
        return out

    def search(self, q, limit=30):
        """-> {'exact': [...], 'prefix': [...], 'meaning': [...]}: Acehnese headwords, then Indonesian meanings containing q."""
        key = fold(q)
        if not key:
            return {"exact": [], "prefix": [], "meaning": []}
        exact = self.lookup(q)
        used = {id(e) for e in exact}
        prefix = []
        i = bisect.bisect_left(self.keys, key)
        while i < len(self.keys) and self.keys[i].startswith(key) and len(prefix) < limit:
            for e in self.by_key[self.keys[i]]:
                if id(e) not in used:
                    used.add(id(e)); prefix.append(e)
            i += 1
        meaning = []
        if len(key) >= 3:
            pat = re.compile(r"\b" + re.escape(key), re.I)
            for e in self.entries:
                if id(e) not in used and pat.search(e["meaning"]):
                    meaning.append(e)
                    if len(meaning) >= limit:
                        break
        return {"exact": exact, "prefix": prefix[:limit], "meaning": meaning}
