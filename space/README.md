---
title: Penerjemah Aceh Indonesia
emoji: 🌊
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 6.29.1
python_version: "3.12"
app_file: app.py
pinned: true
license: cc-by-nc-4.0
short_description: Acehnese to Indonesian translator (fine-tuned NLLB-200)
---

# Penerjemah Aceh → Indonesia

Acehnese → Indonesian machine translation. Model: Meta NLLB-200 distilled 600M, fine-tuned on human-translated pairs
(NusaX-MT, FLORES-200). Set the Space variable `MODEL_ID` to the fine-tuned model repo (the Colab notebook does this);
without it the base NLLB-200 model is used. Accuracy on held-out test sets is shown in the app.

Code: https://github.com/Mutaib-yye/aceh_code (folder `space/`). Non-commercial use (NLLB weights are CC-BY-NC 4.0).
