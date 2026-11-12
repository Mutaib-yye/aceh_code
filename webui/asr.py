"""Voice input: Acehnese speech -> text with Meta's MMS (facebook/mms-1b-all, language adapter "ace", CC-BY-NC 4.0).

Runs on this computer: audio is never sent anywhere. The model (about 4 GB) is downloaded from Hugging Face the first time the
microphone is used, not at start-up, and then cached. The browser records, resamples to 16 kHz mono and sends a WAV file."""
import io, wave, threading

MODEL_ID, LANG = "facebook/mms-1b-all", "ace"
MAX_SECONDS = 90
SR = 16000

def wav_to_float(data):
    """16-bit PCM WAV bytes -> (float32 numpy array in [-1, 1], sample_rate). Mono only; ValueError for anything else."""
    import numpy as np
    try:
        with wave.open(io.BytesIO(data)) as w:
            ch, width, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            raw = w.readframes(n)
    except (wave.Error, EOFError) as e:
        raise ValueError(f"Bukan file WAV yang valid · not a valid WAV file ({e})")
    if width != 2 or ch != 1:
        raise ValueError("Audio harus WAV 16-bit mono · audio must be 16-bit mono WAV")
    return np.frombuffer(raw, dtype="<i2").astype("float32") / 32768.0, sr

class Recognizer:
    """Lazy MMS wrapper. load() is slow the first time (download); transcribe() is one clip at a time."""
    def __init__(self, model_id=MODEL_ID, lang=LANG):
        self.model_id, self.lang = model_id, lang
        self.model = self.processor = None
        self.lock = threading.Lock()

    @property
    def loaded(self):
        return self.model is not None

    def load(self):
        if self.loaded:
            return
        import torch
        from transformers import Wav2Vec2ForCTC, AutoProcessor
        self.torch = torch
        self.processor = AutoProcessor.from_pretrained(self.model_id, target_lang=self.lang)
        self.model = Wav2Vec2ForCTC.from_pretrained(self.model_id, target_lang=self.lang, ignore_mismatched_sizes=True).float().eval()

    def transcribe(self, data):
        audio, sr = wav_to_float(data)
        if sr != SR:
            raise ValueError(f"Audio harus 16 kHz (diterima {sr} Hz) · audio must be 16 kHz")
        if len(audio) < SR // 4:
            raise ValueError("Rekaman terlalu pendek · the recording is too short")
        if len(audio) > MAX_SECONDS * SR:
            raise ValueError(f"Rekaman terlalu panjang (maksimal {MAX_SECONDS} detik) · the recording is too long")
        if float(abs(audio).max()) < 0.005:
            raise ValueError("Tidak ada suara terdeteksi · no sound detected: check the microphone")
        with self.lock:
            self.load()
            inputs = self.processor(audio, sampling_rate=SR, return_tensors="pt")
            with self.torch.inference_mode():
                logits = self.model(**inputs).logits
            ids = self.torch.argmax(logits, dim=-1)[0]
            return self.processor.decode(ids).strip()
