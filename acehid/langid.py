"""Offline language check: Acehnese vs Indonesian, plus MIXED for code-mixed lines.

Character 1-4-gram naive-Bayes log-likelihood ratio, trained on
  Acehnese   : AcehX lines (monolingual, Latin script)
  Indonesian : NusaX-MT *train* Indonesian side only
and evaluated on NusaX valid+test (both sides), which the model never saw.
The model is a small gzip'd JSON (config/langid_model.json.gz), so there is no download at run time.
This is a screening aid, not ground truth: short lines (< 3 words) are unreliable.
"""
import gzip, json, math, re, random, collections, csv, glob
from .common import ROOT

MODEL_PATH = ROOT / "config" / "langid_model.json.gz"
_model = None

def _norm(s):
    return " " + re.sub(r"[^\w' ]+", " ", s.lower()) + " "

def _grams(s, ns=(1, 2, 3, 4)):
    s = _norm(s)
    return [s[i:i + k] for k in ns for i in range(len(s) - k + 1)]

def train(ace_lines, ind_lines, min_count=8):
    ca = collections.Counter(g for t in ace_lines for g in _grams(t))
    ci = collections.Counter(g for t in ind_lines for g in _grams(t))
    na, ni = sum(ca.values()), sum(ci.values())
    keys = {g for g in set(ca) | set(ci) if ca[g] + ci[g] >= min_count}
    V = len(keys)
    llr = {g: round(math.log((ca[g] + .1) / (na + .1 * V)) - math.log((ci[g] + .1) / (ni + .1 * V)), 3) for g in keys}
    return {"llr": llr, "n_ace_lines": len(ace_lines), "n_ind_lines": len(ind_lines)}

def load():
    global _model
    if _model is None:
        with gzip.open(MODEL_PATH, "rt", encoding="utf-8") as f:
            _model = json.load(f)
    return _model

def score(s, model=None):
    """Mean per-character log-likelihood ratio. > 0 leans Acehnese, < 0 leans Indonesian."""
    llr = (model or load())["llr"]
    return sum(llr.get(g, 0.0) for g in _grams(s)) / max(1, len(_norm(s)))

# thresholds calibrated on NusaX valid (see build()); lines between them are "mixed/unsure"
ACE_T, IND_T = 0.4, -0.4

def classify(s, model=None):
    """-> (label, score) with label in {'ace','ind','mixed'}"""
    x = score(s, model)
    return ("ace" if x >= ACE_T else "ind" if x <= IND_T else "mixed"), round(x, 3)

def _nusax(split):
    with open(ROOT / "data/raw/external/nusax" / f"{split}.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def build(acehx_glob="data/raw/acehx/*.txt", n_ace=60000, seed=0):
    random.seed(seed)
    ace = [l.strip() for f in sorted(glob.glob(str(ROOT / acehx_glob))) for l in open(f, encoding="utf-8") if len(l.split()) >= 3]
    random.shuffle(ace)
    ind = [r["indonesian"] for r in _nusax("train")]
    m = train(ace[:n_ace], ind)
    MODEL_PATH.parent.mkdir(exist_ok=True)
    with gzip.open(MODEL_PATH, "wt", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, separators=(",", ":"))
    return evaluate(m)

def evaluate(model=None):
    """Accuracy on NusaX valid+test (held out). Returns dict, also the numbers quoted in the reports."""
    out = {}
    for sp in ("valid", "test"):
        rows = _nusax(sp)
        a = [classify(r["acehnese"], model)[0] for r in rows]
        i = [classify(r["indonesian"], model)[0] for r in rows]
        out[sp] = {"n_per_side": len(rows), "ace_as_ace": sum(x == "ace" for x in a) / len(a),
                   "ace_as_ind": sum(x == "ind" for x in a) / len(a), "ind_as_ind": sum(x == "ind" for x in i) / len(i),
                   "ind_as_ace": sum(x == "ace" for x in i) / len(i), "unsure": (sum(x == "mixed" for x in a) + sum(x == "mixed" for x in i)) / (2 * len(rows))}
    return out
