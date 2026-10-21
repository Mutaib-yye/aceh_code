"""Rule-based machine translation baselines, for the report: how far do the classic approaches get, compared with the neural model?

direct    word-for-word dictionary lookup (unknown words stay as they are)            -- "direct approach"
transfer  analysis -> transfer -> generation: split Acehnese subject prefixes (ji-, geu-, neu-, ta-) and the suffix -jih,
          map a small closed set of function words, then look the rest up in the dictionary -- "transfer approach"
neural    the fine-tuned NLLB model (interlingual-style: one shared representation for all languages; see evalnusax/train)

The dictionary is the optional Kamus Aceh-Indonesia (1985) A-L word list in data/glossary/ (git-ignored). It covers only words
beginning A-L, so these baselines are weak on purpose: the point is the comparison. Function words below were kept only when
the NusaX train/validation sentences support them (the Indonesian word appears in >= 50% of the sentences containing the
Acehnese word, in >= 20 sentences); mappings the data did not support (bak->pada 12%, that->sangat 31%, ...) were left out."""
import re, json, importlib.util
from pathlib import Path
from .common import ROOT, log

FUNCTION = {"hana": "tidak", "nyang": "yang", "nyoe": "ini", "u": "ke", "lon": "saya", "bek": "jangan", "atawa": "atau", "ureueng": "orang",
            "na": "ada", "ngon": "dengan", "ka": "sudah", "le": "banyak", "jeut": "bisa", "dan": "dan", "di": "di"}
AGREE = {"geu": "beliau", "neu": "Anda", "ji": "dia", "ta": "kita"}          # subject agreement prefixes on Acehnese verbs
PRONOUNS = set(AGREE.values()) | {"saya", "kamu", "dia"}
TOKEN = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*|\d+|[^\w\s]")

def load_glossary(path=None):
    spec = importlib.util.spec_from_file_location("space_core", ROOT / "space/core.py")
    core = importlib.util.module_from_spec(spec); spec.loader.exec_module(core)
    g = core.Glossary.load(path)
    if g is None:
        raise FileNotFoundError("could not download the dictionary list from GitHub (is the repo public and are you online?)")
    return g, core._fold

def short_gloss(meaning):
    """'dia, ia mereka, sebutan kehormatan ...' -> 'dia'; keeps the first short phrase of the first meaning."""
    m = re.sub(r"\([^)]*\)", "", meaning)
    first = re.split(r"[;,]", m)[0].strip().lower()
    return " ".join(first.split()[:3]) or None

class Translator:
    def __init__(self, glossary=None):
        self.g, self.fold = glossary or load_glossary()

    def gloss(self, word):
        ms = self.g.entries.get(self.fold(word))
        return short_gloss(ms[0]) if ms else None

    def direct(self, sentence):
        out = [self.gloss(t) or t if t[0].isalpha() else t for t in TOKEN.findall(sentence)]
        return self._generate(out)

    def transfer(self, sentence):
        out = []
        for t in TOKEN.findall(sentence):
            w = t.lower()
            if not t[0].isalpha():
                out.append(t); continue
            if w in FUNCTION:                                                   # transfer of closed-class words
                out.append(FUNCTION[w]); continue
            if w.endswith("jih") and self.gloss(w[:-3]):                        # analysis: noun + possessive suffix -jih
                out.append(self.gloss(w[:-3]) + "nya"); continue
            pre = next((p for p in AGREE if w.startswith(p) and len(w) > len(p) + 1 and self.gloss(w[len(p):])), None)
            if pre and w not in self.g.entries:                                 # analysis: subject prefix + verb
                if not (out and out[-1] in PRONOUNS):                           # the subject was not already written out
                    out.append(AGREE[pre])
                out.append(self.gloss(w[len(pre):])); continue
            out.append(self.gloss(t) or t)
        return self._generate(out)

    @staticmethod
    def _generate(tokens):
        s = " ".join(tokens)
        s = re.sub(r"\s+([.,!?;:])", r"\1", s)
        return s[:1].upper() + s[1:]

def compare(test=ROOT / "data/final/nusax/test.json", out=ROOT / "reports/mt_approaches.json", glossary=None):
    """chrF++ / BLEU on the NusaX test set for: copy (nothing translated), direct, transfer."""
    import sacrebleu
    rows = json.load(open(test, encoding="utf-8"))
    refs = [r["ind"] for r in rows]
    t = Translator(glossary)
    systems = {"copy (Acehnese text unchanged)": [r["ace"] for r in rows], "direct (dictionary, word for word)": [t.direct(r["ace"]) for r in rows],
               "transfer (rules + dictionary)": [t.transfer(r["ace"]) for r in rows]}
    res = {}
    for name, hyp in systems.items():
        res[name] = {"chrF++": round(sacrebleu.corpus_chrf(hyp, [refs], word_order=2).score, 1), "BLEU": round(sacrebleu.corpus_bleu(hyp, [refs]).score, 1)}
    res["_n"] = len(rows); res["_examples"] = [{"ace": rows[i]["ace"], "ref": refs[i], "direct": systems["direct (dictionary, word for word)"][i],
                                                "transfer": systems["transfer (rules + dictionary)"][i]} for i in range(3)]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log("compare-approaches", **{k.split(" ")[0]: v["chrF++"] for k, v in res.items() if not k.startswith("_")})
    return res
