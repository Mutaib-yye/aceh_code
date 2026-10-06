"""Whole pipeline in-process: source file(s) -> screened, normalized, deduplicated sentence rows (ready for translation/review/export)."""
import tempfile, os, shutil
from .common import *
from . import extract, screen, normalize, dedupe

def process_files(paths, ocr=True, layout="auto", ref=None, meta=None, start_index=1):
    pages = []
    for i, p in enumerate(paths, start_index):
        pages += extract.extract_file(p, f"HIK_{i:03d}", meta or extract.load_meta(), ocr)
    rows = screen.sentences_from_pages(pages, layout)
    rows = normalize.run(rows)
    rows = dedupe.run(rows, ref=ref)
    return pages, rows

def summary(rows):
    import collections
    return {"sentences": len(rows), "screening": dict(collections.Counter(r["screening"] for r in rows)),
            "dedup": dict(collections.Counter(r["dedup"] for r in rows)),
            "usable_for_translation": sum(r["screening"] == "KEEP" and r["dedup"] == "unique" for r in rows)}
