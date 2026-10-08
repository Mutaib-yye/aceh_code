# Dataset card: ace-id (Acehnese → Indonesian), version ace-id-v0.2-dev

**Status:** pipeline + human-translated training/evaluation pairs (NusaX-MT, FLORES-200 once imported). Hikayat pairs: pending (book received, not yet extracted/reviewed).

## Contents
| Part | Size | Parallel | Licence | In `data/final/` |
|---|---|---|---|---|
| NusaX-MT ace↔ind (human translated) | 1,000 pairs (500 train / 100 valid / 400 test) | yes | CC-BY-SA 4.0 | yes, `data/final/nusax/` |
| FLORES-200 ace↔ind (professional translation) | 997 dev + 1,012 devtest | yes | CC-BY-SA 4.0 | `data/final/flores/` after `python -m acehid flores <tar>` |
| AcehX | 164,778 lines (159,851 unique) | **no** (Acehnese only) | unknown, ask Andrie | no (reference for dedup only) |
| Hikayat Abu Sammah (Depdikbud, 126 pp.) | not extracted yet | if bilingual | unclear ("Milik Depdikbud, tidak diperdagangkan") | no (kept out of the public repo) |
| Song lyrics | 8 rows | no | copyrighted | **excluded** |

## Fine-tuning set (`python -m acehid build-train` → `data/final/combined/`, rebuilt, not committed)
| split | contents | role |
|---|---|---|
| train | NusaX train + FLORES dev minus 200 (+ reviewed extra pairs) | training |
| validation | NusaX valid + 200 FLORES dev | best epoch / early stopping |
| test_nusax, test_flores | NusaX test (400), FLORES devtest (1,012) | final score only |

Leak control: training pairs whose Acehnese or Indonesian side equals a validation/test sentence (ignoring case, diacritics,
punctuation, old spelling) or whose Acehnese side is ≥ 90 % similar to one are dropped; counts are in `manifest.json`.
Do **not** add Belebele or SIB-200: they reuse FLORES sentences and would leak the test set.

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
