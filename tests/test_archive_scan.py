import json, zipfile, pytest, pymupdf
from acehid import archive_scan
from acehid.common import ROOT

def _pdf(path, pages):
    doc = pymupdf.open()
    for lines in pages:
        pg = doc.new_page(); y = 60
        for t in lines:
            pg.insert_text((40, y), t, fontsize=10); y += 14
    doc.save(str(path)); return path

def _scan_pdf(path):
    ipg_doc = pymupdf.open(); ipg = ipg_doc.new_page(); ipg.insert_text((40, 60), "scanned page text", fontsize=12)
    pix = ipg.get_pixmap(dpi=120)
    doc = pymupdf.open(); p1 = doc.new_page(); p1.insert_text((40, 60), "Halaman ini punya lapisan teks yang cukup panjang.", fontsize=10)
    p2 = doc.new_page(); p2.insert_image(p2.rect, pixmap=pix)
    doc.save(str(path)); return path

@pytest.fixture
def archive(tmp_path):
    nx = json.load(open(ROOT / "data/final/nusax/test.json", encoding="utf-8"))
    ace = [r["ace"] for r in nx if len(r["ace"].split()) >= 5][:24]
    ind = [r["ind"] for r in nx if len(r["ind"].split()) >= 5][:24]
    d = tmp_path / "src"; d.mkdir()
    _pdf(d / "Kamus Aceh Indonesia.pdf", [ace[:8], ace[8:16], ace[16:24]])
    bil_pages = [[t for a, i in zip(ace[k:k + 4], ind[k:k + 4]) for t in (a, i)] for k in (0, 4, 8, 12, 16, 20)]
    _pdf(d / "syair_bilingual.pdf", bil_pages)
    _pdf(d / "lirik_indonesia.pdf", [ind[:8], ind[8:16]])
    _scan_pdf(d / "scan.pdf")
    z = tmp_path / "Data Syair dan Lagu.zip"
    with zipfile.ZipFile(z, "w") as f:
        for p in d.iterdir(): f.write(p, p.name)
        f.writestr("notes.docx", "x")
    return z

def test_scan_inventory_flags_language_bilingual_and_ocr(archive, tmp_path):
    rows = archive_scan.scan(archive, workdir=tmp_path / "work", out_dir=tmp_path / "rep", log_fn=lambda *_: None)
    by = {r["file"]: r for r in rows}
    assert set(by) == {"Kamus Aceh Indonesia.pdf", "syair_bilingual.pdf", "lirik_indonesia.pdf", "scan.pdf"}
    assert by["Kamus Aceh Indonesia.pdf"]["type_guess"] == "dictionary" and by["syair_bilingual.pdf"]["type_guess"] == "syair"
    assert by["Kamus Aceh Indonesia.pdf"]["ace_share"] > 0.6 and by["lirik_indonesia.pdf"]["ind_share"] > 0.6
    assert by["syair_bilingual.pdf"]["possibly_bilingual"] is True and by["Kamus Aceh Indonesia.pdf"]["possibly_bilingual"] is False
    assert by["scan.pdf"]["scan_pages"] == 1 and by["scan.pdf"]["pages"] == 2
    md = (tmp_path / "rep/archive_data_syair_dan_lagu.md").read_text(encoding="utf-8")
    assert "Needs OCR (1 files)" in md and "Possibly bilingual (1 files)" in md and "docx" in md
    assert "scanned page text" not in md and "Halaman ini" not in md and "Kamus Aceh Indonesia.pdf" in md   # file names yes, page text never
    assert (tmp_path / "rep/archive_data_syair_dan_lagu.csv").exists()

def test_missing_extractor_gives_clear_message(tmp_path, monkeypatch):
    import shutil
    rar = tmp_path / "x.rar"; rar.write_bytes(b"Rar!\x1a\x07\x00")
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(SystemExit, match="brew install unar"):
        archive_scan.extract(rar, tmp_path / "w")
