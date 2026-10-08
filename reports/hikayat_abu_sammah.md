# Hikayat Abu Sammah: bilingual extraction report

**Source:** *Hikayat Abu Sammah*, Depdikbud (Tim Peneliti: M. Alamsyah B., M. Yusuf Hasdy, ...), 126 pages, scanned with an
Acrobat OCR text layer. Copy used: `HIKAYAT ABU SAMMAH_compressed.pdf` (6.4 MB, images ~73 dpi). Marked *"Milik Depdikbud,
tidak diperdagangkan"*: a free-distribution government book; **reuse terms to be confirmed with Andrie**.

**Layout:** Bab II *Alihaksara* (Acehnese verse, pages 14–59 of the PDF) and Bab III *Alih Bahasa* (its Indonesian translation,
pages 60–105), line for line. Pages 107–121 are analysis (Indonesian), 122–125 bibliography and manuscript list (not used).

Rebuild: `python -m acehid hikayat-pairs "data/raw/hikayat/HIKAYAT ABU SAMMAH_compressed.pdf" --ace-pages 14-59 --ind-pages 60-105 --test-pages 50-53 --valid-pages 47-48`

## Stages and counts
| stage | Acehnese | Indonesian |
|---|---|---|
| OCR lines kept (RapidOCR, 300 dpi) | 1882 | 1892 |
| dropped: page numbers / headings / footnotes / unreadable | 47 / 2 / 0 / 8 | 46 / 2 / 4 / 8 |
| wrapped half-lines re-joined | 3 | 5 |
| words repaired (OCR slips, checked against AcehX / Indonesian references) | 159 | 64 |
| lines left without a partner (skipped by the aligner) | 26 | 36 |

Aligned pairs: **1856** (all one line ↔ one line). Screening: KEEP 1654, REVIEW 199
(weak alignment evidence or OCR confidence < 0.9, exported to `data/review/abu_sammah_review.csv`), REMOVE 3 (untranslated Arabic lines).

Deduplication against AcehX: **199 lines already exist in AcehX**, all in `corpus_Iskandar_file_4.txt`
(from line ~1050: a student had typed part of this hikayat), 10 near-duplicates for review,
1647 unique. Atlas JSON (`data/final/hikayat/abu_sammah/atlas.json`) contains only KEEP + unique rows: **1467** records.
For translation training the AcehX duplicates are kept (AcehX has no Indonesian side, so they add no leakage).

Training split by contiguous page blocks (neighbouring verses continue each other, so they must not straddle train and test):
train 1432, validation 79 (pages 47-48), test 143 (pages 50-53).

## Quality checks (measured)
- **OCR:** 16 lines of page 15 typed by hand from the scan. Word error rate: Acrobat text layer 11.3 %, RapidOCR at 300 dpi **0.8 %**
  (chrF 95.6 → 99.5). So every page was re-OCR'd instead of using the PDF's text layer.
- **Alignment:** 40 random KEEP pairs from the final output read by hand: **40 / 40 are translations of each other**
  (95 % confidence: at least ~91 % correct; an earlier check of 30 pairs with preliminary settings was also 30 / 30). Pairs with
  little word overlap are still usually right (e.g. *Aneuk pimoe ayah pimoe* ↔ *Anak menangis ayahpun menangis*); they are KEEP
  only when both neighbouring pairs are strong matches, otherwise REVIEW.
- **OCR repair:** 223 single-letter repairs proposed on the full text and all were read: about 4 were doubtful (e.g. *merab-raba* → *merah-raba*);
  words shorter than 5 letters are never changed (in Indonesian *bak* "like" and *nang* are real words, not OCR slips).
- Remaining known noise: a few OCR slips the repair cannot decide; the Indonesian is an older literary translation (some
  archaic words, *Mesjid*, *ananda*), not modern everyday Indonesian.
- These checks were made by the developer (Claude). An Acehnese speaker should confirm a random sample of ~50 pairs
  (`data/review/abu_sammah_review.csv` holds the 199 uncertain ones).
