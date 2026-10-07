"""python -m acehid <command> ...   (run `python -m acehid -h`)"""
import argparse, json, os, sys, glob
from .common import *

def main(argv=None):
    ap = argparse.ArgumentParser(prog="acehid", description="Acehnese -> Indonesian corpus pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("audit", help="1. load AcehX, write data/extracted/acehx.jsonl + reports/acehx_audit.md")
    p = sub.add_parser("extract", help="2. PDFs/TXT in data/raw/hikayat -> pages (OCR for scanned pages)"); p.add_argument("--src", default="data/raw/hikayat"); p.add_argument("--no-ocr", action="store_true")
    p = sub.add_parser("screen", help="3. pages -> sentences + screening labels"); p.add_argument("--layout", default="auto", choices=["auto", "verse", "prose"])
    p = sub.add_parser("normalize", help="4. add ace_normalized"); p.add_argument("--strip-all", action="store_true")
    sub.add_parser("dedupe", help="5. exact + near-duplicate check vs AcehX and itself")
    p = sub.add_parser("review-export", help="CSV of rows a human must check"); p.add_argument("--inp", default="data/deduplicated/hikayat.jsonl"); p.add_argument("--out", default="data/review/review_sheet.csv")
    p = sub.add_parser("review-import", help="apply a filled-in review sheet"); p.add_argument("sheet"); p.add_argument("--inp", default="data/deduplicated/hikayat.jsonl"); p.add_argument("--out", default="data/deduplicated/hikayat_reviewed.jsonl")
    p = sub.add_parser("translate", help="6. draft translation (machine_draft)"); p.add_argument("--inp", default="data/deduplicated/hikayat.jsonl"); p.add_argument("--out", default="data/aligned/hikayat_translated.jsonl")
    p.add_argument("--provider", default="claude", choices=["claude", "groq", "nllb", "copy"]); p.add_argument("--model"); p.add_argument("--limit", type=int); p.add_argument("--fewshot", type=int, default=5)
    p = sub.add_parser("export", help="7. QC + Atlas JSON + source-level split"); p.add_argument("--inp", default="data/aligned/hikayat_translated.jsonl"); p.add_argument("--version", default="ace-id-v0.1"); p.add_argument("--include-drafts", action="store_true")
    sub.add_parser("fetch-nusax", help="download NusaX-MT csv files from GitHub into data/raw/external/nusax")
    sub.add_parser("nusax", help="NusaX-MT -> Atlas format (data/final/nusax)")
    p = sub.add_parser("eval", help="chrF/BLEU/TER on NusaX valid+test"); p.add_argument("--provider", nargs="+", default=["copy"]); p.add_argument("--model"); p.add_argument("--fewshot", type=int, default=5); p.add_argument("--limit", type=int)
    p = sub.add_parser("train", help="fine-tune NLLB on Aceh->Indonesian pairs (GPU/Colab recommended)"); p.add_argument("--base", default="facebook/nllb-200-distilled-600M"); p.add_argument("--out", default="models/ace-id-nllb")
    p.add_argument("--extra", nargs="*", default=[], help="extra reviewed pair files [{ace,ind}], e.g. data/final/train.json"); p.add_argument("--epochs", type=int, default=5); p.add_argument("--lr", type=float, default=1e-4); p.add_argument("--batch-size", type=int, default=8)
    sub.add_parser("langid-build", help="retrain the language-check model from AcehX + NusaX train")
    p = sub.add_parser("serve", help="web app"); p.add_argument("--port", type=int, default=8000); p.add_argument("--host", default="127.0.0.1"); p.add_argument("--open", action="store_true", help="open the browser")
    p = sub.add_parser("all", help="2-5 + export on data/raw/hikayat (translate separately)"); p.add_argument("--no-ocr", action="store_true")
    a = ap.parse_args(argv)
    P = lambda s: ROOT / s

    if a.cmd == "audit":
        from . import audit; audit.run()
    elif a.cmd == "extract":
        from . import extract; extract.run(a.src, P("data/extracted/hikayat_pages.jsonl"), ocr=not a.no_ocr)
    elif a.cmd == "screen":
        from . import screen; screen.run(P("data/extracted/hikayat_pages.jsonl"), P("data/cleaned/hikayat_sentences.jsonl"), a.layout)
    elif a.cmd == "normalize":
        from . import normalize
        write_jsonl(P("data/normalized/hikayat.jsonl"), normalize.run(read_jsonl(P("data/cleaned/hikayat_sentences.jsonl")), a.strip_all))
    elif a.cmd == "dedupe":
        from . import dedupe
        write_jsonl(P("data/deduplicated/hikayat.jsonl"), dedupe.run(list(read_jsonl(P("data/normalized/hikayat.jsonl")))))
    elif a.cmd == "review-export":
        from . import review; os.makedirs(os.path.dirname(P(a.out)), exist_ok=True); review.export_sheet(list(read_jsonl(P(a.inp))), P(a.out))
    elif a.cmd == "review-import":
        from . import review; write_jsonl(P(a.out), review.import_sheet(list(read_jsonl(P(a.inp))), a.sheet))
    elif a.cmd == "translate":
        from . import translate
        out = P(a.out); done = {r["id"]: r for r in read_jsonl(out)} if out.exists() else {}
        tr = translate.Translator(a.provider, a.model, a.fewshot)
        rows = list(read_jsonl(P(a.inp)))
        translate.run(rows, tr, a.limit, done, on_progress=lambda d: write_jsonl(out, d.values()))
        write_jsonl(out, done.values())
    elif a.cmd == "export":
        from . import export
        print(json.dumps(export.export(list(read_jsonl(P(a.inp))), a.version, include_drafts=a.include_drafts), indent=1))
    elif a.cmd == "fetch-nusax":
        import urllib.request
        d = P("data/raw/external/nusax"); d.mkdir(parents=True, exist_ok=True)
        for sp in ("train", "valid", "test"):
            urllib.request.urlretrieve(f"https://raw.githubusercontent.com/IndoNLP/nusax/main/datasets/mt/{sp}.csv", d / f"{sp}.csv")
        print("downloaded to", d)
    elif a.cmd == "nusax":
        from . import nusax; nusax.run()
    elif a.cmd == "eval":
        from . import evalnusax
        from .translate import Translator
        res = [evalnusax.evaluate(Translator(p, a.model, a.fewshot), limit=a.limit) for p in a.provider]
        print(evalnusax.write_report(res))
        json.dump(res, open(P("reports/eval_nusax.json"), "w"), indent=1)
    elif a.cmd == "train":
        from . import train
        train.train(a.base, a.out, a.extra, a.epochs, a.lr, a.batch_size)
    elif a.cmd == "langid-build":
        from . import langid; print(json.dumps(langid.build(), indent=1))
    elif a.cmd == "serve":
        from app.server import serve
        if a.open:
            import threading, webbrowser; threading.Timer(1.5, lambda: webbrowser.open(f"http://{a.host}:{a.port}")).start()
        serve(a.host, a.port)
    elif a.cmd == "all":
        from . import extract, screen, normalize, dedupe, review
        extract.run(str(P("data/raw/hikayat")), P("data/extracted/hikayat_pages.jsonl"), ocr=not a.no_ocr)
        rows = screen.run(P("data/extracted/hikayat_pages.jsonl"), P("data/cleaned/hikayat_sentences.jsonl"))
        rows = dedupe.run(normalize.run(rows)); write_jsonl(P("data/deduplicated/hikayat.jsonl"), rows)
        os.makedirs(P("data/review"), exist_ok=True); review.export_sheet(rows, P("data/review/review_sheet.csv"))
        from .pipeline import summary; print(json.dumps(summary(rows), indent=1))

if __name__ == "__main__":
    main()
