"""Translation core of the hosted app (no UI code, so it is unit-tested without Gradio).

Model: MODEL_ID env var / Space variable (our fine-tuned NLLB, e.g. <user>/ace-id-nllb), default: base NLLB-200 600M.
Input is normalized exactly like the training data (same rules as acehid/normalize.py; tests/test_space.py checks they agree),
split into sentences (NLLB is trained on single sentences), translated in batches with beam search, and cached."""
import os, re, json, unicodedata

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
