import json, threading, urllib.request, pytest, pymupdf
from conftest import make_pdf, ACE
from acehid import extract, pipeline, dedupe
from acehid.common import key_hash, write_jsonl

import importlib.util
OCR_BACKENDS = [b for b in ("rapidocr", "rapidocr_onnxruntime") if importlib.util.find_spec(b)]

def test_digital_pdf_end_to_end(tmp_path):
    pdf = make_pdf(tmp_path / "h.pdf", [[ACE[i % 6], ACE[(i + 1) % 6]] for i in range(6)])
    pages, rows = pipeline.process_files([str(pdf)])
    assert len(pages) == 6 and all(p["method"] == "pdf_text" for p in pages)
    texts = [r["ace_raw"] for r in rows]
    assert not any("HIKAYAT CONTOH" in t for t in texts), "running header must be removed"
    assert any(r["screening"] == "KEEP" for r in rows)
    assert sum(r["dedup"] == "DUPLICATE_SELF" for r in rows) > 0, "pages repeat sentences on purpose"

def test_duplicates_against_reference_are_found_in_pdf(tmp_path):
    ref_p = tmp_path / "ref.jsonl"
    write_jsonl(ref_p, [{"src_file": "f", "line": 1, "ace_raw": ACE[0], "key": key_hash(ACE[0])}])
    ref = dedupe.build_ref(str(ref_p), cache=tmp_path / "c.pkl")
    pads = ["Ureueng nyan geujak u pasi.", "Gobnyan geubloe boh kayee.", "Aneuek miet jimeulakee bu.", "Ayah jijak u blang."]
    pdf = make_pdf(tmp_path / "h.pdf", [[pads[i], ACE[0] if i == 1 else ACE[4], pads[(i + 1) % 4]] for i in range(4)])
    _, rows = pipeline.process_files([str(pdf)], ref=ref)
    assert any(r["dedup"] == "DUPLICATE_ACEHX" for r in rows) and any(r["dedup"] == "unique" for r in rows)

@pytest.mark.skipif(not OCR_BACKENDS, reason="no OCR package installed")
@pytest.mark.parametrize("backend", OCR_BACKENDS)
def test_scanned_pdf_goes_through_ocr(tmp_path, monkeypatch, backend):
    monkeypatch.setattr(extract, "ocr_backend", lambda: backend); monkeypatch.setattr(extract, "_ocr", None)
    src = make_pdf(tmp_path / "t.pdf", [[ACE[1], ACE[3]]])
    img = pymupdf.open(str(src))[0].get_pixmap(dpi=200)
    doc = pymupdf.open(); pg = doc.new_page(); pg.insert_image(pg.rect, pixmap=img); doc.save(str(tmp_path / "scan.pdf"))
    pages = extract.extract_file(str(tmp_path / "scan.pdf"), "HIK_001")
    assert pages[0]["method"] == "ocr" and pages[0]["ocr_conf"] > 0.5
    assert "ateueh jeumala" in pages[0]["text"]
    # without OCR the page is flagged, not silently dropped
    assert extract.extract_file(str(tmp_path / "scan.pdf"), "HIK_001", ocr=False)[0]["method"] == "ocr_needed"

def test_txt_source(tmp_path):
    f = tmp_path / "s.txt"; f.write_text("\n".join(ACE[:4]), encoding="utf-8")
    pages, rows = pipeline.process_files([str(f)])
    assert pages[0]["method"] == "txt" and len(rows) >= 1

def test_web_app(tmp_path):
    from http.server import ThreadingHTTPServer
    from app import server
    srv = ThreadingHTTPServer(("127.0.0.1", 0), server.H); port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    try:
        assert b"Aceh" in urllib.request.urlopen(base + "/").read()
        st = json.load(urllib.request.urlopen(base + "/api/status")); assert "copy" in st["providers"] and st["recommended"] in st["providers"]
        bad_key = urllib.request.Request(base + "/api/set_key", data=json.dumps({"provider": "nope", "key": "x"}).encode())
        with pytest.raises(urllib.error.HTTPError) as e0: urllib.request.urlopen(bad_key)
        assert e0.value.code == 400
        req = urllib.request.Request(base + "/api/translate_text", data=json.dumps({"text": "Njang djipeugot löen\nTiep uroe tuhan jijak u pasi jimeuen ngon anoe", "provider": "copy"}).encode())
        items = json.load(urllib.request.urlopen(req))["items"]
        assert items[0]["ace_normalized"] == "Nyang jipeugot loen" and items[0]["status"] == "machine_draft"
        req = urllib.request.Request(base + "/api/translate_text", data=json.dumps({"text": "Lon\nTiep uroe tuhan jijak u pasi", "provider": "copy"}).encode())
        items = json.load(urllib.request.urlopen(req))["items"]
        assert items[0]["status"] == "too_short" and items[0]["ind"] == "" and items[1]["status"] == "machine_draft"
        req = urllib.request.Request(base + "/api/process?ocr=0", data="\n".join(ACE).encode(), headers={"X-Filename": "../../evil.txt"})
        j = json.load(urllib.request.urlopen(req)); assert j["summary"]["sentences"] >= 1
        req = urllib.request.Request(base + "/api/review_csv", data=json.dumps({"rows": j["rows"]}).encode())
        assert urllib.request.urlopen(req).status == 200
        bad = urllib.request.Request(base + "/api/process", data=b"x", headers={"X-Filename": "a.exe"})
        with pytest.raises(urllib.error.HTTPError) as e: urllib.request.urlopen(bad)
        assert e.value.code == 400
    finally:
        srv.shutdown()
