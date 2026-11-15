"""The Balai Bahasa dictionaries: entry parsing, example-sentence candidates, picture-dictionary triples, and the unified word lookup."""
import json
from acehid import books
from acehid.dictionary import Dictionary

TXT = """##### PAGE 1
abaih
alu
A
abaih
/a.bayh/
v
mengarahkan
(umpama perahu): kamo meu— jalô u
kuala ‘kami mengarahkan perahu ke
kuala’
abè  /a.bɛ/ n  partikel padat yg
berukuran sangat kecil
##### PAGE 2
bôt /bot/ n perahu: — Kuala luah that ‘Perahu di Kuala besar sekali’
bîk /bik/ n sesuatu: musém barat laôt meu— that ‘musim barat sangat – ’
"""

def test_entries_are_headword_plus_pronunciation_and_guide_words_are_ignored():
    es = books.parse_entries(TXT, "maritim")
    assert [e["word"] for e in es] == ["abaih", "abè", "bôt", "bîk"]                      # 'abaih'/'alu'/'A' guide lines are not entries
    assert es[0]["ipa"] == "a.bayh" and es[0]["page"] == "1" and "mengarahkan" in es[0]["text"] and es[2]["page"] == "2"


def test_example_candidates_fill_the_headword_dash_and_flag_what_needs_a_human():
    rows = {r["headword"]: r for r in books.example_candidates(books.parse_entries(TXT, "maritim"))}
    assert rows["abaih"]["ace"] == "kamo meuabaih jalô u kuala" and rows["abaih"]["ind"] == "kami mengarahkan perahu ke kuala" and rows["abaih"]["status"] == "filled"
    assert rows["bôt"]["ace"].startswith("bôt Kuala") and rows["bôt"]["status"] == "filled"
    assert rows["bîk"]["status"] == "needs_human"                                         # a dash in the Indonesian side cannot be filled
    assert all(r["book"] == "maritim" for r in rows.values())


def test_picture_dictionary_triples_titles_latin_names_and_prose_skipped():
    txt = """##### PAGE pdf3
Ini kalimat pengantar yang panjang dan berakhir dengan titik.
##### PAGE 3
inöng jaroe
ibu jari
thumb
jaroe - jari - finger
limo
jeruk
orange
〔Citrus sp.〕
Kamus Bergambar Aceh-Indonesia-Inggris | 3
"""
    t = books.parse_triples(txt)
    assert [(x["word"], x["ind"], x["eng"]) for x in t] == [("inöng jaroe", "ibu jari", "thumb"), ("jaroe", "jari", "finger"), ("limo", "jeruk", "orange")]
    assert t[2]["latin"] == "Citrus sp." and t[1]["title"] is True


def test_dictionary_loads_the_books_next_to_the_1985_list(tmp_path):
    csv_path = tmp_path / "k.csv"
    csv_path.write_text('input,target,error_category,error_type,severity,source,wer,translate_ind,sentiment\n'
                        'abaih,abaih,none,none,none,"Kamus (1985), hlm. 1; belum validasi",0,nama laki-laki,neutral\n', encoding="utf-8")
    entries = books.parse_entries(TXT, "maritim") + books.parse_triples("##### PAGE 5\nlimo\njeruk\norange\n")
    (tmp_path / "entries.json").write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    d = Dictionary(csv_path, books=tmp_path / "entries.json")
    assert d.sources == {"Kamus Aceh–Indonesia (1985)": 1, "Kamus Kemaritiman Aceh–Indonesia (2021)": 4, "Kamus Bergambar Aceh–Indonesia–Inggris (2023)": 1}
    hits = d.lookup("ABAIH"); assert {e["source"] for e in hits} == {"Kamus Aceh–Indonesia (1985)", "Kamus Kemaritiman Aceh–Indonesia (2021)"}
    assert [e["meaning"] for e in d.lookup("limo")] == ["jeruk (en: orange)"] and d.lookup("limo")[0]["page"] == 5
    assert any(e["ipa"] == "a.bayh" for e in hits if "ipa" in e)
    assert Dictionary(csv_path).sources == {"Kamus Aceh–Indonesia (1985)": 1}                 # the default books file is used only with the default path


def test_dictionary_without_books_still_works(tmp_path):
    d = Dictionary(tmp_path / "none.csv", books=tmp_path / "none.json")
    assert not d.loaded and d.sources == {}
