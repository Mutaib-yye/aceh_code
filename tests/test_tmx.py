import json
from acehid import tmx

def _tu(a, i): return f'<tu><tuv xml:lang="ace"><seg>{a}</seg></tuv><tuv xml:lang="id"><seg>{i}</seg></tuv></tu>'

def test_import_filters_bad_alignments_and_citations(tmp_path):
    good_a = "Teuma boh nyang toh nikmat Po gata takheun bandua teuh sulet leupah"
    good_i = "Maka buah yang ada nikmat Tuhan kamu katakan bandua kami sulet leupah[1]"
    f = tmp_path / "x.tmx"
    f.write_text("<tmx><body>" + _tu(good_a, good_i) + _tu("Peundidékan", "Peundidikan") + _tu(good_a, "pendek sekali ini") + _tu(good_a, good_i) + "</body></tmx>", encoding="utf-8")
    r = tmx.run(f, tmp_path / "o.json")
    rows = json.load(open(tmp_path / "o.json", encoding="utf-8"))
    assert r["read"] == 4 and r["kept"] == len(rows) <= 1
    assert all("[1]" not in x["ind"] for x in rows)
