#!/bin/sh
# One-command local GUI (macOS/Linux): creates .venv, installs, fetches NusaX, opens http://127.0.0.1:8000
#   ./start.sh          full install (includes the free NLLB engine; first translation downloads its model once, ~2.5 GB)
#   ./start.sh --light  no NLLB/torch (Claude key or 'copy' baseline only)
cd "$(dirname "$0")" || exit 1
PY=""
for c in python3.12 python3.13 python3.11 python3.14 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "Python 3.10+ not found. Install it (macOS: brew install python@3.12) and re-run."; exit 1; }
if [ -x .venv/bin/python ] && ! .venv/bin/python -c 'import sys' 2>/dev/null; then rm -rf .venv; fi
[ -d .venv ] || "$PY" -m venv .venv || { echo "Could not create .venv with $PY"; exit 1; }
. .venv/bin/activate
echo "Using $(python --version) in .venv"
python -m pip install -q --upgrade pip >/dev/null 2>&1
if ! python -m pip install -q -r requirements.txt; then
  echo "Full install failed; retrying without OCR (scanned PDFs will be flagged 'ocr_needed' instead of OCR'd)."
  grep -viE 'rapidocr|onnxruntime' requirements.txt > .venv/req-no-ocr.txt
  python -m pip install -q -r .venv/req-no-ocr.txt || { echo "Install failed. Copy the error above and send it to Claude."; exit 1; }
fi
if [ "$1" != "--light" ]; then
  python -m pip install -q transformers torch sentencepiece || echo "NLLB engine not installed (torch failed); continuing without it."
fi
[ -f data/raw/external/nusax/train.csv ] || python -m acehid fetch-nusax
[ -f config/langid_model.json.gz ] || python -m acehid langid-build
# Optional: put AcehX .txt files in data/raw/acehx/ and run `python -m acehid audit` once to enable the duplicate check.
python -m acehid serve --open
