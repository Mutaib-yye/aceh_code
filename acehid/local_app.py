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

def load_space_app():
    space = ROOT / "space"
    sys.path.insert(0, str(space))                                  # space/app.py does `from core import ...`
    spec = importlib.util.spec_from_file_location("space_app", space / "app.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

def run(model=None, share=False, port=7860, open_browser=True, **launch_extra):
    model = model or ensure_model()
    print(f"model: {model}")
    print(f"starting the app at http://127.0.0.1:{port}  (stop with Ctrl+C)")
    return load_space_app().start(model, share=share, server_name="127.0.0.1", server_port=port, inbrowser=open_browser, **launch_extra)
