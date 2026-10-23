# Pipeline report (updated 2026-10-08)

All numbers below were measured in this repo, except where marked **not measured yet**.

## Data
| Source | Result | Used for |
|---|---|---|
| NusaX-MT (CC-BY-SA 4.0) | 1,000 human-translated pairs (500 / 100 / 400) | train / validation / test |
| FLORES-200 (CC-BY-SA 4.0) | 997 dev + 1,012 devtest; downloaded by the Colab notebook (blocked in the build sandbox) | train (+200 validation) / test |
| Hikayat Abu Sammah (Depdikbud; reuse terms to confirm) | 1,856 aligned verse pairs, 1,654 KEEP: train 1,432 / validation 79 / test 143 (page blocks); 199 REVIEW. Details: `reports/hikayat_abu_sammah.md` | train / validation / test |
| AcehX (licence unknown) | 164,778 lines, 159,851 unique (3.0 % duplicates), **no Indonesian side**; contains 199 lines of Hikayat Abu Sammah (`corpus_Iskandar_file_4.txt`) | duplicate check + OCR spelling reference only |
| Data Syair dan Lagu.rar | 83 PDFs, 343 pages (108 scanned): ~60 copyrighted songs (excluded), 4 monolingual hikayat, 4 syair, the Razali Abdullah dictionary (96 scanned pages, copyrighted), 3 possibly bilingual papers on pantun / oral tradition (not yet checked). `scan-archive` report | not used yet |
| Lyrics CSV/JSON | 8 garbled rows, copyrighted, no Indonesian side | excluded |
| Quran (Acehnese, Tgk. Mahjiddin Jusuf × Kemenag Indonesian) | 6,236 verses; 5,466 after length filter | off by default (`--quran`), ask Andrie |

Leak control for training (`build-train`): any training pair whose Acehnese or Indonesian side matches a validation/test
sentence (case, diacritics, punctuation, old spelling ignored) or is ≥ 90 % similar on the Acehnese side is dropped; `train`
refuses to start if any leak remains. Current build without FLORES: 8,123 training pairs, 0 leaks (hikayat Abu Sammah 1,432; Quran 5,466; NusaX 500; Wikipedia 375; hikayat Malik Mawot 350). The NLLB-Seed pivot (`seed-pivot`, about 5,750 pairs with machine Indonesian) is added by the Colab notebook when `USE_SEED_PIVOT` is on.

## Quality checks
- Language check (character n-grams, trained on AcehX + NusaX train, tested on NusaX valid+test): Acehnese recognised 96–98 %,
  Indonesian 99.5–100 %.
- Hikayat OCR: word error rate 0.8 % (RapidOCR 300 dpi) vs 11.3 % for the PDF's own text layer, on 16 hand-typed lines.
- Hikayat alignment: 40 / 40 random KEEP pairs correct (developer check; an Acehnese speaker should confirm a sample).
- Vocabulary: 13.5–14 % of the words in the test sets never occur in training; only 66 % of AcehX running words occur in training.
  Expect weak translations for unfamiliar words, names and dialect forms.

## Translation scores (sacreBLEU)
| system | test set | chrF | BLEU |
|---|---|---|---|
| copy source (no translation, the floor) | NusaX test (400) | 35.89 | 6.31 |
| base NLLB-200 600M | NusaX / FLORES / hikayat test | **not measured yet** | |
| our fine-tuned model | NusaX / FLORES / hikayat test | **not measured yet** | |

The Colab notebook (`notebooks/train_colab.ipynb`) measures base vs fine-tuned on every test set and writes
`models/ace-id-nllb/RESULTS.md`; copy that table here after the run.

## Software
- `python -m acehid ...`: extract (PDF text layer + OCR), screen, normalize, dedupe (exact + near vs AcehX), review sheet,
  translate (drafts), export (Atlas JSON), flores, hikayat-pairs, scan-archive, build-train, train, eval, serve.
- Translator app (`space/`): runs on your own computer with `./run_app.sh` (http://127.0.0.1:7860, offline after the model is fetched once); `notebooks/demo_colab.ipynb` runs it in Colab. Hosting it as a Hugging Face Space needs a paid plan since 2026 (HTTP 402), so we do not use that. Checked on desktop, phone and dark mode with a test model.
- Test suite: 73 tests pass (`python -m pytest tests`). The notebook was rehearsed end to end with a small stand-in model.

## Not done / limits
- Colab run (22-23 Oct 2026, T4): 17,547 training pairs, best epoch 3 of 5. chrF++ base -> fine-tuned: NusaX 38.66 -> 57.15, FLORES 46.27 -> 52.81, hikayat 23.98 -> 60.92. Full output: `reports/colab_run_results.md`. Not yet tested: training without the Seed pivot.
- No human review of translations or of the Hikayat alignment beyond the developer's checks.
- Atlas JSON schema is unconfirmed (plan section 17); Indonesian output is not normalized to PUEBI.
- Dedup finds spelling/format variants, not paraphrases.
- Licences to confirm with Andrie: Hikayat Abu Sammah (Depdikbud), AcehX, Quran translation.

## Added later
- `import-tmx`: Wikipedia ace-id TMX -> 375 filtered pairs (`data/final/wikipedia/pairs.json`, CC-BY-SA).
- `malik-mawot`: thesis edition (verse + translation) -> 350 pairs, `data/human/malik_mawot_pairs.json` (git-ignored).
- `seed-pivot`: NLLB-Seed Acehnese + English -> Acehnese + Indonesian (NLLB machine translation); GPU.
- `kamus-build` / `kamus`: personal lookup in the Kamus Budaya book (local text in `data/raw/kamus/`).
- App: optional word-by-word panel from the 1985 dictionary list (`data/glossary/`), meanings ranked by the translation.
- `compare-approaches`: direct vs transfer baselines on the NusaX test (chrF++ 32.0 copy / 35.5 direct / 39.2 transfer). See `reports/mt_approaches.md`.
- Tests: 86.
