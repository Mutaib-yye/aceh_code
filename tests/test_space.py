"""The hosted app (space/): text handling, model wrapper and UI wiring. Uses a tiny local model / a fake engine (no download)."""
import json, sys, importlib, pytest
from pathlib import Path
from acehid.common import ROOT
from acehid.normalize import normalize as pipeline_normalize

def _load(name, path):
    """Load space/*.py by path: the repo also has an `app` package (local web app), so plain imports would be ambiguous."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod

core = _load("core", ROOT / "space/core.py")          # space/app.py does `from core import ...` (true on Hugging Face too)

def load_space_app():
    return _load("space_app", ROOT / "space/app.py")

def test_normalize_identical_to_training_pipeline():
    texts = [r["ace"] for f in ("train", "validation", "test") for r in json.load(open(ROOT / f"data/final/nusax/{f}.json", encoding="utf-8"))]
    texts += ["Njang djipeugot löen", "TJOET Nja'", "  ‘Ureuëng’  —  inöng  ", "Ë Ö Ü Ï Ä ë ö ü ï ä é è ô", "Djeumpa​ njan"]
    acehx = ROOT / "data/raw/acehx"
    if acehx.exists():
        for f in sorted(acehx.glob("*.txt"))[:3]:
            texts += f.read_text(encoding="utf-8", errors="replace").splitlines()[:2000]
    bad = [t for t in texts if core.normalize(t) != pipeline_normalize(t)[0]]
    assert not bad, f"{len(bad)} differ, e.g. {bad[0]!r}"

def test_split_sentences():
    assert core.split_sentences("Lon jak u peukan. Gobnyan tinggai di rumoh! Pue kaba?  ") == ["Lon jak u peukan.", "Gobnyan tinggai di rumoh!", "Pue kaba?"]
    assert core.split_sentences("hana titik") == ["hana titik"] and core.split_sentences("   ") == []

class FakeEngine(core.Engine):
    """Engine without a model: 'translates' by upper-casing, counting calls, so the text logic is tested exactly."""
    def __init__(self):
        self.model_id, self.info, self.cache, self.calls, self.beams = "fake", None, {}, [], 4
    def _generate(self, sents):
        self.calls.append(list(sents)); return [s.upper() for s in sents]
    def explain(self, normalized, indonesian=None):
        return normalized.split(), (indonesian or "").split()

def test_translate_keeps_lines_normalizes_caches_and_warns():
    e = FakeEngine()
    out, details, notes = e.translate("Njang löen. Gobnyan geujak u pasi uroe nyoe!\n\nAneuek miet jimeulakee bu")
    assert out == "NYANG LOEN. GOBNYAN GEUJAK U PASI UROE NYOE!\n\nANEUEK MIET JIMEULAKEE BU"
    assert details[0] == ["Njang löen.", "Nyang loen.", "NYANG LOEN."] and len(details) == 3
    assert any("Single words" in n for n in notes)                      # "Nyang loen." has < 3 words
    e.translate("Gobnyan geujak u pasi uroe nyoe!")                      # cached: no new model call
    assert len(e.calls) == 1
    assert e.translate("   ") == ("", [], [])
    _, _, notes = e.translate("Gobnyan geujak u pasi uroe nyoe. " * 400)
    assert any("first 5000 characters" in n for n in notes)

def test_accuracy_text():
    assert "not fine-tuned yet" in core.accuracy_markdown(None, "facebook/nllb-200-distilled-600M")
    info = {"train_pairs": 1297, "tests": {"nusax": {"n": 400, "base": {"chrF++": 41.2}, "finetuned": {"chrF++": 47.9}}}}
    md = core.accuracy_markdown(info, "me/ace-id-nllb")
    assert "1297" in md and "| NusaX test (reviews, everyday text) | 400 | 41.2 | **47.9** |" in md

def test_load_info_from_local_model_dir(tmp_path):
    (tmp_path / "training_log.json").write_text(json.dumps({"tests": {}}))
    assert core.load_info(str(tmp_path)) == {"tests": {}} and core.load_info(str(tmp_path / "missing")) is None

def test_engine_with_tiny_real_model(tmp_path):
    pytest.importorskip("torch"); spm = pytest.importorskip("sentencepiece")
    from transformers import NllbTokenizer, M2M100Config, M2M100ForConditionalGeneration
    (tmp_path / "c.txt").write_text("Gobnyan geujak u pasi\nDia pergi ke pantai\nAneuek miet\nAnak kecil", encoding="utf-8")
    spm.SentencePieceTrainer.train(input=str(tmp_path / "c.txt"), model_prefix=str(tmp_path / "sp"), vocab_size=40, model_type="bpe", hard_vocab_limit=False, minloglevel=2)
    tok = NllbTokenizer(vocab_file=str(tmp_path / "sp.model"), src_lang="ace_Latn", tgt_lang="ind_Latn")
    cfg = M2M100Config(vocab_size=len(tok), d_model=16, encoder_layers=1, decoder_layers=1, encoder_attention_heads=2, decoder_attention_heads=2,
                       encoder_ffn_dim=32, decoder_ffn_dim=32, max_position_embeddings=600, pad_token_id=tok.pad_token_id,
                       bos_token_id=tok.bos_token_id, eos_token_id=tok.eos_token_id, decoder_start_token_id=tok.eos_token_id)
    d = tmp_path / "m"; M2M100ForConditionalGeneration(cfg).half().save_pretrained(d); tok.save_pretrained(d)   # fp16 like our Hub upload
    (d / "training_log.json").write_text(json.dumps({"train_pairs": 3, "tests": {"nusax": {"n": 1, "base": {"chrF++": 1.0}, "finetuned": {"chrF++": 2.0}}}}))
    e = core.Engine(str(d), beams=2)
    out, details, _ = e.translate("Gobnyan geujak u pasi. Aneuek miet\nGobnyan geujak u pasi.")
    assert out.count("\n") == 1 and len(details) == 3 and all(isinstance(x[2], str) for x in details)
    assert e.info["train_pairs"] == 3

def test_ui_builds_and_translate_event_works():
    gr = pytest.importorskip("gradio")
    app = load_space_app()
    demo = app.build_ui(FakeEngine())
    assert isinstance(demo, gr.Blocks)
    fn = next(d.fn for d in demo.fns.values() if d.api_name == "translate")
    out, notes, details, how, words = fn("Gobnyan geujak u pasi uroe nyoe.")
    assert out == "GOBNYAN GEUJAK U PASI UROE NYOE." and notes.visible is False and details[0][2] == out
    assert "Langkah 1" in how and "`Gobnyan`" in how and "Langkah 2" in how
    assert words == ""                                                  # no glossary loaded: the panel stays empty
    assert app.launch_kwargs()["css"] and app.EXAMPLES
    test = {r["ace"] for r in json.load(open(ROOT / "data/final/nusax/test.json", encoding="utf-8"))}
    hik = ROOT / "data/final/hikayat/abu_sammah/test.json"
    test |= {r["ace"] for r in json.load(open(hik, encoding="utf-8"))} if hik.exists() else set()
    assert all(e in test for e in app.EXAMPLES), "demo examples must come from a test set (never trained on)"

def test_explain_shows_real_encoder_and_decoder_tokens(tmp_path):
    pytest.importorskip("torch"); spm = pytest.importorskip("sentencepiece")
    from transformers import NllbTokenizer
    (tmp_path / "c.txt").write_text("Gobnyan geujak u pasi\nDia pergi ke pantai\nAneuek miet\nAnak kecil", encoding="utf-8")
    spm.SentencePieceTrainer.train(input=str(tmp_path / "c.txt"), model_prefix=str(tmp_path / "sp"), vocab_size=40, model_type="bpe", hard_vocab_limit=False, minloglevel=2)
    tok = NllbTokenizer(vocab_file=str(tmp_path / "sp.model"), src_lang="ace_Latn", tgt_lang="ind_Latn")
    e = core.Engine.__new__(core.Engine)
    e.tok, e.beams = tok, 4
    src, tgt = e.explain("Gobnyan geujak", "Dia pergi")
    assert src[0] == "ace_Latn" and src[-1] == "</s>"            # encoder: Acehnese language token ... end of sentence
    assert tgt[0] == "ind_Latn" and tgt[-1] == "</s>"            # decoder: starts from the Indonesian language token


GLOSS = ("input,target,error_category,error_type,severity,source,wer,translate_ind,sentiment\n"
         "zaaba,zaaba,none,none,none,x,0,sejenis pohon,neutral\n"
         "zaaba,zaaba,none,none,none,x,0,pagar dari bambu,neutral\n"
         "zaabé; zaabu,\"zaabé, zaabu\",none,none,none,x,0,kata ujian kedua,neutral\n"
         "zaabo,zaabx,orthographic,character_substitution,minor,x,0.2,salah ejaan buatan,neutral\n")

def test_glossary_loads_variants_skips_misspellings_and_ranks_meanings_by_the_translation(tmp_path):
    p = tmp_path / "g.csv"; p.write_text(GLOSS, encoding="utf-8")
    g = core.Glossary.load(str(p))
    assert core.Glossary.load(str(tmp_path / "none.csv")) is None
    found = dict(g.lookup("Zaaba dan ZAABU, zaabx", "ada pagar bambu di sini"))
    assert list(found) == ["Zaaba", "ZAABU"]                              # accents/case ignored; the misspelling row is not a headword
    assert found["Zaaba"][0] == ("pagar dari bambu", 2) and found["Zaaba"][1][1] == 0   # the meaning matching the translation comes first
    assert found["ZAABU"] == [("kata ujian kedua", 0)]

def test_words_panel_marks_the_best_meaning_and_stays_empty_without_glossary(tmp_path):
    p = tmp_path / "g.csv"; p.write_text(GLOSS, encoding="utf-8")
    app = load_space_app()
    e = FakeEngine(); e.glossary = core.Glossary.load(str(p))
    md = app.words_md(e, [["Zaaba", "Zaaba", "ada pagar bambu"]])
    assert "**Zaaba** (beberapa arti) — ✓ pagar dari bambu / sejenis pohon" in md and "Kamus Aceh-Indonesia (1985)" in md
    e.glossary = None
    assert app.words_md(e, [["Zaaba", "Zaaba", "x"]]) == ""


HEAD = "input,target,error_category,error_type,severity,source,wer,translate_ind,sentiment\n"

def test_find_glossary_finds_the_csv_wherever_it_is(tmp_path, monkeypatch):
    monkeypatch.delenv("GLOSSARY", raising=False)
    root = tmp_path / "proj"; (root / "a/b").mkdir(parents=True)
    assert core.find_glossary(roots=[root]) is None
    (root / "other.csv").write_text(HEAD)                                  # no 'kamus' in the name: ignored
    (root / "a/b/kamus_wrong_columns.csv").write_text("x,y\n1,2\n")         # right name, wrong header: ignored
    assert core.find_glossary(roots=[root]) is None
    deep = root / "a/b/Kamus aceh copy.csv"; deep.write_text(HEAD)         # renamed, in a sub-sub-folder
    assert core.find_glossary(roots=[root]) == str(deep)
    (root / "data").mkdir(); exact = root / "data" / "kamus_aceh_indonesia_1985.csv"; exact.write_text(HEAD)
    assert core.find_glossary(roots=[root]) == str(exact)                  # the expected place wins over a deep copy
    monkeypatch.setenv("GLOSSARY", str(deep))
    assert core.find_glossary(roots=[root]) == str(deep)                   # $GLOSSARY wins over everything

def test_glossary_load_searches_by_itself(tmp_path, monkeypatch):
    monkeypatch.delenv("GLOSSARY", raising=False); monkeypatch.chdir(tmp_path)
    (tmp_path / "Downloads").mkdir(); (tmp_path / "Downloads" / "kamusbahasaaceh-indo.csv").write_text(HEAD + "zaaba,zaaba,none,none,none,x,0,rumah,neutral\n")
    monkeypatch.setattr(core, "__file__", str(tmp_path / "space" / "core.py"))      # the 'repo' is the empty tmp folder, not the real one
    monkeypatch.setattr(core.os.path, "expanduser", lambda p: str(tmp_path) if p == "~" else p)
    g = core.Glossary.load()
    assert g is not None and "zaaba" in g.entries

class _Resp:
    def __init__(self, data): self.data = data
    def read(self): return self.data
    def __enter__(self): return self
    def __exit__(self, *a): return False

def test_fetch_glossary_downloads_validates_and_tries_the_next_url(tmp_path, monkeypatch):
    import urllib.request
    good = (HEAD + "zaaba,zaaba,none,none,none,x,0,rumah,neutral\n").encode()
    calls = []
    def fake(url, timeout=0):
        calls.append(url)
        if url == "bad": raise OSError("no network")
        return _Resp(good if url == "ok" else b"<html>not found</html>")
    monkeypatch.setattr(urllib.request, "urlopen", fake)
    dest = tmp_path / "data" / "glossary" / "k.csv"
    assert core.fetch_glossary(str(dest), urls=["bad", "html", "ok"]) == str(dest) and calls == ["bad", "html", "ok"]
    assert core.Glossary.load(str(dest)) is not None
    dest.unlink()
    assert core.fetch_glossary(str(dest), urls=["html"]) is None and not dest.exists()      # wrong content is thrown away

def test_glossary_load_fetches_from_the_repo_when_not_on_this_computer(tmp_path, monkeypatch):
    monkeypatch.delenv("GLOSSARY", raising=False); monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(core, "__file__", str(tmp_path / "space" / "core.py"))
    monkeypatch.setattr(core.os.path, "expanduser", lambda p: str(tmp_path) if p == "~" else p)
    fetched = tmp_path / "got.csv"; fetched.write_text(HEAD + "zaaba,zaaba,none,none,none,x,0,rumah,neutral\n")
    monkeypatch.setattr(core, "fetch_glossary", lambda *a, **k: str(fetched))
    assert "zaaba" in core.Glossary.load().entries
