"""AcehTranslate AI: the local web app (stdlib server + static page). Started by `python -m acehid app` -> http://127.0.0.1:7860

The page (webui/static) talks to this server only through the JSON API below, so the model can be swapped without touching the UI.
  GET  /api/status        model, dictionary and feedback status          POST /api/translate  text -> translation (+ alternatives)
  GET  /api/dictionary    ?q=word search the Kamus list                  POST /api/batch      one translation per input line
  POST /api/explain       tokens + dictionary entries for a sentence     POST /api/feedback   rating / correction (needs consent)
  GET  /api/evaluation    scores from the model's training_log.json      GET  /api/feedback.csv  export for review
History is kept in the browser (localStorage) and never sent here. Feedback is stored in data/feedback/ (git-ignored) only when the
user ticks the consent box; it is for human review and is never used to train automatically."""
import csv, io, json, re, threading, datetime, mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from acehid.common import ROOT
from acehid.dictionary import Dictionary

STATIC = Path(__file__).parent / "static"
FEEDBACK = ROOT / "data/feedback/feedback.jsonl"
MAX_CHARS, MAX_BATCH_LINES, MAX_BODY = 5000, 200, 1 << 20
ERROR_TYPES = {"vocabulary", "word_order", "missing_meaning", "dialect", "other"}
_lock = threading.Lock()                      # one translation at a time: the model is not thread-safe

class State:
    def __init__(self, engine, dictionary=None, feedback_path=FEEDBACK):
        self.engine, self.dictionary, self.feedback_path = engine, dictionary or Dictionary(), Path(feedback_path)

    def status(self):
        e = self.engine
        return {"model_id": e.model_id, "finetuned": bool((e.info or {}).get("tests")), "max_chars": MAX_CHARS,
                "max_batch_lines": MAX_BATCH_LINES, "dictionary": {"loaded": self.dictionary.loaded, "entries": len(self.dictionary.entries)},
                "voice": False}

    def translate(self, d):
        text = (d.get("text") or "").strip()
        if not text:
            raise ValueError("Teks kosong · the input is empty")
        if len(text) > MAX_CHARS:
            raise ValueError(f"Teks terlalu panjang ({len(text)} > {MAX_CHARS} karakter) · the input is too long")
        norm = d.get("normalize", True) is not False
        with _lock:
            out, details, notes = self.engine.translate(text, normalize_input=norm)
            alts = []
            if d.get("alternatives") and len(details) == 1:
                alts = self.engine.alternatives(details[0][1], 2)
            elif d.get("alternatives"):
                notes.append("Alternatif hanya tersedia untuk satu kalimat · alternatives are shown for a single sentence only.")
        return {"translation": out, "details": [{"src": a, "norm": b, "tgt": c} for a, b, c in details], "notes": notes,
                "alternatives": alts, "normalized": "\n".join(n for _, n, _ in details), "normalize": norm}

    def batch(self, d):
        lines = [l.rstrip() for l in str(d.get("text") or "").splitlines()]
        while lines and not lines[-1].strip():
            lines.pop()
        if not any(l.strip() for l in lines):
            raise ValueError("Teks kosong · the input is empty")
        if len(lines) > MAX_BATCH_LINES:
            raise ValueError(f"Maksimal {MAX_BATCH_LINES} baris · at most {MAX_BATCH_LINES} lines")
        if sum(len(l) for l in lines) > MAX_CHARS * 4:
            raise ValueError("Teks terlalu panjang · the input is too long")
        with _lock:
            tgt = self.engine.translate_lines([l.strip() for l in lines], normalize_input=d.get("normalize", True) is not False)
        return {"rows": [{"src": s, "tgt": t} for s, t in zip(lines, tgt)]}

    def dictionary_search(self, q):
        if not self.dictionary.loaded:
            return {"loaded": False, "q": q}
        r = self.dictionary.search(q)
        return {"loaded": True, "q": q, **r, "found": any(r.values())}

    def explain(self, d):
        sent = (d.get("text") or "").strip().split("\n")[0][:500]
        if not sent:
            raise ValueError("Teks kosong · the input is empty")
        words = []
        for w in dict.fromkeys(re.findall(r"[\w'’\-]+", sent)):
            hits = self.dictionary.lookup(w) if self.dictionary.loaded else []
            words.append({"word": w, "entries": hits[:3]})
        with _lock:
            src, tgt = self.engine.explain(sent, d.get("translation") or None)
        return {"sentence": sent, "words": words, "dictionary_loaded": self.dictionary.loaded, "src_tokens": src, "tgt_tokens": tgt}

    def feedback(self, d):
        rating = d.get("rating")
        if rating not in ("up", "down"):
            raise ValueError("rating must be up or down")
        consent = d.get("consent") is True
        rec = {"time": datetime.datetime.now().isoformat(timespec="seconds"), "model": self.engine.model_id, "rating": rating,
               "consent": consent, "review": "pending"}
        if consent:                                       # texts are stored only with consent
            et = d.get("error_type")
            rec.update(source=str(d.get("source") or "")[:MAX_CHARS], translation=str(d.get("translation") or "")[:MAX_CHARS],
                       correction=str(d.get("correction") or "")[:MAX_CHARS], error_type=et if et in ERROR_TYPES else "")
        self.feedback_path.parent.mkdir(parents=True, exist_ok=True)
        with _lock, open(self.feedback_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return {"ok": True, "stored_text": consent}

    def feedback_csv(self):
        rows = [json.loads(l) for l in self.feedback_path.read_text(encoding="utf-8").splitlines() if l.strip()] if self.feedback_path.exists() else []
        cols = ["time", "model", "rating", "consent", "review", "error_type", "source", "translation", "correction"]
        buf = io.StringIO(); w = csv.DictWriter(buf, cols, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
        return buf.getvalue()

    def evaluation(self):
        info = self.engine.info or {}
        if not info.get("tests"):
            return {"available": False}
        names = {"nusax": "NusaX test (reviews, everyday text)", "flores": "FLORES devtest (Wikipedia-style text)",
                 "hikayat": "Hikayat Abu Sammah (verse, held-out pages)"}
        return {"available": True, "model_id": self.engine.model_id, "train_pairs": info.get("train_pairs"),
                "rows": [{"set": names.get(k, k), "n": t["n"], "base": t["base"].get("chrF++"), "model": t["finetuned"].get("chrF++")}
                         for k, t in info["tests"].items()]}

def make_handler(state):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def _send(self, code, body, ctype="application/json", extra=None):
            b = body if isinstance(body, bytes) else (json.dumps(body, ensure_ascii=False) if ctype == "application/json" else body).encode()
            self.send_response(code); self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.split("/")[0] == "text" or ctype == "application/json" else ""))
            self.send_header("Content-Length", str(len(b))); self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items(): self.send_header(k, v)
            self.end_headers(); self.wfile.write(b)

        def do_GET(self):
            u = urlparse(self.path); q = parse_qs(u.query)
            try:
                if u.path == "/api/status": return self._send(200, state.status())
                if u.path == "/api/dictionary": return self._send(200, state.dictionary_search((q.get("q") or [""])[0][:100]))
                if u.path == "/api/evaluation": return self._send(200, state.evaluation())
                if u.path == "/api/feedback.csv":
                    return self._send(200, state.feedback_csv(), "text/csv", {"Content-Disposition": 'attachment; filename="feedback.csv"'})
            except Exception as e:
                return self._send(500, {"error": f"Server error: {e}"})
            rel = "index.html" if u.path in ("/", "") else u.path.lstrip("/")
            f = (STATIC / rel).resolve()
            if STATIC.resolve() not in f.parents or not f.is_file():
                return self._send(404, {"error": "not found"})
            self._send(200, f.read_bytes(), mimetypes.guess_type(f.name)[0] or "application/octet-stream")

        def do_POST(self):
            routes = {"/api/translate": state.translate, "/api/batch": state.batch, "/api/explain": state.explain, "/api/feedback": state.feedback}
            fn = routes.get(urlparse(self.path).path)
            if not fn: return self._send(404, {"error": "not found"})
            try:
                n = int(self.headers.get("Content-Length") or 0)
                if n > MAX_BODY: return self._send(413, {"error": "Request too large"})
                d = json.loads(self.rfile.read(n) or b"{}")
                if not isinstance(d, dict): raise ValueError("bad request")
                self._send(200, fn(d))
            except (ValueError, json.JSONDecodeError) as e:
                self._send(400, {"error": str(e)})
            except Exception as e:
                self._send(500, {"error": f"Model error: {e}"})
    return H

def serve(engine, host="127.0.0.1", port=7860, open_browser=True, dictionary=None):
    state = State(engine, dictionary)
    httpd = ThreadingHTTPServer((host, port), make_handler(state))
    url = f"http://{host}:{port}"
    print(f"AcehTranslate AI: {url}  (stop with Ctrl+C)")
    if open_browser:
        import webbrowser; threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
