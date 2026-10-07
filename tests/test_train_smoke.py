"""Smoke test of the fine-tuning loop on a TINY random model + tokenizer built locally (no Hugging Face download).
It proves the code path (tokenization with language codes, loss, optimizer step, dev scoring, best-epoch save, leak check, log file)
runs end to end. It says NOTHING about translation quality: that needs the real NLLB model on a GPU (notebooks/train_colab.ipynb)."""
import json, pytest
torch = pytest.importorskip("torch"); pytest.importorskip("transformers"); spm = pytest.importorskip("sentencepiece")
from acehid import train
from acehid.common import ROOT

PAIRS = [{"ace": f"Tiep uroe tuhan jijak u pasi {w} ngon anoe", "ind": f"Setiap hari tuan pergi ke pantai {w} dengan kuda"} for w in "alfa beta gama delta epsilon zeta eta teta iota kapa lamda mu".split()]

def tiny_model(tmp_path):
    from transformers import NllbTokenizer, M2M100Config, M2M100ForConditionalGeneration
    corpus = tmp_path / "c.txt"; corpus.write_text("\n".join(p["ace"] + "\n" + p["ind"] for p in PAIRS), encoding="utf-8")
    spm.SentencePieceTrainer.train(input=str(corpus), model_prefix=str(tmp_path / "sp"), vocab_size=60, model_type="bpe", character_coverage=1.0, hard_vocab_limit=False)
    tok = NllbTokenizer(vocab_file=str(tmp_path / "sp.model"), src_lang="ace_Latn", tgt_lang="ind_Latn")
    cfg = M2M100Config(vocab_size=len(tok), d_model=32, encoder_layers=1, decoder_layers=1, encoder_attention_heads=2, decoder_attention_heads=2,
                       encoder_ffn_dim=64, decoder_ffn_dim=64, max_position_embeddings=64, pad_token_id=tok.pad_token_id,
                       bos_token_id=tok.bos_token_id, eos_token_id=tok.eos_token_id, decoder_start_token_id=tok.eos_token_id)
    d = tmp_path / "tiny"; M2M100ForConditionalGeneration(cfg).save_pretrained(d); tok.save_pretrained(d)
    return str(d)

def test_training_loop_runs_and_logs(tmp_path, monkeypatch):
    base = tiny_model(tmp_path)
    (tmp_path / "tr.json").write_text(json.dumps(PAIRS[:8]), encoding="utf-8")
    (tmp_path / "dv.json").write_text(json.dumps(PAIRS[8:10]), encoding="utf-8")
    (tmp_path / "te.json").write_text(json.dumps(PAIRS[10:]), encoding="utf-8")
    monkeypatch.setattr(train, "ROOT", tmp_path)
    run = train.train(base=base, out="out", epochs=2, lr=1e-3, batch_size=4, max_len=32, eval_beams=1,
                      train_file="tr.json", dev_file="dv.json", test_file="te.json", log=lambda *_: None)
    assert len(run["history"]) == 2 and run["history"][0]["train_loss"] > 0 and run["best_epoch"] in (1, 2)
    assert (tmp_path / "out" / "training_log.json").exists() and (tmp_path / "out" / "config.json").exists()
    from acehid.translate import Translator            # the saved model must load through the app's translator path
    res = Translator("nllb", model=str(tmp_path / "out")).translate(["Tiep uroe tuhan jijak u pasi alfa ngon anoe"])
    assert len(res) == 1 and isinstance(res[0]["ind"], str)
    assert set(run["test_finetuned"]) == {"chrF", "BLEU"} and set(run["test_base"]) == {"chrF", "BLEU"}

def test_leak_check_blocks_training_on_eval_sentences():
    with pytest.raises(ValueError, match="dev/test"):
        train.assert_no_leak([("a b c", "x y z")], [("A b c!", "q")])
    train.assert_no_leak([("a b c", "x y z")], [("d e f", "q")])    # no overlap: fine

def test_real_nusax_files_have_no_leak():
    tr = train.load_pairs(ROOT / "data/final/nusax/train.json")
    ev = train.load_pairs(ROOT / "data/final/nusax/validation.json") + train.load_pairs(ROOT / "data/final/nusax/test.json")
    train.assert_no_leak(tr, ev)
