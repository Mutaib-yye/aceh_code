const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");
const { applyTheme } = require("/root/.claude/skills/synced/7e83ec5a-8963-4c73-833d-1c31467567c1_d76b676b-3297-467f-b57d-39709cd2abe1/pptx/scripts/apply_theme.js");

const OUT = process.argv[2] || "deck.pptx";
const THEME = {
  name: "Aceh Translator",
  headFontFace: "Georgia",
  bodyFontFace: "Arial",
  colors: { dk1: "12303A", lt1: "FFFFFF", dk2: "0B3C49", lt2: "EAF4F4", accent1: "0D9488", accent2: "E9A23B", accent3: "2563EB",
            accent4: "D9482B", accent5: "4F6F7A", accent6: "9DB4BB", hlink: "0D9488", folHlink: "4F6F7A" },
};
const HEX = { ink: "12303A", deep: "0B3C49", tint: "EAF4F4", teal: "0D9488", gold: "E9A23B", slate: "4F6F7A", mist: "9DB4BB", white: "FFFFFF" };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "Acehnese to Indonesian Neural Translator";
pres.author = "Mutaib Rather and team";
const C = pres.SchemeColor;

// ---------- icons ----------
async function icon(name, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(fa[name], { color: "#" + color, size: String(size) }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

// ---------- layouts ----------
pres.defineSlideMaster({
  title: "TITLE", background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.0, w: 7.8, h: 2.4, fontSize: 44, bold: true, color: C.background1, margin: 0, valign: "top", align: "left" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 4.6, w: 7.6, h: 1.0, fontSize: 22, color: C.background2, margin: 0, valign: "top" }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT", background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.5, w: 12.13, h: 0.85, fontSize: 36, bold: true, color: C.text1, margin: 0, valign: "middle", align: "left" }, text: "" } },
    { text: { text: "Acehnese → Indonesian neural translator  ·  Midterm presentation", options: { x: 0.6, y: 7.05, w: 7, h: 0.3, fontSize: 10, color: C.accent5, margin: 0 } } },
  ],
  slideNumber: { x: 12.1, y: 7.05, w: 0.6, h: 0.3, fontSize: 10, color: C.accent5, align: "right" },
});

// ---------- helpers ----------
function ctext(s, text, o) { s.addText(text, Object.assign({ margin: 0, isTextBox: true, fontSize: 12, color: C.text1, valign: "middle" }, o)); }
function chartTitle(s, o) { if (o.title) { ctext(s, o.title, { x: o.x, y: o.y, w: o.w, h: 0.4, fontSize: 14, bold: true }); return o.y + 0.5; } return o.y; }
function hBars(s, o) {
  const top = chartTitle(s, o), n = o.labels.length, slot = (o.y + o.h - top) / n, bh = slot * 0.62, plotX = o.x + o.labelW + 0.15, plotW = o.w - o.labelW - 0.15 - 0.95;
  o.labels.forEach((lab, i) => {
    const cy = top + i * slot + (slot - bh) / 2, bw = Math.max(plotW * o.values[i] / o.max, 0.05), col = o.colors[i % o.colors.length];
    ctext(s, lab, { x: o.x, y: cy, w: o.labelW, h: bh, fontSize: o.fontSize, align: "right" });
    s.addShape(pres.shapes.RECTANGLE, { x: plotX, y: cy, w: bw, h: bh, fill: { color: col }, line: { color: col, width: 0 }, objectName: "Bar " + lab });
    ctext(s, o.fmt(o.values[i]), { x: plotX + bw + 0.1, y: cy, w: 0.85, h: bh, fontSize: o.fontSize, bold: true });
  });
}
function gridAndAxis(s, o, plotX, plotW, plotTop, plotBottom, lo, hi) {
  o.ticks.forEach((t) => {
    const yy = plotBottom - (plotBottom - plotTop) * (t - lo) / (hi - lo);
    s.addShape(pres.shapes.LINE, { x: plotX, y: yy, w: plotW, h: 0, line: { color: "D5E3E3", width: 0.75 }, objectName: "Gridline" });
    ctext(s, String(t), { x: o.x, y: yy - 0.15, w: plotX - o.x - 0.1, h: 0.3, fontSize: 11, align: "right", color: C.accent5 });
  });
}
function colChart(s, o) {
  const top = chartTitle(s, o), left = 0.6, legendH = 0.5, axisH = 0.5, plotX = o.x + left, plotW = o.w - left, plotTop = top + 0.35, plotBottom = o.y + o.h - legendH - axisH, plotH = plotBottom - plotTop;
  gridAndAxis(s, o, plotX, plotW, plotTop, plotBottom, 0, o.max);
  const gw = plotW / o.groups.length, bw = gw * 0.3;
  o.groups.forEach((g, gi) => {
    const gx = plotX + gi * gw;
    g.vals.forEach((v, si) => {
      const bh = plotH * v / o.max, bx = gx + gw / 2 - bw + si * bw;
      s.addShape(pres.shapes.RECTANGLE, { x: bx, y: plotBottom - bh, w: bw, h: bh, fill: { color: o.colors[si] }, line: { color: o.colors[si], width: 0 }, objectName: "Column " + g.label + " " + o.series[si] });
      ctext(s, v.toFixed(1), { x: bx - 0.2, y: plotBottom - bh - 0.34, w: bw + 0.4, h: 0.3, fontSize: 13, bold: true, align: "center" });
    });
    ctext(s, g.label, { x: gx, y: plotBottom + 0.08, w: gw, h: axisH - 0.1, fontSize: 13, align: "center" });
  });
  const ly = o.y + o.h - legendH + 0.1;
  o.series.forEach((nm, i) => {
    const lx = plotX + 0.4 + i * 3.1;
    s.addShape(pres.shapes.RECTANGLE, { x: lx, y: ly + 0.07, w: 0.22, h: 0.22, fill: { color: o.colors[i] }, line: { color: o.colors[i], width: 0 }, objectName: "Legend swatch" });
    ctext(s, nm, { x: lx + 0.32, y: ly, w: 2.7, h: 0.36, fontSize: 13 });
  });
}
function lineChart(s, o) {
  const top = chartTitle(s, o), left = 0.6, axisH = 0.5, plotX = o.x + left, plotW = o.w - left, plotTop = top + 0.45, plotBottom = o.y + o.h - axisH, plotH = plotBottom - plotTop, n = o.labels.length;
  gridAndAxis(s, o, plotX, plotW, plotTop, plotBottom, o.min, o.max);
  const pts = o.values.map((v, i) => [plotX + plotW * (i + 0.5) / n, plotBottom - plotH * (v - o.min) / (o.max - o.min)]);
  for (let i = 0; i < n - 1; i++) {
    const [x1, y1] = pts[i], [x2, y2] = pts[i + 1];
    s.addShape(pres.shapes.LINE, { x: x1, y: Math.min(y1, y2), w: x2 - x1, h: Math.abs(y2 - y1), flipV: y2 < y1, line: { color: o.color, width: 3.5 }, objectName: "Line segment " + (i + 1) });
  }
  pts.forEach(([px, py], i) => {
    s.addShape(pres.shapes.OVAL, { x: px - 0.11, y: py - 0.11, w: 0.22, h: 0.22, fill: { color: o.color }, line: { color: "FFFFFF", width: 1.5 }, objectName: "Point " + o.labels[i] });
    ctext(s, o.values[i].toFixed(2), { x: px - 0.6, y: py - 0.46, w: 1.2, h: 0.3, fontSize: 13, bold: true, align: "center" });
    ctext(s, o.labels[i], { x: px - 0.7, y: plotBottom + 0.1, w: 1.4, h: 0.35, fontSize: 12, align: "center" });
  });
}

const kicker = (s, t) => s.addText(t.toUpperCase(), { x: 0.6, y: 0.22, w: 8, h: 0.3, fontSize: 12, bold: true, color: C.accent1, margin: 0, charSpacing: 3, isTextBox: true, objectName: "Section label" });
const card = (s, x, y, w, h, name, fill) => s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill || C.background2 }, line: { color: fill || C.background2, width: 0 }, objectName: name || "Card" });
const T = (s, text, o) => s.addText(text, Object.assign({ margin: 0, isTextBox: true, color: C.text1, fontSize: 14, valign: "top" }, o));
async function badge(s, name, x, y, d, fillScheme, iconColor) {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fillScheme }, line: { color: fillScheme, width: 0 }, objectName: "Icon circle" });
  const pad = d * 0.27;
  s.addImage({ data: await icon(name, iconColor || HEX.white), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad, altText: name.replace("Fa", "") + " icon" });
}
function stat(s, x, y, w, num, label, o = {}) {
  T(s, num, { x, y, w, h: 0.8, fontSize: o.size || 44, bold: true, color: o.color || C.accent1, fontFace: "Georgia", objectName: "Stat " + label });
  T(s, label, { x, y: y + (o.size ? o.size / 60 : 0.8), w, h: o.lh || 0.6, fontSize: 14, color: C.accent5 });
}
const arrow = (s, x, y) => s.addShape(pres.shapes.RIGHT_ARROW, { x: x + 0.01, y, w: 0.22, h: 0.28, fill: { color: C.accent1 }, line: { color: C.accent1, width: 0 }, objectName: "Flow arrow" });
const section = (name) => pres.addSection({ title: name });
const header = (s, kick, title) => { kicker(s, kick); s.addText(title, { placeholder: "title" }); };
const tbl = (s, rows, o) => s.addTable(rows, Object.assign({ fontSize: 12, color: HEX.ink, border: { type: "solid", pt: 0.5, color: "CFE0E0" }, valign: "middle", margin: [0.04, 0.1, 0.04, 0.1] }, o));
const th = (t, align) => ({ text: t, options: { bold: true, color: HEX.white, fill: { color: HEX.teal }, fontSize: 11, align: align || "left" } });
const td = (t, o) => ({ text: t, options: Object.assign({ fontSize: 12 }, o || {}) });
const unusedChartText = { catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt", legendFontFace: "+mn-lt", titleFontFace: "+mj-lt" };

(async () => {
  // ================= 1 TITLE =================
  section("Introduction");
  let s = pres.addSlide({ masterName: "TITLE", sectionTitle: "Introduction" });
  s.addText("Acehnese → Indonesian neural translator", { placeholder: "title" });
  s.addText("Our data, techniques and results: a fine-tuned NLLB-200 model with a local app", { placeholder: "body" });
  T(s, "Mutaib Rather and team  ·  Universitas Syiah Kuala  ·  Midterm presentation  ·  23 October 2026", { x: 0.8, y: 6.5, w: 9, h: 0.4, fontSize: 14, color: C.accent6 });
  // motif: overlapping circles with stats
  for (const [x, y, d, col, tr] of [[8.9, 1.0, 3.6, HEX.teal, 25], [10.6, 3.2, 2.5, HEX.gold, 20], [8.6, 4.4, 2.2, HEX.teal, 45]]) {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: col, transparency: tr }, line: { color: col, width: 0 }, objectName: "Decor circle" });
  }
  T(s, "17,547", { x: 9.2, y: 2.05, w: 3.0, h: 0.8, fontSize: 40, bold: true, color: C.background1, fontFace: "Georgia", align: "center" });
  T(s, "training pairs", { x: 9.2, y: 2.85, w: 3.0, h: 0.4, fontSize: 16, color: C.background1, align: "center" });
  T(s, "57.1", { x: 10.6, y: 3.95, w: 2.5, h: 0.7, fontSize: 36, bold: true, color: C.text2, fontFace: "Georgia", align: "center" });
  T(s, "chrF++ on NusaX", { x: 10.6, y: 4.6, w: 2.5, h: 0.4, fontSize: 14, color: C.text2, align: "center" });
  s.addNotes("Introduce the project: we built a translator from Acehnese to Indonesian. We fine-tuned Meta's NLLB-200 model on 17,547 sentence pairs that we collected, cleaned and aligned from many sources, tested it on sentences it never saw, and put it in a local app. Today: the data, the techniques, the results and how the app works.");

  // ================= 2 AT A GLANCE =================
  section("Overview");
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Overview" });
  header(s, "Overview", "The project at a glance");
  const g = [["17,547", "training pairs from nine sources", HEX.teal], ["57.1", "chrF++ on NusaX, up from 38.7", HEX.teal], ["+36.9", "chrF++ gain on held-out hikayat verse", HEX.teal]];
  g.forEach(([n, l, c], i) => { const x = 0.6 + i * 4.1; card(s, x, 1.6, 3.9, 1.9, "Stat card"); T(s, n, { x: x + 0.3, y: 1.8, w: 3.3, h: 0.9, fontSize: 48, bold: true, color: C.accent1, fontFace: "Georgia" }); T(s, l, { x: x + 0.3, y: 2.75, w: 3.3, h: 0.6, fontSize: 15 }); });
  const gl = [["FaDatabase", "Data", "Nine sources: public corpora, scanned books, a thesis, team translations. Cleaned, aligned and leak-checked."],
              ["FaCogs", "Techniques", "OCR and alignment, pivot augmentation, fine-tuning, plus direct, transfer and neural translation compared."],
              ["FaFlask", "Evaluation", "Three held-out test sets scored with chrF++ and BLEU; the base model is the comparison."],
              ["FaLaptop", "Application", "A local, offline app with a dictionary panel that picks the best-fitting meaning of each word."]];
  for (let i = 0; i < 4; i++) {
    const x = 0.6 + (i % 2) * 6.15, y = 3.85 + Math.floor(i / 2) * 1.5;
    await badge(s, gl[i][0], x, y + 0.05, 0.75, C.accent1);
    T(s, gl[i][1], { x: x + 0.95, y, w: 5.0, h: 0.35, fontSize: 18, bold: true });
    T(s, gl[i][2], { x: x + 0.95, y: y + 0.38, w: 5.0, h: 0.9, fontSize: 14, color: C.accent5 });
  }
  s.addNotes("One-slide summary. Three headline numbers: 17,547 training pairs, 57.1 chrF++ on the NusaX test set versus 38.7 for the base model, and a 36.9 point gain on held-out hikayat verse. Then the four parts of the work: data, techniques, evaluation and the application.");

  // ================= 3 TECHNIQUES TABLE =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Overview" });
  header(s, "Overview", "Techniques in our system");
  tbl(s, [
    [th("Technique"), th("How it works in our project"), th("Evidence")],
    [td("Direct approach", { bold: true }), td("Word-for-word lookup in the 1985 Kamus Aceh-Indonesia list (5,260 headwords), keeping word order", { fontSize: 14 }), td("35.5 chrF++", { fontSize: 14 })],
    [td("Transfer approach", { bold: true }), td("Analyse prefixes and the suffix -jih, map 15 function words, then generate the Indonesian sentence", { fontSize: 14 }), td("39.2 chrF++", { fontSize: 14 })],
    [td("Interlingual view", { bold: true }), td("NLLB's encoder maps Acehnese into a shared multilingual representation; the decoder writes Indonesian", { fontSize: 14 }), td("Tokens shown in the app", { fontSize: 14 })],
    [td("Neural translation", { bold: true }), td("NLLB-200 (600M) fine-tuned on 17,547 pairs, with early stopping on validation scores", { fontSize: 14 }), td("57.1 chrF++ / 30.8 BLEU", { fontSize: 14 })],
    [td("Data augmentation", { bold: true }), td("Pivot translation: human Acehnese plus English, English translated to Indonesian by NLLB", { fontSize: 14 }), td("About 5,700 extra pairs", { fontSize: 14 })],
    [td("Disambiguation", { bold: true }), td("Dictionary meanings ranked by overlap with the translation; best meaning marked with a tick", { fontSize: 14 }), td("266 multi-meaning headwords", { fontSize: 14 })],
  ], { x: 0.6, y: 1.55, w: 12.13, colW: [2.5, 6.9, 2.73], rowH: [0.45, 0.78, 0.78, 0.78, 0.78, 0.78, 0.78], fontSize: 14, fill: { color: HEX.white } });
  s.addNotes("This is the map of the techniques your professor listed. Direct and transfer are classic rule-based approaches, which we built as baselines. The neural model is the main system, and its shared encoder is the closest equivalent to an interlingua. Data augmentation is our pivot translation. Disambiguation is the dictionary-based meaning picker in the app. Each of these gets its own slide later.");

  // ================= 4 PIPELINE =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Overview" });
  header(s, "Overview", "From raw sources to a running app");
  const steps = [["FaBook", "Collect", "Corpora, scanned books, a thesis, stories, team files"], ["FaTools", "Clean and align", "OCR, filtering, sentence alignment"],
                 ["FaShieldAlt", "Normalize and check", "Spelling rules, language ID, duplicate and leak control"], ["FaMicrochip", "Fine-tune", "NLLB-200 on a Colab T4 GPU"], ["FaLaptop", "Evaluate and serve", "Three test sets, local app, Colab demo"]];
  for (let i = 0; i < 5; i++) {
    const x = 0.6 + i * 2.45;
    card(s, x, 1.8, 2.2, 3.0, "Pipeline step");
    await badge(s, steps[i][0], x + 0.72, 2.05, 0.75, C.accent1);
    T(s, steps[i][1], { x: x + 0.15, y: 3.0, w: 1.9, h: 0.55, fontSize: 16, bold: true, align: "center" });
    T(s, steps[i][2], { x: x + 0.15, y: 3.6, w: 1.9, h: 1.1, fontSize: 13, color: C.accent5, align: "center" });
    if (i < 4) arrow(s, x + 2.2, 2.95 + 0.1);
  }
  card(s, 0.6, 5.2, 12.13, 1.5, "Tools card", C.text2);
  T(s, "Tools used", { x: 0.9, y: 5.35, w: 3, h: 0.35, fontSize: 14, bold: true, color: C.accent2 });
  T(s, "PyMuPDF and RapidOCR (scanned books)  ·  rapidfuzz and datasketch (duplicates)  ·  Hugging Face Transformers and PyTorch (training)  ·  sacreBLEU (scoring)  ·  Gradio (app)  ·  Google Colab T4 GPU", { x: 0.9, y: 5.75, w: 11.5, h: 0.8, fontSize: 15, color: C.background1 });
  s.addNotes("Five stages. We collect data from many places, clean and align it, normalize and check it, fine-tune the model, then evaluate and serve it. Every stage is a command in our code, so the whole pipeline is reproducible. The tools listed are the main libraries behind each stage.");

  // ================= 5 PARALLEL DATA =================
  section("Data");
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data" });
  header(s, "Data", "Parallel data we collected");
  tbl(s, [
    [th("Source"), th("What it is"), th("Pairs used"), th("Licence / origin")],
    [td("NusaX-MT", { bold: true }), td("Human Acehnese–Indonesian translations (IndoNLP)"), td("500 train, 100 val, 400 test"), td("CC-BY-SA 4.0")],
    [td("FLORES-200", { bold: true }), td("Meta's professional translations of Wikipedia-style sentences"), td("797 train, 200 val, 1,012 test"), td("CC-BY-SA 4.0")],
    [td("Hikayat Abu Sammah", { bold: true }), td("Verse story with Indonesian translation; scanned book (Depdikbud)"), td("1,432 train, 79 val, 143 test"), td("Government book, credited")],
    [td("Hikayat Malik Mawot", { bold: true }), td("Verse edition with translation (Inayati, UIN Ar-Raniry, 2017)"), td("350"), td("Thesis, credited")],
    [td("Quran translation", { bold: true }), td("Tgk. Mahjiddin Jusuf (Acehnese) with Kemenag (Indonesian)"), td("5,466 verse pairs"), td("Credited")],
    [td("Wikipedia (OPUS)", { bold: true }), td("Aligned Acehnese and Indonesian article sentences"), td("375 of 557"), td("CC-BY-SA 4.0")],
    [td("NLLB-Seed pivot", { bold: true }), td("Meta/OLDI: 6,193 human Acehnese sentences with English"), td("About 5,700"), td("CC-BY-SA 4.0")],
    [td("Team translations", { bold: true }), td("Andrie's file (5,000 rows) and five short stories (103 pairs)"), td("2,798 and 96"), td("Our team's work")],
  ], { x: 0.6, y: 1.5, w: 12.13, colW: [2.55, 5.0, 2.6, 1.98], rowH: [0.45, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62], fontSize: 13, fill: { color: HEX.white } });
  s.addNotes("Eight parallel sources, which means Acehnese sentences with an Indonesian translation. Public corpora: NusaX, FLORES, Wikipedia and NLLB-Seed. Books and a thesis that we digitized: the hikayat Abu Sammah and Malik Mawot. The Quran translation. And our own team's translations. Each one is credited, and the licence is tracked per source in our repository.");

  // ================= 6 TRAINING MIX =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data" });
  header(s, "Data", "The 17,547-pair training mix");
  hBars(s, { x: 0.6, y: 1.5, w: 7.9, h: 5.3, labels: ["Quran verses", "NLLB-Seed pivot (about)", "Team: Andrie's pairs", "Hikayat Abu Sammah", "FLORES dev", "NusaX train", "Wikipedia", "Hikayat Malik Mawot", "Team: stories"], values: [5466, 5733, 2798, 1432, 797, 500, 375, 350, 96], colors: [HEX.teal], max: 6200, labelW: 2.7, fmt: (v) => v.toLocaleString("en-US"), fontSize: 13 });
  card(s, 8.9, 1.6, 3.83, 1.5, "Stat card"); stat(s, 9.15, 1.7, 3.4, "379", "validation sentences (pick the best epoch)", { size: 36, lh: 0.7 });
  card(s, 8.9, 3.3, 3.83, 3.4, "Stat card");
  T(s, "Held-out test sets", { x: 9.15, y: 3.45, w: 3.4, h: 0.4, fontSize: 16, bold: true });
  [["400", "NusaX: everyday text"], ["1,012", "FLORES: Wikipedia style"], ["143", "Hikayat: old verse (pages 50–53)"]].forEach(([n, l], i) => {
    T(s, n, { x: 9.15, y: 3.95 + i * 0.9, w: 1.3, h: 0.6, fontSize: 28, bold: true, color: C.accent1, fontFace: "Georgia" });
    T(s, l, { x: 10.45, y: 4.05 + i * 0.9, w: 2.2, h: 0.6, fontSize: 13, color: C.accent5 });
  });
  s.addNotes("This is exactly what went into the training run: 17,547 pairs. The Quran and the pivot data are the largest parts, followed by our team's translations and the hikayat. The 379 validation sentences choose the best epoch, and the three test sets are completely separate: they are never trained on and never used to choose anything.");

  // ================= 7 SCANNED BOOK -> PAIRS =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data" });
  header(s, "Data", "From a scanned book to pairs");
  const bs = ["OCR every page at 300 dpi (RapidOCR)", "Remove page numbers, headings, footnotes and low-confidence lines", "Rejoin lines the layout split in two",
              "Repair OCR letter mistakes, only when a reference text confirms the word", "Align Acehnese and Indonesian verses by dynamic programming", "Label every pair KEEP or REVIEW; delete nothing"];
  bs.forEach((t, i) => {
    const y = 1.55 + i * 0.85;
    s.addShape(pres.shapes.OVAL, { x: 0.6, y, w: 0.55, h: 0.55, fill: { color: C.accent1 }, line: { color: C.accent1, width: 0 }, objectName: "Step number" });
    T(s, String(i + 1), { x: 0.6, y, w: 0.55, h: 0.55, fontSize: 16, bold: true, color: C.background1, align: "center", valign: "middle" });
    T(s, t, { x: 1.35, y: y - 0.02, w: 5.9, h: 0.65, fontSize: 15, valign: "middle" });
  });
  [["11.3% → 0.8%", "word error: PDF text layer versus our OCR, on a hand-checked sample"], ["1,856", "verse pairs aligned from the book"], ["1,654", "pairs labelled KEEP (199 marked REVIEW)"], ["40 of 40", "random KEEP pairs checked by hand were correct"]].forEach(([n, l], i) => {
    const x = 7.7 + (i % 2) * 2.6, y = 1.55 + Math.floor(i / 2) * 2.55;
    card(s, x, y, 2.45, 2.35, "Stat card");
    T(s, n, { x: x + 0.15, y: y + 0.2, w: 2.15, h: 0.8, fontSize: i === 0 ? 20 : 30, bold: true, color: C.accent1, fontFace: "Georgia", valign: "middle" });
    T(s, l, { x: x + 0.15, y: y + 1.1, w: 2.15, h: 1.1, fontSize: 13, color: C.accent5 });
  });
  s.addNotes("Hikayat Abu Sammah is a scanned printed book with the Acehnese verse in one section and the Indonesian translation in another. Its PDF text layer was unreliable: 11.3 percent of the words were wrong on a sample we checked by hand. Re-reading every page with OCR at 300 dpi cut that to 0.8 percent. We then removed the noise and aligned the verses with dynamic programming, which keeps the order and matches shared words. 40 of 40 random pairs we checked by hand were correct translations of each other.");

  // ================= 8 THESIS, STORIES, TEAM =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data" });
  header(s, "Data", "Thesis, stories and team translations");
  const cols = [
    ["FaBookOpen", "Hikayat Malik Mawot", [["1,030", "alternating verse lines"], ["350", "pairs kept"]], "Footnotes cut, then every pair checked for line similarity and Acehnese language."],
    ["FaListOl", "Andrie's team file", [["5,000", "rows received"], ["2,798", "pairs after cleaning"]], "Dropped heavy OCR errors, missing translations and rows overlapping our test sets."],
    ["FaFileAlt", "Five short stories", [["103", "numbered sentence pairs"], ["96", "pairs kept"]], "Human-aligned table; very short rows and unclear Acehnese rows removed."],
  ];
  for (let i = 0; i < 3; i++) {
    const x = 0.6 + i * 4.1;
    card(s, x, 1.55, 3.93, 5.2, "Source card");
    await badge(s, cols[i][0], x + 0.3, 1.8, 0.8, C.accent1);
    T(s, cols[i][1], { x: x + 1.25, y: 1.85, w: 2.5, h: 0.7, fontSize: 18, bold: true, valign: "middle" });
    cols[i][2].forEach(([n, l], k) => { T(s, n, { x: x + 0.3, y: 2.9 + k * 1.05, w: 1.7, h: 0.7, fontSize: 34, bold: true, color: k ? C.accent1 : C.accent5, fontFace: "Georgia", valign: "middle" }); T(s, l, { x: x + 2.0, y: 2.9 + k * 1.05, w: 1.75, h: 0.7, fontSize: 13, color: C.accent5, valign: "middle" }); });
    T(s, cols[i][3], { x: x + 0.3, y: 5.2, w: 3.35, h: 1.4, fontSize: 14 });
  }
  s.addNotes("Three smaller sources, each needed its own parser. Malik Mawot is a thesis edition where every Acehnese line is followed by its translation, so we split by line, cut the footnotes and kept only pairs that passed a similarity and language check. Andrie's file gave 2,798 clean pairs. The stories came as a numbered table of 103 sentence pairs, of which 96 were kept.");

  // ================= 9 DATA AUGMENTATION =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data" });
  header(s, "Data augmentation", "Pivot translation adds about 5,700 pairs");
  const bx = [["Acehnese", "6,193 human-written sentences (NLLB-Seed)", HEX.teal], ["English", "Same meaning, from the same dataset", HEX.slate], ["NLLB English → Indonesian", "A strong, high-resource direction", HEX.deep], ["Training pair", "Human Acehnese + machine Indonesian, labelled", HEX.gold]];
  bx.forEach(([t, d, col], i) => {
    const x = 0.6 + i * 3.1;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.65, w: 2.8, h: 1.9, rectRadius: 0.12, fill: { color: col }, line: { color: col, width: 0 }, objectName: "Flow box" });
    T(s, t_(t), { x: x + 0.15, y: 1.8, w: 2.5, h: 0.7, fontSize: 17, bold: true, color: i === 3 ? HEX.ink : HEX.white, valign: "middle" });
    T(s, d, { x: x + 0.15, y: 2.5, w: 2.5, h: 0.95, fontSize: 13, color: i === 3 ? HEX.ink : HEX.white });
    if (i < 3) arrow(s, x + 2.8, 2.3 + 0.1);
  });
  card(s, 0.6, 3.95, 5.9, 2.85, "Filters card");
  T(s, "Filters before a pair is kept", { x: 0.9, y: 4.1, w: 5.4, h: 0.4, fontSize: 17, bold: true });
  T(s, [{ text: "4 to 60 words on each side", options: { bullet: true, breakLine: true } }, { text: "Word-count ratio between the two sides within 0.5 to 2", options: { bullet: true, breakLine: true } },
        { text: "Acehnese side must pass the language check", options: { bullet: true, breakLine: true } }, { text: "Leak check against validation and test sets", options: { bullet: true } }], { x: 0.9, y: 4.55, w: 5.4, h: 2.15, fontSize: 16, paraSpaceAfter: 8 });
  card(s, 6.83, 3.95, 5.9, 2.85, "Result card");
  stat(s, 7.13, 4.1, 2.6, "5,750", "candidates after filtering", { size: 40, lh: 0.6 });
  stat(s, 10.0, 4.1, 2.6, "5,733", "pairs in the final training mix (about)", { size: 40, lh: 0.8 });
  T(s, "Also broadening the data: Wikipedia aligned sentences (375) and Quran verses (5,466).", { x: 7.13, y: 5.85, w: 5.4, h: 0.85, fontSize: 14 });
  s.addNotes("Data augmentation means creating more training data from what exists. NLLB-Seed has about six thousand sentences written by people in Acehnese, each paired with English. English to Indonesian is one of the strongest directions in NLLB, so we translated the English side into Indonesian and paired it with the human Acehnese. After filtering we had about 5,750 candidates, and about 5,700 went into training. The Indonesian side is machine output and is labelled that way in the data.");

  // ================= 10 PREPARING THE TEXT =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data" });
  header(s, "Data", "Preparing and checking the text");
  const pc = [["FaLanguage", "Normalization", "Same rules in training and in the app",
               ["Unicode NFC and straight quotes", "Dutch-era spellings: njang → nyang, djipeugot → jipeugot", "Diaeresis removed: löen → loen", "Original text always kept beside the normalized text"]],
              ["FaSearch", "Language check", "Character n-gram model (naive Bayes)",
               ["Trained on AcehX and NusaX train", "Acehnese recognised 96–98%", "Indonesian recognised 99.5–100%", "Filters foreign or noisy lines"]],
              ["FaClone", "Duplicate control", "Exact and near-duplicate matching",
               ["Match key ignores case, accents, punctuation, old spelling", "Near duplicates: 90% similarity or more (rapidfuzz)", "MinHash-LSH against AcehX (164,778 lines)", "Duplicates marked, not silently dropped"]]];
  for (let i = 0; i < 3; i++) {
    const x = 0.6 + i * 4.1;
    card(s, x, 1.55, 3.93, 5.2, "Check card");
    await badge(s, pc[i][0], x + 0.3, 1.8, 0.75, C.accent1);
    T(s, pc[i][1], { x: x + 1.25, y: 1.8, w: 2.5, h: 0.4, fontSize: 18, bold: true });
    T(s, pc[i][2], { x: x + 1.25, y: 2.2, w: 2.5, h: 0.45, fontSize: 12, color: C.accent5 });
    T(s, pc[i][3].map((t, k) => ({ text: t, options: { bullet: true, breakLine: k < 3 } })), { x: x + 0.3, y: 3.05, w: 3.4, h: 3.6, fontSize: 16, paraSpaceAfter: 12 });
  }
  s.addNotes("Three checks before any text reaches the model. Normalization makes spelling consistent, and the app uses exactly the same rules, which a test enforces. A language classifier built from character n-grams removes lines that are not Acehnese. Duplicate control uses a match key and fuzzy matching so the same sentence cannot appear twice or leak across splits. AcehX, a 164,778-line Acehnese corpus, serves as our spelling and duplicate reference.");

  // ================= 11 KEEPING THE TEST HONEST =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data" });
  header(s, "Evaluation design", "Keeping the test honest");
  const hs = ["Test and validation pages are kept as whole blocks, so neighbouring verses never land on both sides", "Any training pair matching a validation or test sentence is removed, ignoring case, accents, punctuation and old spelling",
              "Any training pair 90% or more similar to a test sentence on the Acehnese side is removed", "The training script refuses to start if a single leak remains", "The best epoch is chosen on validation only, never on the test sets"];
  hs.forEach((t, i) => { const y = 1.6 + i * 1.05; card(s, 0.6, y, 7.3, 0.9, "Rule card"); T(s, String(i + 1), { x: 0.8, y, w: 0.5, h: 0.9, fontSize: 24, bold: true, color: C.accent1, fontFace: "Georgia", valign: "middle" }); T(s, t, { x: 1.4, y, w: 6.35, h: 0.9, fontSize: 14, valign: "middle" }); });
  [["Training", "17,547", HEX.teal, HEX.white], ["Validation", "379", HEX.gold, HEX.ink], ["Test", "1,555", HEX.deep, HEX.white]].forEach(([n, v, col, tc], i) => {
    const y = 1.6 + i * 1.75;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.5, y, w: 4.23, h: 1.55, rectRadius: 0.12, fill: { color: col }, line: { color: col, width: 0 }, objectName: "Split box" });
    T(s, v, { x: 8.8, y: y + 0.15, w: 3.6, h: 0.8, fontSize: 40, bold: true, color: tc, fontFace: "Georgia" });
    T(s, n + (i === 2 ? " (400 + 1,012 + 143)" : ""), { x: 8.8, y: y + 0.95, w: 3.6, h: 0.45, fontSize: 14, color: tc });
  });
  s.addNotes("The scores are only meaningful if the model has never seen the test sentences, so we protected them in layers. Whole pages are kept together, exact and near-duplicate matches are removed, and the training script stops if any leak remains. The best epoch is chosen on the validation set, so the test sets are used once, at the end.");

  // ================= 12 MODEL AND RECIPE =================
  section("Method");
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Method" });
  header(s, "Method", "Model and training recipe");
  tbl(s, [
    [th("Setting"), th("Value"), th("Why")],
    [td("Base model", { bold: true }), td("NLLB-200 distilled, 600M parameters"), td("Already includes Acehnese (ace_Latn)")],
    [td("Trained", { bold: true }), td("All weights"), td("Adapts the whole model to our data")],
    [td("Optimiser", { bold: true }), td("Adafactor, learning rate 1e-4, 10% warm-up"), td("Low memory: fits a Colab T4 GPU")],
    [td("Batch and length", { bold: true }), td("8 pairs, up to 128 tokens"), td("Fits GPU memory")],
    [td("Label smoothing", { bold: true }), td("0.1"), td("Less overconfidence on a small corpus")],
    [td("Stopping", { bold: true }), td("Up to 10 epochs, patience 2"), td("Stops when validation stops improving")],
    [td("Selection", { bold: true }), td("Best epoch on validation chrF++"), td("Test sets never choose the model")],
    [td("Saved model", { bold: true }), td("Half precision, 1.2 GB"), td("Same translations, half the size")],
  ], { x: 0.6, y: 1.5, w: 12.13, colW: [2.6, 5.3, 4.23], rowH: [0.42, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62], fontSize: 14, fill: { color: HEX.white } });
  s.addNotes("We start from NLLB-200 distilled with 600 million parameters, which already includes Acehnese. We train all weights with the Adafactor optimizer, which uses little memory so it fits a free GPU. Label smoothing and early stopping guard against overfitting on a small dataset. The model is saved in half precision, which halves its size without changing the translations.");

  // ================= 13 TRAINING RUN =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Method" });
  header(s, "Method", "The training run");
  lineChart(s, { x: 0.6, y: 1.5, w: 7.9, h: 5.3, title: "Validation chrF++ by epoch", labels: ["Epoch 1", "Epoch 2", "Epoch 3", "Epoch 4", "Epoch 5"], values: [52.85, 54.67, 55.72, 55.33, 55.01], min: 50, max: 58, ticks: [50, 52, 54, 56, 58], color: HEX.teal });
  [["3 of 5", "best epoch, kept by early stopping"], ["3.39 → 2.31", "training loss, epoch 1 to 5"], ["T4 GPU", "Google Colab, 17,547 pairs"]].forEach(([n, l], i) => {
    const y = 1.6 + i * 1.75; card(s, 8.9, y, 3.83, 1.55, "Stat card");
    T(s, n, { x: 9.15, y: y + 0.2, w: 3.4, h: 0.7, fontSize: 30, bold: true, color: C.accent1, fontFace: "Georgia" }); T(s, l, { x: 9.15, y: y + 0.9, w: 3.4, h: 0.5, fontSize: 14, color: C.accent5 });
  });
  s.addNotes("Validation chrF++ rose from 52.9 in epoch 1 to 55.7 in epoch 3, then slipped slightly in epochs 4 and 5 while the training loss kept falling. Early stopping detected that and kept epoch 3, which is the model we tested. This is the standard sign that training should stop before the model starts to memorize.");

  // ================= 14 RESULTS =================
  section("Results");
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  header(s, "Results", "Fine-tuning lifts every test set");
  colChart(s, { x: 0.6, y: 1.5, w: 7.6, h: 5.3, title: "chrF++ (higher is better)", groups: [{ label: "NusaX (400)", vals: [38.66, 57.15] }, { label: "FLORES (1,012)", vals: [46.27, 52.81] }, { label: "Hikayat (143)", vals: [23.98, 60.92] }], series: ["Base NLLB-200", "Our fine-tuned model"], colors: [HEX.mist, HEX.teal], max: 70, ticks: [0, 10, 20, 30, 40, 50, 60, 70] });
  tbl(s, [[th("Test set"), th("Base BLEU", "right"), th("Our BLEU", "right"), th("chrF++ gain", "right")],
          [td("NusaX"), td("13.5", { align: "right" }), td("30.8", { align: "right", bold: true }), td("+18.5", { align: "right", bold: true, color: HEX.teal })],
          [td("FLORES"), td("21.3", { align: "right" }), td("27.3", { align: "right", bold: true }), td("+6.5", { align: "right", bold: true, color: HEX.teal })],
          [td("Hikayat"), td("2.7", { align: "right" }), td("35.9", { align: "right", bold: true }), td("+36.9", { align: "right", bold: true, color: HEX.teal })]],
    { x: 8.5, y: 1.7, w: 4.23, colW: [1.0, 1.05, 0.95, 1.23], rowH: [0.5, 0.5, 0.5, 0.5], fontSize: 13, fill: { color: HEX.white } });
  card(s, 8.5, 4.0, 4.23, 2.8, "Note card");
  T(s, "How to read this", { x: 8.75, y: 4.15, w: 3.8, h: 0.4, fontSize: 16, bold: true });
  T(s, "Test sentences were never trained on and never used to choose the model. The sets measure different text types: everyday reviews, Wikipedia style and old verse. Hikayat is closest to our verse training data; NusaX and FLORES show everyday use.", { x: 8.75, y: 4.6, w: 3.8, h: 2.15, fontSize: 14, color: C.accent5 });
  s.addNotes("The headline result. On NusaX everyday text, chrF++ goes from 38.7 to 57.1. On FLORES, 46.3 to 52.8. On held-out hikayat verse, 24.0 to 60.9. BLEU rises on all three as well. The three sets measure different kinds of text, so we report all of them rather than one number. Hikayat is closest to our verse training sources, so NusaX and FLORES are the better guide for everyday text.");

  // ================= 15 CLASSICAL VS NEURAL =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  header(s, "Results", "Classical approaches versus neural");
  hBars(s, { x: 0.6, y: 1.5, w: 7.9, h: 5.3, title: "chrF++ on the 400 NusaX test sentences", labels: ["Copy (nothing translated)", "Direct (dictionary)", "Transfer (rules)", "Base NLLB-200", "Fine-tuned NLLB"], values: [32.0, 35.5, 39.2, 38.7, 57.1], colors: [HEX.mist, HEX.slate, HEX.slate, HEX.mist, HEX.teal], max: 65, labelW: 3.0, fmt: (v) => v.toFixed(1), fontSize: 14 });
  [["+3.5", "Direct lookup over copying"], ["+3.7", "Transfer rules over direct"], ["+17.9", "Fine-tuned neural over transfer"]].forEach(([n, l], i) => {
    const y = 1.6 + i * 1.75; card(s, 8.9, y, 3.83, 1.55, "Stat card");
    T(s, n, { x: 9.15, y: y + 0.2, w: 3.4, h: 0.7, fontSize: 36, bold: true, color: C.accent1, fontFace: "Georgia" }); T(s, l, { x: 9.15, y: y + 0.95, w: 3.4, h: 0.5, fontSize: 14, color: C.accent5 });
  });
  s.addNotes("This answers the professor's question about the classic approaches. Copying the Acehnese text unchanged scores 32.0. A word-for-word dictionary lookup, the direct approach, reaches 35.5. Adding analysis and transfer rules reaches 39.2. The fine-tuned neural model reaches 57.1. Each step adds accuracy, and the neural step adds the most.");

  // ================= 16 DIRECT AND TRANSFER =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  header(s, "Techniques", "Direct and transfer in detail");
  card(s, 0.6, 1.55, 5.95, 3.1, "Direct card");
  T(s, "Direct approach", { x: 0.9, y: 1.7, w: 5.4, h: 0.4, fontSize: 18, bold: true, color: C.accent1 });
  T(s, [{ text: "Look up each word in the 1985 dictionary list", options: { bullet: true, breakLine: true } }, { text: "Take the first short meaning", options: { bullet: true, breakLine: true } }, { text: "Keep the Acehnese word order", options: { bullet: true, breakLine: true } }, { text: "Unknown words stay as they are", options: { bullet: true } }], { x: 0.9, y: 2.2, w: 5.4, h: 2.3, fontSize: 16, paraSpaceAfter: 8 });
  card(s, 6.78, 1.55, 5.95, 3.1, "Transfer card");
  T(s, "Transfer approach", { x: 7.08, y: 1.7, w: 5.4, h: 0.4, fontSize: 18, bold: true, color: C.accent1 });
  T(s, [{ text: "Analysis: split prefixes ji-, geu-, neu-, ta- and the suffix -jih", options: { bullet: true, breakLine: true } }, { text: "Transfer: 15 function words, e.g. hana → tidak, nyang → yang, lon → saya", options: { bullet: true, breakLine: true } }, { text: "Generation: assemble and capitalise the sentence", options: { bullet: true, breakLine: true } }, { text: "Each word kept only if NusaX supports it (50%+ of 20+ sentences)", options: { bullet: true } }], { x: 7.08, y: 2.2, w: 5.4, h: 2.3, fontSize: 15, paraSpaceAfter: 6 });
  card(s, 0.6, 4.9, 12.13, 1.95, "Example card", C.text2);
  T(s, "Real example from the NusaX test set", { x: 0.9, y: 5.0, w: 6, h: 0.35, fontSize: 14, bold: true, color: C.accent2 });
  [["Acehnese", "Toe ngon hotel lon dom"], ["Direct", "Toe meuteumee hotel padam bermalam"], ["Transfer", "Toe dengan hotel saya bermalam"], ["Reference", "Dekat dengan hotel saya menginap"]].forEach(([a, b], i) => {
    const x = 0.9 + (i % 2) * 6.0, y = 5.4 + Math.floor(i / 2) * 0.62;
    T(s, a, { x, y, w: 1.2, h: 0.5, fontSize: 14, bold: true, color: C.accent6, valign: "middle" }); T(s, b, { x: x + 1.25, y, w: 4.6, h: 0.5, fontSize: 15, color: C.background1, valign: "middle" });
  });
  s.addNotes("Direct translation looks each word up and keeps the order. Transfer first analyses the Acehnese words by splitting prefixes and the -jih suffix, then transfers a small set of function words with rules, then generates the sentence. We only kept a rule when the NusaX training sentences supported it. In the example, direct translation turns 'lon' into 'padam', while transfer correctly gives 'saya'.");

  // ================= 17 INTERLINGUAL =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  header(s, "Techniques", "Interlingual view: shared space");
  const fl = [["Acehnese text", "ace_Latn tag marks the source language", HEX.slate], ["Encoder", "Reads sub-word tokens and builds meaning vectors", HEX.teal], ["Shared space", "One multilingual representation for about 200 languages", HEX.gold], ["Decoder", "Writes tokens step by step; ind_Latn tag selects Indonesian", HEX.teal], ["Indonesian text", "Tokens merged back into a sentence", HEX.slate]];
  fl.forEach(([t, d, col], i) => {
    const x = 0.6 + i * 2.45, tc = i === 2 ? HEX.ink : HEX.white;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.7, w: 2.2, h: 2.6, rectRadius: 0.12, fill: { color: col }, line: { color: col, width: 0 }, objectName: "Flow box" });
    T(s, t, { x: x + 0.15, y: 1.85, w: 1.9, h: 0.6, fontSize: 16, bold: true, color: tc, valign: "middle" }); T(s, d, { x: x + 0.15, y: 2.5, w: 1.9, h: 1.7, fontSize: 14, color: tc });
    if (i < 4) arrow(s, x + 2.2, 2.75 + 0.1);
  });
  const pt = [["FaGlobe", "One shared model", "Every language passes through the same representation, a learned alternative to a hand-built interlingua."], ["FaEye", "Visible in the app", "The 'Cara kerja model' panel shows the real encoder tokens and decoder tokens for each translation."], ["FaExchangeAlt", "Selected by tags", "Language tags choose the source and the target, so the same model can translate in either direction."]];
  for (let i = 0; i < 3; i++) { const x = 0.6 + i * 4.1; await badge(s, pt[i][0], x, 4.75, 0.7, C.accent1); T(s, pt[i][1], { x: x + 0.9, y: 4.72, w: 3.0, h: 0.4, fontSize: 16, bold: true }); T(s, pt[i][2], { x: x + 0.9, y: 5.15, w: 3.0, h: 1.7, fontSize: 14, color: C.accent5 }); }
  s.addNotes("In interlingual machine translation, the source is converted into a language-neutral meaning, and the target is generated from it. Classic systems built that representation by hand. NLLB learns one: its encoder maps all languages into a shared space, and its decoder writes any target language from it. The language tags ace_Latn and ind_Latn select the source and target. Our app shows the actual encoder and decoder tokens.");

  // ================= 18 DISAMBIGUATION =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  header(s, "Techniques", "Dictionary-based disambiguation");
  const ds = ["Find each Acehnese word among 5,260 headwords of the Kamus Aceh-Indonesia (1985)", "Collect every meaning listed for the word", "Score each meaning by words it shares with the model's Indonesian translation, ignoring common function words", "Mark the best meaning with a tick when it clearly leads"];
  ds.forEach((t, i) => {
    const y = 1.6 + i * 1.2;
    s.addShape(pres.shapes.OVAL, { x: 0.6, y, w: 0.6, h: 0.6, fill: { color: C.accent1 }, line: { color: C.accent1, width: 0 }, objectName: "Step number" });
    T(s, String(i + 1), { x: 0.6, y, w: 0.6, h: 0.6, fontSize: 18, bold: true, color: C.background1, align: "center", valign: "middle" });
    T(s, t, { x: 1.45, y: y - 0.1, w: 5.5, h: 1.0, fontSize: 15, valign: "middle" });
  });
  card(s, 7.4, 1.55, 5.33, 3.4, "Example card", C.text2);
  T(s, "Example", { x: 7.7, y: 1.7, w: 3, h: 0.35, fontSize: 14, bold: true, color: C.accent2 });
  T(s, "Gobnyan jak u keude", { x: 7.7, y: 2.1, w: 4.8, h: 0.4, fontSize: 17, bold: true, color: C.background1 });
  T(s, "Translation: Dia pergi ke toko", { x: 7.7, y: 2.55, w: 4.8, h: 0.4, fontSize: 14, color: C.background2 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.7, y: 3.15, w: 4.75, h: 0.75, rectRadius: 0.1, fill: { color: HEX.teal }, line: { color: HEX.teal, width: 0 }, objectName: "Best meaning" });
  s.addImage({ data: await icon("FaCheck", HEX.white), x: 7.9, y: 3.38, w: 0.3, h: 0.3, altText: "Tick mark" });
  T(s, "keude: kedai, toko …", { x: 8.35, y: 3.15, w: 4.0, h: 0.75, fontSize: 14, bold: true, color: C.background1, valign: "middle" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.7, y: 4.05, w: 4.75, h: 0.7, rectRadius: 0.1, fill: { color: C.text1 }, line: { color: C.text1, width: 0 }, objectName: "Other meaning" });
  T(s, "keude: endapan sisa masakan berkuah", { x: 7.85, y: 4.05, w: 4.5, h: 0.7, fontSize: 14, color: C.background2, valign: "middle" });
  [["5,260", "headwords"], ["266", "with several meanings"]].forEach(([n, l], i) => { const x = 7.4 + i * 2.75; card(s, x, 5.2, 2.58, 1.6, "Stat card"); T(s, n, { x: x + 0.2, y: 5.3, w: 2.2, h: 0.7, fontSize: 34, bold: true, color: C.accent1, fontFace: "Georgia" }); T(s, l, { x: x + 0.2, y: 6.0, w: 2.2, h: 0.6, fontSize: 14, color: C.accent5 }); });
  s.addNotes("Many Acehnese words have several meanings. For each word in the user's sentence, our module finds all of its dictionary meanings in the 1985 Kamus Aceh-Indonesia list. It scores each meaning by how many content words it shares with the model's Indonesian translation, and marks the best one with a tick when it clearly leads. In the example, keude has two meanings, and the one that mentions toko matches the translation. This appears in the app as the Kata per kata panel.");

  // ================= 19 EXAMPLES =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  header(s, "Results", "Translations from the model");
  const ex = [["Lon jak u peukan uroe nyoe.", "Saya pergi ke pasar hari ini.", null, null], ["Teuma troih le Abu Sammah, budak indah paraih rupa", "Lalu sampailah Abu Sammah, budak indah paras rupa", null, null],
              ["Nyo beutoi, jih teungoh jaga warong.", "Ini benar, dia sedang menjaga warung.", "Ini benar, karena dia sedang menjaga warganya.", "Iya benar, dia sedang jaga warung."]];
  const ys19 = [1.55, 3.1, 4.65], hs19 = [1.35, 1.35, 1.95];
  ex.forEach((e, i) => {
    const y = ys19[i]; card(s, 0.6, y, 12.13, hs19[i], "Example card");
    T(s, "Acehnese", { x: 0.9, y: y + 0.18, w: 1.3, h: 0.4, fontSize: 12, bold: true, color: C.accent5, valign: "middle" }); T(s, e[0], { x: 2.2, y: y + 0.15, w: 10.3, h: 0.45, fontSize: 18, bold: true, valign: "middle" });
    T(s, "Our model", { x: 0.9, y: y + 0.72, w: 1.3, h: 0.4, fontSize: 12, bold: true, color: C.accent1, valign: "middle" }); T(s, e[1], { x: 2.2, y: y + 0.7, w: 10.3, h: 0.45, fontSize: 18, color: C.accent1, bold: true, valign: "middle" });
    if (e[2]) { T(s, "Base NLLB", { x: 0.9, y: y + 1.3, w: 1.3, h: 0.4, fontSize: 12, bold: true, color: C.accent5, valign: "middle" }); T(s, e[2], { x: 2.2, y: y + 1.28, w: 4.9, h: 0.45, fontSize: 14, color: C.accent5, valign: "middle" });
                T(s, "Reference", { x: 7.3, y: y + 1.3, w: 1.2, h: 0.4, fontSize: 12, bold: true, color: C.accent5, valign: "middle" }); T(s, e[3], { x: 8.5, y: y + 1.28, w: 4.1, h: 0.45, fontSize: 14, color: C.accent5, valign: "middle" }); }
  });
  s.addNotes("Three real outputs. The first is a simple everyday sentence. The second is a line of hikayat verse that the model was never trained on: it keeps the sentence structure and old vocabulary. The third is from the NusaX test set, where the base model misreads 'warong' as 'warganya', while the fine-tuned model gives a translation close to the human reference.");

  // ================= 20 APP =================
  section("Application");
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Application" });
  header(s, "Application", "The translator app");
  const af = [["FaWifi", "Local and offline", "Runs at 127.0.0.1:7860; no internet after the first start"], ["FaLanguage", "Same normalization", "Input is cleaned exactly like the training data"], ["FaListOl", "Sentence by sentence", "Details table with original, normalized and translated text"],
              ["FaProjectDiagram", "Model view", "Encoder and decoder tokens for each translation"], ["FaBook", "Dictionary panel", "Word meanings with the best-fitting one ticked"], ["FaCheckCircle", "Accuracy panel", "Test scores shown next to the translator"]];
  for (let i = 0; i < 6; i++) {
    const x = 0.6 + (i % 2) * 3.35, y = 1.55 + Math.floor(i / 2) * 1.5;
    card(s, x, y, 3.2, 1.35, "Feature card");
    await badge(s, af[i][0], x + 0.15, y + 0.15, 0.55, C.accent1);
    T(s, af[i][1], { x: x + 0.82, y: y + 0.15, w: 2.3, h: 0.55, fontSize: 14, bold: true, valign: "middle" });
    T(s, af[i][2], { x: x + 0.15, y: y + 0.75, w: 2.95, h: 0.55, fontSize: 12, color: C.accent5 });
  }
  // UI mock
  card(s, 7.45, 1.55, 5.28, 4.2, "App mock", C.text2);
  T(s, "Penerjemah Aceh → Indonesia", { x: 7.75, y: 1.75, w: 4.7, h: 0.45, fontSize: 18, bold: true, color: C.background1 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.75, y: 2.35, w: 2.3, h: 1.5, rectRadius: 0.08, fill: { color: C.background1 }, line: { color: C.background1, width: 0 }, objectName: "Input box" });
  T(s, "Bahasa Aceh", { x: 7.85, y: 2.4, w: 2.1, h: 0.3, fontSize: 11, color: C.accent5 }); T(s, "Lon jak u peukan uroe nyoe.", { x: 7.85, y: 2.75, w: 2.1, h: 1.0, fontSize: 14, color: C.text1 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 10.3, y: 2.35, w: 2.15, h: 1.5, rectRadius: 0.08, fill: { color: C.background1 }, line: { color: C.background1, width: 0 }, objectName: "Output box" });
  T(s, "Bahasa Indonesia", { x: 10.4, y: 2.4, w: 1.95, h: 0.3, fontSize: 11, color: C.accent5 }); T(s, "Saya pergi ke pasar hari ini.", { x: 10.4, y: 2.75, w: 1.95, h: 1.0, fontSize: 14, bold: true, color: C.accent1 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.75, y: 4.1, w: 4.7, h: 0.6, rectRadius: 0.1, fill: { color: HEX.teal }, line: { color: HEX.teal, width: 0 }, objectName: "Button" });
  T(s, "Terjemahkan · Translate", { x: 7.75, y: 4.1, w: 4.7, h: 0.6, fontSize: 15, bold: true, color: C.background1, align: "center", valign: "middle" });
  T(s, "Cara kerja model  ·  Kata per kata  ·  Seberapa akurat?", { x: 7.75, y: 4.9, w: 4.7, h: 0.35, fontSize: 12, color: C.background2 });
  card(s, 0.6, 6.0, 12.13, 0.85, "Run card");
  T(s, "Run it:  ./run_app.sh (Mac)  ·  run_app.bat (Windows)  ·  Colab demo notebook with a public link  ·  model on Hugging Face", { x: 0.9, y: 6.0, w: 11.6, h: 0.85, fontSize: 14, valign: "middle" });
  s.addNotes("The app runs on the user's own computer and works offline after the first start. It normalizes the input the same way as the training data, translates sentence by sentence, and shows a details table. The Cara kerja model panel shows the encoder and decoder tokens, the Kata per kata panel shows the dictionary meanings, and the accuracy panel shows our test scores. It can also run in Colab with a temporary public link for demos.");

  // ================= 21 QUALITY =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Application" });
  header(s, "Quality", "Reproducible, tested and documented");
  [["91", "automated tests", "Leak check, normalization, OCR, alignment, training loop, app and launcher"], ["1", "command per stage", "Every step runs from the acehid command line"], ["Git", "code and data in the repository", "Source list with licences in config/sources.csv"]].forEach(([n, l, d], i) => {
    const x = 0.6 + i * 4.1; card(s, x, 1.6, 3.93, 2.5, "Stat card");
    T(s, n, { x: x + 0.3, y: 1.75, w: 3.3, h: 0.9, fontSize: 48, bold: true, color: C.accent1, fontFace: "Georgia" }); T(s, l, { x: x + 0.3, y: 2.65, w: 3.4, h: 0.4, fontSize: 16, bold: true }); T(s, d, { x: x + 0.3, y: 3.1, w: 3.4, h: 0.95, fontSize: 13, color: C.accent5 });
  });
  card(s, 0.6, 4.4, 6.0, 2.4, "Tools card");
  T(s, "Tools", { x: 0.9, y: 4.55, w: 5, h: 0.4, fontSize: 18, bold: true });
  T(s, "Python  ·  PyTorch  ·  Transformers 5.19  ·  sentencepiece  ·  Gradio 6.29  ·  PyMuPDF  ·  RapidOCR  ·  rapidfuzz  ·  datasketch  ·  sacreBLEU  ·  Google Colab", { x: 0.9, y: 5.05, w: 5.4, h: 1.6, fontSize: 16, color: C.accent5 });
  card(s, 6.83, 4.4, 5.9, 2.4, "AI card", C.text2);
  T(s, "AI assistance", { x: 7.13, y: 4.55, w: 5, h: 0.4, fontSize: 18, bold: true, color: C.accent2 });
  T(s, "We used Claude, an AI assistant, to write much of the code. The team chose the data sources, the split rules and the evaluation, ran the training, and checked the results.", { x: 7.13, y: 5.05, w: 5.3, h: 1.6, fontSize: 16, color: C.background1 });
  s.addNotes("The project is reproducible: 91 automated tests, one command per stage and everything in a Git repository. We want to be open about tools: we used Claude, an AI assistant, to help write the code. The team decided the data sources, the split rules and the evaluation, and ran and checked the results.");

  // ================= 22 LICENCES =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Application" });
  header(s, "Responsible use", "Licences and credits");
  const lc = [["FaShieldAlt", "Model", "NLLB-200 weights are CC-BY-NC 4.0, so our fine-tuned model is for research and teaching, not commercial use."], ["FaDatabase", "Open data", "NusaX, FLORES, NLLB-Seed and Wikipedia are CC-BY-SA 4.0 and credited to their authors."],
              ["FaBook", "Books and thesis", "Depdikbud (Hikayat Abu Sammah), Inayati (Hikayat Malik Mawot), Kemenag and Tgk. Mahjiddin Jusuf (Quran), Balai Bahasa Aceh (Kamus Budaya)."], ["FaFileAlt", "Source inventory", "Every source, its licence and how we used it is recorded in config/sources.csv."]];
  for (let i = 0; i < 4; i++) {
    const x = 0.6 + (i % 2) * 6.15, y = 1.6 + Math.floor(i / 2) * 2.65;
    card(s, x, y, 5.98, 2.45, "Credit card");
    await badge(s, lc[i][0], x + 0.3, y + 0.3, 0.75, C.accent1);
    T(s, lc[i][1], { x: x + 1.3, y: y + 0.35, w: 4.4, h: 0.5, fontSize: 18, bold: true, valign: "middle" });
    T(s, lc[i][2], { x: x + 0.3, y: y + 1.2, w: 5.4, h: 1.15, fontSize: 16, color: C.accent5 });
  }
  s.addNotes("We track licences for every source. The NLLB model weights are non-commercial, so our model is for research and teaching. The open datasets are share-alike and credited. The books and thesis are credited to their authors and publishers, and the full inventory is in the repository.");

  // ================= 23 CONCLUSION =================
  section("Close");
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Close" });
  header(s, "Conclusion", "What we achieved and what comes next");
  card(s, 0.6, 1.55, 6.0, 5.25, "Achieved card");
  T(s, "Achieved", { x: 0.9, y: 1.7, w: 5, h: 0.45, fontSize: 20, bold: true, color: C.accent1 });
  T(s, ["Collected and cleaned 17,547 pairs from nine sources", "Fine-tuned NLLB-200: NusaX 38.7 → 57.1, FLORES 46.3 → 52.8, hikayat 24.0 → 60.9 chrF++", "Compared direct, transfer and neural approaches on the same test set", "Added pivot augmentation and dictionary disambiguation", "Delivered a local, offline app with encoder and decoder view"].map((t, k) => ({ text: t, options: { bullet: true, breakLine: k < 4 } })),
    { x: 0.9, y: 2.3, w: 5.4, h: 4.4, fontSize: 18, paraSpaceAfter: 14 });
  card(s, 6.83, 1.55, 5.9, 5.25, "Next card", C.text2);
  T(s, "Next steps", { x: 7.13, y: 1.7, w: 5, h: 0.45, fontSize: 20, bold: true, color: C.accent2 });
  T(s, ["Add more team translations, each checked by a second speaker", "Measure each data source's contribution by training with and without it", "Extend augmentation with back-translation", "Offer a hosted version of the app"].map((t, k) => ({ text: t, options: { bullet: true, breakLine: k < 3 } })),
    { x: 7.13, y: 2.3, w: 5.3, h: 4.4, fontSize: 18, color: C.background1, paraSpaceAfter: 14 });
  s.addNotes("To close: we built a full pipeline from raw sources to a running app, and the fine-tuned model clearly beats the base model on all three test sets. Next we want more checked translations from Acehnese speakers, to measure each data source's contribution by training with and without it, to add back-translation, and to host the app.");

  // ================= 24 THANK YOU =================
  s = pres.addSlide({ masterName: "TITLE", sectionTitle: "Close" });
  s.addText("Thank you", { placeholder: "title" });
  s.addText("Questions and discussion", { placeholder: "body" });
  T(s, "Code and data: github.com/Mutaib-yye/aceh_code", { x: 0.8, y: 6.4, w: 9, h: 0.4, fontSize: 14, color: C.accent6 });
  for (const [x, y, d, col, tr] of [[8.9, 1.0, 3.6, HEX.teal, 25], [10.6, 3.2, 2.5, HEX.gold, 20], [8.6, 4.4, 2.2, HEX.teal, 45]]) s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: col, transparency: tr }, line: { color: col, width: 0 }, objectName: "Decor circle" });
  s.addNotes("Thank the audience and invite questions. Useful details if asked: all numbers come from our Colab run; the model is saved privately on Hugging Face; the repository has every command to reproduce the pipeline.");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("written", OUT);
})();
function t_(x) { return x; }
