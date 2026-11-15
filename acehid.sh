#!/bin/sh
# Run any acehid command with the project's Python:   ./acehid.sh make-packs --people "A,B,C" --per-person 25
cd "$(dirname "$0")" || exit 1
if [ -x .venv/bin/python ]; then exec .venv/bin/python -m acehid "$@"; fi
exec python3 -m acehid "$@"
