"""Run the translator app on this computer: http://127.0.0.1:7860   (python -m acehid app, or ./run_app.sh)

The trained model is looked for, in this order, and kept in models/ace-id-nllb/ so it is fetched only once:
  1. models/ace-id-nllb/            (already here)
  2. ~/Downloads/ace-id-nllb*.zip   (the zip downloaded from the Colab training notebook)
  3. your Hugging Face account      (<you>/ace-id-nllb, saved there by the Colab notebook; needs your token once)
  4. otherwise the base NLLB-200 model (not fine-tuned), so the app still works.
After the first run everything is on this computer and the app works offline."""
import os, sys, shutil, zipfile, importlib.util
from pathlib import Path
from .common import ROOT

LOCAL = ROOT / "models/ace-id-nllb"
BASE_MODEL = "facebook/nllb-200-distilled-600M"

def _has_model(d):
    return (Path(d) / "config.json").exists()

def _from_zip(target, search=(Path.home() / "Downloads",)):
    for folder in search:
        for z in sorted(Path(folder).glob("ace-id-nllb*.zip"), key=lambda p: p.stat().st_mtime, reverse=True):
            print(f"unpacking {z} ...")
            target.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(z) as f:
                for m in f.infolist():
                    name = Path(m.filename).name                       # flatten: the zip may contain a top folder
                    if m.is_dir() or not name:
                        continue
                    with f.open(m) as src, open(target / name, "wb") as dst:
                        shutil.copyfileobj(src, dst, 1 << 20)
            if _has_model(target):
                return True
    return False

def _from_hub(target, token, repo=None):
    from huggingface_hub import HfApi, snapshot_download
    repo = repo or f"{HfApi(token=token).whoami()['name']}/ace-id-nllb"
    print(f"downloading your model {repo} (about 1.2 GB, only this once) ...")
    snapshot_download(repo, local_dir=str(target), token=token)
    return _has_model(target)

def ensure_model(target=LOCAL, ask=input, zip_search=(Path.home() / "Downloads",)):
    """-> path or model id to load. Never raises: falls back to the base model."""
    target = Path(target)
    if _has_model(target):
        return str(target)
    try:
        if _from_zip(target, zip_search):
            return str(target)
    except Exception as e:
        print(f"could not unpack the zip ({e})")
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        print("Your trained model is not on this computer yet.")
        token = ask("Paste your Hugging Face token to download it once (or just press Enter to use the base model): ").strip()
    if token:
        try:
            if _from_hub(target, token):
                return str(target)
        except Exception as e:
            print(f"could not download your model ({str(e).splitlines()[0]})")
    print("Using the base NLLB-200 model (not fine-tuned). The first start downloads it once (about 2.5 GB).")
    return BASE_MODEL

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod

def load_space_app():
    """space/app.py by path (the repo also has an `app` package, the local pipeline web app); its `from core import` finds core."""
    _load("core", ROOT / "space/core.py")
    return _load("space_app", ROOT / "space/app.py")

def run(model=None, share=False, port=7860, open_browser=True, **launch_extra):
    model = model or ensure_model()
    if Path(model).is_dir():
        os.environ.setdefault("HF_HUB_OFFLINE", "1")                # model is on this computer: never touch the network
    print(f"model: {model}")
    print(f"starting the app at http://127.0.0.1:{port}  (stop with Ctrl+C)")
    return load_space_app().start(model, share=share, server_name="127.0.0.1", server_port=port, inbrowser=open_browser, **launch_extra)

def run_web(model=None, port=7860, open_browser=True):
    """The AcehTranslate AI interface (webui/): plain Python server, no Gradio needed. Same model lookup as run()."""
    model = model or ensure_model()
    # No HF_HUB_OFFLINE here (unlike run()): a model folder loads without the network anyway, and the voice model must be able to
    # download itself the first time the microphone is used.
    _load("core", ROOT / "space/core.py")
    core = sys.modules["core"]
    try:
        engine = core.Engine(model)
    except Exception as e:
        print(f"could not load {model!r} ({e}); falling back to {BASE_MODEL}")
        engine = core.Engine(BASE_MODEL)
    from webui.server import serve
    try:
        core.ensure_glossary()                      # the dictionary list: data/glossary/, downloaded from the repo once if missing
    except Exception:
        pass
    print(f"model: {model}")
    return serve(engine, "127.0.0.1", port, open_browser)

def doctor(port=7860, model=None):
    """`./run_app.sh --doctor` / `run_app.bat --doctor`: a checklist to paste into a message when the app does not start."""
    import platform, shutil, socket, urllib.request
    rows = []
    def add(ok, name, detail=""):
        rows.append(f"[{'OK' if ok else '!!'}] {name}" + (f": {detail}" if detail else ""))
    add(sys.version_info >= (3, 10), "Python 3.10+", f"{platform.python_version()} on {platform.system()} {platform.machine()}")
    for mod in ("torch", "transformers", "sentencepiece", "huggingface_hub", "numpy"):
        try:
            m = __import__(mod); add(True, mod, getattr(m, "__version__", ""))
        except Exception as e:
            add(False, mod, f"not installed ({e.__class__.__name__}); re-run the launcher to install")
    target = Path(model) if model else LOCAL
    zips = list((Path.home() / "Downloads").glob("ace-id-nllb*.zip")) if (Path.home() / "Downloads").exists() else []
    add(True, "trained model",
        f"found in {target}" if _has_model(target) else ("zip in Downloads (will be unpacked)" if zips else
        "not on this computer yet (normal before the first start): the app asks for the Hugging Face token and downloads it once"))
    from .dictionary import Dictionary
    d = Dictionary(); add(d.loaded, "dictionary", f"{len(d.entries)} entries from {d.path.name}" if d.loaded else "word list not found")
    free = shutil.disk_usage(ROOT).free / 1e9
    add(free > 6, "free disk space", f"{free:.1f} GB (model 1.2 GB; voice model +4 GB; packages ~3 GB)")
    try:
        urllib.request.urlopen(urllib.request.Request("https://huggingface.co", method="HEAD"), timeout=8); add(True, "internet to huggingface.co")
    except Exception as e:
        add(False, "internet to huggingface.co", f"{e.__class__.__name__}: needed once for the model and for the voice model")
    try:
        from huggingface_hub import try_to_load_from_cache
        cached = isinstance(try_to_load_from_cache("facebook/mms-1b-all", "config.json"), str)
        add(True, "voice model (Meta MMS)", "already downloaded" if cached else "not downloaded yet: downloads (about 4 GB) the first time the microphone is used")
    except Exception:
        add(True, "voice model (Meta MMS)", "will download on first use")
    with socket.socket() as s:
        add(s.connect_ex(("127.0.0.1", port)) != 0, f"port {port} free", "" if s.connect_ex(("127.0.0.1", port)) != 0 else "something is already running there: close it or use --port 7861")
    add((ROOT / "webui/static/index.html").exists(), "app files", str(ROOT))
    print("\n".join(rows)); print("\nIf any line shows [!!], copy this whole list into your message.")
    return all(r.startswith("[OK]") for r in rows)
