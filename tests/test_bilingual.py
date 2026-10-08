import json, importlib.util, pytest
from acehid import bilingual, corpus
from acehid.common import ROOT

ACE = ["Dum syeedara agam inong, baroh tunong tuha muda", "Hikayat bek takheun mantong, tapeukeunong jroh suara",
       "Demi Allah meunyo meunan, page Tuhan neubri neuraka", "Khaba ajab le meufeu-at, kisah sahabat saidina Umar",
       "Dua nanggroe jih seulamat, leubeh pangkat ngon bahagia", "Dalam donya leubeh izzat, beureukat khaba areuta",
       "Lom leubeh nanggroe akhirat, geubri teumpat lam syeureuga", "Teuma troih le Abu Sammah, budak indah paraih rupa"]
IND = ["Semua saudara laki wanita, utara selatan tua muda", "Hikayat jangan dibaca saja, diperkena indah suara",
       "Demi Allah kalau demikian, kelak Tuhan memberi neraka", "Kabar ajab banyak manfaat, kisah sahabat Saidina Umar",
       "Dua negeri ia selamat, lebih pangkat dengan bahagia", "Di dalam dunia lebih izzat, berkat khabar harta",
       "Lagi lebih negeri akhirat, diberi tempat dalam surga", "Kemudian sampailah Abu Sammah, budak indah paras rupa"]
L = lambda xs: [{"text": t} for t in xs]

def test_section_lines_filters_and_rejoins():
    page = {"page": 3, "lines": [{"text": "BAB II", "conf": .99}, {"text": "ALIH AKSARA", "conf": .99}, {"text": ACE[0], "conf": .99},
                                 {"text": "Na e d e lana", "conf": .97}, {"text": "Hikayat bek takheun mantong, tapeukeunong", "conf": .98},
                                 {"text": "jroh suara", "conf": .99}, {"text": "Kana S s a m nnan", "conf": .55},
                                 {"text": '") Pedang', "conf": .99}, {"text": "12", "conf": .99}]}
    out = bilingual.section_lines([page])
    assert [x["text"] for x in out] == [ACE[0], ACE[1]]
    assert bilingual.section_lines.last_stats == {"heading": 2, "page_no": 1, "footnote": 1, "low_conf": 1, "garbage": 1, "rejoined": 1}

def test_ocr_repair_uses_reference_spelling_only():
    vocab = bilingual.word_counts(["ateueh rumoh ateueh", "semua orang hukum"] * 5 + ["bak hak hak hak hak hak"])
    fixed, n = bilingual.repair("Scmua ateuch bukum bak", vocab)
    assert fixed == "Semua ateueh hukum bak" and n == 3        # 'bak' is a real (short) word: never 'corrected' to 'hak'
    assert bilingual.repair("Gobnyan", vocab) == ("Gobnyan", 0)  # unknown word without a common variant stays

def test_align_handles_inserted_and_missing_lines():
    ace = ACE[:3] + ACE[4:]                                       # Acehnese line 3 missing (e.g. OCR lost it)
    ind = IND[:6] + ["Sebagaimana disuruh semua ikut, kalau tidak dibunuh didera"] + IND[6:]   # translator added a line
    steps = bilingual.align(L(ace), L(ind), band=10)
    pairs = {ace[a[0]]: ind[b[0]] for a, b, _ in steps}
    for a, i in zip(ACE, IND):
        if a in pairs:
            assert pairs[a] == i, (a, pairs[a])
    assert len(pairs) == 7 and all(len(a) == len(b) == 1 for a, b, _ in steps)

def test_similarity_separates_translations_from_neighbours():
    true = [bilingual.similarity(a, i) for a, i in zip(ACE, IND)]
    false = [bilingual.similarity(a, IND[(k + 3) % len(IND)]) for k, a in enumerate(ACE)]
    assert sum(true) / len(true) > 3 * sum(false) / len(false)

def test_block_split_keeps_pages_together():
    rows = [{"page": p, "id": str(p)} for p in range(10, 20)]
    s = bilingual.block_split(rows, "17-18", "15-15")
    assert [r["page"] for r in s["test"]] == [17, 18] and [r["page"] for r in s["validation"]] == [15] and len(s["train"]) == 7

OCR = importlib.util.find_spec("rapidocr") or importlib.util.find_spec("rapidocr_onnxruntime")

@pytest.mark.skipif(not OCR, reason="no OCR package installed")
def test_build_pairs_end_to_end_on_a_generated_book(tmp_path):
    import pymupdf
    doc = pymupdf.open()
    for heading, lines in (("ALIH AKSARA", ACE[:4]), (None, ACE[4:]), ("ALIH BAHASA", IND[:4]), (None, IND[4:])):
        pg = doc.new_page(width=420, height=600); y = 60
        if heading:
            pg.insert_text((150, y), heading, fontsize=11); y += 30
        for t in lines:
            pg.insert_text((40, y), t, fontsize=10); y += 16
        pg.insert_text((200, 570), str(doc.page_count), fontsize=9)
    pdf = tmp_path / "book.pdf"; doc.save(str(pdf))
    rows, stats = bilingual.build_pairs(str(pdf), "1-2", "3-4", ocr_cache=tmp_path / "ocr.jsonl", ind_vocab_texts=IND)
    assert stats["pairs"] == 8 and stats["ace_dropped"]["heading"] == 1 and stats["ind_dropped"]["page_no"] == 2
    by = {r["ace_raw"]: r["ind_raw"] for r in rows}
    ok = sum(by.get(a) == i for a, i in zip(ACE, IND))
    assert ok >= 7, by                                           # OCR may misread a letter; alignment must be right
    assert all(r["translation_status"] == "human_translated" and r["page"] in (1, 2) for r in rows)
    assert (tmp_path / "ocr.jsonl").exists()                     # cached: a second run does not OCR again
    rows2, _ = bilingual.build_pairs(str(pdf), "1-2", "3-4", ocr_cache=tmp_path / "ocr.jsonl", ind_vocab_texts=IND)
    assert [r["ace_raw"] for r in rows2] == [r["ace_raw"] for r in rows]

def test_corpus_includes_hikayat_books_and_optional_quran(tmp_path, monkeypatch):
    nx = json.load(open(ROOT / "data/final/nusax/train.json", encoding="utf-8"))
    d = tmp_path / "data/final/nusax"; d.mkdir(parents=True)
    for k, v in {"train": nx[:20], "validation": nx[20:24], "test": nx[24:28]}.items():
        json.dump(v, open(d / f"{k}.json", "w"))
    h = tmp_path / "data/final/hikayat/book1"; h.mkdir(parents=True)
    pairs = [{"ace": a, "ind": i} for a, i in zip(ACE, IND)]
    json.dump(pairs[:5], open(h / "train.json", "w")); json.dump(pairs[5:6], open(h / "validation.json", "w")); json.dump(pairs[6:], open(h / "test.json", "w"))
    q = tmp_path / "data/raw/external/quran"; q.mkdir(parents=True)
    json.dump({"quran": [{"chapter": 1, "verse": 1, "text": "Ngon nama Allah nyang Maha Murah"}, {"chapter": 1, "verse": 2, "text": "x"}]}, open(q / "ace-tgkhmahjiddinju.json", "w"))
    json.dump({"quran": [{"chapter": 1, "verse": 1, "text": "Dengan nama Allah Yang Maha Pengasih"}, {"chapter": 1, "verse": 2, "text": "y"}]}, open(q / "ind-indonesianislam.json", "w"))
    monkeypatch.setattr(corpus, "ROOT", tmp_path)
    m = corpus.build()
    assert m["train"]["by_source"] == {"hikayat": 5, "nusax": 20} and m["tests"]["hikayat"]["n"] == 2 and m["validation"]["by_source"]["hikayat"] == 1
    m = corpus.build(quran=True)
    assert m["train"]["by_source"]["quran"] == 1 and "Mahjiddin" in m["license"]      # the 1-word verse pair is filtered out

def test_committed_hikayat_split_is_leak_free():
    d = ROOT / "data/final/hikayat/abu_sammah"
    if not d.exists():
        pytest.skip("hikayat not built")
    tr, va, te = (json.load(open(d / f"{k}.json", encoding="utf-8")) for k in ("train", "validation", "test"))
    assert len(tr) > 1000 and len(te) > 100 and len(va) > 50
    from acehid.train import assert_no_leak
    assert_no_leak([(r["ace"], r["ind"]) for r in tr], [(r["ace"], r["ind"]) for r in va + te])

class _FakeApi:
    calls, refuse_space = [], False
    def __init__(self, token): self.calls.append(("init", token))
    def whoami(self): return {"name": "muttu"}
    def create_repo(self, repo_id, **kw):
        if kw.get("repo_type") == "space" and self.refuse_space:
            e = RuntimeError("Client error '402 Payment Required' for url 'https://huggingface.co/api/repos/create'")
            e.server_message = "Payment required"; raise e
        self.calls.append(("create", repo_id, kw.get("repo_type"), kw.get("private")))
    def update_repo_settings(self, repo_id, **kw): self.calls.append(("settings", repo_id, kw.get("private")))
    def upload_folder(self, repo_id, folder_path, **kw): self.calls.append(("upload", repo_id, folder_path))
    def add_space_variable(self, repo_id, key, value): self.calls.append(("var", repo_id, key, value))
    def add_space_secret(self, repo_id, key, value): self.calls.append(("secret", repo_id, key, value))

def _cell(nb, marker):
    return next("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code" and marker in "".join(c["source"]))

def _run_save_cell(tmp_path, monkeypatch, trained, token="hf_test", download_zip=False):
    import huggingface_hub, os
    nb = json.load(open(ROOT / "notebooks/train_colab.ipynb", encoding="utf-8"))
    src = _cell(nb, "save your trained model")
    _FakeApi.calls, _FakeApi.refuse_space = [], False
    monkeypatch.setattr(huggingface_hub, "HfApi", _FakeApi)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "models/ace-id-nllb").mkdir(parents=True)
    for f in ("training_log.json", "RESULTS.md", "README.md"):
        (tmp_path / "models/ace-id-nllb" / f).write_text("x")
    class Saver:
        def half(self): return self
        def save_pretrained(self, d): os.makedirs(d, exist_ok=True); open(os.path.join(d, "config.json"), "w").write("{}")
    ns = {"model": Saver(), "tok": Saver(), "HF_TOKEN": token, "TRAINED": trained, "DOWNLOAD_ZIP": download_zip, "os": os, "REPO": str(tmp_path)}
    exec(src, ns)
    return _FakeApi.calls

def test_notebook_saves_trained_model_privately_and_never_creates_a_space(tmp_path, monkeypatch):
    calls = _run_save_cell(tmp_path, monkeypatch, trained=True)
    assert calls == [("init", "hf_test"), ("create", "muttu/ace-id-nllb", None, True), ("settings", "muttu/ace-id-nllb", True),
                     ("upload", "muttu/ace-id-nllb", "models/ace-id-nllb-fp16")]
    assert not (tmp_path / "ace-id-nllb.zip").exists()

def test_notebook_without_token_makes_a_zip_the_mac_launcher_can_use(tmp_path, monkeypatch):
    import zipfile
    calls = _run_save_cell(tmp_path, monkeypatch, trained=True, token="")
    assert calls == [] and zipfile.ZipFile(tmp_path / "ace-id-nllb.zip").namelist()   # zip of the model folder
    assert "config.json" in zipfile.ZipFile(tmp_path / "ace-id-nllb.zip").namelist()

def test_notebook_without_training_saves_nothing(tmp_path, monkeypatch, capsys):
    assert _run_save_cell(tmp_path, monkeypatch, trained=False) == [] and "no model to save" in capsys.readouterr().out

def test_both_notebooks_end_by_starting_the_app_with_a_public_link():
    for name in ("train_colab.ipynb", "demo_colab.ipynb"):
        nb = json.load(open(ROOT / "notebooks" / name, encoding="utf-8"))
        last = "".join(nb["cells"][-1]["source"])
        assert "app.start(" in last and "share=True" in last, name
