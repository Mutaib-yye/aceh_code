import pytest
from acehid import kamus

# invented entries: the test never contains text from the real book
SAMPLE = ("##### PAGE 4\nKamus contoh\nzaaba\nzaaba\t/za.ba/ n kata buatan untuk uji\n\nzaabé /za.be/ v kata kedua\n"
          "##### PAGE 5\nzaabu /za.bu/ a kata ketiga\n")

@pytest.fixture
def book(tmp_path):
    p = tmp_path / "book.txt"; p.write_text(SAMPLE, encoding="utf-8"); return p

def test_lookup_ignores_accents_case_and_counts_repeated_headword_once(book):
    hits = kamus.lookup("ZAABA", book)
    assert [p for p, _ in hits] == [4] and "kata buatan untuk uji" in hits[0][1]
    assert kamus.lookup("zaabe", book)[0][1].startswith("zaabé /za.be/")

def test_lookup_needs_the_whole_word_and_reports_pages(book):
    assert kamus.lookup("zaa", book) == [] and kamus.lookup("tidakada", book) == []
    assert kamus.lookup("zaabu", book)[0][0] == 5

def test_entry_stops_at_the_page_end(book):
    assert "zaabu" not in kamus.lookup("zaabé", book)[0][1]

def test_missing_book_says_how_to_build_it(tmp_path):
    with pytest.raises(FileNotFoundError, match="kamus-build"):
        kamus.lookup("ampu", tmp_path / "none.txt")

def test_show_prints_page_or_a_hint(book, capsys):
    kamus.show("zaaba", book); assert "[pdf page 4]" in capsys.readouterr().out
    kamus.show("qqq", book); assert "does not start any line" in capsys.readouterr().out
