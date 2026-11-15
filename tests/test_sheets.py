import csv, json
from acehid import sheets
from acehid.common import write_jsonl
from conftest import ACE

def _project(tmp_path, monkeypatch):
    monkeypatch.setattr(sheets, "ROOT", tmp_path)
    (tmp_path / "data/final/combined").mkdir(parents=True)
    json.dump([{"ace": ACE[0], "ind": "Orang itu pergi."}], open(tmp_path / "data/final/combined/train.json", "w"))
    rows = [{"src_file": "corpus_x_file_1.txt", "line": i, "ace_raw": t} for i, t in enumerate(ACE + [ACE[1] + " tambahan kata", "pendek"] * 1, 1)]
    write_jsonl(tmp_path / "data/extracted/acehx.jsonl", rows)

def test_sentence_sheet_excludes_existing_sentences_and_bad_lengths(tmp_path, monkeypatch):
    _project(tmp_path, monkeypatch)
    n = sheets.make_sentence_sheet(out=tmp_path / "sheets", n=50)
    got = list(csv.DictReader(open(tmp_path / "sheets/sentences.csv", encoding="utf-8-sig")))
    texts = [r["acehnese"] for r in got]
    assert n == len(got) and ACE[0] not in texts                       # already in our training data: never re-sheeted
    assert all(4 <= len(t.split()) <= 25 for t in texts)               # 'pendek' is too short
    assert set(got[0]) == set(sheets.SENT_COLS) and all(r["indonesian"] == "" for r in got)

def test_word_sheet_has_frequent_acehnese_words_and_guide(tmp_path, monkeypatch):
    _project(tmp_path, monkeypatch)
    n = sheets.make_word_sheet(out=tmp_path / "sheets", n=10)
    got = list(csv.DictReader(open(tmp_path / "sheets/words.csv", encoding="utf-8-sig")))
    assert n == len(got) and set(got[0]) == set(sheets.WORD_COLS)
    assert all(r["indonesian_meaning"] == "" for r in got)
    assert "Do NOT use Google Translate" in (tmp_path / "sheets/TRANSLATOR_GUIDE.txt").read_text(encoding="utf-8")

def test_import_accepts_only_translator_plus_different_checker(tmp_path, monkeypatch):
    _project(tmp_path, monkeypatch)
    f = tmp_path / "filled.csv"
    with open(f, "w", encoding="utf-8-sig", newline="") as h:
        w = csv.DictWriter(h, sheets.SENT_COLS); w.writeheader()
        w.writerow({"id": "S1", "acehnese": ACE[2], "indonesian": "Ibu bilang tidak.", "translator": "Andrie", "checker": "Muttu", "notes": ""})
        w.writerow({"id": "S2", "acehnese": ACE[3], "indonesian": "Ayah pergi.", "translator": "Muttu", "checker": "muttu", "notes": ""})   # same person
        w.writerow({"id": "S3", "acehnese": ACE[4], "indonesian": "", "translator": "Andrie", "checker": "Muttu", "notes": ""})            # not translated
        w.writerow({"id": "S4", "acehnese": ACE[5], "indonesian": "?", "translator": "Andrie", "checker": "Muttu", "notes": "unsure"})   # unsure
        w.writerow({"id": "S5", "acehnese": ACE[0], "indonesian": "Orang itu.", "translator": "Andrie", "checker": "", "notes": ""})      # no checker
    st = sheets.import_sheets(sentences=f, outdir=tmp_path / "human")
    assert st["sentences_in"] == 5 and st["sentences_accepted"] == 1
    pairs = json.load(open(tmp_path / "human/pairs.json", encoding="utf-8"))
    assert [p["id"] for p in pairs] == ["S1"] and pairs[0]["ind"] == "Ibu bilang tidak."
    assert "human" in pairs[0]["source"]


def _many(tmp_path, monkeypatch, n=60):
    monkeypatch.setattr(sheets, "ROOT", tmp_path)
    (tmp_path / "data/final/combined").mkdir(parents=True)
    json.dump([], open(tmp_path / "data/final/combined/train.json", "w"))
    rows = [{"src_file": "c.txt", "line": i, "ace_raw": f"gobnyan geujak u pasi rumoh {chr(97 + i % 26)}{i} ureueng nyan ka troh"} for i in range(n)]
    write_jsonl(tmp_path / "data/extracted/acehx.jsonl", rows)
    monkeypatch.setattr(sheets.langid, "classify", lambda t: ("ace", 1.0))


def test_packs_give_each_person_distinct_sentences_and_a_different_checker(tmp_path, monkeypatch):
    _many(tmp_path, monkeypatch)
    r = sheets.make_packs(["Ana", "Budi", "Cut"], per_person=20, out=tmp_path / "packs")
    assert r["sentences"] == 60
    files = sorted((tmp_path / "packs").glob("0*.csv")); assert len(files) == 3
    all_ids, all_text = [], []
    for f, who in zip(files, ["Ana", "Budi", "Cut"]):
        rows = list(csv.DictReader(open(f, encoding="utf-8-sig")))
        assert len(rows) == 20 and all(x["translator"] == who and x["checker"] == "" and x["indonesian"] == "" for x in rows)
        all_ids += [x["id"] for x in rows]; all_text += [x["acehnese"] for x in rows]
    assert len(set(all_ids)) == 60 and len(set(all_text)) == 60                    # no sentence in two packs
    md = (tmp_path / "packs/PACKS.md").read_text(encoding="utf-8")
    assert "| Ana | 01_ana.csv | Cut |" in md and "| Budi | 02_budi.csv | Ana |" in md       # nobody checks their own pack


def test_packs_refuse_bad_sizes_and_one_person(tmp_path, monkeypatch):
    _many(tmp_path, monkeypatch)
    import pytest
    with pytest.raises(ValueError): sheets.make_packs(["Ana"], 20, out=tmp_path / "p")
    with pytest.raises(ValueError): sheets.make_packs(["Ana", "Budi"], 19, out=tmp_path / "p")
    with pytest.raises(ValueError): sheets.make_packs(["Ana", "Budi"], 31, out=tmp_path / "p")
    with pytest.raises(ValueError, match="needed"): sheets.make_packs(["A", "B", "C", "D"], 30, out=tmp_path / "p")


def test_import_builds_parallel_and_golden_corpus_from_several_packs(tmp_path, monkeypatch):
    _project(tmp_path, monkeypatch)
    def sheet(name, rows):
        f = tmp_path / name
        with open(f, "w", encoding="utf-8-sig", newline="") as h:
            w = csv.DictWriter(h, sheets.SENT_COLS); w.writeheader(); [w.writerow(r) for r in rows]
        return f
    a = sheet("a.csv", [{"id": "P01-001", "acehnese": ACE[2], "indonesian": "Ibu bilang tidak.", "translator": "Ana", "checker": "Budi", "verdict": "ok"},
                        {"id": "P01-002", "acehnese": ACE[3], "indonesian": "Ayah pergi.", "translator": "Ana", "checker": "Budi", "verdict": "fixed", "notes": "ubah kata"}])
    b = sheet("b.csv", [{"id": "P02-001", "acehnese": ACE[4], "indonesian": "Kami makan.", "translator": "Budi", "checker": "Ana", "verdict": "OK"},
                        {"id": "P02-002", "acehnese": ACE[5], "indonesian": "Dia datang.", "translator": "Budi", "checker": "Budi", "verdict": "ok"}])   # self-check: rejected
    st = sheets.import_sheets(sentences=[a, b], outdir=tmp_path / "human")
    assert st["sentences_in"] == 4 and st["sentences_accepted"] == 3 and st["golden"] == 2
    par = json.load(open(tmp_path / "human/pairs.json", encoding="utf-8")); gold = json.load(open(tmp_path / "human/golden.json", encoding="utf-8"))
    assert [r["id"] for r in par] == ["P01-001", "P01-002", "P02-001"] and [r["id"] for r in gold] == ["P01-001", "P02-001"]


def test_packs_build_the_corpus_index_by_themselves_on_a_fresh_clone(tmp_path, monkeypatch):
    from acehid import audit
    monkeypatch.setattr(sheets, "ROOT", tmp_path); monkeypatch.setattr(audit, "ROOT", tmp_path)
    (tmp_path / "data/raw/acehx").mkdir(parents=True); (tmp_path / "data/final/combined").mkdir(parents=True)
    json.dump([], open(tmp_path / "data/final/combined/train.json", "w"))
    (tmp_path / "data/raw/acehx/c.txt").write_text("\n".join(f"gobnyan geujak u pasi rumoh {chr(97 + i % 26)}{i} ureueng nyan" for i in range(50)), encoding="utf-8")
    assert not (tmp_path / "data/extracted/acehx.jsonl").exists()
    monkeypatch.setattr(sheets.langid, "classify", lambda t: ("ace", 1.0))
    r = sheets.make_packs(["Ana", "Budi"], per_person=20, out=tmp_path / "packs")
    assert r["sentences"] == 40 and (tmp_path / "data/extracted/acehx.jsonl").exists()
