import json
from acehid import pivot

def test_pivot_keeps_human_acehnese_and_machine_indonesian_with_filters(tmp_path):
    d = tmp_path / "seed"; d.mkdir()
    ace = ["Teuma troih le Abu Sammah, budak indah paraih rupa", "Dalam donya leubeh izzat, beureukat khaba areuta", "pendek"]
    eng = ["Then Abu Sammah arrived, a boy with a beautiful face", "In this world there is more honour, blessing and wealth", "short"]
    (d / "ace_Latn").write_text("\n".join(ace), encoding="utf-8"); (d / "eng_Latn").write_text("\n".join(eng), encoding="utf-8")
    seen = []
    def fake(sents): seen.extend(sents); return ["Kemudian Abu Sammah tiba, anak laki-laki berwajah indah", "Dalam dunia ini lebih banyak kehormatan, berkah dan kekayaan"][:len(sents)]
    r = pivot.run(d, tmp_path / "o.json", translate=fake)
    rows = json.load(open(tmp_path / "o.json", encoding="utf-8"))
    assert r["kept"] == len(rows) == 2 and len(seen) == 2                       # the 1-word line never reaches the translator
    assert rows[0]["ace"].startswith("Teuma troih") and "machine translation" in rows[0]["source"]
