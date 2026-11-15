"""The student sheet-maker page: the block rule (shared with the page's JavaScript) and the generated file."""
from acehid import sheetmaker


def test_fnv1a_matches_the_known_32_bit_values():
    assert sheetmaker.fnv1a("") == 0x811C9DC5 and sheetmaker.fnv1a("a") == 0xE40C292C and sheetmaker.fnv1a("abc") == 0x1A47E90B


def test_the_student_number_picks_a_block_and_spaces_do_not_matter():
    n = 25 * 100
    b = sheetmaker.block_of("250820701100010", n)
    assert 0 <= b < 100 and b == sheetmaker.block_of(" 2508 2070 1100010 ", n)
    assert len({sheetmaker.block_of(str(250820701100000 + i), n) for i in range(60)}) > 40        # different students mostly differ


def test_build_embeds_the_pool_and_leaves_no_placeholder(tmp_path, monkeypatch):
    rows = [("AcehX_Corpus.txt", i, f"kalimat aceh nomor {i} nyoe") for i in range(1, 80)]
    monkeypatch.setattr(sheetmaker, "pool", lambda: rows)
    r = sheetmaker.build(tmp_path / "m.html")
    html = (tmp_path / "m.html").read_text(encoding="utf-8")
    assert r["sentences"] == 79 and r["blocks"] == 3 and "/*POOL*/[]" not in html and "/*FILES*/[]" not in html
    assert '"AcehX_Corpus.txt"' in html and "kalimat aceh nomor 7 nyoe" in html and "<NAMA PEMERIKSA>" in html
