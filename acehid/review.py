"""Human review sheet: export rows that need a person (REVIEW / NEAR_DUP_REVIEW / OCR_ERROR / mixed language / low-confidence MT)
to CSV, a human fills `decision` (+ optional `ace_fixed` / `ind_fixed`), and `import_sheet` applies it.
decision values: keep | remove | edit.   After `edit`/`keep` of a machine draft, set translation_status via `mark` (reviewed|human_validated)."""
import csv
from .common import *
from .normalize import normalize

COLS = ["id", "source_id", "page", "reason", "ace_raw", "ace_normalized", "ind_raw", "dedup_ref", "decision", "ace_fixed", "ind_fixed", "notes"]

def needs_review(r):
    why = []
    if r.get("screening") in ("REVIEW", "OCR_ERROR"):
        why.append(f"{r['screening']}:{r.get('screen_reason','')}")
    if r.get("dedup") == "NEAR_DUP_REVIEW":
        why.append("NEAR_DUP_REVIEW")
    if r.get("mt_confidence") == "low":
        why.append("MT_LOW_CONFIDENCE")
    return ";".join(why)

def export_sheet(rows, path):
    sel = [(r, needs_review(r)) for r in rows]
    sel = [(r, w) for r, w in sel if w]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:     # utf-8-sig so Excel opens Acehnese diacritics correctly
        w = csv.DictWriter(f, COLS); w.writeheader()
        for r, why in sel:
            w.writerow({"id": r["id"], "source_id": r["source_id"], "page": r.get("page"), "reason": why, "ace_raw": r["ace_raw"],
                        "ace_normalized": r.get("ace_normalized", ""), "ind_raw": r.get("ind_raw", ""), "dedup_ref": r.get("dedup_ref") or ""})
    log("review_export", rows=len(sel))
    return len(sel)

def import_sheet(rows, path, mark="reviewed"):
    dec = {r["id"]: r for r in csv.DictReader(open(path, encoding="utf-8-sig"))}
    n = {"keep": 0, "remove": 0, "edit": 0}
    for r in rows:
        d = dec.get(r["id"])
        if not d or not d.get("decision", "").strip():
            continue
        x = d["decision"].strip().lower()
        if x == "remove":
            r["screening"], r["screen_reason"] = "REMOVE", "human"
        elif x in ("keep", "edit"):
            r["screening"], r["screen_reason"] = "KEEP", "human"
            if r.get("dedup") == "NEAR_DUP_REVIEW":
                r["dedup"] = "unique"
            if x == "edit":
                if d.get("ace_fixed", "").strip():
                    r["ace_raw_original"] = r["ace_raw"]; r["ace_raw"] = d["ace_fixed"].strip()
                    r["ace_normalized"], r["norm_rules"] = normalize(r["ace_raw"])
                if d.get("ind_fixed", "").strip():
                    r["ind_raw"] = d["ind_fixed"].strip(); r["translation_status"] = mark
        else:
            continue
        n[x] += 1
    log("review_import", **n)
    return rows
