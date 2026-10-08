import io, json, tarfile, zipfile, pytest
from acehid import flores, corpus, translate
from acehid.common import ROOT

ACE = ["Ureueng nyan geujak u pasi.", "Gobnyan geubloe boh kayee bak peukan.", "Aneuek miet jimeulakee bu.", "Ayah jijak u blang uroe nyoe.",
       "Lon hana meuphôm peue nyang neukheun.", "Gampong kamoe that ijo."]
IND = ["Orang itu pergi ke pantai.", "Dia membeli buah di pasar.", "Anak kecil meminta nasi.", "Ayah pergi ke sawah hari ini.",
       "Saya tidak mengerti apa yang Anda katakan.", "Kampung kami sangat hijau."]

def _files(layout):
    """FLORES files for 2 splits x 2 languages (+ a distractor language) in the given naming layout."""
    names = {"flores200": "flores200_dataset/{s}/{l}.{s}", "plus_text": "floresp/{s}.{l}", "plus_dir": "x/{s}/{l}"}[layout]
    data = {}
    for s, rng in (("dev", range(0, 3)), ("devtest", range(3, 6))):
        data[names.format(s=s, l="ace_Latn")] = "\n".join(ACE[i] for i in rng) + "\n"
        data[names.format(s=s, l="ind_Latn")] = "\n".join(IND[i] for i in rng) + "\n"
        data[names.format(s=s, l="jav_Latn")] = "ignored\n" * 3
    return data

def _tar(path, files):
    with tarfile.open(path, "w") as t:
        for n, txt in files.items():
            b = txt.encode(); ti = tarfile.TarInfo(n); ti.size = len(b); t.addfile(ti, io.BytesIO(b))
    return path

@pytest.mark.parametrize("layout", ["flores200", "plus_text", "plus_dir"])
@pytest.mark.parametrize("container", ["tar", "zip", "dir"])
def test_flores_reader_all_layouts(tmp_path, layout, container):
    files = _files(layout)
    if container == "tar":
        src = _tar(tmp_path / "f.tar", files)
    elif container == "zip":
        src = tmp_path / "f.zip"
        with zipfile.ZipFile(src, "w") as z:
            for n, txt in files.items(): z.writestr(n, txt)
    else:
        src = tmp_path / "d"
        for n, txt in files.items():
            (src / n).parent.mkdir(parents=True, exist_ok=True); (src / n).write_text(txt, encoding="utf-8")
    found = flores.read_files(src)
    assert set(found) == {("dev", "ace"), ("dev", "ind"), ("devtest", "ace"), ("devtest", "ind")}
    assert found[("devtest", "ind")][0] == IND[3]

def test_flores_run_normalizes_and_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(flores, "ROOT", tmp_path)
    sizes = flores.run(_tar(tmp_path / "f.tar", _files("flores200")))
    assert sizes == {"dev": 3, "devtest": 3}
    dt = json.load(open(tmp_path / "data/final/flores/devtest.json", encoding="utf-8"))
    assert dt[1]["ace"] == "Lon hana meuphôm peue nyang neukheun." and dt[1]["ind"] == IND[4]   # ô is kept, only two-dot vowels are folded

def test_flores_rejects_misaligned_or_one_sided(tmp_path):
    f = _files("flores200"); f["flores200_dataset/dev/ace_Latn.dev"] += "extra line\n"
    with pytest.raises(ValueError, match="not aligned"):
        flores.read_files(_tar(tmp_path / "a.tar", f))
    f = {k: v for k, v in _files("flores200").items() if "dev/ind_Latn" not in k}
    with pytest.raises(ValueError, match="one language side"):
        flores.read_files(_tar(tmp_path / "b.tar", f))
    with pytest.raises(ValueError, match="no ace_Latn"):
        flores.read_files(_tar(tmp_path / "c.tar", {"x/readme.txt": "hi"}))

def test_remove_leaks_exact_near_and_duplicates():
    held = [{"ace": "Gobnyan geubloe boh kayee bak peukan.", "ind": "Dia membeli buah di pasar."}]
    train = [{"ace": "GOBNYAN geubloe boh kayèe bak peukan!", "ind": "something else"},     # exact after folding case/diacritics/punctuation
             {"ace": "Gobnyan geublo boh kayee bak peukan", "ind": "another"},              # near (one letter)
             {"ace": "Ureueng nyan geujak u pasi.", "ind": "Dia membeli buah di pasar."},   # Indonesian side leaks
             {"ace": "Aneuek miet jimeulakee bu.", "ind": "Anak kecil meminta nasi."},
             {"ace": "Aneuek miet jimeulakee bu", "ind": "Anak kecil meminta nasi"}]        # duplicate of the previous
    kept, st = corpus.remove_leaks(train, held)
    assert [r["ace"] for r in kept] == ["Aneuek miet jimeulakee bu."]
    assert st == {"exact_leak": 2, "near_leak": 1, "dup_in_train": 1}

def _fake_root(tmp_path, n_flores_dev=40):
    nusax = json.load(open(ROOT / "data/final/nusax/train.json", encoding="utf-8"))
    d = tmp_path / "data/final/nusax"; d.mkdir(parents=True)
    json.dump(nusax[:30], open(d / "train.json", "w")); json.dump(nusax[30:36], open(d / "validation.json", "w"))
    json.dump(nusax[36:42] + [nusax[0]], open(d / "test.json", "w"))           # nusax[0] is ALSO in train: must be removed
    f = tmp_path / "data/final/flores"; f.mkdir(parents=True)
    json.dump(nusax[100:100 + n_flores_dev], open(f / "dev.json", "w")); json.dump(nusax[200:220], open(f / "devtest.json", "w"))
    return tmp_path

def test_build_train_splits_and_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(corpus, "ROOT", _fake_root(tmp_path))
    extra = tmp_path / "hik_train.json"; json.dump([{"ace": "Hikayat nyoe geukarang lé ureueng tuha.", "ind": "Hikayat ini dikarang oleh orang tua."}], open(extra, "w"))
    m = corpus.build(extra=[str(extra)], extra_test=[f"hikayat={extra}"])
    assert m["validation"]["by_source"] == {"flores": 10, "nusax": 6}
    assert m["tests"]["nusax"]["n"] == 7 and m["tests"]["flores"]["n"] == 20 and m["tests"]["hikayat"]["n"] == 1
    assert m["train"]["exact_leak"] >= 2      # nusax[0] (in nusax test) and the extra pair (also used as a test set)
    assert m["train"]["by_source"]["flores"] == 30 and "hik_train" not in m["train"]["by_source"]
    tr = json.load(open(tmp_path / "data/final/combined/train.json")); held = []
    for k in ("validation.json", "test_nusax.json", "test_flores.json", "test_hikayat.json"):
        held += json.load(open(tmp_path / "data/final/combined" / k))
    from acehid.train import assert_no_leak
    assert_no_leak([(r["ace"], r["ind"]) for r in tr], [(r["ace"], r["ind"]) for r in held])
    m2 = corpus.build(extra=[str(extra)], extra_test=[f"hikayat={extra}"])          # deterministic
    assert json.load(open(tmp_path / "data/final/combined/train.json")) == tr and m2["train"] == m["train"]

def test_build_without_flores_still_works(tmp_path, monkeypatch):
    root = _fake_root(tmp_path)
    for f in (root / "data/final/flores").iterdir(): f.unlink()
    monkeypatch.setattr(corpus, "ROOT", root)
    m = corpus.build()
    assert m["sources"] == ["nusax"] and set(m["tests"]) == {"nusax"} and m["train"]["n"] == 29

def test_real_repo_data_has_no_leak():
    """The committed NusaX (+ FLORES when present) data must build into a leak-free training set."""
    import shutil, tempfile
    with tempfile.TemporaryDirectory() as t:
        out = f"{t}/combined"
        m = corpus.build(outdir=out)
        assert m["train"]["n"] > 400 and m["tests"]["nusax"]["n"] == 400

def test_app_prefers_finetuned_model(tmp_path, monkeypatch):
    monkeypatch.setattr(translate, "FINETUNED", tmp_path)
    assert translate.default_model("nllb") == "facebook/nllb-200-distilled-600M"
    (tmp_path / "config.json").write_text("{}")
    assert translate.default_model("nllb") == str(tmp_path) and translate.Translator("nllb").model == str(tmp_path)
