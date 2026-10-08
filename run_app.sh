#!/bin/sh
# Start the Acehnese -> Indonesian translator on this computer and open http://127.0.0.1:7860
#   ./run_app.sh            first time: installs, fetches your trained model once; later: starts in seconds, offline
#   ./run_app.sh --share    also prints a temporary public link (works while this window stays open)
cd "$(dirname "$0")" || exit 1
PY=""
for c in python3.12 python3.13 python3.11 python3.14 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "Python 3.10+ not found. Install it (macOS: brew install python@3.12) and re-run."; exit 1; }
if [ -x .venv/bin/python ] && ! .venv/bin/python -c 'import sys' 2>/dev/null; then rm -rf .venv; fi
[ -d .venv ] || "$PY" -m venv .venv || { echo "Could not create .venv with $PY"; exit 1; }
. .venv/bin/activate
if ! python -c 'import gradio, transformers, torch, sentencepiece' 2>/dev/null; then
  echo "Installing (first time only, a few minutes)..."
  python -m pip install -q --upgrade pip >/dev/null 2>&1
  python -m pip install -q "gradio==6.29.1" "transformers==5.19.0" "sentencepiece>=0.2" torch huggingface_hub \
    || { echo "Install failed. Copy the error above and send it to Claude."; exit 1; }
fi
python -m acehid app "$@"
