#!/bin/sh
# One-command local GUI (macOS/Linux): creates a venv, installs, fetches NusaX, opens http://127.0.0.1:8000
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q -r requirements.txt
# free local translation engine (NLLB, no API key). First translation downloads the model once (~2.5 GB). Skip with: ./start.sh --light
[ "$1" = "--light" ] || pip install -q transformers torch sentencepiece
[ -f data/raw/external/nusax/train.csv ] || python -m acehid fetch-nusax
[ -f config/langid_model.json.gz ] || python -m acehid langid-build
# Optional: put AcehX .txt files in data/raw/acehx/ and run `python -m acehid audit` once to enable the duplicate check.
python -m acehid serve --open
