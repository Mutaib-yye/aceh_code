"""Stage 3: pages -> sentences -> screening label. Nothing is deleted here, only labelled with a reason.
Labels: KEEP / REVIEW / REMOVE / NON_ACEH / FRAGMENT / OCR_ERROR
Each row also gets lang ('ace'|'ind'|'mixed'), lang_score and tags (e.g. 'mixed_language', 'ocr_low_conf')."""
import re, statistics, collections
import pysbd
from .common import *
from . import langid

_seg = pysbd.Segmenter(language="en", clean=False)   # pysbd has no id/ace model; English rules work for Latin script
PAGE_NO = re.compile(r"^\W*\d{1,4}\W*$")
TERM = re.compile(r"[.!?…][\"')\]”’]*$")
OCR_MIN_CONF = 0.80

def strip_running_lines(pages, min_pages=4):
    """Drop running headers/footers: only the first/last 2 lines of a page are candidates, and only if the same
    (digit-normalized) line sits at the page edge on >=30% of a source's pages (and at least 3). Lines in the middle of a page
    are never touched, because hikayat refrains legitimately repeat. Needs >= min_pages pages."""
    by = collections.defaultdict(list)
    for p in pages:
        by[p["source_id"]].append(p)
    norm = lambda l: re.sub(r"\d+", "#", l.strip().lower())
    edges = lambda ls: set(range(min(2, len(ls)))) | set(range(max(0, len(ls) - 2), len(ls)))
    for ps in by.values():
        if len(ps) < min_pages:
            continue
        cnt = collections.Counter()
        for p in ps:
            ls = [l for l in p["text"].split("\n") if l.strip()]
            cnt.update({norm(ls[i]) for i in edges(ls)})
        need = max(3, -(-3 * len(ps) // 10))
        for p in ps:
            ls = [l for l in p["text"].split("\n") if l.strip()]
            drop = {i for i in edges(ls) if cnt[norm(ls[i])] >= need}
            p["text"] = "\n".join(l for i, l in enumerate(ls) if i not in drop)
    return pages

def detect_layout(text):
    """'verse' if the page is many short, mostly unpunctuated lines (hikayat couplets), else 'prose'."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if len(lines) < 4:
        return "prose"
    mean_len = statistics.mean(len(l) for l in lines)
    term = sum(bool(TERM.search(l)) for l in lines) / len(lines)
    return "verse" if mean_len <= 55 and term < 0.5 else "prose"

def split_page(text, layout="auto"):
    text = text.replace("­", "")
    if layout == "auto":
        layout = detect_layout(text)
    if layout == "verse":
        return [re.sub(r"\s+", " ", l).strip() for l in text.split("\n") if l.strip()], layout
    t = re.sub(r"-\n(?=[a-zà-ÿ])", "", text)                 # re-join words hyphenated at line end
    out = []
    for para in re.split(r"\n\s*\n", t):
        para = re.sub(r"\s*\n\s*", " ", para)                 # single newline = same paragraph
        out += [re.sub(r"\s+", " ", s).strip() for s in _seg.segment(para)]
    return [s for s in out if s], layout

def screen(s, ocr_conf=None):
    """-> (label, reason, lang, lang_score, tags)"""
    n = len(s.split())
    lang, sc = langid.classify(s) if n >= 3 else ("ace", 0.0)
    tags = []
    if ocr_conf is not None:
        tags.append("ocr_low_conf" if ocr_conf < OCR_MIN_CONF else "ocr")
    if PAGE_NO.match(s) or re.match(r"^(bab|halaman|daftar isi|hak cipta|copyright)\b", s.lower()):
        return "REMOVE", "header/footer/page", lang, sc, tags
    if re.search(r"https?://|www\.", s):
        return "REMOVE", "url", lang, sc, tags
    if re.search(r"[؀-ۿ]", s):
        return "REVIEW", "arabic_script", lang, sc, tags + ["mixed_language"]
    if n < 3:
        return "FRAGMENT", "under_3_words", lang, sc, tags
    if n > 80:
        return "REVIEW", "over_80_words", lang, sc, tags
    if sum(c.isalpha() for c in s) / max(1, len(s)) < 0.6:
        return "OCR_ERROR", "low_letter_ratio", lang, sc, tags
    if re.search(r"[^\W\d_]\d[^\W\d_]", s):
        return "OCR_ERROR", "digit_inside_word", lang, sc, tags
    if lang == "ind":
        return "NON_ACEH", "language_check:indonesian", lang, sc, tags
    if lang == "mixed":
        return "REVIEW", "mixed_language", lang, sc, tags + ["mixed_language"]
    if "ocr_low_conf" in tags:
        return "REVIEW", f"ocr_conf_below_{OCR_MIN_CONF}", lang, sc, tags
    return "KEEP", "", lang, sc, tags

def sentences_from_pages(pages, layout="auto"):
    rows, k = [], 0
    pages = strip_running_lines([dict(p) for p in pages if p["method"] != "ocr_needed"])
    for p in pages:
        sents, lay = split_page(p["text"], layout)
        for s in sents:
            k += 1
            label, why, lang, sc, tags = screen(s, p.get("ocr_conf") if p["method"] == "ocr" else None)
            rows.append({"id": f"{p['source_id']}_{k:06d}", "source_id": p["source_id"], "title": p["title"], "license": p["license"],
                         "page": p["page"], "layout": lay, "extraction": p["method"], "ace_raw": s, "screening": label,
                         "screen_reason": why, "lang": lang, "lang_score": sc, "tags": tags})
    return rows

def run(pages="data/extracted/hikayat_pages.jsonl", out="data/cleaned/hikayat_sentences.jsonl", layout="auto"):
    rows = sentences_from_pages(list(read_jsonl(pages)), layout)
    write_jsonl(out, rows)
    log("screen", sentences=len(rows), **dict(collections.Counter(r["screening"] for r in rows)))
    return rows
