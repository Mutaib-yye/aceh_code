# Pipeline report (2026-10-06)

All numbers below were measured in this repo, except where marked **not measured**.

## Inputs
| Source | Result |
|---|---|
| AcehX (11 files) | 164,778 non-empty lines; 159,851 unique after case/diacritic/punctuation/old-spelling folding → **3.0 % duplicates** (4,927). 1,515 duplicate keys occur in more than one file. 73 Arabic-script lines. **No Indonesian side**: it is monolingual, so it cannot train a translator. |
| Language check on AcehX (lines ≥ 3 words) | 162,236 Acehnese · 1,318 code-mixed/unsure · 567 Indonesian |
| NusaX-MT | 1,000 human-translated pairs (500/100/400). 0 exact overlap with AcehX. |
| Lyrics CSV/JSON | Excluded: 8 garbled rows, copyrighted, no Indonesian side. |
| Hikayat PDFs | **Not received.** |

## Language check (held out)
Character 1–4-gram naive Bayes; Acehnese side trained on AcehX, Indonesian side on NusaX **train** only; evaluated on NusaX valid+test (never seen).
| split | n per side | Acehnese→ace | Acehnese→ind | Indonesian→ind | Indonesian→ace | unsure |
|---|---|---|---|---|---|---|
| valid | 100 | 98.0 % | 0.0 % | 100 % | 0.0 % | 1.0 % |
| test | 400 | 96.0 % | 0.75 % | 99.5 % | 0.0 % | 1.9 % |

## Pipeline checks on realistic inputs (generated PDFs)
- 300 AcehX lines (every 5th upper-cased) rendered to a PDF with running headers and page numbers → 252 sentences; **241 flagged DUPLICATE_ACEHX**, 7 NEAR_DUP_REVIEW, 4 unique (residual comes from lines truncated/merged at page layout), headers and page numbers removed.
- 120 NusaX test sentences (zero overlap with AcehX) as wrapped prose → 232 sentences (sentence splitting turns 120 reviews into 232), 202 KEEP, 8 REVIEW (code-mixed), 14 FRAGMENT, 8 NON_ACEH; 231 unique, 1 DUPLICATE_ACEHX (a short sentence that does occur in AcehX).
- Scanned page (image-only PDF) → OCR text recovered with confidence > 0.5, and flagged `ocr`; with OCR disabled the page is flagged `ocr_needed`, not dropped.
- Export QC rejected 40/40 "translations" produced by the copy baseline (`identical_to_source`), as intended.
- Test suite: 21 passed (normalization, language check on held-out data, screening, hyphenation, verse layout, dedupe variants, OCR, export gates, source-level split, review round trip, web app).

## Baseline translation score (NusaX, sacreBLEU)
| system | split | n | chrF | BLEU | TER |
|---|---|---|---|---|---|
| copy source (no translation) | valid | 100 | 37.5 | 7.53 | 82.93 |
| copy source (no translation) | test | 400 | 35.89 | 6.31 | 85.09 |

**Not measured:** NLLB, Claude, Groq. No API key was available and Hugging Face is blocked from the build sandbox. Run `python -m acehid eval --provider copy nllb claude` where you have access.

## Bug found and fixed in the inherited code
The old header/footer remover deleted any line repeating on ≥ 30 % of pages, **anywhere on the page**, which would have removed legitimate refrains in verse. It now only considers the first/last two lines of a page and requires ≥ 3 repeats.

## Not done / limits
- No real hikayat input has been processed; layout detection (verse vs prose) and sentence splitting are tuned on synthetic pages only.
- Dedup does not catch paraphrases. Normalization of Indonesian output to PUEBI is not implemented.
- No model has been trained or fine-tuned; no human review has been done.
- Extra datasets (FLORES-200, Acehnese Wikipedia, OPUS, Hugging Face `ace`) were **not downloaded**: those hosts are denied by this environment's network policy. They are listed in `config/sources.csv` as candidates to verify.
