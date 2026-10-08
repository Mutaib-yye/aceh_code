"""Stage 2: source files -> per-page text rows (data/extracted/hikayat_pages.jsonl).

PDF   : text layer via PyMuPDF; pages with no text layer are OCR'd (RapidOCR, pip-only, no system install)
        and marked method="ocr", ocr_conf=mean confidence. OCR output is RAW, LOW confidence, and loses
        diacritics (e.g. è -> e); screening/review must treat it accordingly. If OCR is unavailable the page is
        flagged "ocr_needed" and skipped later.
TXT   : .txt/.md files; pages separated by form-feed, otherwise one page.
"""
import csv, os, glob
from .common import *

EXTS = (".pdf", ".txt", ".md")
_ocr = None

def ocr_backend():
    """'rapidocr' (v3, any Python), 'rapidocr_onnxruntime' (v1, Python < 3.13) or None. Cheap: does not load models."""
    import importlib.util
    for name in ("rapidocr", "rapidocr_onnxruntime"):
        if importlib.util.find_spec(name):
            return name
    return None

def _get_ocr():
    global _ocr
    if _ocr is None:
        try:
            if ocr_backend() == "rapidocr":
                from rapidocr import RapidOCR
                eng = RapidOCR()
                def run(img):
                    r = eng(img)
                    if r.boxes is None or not r.txts:
                        return []
                    return [(b.tolist(), t, s) for b, t, s in zip(r.boxes, r.txts, r.scores)]
            else:
                from rapidocr_onnxruntime import RapidOCR
                eng = RapidOCR()
                run = lambda img: eng(img)[0] or []
            _ocr = run
        except Exception:
            _ocr = False
    return _ocr

def ocr_page(page, dpi=200):
    eng = _get_ocr()
    if not eng:
        return None, None
    import numpy as np
    pix = page.get_pixmap(dpi=dpi)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    res = eng(np.ascontiguousarray(img[:, :, :3]) if pix.n >= 3 else img)
    if not res:
        return "", 0.0
    # reading order: top->bottom, then left->right (box = 4 corner points); lines sharing a baseline are merged
    items = sorted(((b[0][1], b[0][0], t, float(c)) for b, t, c in res), key=lambda x: (round(x[0] / 12), x[1]))
    lines, last_y = [], None
    for y, x, t, c in items:
        if last_y is not None and abs(y - last_y) < 12 and lines:
            lines[-1] += " " + t
        else:
            lines.append(t)
        last_y = y
    return "\n".join(lines), sum(i[3] for i in items) / len(items)

def load_meta(path="config/sources.csv"):
    p = ROOT / path
    if not p.exists():
        return {}
    return {r["file"]: r for r in csv.DictReader(open(p, encoding="utf-8"))}

def extract_file(path, source_id, meta=None, ocr=True):
    meta = meta or {}
    name = os.path.basename(path)
    m = meta.get(name, {})
    base = {"source_id": source_id, "file": name, "title": m.get("title") or name,
            "license": m.get("license", "UNKNOWN"), "script": m.get("script", "latin")}
    rows = []
    if path.lower().endswith(".pdf"):
        import pymupdf
        for pno, page in enumerate(pymupdf.open(path), 1):
            text, method, conf = page.get_text().strip(), "pdf_text", None
            if len(text) < 30:
                text, method = "", "ocr_needed"
                if ocr:
                    t, conf = ocr_page(page)
                    if t is not None:
                        text, method = t, "ocr"
            rows.append({**base, "page": pno, "text": text, "method": method, "ocr_conf": conf})
    else:
        raw = open(path, encoding="utf-8", errors="replace").read().replace("\r", "")
        for pno, chunk in enumerate(raw.split("\f"), 1):
            rows.append({**base, "page": pno, "text": chunk.strip(), "method": "txt", "ocr_conf": None})
    return rows

def run(src_dir="data/raw/hikayat", out="data/extracted/hikayat_pages.jsonl", ocr=True):
    meta = load_meta()
    files = sorted(f for f in glob.glob(f"{src_dir}/*") if f.lower().endswith(EXTS))
    pages = []
    for i, f in enumerate(files, 1):
        pages += extract_file(f, f"HIK_{i:03d}", meta, ocr)
    n = write_jsonl(out, pages)
    log("extract", files=len(files), pages=n, ocr_pages=sum(p["method"] == "ocr" for p in pages),
        pages_needing_ocr=sum(p["method"] == "ocr_needed" for p in pages))
    return pages
