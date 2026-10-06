#!/bin/sh
# End to end. Put hikayat PDFs/TXT in data/raw/hikayat/ and add a row per file to config/sources.csv first.
# AcehX .txt files go in data/raw/acehx/ (needed for the duplicate check against AcehX).
set -e
pip install -q -r requirements.txt
python3 -m acehid fetch-nusax
python3 -m acehid audit            # AcehX -> data/extracted/acehx.jsonl + reports/acehx_audit.md
python3 -m acehid nusax            # NusaX-MT -> data/final/nusax/ (needs data/raw/external/nusax/*.csv)
python3 -m acehid all              # extract (+OCR) -> screen -> normalize -> dedupe -> data/review/review_sheet.csv
# A human fixes data/review/review_sheet.csv (decision column), then:
#   python3 -m acehid review-import data/review/review_sheet.csv
# Translation (pick one; keys only from environment variables):
#   ANTHROPIC_API_KEY=... python3 -m acehid translate --provider claude
#   python3 -m acehid translate --provider nllb            # local / Colab, no key
# python3 -m acehid export --include-drafts               # drafts are excluded from training unless you pass this
