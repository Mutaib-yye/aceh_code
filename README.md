# Aceh → Indonesia toolkit

Turns Acehnese sources (hikayat PDFs, text files) into a **screened, normalized, deduplicated** sentence set, drafts an Indonesian
translation, and exports **Atlas-style JSON**. It comes with a small web app and a test suite.

**Easiest:** `./start.sh` (opens the app in your browser; `./start.sh --light` skips the translation engine). No API key is needed:
cleanup, language check, duplicate detection and export work offline, and translation can use the free local NLLB engine
(first use downloads ~2.5 GB once; **NLLB path is untested here**, since Hugging Face is blocked in the build sandbox).

```bash
pip install -r requirements.txt
python -m acehid fetch-nusax   # evaluation data (CC-BY-SA), once
# put AcehX .txt files in data/raw/acehx/ then: python -m acehid audit   (needed for the duplicate check)
python -m acehid serve          # web app on http://127.0.0.1:8000
python -m pytest tests -q       # 21 tests, no network needed
```

## What works today (tested) and what does not

| Part | Status |
|---|---|
| Extract: PDF text layer, TXT, **OCR for scanned pages** (RapidOCR, pip only) | works; tested on generated PDFs, **not yet on real hikayat scans** |
| Screening (headers/footers, URLs, Arabic script, fragments, OCR errors, language) | works; language check measured on held-out NusaX: Acehnese 96–98 %, Indonesian 99.5–100 % |
| Normalization (`löen → loen`, Dutch-era `dj/tj/nj`, quotes) with raw text always kept | works |
| Deduplication vs AcehX (exact + spelling-variant + near-duplicate) and within the new data | works; AcehX index builds once (~4 min), then cached |
| Review sheet (CSV out, edited CSV back in) | works |
| Export to Atlas JSON + train/validation/test split **by source** | works; **schema is unconfirmed** (see below) |
| Web app (translate text, process a PDF, download JSON / review CSV) | works |
| **Translation** (`claude`, `groq`, `nllb`) | **code is in place but was not run against any model**: no API key, and Hugging Face is blocked in the build sandbox. Only the `copy` baseline was run. |
| Hikayat data | **none yet**: Andrie has not sent the PDFs |

Nothing here has been trained. No translation quality number exists for any real model yet.

## Run it on a hikayat PDF

1. Put the PDF in `data/raw/hikayat/`, add a row in `config/sources.csv` (title, url, licence).
2. `python -m acehid all` → `data/deduplicated/hikayat.jsonl` and `data/review/review_sheet.csv`.
   (Or use the web app, tab 2.)
3. A person fills `decision` (keep / remove / edit) in the review sheet; `python -m acehid review-import data/review/review_sheet.csv`.
4. Translate (below), then `python -m acehid export` → `data/final/atlas_master.json`, `train/validation/test.json`.

Rows are **labelled, never deleted**: `KEEP / REVIEW / REMOVE / NON_ACEH / FRAGMENT / OCR_ERROR`, and `unique / DUPLICATE_ACEHX / DUPLICATE_SELF / NEAR_DUP_REVIEW`.
Only `KEEP` + `unique` rows are translated. Near-duplicates go to a human.

## Translation: three ways, measure before trusting

```bash
# 1. Claude (best chance for literary text; needs an API key in the environment)
export ANTHROPIC_API_KEY=...        # never paste keys into files or chat
python -m acehid eval --provider claude          # chrF/BLEU/TER on NusaX valid+test, cached, few-shot from NusaX train
python -m acehid translate --provider claude

# 2. NLLB-200 (free; run on Colab/Kaggle GPU or locally; ace_Latn -> ind_Latn)
pip install transformers torch sentencepiece
python -m acehid eval --provider nllb
python -m acehid translate --provider nllb

# 3. Groq free tier
export GROQ_API_KEY=...  ; python -m acehid eval --provider groq

# Compare everything in one table (writes reports/eval_nusax.md)
python -m acehid eval --provider copy nllb claude
```

Floor to beat (copy the Acehnese text unchanged, measured): **chrF 35.9 / BLEU 6.3 / TER 85.1** on NusaX test (400 sentences).
NusaX is modern review text, so these scores will **not** predict quality on hikayat. Have an Acehnese speaker check ~100 random rows.
All output is `machine_draft`: excluded from the training split unless `--include-drafts`, and quality `low` in the Atlas JSON until a human marks it `reviewed` / `human_validated`.

## Data in this repo

- `data/final/nusax/`: the 1,000 human-translated NusaX-MT pairs in Atlas format (**CC-BY-SA 4.0, share-alike; keep separate**). valid+test are the evaluation set, never train on them.
- `reports/acehx_audit.md`: AcehX audit (164,778 lines, 3.0 % duplicates, **no Indonesian side**, mixed old/modern spelling).
- `reports/pipeline_report.md`: numbers and limitations. `DATASET_CARD.md`, `TRANSLATION_GUIDELINE.md`.
- Raw/intermediate data stays local (`data/raw/` etc. are git-ignored). Song lyrics are **excluded** (copyrighted, garbled).

## Atlas JSON (needs Andrie's confirmation)

Uses section 17 of the project plan (`id, source{title,type,page,license}, language, text{ace_raw, ace_normalized, ind_raw, ind_normalized}, processing, quality`).
Andrie said the format is in the plan but never sent a sample. If the real Atlas schema differs, only `to_atlas_record()` in `acehid/export.py` changes.

## Layout

`acehid/` (audit, extract, screen, normalize, dedupe, translate, evalnusax, export, review, nusax, langid, cli) · `app/` (web app) · `tests/` · `config/` (sources.csv, language model) · `reports/` · `data/final/`.
