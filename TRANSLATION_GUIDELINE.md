# Translation & normalization guideline (v0.2)

Defaults chosen so work can continue. Items marked **ASK** are open questions for Andrie / an Acehnese speaker; change them here once decided.

## Normalization of the Acehnese side (`ace_normalized`)
`ace_raw` is never modified. Rules, in order, each logged per row in `norm_rules`:
1. `unicode`: NFC, curly quotes → `'`, non-breaking/zero-width spaces removed, whitespace collapsed.
2. `old_spell`: word-initial Dutch-era `dj→j`, `tj→c`, `nj→ny` (`njang → nyang`, `djipeugot → jipeugot`).
3. `diaeresis` (Andrie's rule): `ö ë ü ï ä → o e u i a` (`löen → loen`).
   *Not applied by default:* stripping `é è ô ó ò` (different vowels in Acehnese; `--strip-all` exists but loses information).
   *Not applied:* `oe→u`, `j→y`. In AcehX `oe` is common in modern-spelling files too, so converting it would damage words. Needs a word list or a speaker.

## Indonesian side
Translate from `ace_normalized`. Target is standard Indonesian (PUEBI/EYD). `ind_normalized` currently equals `ind_raw`; a rule-based
PUEBI pass is **not implemented** and must come from the official guidelines/KBBI, not intuition.

## Policy defaults
- Person and place names: keep unchanged. Titles (Teungku, Cut, Sultan, Po, Habib): keep unchanged.
- Cultural terms (meunasah, gampong, khanduri): keep the Acehnese word, no gloss. **ASK** whether to gloss.
- Idioms: translate meaning, not word for word. Literary repetition: keep if natural, else merge.
- Arabic/Malay quotations: **kept as-is, tagged `mixed_language`, status REVIEW, excluded from training.** **ASK** keep or drop.
- Archaic or unclear words: model is told to set `confidence: low`; those rows go to the review sheet. Never guess silently.
- Screening: `lang=mixed` (code-mixed Acehnese/Indonesian) → REVIEW; `lang=ind` → NON_ACEH.
- OCR text is marked `ocr` / `ocr_low_conf` (OCR drops diacritics: `è → e`) and low-confidence pages go to REVIEW.

## Statuses and quality
`machine_draft` (quality low) → `reviewed` (medium) → `human_validated` (high). `human_translated` (NusaX) = high.
Only reviewed/validated/human rows enter the train split by default.

## QC gates (export)
Rejected: no translation, translation identical to source (untranslated copy), length ratio outside 0.4–2.5.
Splits are by **source** so near-identical text cannot leak across train/validation/test.
