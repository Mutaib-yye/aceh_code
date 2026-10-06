import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import pytest, pymupdf

# Short Acehnese lines (taken from the public AcehX/NusaX style of text) used only as fixtures.
ACE = ["Teuma boh nyang toh nikmat Po gata takheun bandua teuh sulet leupah.",
       "Bak kamoe ateueh jeumala hana meuteumè ngon ureueng nyang jak.",
       "Ayah jih ban mantong abéh umu, ibu jih meunyoe hana na keu aneuek.",
       "Tiep uroe tuhan jijak u pasi jimeuen ngon anoe.",
       "Gobnyan jipeugot meunasah di tengoh gampong nyang that rayek.",
       "Meunyo lagèe nyoe neupeugah, lon hana meuphôm peue nyang neukheun."]

def make_pdf(path, pages, header="HIKAYAT CONTOH", wrap=48):
    doc = pymupdf.open()
    for n, lines in enumerate(pages, 1):
        pg = doc.new_page()
        pg.insert_text((72, 40), header, fontsize=9)
        y = 90
        for ln in lines:
            pg.insert_text((72, y), ln, fontsize=11); y += 16
        pg.insert_text((290, 800), str(n), fontsize=9)
    doc.save(str(path)); return path

@pytest.fixture
def ace(): return ACE
