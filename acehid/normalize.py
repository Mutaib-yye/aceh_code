"""Stage 4: Acehnese spelling normalization. ace_raw is NEVER changed; ace_normalized is a new field.
Rules (each logged per row in `norm_rules`):
  unicode   NFC, curly quotes -> ', nbsp/zero-width removed, whitespace collapsed
  old_spell Dutch-era word-initial dj->j, tj->c, nj->ny  (njang->nyang, djipeugot->jipeugot)
  diaeresis Andrie's rule: remove the two-dot marks not used in Indonesian writing (ö->o, ë->e, ü->u, ï->i, ä->a), e.g. löen -> loen.
            --strip-all also strips é è ô ó ò etc. (loses information: in Acehnese é/è/ë/ô/ö are different vowels)
Evidence for the rule list: in AcehX only dj/tj/nj differ systematically between the old-spelling files and the modern ones
(reports/acehx_audit.md); 'oe' is frequent in every file (modern spelling too), so oe->u and j->y are NOT applied."""
import re, unicodedata, collections
from .common import *

DIAERESIS = str.maketrans({"ö": "o", "Ö": "O", "ë": "e", "Ë": "E", "ü": "u", "Ü": "U", "ï": "i", "Ï": "I", "ä": "a", "Ä": "A"})
QUOTES = str.maketrans({"’": "'", "‘": "'", "`": "'", "´": "'", "“": '"', "”": '"', "–": "-", "—": "-"})
OLD = [(re.compile(r"(?<![\w])dj(?=\w)", re.I), "j"), (re.compile(r"(?<![\w])tj(?=\w)", re.I), "c"),
       (re.compile(r"(?<![\w])nj(?=[aeiouèéëôö])", re.I), "ny")]

def _case(orig, new):
    return new.upper() if orig.isupper() and len(orig) > 1 else (new.capitalize() if orig[0].isupper() else new)

def normalize(s, strip_all=False):
    rules = []
    t = unicodedata.normalize("NFC", s).translate(QUOTES)
    t = re.sub(r"[ ​‌‍﻿]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if t != s:
        rules.append("unicode")
    before = t
    for pat, rep in OLD:
        t = pat.sub(lambda m: _case(m.group(0), rep), t)
    if t != before:
        rules.append("old_spell")
    before = t
    t = strip_diacritics(t) if strip_all else t.translate(DIAERESIS)
    if t != before:
        rules.append("strip_all" if strip_all else "diaeresis")
    return t, rules

def run(rows, strip_all=False):
    c, out = collections.Counter(), []
    for r in rows:
        r["ace_normalized"], r["norm_rules"] = normalize(r["ace_raw"], strip_all)
        c.update(r["norm_rules"]); out.append(r)
    log("normalize", rows=len(out), **dict(c))
    return out
