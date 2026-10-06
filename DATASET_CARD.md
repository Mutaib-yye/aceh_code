# Dataset card: ace-id (Acehnese → Indonesian), version ace-id-v0.2-dev

**Status:** pipeline + evaluation set only. No hikayat data has been collected yet, so there is no hikayat release.

## Contents
| Part | Size | Parallel | Licence | In `data/final/` |
|---|---|---|---|---|
| NusaX-MT ace↔ind (human translated) | 1,000 pairs (500 train / 100 valid / 400 test) | yes | CC-BY-SA 4.0 | yes, `data/final/nusax/` |
| AcehX | 164,778 lines (159,851 unique) | **no** (Acehnese only) | unknown, ask Andrie | no (reference for dedup only) |
| Hikayat (Atlas additions) | 0 | planned | per source | no |
| Song lyrics | 8 rows | no | copyrighted | **excluded** |

## Intended use
Research/education: building and evaluating an Acehnese→Indonesian translation model; deduplicating new Acehnese sources against AcehX.
Not for: treating machine drafts as reference translations.

## Known limitations
- NusaX is modern review-style text; it does not represent hikayat language.
- Language check is a character n-gram model: 96–98 % Acehnese / 99.5–100 % Indonesian on NusaX sentences; weaker on short lines and heavily code-mixed text. ~1,300 AcehX lines are code-mixed.
- Deduplication catches spelling/format variants (case, diacritics, punctuation, Dutch-era `dj/tj/nj`, MinHash Jaccard ≥ 0.85), **not paraphrases with equal meaning**.
- Normalization follows Andrie's diaeresis rule and documented Dutch-era rules; it is lossy for ö/ë.
- OCR drops diacritics; sentence splitting uses English rules (no Acehnese/Indonesian model available).
- Machine translations are drafts until a speaker reviews them.
