from acehid import malik_mawot as mm

def test_pair_up_pairs_alternating_lines_and_resyncs_on_a_stray_segment():
    segs = ["Teuma troih le Abu Sammah, budak indah paraih rupa", "Kemudian sampailah Abu Sammah, budak indah paras rupa",
            "catatan lepas tanpa pasangan", "Dalam donya leubeh izzat, beureukat khaba areuta", "Di dalam dunia lebih izzat, berkat khabar harta"]
    p = mm.pair_up(segs)
    assert [x["ind"] for x in p] == [segs[1], segs[4]] and p[0]["ace"].startswith("Teuma troih")
