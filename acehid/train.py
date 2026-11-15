"""Fine-tune a pretrained multilingual translation model (default: Meta NLLB-200 distilled 600M) on Acehnese -> Indonesian pairs.

Why fine-tune and not train from scratch: a translation model needs millions of sentence pairs; we have ~2,000 human-translated
pairs (NusaX + FLORES). Fine-tuning keeps what NLLB already knows (it includes Acehnese, ace_Latn) and adapts it to our data.
The result is our own model (our weights, our data, our training run). NLLB weights are CC-BY-NC 4.0: the fine-tuned model is
for research/non-commercial use.

Data (built by `python -m acehid build-train`, see corpus.py): data/final/combined/
  train.json         NusaX train + FLORES dev (minus held-out slice) + reviewed extra pairs, leak-filtered
  validation.json    NusaX valid + 200 FLORES dev sentences: picks the best epoch / early stopping, never trained on
  test_*.json        NusaX test, FLORES devtest (+ extra): scored ONCE at the end, base vs fine-tuned, never used for selection
Metrics: chrF++ (main, as in the NLLB paper), chrF, BLEU (sacreBLEU). Output: <out>/training_log.json and <out>/RESULTS.md.
Needs: pip install torch transformers sentencepiece sacrebleu. GPU strongly recommended (free Colab T4: ~15-30 min).
"""
import json, random, time, os, math
from .common import *

DEFAULT_BASE = "facebook/nllb-200-distilled-600M"
DATA = "data/final/combined"

def load_pairs(path):
    return [(r["ace"], r["ind"]) for r in json.load(open(path, encoding="utf-8"))]

def load_data(data_dir=DATA):
    d = ROOT / data_dir
    m = json.load(open(d / "manifest.json", encoding="utf-8"))
    tests = {k: load_pairs(d / v["file"]) for k, v in m["tests"].items()}
    return load_pairs(d / m["train"]["file"]), load_pairs(d / m["validation"]["file"]), tests, m

def assert_no_leak(train_pairs, eval_pairs):
    ev = {match_key(a) for a, _ in eval_pairs} | {match_key(i) for _, i in eval_pairs}
    bad = [a for a, i in train_pairs if match_key(a) in ev or match_key(i) in ev]
    if bad:
        raise ValueError(f"{len(bad)} training sentences also occur in the dev/test sets (e.g. {bad[0][:60]!r}); refusing to train")

LANG = {"ace": "ace_Latn", "ind": "ind_Latn"}

def directions_of(direction):
    """"both" = Acehnese -> Indonesian AND Indonesian -> Acehnese, one model with language tags (NLLB's own way)."""
    if direction == "both":
        return ["ace-ind", "ind-ace"]
    if direction not in ("ace-ind", "ind-ace"):
        raise ValueError(f"direction must be ace-ind, ind-ace or both, not {direction!r}")
    return [direction]

def oriented(pairs, d):
    """[(ace, ind)] -> [(source, target)] for direction d."""
    return list(pairs) if d == "ace-ind" else [(i, a) for a, i in pairs]

def set_langs(tok, d):
    s, t = d.split("-"); tok.src_lang, tok.tgt_lang = LANG[s], LANG[t]
    return tok.convert_tokens_to_ids(LANG[t])

def translate_batch(model, tok, texts, device, max_len=128, beams=4, bs=16, direction="ace-ind"):
    import torch
    out = []
    model.eval()
    bos = set_langs(tok, direction)
    for b in range(0, len(texts), bs):
        enc = tok(texts[b:b + bs], return_tensors="pt", padding=True, truncation=True, max_length=max_len).to(device)
        with torch.no_grad():
            gen = model.generate(**enc, forced_bos_token_id=bos, max_new_tokens=max_len, num_beams=beams)
        out += tok.batch_decode(gen, skip_special_tokens=True)
    return out

def metrics(hyp, ref):
    import sacrebleu
    return {"chrF++": round(sacrebleu.corpus_chrf(hyp, [ref], word_order=2).score, 2),
            "chrF": round(sacrebleu.corpus_chrf(hyp, [ref]).score, 2),
            "BLEU": round(sacrebleu.corpus_bleu(hyp, [ref]).score, 2)}

def score(model, tok, pairs, device, return_hyp=False, direction="ace-ind", **kw):
    """pairs are always [(ace, ind)]; direction picks which side is the input."""
    pr = oriented(pairs, direction)
    hyp = translate_batch(model, tok, [a for a, _ in pr], device, direction=direction, **kw)
    m = metrics(hyp, [i for _, i in pr])
    return (m, hyp) if return_hyp else m

def dev_score(model, tok, dev, device, dirs, **kw):
    """Validation chrF++ etc. For one direction the plain metrics; for both, the mean plus each direction under its own key."""
    per = {d: score(model, tok, dev, device, direction=d, **kw) for d in dirs}
    if len(dirs) == 1:
        return per[dirs[0]]
    mean = {k: round(sum(m[k] for m in per.values()) / len(per), 2) for k in next(iter(per.values()))}
    return {**mean, **per}

def results_md(run):
    both = bool(run.get("tests_rev")) and bool(run["tests"])
    rows = [f"# Fine-tuning results: {run['base']} -> {run['out']}" + (" (both directions)" if both else "") + "\n",
            f"Training pairs: {run['train_pairs']} ({', '.join(f'{k} {v}' for k, v in run['train_by_source'].items())}); "
            f"best epoch {run.get('best_epoch')} of {len(run['history'])} (early stopping on validation chrF++).",
            "Test sets were never trained on and never used to pick the epoch. Higher is better.\n",
            "| test set | n | base chrF++ | fine-tuned chrF++ | change | base BLEU | fine-tuned BLEU |", "|---|---|---|---|---|---|---|"]
    for k, t in run["tests"].items():
        b, f = t["base"], t["finetuned"]
        rows.append(f"| {k} | {t['n']} | {b['chrF++']} | {f['chrF++']} | {f['chrF++'] - b['chrF++']:+.2f} | {b['BLEU']} | {f['BLEU']} |")
    for k, t in run["tests"].items():
        rows += [f"\n## Examples: {k}\n", "| Acehnese | reference | base | fine-tuned |", "|---|---|---|---|"]
        for s in t["samples"]:
            rows.append("| " + " | ".join(x.replace("|", "/") for x in (s["ace"], s["ref"], s["base"], s["finetuned"])) + " |")
    if run.get("tests_rev"):
        rows += ["\n# Indonesian -> Acehnese\n", "| test set | n | base chrF++ | fine-tuned chrF++ | change | base BLEU | fine-tuned BLEU |", "|---|---|---|---|---|---|---|"]
        for k, t in run["tests_rev"].items():
            b, f = t["base"], t["finetuned"]
            rows.append(f"| {k} | {t['n']} | {b['chrF++']} | {f['chrF++']} | {f['chrF++'] - b['chrF++']:+.2f} | {b['BLEU']} | {f['BLEU']} |")
        for k, t in run["tests_rev"].items():
            rows += [f"\n## Examples (Indonesian -> Acehnese): {k}\n", "| Indonesian | reference | base | fine-tuned |", "|---|---|---|---|"]
            for s in t["samples"]:
                rows.append("| " + " | ".join(x.replace("|", "/") for x in (s["ind"], s["ref"], s["base"], s["finetuned"])) + " |")
    return "\n".join(rows) + "\n"

def model_card(run):
    """README.md for the Hugging Face model repo (metadata header + the results table)."""
    names = {"nusax": "NusaX-MT", "flores": "FLORES-200", "hikayat": "Hikayat Abu Sammah (Depdikbud)"}
    srcs = ", ".join(names.get(k, k) for k in run.get("train_by_source", {})) or "NusaX-MT"
    return ("---\nlicense: cc-by-nc-4.0\nbase_model: " + run["base"] + "\nlanguage:\n- ace\n- id\npipeline_tag: translation\n"
            "tags:\n- acehnese\n- nllb\n- translation\n---\n\n"
            f"# Acehnese → Indonesian (fine-tuned {run['base'].split('/')[-1]})\n\n"
            f"Fine-tuned on {run['train_pairs']} human-translated sentence/verse pairs ({srcs}). Input is normalized as in "
            "https://github.com/Mutaib-yye/aceh_code (`acehid/normalize.py`); use `src_lang='ace_Latn'` and force `ind_Latn`.\n"
            "Non-commercial use (NLLB weights are CC-BY-NC 4.0). Machine translation: have important text checked by a speaker.\n\n"
            + results_md(run).split("\n", 1)[1])

def train(base=DEFAULT_BASE, out="models/ace-id-nllb", data_dir=DATA, epochs=10, lr=1e-4, batch_size=8, max_len=128, seed=0,
          patience=2, warmup=0.1, label_smoothing=0.1, eval_beams=4, n_samples=8, direction="both", log=print):
    import torch
    import torch.nn.functional as F
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    from transformers.optimization import Adafactor
    random.seed(seed); torch.manual_seed(seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dirs = directions_of(direction)
    pairs, dev, tests, manifest = load_data(data_dir)
    assert_no_leak(pairs, dev + [p for t in tests.values() for p in t])
    log(f"device={device} directions={dirs} train_pairs={len(pairs)} dev={len(dev)} tests={ {k: len(v) for k, v in tests.items()} } base={base}")
    if device == "cpu":
        log("WARNING: no GPU found; the 600M model will be very slow on CPU. Use Google Colab (Runtime > Change runtime type > T4 GPU).")

    tok = AutoTokenizer.from_pretrained(base, src_lang="ace_Latn", tgt_lang="ind_Latn")
    model = AutoModelForSeq2SeqLM.from_pretrained(base).to(device)
    opt = Adafactor(model.parameters(), lr=lr, scale_parameter=False, relative_step=False, warmup_init=False, clip_threshold=1.0, weight_decay=1e-3)
    steps_per_epoch = math.ceil(len(pairs) / batch_size) * len(dirs)
    warm = max(1, int(warmup * steps_per_epoch * epochs))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / warm))     # linear warm-up, then constant
    run = {"base": base, "out": out, "train_pairs": len(pairs), "train_by_source": manifest["train"].get("by_source", {}),
           "max_epochs": epochs, "lr": lr, "batch_size": batch_size, "max_len": max_len, "seed": seed, "patience": patience,
           "direction": direction, "warmup_steps": warm, "label_smoothing": label_smoothing, "optimizer": "Adafactor", "device": device, "data_dir": data_dir, "history": []}
    run["baseline_dev"] = dev_score(model, tok, dev, device, dirs, max_len=max_len, beams=eval_beams)
    log(f"base model, validation: {run['baseline_dev']}")
    best, bad_epochs = run["baseline_dev"]["chrF++"], 0
    os.makedirs(ROOT / out, exist_ok=True)
    model.save_pretrained(ROOT / out); tok.save_pretrained(ROOT / out); run["best_epoch"] = 0   # never worse than the base model
    for ep in range(1, epochs + 1):
        model.train(); losses = []; t0 = time.time()
        batches = []                                            # batches never mix directions: each has one source/target language
        for d in dirs:
            ex = oriented(pairs, d); random.shuffle(ex)
            batches += [(d, ex[b:b + batch_size]) for b in range(0, len(ex), batch_size)]
        random.shuffle(batches)
        for d, chunk in batches:
            set_langs(tok, d)
            enc = tok([a for a, _ in chunk], text_target=[i for _, i in chunk], return_tensors="pt", padding=True, truncation=True, max_length=max_len)
            enc["labels"][enc["labels"] == tok.pad_token_id] = -100
            enc = {k: v.to(device) for k, v in enc.items()}
            logits = model(**enc).logits
            loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), enc["labels"].reshape(-1), ignore_index=-100, label_smoothing=label_smoothing)
            loss.backward(); opt.step(); sched.step(); opt.zero_grad(); losses.append(loss.item())
        dev_s = dev_score(model, tok, dev, device, dirs, max_len=max_len, beams=eval_beams)
        run["history"].append({"epoch": ep, "train_loss": round(sum(losses) / len(losses), 4), "dev": dev_s, "seconds": round(time.time() - t0)})
        log(f"epoch {ep}: loss={run['history'][-1]['train_loss']} validation={dev_s}")
        if dev_s["chrF++"] > best:                                   # keep the best epoch on validation, not the last
            best, bad_epochs = dev_s["chrF++"], 0
            model.save_pretrained(ROOT / out); tok.save_pretrained(ROOT / out)
            run["best_epoch"], run["best_dev"] = ep, dev_s
        else:
            bad_epochs += 1
            if bad_epochs >= patience:
                log(f"early stop: no validation improvement for {patience} epochs"); break
    del model, opt
    if device == "cuda":
        torch.cuda.empty_cache()
    # final, one-time test scores of the selected model vs the untouched base model, per direction
    # run["tests"] = Acehnese -> Indonesian (as before), run["tests_rev"] = Indonesian -> Acehnese
    keys = {"ace-ind": "tests", "ind-ace": "tests_rev"}
    for d in dirs:
        run[keys[d]] = {k: {"n": len(v)} for k, v in tests.items()}
    if "ace-ind" not in dirs:
        run["tests"] = {}
    for name, path in (("finetuned", ROOT / out), ("base", base)):
        m = AutoModelForSeq2SeqLM.from_pretrained(path).to(device)
        for d in dirs:
            for k, v in tests.items():
                run[keys[d]][k][name], run[keys[d]][k][f"_hyp_{name}"] = score(m, tok, v, device, return_hyp=True, direction=d, max_len=max_len, beams=eval_beams)
        del m
        if device == "cuda":
            torch.cuda.empty_cache()
    for d in dirs:
        for k, v in tests.items():
            t = run[keys[d]][k]; hb, hf = t.pop("_hyp_base"), t.pop("_hyp_finetuned")
            src_key = "ace" if d == "ace-ind" else "ind"
            t["samples"] = [{src_key: a, "ref": r, "base": hb[i], "finetuned": hf[i]} for i, (a, r) in enumerate(oriented(v, d)[:n_samples])]
            log(f"TEST {d} {k} (n={len(v)})  base: {t['base']}   fine-tuned: {t['finetuned']}")
    json.dump(run, open(ROOT / out / "training_log.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    md = results_md(run)
    (ROOT / out / "RESULTS.md").write_text(md, encoding="utf-8")
    (ROOT / out / "README.md").write_text(model_card(run), encoding="utf-8")
    (ROOT / "reports").mkdir(exist_ok=True); (ROOT / "reports/finetune_results.md").write_text(md, encoding="utf-8")
    return run
