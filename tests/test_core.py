import json, os, pathlib, textwrap
import pytest
from acehid import normalize, langid, screen, dedupe, export, review, translate
from acehid.common import match_key, key_hash, write_jsonl, read_jsonl, ROOT

NUSAX = ROOT / "data/raw/external/nusax/valid.csv"

# ---- normalize ---------------------------------------------------------------
def test_normalize_rules_and_case():
    assert normalize.normalize("Njang djipeugot löen")[0] == "Nyang jipeugot loen"
    t, rules = normalize.normalize("Ampön ’oh")
    assert t == "Ampon 'oh" and rules == ["unicode", "diaeresis"]
    assert normalize.normalize("TJOET")[0] == "COET"
    # é è ô are different vowels in Acehnese: kept by default
    assert normalize.normalize("meuteumè séh ôh")[0] == "meuteumè séh ôh"
    assert normalize.normalize("meuteumè séh ôh", strip_all=True)[0] == "meuteume seh oh"
    # oe is NOT converted (frequent in modern spelling too)
    assert normalize.normalize("droeneuh")[0] == "droeneuh"

def test_match_key_folds_variants():
    assert key_hash("Njang djipeugot, löen!") == key_hash("nyang jipeugot loen")

# ---- language check ----------------------------------------------------------
def test_langid_basic():
    assert langid.classify("Tiep uroe tuhan jijak u pasi jimeuen ngon anoe")[0] == "ace"
    assert langid.classify("Saya pergi ke pasar untuk membeli sayur dan buah untuk keluarga")[0] == "ind"

@pytest.mark.skipif(not NUSAX.exists(), reason="NusaX not downloaded")
def test_langid_heldout_accuracy():
    ev = langid.evaluate()
    for sp in ("valid", "test"):
        assert ev[sp]["ace_as_ace"] >= 0.94 and ev[sp]["ind_as_ind"] >= 0.98

# ---- screening / segmentation ------------------------------------------------
def pages(texts, sid="HIK_001"):
    return [{"source_id": sid, "title": "t", "license": "x", "page": i + 1, "text": t, "method": "pdf_text"} for i, t in enumerate(texts)]

def test_running_headers_and_page_numbers_removed(ace):
    pg = [f"HIKAYAT CONTOH\n{ace[i % 6]}\n{i+10}" for i in range(6)]
    rows = screen.sentences_from_pages(pages(pg))
    assert not any("HIKAYAT" in r["ace_raw"] for r in rows)
    assert not any(r["ace_raw"].strip().isdigit() for r in rows)

def test_hyphenation_rejoined_and_sentences_split():
    p = pages(["Gobnyan jipeugot meunasah di tengoh gam-\npong nyang that rayek. Tiep uroe tuhan jijak u pasi jimeuen ngon anoe."])
    rows = screen.sentences_from_pages(p, layout="prose")
    assert rows[0]["ace_raw"].startswith("Gobnyan jipeugot meunasah di tengoh gampong nyang that rayek")
    assert len(rows) == 2

def test_verse_layout_is_one_row_per_line():
    verse = "\n".join(["Teuma boh nyang toh nikmat", "Po gata takheun bandua", "Bak kamoe ateueh jeumala", "Hana meuteumè ngon ureueng"])
    rows = screen.sentences_from_pages(pages([verse]))
    assert [r["layout"] for r in rows] == ["verse"] * 4 and len(rows) == 4

def test_screen_labels():
    assert screen.screen("12")[0] == "REMOVE"
    assert screen.screen("lihat https://example.com untuk info lebih lanjut")[0] == "REMOVE"
    assert screen.screen("bismillahirrahmanirrahim الحمد لله رب العالمين hai")[0] == "REVIEW"
    assert screen.screen("Gobnyan")[0] == "FRAGMENT"
    assert screen.screen("Saya pergi ke pasar untuk membeli sayur dan buah untuk keluarga")[0] == "NON_ACEH"
    assert screen.screen("Tiep uroe tuhan jijak u pasi jimeuen ngon anoe")[0] == "KEEP"
    assert screen.screen("Tiep uroe tuhan jijak u pa5si jimeuen ngon anoe")[0] == "OCR_ERROR"

def test_ocr_low_conf_goes_to_review():
    label, why, *_ = screen.screen("Tiep uroe tuhan jijak u pasi jimeuen ngon anoe", ocr_conf=0.5)
    assert label == "REVIEW"

# ---- dedupe ------------------------------------------------------------------
def make_ref(tmp_path, lines):
    p = tmp_path / "ref.jsonl"
    write_jsonl(p, [{"src_file": "f.txt", "line": i, "ace_raw": l, "key": key_hash(l)} for i, l in enumerate(lines, 1)])
    return dedupe.build_ref(str(p), cache=tmp_path / "c.pkl")

def test_dedupe_exact_variant_near_self(tmp_path):
    ref = make_ref(tmp_path, ["Nyang jipeugot meunasah di tengoh gampong that rayek sigom", "Tiep uroe tuhan jijak u pasi jimeuen ngon anoe"])
    rows = [{"id": str(i), "ace_raw": t} for i, t in enumerate([
        "Njang djipeugot meunasah di tengoh gampong that rayek sigom!",     # exact after folding
        "Tiep uroe tuhan jijak u pasi jimeuen ngon anoe lom",               # near duplicate
        "Hana meuteumè ngon ureueng nyang jak u keunoe",                    # unique
        "hana meuteume ngon ureueng nyang jak u keunoe"])]                  # self duplicate
    out = dedupe.run(rows, ref=ref)
    assert [r["dedup"] for r in out] == ["DUPLICATE_ACEHX", "NEAR_DUP_REVIEW", "unique", "DUPLICATE_SELF"]

def test_dedupe_without_reference_is_flagged_not_silent(tmp_path):
    out = dedupe.run([{"id": "1", "ace_raw": "Tiep uroe tuhan jijak u pasi"}], ref_path=tmp_path / "missing.jsonl")
    assert out[0]["dedup"] == "unique" and out[0]["dedup_checked_vs_acehx"] is False

# ---- translate (no network: fake LLM) ----------------------------------------
def test_llm_batch_parsing_and_status(monkeypatch):
    tr = translate.Translator("claude", k_fewshot=0)
    monkeypatch.setattr(tr, "_llm", lambda user: "```json\n" + json.dumps([{"i": 0, "ind": "satu", "confidence": "high"}, {"i": 1, "ind": "dua", "confidence": "low"}]) + "\n```")
    rows = [{"id": "a", "ace_normalized": "x y z", "screening": "KEEP", "dedup": "unique"},
            {"id": "b", "ace_normalized": "x y z w", "screening": "KEEP", "dedup": "unique"},
            {"id": "c", "ace_normalized": "x y z", "screening": "REMOVE", "dedup": "unique"},
            {"id": "d", "ace_normalized": "x y z", "screening": "KEEP", "dedup": "NEAR_DUP_REVIEW"}]
    done = translate.run(rows, tr)
    assert set(done) == {"a", "b"} and done["a"]["translation_status"] == "machine_draft" and done["b"]["mt_confidence"] == "low"

@pytest.mark.skipif(not (ROOT / "data/raw/external/nusax/train.csv").exists(), reason="NusaX not downloaded")
def test_fewshot_uses_train_only():
    train = {a for a, _ in translate._pairs()}
    import csv
    test = {r["acehnese"] for r in csv.DictReader(open(ROOT / "data/raw/external/nusax/test.csv", encoding="utf-8"))}
    shots = translate.fewshot("Kueh nyang dihidang peuingat lon masa dilee", 5)
    assert shots and all(a in train and a not in test for a, _ in shots)

# ---- export / review ---------------------------------------------------------
def tr_row(i, sid, status="human_validated", ind="Ini terjemahan yang cukup panjang"):
    return {"id": f"R{i}", "source_id": sid, "title": sid, "license": "x", "page": 1, "ace_raw": "a b c d e", "ace_normalized": "a b c d e",
            "ind_raw": ind, "translation_status": status, "screening": "KEEP", "dedup": "unique", "norm_rules": []}

def test_export_gates_and_source_split(tmp_path, monkeypatch):
    monkeypatch.setattr(export, "ROOT", tmp_path)
    rows = [tr_row(i, f"S{i % 5}") for i in range(50)]
    rows += [tr_row(100, "S1", "machine_draft"), tr_row(101, "S1", ind=""), tr_row(102, "S1", ind="a b c d e"), tr_row(103, "S1", ind="x" + " y" * 40)]
    st = export.export(rows, outdir="out")
    assert st["atlas_records"] == 51 and st["trainable"] == 50      # draft in master but not in training
    assert st["rejected"] == {"no_translation": 1, "identical_to_source": 1, "bad_length_ratio": 1}
    splits = {n: json.load(open(tmp_path / "out" / f"{n}.json")) for n in ("train", "validation", "test")}
    assert sum(map(len, splits.values())) == 50
    atlas = json.load(open(tmp_path / "out/atlas_master.json"))["data"][0]
    assert set(atlas) == {"id", "source", "language", "text", "processing", "quality"} and set(atlas["text"]) == {"ace_raw", "ace_normalized", "ind_raw", "ind_normalized"}

def test_split_never_splits_a_source():
    rows = [tr_row(i, f"S{i % 6}") for i in range(60)]
    sp = export.split_by_source(rows)
    owner = {}
    for name, rs in sp.items():
        for r in rs: owner.setdefault(r["source_id"], set()).add(name)
    assert all(len(v) == 1 for v in owner.values())

def test_review_roundtrip(tmp_path):
    rows = [{"id": "1", "source_id": "S", "page": 1, "ace_raw": "Njang djipeugot", "ace_normalized": "Nyang jipeugot", "screening": "REVIEW", "screen_reason": "mixed_language", "dedup": "unique"},
            {"id": "2", "source_id": "S", "page": 1, "ace_raw": "ok", "ace_normalized": "ok", "screening": "KEEP", "dedup": "unique"}]
    p = tmp_path / "s.csv"
    assert review.export_sheet(rows, p) == 1
    import csv
    sheet = list(csv.DictReader(open(p, encoding="utf-8-sig")))
    sheet[0].update(decision="edit", ace_fixed="Njang djipeugot meunasah", ind_fixed="Yang membangun meunasah")
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, sheet[0].keys()); w.writeheader(); w.writerows(sheet)
    out = review.import_sheet(rows, p)
    assert out[0]["screening"] == "KEEP" and out[0]["ace_normalized"] == "Nyang jipeugot meunasah" and out[0]["translation_status"] == "reviewed"
