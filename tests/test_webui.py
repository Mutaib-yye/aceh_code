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
    s = J(call("/api/status"))[1]; assert s["model_id"] == "fake/model" and s["finetuned"] is False and s["voice"] is False
    req = urllib.request.Request(call.__closure__[0].cell_contents + "/api/translate", data=b"{bad", method="POST")
    with pytest.raises(urllib.error.HTTPError) as e: urllib.request.urlopen(req)
    assert e.value.code == 400
