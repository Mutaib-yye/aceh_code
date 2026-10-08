"""Smoke test of the fine-tuning loop on a TINY random model + tokenizer built locally (no Hugging Face download).
It proves the code path (build-train -> tokenization with language codes, label-smoothed loss, optimizer + warm-up, validation scoring,
best-epoch save, early stopping, test scoring base vs fine-tuned, RESULTS.md, leak check) runs end to end.
It says NOTHING about translation quality: that needs the real NLLB model on a GPU (notebooks/train_colab.ipynb)."""
import json, pytest
torch = pytest.importorskip("torch"); pytest.importorskip("transformers"); spm = pytest.importorskip("sentencepiece")
from acehid import train, corpus
from acehid.common import ROOT

def tiny_model(tmp_path, texts):
    from transformers import NllbTokenizer, M2M100Config, M2M100ForConditionalGeneration
    c = tmp_path / "c.txt"; c.write_text("\n".join(texts), encoding="utf-8")
    spm.SentencePieceTrainer.train(input=str(c), model_prefix=str(tmp_path / "sp"), vocab_size=200, model_type="bpe", character_coverage=1.0, hard_vocab_limit=False)
    tok = NllbTokenizer(vocab_file=str(tmp_path / "sp.model"), src_lang="ace_Latn", tgt_lang="ind_Latn")
    cfg = M2M100Config(vocab_size=len(tok), d_model=32, encoder_layers=1, decoder_layers=1, encoder_attention_heads=2, decoder_attention_heads=2,
                       encoder_ffn_dim=64, decoder_ffn_dim=64, max_position_embeddings=128, pad_token_id=tok.pad_token_id,
                       bos_token_id=tok.bos_token_id, eos_token_id=tok.eos_token_id, decoder_start_token_id=tok.eos_token_id)
    d = tmp_path / "tiny"; M2M100ForConditionalGeneration(cfg).save_pretrained(d); tok.save_pretrained(d)
    return str(d)

@pytest.fixture
def data_root(tmp_path, monkeypatch):
    nx = json.load(open(ROOT / "data/final/nusax/train.json", encoding="utf-8"))
    for sub, files in {"nusax": {"train": nx[:24], "validation": nx[24:28], "test": nx[28:32]},
                       "flores": {"dev": nx[40:56], "devtest": nx[60:64]}}.items():
        d = tmp_path / "data/final" / sub; d.mkdir(parents=True)
        for k, v in files.items():
            json.dump(v, open(d / f"{k}.json", "w"))
    monkeypatch.setattr(corpus, "ROOT", tmp_path); monkeypatch.setattr(train, "ROOT", tmp_path)
    corpus.build()
    return tmp_path, [x for r in nx[:64] for x in (r["ace"], r["ind"])]

def test_training_loop_runs_and_logs(tmp_path, data_root):
    root, texts = data_root
    base = tiny_model(tmp_path, texts)
    run = train.train(base=base, out="out", epochs=3, lr=1e-3, batch_size=8, max_len=48, eval_beams=1, patience=5, log=lambda *_: None)
    assert len(run["history"]) == 3 and run["history"][0]["train_loss"] > 0 and run["best_epoch"] in (0, 1, 2, 3)
    assert set(run["tests"]) == {"nusax", "flores"} and run["tests"]["nusax"]["n"] == 4
    for t in run["tests"].values():
        assert set(t["base"]) == set(t["finetuned"]) == {"chrF++", "chrF", "BLEU"} and len(t["samples"]) == 4
    out = root / "out"
    assert (out / "training_log.json").exists() and (out / "config.json").exists()
    md = (out / "RESULTS.md").read_text(encoding="utf-8"); assert "| nusax | 4 |" in md and "| flores | 4 |" in md
    from acehid.translate import Translator            # the saved model must load through the app's translator path
    res = Translator("nllb", model=str(out)).translate(["Tiep uroe tuhan jijak u pasi alfa ngon anoe"])
    assert len(res) == 1 and isinstance(res[0]["ind"], str)

def test_early_stopping(tmp_path, data_root):
    _, texts = data_root
    run = train.train(base=tiny_model(tmp_path, texts), out="out2", epochs=6, lr=0.0, batch_size=8, max_len=48, eval_beams=1, patience=1, log=lambda *_: None)
    assert len(run["history"]) == 1 and run["best_epoch"] == 0      # lr=0 cannot improve -> stops after 1 epoch, keeps the base model

def test_leak_check_blocks_training_on_eval_sentences():
    with pytest.raises(ValueError, match="dev/test"):
        train.assert_no_leak([("a b c", "x y z")], [("A b c!", "q")])
    train.assert_no_leak([("a b c", "x y z")], [("d e f", "q")])    # no overlap: fine

def test_real_nusax_files_have_no_leak():
    tr = train.load_pairs(ROOT / "data/final/nusax/train.json")
    ev = train.load_pairs(ROOT / "data/final/nusax/validation.json") + train.load_pairs(ROOT / "data/final/nusax/test.json")
    train.assert_no_leak(tr, ev)
