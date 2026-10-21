"""Translation core of the hosted app (no UI code, so it is unit-tested without Gradio).

Model: MODEL_ID env var / Space variable (our fine-tuned NLLB, e.g. <user>/ace-id-nllb), default: base NLLB-200 600M.
Input is normalized exactly like the training data (same rules as acehid/normalize.py; tests/test_space.py checks they agree),
split into sentences (NLLB is trained on single sentences), translated in batches with beam search, and cached."""
import os, re, csv, json, unicodedata

BASE_MODEL = "facebook/nllb-200-distilled-600M"
SRC, TGT = "ace_Latn", "ind_Latn"
MAX_CHARS = 5000
MIN_WORDS = 3

# --- normalization (copy of acehid/normalize.py, kept identical by a test) ---------------------------------------------
DIAERESIS = str.maketrans({"ö": "o", "Ö": "O", "ë": "e", "Ë": "E", "ü": "u", "Ü": "U", "ï": "i", "Ï": "I", "ä": "a", "Ä": "A"})
QUOTES = str.maketrans({"’": "'", "‘": "'", "`": "'", "´": "'", "“": '"', "”": '"', "–": "-", "—": "-"})
OLD = [(re.compile(r"(?<![\w])dj(?=\w)", re.I), "j"), (re.compile(r"(?<![\w])tj(?=\w)", re.I), "c"),
       (re.compile(r"(?<![\w])nj(?=[aeiouèéëôö])", re.I), "ny")]

def _case(orig, new):
    return new.upper() if orig.isupper() and len(orig) > 1 else (new.capitalize() if orig[0].isupper() else new)

def normalize(s):
    t = unicodedata.normalize("NFC", s).translate(QUOTES)
    t = re.sub(r"[ ​‌‍﻿]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    for pat, rep in OLD:
        t = pat.sub(lambda m: _case(m.group(0), rep), t)
    return t.translate(DIAERESIS)

def split_sentences(line):
    return [s for s in re.split(r"(?<=[.!?])\s+", line.strip()) if s]

# --- word glossary (optional): Kamus Aceh-Indonesia (1985) A-L, downloaded from the project's repo once ------
GLOSSARY_NAME = "kamus_aceh_indonesia_1985.csv"
def _is_glossary(path):
    """A CSV counts only if its header has the dictionary's columns (so another CSV is never picked up by mistake)."""
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            head = f.readline().lower()
    except OSError:
        return False
    return "translate_ind" in head and "target" in head

def glossary_dest():
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "glossary", GLOSSARY_NAME))

def ensure_glossary():
    """The one fixed place for the dictionary list (data/glossary/): use it if it is there, otherwise download it from GitHub. -> path or None."""
    dest = glossary_dest()
    return dest if _is_glossary(dest) else fetch_glossary(dest)

GLOSSARY_URLS = ["https://raw.githubusercontent.com/Mutaib-yye/aceh_code/claude/dataset-product-build-108xu8/data/kamus_aceh_indonesia_1985.csv",
                 "https://raw.githubusercontent.com/Mutaib-yye/aceh_code/claude/dataset-product-build-108xu8/data/glossary/kamus_aceh_indonesia_1985.csv"]

def fetch_glossary(dest=None, urls=None):
    """Download the dictionary CSV from the project's GitHub repo (works while the repo is public) into data/glossary/. -> path or None."""
    import urllib.request
    dest = dest or glossary_dest()
    for url in urls or GLOSSARY_URLS:
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                data = r.read()
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(data)
            if _is_glossary(dest):
                return dest
            os.remove(dest)
        except Exception:
            continue
    return None

WORD = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*")

def _fold(s):
    """Lower case, no accents, no apostrophes: ampéh, 'ampeh and AMPEH are the same key."""
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return re.sub(r"['’`´]", "", s).lower().strip()

STOP = {"yang", "dan", "untuk", "dengan", "dari", "pada", "itu", "ini", "atau", "ada", "tidak", "dalam", "akan", "juga", "bagi", "oleh"}

def _content(s):
    """Folded words that can carry a meaning: 3+ letters, not a common function word."""
    return {_fold(w) for w in WORD.findall(s) if len(w) >= 3} - STOP

class Glossary:
    """Acehnese headword -> Indonesian meanings. When a word has several meanings, the one that shares most words with the
    model's Indonesian translation is ranked first: a simple word-sense disambiguation aid."""
    def __init__(self, entries):
        self.entries = entries

    @classmethod
    def load(cls, path=None):
        path = path or ensure_glossary()
        if not path or not os.path.isfile(path):
            return None
        entries = {}
        with open(path, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                meaning = " ".join((r.get("translate_ind") or "").split())
                if r.get("error_category", "none") != "none" or not meaning:      # skip the synthetic misspelling rows
                    continue
                for head in (r.get("target") or "").split(","):
                    key = _fold(head)
                    if len(key) >= 2 and meaning not in entries.setdefault(key, []):
                        entries[key].append(meaning)
        return cls(entries) if entries else None

    def lookup(self, text, indonesian=""):
        """-> [(word as typed, [(meaning, overlap with the translation)] best first)] for the words found in the glossary."""
        out_words = _content(indonesian)
        seen, found = set(), []
        for w in WORD.findall(text):
            key = _fold(w)
            if key in seen or key not in self.entries:
                continue
            seen.add(key)
            scored = [(m, len(_content(m) & out_words)) for m in self.entries[key]]
            found.append((w, sorted(scored, key=lambda t: -t[1])))
        return found

# --- accuracy numbers shipped with the model (training_log.json written by `python -m acehid train`) --------------------
SOURCE_NAMES = {"nusax": "NusaX-MT", "flores": "FLORES-200", "hikayat": "Hikayat Abu Sammah (Depdikbud)"}

def sources_text(info):
    by = (info or {}).get("train_by_source") or {}
    return ", ".join(SOURCE_NAMES.get(k, k) for k in by) or "NusaX-MT and FLORES-200"

def load_info(model_id):
    p = os.path.join(model_id, "training_log.json")
    try:
        if not os.path.isdir(model_id):
            from huggingface_hub import hf_hub_download
            p = hf_hub_download(model_id, "training_log.json")
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None

def accuracy_markdown(info, model_id):
    if not info or "tests" not in info:
        return (f"**Model:** `{model_id}` (base NLLB-200, not fine-tuned yet). No accuracy numbers yet: they appear here "
                "after the Colab training run.")
    names = {"nusax": "NusaX test (reviews, everyday text)", "flores": "FLORES devtest (Wikipedia-style text)",
             "hikayat": "Hikayat Abu Sammah (verse, held-out pages)"}
    rows = ["| held-out test set | sentences | base NLLB | **this model** |", "|---|---|---|---|"]
    for k, t in info["tests"].items():
        rows.append(f"| {names.get(k, k)} | {t['n']} | {t['base']['chrF++']} | **{t['finetuned']['chrF++']}** |")
    return (f"**Model:** `{model_id}`, fine-tuned on {info.get('train_pairs', '?')} human-translated sentence pairs.\n\n"
            "Score: chrF++ (0–100, higher is better; it measures how close the output is to a human translation). "
            "These sentences were never seen in training.\n\n" + "\n".join(rows))

# --- engine ------------------------------------------------------------------------------------------------------------
class Engine:
    def __init__(self, model_id=None, beams=4, batch_size=8, device=None):
        import torch
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        self.model_id = model_id or os.environ.get("MODEL_ID") or BASE_MODEL
        self.torch, self.beams, self.batch_size = torch, beams, batch_size
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")      # GPU when run in Colab, CPU on a server
        self.tok = AutoTokenizer.from_pretrained(self.model_id, src_lang=SRC)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_id).float().to(self.device).eval()   # .float(): our upload is fp16
        self.bos = self.tok.convert_tokens_to_ids(TGT)
        self.info = load_info(self.model_id)
        self.glossary = Glossary.load()
        self.cache = {}

    def _generate(self, sents):
        out = []
        for b in range(0, len(sents), self.batch_size):
            chunk = sents[b:b + self.batch_size]
            enc = self.tok(chunk, return_tensors="pt", padding=True, truncation=True, max_length=200).to(self.device)
            with self.torch.inference_mode():
                gen = self.model.generate(**enc, forced_bos_token_id=self.bos, num_beams=self.beams,
                                          max_new_tokens=min(256, int(enc["input_ids"].shape[1] * 2) + 10))
            out += self.tok.batch_decode(gen, skip_special_tokens=True)
        return out

    def translate_sentences(self, sents):
        todo = sorted({s for s in sents if s not in self.cache}, key=len)      # similar lengths batch well
        for s, t in zip(todo, self._generate(todo) if todo else []):
            self.cache[s] = t
        if len(self.cache) > 20000:
            self.cache.clear()
        return [self.cache[s] for s in sents]

    def translate(self, text):
        """-> (indonesian_text, details [[acehnese, normalized, indonesian]], notes [str]). Keeps the line structure."""
        notes = []
        text = (text or "").strip()
        if not text:
            return "", [], notes
        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS]; notes.append(f"Only the first {MAX_CHARS} characters were translated.")
        lines = [[(s, normalize(s)) for s in split_sentences(l)] for l in text.splitlines()]
        flat = [n for l in lines for _, n in l]
        res = dict(zip(flat, self.translate_sentences(flat)))
        out = "\n".join(" ".join(res[n] for _, n in l) for l in lines)
        details = [[s, n, res[n]] for l in lines for s, n in l]
        if any(len(n.split()) < MIN_WORDS for n in flat):
            notes.append("Single words and very short phrases are often ambiguous. A full sentence gives a better translation.")
        return out, details, notes

    def explain(self, normalized, indonesian=None):
        """The real subword tokens: what the encoder reads (Acehnese) and what the decoder writes (Indonesian)."""
        src = self.tok.convert_ids_to_tokens(self.tok(normalized).input_ids)
        tgt = []
        if indonesian:
            self.tok.tgt_lang = TGT
            tgt = self.tok.convert_ids_to_tokens(self.tok(text_target=indonesian).input_ids)
        return src, tgt
