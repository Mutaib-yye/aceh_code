"""Stage 6: DRAFT translation Aceh -> Indonesian. Output is always `machine_draft`, never ground truth.

Providers (select with provider=...; keys come from environment variables ONLY, never files/chat):
  claude : pip install anthropic ; ANTHROPIC_API_KEY ; model via TRANSLATE_MODEL (default below)
  groq   : requests              ; GROQ_API_KEY      ; model via TRANSLATE_MODEL (check Groq's current model list)
  nllb   : pip install transformers torch sentencepiece ; runs locally/Colab, no key. NLLB-200 supports ace_Latn -> ind_Latn.
           model via TRANSLATE_MODEL (default facebook/nllb-200-distilled-600M). Needs a one-time model download from Hugging Face.
  copy   : baseline that returns the Acehnese text unchanged (floor for chrF/BLEU; NOT a translator)

LLM providers get k few-shot examples retrieved from NusaX-MT train (most similar Acehnese sentences), see `fewshot`.
"""
import os, json, re, time, csv, functools
from .common import *

DEFAULT_MODELS = {"claude": "claude-sonnet-5-5", "groq": "llama-3.3-70b-versatile", "nllb": "facebook/nllb-200-distilled-600M", "copy": "copy"}
BATCH = 20
MIN_WORDS = 3   # Andrie's rule: a sentence needs at least 3 words to be translated (single words are ambiguous)

SYSTEM = """You translate Acehnese (Latin script) into standard Indonesian (EYD/PUEBI spelling).
Rules: keep personal and place names unchanged; keep titles (Teungku, Cut, Sultan, Po, Habib) unchanged; translate meaning, not word-for-word;
if the sentence is unclear, archaic, or not Acehnese, set "confidence":"low" and still give your best attempt; never add information.
Return ONLY a JSON list: [{"i":<int>,"ind":"<translation>","confidence":"high|medium|low"}] in the same order as the input."""

@functools.lru_cache(maxsize=1)
def _pairs():
    p = ROOT / "data/raw/external/nusax/train.csv"
    if not p.exists():
        return []
    return [(r["acehnese"], r["indonesian"]) for r in csv.DictReader(open(p, encoding="utf-8"))]

def fewshot(text, k=5):
    """k most similar NusaX *train* pairs (never valid/test, so evaluation stays clean)."""
    pairs = _pairs()
    if not pairs or k <= 0:
        return []
    from rapidfuzz import process, fuzz
    hits = process.extract(text, [a for a, _ in pairs], scorer=fuzz.token_set_ratio, limit=k)
    return [pairs[i] for _, _, i in hits]

def available_providers():
    out = {"copy": "baseline only"}
    if os.environ.get("ANTHROPIC_API_KEY"):
        out["claude"] = os.environ.get("TRANSLATE_MODEL") or DEFAULT_MODELS["claude"]
    if os.environ.get("GROQ_API_KEY"):
        out["groq"] = DEFAULT_MODELS["groq"]
    try:
        import transformers, torch  # noqa
        out["nllb"] = DEFAULT_MODELS["nllb"]
    except Exception:
        pass
    return out

def recommended(avail=None):
    """Best configured engine: free local NLLB first (no key), then Claude, then Groq. 'copy' only if nothing else exists."""
    avail = avail or available_providers()
    for k in ("nllb", "claude", "groq"):
        if k in avail:
            return k
    return "copy"

def _parse(raw):
    txt = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    return {x["i"]: x for x in json.loads(txt)}

class Translator:
    def __init__(self, provider="claude", model=None, k_fewshot=5):
        self.provider, self.k = provider, k_fewshot
        self.model = model or os.environ.get("TRANSLATE_MODEL") or DEFAULT_MODELS[provider]
        self.tag = f"{provider}:{self.model}" + (f":fs{k_fewshot}" if provider in ("claude", "groq") and k_fewshot else "")
        self._nllb = None

    # -- backends -------------------------------------------------------------
    def _llm(self, user):
        system = SYSTEM
        if self.provider == "groq":
            import requests
            key = os.environ["GROQ_API_KEY"]
            for attempt in range(5):
                r = requests.post("https://api.groq.com/openai/v1/chat/completions", timeout=120, headers={"Authorization": f"Bearer {key}"},
                                  json={"model": self.model, "temperature": 0, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
                if r.status_code == 429:
                    time.sleep(10 * (attempt + 1)); continue   # free-tier rate limit
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
            raise RuntimeError("Groq rate limit: try a smaller batch or wait")
        import anthropic
        m = anthropic.Anthropic().messages.create(model=self.model, max_tokens=16000, system=system, output_config={"effort": "low"}, messages=[{"role": "user", "content": user}])
        return m.content[0].text

    def _nllb_translate(self, texts):
        if self._nllb is None:
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            tok = AutoTokenizer.from_pretrained(self.model, src_lang="ace_Latn")
            self._nllb = (tok, AutoModelForSeq2SeqLM.from_pretrained(self.model))
        tok, mdl = self._nllb
        enc = tok(texts, return_tensors="pt", padding=True, truncation=True, max_length=256)
        out = mdl.generate(**enc, forced_bos_token_id=tok.convert_tokens_to_ids("ind_Latn"), max_new_tokens=256, num_beams=4)
        return tok.batch_decode(out, skip_special_tokens=True)

    # -- public ---------------------------------------------------------------
    def translate(self, texts):
        """list[str] -> list[{'ind': str, 'confidence': 'high|medium|low|n/a'}]  (same order)."""
        if self.provider == "copy":
            return [{"ind": t, "confidence": "n/a"} for t in texts]
        if self.provider == "nllb":
            return [{"ind": s, "confidence": "n/a"} for s in self._nllb_translate(list(texts))]
        out = []
        for b in range(0, len(texts), BATCH):
            chunk = texts[b:b + BATCH]
            payload = {"input": [{"i": i, "ace": t} for i, t in enumerate(chunk)]}
            if self.k:
                shots = {}
                for t in chunk:
                    for a, ind in fewshot(t, self.k):
                        shots[a] = ind
                payload["reference_examples_ace_to_ind"] = [{"ace": a, "ind": i} for a, i in list(shots.items())[:40]]
            res = _parse(self._llm(json.dumps(payload, ensure_ascii=False)))
            out += [{"ind": res.get(i, {}).get("ind", ""), "confidence": res.get(i, {}).get("confidence", "low")} for i in range(len(chunk))]
        return out

def run(rows, translator, limit=None, done=None, on_progress=None):
    """Translate rows with screening==KEEP and dedup==unique. Resumable via `done` {id: row}."""
    done = done if done is not None else {}
    todo = [r for r in rows if r["id"] not in done and r.get("screening") == "KEEP" and r.get("dedup") == "unique" and len(r["ace_normalized"].split()) >= MIN_WORDS][:limit]
    for b in range(0, len(todo), BATCH):
        chunk = todo[b:b + BATCH]
        res = translator.translate([r["ace_normalized"] for r in chunk])
        for r, x in zip(chunk, res):
            r.update(ind_raw=x["ind"], translation_status="machine_draft", mt_confidence=x["confidence"], mt_model=translator.tag)
            done[r["id"]] = r
        if on_progress:
            on_progress(done)
        log("translate", done=len(done), of=len(todo))
    return done
