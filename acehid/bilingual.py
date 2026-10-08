"""Bilingual book -> aligned Acehnese/Indonesian line pairs (e.g. Depdikbud hikayat editions: Bab "Alihaksara" = Acehnese text,
Bab "Alih Bahasa" = its Indonesian translation, same verse lines in the same order).

1. OCR   : every page of both sections is re-OCR'd with RapidOCR at 300 dpi (on the Hikayat Abu Sammah scan this gave
           0.8 % word errors vs 11.3 % for the PDF's own Acrobat text layer; measured on 16 hand-checked lines).
           Lines keep their OCR confidence. Page numbers and chapter headings are dropped.
2. ALIGN : monotonic dynamic programming over the two line sequences (1-1, 1-0, 0-1, 2-1, 1-2 steps), scored by
           shared words/cognates (Acehnese and Indonesian share many: hikayat, Allah, ajab, indah, names), a bilingual
           word list, line-length ratio and relative position. Same idea as Hunalign / Gale-Church, at verse-line level.
3. QC    : each pair gets align_score + ocr_conf; low ones are flagged for review instead of being trusted.
The translation itself is a published human translation, so pairs are `human_translated` (not machine drafts)."""
import re, json, math
from .common import *

def ocr_lines(page, dpi=300):
    """-> [{'text','conf','y','h'}] in reading order, one entry per printed line."""
    from .extract import _get_ocr
    import numpy as np
    eng = _get_ocr()
    if not eng:
        raise RuntimeError("OCR not installed: pip install rapidocr onnxruntime")
    pix = page.get_pixmap(dpi=dpi)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    res = eng(np.ascontiguousarray(img[:, :, :3]) if pix.n >= 3 else img) or []
    boxes = []
    for b, t, c in res:
        ys = [p[1] for p in b]; xs = [p[0] for p in b]
        boxes.append({"y": (min(ys) + max(ys)) / 2, "h": max(ys) - min(ys), "x": min(xs), "text": t.strip(), "conf": float(c)})
    if not boxes:
        return []
    med_h = sorted(b["h"] for b in boxes)[len(boxes) // 2]
    lines = []
    for b in sorted(boxes, key=lambda b: b["y"]):
        if lines and abs(b["y"] - lines[-1]["y"]) < 0.5 * med_h:
            lines[-1]["parts"].append(b)
        else:
            lines.append({"y": b["y"], "parts": [b]})
    out = []
    for l in lines:
        parts = sorted(l["parts"], key=lambda b: b["x"])
        n = sum(len(p["text"]) for p in parts) or 1
        out.append({"text": " ".join(p["text"] for p in parts), "conf": round(sum(p["conf"] * len(p["text"]) for p in parts) / n, 4),
                    "y": round(l["y"] * 72 / dpi, 1), "h": round(med_h * 72 / dpi, 1)})
    return out

def ocr_pdf(pdf, pages, dpi=300, cache=None, progress=None):
    """OCR the given 1-based pages; results cached as JSONL (one row per page) so re-runs are instant."""
    import pymupdf
    done = {}
    if cache and Path(cache).exists():
        done = {r["page"]: r for r in read_jsonl(cache)}
    doc = pymupdf.open(pdf)
    for p in pages:
        if p not in done:
            done[p] = {"page": p, "lines": ocr_lines(doc[p - 1], dpi)}
            if cache:
                write_jsonl(cache, [done[k] for k in sorted(done)])
            if progress:
                progress(p)
    return [done[p] for p in pages]

# --- cleaning -------------------------------------------------------------------------------------------------------------
_HEADING = re.compile(r"^\W*(bab\W*[ivxl1|\u2160-\u217f]{0,5}|alih\s*aksara|alih\s*bahasa)\W*$", re.I)
_FOOTNOTE = re.compile(r"^\W{0,3}\d{0,2}\s*\)\s*\S")            # ') Pedang', '1) Pedang', '*) ...'

def _garbage(t):
    toks = t.split()
    return len(toks) >= 3 and sum(len(w) <= 2 for w in toks) / len(toks) > 0.5     # 'Na e d e lana', 'Amms n n mn o an'

def section_lines(pages, min_conf=0.85):
    """OCR page rows -> [{'text','conf','page','n'}]: drops page numbers, chapter headings, footnotes, unreadable OCR lines;
    re-joins wrapped continuations (a 1-2 word line belongs to the line above, e.g. '... belum' + 'masanya')."""
    out, dropped = [], {"heading": 0, "page_no": 0, "footnote": 0, "low_conf": 0, "garbage": 0, "rejoined": 0}
    for r in pages:
        first = len(out)
        for k, l in enumerate(r["lines"]):
            t = " ".join(l["text"].split())
            if not t:
                continue
            if re.fullmatch(r"[\d\W]{1,4}", t):
                dropped["page_no"] += 1
            elif _HEADING.match(t):
                dropped["heading"] += 1
            elif _FOOTNOTE.match(t):
                dropped["footnote"] += 1
            elif l["conf"] < min_conf:
                dropped["low_conf"] += 1
            elif _garbage(t):
                dropped["garbage"] += 1
            elif len(t.split()) <= 2 and len(out) > first:
                out[-1]["text"] += " " + t; out[-1]["conf"] = min(out[-1]["conf"], l["conf"]); dropped["rejoined"] += 1
            else:
                out.append({"text": t, "conf": l["conf"], "page": r["page"], "n": k})
    section_lines.last_stats = dropped
    return out

# --- OCR spelling repair -----------------------------------------------------------------------------------------------------
# RapidOCR's typical slips on this print: e->c (kreueh->kreuch, pimoe->pimoc), h->b (hukum->bukum), m->rn/rb, d->cl, u->n.
CONFUSIONS = [("c", "e"), ("b", "h"), ("rn", "m"), ("rb", "m"), ("cl", "d"), ("n", "u"), ("u", "n"), ("l", "i"), ("i", "l"), ("I", "l")]

def word_counts(texts):
    import collections
    c = collections.Counter()
    for t in texts:
        c.update(w.lower() for w in re.findall(r"[^\W\d_]+", t))
    return c

def repair(text, vocab, min_count=5):
    """Replace a word that is rare/unknown in `vocab` by a one-confusion variant that is common in it. -> (text, n_fixed)."""
    fixed = 0
    def fix(m):
        nonlocal fixed
        w = m.group(0); lw = w.lower()
        n = vocab.get(lw, 0)
        if n >= 2 or (len(lw) < 5 and n > 0):
            return w
        best, bc = None, min_count - 1
        for a, b in CONFUSIONS:
            if len(lw) < 5 and (a, b) != ("c", "e"):     # short words: a one-letter change often gives another real word (bak/hak)
                continue
            start = lw.find(a.lower())
            while start != -1:
                cand = lw[:start] + b + lw[start + len(a):]
                if vocab.get(cand, 0) > bc:
                    best, bc = cand, vocab[cand]
                start = lw.find(a.lower(), start + 1)
        if not best:
            return w
        fixed += 1
        return best.capitalize() if w[0].isupper() else best
    return re.sub(r"[^\W\d_]+", fix, text), fixed

# --- similarity ------------------------------------------------------------------------------------------------------------
def _words(s):
    return [w for w in re.findall(r"[a-z]+", strip_diacritics(s.lower())) if len(w) > 1]

def _skel(w):
    """Rough Acehnese/Indonesian cognate key: neureuka/neraka, seulamat/selamat, rumoh/rumah, teumpat/tempat."""
    w = re.sub(r"eu|e", "e", w); w = w.replace("oe", "u").replace("ue", "u").replace("ie", "i").replace("ee", "e")
    w = re.sub(r"(?<=[^aeiou])e(?=[^aeiou])", "", w) if len(w) > 4 else w      # drop schwa: beureukat -> brkat ~ berkat -> brkat
    return re.sub(r"(oh|ih|uh)$", "ah", w)

def load_lexicon(paths):
    """{acehnese_word: {indonesian words}} from TSV/CSV files with an Acehnese and an Indonesian column."""
    import csv
    lex = {}
    for p in paths:
        with open(p, encoding="utf-8", errors="replace") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            continue
        cols = {c.lower(): c for c in rows[0]}
        a = next((cols[c] for c in cols if c in ("acehnese", "aceh", "ace")), None)
        i = next((cols[c] for c in cols if c in ("indonesian", "indonesia", "ind", "id")), None)
        if not (a and i):
            continue
        for r in rows:
            for aw in _words(r[a] or ""):
                lex.setdefault(aw, set()).update(_words(r[i] or ""))
    return lex

class _Side:
    """Pre-tokenized lines (words + cognate keys) so the aligner can score thousands of candidate pairs quickly."""
    def __init__(self, texts):
        self.words = [_words(t) for t in texts]
        self.skels = [[_skel(w) for w in ws] for ws in self.words]

def _sim_tokens(A, A_sk, B, B_sk, lex=None):
    from rapidfuzz import process, fuzz
    if not A or not B:
        return 0.0
    Bset, Bs = set(B), set(B_sk)
    Bs_long = [b for b in Bs if len(b) >= 4]
    hit = 0
    for w, k in zip(A, A_sk):
        if w in Bset or k in Bs or (lex and lex.get(w, set()) & Bset):
            hit += 1
        elif len(k) >= 4 and Bs_long and process.extractOne(k, Bs_long, scorer=fuzz.ratio, score_cutoff=80):
            hit += 1
    lr = min(len(A), len(B)) / max(len(A), len(B))
    return 2 * hit / (len(A) + len(B)) * (0.6 + 0.4 * lr)

def similarity(ace, ind, lex=None):
    """0..1: share of words that have a cognate or dictionary match on the other side (Dice-style), damped by length ratio."""
    a, b = _Side([ace]), _Side([ind])
    return round(_sim_tokens(a.words[0], a.skels[0], b.words[0], b.skels[0], lex), 4)

# --- alignment -------------------------------------------------------------------------------------------------------------
def align(ace, ind, lex=None, band=60, pair_bonus=0.15, skip_cost=0.3, merge_cost=0.35):
    """Monotonic DP over two line lists (dicts with 'text'). Steps 1-1, 1-0, 0-1, 2-1, 1-2.
    Verse translations are almost always line-for-line, so a 1-1 step gets a bonus and skipping a line costs; the DP leaves
    the diagonal only when the cognate/dictionary evidence for a shifted alignment is clearly stronger.
    -> [(ace_indices, ind_indices, similarity)] for the matched steps."""
    N, M = len(ace), len(ind)
    SA, SB = _Side([a["text"] for a in ace]), _Side([b["text"] for b in ind])
    cache = {}
    def sim(i0, i1, j0, j1):
        k = (i0, i1, j0, j1)
        if k not in cache:
            A = [w for i in range(i0, i1) for w in SA.words[i]]; Ak = [w for i in range(i0, i1) for w in SA.skels[i]]
            B = [w for j in range(j0, j1) for w in SB.words[j]]; Bk = [w for j in range(j0, j1) for w in SB.skels[j]]
            cache[k] = _sim_tokens(A, Ak, B, Bk, lex)
        return cache[k]
    best = {(0, 0): (0.0, None, None)}
    for i in range(N + 1):
        centre = i * M / max(1, N)
        for j in range(max(0, int(centre - band)), min(M, int(centre + band)) + 1):
            if (i, j) == (0, 0):
                continue
            top = None
            for di, dj in ((1, 1), (1, 0), (0, 1), (2, 1), (1, 2)):
                p = (i - di, j - dj)
                if p not in best:
                    continue
                if di and dj:
                    gain = sim(p[0], i, p[1], j) + pair_bonus - (merge_cost if di + dj == 3 else 0.0)
                else:
                    gain = -skip_cost
                c = (best[p][0] + gain, p, (di, dj))
                if top is None or c[0] > top[0]:
                    top = c
            if top:
                best[(i, j)] = top
    if (N, M) not in best:
        raise ValueError("alignment band too narrow")
    steps, cur = [], (N, M)
    while cur != (0, 0):
        _, prev, (di, dj) = best[cur]
        if di and dj:
            steps.append((list(range(prev[0], cur[0])), list(range(prev[1], cur[1])), round(sim(prev[0], cur[0], prev[1], cur[1]), 4)))
        cur = prev
    return steps[::-1]

# --- whole book -> pairs ---------------------------------------------------------------------------------------------------
def _pages(spec):
    a, b = (int(x) for x in spec.split("-"))
    return list(range(a, b + 1))

def _copyish(ace, ind):
    A, B = set(_words(ace)), set(_words(ind))
    return bool(A) and len(A & B) / len(A | B) > 0.7            # untranslated lines (Arabic prayers, Bismillah)

def build_pairs(pdf, ace_pages, ind_pages, source_id="HIK_ABU_SAMMAH", title="Hikayat Abu Sammah",
                license="Depdikbud publication ('Milik Depdikbud, tidak diperdagangkan'); confirm reuse terms",
                ocr_cache=None, ace_vocab_texts=(), ind_vocab_texts=(), lex=None):
    """-> (rows, stats). One row per aligned verse pair, with labels (nothing is deleted)."""
    pa, pi = _pages(ace_pages), _pages(ind_pages)
    pages = {r["page"]: r for r in ocr_pdf(pdf, pa + pi, cache=ocr_cache)}
    A = section_lines([pages[p] for p in pa]); sa = dict(section_lines.last_stats)
    B = section_lines([pages[p] for p in pi]); sb = dict(section_lines.last_stats)
    # references only: counting the book itself would make a systematic OCR slip (e.g. 'ateuch') look like a real word
    va, vi = word_counts(ace_vocab_texts), word_counts(ind_vocab_texts)
    for side, vocab in ((A, va), (B, vi)):
        for x in side:
            x["text"], x["fixes"] = repair(x["text"], vocab) if vocab else (x["text"], 0)
    steps = align(A, B, lex)
    from .normalize import normalize
    rows = []
    for k, (ia, ib, sim) in enumerate(steps):
        ace = " ".join(A[i]["text"] for i in ia); ind = " ".join(B[j]["text"] for j in ib)
        prev_ok = k > 0 and len(steps[k - 1][0]) == len(steps[k - 1][1]) == 1 and steps[k - 1][2] >= 0.15
        next_ok = k + 1 < len(steps) and len(steps[k + 1][0]) == len(steps[k + 1][1]) == 1 and steps[k + 1][2] >= 0.15
        conf = min([A[i]["conf"] for i in ia] + [B[j]["conf"] for j in ib])
        kind = f"{len(ia)}-{len(ib)}"
        copy = _copyish(ace, ind)
        if copy:
            screening, reason = "REMOVE", "untranslated (same text both sides)"
        elif kind == "1-1" and (sim >= 0.15 or (prev_ok and next_ok)) and conf >= 0.9:
            screening, reason = "KEEP", ""
        else:
            screening, reason = "REVIEW", f"{kind} alignment, similarity {sim:.2f}, OCR confidence {conf:.2f}"
        norm, rules = normalize(ace)
        rows.append({"id": f"{source_id}_{k:05d}", "source_id": source_id, "title": title, "license": license,
                     "page": A[ia[0]]["page"], "page_ind": B[ib[0]]["page"], "ace_raw": ace, "ace_normalized": norm, "norm_rules": rules,
                     "ind_raw": ind, "translation_status": "human_translated", "align": kind, "align_score": sim,
                     "anchored": prev_ok and next_ok, "ocr_conf": round(conf, 3), "ocr_fixes": sum(A[i]["fixes"] for i in ia) + sum(B[j]["fixes"] for j in ib),
                     "screening": screening, "screen_reason": reason, "tags": ["hikayat", "verse"]})
    used_a = {i for ia, _, _ in steps for i in ia}; used_b = {j for _, ib, _ in steps for j in ib}
    stats = {"ace_lines": len(A), "ind_lines": len(B), "ace_dropped": sa, "ind_dropped": sb, "pairs": len(rows),
             "align_kinds": dict(__import__("collections").Counter(r["align"] for r in rows)),
             "unaligned_ace": len(A) - len(used_a), "unaligned_ind": len(B) - len(used_b),
             "ocr_words_fixed": {"ace": sum(x["fixes"] for x in A), "ind": sum(x["fixes"] for x in B)},
             "screening": dict(__import__("collections").Counter(r["screening"] for r in rows))}
    return rows, stats

def block_split(rows, test_pages, valid_pages):
    """Contiguous page blocks, so neighbouring verses (which often continue each other) never straddle train and test."""
    tp, vp = set(_pages(test_pages)), set(_pages(valid_pages))
    return ({"train": [r for r in rows if r["page"] not in tp | vp], "validation": [r for r in rows if r["page"] in vp],
             "test": [r for r in rows if r["page"] in tp]})

def _vocab_texts():
    """Spelling references for OCR repair: AcehX (Acehnese) and every Indonesian text we have (NusaX, FLORES, Quran if fetched)."""
    ace, ind = [], []
    ax = ROOT / "data/extracted/acehx.jsonl"
    if ax.exists():
        ace = [r["ace_raw"] for r in read_jsonl(ax)]
    for f in list((ROOT / "data/final/nusax").glob("*.json")) + list((ROOT / "data/final/flores").glob("dev*.json")):
        if f.name.startswith(("train", "validation", "test", "dev")):
            ind += [r["ind"] for r in json.load(open(f, encoding="utf-8"))]
    for f in (ROOT / "data/raw/external/quran").glob("ind-*.json"):
        ind += [v["text"] for v in json.load(open(f, encoding="utf-8"))["quran"]]
    return ace, ind

def run(pdf, ace_pages, ind_pages, test_pages, valid_pages, slug="abu_sammah", source_id="HIK_ABU_SAMMAH", title="Hikayat Abu Sammah"):
    from . import dedupe, review, export as ex
    ace_v, ind_v = _vocab_texts()
    rows, stats = build_pairs(pdf, ace_pages, ind_pages, source_id, title, ocr_cache=ROOT / f"data/extracted/{slug}_ocr.jsonl",
                              ace_vocab_texts=ace_v, ind_vocab_texts=ind_v)
    rows = dedupe.run(rows)
    write_jsonl(ROOT / f"data/aligned/{slug}_pairs.jsonl", rows)
    keep = [r for r in rows if r["screening"] == "KEEP"]
    out = ROOT / f"data/final/hikayat/{slug}"; out.mkdir(parents=True, exist_ok=True)
    sizes = {}
    for name, rs in block_split(keep, test_pages, valid_pages).items():
        json.dump([{"ace": r["ace_normalized"], "ind": r["ind_raw"], "id": r["id"]} for r in rs], open(out / f"{name}.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        sizes[name] = len(rs)
    atlas = [ex.to_atlas_record({**r, "page": r["page"]}) for r in keep if r["dedup"] == "unique"]
    json.dump({"version": f"{slug}-v0.1", "license": rows[0]["license"] if rows else "", "n_pairs": len(atlas), "data": atlas},
              open(out / "atlas.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    (ROOT / "data/review").mkdir(parents=True, exist_ok=True)
    n_review = review.export_sheet(rows, ROOT / f"data/review/{slug}_review.csv")
    stats.update(splits=sizes, atlas_records=len(atlas), review_rows=n_review,
                 dedup=dict(__import__("collections").Counter(r["dedup"] for r in rows)), split_pages={"test": test_pages, "validation": valid_pages})
    json.dump(stats, open(out / "stats.json", "w"), indent=1)
    log("hikayat-pairs", pairs=stats["pairs"], keep=len(keep), **sizes, review=n_review)
    return stats
