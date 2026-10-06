"""Local web app (stdlib only). Run: python -m acehid serve  ->  http://127.0.0.1:8000
  Tab 1  Translate text : paste Acehnese -> language check, normalization, draft translation
  Tab 2  Process source : upload hikayat PDF/TXT -> extract (OCR if scanned) -> screen -> normalize -> dedupe vs AcehX
                          -> optional draft translation -> download Atlas JSON / review CSV
Binds to localhost by default. Translation keys are read from environment variables on the server only."""
import json, os, re, tempfile, threading, io, csv, traceback, mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from acehid.common import ROOT
from acehid import pipeline, screen, normalize, langid, translate, export, review, dedupe

HERE = Path(__file__).parent
MAX_UPLOAD = 200 * 1024 * 1024
STATE = {"ref": None, "ref_status": "not loaded"}
_translators = {}

def _load_ref():
    ref_path = ROOT / "data/extracted/acehx.jsonl"
    if not ref_path.exists():
        STATE["ref_status"] = "AcehX not found (run `python -m acehid audit` with data/raw/acehx/*.txt); duplicate check vs AcehX is skipped"
        return
    STATE["ref_status"] = "loading AcehX index (first run takes a few minutes)"
    try:
        STATE["ref"] = dedupe.build_ref(ref_path); STATE["ref_status"] = f"ready ({len(STATE['ref'][1])} unique AcehX sentences indexed)"
    except Exception as e:
        STATE["ref_status"] = f"failed: {e}"

def _translator(provider):
    if provider not in _translators:
        _translators[provider] = translate.Translator(provider)
    return _translators[provider]

def _ocr_available():
    try:
        import rapidocr_onnxruntime  # noqa
        return True
    except Exception:
        return False

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, code, body, ctype="application/json", extra=None):
        b = body if isinstance(body, bytes) else (json.dumps(body, ensure_ascii=False).encode() if ctype == "application/json" else body.encode())
        self.send_response(code); self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text") or ctype == "application/json" else ""))
        self.send_header("Content-Length", str(len(b)))
        for k, v in (extra or {}).items(): self.send_header(k, v)
        self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            return self._send(200, (HERE / "index.html").read_bytes(), "text/html")
        if u.path == "/api/status":
            return self._send(200, {"providers": translate.available_providers(), "ocr": _ocr_available(), "acehx": STATE["ref_status"],
                                    "langid_eval": langid.evaluate(), "nusax_fewshot": len(translate._pairs())})
        if u.path == "/favicon.ico":
            return self._send(204, b"", "image/x-icon")
        self._send(404, {"error": "not found"})

    def do_POST(self):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length", 0))
        if n > MAX_UPLOAD:
            return self._send(413, {"error": "file too large"})
        body = self.rfile.read(n)
        try:
            if u.path == "/api/process":
                name = os.path.basename(self.headers.get("X-Filename", "upload.txt")) or "upload.txt"
                if not name.lower().endswith((".pdf", ".txt", ".md")):
                    return self._send(400, {"error": "only .pdf, .txt, .md"})
                q = parse_qs(u.query)
                with tempfile.TemporaryDirectory() as d:
                    p = os.path.join(d, name); open(p, "wb").write(body)
                    pages, rows = pipeline.process_files([p], ocr=q.get("ocr", ["1"])[0] == "1", layout=q.get("layout", ["auto"])[0], ref=STATE["ref"])
                return self._send(200, {"summary": pipeline.summary(rows), "pages": len(pages), "ocr_pages": sum(p["method"] == "ocr" for p in pages),
                                        "pages_needing_ocr": sum(p["method"] == "ocr_needed" for p in pages), "rows": rows})
            req = json.loads(body or "{}")
            if u.path == "/api/translate_text":
                sents, _ = screen.split_page(req.get("text", ""), "prose" if "\n" not in req.get("text", "").strip() else "verse")
                items = []
                for s in sents:
                    norm, rules = normalize.normalize(s)
                    lang, sc = langid.classify(norm) if len(norm.split()) >= 3 else ("ace", 0.0)
                    items.append({"ace_raw": s, "ace_normalized": norm, "norm_rules": rules, "lang": lang, "lang_score": sc})
                prov = req.get("provider", "copy")
                res = _translator(prov).translate([i["ace_normalized"] for i in items]) if items else []
                for i, r in zip(items, res): i.update(ind=r["ind"], confidence=r["confidence"], model=_translator(prov).tag, status="machine_draft")
                return self._send(200, {"items": items})
            if u.path == "/api/translate_rows":
                rows = req["rows"]; tr = _translator(req.get("provider", "copy"))
                translate.run(rows, tr, req.get("limit"))
                return self._send(200, {"rows": rows})
            if u.path == "/api/export":
                rows = req["rows"]; recs = [export.to_atlas_record(r, "hikayat") for r in rows
                                           if r.get("screening") == "KEEP" and r.get("dedup") == "unique" and "ind_raw" in r and not export.qc(r)
                                           and (req.get("include_drafts") or r["translation_status"] != "machine_draft")]
                return self._send(200, json.dumps({"version": "ace-id-v0.1", "n_pairs": len(recs), "data": recs}, ensure_ascii=False, indent=1), "application/json",
                                  {"Content-Disposition": "attachment; filename=atlas_master.json"})
            if u.path == "/api/review_csv":
                buf = io.StringIO(); tmp = Path(tempfile.mkstemp(suffix=".csv")[1])
                review.export_sheet(req["rows"], tmp); data = tmp.read_bytes(); tmp.unlink()
                return self._send(200, data, "text/csv", {"Content-Disposition": "attachment; filename=review_sheet.csv"})
            self._send(404, {"error": "not found"})
        except Exception as e:
            traceback.print_exc()
            self._send(500, {"error": f"{type(e).__name__}: {e}"})

def serve(host="127.0.0.1", port=8000):
    threading.Thread(target=_load_ref, daemon=True).start()
    print(f"Aceh→Indonesian toolkit on http://{host}:{port}  (providers: {list(translate.available_providers())})")
    ThreadingHTTPServer((host, port), H).serve_forever()
