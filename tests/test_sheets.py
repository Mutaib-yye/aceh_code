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
