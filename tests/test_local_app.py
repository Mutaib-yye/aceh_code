"""The Mac launcher (python -m acehid app / ./run_app.sh): finds the trained model once, then serves the app on localhost."""
import json, zipfile, threading, pytest
from acehid import local_app

def _model_dir(d):
    d.mkdir(parents=True, exist_ok=True); (d / "config.json").write_text("{}"); (d / "model.safetensors").write_bytes(b"x" * 10)
    return d

def test_uses_local_model_folder_first(tmp_path):
    target = _model_dir(tmp_path / "models/ace-id-nllb")
    assert local_app.ensure_model(target, ask=lambda _: pytest.fail("must not ask"), zip_search=()) == str(target)

def test_unpacks_the_colab_zip_from_downloads(tmp_path):
    src = _model_dir(tmp_path / "zipsrc")
    dl = tmp_path / "Downloads"; dl.mkdir()
    with zipfile.ZipFile(dl / "ace-id-nllb (1).zip", "w") as z:            # browsers add " (1)"; the zip may hold a top folder
        for f in src.iterdir(): z.write(f, f"ace-id-nllb-fp16/{f.name}")
    target = tmp_path / "models/ace-id-nllb"
    assert local_app.ensure_model(target, ask=lambda _: pytest.fail("must not ask"), zip_search=(dl,)) == str(target)
    assert (target / "config.json").exists() and (target / "model.safetensors").read_bytes() == b"x" * 10

def test_downloads_from_the_account_once_when_given_a_token(tmp_path, monkeypatch):
    got = {}
    def fake_hub(target, token, repo=None):
        got["token"] = token; _model_dir(target); return True
    monkeypatch.setattr(local_app, "_from_hub", fake_hub); monkeypatch.delenv("HF_TOKEN", raising=False)
    target = tmp_path / "m"
    assert local_app.ensure_model(target, ask=lambda _: " hf_abc ", zip_search=()) == str(target) and got["token"] == "hf_abc"
    assert local_app.ensure_model(target, ask=lambda _: pytest.fail("second run must not ask"), zip_search=()) == str(target)

def test_falls_back_to_base_model_without_token_or_on_failure(tmp_path, monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    assert local_app.ensure_model(tmp_path / "a", ask=lambda _: "", zip_search=()) == local_app.BASE_MODEL
    def broken(target, token, repo=None): raise RuntimeError("404 Repository Not Found\nmore")
    monkeypatch.setattr(local_app, "_from_hub", broken)
    assert local_app.ensure_model(tmp_path / "b", ask=lambda _: "hf_x", zip_search=()) == local_app.BASE_MODEL

def test_app_serves_translations_on_localhost(tmp_path):
    pytest.importorskip("gradio"); pytest.importorskip("torch"); spm = pytest.importorskip("sentencepiece")
    from transformers import NllbTokenizer, M2M100Config, M2M100ForConditionalGeneration
    (tmp_path / "c.txt").write_text("Gobnyan geujak u pasi\nDia pergi ke pantai\nAneuek miet\nAnak kecil", encoding="utf-8")
    spm.SentencePieceTrainer.train(input=str(tmp_path / "c.txt"), model_prefix=str(tmp_path / "sp"), vocab_size=40, model_type="bpe", hard_vocab_limit=False, minloglevel=2)
    tok = NllbTokenizer(vocab_file=str(tmp_path / "sp.model"), src_lang="ace_Latn", tgt_lang="ind_Latn")
    cfg = M2M100Config(vocab_size=len(tok), d_model=16, encoder_layers=1, decoder_layers=1, encoder_attention_heads=2, decoder_attention_heads=2,
                       encoder_ffn_dim=32, decoder_ffn_dim=32, max_position_embeddings=600, pad_token_id=tok.pad_token_id,
                       bos_token_id=tok.bos_token_id, eos_token_id=tok.eos_token_id, decoder_start_token_id=tok.eos_token_id)
    d = tmp_path / "m"; M2M100ForConditionalGeneration(cfg).half().save_pretrained(d); tok.save_pretrained(d)
    demo = local_app.run(str(d), port=7871, open_browser=False, prevent_thread_lock=True)
    try:
        from gradio_client import Client
        out = Client("http://127.0.0.1:7871/", verbose=False).predict("Gobnyan geujak u pasi.", api_name="/translate")
        assert isinstance(out[0], str) and len(out) == 3
    finally:
        import gradio as gr
        gr.close_all()
