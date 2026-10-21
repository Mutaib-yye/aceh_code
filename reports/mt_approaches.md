# Machine translation approaches for Acehnese → Indonesian

The professor listed these items: direct approach, transfer approach, interlingual machine translation, data augmentation,
and a disambiguation module. This page says what each one is, where it appears in our project, and what we measured.

## 1. Direct approach
Translate word by word with a bilingual dictionary and keep the source word order. It needs no grammar, but it cannot handle
word order, affixes, or words with several meanings.
**Ours:** `Translator.direct` in `acehid/approaches.py`, using the Kamus Aceh-Indonesia (1985) word list (A–L only, about 5,760 headwords).

## 2. Transfer approach
Three steps: **analysis** of the source sentence (split off prefixes and suffixes), **transfer** with rules and a lexicon,
and **generation** of the target sentence.
**Ours:** `Translator.transfer`. Analysis splits the subject prefixes of Acehnese verbs (ji-, geu-, neu-, ta-) and the suffix -jih
("-nya"). Transfer maps 15 function words (hana → tidak, nyang → yang, ...) that the NusaX training sentences support
(the Indonesian word appears in at least 50% of the sentences that contain the Acehnese word; 20+ sentences). Everything else is
looked up in the dictionary.

## 3. Interlingual machine translation
Translate the source into a language-neutral meaning representation (the interlingua), then generate the target language from it.
Classic interlingua systems used hand-built symbolic representations. We did not build one: that needs a full semantic model of both languages.
**Ours (closest equivalent):** NLLB-200 is a neural encoder–decoder trained on about 200 languages, so the encoder maps every language into a shared
vector space and the decoder writes any target language from it. This is a learned, not hand-written, interlingua. The app's
"Cara kerja model" panel shows the encoder tokens and the decoder tokens.

## 4. Neural machine translation (what the app uses)
NLLB-200 distilled 600M, fine-tuned on our Acehnese–Indonesian pairs (see `reports/pipeline_report.md`).

## 5. Data augmentation
Making more training data from what exists. In our project:
- **Pivot translation** (`acehid/pivot.py`): NLLB-Seed has human Acehnese sentences paired with English. We translate the English into Indonesian with NLLB
  (a strong direction) and pair it with the human Acehnese: about 5,750 extra pairs, labelled as machine target.
- **Not yet done:** back-translation (generate synthetic Acehnese from Indonesian text) and mining Wikipedia articles for aligned sentences.
Every augmented source is judged by training with and without it and comparing held-out scores (the `USE_SEED_PIVOT` switch in the Colab notebook).

## 6. Disambiguation module
Many Acehnese words have several meanings (for example "adat", "acu", "abaih" in the dictionary have more than one entry).
**Ours (simple):** the app's "Kata per kata" panel lists the meanings of each word and marks with ✓ the meaning that shares the most
words with the model's Indonesian translation. It only marks a meaning when one clearly wins. It is a word-sense disambiguation aid, not a full module:
it does not change the translation itself.

## Results on the NusaX test set (400 held-out sentences)

Score: chrF++ (0–100, higher is better); BLEU in brackets. Measured with `python -m acehid compare-approaches`.

| System | chrF++ | BLEU |
|---|---|---|
| Copy (Acehnese text left unchanged) | 32.0 | 6.3 |
| Direct (dictionary, word for word) | 35.5 | 6.1 |
| Transfer (rules + dictionary) | 39.2 | 9.1 |
| Neural, base NLLB-200 (not fine-tuned) | [fill in from Colab] | [fill in] |
| Neural, fine-tuned on our data | [fill in from Colab] | [fill in] |

## Limits you should state
- The dictionary covers only words beginning A–L, and its extraction is automatic and not fully validated, so some meanings are noisy.
- The rules are hand-written and small. They sometimes fire wrongly: for example "tapak" was split as ta- + "pak" ("kita pajak gadai").
- The rule baselines are weak on purpose: they show how far the older approaches get, and why the neural model is used.
- The source dictionary and the Kamus are copyrighted; keep their data files out of the public repo.
