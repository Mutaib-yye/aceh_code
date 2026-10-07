"""Fine-tune a pretrained multilingual translation model (default: Meta NLLB-200 distilled 600M) on Acehnese -> Indonesian pairs.

Why fine-tune and not train from scratch: a translation model needs millions of sentence pairs; we have ~500 (NusaX train) plus whatever
reviewed hikayat pairs get added. Fine-tuning keeps what NLLB already knows (it includes Acehnese, ace_Latn) and adapts it to our data.
The result is our own model (our weights, our data, our training run); log is written to <out>/training_log.json.

Data rules (enforced here):
  * training pairs: data/final/nusax/train.json  (+ --extra files such as reviewed hikayat pairs)
  * dev set (model selection): NusaX validation   - never trained on
  * test set (final score):    NusaX test         - never trained on, never used for model selection
  * a leak check refuses to train if any training sentence also occurs in NusaX validation/test
Machine drafts must NOT be passed in --extra unless a person reviewed them (see TRANSLATION_GUIDELINE.md).

Needs: pip install torch transformers sentencepiece sacrebleu. A GPU is strongly recommended (free Colab T4 works for the 600M model).
"""
import json, random, time, os
from .common import *

DEFAULT_BASE = "facebook/nllb-200-distilled-600M"

def load_pairs(path):
    return [(r["ace"], r["ind"]) for r in json.load(open(path, encoding="utf-8"))]

def assert_no_leak(train_pairs, eval_pairs):
    ev = {match_key(a) for a, _ in eval_pairs} | {match_key(i) for _, i in eval_pairs}
    bad = [a for a, i in train_pairs if match_key(a) in ev or match_key(i) in ev]
    if bad:
        raise ValueError(f"{len(bad)} training sentences also occur in the dev/test sets (e.g. {bad[0][:60]!r}); refusing to train")

def translate_batch(model, tok, texts, device, max_len=128, beams=4, bs=16):
    import torch
    out = []
    model.eval()
    for b in range(0, len(texts), bs):
        enc = tok(texts[b:b + bs], return_tensors="pt", padding=True, truncation=True, max_length=max_len).to(device)
        with torch.no_grad():
            gen = model.generate(**enc, forced_bos_token_id=tok.convert_tokens_to_ids("ind_Latn"), max_new_tokens=max_len, num_beams=beams)
        out += tok.batch_decode(gen, skip_special_tokens=True)
    return out

def score(model, tok, pairs, device, **kw):
    import sacrebleu
    hyp = translate_batch(model, tok, [a for a, _ in pairs], device, **kw)
    ref = [i for _, i in pairs]
    return {"chrF": round(sacrebleu.corpus_chrf(hyp, [ref]).score, 2), "BLEU": round(sacrebleu.corpus_bleu(hyp, [ref]).score, 2)}

def train(base=DEFAULT_BASE, out="models/ace-id-nllb", extra=(), epochs=5, lr=1e-4, batch_size=8, max_len=128, seed=0,
          train_file="data/final/nusax/train.json", dev_file="data/final/nusax/validation.json", test_file="data/final/nusax/test.json",
          eval_beams=4, log=print):
    import torch
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    from transformers.optimization import Adafactor
    random.seed(seed); torch.manual_seed(seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    pairs = load_pairs(ROOT / train_file)
    for f in extra:
        pairs += load_pairs(f)
    dev, test = load_pairs(ROOT / dev_file), load_pairs(ROOT / test_file)
    assert_no_leak(pairs, dev + test)
    log(f"device={device} train_pairs={len(pairs)} dev={len(dev)} test={len(test)} base={base}")
    if device == "cpu":
        log("WARNING: no GPU found; the 600M model will be very slow on CPU. Use Google Colab (Runtime > Change runtime type > T4 GPU).")

    tok = AutoTokenizer.from_pretrained(base, src_lang="ace_Latn", tgt_lang="ind_Latn")
    model = AutoModelForSeq2SeqLM.from_pretrained(base).to(device)
    opt = Adafactor(model.parameters(), lr=lr, scale_parameter=False, relative_step=False, warmup_init=False, clip_threshold=1.0)   # low-memory optimizer used for NLLB fine-tuning

    run = {"base": base, "train_pairs": len(pairs), "epochs": epochs, "lr": lr, "batch_size": batch_size, "max_len": max_len, "seed": seed,
           "optimizer": "Adafactor", "device": device, "extra_files": [str(e) for e in extra], "history": []}
    run["baseline_dev"] = score(model, tok, dev, device, max_len=max_len, beams=eval_beams)
    log(f"base model, dev: {run['baseline_dev']}")
    best = None
    os.makedirs(ROOT / out, exist_ok=True)
    for ep in range(1, epochs + 1):
        model.train(); random.shuffle(pairs); losses = []; t0 = time.time()
        for b in range(0, len(pairs), batch_size):
            chunk = pairs[b:b + batch_size]
            enc = tok([a for a, _ in chunk], text_target=[i for _, i in chunk], return_tensors="pt", padding=True, truncation=True, max_length=max_len)
            enc["labels"][enc["labels"] == tok.pad_token_id] = -100
            loss = model(**{k: v.to(device) for k, v in enc.items()}).loss
            loss.backward(); opt.step(); opt.zero_grad(); losses.append(loss.item())
        dev_s = score(model, tok, dev, device, max_len=max_len, beams=eval_beams)
        run["history"].append({"epoch": ep, "train_loss": round(sum(losses) / len(losses), 4), "dev": dev_s, "seconds": round(time.time() - t0)})
        log(f"epoch {ep}: loss={run['history'][-1]['train_loss']} dev={dev_s}")
        if best is None or dev_s["chrF"] > best:                       # keep the best epoch on the dev set, not the last
            best = dev_s["chrF"]; model.save_pretrained(ROOT / out); tok.save_pretrained(ROOT / out)
            run["best_epoch"] = ep; run["best_dev"] = dev_s
    # final, one-time test score of the selected model vs the untouched base model
    best_model = AutoModelForSeq2SeqLM.from_pretrained(ROOT / out).to(device)
    run["test_finetuned"] = score(best_model, tok, test, device, max_len=max_len, beams=eval_beams)
    del best_model, model, opt
    if device == "cuda":
        torch.cuda.empty_cache()
    base_model = AutoModelForSeq2SeqLM.from_pretrained(base).to(device)
    run["test_base"] = score(base_model, tok, test, device, max_len=max_len, beams=eval_beams)
    json.dump(run, open(ROOT / out / "training_log.json", "w"), indent=1)
    log(f"TEST  base: {run['test_base']}   fine-tuned: {run['test_finetuned']}")
    return run
