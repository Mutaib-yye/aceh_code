"""Penerjemah Aceh -> Indonesia: the hosted translator (Hugging Face Space, free CPU) - also runs locally: python app.py"""
import os
import gradio as gr
from core import Engine, BASE_MODEL, MAX_CHARS, accuracy_markdown, sources_text

EXAMPLES = [  # from the TEST sets (NusaX-MT, CC-BY-SA 4.0; Hikayat Abu Sammah held-out pages): never trained on, so the demo is honest
    "Le hai nyang jeuet tanyoe pubuet tapasoe watee kosong.",
    "Kebun raya bogor jeut tacok keu saboh tujuan destinasi wisata",
    "Nyoe adalah sop stengkel termangat di Aceh Tamiang.",
    "Aplikasi google maps cukop meupaedah, that pueh loen pakek!",
    "Olahraga malam uroe jeuet keu pilehan keu tapasoe watee luweueng",
    "Nabi Yusuf bala nyang that, deungon aduen raja lahud",
]

CSS = """
.gradio-container {max-width: 1080px !important; margin: 0 auto !important;}
#hero {text-align: center; padding: 26px 8px 6px;}
#hero h1 {font-size: clamp(1.6rem, 4vw, 2.3rem); font-weight: 800; letter-spacing: -0.02em; margin: 0; line-height: 1.15;}
#hero h1 span {background: linear-gradient(90deg, #0d9488, #2563eb); -webkit-background-clip: text; background-clip: text; color: transparent;}
#hero p {margin: .45rem 0 0; opacity: .72; font-size: 1rem;}
.pill {display: inline-block; margin-top: 12px; padding: 3px 12px; border-radius: 999px; font-size: .78rem; font-weight: 600;}
.pill.ok {background: rgba(13,148,136,.13); color: #0f766e;} .pill.base {background: rgba(234,179,8,.16); color: #a16207;}
.dark .pill.ok {color: #5eead4;} .dark .pill.base {color: #fde047;}
#panes {gap: 14px !important; align-items: stretch;}
#panes textarea {font-size: 1.08rem !important; line-height: 1.55 !important;}
#out textarea {background: rgba(13,148,136,.05) !important;}
#go {min-height: 50px; font-size: 1.05rem; font-weight: 700;}
#notes {font-size: .92rem;} #notes p {margin: 0;}
.hint {opacity: .62; font-size: .85rem; text-align: center; margin-top: 2px;}
#foot {opacity: .62; font-size: .82rem; text-align: center; padding: 10px 0 18px;}
"""
SHORTCUT_JS = """() => { document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { const b = document.querySelector('#go'); if (b) b.click(); } }); }"""

def build_ui(engine):
    finetuned = engine.info is not None and "tests" in (engine.info or {})
    pill = ('<span class="pill ok">Model khusus Aceh (fine-tuned)</span>' if finetuned
            else '<span class="pill base">Model dasar NLLB-200 · belum di-fine-tune</span>')

    def run(text):
        out, details, notes = engine.translate(text)
        return out, gr.Markdown(value="\n\n".join(f"⚠️ {n}" for n in notes), visible=bool(notes)), details

    with gr.Blocks(title="Penerjemah Aceh → Indonesia") as demo:
        gr.HTML(f"""<div id="hero"><h1>Penerjemah <span>Aceh → Indonesia</span></h1>
            <p>Terjemahkan bahasa Aceh ke bahasa Indonesia · Acehnese → Indonesian translator</p>{pill}</div>""")
        with gr.Row(elem_id="panes", equal_height=True):
            inp = gr.Textbox(label="Bahasa Aceh", placeholder="Tulis atau tempel teks bahasa Aceh di sini…\nType or paste Acehnese text here…",
                             lines=7, max_lines=20, max_length=MAX_CHARS, autofocus=True, elem_id="inp", min_width=320)
            out = gr.Textbox(label="Bahasa Indonesia", lines=7, max_lines=20, interactive=False, buttons=["copy"], elem_id="out", min_width=320,
                             placeholder="Terjemahan muncul di sini · The translation appears here")
        with gr.Row():
            go = gr.Button("Terjemahkan · Translate", variant="primary", scale=3, elem_id="go", min_width=220)
            clear = gr.Button("Hapus · Clear", variant="secondary", scale=1, min_width=120)
        gr.HTML('<div class="hint">Tip: Ctrl/⌘ + Enter untuk menerjemahkan · one sentence per line works best</div>')
        notes = gr.Markdown(visible=False, elem_id="notes")
        gr.Examples(examples=[[e] for e in EXAMPLES], inputs=[inp], label="Contoh · Examples")
        with gr.Accordion("Detail per kalimat · Sentence by sentence", open=False):
            gr.Markdown("Ejaan dinormalisasi seperti data latih (mis. *löen → loen*, *njang → nyang*) sebelum diterjemahkan.")
            details = gr.Dataframe(headers=["Bahasa Aceh", "Dinormalisasi", "Bahasa Indonesia"], datatype=["str", "str", "str"],
                                   interactive=False, wrap=True)
        with gr.Accordion("Seberapa akurat? · How accurate is it?", open=False):
            gr.Markdown(accuracy_markdown(engine.info, engine.model_id))
            gr.Markdown("Terjemahan mesin tidak pernah 100 % sempurna. Untuk teks penting, mintalah penutur bahasa Aceh memeriksanya. "
                        "Nama orang, gelar (Teungku, Cut, Po) dan nama tempat sebaiknya tetap seperti aslinya.")
        trained = f"fine-tuned on {sources_text(engine.info)}" if finetuned else "base model"
        gr.HTML(f'<div id="foot">Model: Meta NLLB-200 (CC-BY-NC 4.0), {trained} · '
                'Universitas Syiah Kuala research project · non-commercial use</div>')
        go.click(run, inp, [out, notes, details], api_name="translate")
        inp.submit(run, inp, [out, notes, details])
        clear.click(lambda: ("", "", gr.Markdown(value="", visible=False), []), None, [inp, out, notes, details])
    return demo

def launch_kwargs():
    theme = gr.themes.Soft(primary_hue="teal", secondary_hue="blue", neutral_hue="slate",
                           font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"])
    return dict(theme=theme, css=CSS, js=SHORTCUT_JS)

if __name__ == "__main__":
    try:
        engine = Engine()
    except Exception as e:                                   # wrong/missing MODEL_ID: still serve, with the base model
        print(f"could not load {os.environ.get('MODEL_ID')!r} ({e}); falling back to {BASE_MODEL}")
        engine = Engine(BASE_MODEL)
    build_ui(engine).queue(default_concurrency_limit=1, max_size=40).launch(**launch_kwargs())
