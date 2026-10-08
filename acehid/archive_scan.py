"""Inventory of a large archive of Acehnese material (RAR, ZIP or folder): per PDF, page count, text layer, language of the
text, and whether it looks bilingual. Writes reports/archive_<name>.csv and .md with counts and file names only, no text from
the books, so the result can be shared. The extracted files stay where they are (data/raw/archive/, git-ignored)."""
import collections, csv, datetime, re, shutil, subprocess, zipfile
from pathlib import Path
from .common import *
from . import langid

TYPE_HINTS = [("kamus", "dictionary"), ("dictionary", "dictionary"), ("lagu", "song"), ("lirik", "song"), ("syair", "syair"),
              ("hikayat", "hikayat"), ("pantun", "pantun"), ("seumapa", "seumapa"), ("doa", "prayer")]
MIN_WORDS, SAMPLE_LINES, MIN_TEXT_CHARS = 3, 1500, 30

def type_guess(name):
    n = name.lower()
    return next((t for k, t in TYPE_HINTS if k in n), "other")

def extract(src, workdir):
    src = Path(src)
    if src.is_dir():
        return src
    out = Path(workdir) / re.sub(r"[^A-Za-z0-9]+", "_", src.stem).strip("_").lower()
    out.mkdir(parents=True, exist_ok=True)
    if zipfile.is_zipfile(src):
        with zipfile.ZipFile(src) as z:
            z.extractall(out)
    elif shutil.which("unar"):
        subprocess.run(["unar", "-q", "-f", "-o", str(out), str(src)], check=True)
    elif shutil.which("bsdtar"):
        subprocess.run(["bsdtar", "-xf", str(src), "-C", str(out)], check=True)
    else:
        raise SystemExit("Cannot open this archive. On a Mac run: brew install unar   (then run the command again)")
    return out

def inspect_pdf(path):
    import pymupdf
    doc = pymupdf.open(str(path))
    text_pages, lines = 0, []
    for page in doc:
        if len(page.get_text().strip()) >= MIN_TEXT_CHARS:
            text_pages += 1
            for line in page.get_text().splitlines():
                if len(line.split()) >= MIN_WORDS:
                    lines.append((page.number + 1, " ".join(line.split())))
    step = max(1, len(lines) // SAMPLE_LINES)
    counts, per_page = collections.Counter(), collections.defaultdict(collections.Counter)
    for pg, line in lines[::step]:
        label, _ = langid.classify(line)
        counts[label] += 1
        per_page[pg][label] += 1
    n = sum(counts.values()) or 1
    ace_pages = sum(1 for c in per_page.values() if c["ace"] > c["ind"] and c["ace"] >= 2)
    ind_pages = sum(1 for c in per_page.values() if c["ind"] > c["ace"] and c["ind"] >= 2)
    both_pages = sum(1 for c in per_page.values() if c["ace"] >= 2 and c["ind"] >= 2)
    ace_share, ind_share = counts["ace"] / n, counts["ind"] / n
    bilingual = both_pages >= 3 or (ace_pages >= 10 and ind_pages >= 10 and ace_share >= 0.2 and ind_share >= 0.2)
    return {"pages": len(doc), "text_pages": text_pages, "scan_pages": len(doc) - text_pages, "lines_sampled": n if counts else 0,
            "ace_share": round(ace_share, 3), "ind_share": round(ind_share, 3), "mixed_share": round(counts["mixed"] / n, 3),
            "ace_majority_pages": ace_pages, "ind_majority_pages": ind_pages, "both_language_pages": both_pages,
            "possibly_bilingual": bilingual}

def scan(src, workdir=ROOT / "data/raw/archive", out_dir=ROOT / "reports", log_fn=print):
    src = Path(src)
    root = extract(src, workdir)
    name = src.stem if src.is_file() else src.name
    slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").lower()
    rows, others = [], collections.Counter()
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        if f.suffix.lower() != ".pdf":
            others[f.suffix.lower() or "(none)"] += 1
            continue
        try:
            info = inspect_pdf(f)
        except Exception as e:
            info = {"error": str(e)[:120]}
        rows.append({"file": f.relative_to(root).as_posix(), "type_guess": type_guess(f.name), "size_kb": round(f.stat().st_size / 1024), **info})
        log_fn(f"  {f.name[:70]}: {info.get('pages', '?')} pages, {info.get('scan_pages', '?')} need OCR, possibly_bilingual={info.get('possibly_bilingual')}")
    out_dir.mkdir(parents=True, exist_ok=True)
    cols = ["file", "type_guess", "size_kb", "pages", "text_pages", "scan_pages", "lines_sampled", "ace_share", "ind_share", "mixed_share",
            "ace_majority_pages", "ind_majority_pages", "both_language_pages", "possibly_bilingual", "error"]
    with open(out_dir / f"archive_{slug}.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    write_md(out_dir / f"archive_{slug}.md", name, rows, others)
    log("archive", pdfs=len(rows), report=f"reports/archive_{slug}.csv")
    return rows

def write_md(path, name, rows, others):
    ok = [r for r in rows if "error" not in r]
    pages = sum(r["pages"] for r in ok); scan_pages = sum(r["scan_pages"] for r in ok)
    lines = [f"# Archive inventory: {name}", "",
             f"Scanned {datetime.date.today().isoformat()}. Counts and language shares only; no text from the files is written here.", "",
             f"- PDFs: {len(rows)} ({len(rows) - len(ok)} could not be read)",
             f"- Pages: {pages}, of which {scan_pages} have no text layer (need OCR)",
             f"- Other files: " + (", ".join(f"{n} {ext}" for ext, n in others.most_common()) or "none"), "",
             "## By type guess (from file names)", "", "| type | files | pages |", "|---|---|---|"]
    by = collections.defaultdict(lambda: [0, 0])
    for r in ok:
        by[r["type_guess"]][0] += 1; by[r["type_guess"]][1] += r["pages"]
    lines += [f"| {t} | {n} | {p} |" for t, (n, p) in sorted(by.items(), key=lambda x: -x[1][1])]
    bil = [r for r in ok if r["possibly_bilingual"]]
    lines += ["", f"## Possibly bilingual ({len(bil)} files)", "",
              "| file | ace share | ind share | ace-majority pages | ind-majority pages |", "|---|---|---|---|---|"]
    lines += [f"| {r['file']} | {r['ace_share']} | {r['ind_share']} | {r['ace_majority_pages']} | {r['ind_majority_pages']} |" for r in bil]
    ocr = [r for r in ok if r["scan_pages"] > 0]
    lines += ["", f"## Needs OCR ({len(ocr)} files)", "", "| file | scanned pages of total |", "|---|---|"]
    lines += [f"| {r['file']} | {r['scan_pages']} of {r['pages']} |" for r in ocr]
    lines += ["", f"## All files ({len(rows)})", "",
              "| file | type | pages | need OCR | ace share | ind share | possibly bilingual |", "|---|---|---|---|---|---|---|"]
    lines += [f"| {r['file']} | {r['type_guess']} | {r.get('pages', '')} | {r.get('scan_pages', '')} | {r.get('ace_share', '')} | "
              f"{r.get('ind_share', '')} | {'yes' if r.get('possibly_bilingual') else ''} |" for r in rows]
    bad = [r for r in rows if "error" in r]
    if bad:
        lines += ["", "## Could not read", ""] + [f"- {r['file']}: {r['error']}" for r in bad]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
