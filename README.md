# Aceh → Indonesia toolkit

Turns Acehnese sources (hikayat PDFs, text files) into a **screened, normalized, deduplicated** sentence set, drafts an Indonesian
translation, and exports **Atlas-style JSON**. It comes with a small web app and a test suite.

**Easiest:** `./start.sh` (macOS/Linux, Python 3.10–3.14; opens the app in your browser; `./start.sh --light` skips the translation engine). No API key is needed:
cleanup, language check, duplicate detection and export work offline, and translation can use the free local NLLB engine
(first use downloads ~2.5 GB once; **NLLB path is untested here**, since Hugging Face is blocked in the build sandbox).

```bash
pip install -r requirements.txt
python -m acehid fetch-nusax   # evaluation data (CC-BY-SA), once
# put AcehX .txt files in data/raw/acehx/ then: python -m acehid audit   (needed for the duplicate check)
python -m acehid serve          # web app on http://127.0.0.1:8000
python -m pytest tests -q       # no network needed
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

## Train our own model (fine-tune NLLB)

**Easiest: Google Colab (free GPU, nothing to install on your Mac).** Open `notebooks/train_colab.ipynb` in Colab
(File → Open notebook → GitHub → `Mutaib-yye/aceh_code`, branch `claude/dataset-product-build-108xu8`), set Runtime → T4 GPU, Run all.
It prints a base-vs-fine-tuned table and saves the model to your Google Drive. On any GPU machine:

```bash
pip install -r requirements.txt torch transformers sentencepiece
python -m acehid flores ~/Downloads/flores200_dataset.tar   # once: FLORES-200 ace/ind -> data/final/flores (CC-BY-SA)
python -m acehid build-train                               # NusaX + FLORES -> leak-checked data/final/combined
python -m acehid build-train --extra data/final/train.json --extra-test hikayat=data/final/test.json   # + REVIEWED hikayat pairs
python -m acehid train                                     # max 10 epochs, early stopping -> models/ace-id-nllb/RESULTS.md
```

| set | from | used for |
|---|---|---|
| train | NusaX train (500) + FLORES dev minus 200 (~797) + reviewed extra pairs | gradient updates |
| validation | NusaX valid (100) + 200 FLORES dev | picking the best epoch, early stopping |
| test_nusax / test_flores | NusaX test (400) / FLORES devtest (1,012) | scored **once** at the end, base vs fine-tuned |

A training pair is dropped if either side matches a validation/test sentence (case, diacritics, punctuation and old spelling ignored)
or its Acehnese side is ≥ 90 % similar to one; `train` also refuses to start if any leak remains. Metrics: chrF++ (main, as in the
NLLB paper), chrF, BLEU. Results go to `models/ace-id-nllb/RESULTS.md` (with example translations) and `reports/finetune_results.md`.
Copy the trained `ace-id-nllb` folder into `models/` and the web app uses it automatically.
The loop is smoke-tested end to end on a tiny random model; the real NLLB run happens on Colab (Hugging Face is blocked in the build sandbox).
NLLB weights are CC-BY-NC 4.0, so the fine-tuned model is for research / non-commercial use.

## Translation providers (for drafts and baselines)

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
