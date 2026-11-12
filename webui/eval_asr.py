"""Measure the voice model on real Acehnese speech:  python -m webui.eval_asr   (needs: pip install soundfile)

Test data: the Acehnese clips of the LibriVox Indonesia *test* split (Universal Declaration of Human Rights read aloud, one reader,
public domain, indonesian-nlp/librivox-indonesia on Hugging Face). Both texts are normalized like the translation input
(old spellings dj/nj/tj, quotes, case, punctuation) before comparing, so the score is not hurt by spelling conventions alone.
Prints WER and CER. The small size (about 10 clips, one reader, formal read speech) means it is a sanity check, not a benchmark."""
import csv, gzip, io, re, tarfile, tempfile, urllib.request
from pathlib import Path
from acehid.normalize import normalize
from webui import asr

BASE = "https://huggingface.co/datasets/indonesian-nlp/librivox-indonesia/resolve/main/data/"

def _get(name, dest):
    urllib.request.urlretrieve(BASE + name, dest)

def edit_distance(a, b):
    d = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        prev, d[0] = d[0], i
        for j, y in enumerate(b, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (x != y))
    return d[-1]

def clean(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w' ]", " ", normalize(s)[0].lower())).strip()

def to_wav16k(mp3_path):
    import numpy as np, soundfile as sf, io, wave
    x, sr = sf.read(mp3_path, dtype="float32", always_2d=True)
    x = x.mean(axis=1)
    if sr != asr.SR:                                           # simple linear resampling is enough for a sanity check
        n = int(len(x) * asr.SR / sr); x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype("float32")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(asr.SR); w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    return buf.getvalue()

def main():
    work = Path(tempfile.mkdtemp(prefix="asr_eval_"))
    print("downloading the test clips (about 30 MB) ...")
    _get("metadata_test.csv.gz", work / "meta.csv.gz"); _get("audio_test.tgz", work / "audio.tgz")
    rows = list(csv.DictReader(io.TextIOWrapper(gzip.open(work / "meta.csv.gz"), encoding="utf-8")))
    ref = {r["path"].split("/")[-1]: r["sentence"] for r in rows if r["language"] == "ace"}
    rec, tw = asr.Recognizer(), [0, 0, 0, 0]
    with tarfile.open(work / "audio.tgz") as t:
        for m in t:
            name = m.name.split("/")[-1]
            if name not in ref or not m.isfile():
                continue
            t.extract(m, work / "x", filter="data")
            hyp = clean(rec.transcribe(to_wav16k(work / "x" / m.name))); rf = clean(ref[name])
            tw[0] += edit_distance(rf.split(), hyp.split()); tw[1] += len(rf.split()); tw[2] += edit_distance(rf, hyp); tw[3] += len(rf)
            print(f"REF: {rf}\nHYP: {hyp}\n")
    print(f"WER {tw[0] / tw[1]:.2f}   CER {tw[2] / tw[3]:.2f}   ({len(ref)} clips)")

if __name__ == "__main__":
    main()
