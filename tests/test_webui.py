"""AcehTranslate AI web app (webui/): API behaviour with a fake engine (no model, no download) and the dictionary lookup."""
import json, threading, urllib.request, urllib.error, pytest
from http.server import ThreadingHTTPServer
from webui import server
from acehid.dictionary import Dictionary

CSV = ('input,target,error_category,error_type,severity,source,wer,translate_ind,sentiment\n'
       'abaih,abaih,none,none,none,"Kamus (1985), hlm. 1, PDF hlm. 27; ekstraksi otomatis belum validasi penuh",0,nama laki-laki,neutral\n'
       'abaih,abaih,none,none,none,"Kamus (1985), hlm. 1; ekstraksi otomatis belum validasi penuh",0,memarang miring,neutral\n'
       "'ab,'ab,none,none,none,\"Kamus (1985), hlm. 1; bukan validasi menyeluruh kamus\",0,menyuap nasi,neutral\n"
       'daih,"daih, deih",none,none,none,"Kamus (1985), hlm. 5; ekstraksi otomatis belum validasi penuh",0,sumbu lampu,neutral\n')

class FakeEngine:
    model_id, info, beams = "fake/model", None, 4
    def translate(self, text, normalize_input=True):
        lines = text.splitlines()
        det = [[l, l.lower() if normalize_input else l, "ID:" + l] for l in lines]
        return "\n".join(d[2] for d in det), det, []
    def alternatives(self, s, n=2): return ["alt1 " + s, "alt2 " + s][:n]
    def translate_lines(self, lines, normalize_input=True): return ["ID:" + l if l else "" for l in lines]
    def explain(self, s, ind=None): return ["▁" + s], ["▁" + (ind or "")]

@pytest.fixture
def app(tmp_path):
    csv = tmp_path / "k.csv"; csv.write_text(CSV, encoding="utf-8")
    state = server.State(FakeEngine(), Dictionary(csv), tmp_path / "fb" / "feedback.jsonl")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(state))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    def call(path, body=None):
        req = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r: return r.status, r.read()
        except urllib.error.HTTPError as e: return e.code, e.read()
    yield call, state
    httpd.shutdown(); httpd.server_close()

def J(r): return r[0], json.loads(r[1])

def test_page_and_assets_served(app):
    call, _ = app
    code, html = call("/"); assert code == 200 and b"AcehTranslate" in html
    assert call("/app.js")[0] == 200 and call("/style.css")[0] == 200
    assert call("/../server.py")[0] == 404 and call("/nothing")[0] == 404

def test_translate_and_errors(app):
    call, _ = app
    code, d = J(call("/api/translate", {"text": "Lon ka jak"})); assert code == 200 and d["translation"] == "ID:Lon ka jak" and d["alternatives"] == []
    code, d = J(call("/api/translate", {"text": "Lon", "alternatives": True})); assert d["alternatives"] == ["alt1 lon", "alt2 lon"]
    code, d = J(call("/api/translate", {"text": "a\nb", "alternatives": True})); assert d["alternatives"] == [] and d["notes"]
    code, d = J(call("/api/translate", {"text": "Lon", "normalize": False})); assert d["normalized"] == "Lon" and d["normalize"] is False
    assert J(call("/api/translate", {"text": "   "}))[0] == 400
    assert J(call("/api/translate", {"text": "x" * 5001}))[0] == 400
    assert call("/api/translate", None)[0] in (200, 404, 400)           # GET on a POST route must not crash the server

def test_batch_keeps_order_and_blank_lines(app):
    call, _ = app
    code, d = J(call("/api/batch", {"text": "satu\n\ndua\ntiga\n\n"}))
    assert code == 200 and [r["tgt"] for r in d["rows"]] == ["ID:satu", "", "ID:dua", "ID:tiga"]
    assert J(call("/api/batch", {"text": ""}))[0] == 400
    assert J(call("/api/batch", {"text": "\n".join(["x"] * 201)}))[0] == 400

def test_dictionary_lookup_search_and_not_found(app):
    call, _ = app
    d = J(call("/api/dictionary?q=Abaih"))[1]; assert d["found"] and len(d["exact"]) == 2 and d["exact"][0]["status"] == "unverified"
    assert J(call("/api/dictionary?q=ab"))[1]["exact"][0]["meaning"] == "menyuap nasi"            # apostrophe ignored
    assert J(call("/api/dictionary?q=deih"))[1]["exact"][0]["word"] == "daih"                     # variants are searchable
    assert [e["word"] for e in J(call("/api/dictionary?q=aba"))[1]["prefix"]] == ["abaih", "abaih"]
    assert J(call("/api/dictionary?q=lampu"))[1]["meaning"][0]["word"] == "daih"                  # reverse lookup
    d = J(call("/api/dictionary?q=tidakada"))[1]; assert d["found"] is False

def test_dictionary_missing_file_is_handled(tmp_path):
    state = server.State(FakeEngine(), Dictionary(tmp_path / "none.csv"), tmp_path / "f.jsonl")
    assert state.dictionary_search("abaih") == {"loaded": False, "q": "abaih"} and state.status()["dictionary"]["loaded"] is False

def test_explain_uses_dictionary_and_tokens(app):
    call, _ = app
    d = J(call("/api/explain", {"text": "abaih tidak", "translation": "x"}))[1]
    w = {x["word"]: x for x in d["words"]}; assert w["abaih"]["entries"] and w["tidak"]["entries"] == [] and d["src_tokens"]

def test_feedback_needs_consent_for_text(app):
    call, state = app
    assert J(call("/api/feedback", {"rating": "up", "source": "SECRET", "translation": "T"}))[1]["stored_text"] is False
    assert J(call("/api/feedback", {"rating": "down", "consent": True, "source": "S", "translation": "T", "correction": "C", "error_type": "dialect"}))[1]["stored_text"] is True
    recs = [json.loads(l) for l in state.feedback_path.read_text(encoding="utf-8").splitlines()]
    assert "source" not in recs[0] and "SECRET" not in state.feedback_path.read_text(encoding="utf-8")
    assert recs[1]["correction"] == "C" and recs[1]["review"] == "pending" and recs[1]["error_type"] == "dialect"
    assert J(call("/api/feedback", {"rating": "meh"}))[0] == 400
    csv_text = call("/api/feedback.csv")[1].decode(); assert csv_text.startswith("time,model,rating") and "dialect" in csv_text

def test_evaluation_only_shows_real_scores(app):
    call, state = app
    assert J(call("/api/evaluation"))[1] == {"available": False}
    state.engine.info = {"train_pairs": 10, "tests": {"nusax": {"n": 400, "base": {"chrF++": 40.1}, "finetuned": {"chrF++": 55.5}}}}
    d = J(call("/api/evaluation"))[1]; assert d["available"] and d["rows"][0]["model"] == 55.5 and d["rows"][0]["set"].startswith("NusaX")

def test_status_and_bad_json(app):
    call, _ = app
    s = J(call("/api/status"))[1]; assert s["model_id"] == "fake/model" and s["finetuned"] is False and s["voice"]["language"] == "ace"
    req = urllib.request.Request(call.__closure__[0].cell_contents + "/api/translate", data=b"{bad", method="POST")
    with pytest.raises(urllib.error.HTTPError) as e: urllib.request.urlopen(req)
    assert e.value.code == 400

# ---- voice input -------------------------------------------------------------------------------------------------------
import io, wave, struct, math
from webui import asr

def _wav(seconds=1.0, sr=16000, amp=0.3, channels=1, width=2):
    n = int(seconds * sr); buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels); w.setsampwidth(width); w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", int(amp * 32767 * math.sin(i / 20))) * channels for i in range(n)))
    return buf.getvalue()

class FakeRecognizer(asr.Recognizer):
    """Real audio validation (Recognizer.transcribe), fake speech model."""
    def load(self):
        self.model = object()
        self.torch = type("T", (), {"inference_mode": staticmethod(lambda: __import__("contextlib").nullcontext()), "argmax": staticmethod(lambda x, dim: [0])})
        self.processor = type("P", (), {"__call__": lambda self, a, sampling_rate, return_tensors: {}, "decode": lambda self, ids: "teks dari suara"})()
        self.model = lambda **kw: type("O", (), {"logits": None})()

@pytest.fixture
def voice(tmp_path):
    state = server.State(FakeEngine(), Dictionary(tmp_path / "none.csv"), tmp_path / "f.jsonl", recognizer=FakeRecognizer())
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.make_handler(state))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    def post(data):
        req = urllib.request.Request(base + "/api/transcribe", data=data, headers={"Content-Type": "audio/wav"})
        try:
            with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e: return e.code, json.loads(e.read())
    yield post, state
    httpd.shutdown(); httpd.server_close()

def test_transcribe_returns_text_and_status_reports_the_model(voice):
    post, state = voice
    assert post(_wav()) == (200, {"text": "teks dari suara"})
    v = state.status()["voice"]; assert v["model"] == "facebook/mms-1b-all" and v["language"] == "ace" and v["loaded"] is True

@pytest.mark.parametrize("data,why", [
    (b"not a wav", "WAV"), (_wav(sr=44100), "16 kHz"), (_wav(channels=2), "mono"), (_wav(seconds=0.1), "pendek"),
    (_wav(amp=0.0), "Tidak ada suara"), (_wav(seconds=91), "panjang")])
def test_transcribe_rejects_bad_audio_with_a_clear_message(voice, data, why):
    post, _ = voice
    code, d = post(data); assert code in (400, 413) and (why in d["error"] or code == 413)

def test_wav_helper_roundtrip():
    a, sr = asr.wav_to_float(_wav(0.5, amp=0.5)); assert sr == 16000 and len(a) == 8000 and 0.4 < float(abs(a).max()) <= 0.5

# ---- the real Engine code paths (alternatives, batch, no-normalize, explain) on a tiny local model ------------------------
@pytest.fixture(scope="module")
def tiny_engine(tmp_path_factory):
    pytest.importorskip("torch"); spm = pytest.importorskip("sentencepiece")
    from transformers import NllbTokenizer, M2M100Config, M2M100ForConditionalGeneration
    import sys, importlib.util
    from acehid.common import ROOT
    tmp = tmp_path_factory.mktemp("tiny")
    (tmp / "c.txt").write_text("Gobnyan geujak u pasi\nDia pergi ke pantai\nAneuek miet\nAnak kecil\nLon ka jak u blang\nSaya sudah pergi", encoding="utf-8")
    spm.SentencePieceTrainer.train(input=str(tmp / "c.txt"), model_prefix=str(tmp / "sp"), vocab_size=40, model_type="bpe", hard_vocab_limit=False, minloglevel=2)
    tok = NllbTokenizer(vocab_file=str(tmp / "sp.model"), src_lang="ace_Latn", tgt_lang="ind_Latn")
    cfg = M2M100Config(vocab_size=len(tok), d_model=16, encoder_layers=1, decoder_layers=1, encoder_attention_heads=2, decoder_attention_heads=2,
                       encoder_ffn_dim=32, decoder_ffn_dim=32, max_position_embeddings=600, pad_token_id=tok.pad_token_id,
                       bos_token_id=tok.bos_token_id, eos_token_id=tok.eos_token_id, decoder_start_token_id=tok.eos_token_id)
    d = tmp / "m"; M2M100ForConditionalGeneration(cfg).save_pretrained(d); tok.save_pretrained(d)
    spec = importlib.util.spec_from_file_location("core", ROOT / "space/core.py"); core = importlib.util.module_from_spec(spec); sys.modules["core"] = core; spec.loader.exec_module(core)
    return core.Engine(str(d), beams=4)

def test_engine_alternatives_batch_and_no_normalize(tiny_engine):
    e = tiny_engine
    main = e.translate_sentences(["gobnyan geujak u pasi"])[0]
    alts = e.alternatives("gobnyan geujak u pasi", 2)
    assert len(alts) <= 2 and main not in alts and len(set(alts)) == len(alts)
    rows = e.translate_lines(["gobnyan geujak", "", "lon ka jak u blang"]); assert len(rows) == 3 and rows[1] == "" and all(isinstance(r, str) for r in rows)
    out, det, _ = e.translate("Njang djipeugot", normalize_input=False); assert det[0][1] == "Njang djipeugot"
    out, det, _ = e.translate("Njang djipeugot"); assert det[0][1] == "Nyang jipeugot"
    src, tgt = e.explain("lon ka jak", "saya"); assert src and tgt

def test_whole_app_with_a_real_engine(tiny_engine, tmp_path):
    state = server.State(tiny_engine, Dictionary(tmp_path / "none.csv"), tmp_path / "f.jsonl", recognizer=FakeRecognizer())
    d = state.translate({"text": "Gobnyan geujak u pasi", "alternatives": True}); assert isinstance(d["translation"], str) and len(d["alternatives"]) <= 2
    b = state.batch({"text": "lon ka jak\n\ngobnyan geujak"}); assert [r["src"] for r in b["rows"]] == ["lon ka jak", "", "gobnyan geujak"] and b["rows"][1]["tgt"] == ""
    x = state.explain({"text": "lon ka jak", "translation": d["translation"]}); assert x["src_tokens"] and x["words"][0]["word"] == "lon"
