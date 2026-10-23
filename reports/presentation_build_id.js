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
pres.title = "Penerjemah Bahasa Aceh ke Bahasa Indonesia";
pres.author = "Kelompok 2 Proyek AcehX";
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
    { text: { text: "Penerjemah Aceh → Indonesia  ·  Presentasi tengah semester", options: { x: 0.6, y: 7.05, w: 7, h: 0.3, fontSize: 10, color: C.accent5, margin: 0 } } },
  ],
  slideNumber: { x: 12.1, y: 7.05, w: 0.6, h: 0.3, fontSize: 10, color: C.accent5, align: "right" },
});

// ---------- helpers ----------
const nf = (v, d = 0) => new Intl.NumberFormat("id-ID", { minimumFractionDigits: d, maximumFractionDigits: d }).format(v);
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
      ctext(s, nf(v, o.dec || 1), { x: bx - 0.2, y: plotBottom - bh - 0.34, w: bw + 0.4, h: 0.3, fontSize: 13, bold: true, align: "center" });
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
    ctext(s, nf(o.values[i], 2), i === 0 ? { x: px + 0.2, y: py - 0.15, w: 1.0, h: 0.3, fontSize: 13, bold: true, align: "left" } : { x: px - 0.6, y: py - 0.46, w: 1.2, h: 0.3, fontSize: 13, bold: true, align: "center" });
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
  // ================= 1 JUDUL =================
  section("Pembuka");
  let s = pres.addSlide({ masterName: "TITLE", sectionTitle: "Pembuka" });
  s.addText("Penerjemah Bahasa Aceh ke Bahasa Indonesia", { placeholder: "title" });
  s.addText("Korpus AcehX dan model NLLB hasil fine-tuning, lengkap dengan aplikasi lokal", { placeholder: "body" });
  T(s, "Kelompok 2 · Proyek AcehX · Universitas Syiah Kuala · 23 Oktober 2026", { x: 0.8, y: 6.5, w: 8.2, h: 0.4, fontSize: 13, color: C.accent6 });
  for (const [x, y, d, col, tr] of [[8.9, 1.0, 3.6, HEX.teal, 25], [10.6, 3.2, 2.5, HEX.gold, 20], [8.6, 4.4, 2.2, HEX.teal, 45]]) {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: col, transparency: tr }, line: { color: col, width: 0 }, objectName: "Lingkaran hias" });
  }
  T(s, "17.547", { x: 9.2, y: 2.05, w: 3.0, h: 0.8, fontSize: 40, bold: true, color: C.background1, fontFace: "Georgia", align: "center" });
  T(s, "pasangan kalimat latih", { x: 9.2, y: 2.85, w: 3.0, h: 0.4, fontSize: 15, color: C.background1, align: "center" });
  T(s, "57,1", { x: 10.6, y: 3.95, w: 2.5, h: 0.7, fontSize: 36, bold: true, color: C.text2, fontFace: "Georgia", align: "center" });
  T(s, "chrF++ di NusaX", { x: 10.6, y: 4.6, w: 2.5, h: 0.4, fontSize: 14, color: C.text2, align: "center" });
  s.addNotes("Selamat pagi. Kami Kelompok 2 Proyek AcehX. Kami membuat penerjemah dari bahasa Aceh ke bahasa Indonesia. Kami melatih model NLLB-200 dengan 17.547 pasangan kalimat yang kami kumpulkan dan bersihkan, mengujinya pada kalimat yang belum pernah dilihat model, lalu membuat aplikasi yang bisa dijalankan di komputer sendiri.");

  // ================= 2 TIM =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Pembuka" });
  header(s, "Tim", "Anggota tim Kelompok 2");
  const team = ["Andrie Fadhlullah Wahby", "M. Miqdad Ramadhan F", "Syaukas Rahmatillah", "Muhammad Khairul Ikhsan", "Mohammad Fawad Karimi", "Habibi", "Mutaib", "Muhammad Raza Adzani", "Muhammad Shiddiq"];
  team.forEach((n, i) => {
    const x = 0.6 + (i % 3) * 4.1, y = 1.65 + Math.floor(i / 3) * 1.7;
    card(s, x, y, 3.93, 1.5, "Kartu anggota");
    const ini = n.split(" ").filter((w) => /^[A-Z]/.test(w)).slice(0, 2).map((w) => w[0]).join("");
    s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: y + 0.32, w: 0.86, h: 0.86, fill: { color: C.accent1 }, line: { color: C.accent1, width: 0 }, objectName: "Inisial" });
    T(s, ini, { x: x + 0.3, y: y + 0.32, w: 0.86, h: 0.86, fontSize: 20, bold: true, color: C.background1, align: "center", valign: "middle", fontFace: "Georgia" });
    T(s, n, { x: x + 1.4, y, w: 2.4, h: 1.5, fontSize: 17, bold: true, valign: "middle" });
  });
  T(s, "Proyek AcehX · Universitas Syiah Kuala", { x: 0.6, y: 6.8, w: 8, h: 0.3, fontSize: 12, color: C.accent5 });
  s.addNotes("Ini sembilan anggota tim Kelompok 2. Kami bekerja bersama: mengumpulkan data, membersihkan dan menyejajarkan teks, melatih model, mengujinya, dan membuat aplikasi.");

  // ================= 3 GAMBARAN SINGKAT =================
  section("Gambaran");
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Gambaran" });
  header(s, "Gambaran", "Proyek kami secara singkat");
  [["17.547", "pasangan latih dari sembilan sumber"], ["57,1", "chrF++ di NusaX, naik dari 38,7"], ["+36,9", "kenaikan chrF++ pada syair hikayat"]].forEach(([n, l], i) => {
    const x = 0.6 + i * 4.1; card(s, x, 1.6, 3.93, 1.9, "Kartu angka");
    T(s, n, { x: x + 0.3, y: 1.8, w: 3.4, h: 0.9, fontSize: 48, bold: true, color: C.accent1, fontFace: "Georgia" }); T(s, l, { x: x + 0.3, y: 2.75, w: 3.4, h: 0.6, fontSize: 15 });
  });
  const gl = [["FaDatabase", "Data", "Sembilan sumber: korpus terbuka, buku hasil pindai, skripsi, dan terjemahan tim. Sudah dibersihkan dan diperiksa."],
              ["FaCogs", "Teknik", "OCR, penyejajaran, augmentasi pivot, fine-tuning, serta perbandingan direct, transfer, dan neural."],
              ["FaFlask", "Evaluasi", "Tiga set uji yang tidak pernah dilatih, dinilai dengan BLEU, chrF, dan chrF++."],
              ["FaLaptop", "Aplikasi", "Aplikasi lokal tanpa internet dengan panel kamus yang menandai arti kata terbaik."]];
  for (let i = 0; i < 4; i++) {
    const x = 0.6 + (i % 2) * 6.15, y = 3.85 + Math.floor(i / 2) * 1.5;
    await badge(s, gl[i][0], x, y + 0.05, 0.75, C.accent1);
    T(s, gl[i][1], { x: x + 0.95, y, w: 5.0, h: 0.35, fontSize: 18, bold: true });
    T(s, gl[i][2], { x: x + 0.95, y: y + 0.38, w: 5.0, h: 0.95, fontSize: 14, color: C.accent5 });
  }
  s.addNotes("Ringkasan satu slide. Tiga angka utama: 17.547 pasangan latih, skor chrF++ 57,1 di NusaX dibanding 38,7 pada model dasar, dan kenaikan 36,9 poin pada syair hikayat. Lalu empat bagian kerja kami: data, teknik, evaluasi, dan aplikasi.");

  // ================= 4 TUJUAN DAN TAHAPAN =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Gambaran" });
  header(s, "Gambaran", "Tujuan dan tahapan proyek");
  const st = [["FaSearch", "1. Sourcing", "Menentukan asal bahan sebelum diolah"], ["FaLanguage", "2. Normalisasi", "Menyamakan ejaan dan bentuk teks"], ["FaCheckCircle", "3. Screening", "Memberi status KEEP, REVIEW, atau DROP"], ["FaFileAlt", "4. Capture", "Memindai, OCR, dan mengetik ulang bahan cetak"]];
  for (let i = 0; i < 4; i++) {
    const x = 0.6 + i * 3.08; card(s, x, 1.6, 2.9, 2.7, "Kartu tahap");
    await badge(s, st[i][0], x + 1.075, 1.8, 0.75, C.accent1);
    T(s, st[i][1], { x: x + 0.15, y: 2.75, w: 2.6, h: 0.45, fontSize: 17, bold: true, align: "center" });
    T(s, st[i][2], { x: x + 0.2, y: 3.25, w: 2.5, h: 0.95, fontSize: 14, color: C.accent5, align: "center" });
  }
  card(s, 0.6, 4.6, 5.95, 2.2, "Kartu sasaran"); T(s, "Sasaran", { x: 0.9, y: 4.75, w: 5, h: 0.4, fontSize: 18, bold: true, color: C.accent1 });
  T(s, [{ text: "Minimal: terjemahan Aceh ke Indonesia", options: { bullet: true, breakLine: true } }, { text: "Ideal: terjemahan dua arah", options: { bullet: true, breakLine: true } }, { text: "Hasil berupa proof of concept (bukti kelayakan)", options: { bullet: true } }], { x: 0.9, y: 5.25, w: 5.4, h: 1.5, fontSize: 15, paraSpaceAfter: 6 });
  card(s, 6.78, 4.6, 5.95, 2.2, "Kartu lanjutan", C.text2); T(s, "Setelah itu", { x: 7.08, y: 4.75, w: 5, h: 0.4, fontSize: 18, bold: true, color: C.accent2 });
  T(s, "Data dibagi menjadi data latih, validasi, dan uji. Lalu disiapkan data card untuk Atlas Data AI: asal data, isi, lisensi, dan cara pakai.", { x: 7.08, y: 5.25, w: 5.4, h: 1.5, fontSize: 15, color: C.background1 });
  s.addNotes("Project brief AcehX menetapkan empat tahap: sourcing, normalisasi, screening, dan capture. Sasaran minimalnya penerjemah Aceh ke Indonesia, idealnya dua arah. Hasilnya berupa proof of concept. Setelah itu data dibagi untuk latih, validasi, dan uji, dan disiapkan data card.");

  // ================= 5 TEKNIK =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Gambaran" });
  header(s, "Gambaran", "Teknik yang kami pakai");
  tbl(s, [
    [th("Teknik"), th("Cara kerja di proyek kami"), th("Bukti")],
    [td("Pendekatan direct", { bold: true }), td("Cari arti tiap kata di daftar Kamus Aceh-Indonesia 1985 (5.260 kata). Urutan kata tetap.", { fontSize: 13 }), td("chrF++ 35,5", { fontSize: 13 })],
    [td("Pendekatan transfer", { bold: true }), td("Pecah awalan dan akhiran -jih, ganti 15 kata fungsi dengan aturan, lalu susun kalimat Indonesia.", { fontSize: 13 }), td("chrF++ 39,2", { fontSize: 13 })],
    [td("Pandangan antarlingua", { bold: true }), td("Encoder NLLB mengubah kalimat Aceh menjadi representasi bersama. Decoder menulis bahasa Indonesia.", { fontSize: 13 }), td("Token terlihat di aplikasi", { fontSize: 13 })],
    [td("Terjemahan neural", { bold: true }), td("NLLB-200 (600 juta parameter) di-fine-tune pada 17.547 pasangan, berhenti dini lewat skor validasi.", { fontSize: 13 }), td("chrF++ 57,1 / BLEU 30,8", { fontSize: 13 })],
    [td("Augmentasi data", { bold: true }), td("Terjemahan pivot: kalimat Aceh buatan manusia dan teks Inggris. NLLB menerjemahkan Inggris ke Indonesia.", { fontSize: 13 }), td("± 5.700 pasangan", { fontSize: 13 })],
    [td("Disambiguasi", { bold: true }), td("Arti kata di kamus diurutkan menurut kecocokan dengan terjemahan. Arti terbaik diberi tanda centang.", { fontSize: 13 }), td("266 kata punya banyak arti", { fontSize: 13 })],
  ], { x: 0.6, y: 1.55, w: 12.13, colW: [2.6, 6.8, 2.73], rowH: [0.45, 0.78, 0.78, 0.78, 0.78, 0.78, 0.78], fontSize: 13, fill: { color: HEX.white } });
  s.addNotes("Ini peta teknik yang diminta dosen. Direct dan transfer adalah pendekatan klasik berbasis aturan, kami buat sebagai pembanding. Model neural adalah sistem utama, dan encoder bersamanya paling dekat dengan konsep antarlingua. Augmentasi data kami lakukan lewat terjemahan pivot. Disambiguasi adalah pemilih arti kata berbasis kamus di aplikasi.");

  // ================= 6 ALUR =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Gambaran" });
  header(s, "Gambaran", "Dari sumber mentah ke aplikasi");
  const steps = [["FaBook", "Kumpulkan", "Korpus, buku pindai, skripsi, cerpen, berkas tim"], ["FaTools", "Bersihkan dan sejajarkan", "OCR, penyaringan, penyejajaran kalimat"], ["FaShieldAlt", "Normalisasi dan periksa", "Ejaan, deteksi bahasa, duplikat, dan kebocoran"], ["FaMicrochip", "Fine-tune", "NLLB-200 di GPU T4 Google Colab"], ["FaLaptop", "Uji dan sajikan", "Tiga set uji, aplikasi lokal, demo Colab"]];
  for (let i = 0; i < 5; i++) {
    const x = 0.6 + i * 2.45;
    card(s, x, 1.8, 2.2, 3.0, "Langkah alur");
    await badge(s, steps[i][0], x + 0.72, 2.05, 0.75, C.accent1);
    T(s, steps[i][1], { x: x + 0.1, y: 3.0, w: 2.0, h: 0.6, fontSize: 15, bold: true, align: "center" });
    T(s, steps[i][2], { x: x + 0.12, y: 3.65, w: 1.96, h: 1.1, fontSize: 12, color: C.accent5, align: "center" });
    if (i < 4) arrow(s, x + 2.2, 3.05);
  }
  card(s, 0.6, 5.2, 12.13, 1.5, "Kartu alat", C.text2);
  T(s, "Alat yang dipakai", { x: 0.9, y: 5.35, w: 3, h: 0.35, fontSize: 14, bold: true, color: C.accent2 });
  T(s, "PyMuPDF dan RapidOCR (buku pindai) · rapidfuzz dan datasketch (duplikat) · Hugging Face Transformers dan PyTorch (pelatihan) · sacreBLEU (penilaian) · Gradio (aplikasi) · Google Colab GPU T4", { x: 0.9, y: 5.75, w: 11.5, h: 0.8, fontSize: 14, color: C.background1 });
  s.addNotes("Lima tahap. Kami mengumpulkan data dari banyak tempat, membersihkan dan menyejajarkannya, menormalkan dan memeriksanya, melatih model, lalu menguji dan menyajikannya. Setiap tahap adalah satu perintah di kode kami, jadi seluruh alur bisa diulang.");

  // ================= 7 DASAR TEORI =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Gambaran" });
  header(s, "Dasar teori", "Dasar teori singkat");
  const th7 = [["FaProjectDiagram", "Transformer", "Model dengan encoder dan decoder. Encoder membaca kalimat sumber. Decoder menulis kalimat tujuan dengan melihat konteks (Vaswani dkk., 2017)."],
               ["FaGlobe", "NLLB-200", "Model terjemahan Meta untuk sekitar 200 bahasa, termasuk bahasa Aceh (kode ace_Latn). Kami memakai versi distilled 600 juta parameter."],
               ["FaDatabase", "NusaX dan FLORES-200", "NusaX: kalimat paralel untuk 10 bahasa daerah. FLORES-200: tolok ukur terjemahan dari Meta. Keduanya kami pakai untuk latih dan uji."],
               ["FaFileAlt", "Datasheets for Datasets", "Data harus punya catatan jelas: asal, isi, cara pengumpulan, dan lisensi. Prinsip ini kami terapkan pada korpus AcehX."]];
  for (let i = 0; i < 4; i++) {
    const x = 0.6 + (i % 2) * 6.15, y = 1.6 + Math.floor(i / 2) * 2.65;
    card(s, x, y, 5.98, 2.45, "Kartu teori");
    await badge(s, th7[i][0], x + 0.3, y + 0.3, 0.75, C.accent1);
    T(s, th7[i][1], { x: x + 1.3, y: y + 0.35, w: 4.4, h: 0.5, fontSize: 18, bold: true, valign: "middle" });
    T(s, th7[i][2], { x: x + 0.3, y: y + 1.15, w: 5.4, h: 1.2, fontSize: 14, color: C.accent5 });
  }
  s.addNotes("Dasar teorinya singkat. Transformer memakai encoder dan decoder. NLLB-200 adalah model terjemahan multibahasa dari Meta yang sudah mengenal bahasa Aceh. NusaX dan FLORES adalah data paralel dan tolok ukur. Dan kami mengikuti prinsip Datasheets for Datasets: setiap data dicatat asal dan lisensinya.");

  // ================= 8 CARA MENILAI =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Gambaran" });
  header(s, "Evaluasi", "Cara menilai terjemahan");
  const ms = [["FaListOl", "BLEU", "Menghitung kecocokan kelompok kata antara hasil model dan terjemahan manusia."], ["FaLanguage", "chrF", "Menghitung kecocokan kelompok huruf. Cocok untuk bahasa dengan banyak imbuhan."], ["FaCheckCircle", "chrF++", "chrF ditambah informasi kata. Ini skor utama kami."]];
  for (let i = 0; i < 3; i++) {
    const x = 0.6 + i * 4.1; card(s, x, 1.6, 3.93, 2.9, "Kartu metrik");
    await badge(s, ms[i][0], x + 0.3, 1.85, 0.75, C.accent1);
    T(s, ms[i][1], { x: x + 1.3, y: 1.9, w: 2.4, h: 0.65, fontSize: 24, bold: true, fontFace: "Georgia", valign: "middle" });
    T(s, ms[i][2], { x: x + 0.3, y: 2.9, w: 3.4, h: 1.5, fontSize: 15, color: C.accent5 });
  }
  card(s, 0.6, 4.8, 12.13, 2.0, "Kartu catatan", C.text2);
  T(s, "Cara membaca skor", { x: 0.9, y: 4.95, w: 6, h: 0.4, fontSize: 18, bold: true, color: C.accent2 });
  T(s, [{ text: "Skala 0 sampai 100. Makin tinggi makin baik.", options: { bullet: true, breakLine: true } }, { text: "BLEU 30,79 tidak berarti 30,79% kalimat benar.", options: { bullet: true, breakLine: true } }, { text: "Kami juga memeriksa contoh keluaran, karena salah makna dan negasi tidak terlihat dari skor.", options: { bullet: true } }], { x: 0.9, y: 5.4, w: 11.5, h: 1.3, fontSize: 15, color: C.background1, paraSpaceAfter: 5 });
  s.addNotes("Kami memakai tiga ukuran: BLEU, chrF, dan chrF++. Semua berskala 0 sampai 100 dan makin tinggi makin baik. Penting: skor ini bukan persentase kalimat yang benar. Karena itu kami juga memeriksa contoh keluaran model.");

  // ================= 9 DATA PARALEL =================
  section("Data");
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data" });
  header(s, "Data", "Data paralel yang kami kumpulkan");
  tbl(s, [
    [th("Sumber"), th("Isi"), th("Pasangan dipakai"), th("Lisensi / asal")],
    [td("NusaX-MT", { bold: true }), td("Terjemahan manusia Aceh–Indonesia (IndoNLP)"), td("500 latih, 100 validasi, 400 uji"), td("CC-BY-SA 4.0")],
    [td("FLORES-200", { bold: true }), td("Terjemahan profesional kalimat gaya Wikipedia (Meta)"), td("797 latih, 200 validasi, 1.012 uji"), td("CC-BY-SA 4.0")],
    [td("Hikayat Abu Sammah", { bold: true }), td("Syair dengan terjemahan, buku hasil pindai (Depdikbud)"), td("1.432 latih, 79 validasi, 143 uji"), td("Buku pemerintah, disebut sumbernya")],
    [td("Hikayat Malik Mawot", { bold: true }), td("Syair dan terjemahan (Inayati, UIN Ar-Raniry, 2017)"), td("350"), td("Skripsi, disebut sumbernya")],
    [td("Terjemahan Al-Qur'an", { bold: true }), td("Tgk. Mahjiddin Jusuf (Aceh) dan Kemenag (Indonesia)"), td("5.466 ayat"), td("Disebut sumbernya")],
    [td("Wikipedia (OPUS)", { bold: true }), td("Kalimat artikel Aceh dan Indonesia yang sejajar"), td("375 dari 557"), td("CC-BY-SA 4.0")],
    [td("Pivot NLLB-Seed", { bold: true }), td("Meta/OLDI: 6.193 kalimat Aceh buatan manusia dengan teks Inggris"), td("± 5.700"), td("CC-BY-SA 4.0")],
    [td("Terjemahan tim", { bold: true }), td("Berkas Andrie (5.000 baris) dan lima cerpen (103 pasang)"), td("2.798 dan 96"), td("Hasil kerja tim")],
  ], { x: 0.6, y: 1.5, w: 12.13, colW: [2.5, 5.0, 2.75, 1.88], rowH: [0.45, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62], fontSize: 13, fill: { color: HEX.white } });
  s.addNotes("Delapan sumber data paralel, yaitu kalimat Aceh dengan terjemahan Indonesia. Korpus terbuka: NusaX, FLORES, Wikipedia, dan NLLB-Seed. Buku dan skripsi yang kami digitalkan: Hikayat Abu Sammah dan Malik Mawot. Terjemahan Al-Qur'an. Dan terjemahan buatan tim kami sendiri. Semuanya dicatat sumber dan lisensinya di repositori.");

  // ================= 10 KORPUS ACEHX =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data" });
  header(s, "Data", "Korpus AcehX: isi berkas");
  tbl(s, [
    [th("Berkas"), th("Unit", "right"), th("Kandidat pasangan", "right")],
    [td("Corpus AcehX (TXT)", { bold: true }), td("63.367", { align: "right" }), td("Belum ada terjemahan", { align: "right" })],
    [td("Cerita (CSV)", { bold: true }), td("11.103", { align: "right" }), td("103", { align: "right" })],
    [td("Lagu dan puisi (CSV)", { bold: true }), td("5.271", { align: "right" }), td("0", { align: "right" })],
    [td("Berkas JSONL", { bold: true }), td("5.000", { align: "right" }), td("4.146", { align: "right" })],
  ], { x: 0.6, y: 1.55, w: 7.6, colW: [3.4, 1.5, 2.7], rowH: [0.5, 0.6, 0.6, 0.6, 0.6], fontSize: 14, fill: { color: HEX.white } });
  T(s, "Unit = baris TXT atau rekaman CSV/JSONL. Kandidat pasangan = kedua sisi teks terisi; belum berarti terjemahannya sudah divalidasi.", { x: 0.6, y: 4.5, w: 7.6, h: 0.7, fontSize: 12, color: C.accent5 });
  card(s, 0.6, 5.3, 7.6, 1.5, "Kartu isi");
  T(s, [{ text: "Cerita: 11.103 kalimat, 103 di antaranya berpasangan", options: { bullet: true, breakLine: true } }, { text: "Lagu: 6 koleksi, 3.675 larik. Puisi: 1 koleksi, 1.596 larik", options: { bullet: true } }], { x: 0.9, y: 5.45, w: 7.0, h: 1.2, fontSize: 14, paraSpaceAfter: 6 });
  [["63.346", "teks unik dari 63.367 baris TXT (21 duplikat)"], ["15.995", "teks unik dari 16.374 rekaman CSV"]].forEach(([n, l], i) => {
    const y = 1.55 + i * 2.7; card(s, 8.6, y, 4.13, 2.5, "Kartu angka");
    T(s, n, { x: 8.9, y: y + 0.3, w: 3.6, h: 0.9, fontSize: 44, bold: true, color: C.accent1, fontFace: "Georgia" }); T(s, l, { x: 8.9, y: y + 1.3, w: 3.6, h: 1.0, fontSize: 15, color: C.accent5 });
  });
  s.addNotes("Ini hasil audit korpus AcehX. Ada empat berkas. Corpus TXT punya 63.367 baris Aceh tanpa terjemahan. Dua berkas CSV, cerita dan lagu-puisi, punya 16.374 rekaman, dan hanya 103 yang punya dua sisi bahasa. Berkas JSONL punya 5.000 rekaman dengan 4.146 kandidat pasangan. Kami memisahkan jumlah unit dari jumlah pasangan, karena sebagian besar bahan masih satu bahasa.");

  // ================= 11 SCREENING =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data" });
  header(s, "Data", "Status screening: KEEP, REVIEW, DROP");
  hBars(s, { x: 0.6, y: 1.5, w: 7.6, h: 3.1, title: "Status 16.374 rekaman CSV", labels: ["KEEP", "REVIEW", "DROP"], values: [4433, 11562, 379], colors: [HEX.teal, HEX.gold, HEX.slate], max: 13000, labelW: 1.4, fmt: (v) => nf(v), fontSize: 15 });
  card(s, 0.6, 4.85, 7.6, 1.95, "Kartu arti");
  T(s, [{ text: "KEEP: lolos pemeriksaan awal", options: { bullet: true, breakLine: true } }, { text: "REVIEW: perlu ditinjau lagi", options: { bullet: true, breakLine: true } }, { text: "DROP: dikeluarkan, tetap disimpan untuk penelusuran", options: { bullet: true } }], { x: 0.9, y: 5.0, w: 7.1, h: 1.7, fontSize: 15, paraSpaceAfter: 6 });
  [["2,31%", "duplikat (379 dari 16.374). Batas di brief: 5%"], ["80", "templat menghasilkan 10.000 unit cerita; partisi nanti dibuat per templat"], ["Penutur", "meninjau rekaman REVIEW: langkah berikutnya"]].forEach(([n, l], i) => {
    const y = 1.6 + i * 1.75; card(s, 8.6, y, 4.13, 1.55, "Kartu angka");
    T(s, n, { x: 8.85, y: y + 0.15, w: 3.7, h: 0.7, fontSize: 30, bold: true, color: C.accent1, fontFace: "Georgia", valign: "middle" }); T(s, l, { x: 8.85, y: y + 0.85, w: 3.7, h: 0.65, fontSize: 13, color: C.accent5 });
  });
  s.addNotes("Setiap rekaman diberi status. KEEP berarti lolos pemeriksaan awal, REVIEW berarti perlu ditinjau lagi, DROP berarti dikeluarkan tetapi tetap disimpan. Ada 4.433 KEEP, 11.562 REVIEW, dan 379 DROP. Semua DROP adalah duplikat persis, sekitar 2,31 persen, di bawah batas 5 persen di brief. Status ini adalah penyaringan awal, bukan pengesahan mutu. Peninjauan oleh penutur adalah langkah berikutnya.");

  // ================= 12 CAMPURAN DATA LATIH =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data" });
  header(s, "Data", "Campuran data latih: 17.547 pasangan");
  hBars(s, { x: 0.6, y: 1.5, w: 7.9, h: 5.3, labels: ["Ayat Al-Qur'an", "Pivot NLLB-Seed (±)", "Tim: pasangan Andrie", "Hikayat Abu Sammah", "FLORES (dev)", "NusaX (latih)", "Wikipedia", "Hikayat Malik Mawot", "Tim: cerpen"], values: [5466, 5733, 2798, 1432, 797, 500, 375, 350, 96], colors: [HEX.teal], max: 6200, labelW: 2.7, fmt: (v) => nf(v), fontSize: 13 });
  card(s, 8.9, 1.6, 3.83, 1.45, "Kartu angka"); stat(s, 9.15, 1.68, 3.4, "379", "validasi: 200 FLORES, 79 hikayat, 100 NusaX", { size: 34, lh: 0.7 });
  card(s, 8.9, 3.25, 3.83, 2.1, "Kartu angka");
  T(s, "Set uji (tidak dilatih)", { x: 9.15, y: 3.35, w: 3.4, h: 0.4, fontSize: 15, bold: true });
  [["400", "NusaX"], ["1.012", "FLORES"], ["143", "Hikayat"]].forEach(([n, l], i) => { T(s, n, { x: 9.15, y: 3.8 + i * 0.5, w: 1.3, h: 0.45, fontSize: 22, bold: true, color: C.accent1, fontFace: "Georgia", valign: "middle" }); T(s, l, { x: 10.5, y: 3.8 + i * 0.5, w: 2.1, h: 0.45, fontSize: 14, color: C.accent5, valign: "middle" }); });
  card(s, 8.9, 5.55, 3.83, 1.25, "Kartu angka"); T(s, "17.618 kandidat menjadi 17.547 setelah 1 pasangan mirip dan 70 duplikat dibuang", { x: 9.15, y: 5.6, w: 3.4, h: 1.15, fontSize: 13, valign: "middle" });
  s.addNotes("Inilah isi pelatihan yang sebenarnya, tercatat di manifest: 17.547 pasangan. Al-Qur'an dan data pivot adalah bagian terbesar, disusul terjemahan tim dan hikayat. Awalnya ada 17.618 kandidat. Satu pasangan yang terlalu mirip dan 70 duplikat dibuang, dan tidak ada kecocokan persis dengan data yang dilindungi. Validasi 379 pasangan dipakai memilih epoch terbaik. Tiga set uji dipisah sepenuhnya.");

  // ================= 13 BUKU PINDAI =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data" });
  header(s, "Data", "Dari buku pindai ke pasangan kalimat");
  const bs = ["OCR setiap halaman dengan 300 dpi (RapidOCR)", "Buang nomor halaman, judul, catatan kaki, dan baris yang kurang yakin", "Gabungkan baris yang terpotong tata letak", "Perbaiki huruf salah hasil OCR, hanya jika teks acuan membenarkannya", "Sejajarkan bait Aceh dan bait Indonesia dengan pemrograman dinamis", "Beri label KEEP atau REVIEW, tidak ada yang dihapus"];
  bs.forEach((t, i) => {
    const y = 1.55 + i * 0.85;
    s.addShape(pres.shapes.OVAL, { x: 0.6, y, w: 0.55, h: 0.55, fill: { color: C.accent1 }, line: { color: C.accent1, width: 0 }, objectName: "Nomor langkah" });
    T(s, String(i + 1), { x: 0.6, y, w: 0.55, h: 0.55, fontSize: 16, bold: true, color: C.background1, align: "center", valign: "middle" });
    T(s, t, { x: 1.35, y: y - 0.04, w: 5.9, h: 0.7, fontSize: 14, valign: "middle" });
  });
  [["11,3% → 0,8%", "kata salah: teks bawaan PDF dibanding OCR kami (contoh yang diperiksa tangan)"], ["1.856", "pasangan bait hasil penyejajaran"], ["1.654", "pasangan berlabel KEEP (199 berlabel REVIEW)"], ["40 dari 40", "pasangan KEEP acak yang diperiksa tangan ternyata benar"]].forEach(([n, l], i) => {
    const x = 7.7 + (i % 2) * 2.6, y = 1.55 + Math.floor(i / 2) * 2.55;
    card(s, x, y, 2.45, 2.35, "Kartu angka");
    T(s, n, { x: x + 0.15, y: y + 0.2, w: 2.15, h: 0.8, fontSize: i === 0 ? 20 : i === 3 ? 24 : 30, bold: true, color: C.accent1, fontFace: "Georgia", valign: "middle" });
    T(s, l, { x: x + 0.15, y: y + 1.1, w: 2.15, h: 1.15, fontSize: 12, color: C.accent5 });
  });
  s.addNotes("Hikayat Abu Sammah adalah buku cetak hasil pindai. Bagian Aceh dan bagian Indonesia ada di halaman berbeda. Teks bawaan PDF kurang baik: 11,3 persen kata salah pada contoh yang kami periksa tangan. Setelah kami baca ulang dengan OCR 300 dpi, kata salah turun menjadi 0,8 persen. Lalu kami bersihkan dan sejajarkan bait dengan pemrograman dinamis. Dari 40 pasangan KEEP acak yang kami periksa, 40 benar.");

  // ================= 14 SKRIPSI, CERPEN, TIM =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data" });
  header(s, "Data", "Skripsi, cerpen, dan terjemahan tim");
  const cols = [
    ["FaBookOpen", "Hikayat Malik Mawot", [["1.030", "baris syair dan terjemahan"], ["350", "pasangan dipakai"]], "Catatan kaki dibuang. Tiap pasangan diperiksa kemiripan baris dan bahasa Acehnya."],
    ["FaListOl", "Berkas tim (Andrie)", [["5.000", "baris diterima"], ["2.798", "pasangan setelah dibersihkan"]], "Baris dengan galat OCR berat, tanpa terjemahan, atau sama dengan set uji dibuang."],
    ["FaFileAlt", "Lima cerpen", [["103", "pasangan kalimat bernomor"], ["96", "pasangan dipakai"]], "Tabel sudah disejajarkan manusia. Baris yang terlalu pendek atau kurang jelas dibuang."],
  ];
  for (let i = 0; i < 3; i++) {
    const x = 0.6 + i * 4.1;
    card(s, x, 1.55, 3.93, 5.2, "Kartu sumber");
    await badge(s, cols[i][0], x + 0.3, 1.8, 0.8, C.accent1);
    T(s, cols[i][1], { x: x + 1.25, y: 1.85, w: 2.55, h: 0.7, fontSize: 17, bold: true, valign: "middle" });
    cols[i][2].forEach(([n, l], k) => { T(s, n, { x: x + 0.3, y: 2.9 + k * 1.05, w: 1.7, h: 0.7, fontSize: 32, bold: true, color: k ? C.accent1 : C.accent5, fontFace: "Georgia", valign: "middle" }); T(s, l, { x: x + 2.0, y: 2.9 + k * 1.05, w: 1.75, h: 0.7, fontSize: 12, color: C.accent5, valign: "middle" }); });
    T(s, cols[i][3], { x: x + 0.3, y: 5.2, w: 3.35, h: 1.4, fontSize: 14 });
  }
  s.addNotes("Tiga sumber yang lebih kecil, masing-masing butuh cara baca sendiri. Malik Mawot adalah skripsi dengan baris Aceh yang diikuti terjemahannya. Kami pisahkan per baris, buang catatan kaki, dan simpan hanya pasangan yang lolos pemeriksaan kemiripan dan bahasa. Berkas tim menghasilkan 2.798 pasangan bersih. Lima cerpen menghasilkan 96 pasangan kalimat.");

  // ================= 15 AUGMENTASI =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data" });
  header(s, "Augmentasi data", "Terjemahan pivot: ± 5.700 pasangan");
  const bx = [["Bahasa Aceh", "6.193 kalimat buatan manusia (NLLB-Seed)", HEX.teal], ["Bahasa Inggris", "Arti yang sama, dari dataset yang sama", HEX.slate], ["NLLB Inggris ke Indonesia", "Arah terjemahan yang sangat kuat", HEX.deep], ["Pasangan latih", "Aceh manusia + Indonesia mesin, diberi label", HEX.gold]];
  bx.forEach(([t, d, col], i) => {
    const x = 0.6 + i * 3.1;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.65, w: 2.8, h: 1.9, rectRadius: 0.12, fill: { color: col }, line: { color: col, width: 0 }, objectName: "Kotak alur" });
    T(s, t, { x: x + 0.15, y: 1.8, w: 2.5, h: 0.7, fontSize: 16, bold: true, color: i === 3 ? HEX.ink : HEX.white, valign: "middle" });
    T(s, d, { x: x + 0.15, y: 2.5, w: 2.5, h: 0.95, fontSize: 12, color: i === 3 ? HEX.ink : HEX.white });
    if (i < 3) arrow(s, x + 2.8, 2.45);
  });
  card(s, 0.6, 3.95, 5.9, 2.85, "Kartu filter");
  T(s, "Penyaringan sebelum pasangan dipakai", { x: 0.9, y: 4.1, w: 5.4, h: 0.4, fontSize: 16, bold: true });
  T(s, [{ text: "4 sampai 60 kata di tiap sisi", options: { bullet: true, breakLine: true } }, { text: "Perbandingan jumlah kata kedua sisi antara 0,5 dan 2", options: { bullet: true, breakLine: true } }, { text: "Sisi Aceh harus lolos deteksi bahasa", options: { bullet: true, breakLine: true } }, { text: "Diperiksa agar tidak bocor ke set validasi dan uji", options: { bullet: true } }], { x: 0.9, y: 4.55, w: 5.4, h: 2.15, fontSize: 15, paraSpaceAfter: 8 });
  card(s, 6.83, 3.95, 5.9, 2.85, "Kartu hasil");
  stat(s, 7.13, 4.1, 2.6, "5.750", "kandidat setelah disaring", { size: 40, lh: 0.6 });
  stat(s, 10.0, 4.1, 2.6, "5.733", "pasangan dipertahankan sebelum digabung", { size: 40, lh: 0.8 });
  T(s, "Sisi Indonesia adalah hasil mesin, jadi asalnya dicatat di metadata.", { x: 7.13, y: 5.85, w: 5.4, h: 0.85, fontSize: 14 });
  s.addNotes("Augmentasi data berarti membuat data latih baru dari data yang ada. NLLB-Seed punya sekitar enam ribu kalimat Aceh buatan manusia dengan teks Inggris. Terjemahan Inggris ke Indonesia adalah salah satu arah terkuat NLLB, jadi kami menerjemahkan sisi Inggris ke Indonesia dan memasangkannya dengan kalimat Aceh asli. Setelah disaring ada 5.750 kandidat dan 5.733 pasangan dipertahankan. Sisi Indonesia adalah hasil mesin dan ditandai demikian.");

  // ================= 16 MENYIAPKAN TEKS =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data" });
  header(s, "Data", "Menyiapkan dan memeriksa teks");
  const pc = [["FaLanguage", "Normalisasi", "Aturan sama untuk pelatihan dan aplikasi", ["Unicode NFC dan tanda kutip lurus", "Ejaan lama: njang → nyang, djipeugot → jipeugot", "Tanda dua titik dibuang: löen → loen", "Teks asli selalu disimpan di samping teks normal"]],
              ["FaSearch", "Deteksi bahasa", "Model n-gram huruf (naive Bayes)", ["Dilatih dari AcehX dan NusaX latih", "Bahasa Aceh dikenali 96–98%", "Bahasa Indonesia dikenali 99,5–100%", "Menyaring baris asing atau berisik"]],
              ["FaClone", "Kontrol duplikat", "Kecocokan persis dan hampir sama", ["Kunci cocok mengabaikan huruf besar, aksen, tanda baca, ejaan lama", "Hampir sama: kemiripan 90% atau lebih (rapidfuzz)", "MinHash-LSH terhadap AcehX (164.778 baris)", "Duplikat ditandai, tidak dibuang diam-diam"]]];
  for (let i = 0; i < 3; i++) {
    const x = 0.6 + i * 4.1;
    card(s, x, 1.55, 3.93, 5.2, "Kartu pemeriksaan");
    await badge(s, pc[i][0], x + 0.3, 1.8, 0.75, C.accent1);
    T(s, pc[i][1], { x: x + 1.25, y: 1.8, w: 2.5, h: 0.4, fontSize: 17, bold: true });
    T(s, pc[i][2], { x: x + 1.25, y: 2.2, w: 2.5, h: 0.5, fontSize: 11, color: C.accent5 });
    T(s, pc[i][3].map((t, k) => ({ text: t, options: { bullet: true, breakLine: k < 3 } })), { x: x + 0.3, y: 3.05, w: 3.4, h: 3.6, fontSize: 14, paraSpaceAfter: 10 });
  }
  s.addNotes("Tiga pemeriksaan sebelum teks masuk model. Normalisasi menyamakan ejaan, dan aplikasi memakai aturan yang sama persis. Pendeteksi bahasa dari n-gram huruf membuang baris yang bukan bahasa Aceh. Kontrol duplikat memakai kunci pembanding dan pencocokan hampir sama, agar kalimat yang sama tidak muncul dua kali atau bocor ke data uji.");

  // ================= 17 UJI JUJUR =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data" });
  header(s, "Desain evaluasi", "Menjaga ujian tetap jujur");
  const hs = ["Halaman uji dan validasi dijaga sebagai satu blok, jadi bait yang bersebelahan tidak terpisah", "Pasangan latih yang sama dengan kalimat validasi atau uji dibuang, tanpa memandang huruf besar, aksen, tanda baca, dan ejaan lama", "Pasangan latih yang 90% atau lebih mirip dengan kalimat uji dibuang", "Skrip pelatihan menolak mulai jika masih ada satu kebocoran", "Epoch terbaik dipilih dari validasi saja, tidak dari set uji"];
  hs.forEach((t, i) => { const y = 1.6 + i * 1.05; card(s, 0.6, y, 7.3, 0.9, "Kartu aturan"); T(s, String(i + 1), { x: 0.8, y, w: 0.5, h: 0.9, fontSize: 24, bold: true, color: C.accent1, fontFace: "Georgia", valign: "middle" }); T(s, t, { x: 1.4, y, w: 6.35, h: 0.9, fontSize: 13, valign: "middle" }); });
  [["Latih", "17.547", HEX.teal, HEX.white], ["Validasi", "379", HEX.gold, HEX.ink], ["Uji", "1.555", HEX.deep, HEX.white]].forEach(([n, v, col, tc], i) => {
    const y = 1.6 + i * 1.75;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.5, y, w: 4.23, h: 1.55, rectRadius: 0.12, fill: { color: col }, line: { color: col, width: 0 }, objectName: "Kotak pembagian" });
    T(s, v, { x: 8.8, y: y + 0.15, w: 3.6, h: 0.8, fontSize: 40, bold: true, color: tc, fontFace: "Georgia" });
    T(s, n + (i === 2 ? " (400 + 1.012 + 143)" : ""), { x: 8.8, y: y + 0.95, w: 3.6, h: 0.45, fontSize: 14, color: tc });
  });
  s.addNotes("Skor hanya berarti jika model belum pernah melihat kalimat ujian. Karena itu kami melindunginya berlapis. Halaman dijaga satu blok, kecocokan persis dan hampir sama dibuang, dan skrip pelatihan berhenti jika ada kebocoran. Pada run yang tercatat, jumlah kecocokan persis dengan data yang dilindungi adalah nol. Epoch terbaik dipilih dari validasi, jadi set uji hanya dipakai sekali di akhir.");

  // ================= 18 MODEL DAN PENGATURAN =================
  section("Metode");
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Metode" });
  header(s, "Metode", "Model dan pengaturan pelatihan");
  tbl(s, [
    [th("Pengaturan"), th("Nilai"), th("Alasan")],
    [td("Model dasar", { bold: true }), td("NLLB-200 distilled, 600 juta parameter"), td("Sudah mengenal bahasa Aceh (ace_Latn)")],
    [td("Yang dilatih", { bold: true }), td("Seluruh bobot"), td("Menyesuaikan seluruh model dengan data kami")],
    [td("Optimizer", { bold: true }), td("Adafactor, laju belajar 1e-4, pemanasan 10%"), td("Hemat memori, muat di GPU T4 Colab")],
    [td("Batch dan panjang", { bold: true }), td("8 pasangan, sampai 128 token"), td("Muat di memori GPU")],
    [td("Label smoothing", { bold: true }), td("0,1"), td("Mengurangi terlalu percaya diri pada data kecil")],
    [td("Penghentian", { bold: true }), td("Maksimal 10 epoch, sabar 2 epoch"), td("Berhenti jika validasi tidak naik")],
    [td("Pemilihan model", { bold: true }), td("Epoch terbaik menurut chrF++ validasi"), td("Set uji tidak ikut memilih")],
    [td("Model tersimpan", { bold: true }), td("Setengah presisi (FP16), 1,2 GB"), td("Terjemahan sama, ukuran separuh")],
  ], { x: 0.6, y: 1.5, w: 12.13, colW: [2.6, 5.3, 4.23], rowH: [0.45, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62, 0.62], fontSize: 13, fill: { color: HEX.white } });
  s.addNotes("Kami mulai dari NLLB-200 distilled 600 juta parameter, yang sudah mengenal bahasa Aceh. Seluruh bobot dilatih dengan optimizer Adafactor yang hemat memori, sehingga muat di GPU gratis. Label smoothing dan penghentian dini mencegah model menghafal data. Model disimpan dalam setengah presisi agar ukurannya separuh tanpa mengubah terjemahan. Pengaturan ini berasal dari kode pelatihan di repositori kami.");

  // ================= 19 PROSES LATIHAN =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Metode" });
  header(s, "Metode", "Proses pelatihan");
  lineChart(s, { x: 0.6, y: 1.5, w: 7.9, h: 5.3, title: "chrF++ validasi per epoch", labels: ["Dasar", "Epoch 1", "Epoch 2", "Epoch 3", "Epoch 4", "Epoch 5"], values: [41.43, 52.85, 54.67, 55.72, 55.33, 55.01], min: 40, max: 58, ticks: [40, 44, 48, 52, 56], color: HEX.teal });
  [["Epoch 3 dari 5", "dipilih; berhenti setelah 2 epoch tanpa kenaikan"], ["3,39 → 2,31", "loss latih, epoch 1 sampai 5"], ["GPU T4", "Google Colab, 17.547 pasangan"]].forEach(([n, l], i) => {
    const y = 1.6 + i * 1.75; card(s, 8.9, y, 3.83, 1.55, "Kartu angka");
    T(s, n, { x: 9.15, y: y + 0.18, w: 3.4, h: 0.7, fontSize: 26, bold: true, color: C.accent1, fontFace: "Georgia" }); T(s, l, { x: 9.15, y: y + 0.88, w: 3.4, h: 0.6, fontSize: 13, color: C.accent5 });
  });
  s.addNotes("Skor validasi model dasar adalah 41,43. Setelah epoch pertama naik menjadi 52,85, dan mencapai 55,72 di epoch ketiga. Setelah itu sedikit turun, padahal loss latih terus turun. Itu tanda model mulai menghafal data latih. Pelatihan berhenti dini setelah epoch kelima dan kami memakai epoch ketiga, yang terbaik pada validasi.");

  // ================= 20 HASIL =================
  section("Hasil");
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Hasil" });
  header(s, "Hasil", "Skor naik di semua set uji");
  colChart(s, { x: 0.6, y: 1.5, w: 6.6, h: 5.3, title: "chrF++ (makin tinggi makin baik)", groups: [{ label: "NusaX (400)", vals: [38.66, 57.15] }, { label: "FLORES (1.012)", vals: [46.27, 52.81] }, { label: "Hikayat (143)", vals: [23.98, 60.92] }], series: ["Model dasar NLLB-200", "Model kami (fine-tuned)"], colors: [HEX.mist, HEX.teal], dec: 2, max: 70, ticks: [0, 10, 20, 30, 40, 50, 60, 70] });
  tbl(s, [[th("Set uji"), th("BLEU", "center"), th("chrF", "center"), th("chrF++", "center")],
          [td("NusaX", { bold: true }), td("13,53 → 30,79", { align: "center" }), td("41,58 → 59,64", { align: "center" }), td("38,66 → 57,15", { align: "center" })],
          [td("FLORES", { bold: true }), td("21,31 → 27,32", { align: "center" }), td("48,74 → 55,05", { align: "center" }), td("46,27 → 52,81", { align: "center" })],
          [td("Hikayat", { bold: true }), td("2,68 → 35,94", { align: "center" }), td("26,84 → 63,02", { align: "center" }), td("23,98 → 60,92", { align: "center" })]],
    { x: 7.4, y: 1.7, w: 5.33, colW: [0.95, 1.46, 1.46, 1.46], rowH: [0.5, 0.5, 0.5, 0.5], fontSize: 11, fill: { color: HEX.white } });
  card(s, 7.4, 4.0, 5.33, 2.8, "Kartu catatan");
  T(s, "Cara membaca", { x: 7.65, y: 4.15, w: 4.8, h: 0.4, fontSize: 16, bold: true });
  T(s, "Tabel: model dasar → model kami. Kalimat uji tidak pernah dilatih dan tidak dipakai memilih model. Hikayat paling dekat dengan data syair kami; NusaX dan FLORES menunjukkan pemakaian sehari-hari.", { x: 7.65, y: 4.6, w: 4.85, h: 2.15, fontSize: 14, color: C.accent5 });
  s.addNotes("Hasil utama. Pada NusaX, chrF++ naik dari 38,7 menjadi 57,1, atau 18,49 poin. Pada FLORES naik dari 46,3 menjadi 52,8, atau 6,54 poin. Pada hikayat naik dari 24,0 menjadi 60,9, atau 36,94 poin. BLEU dan chrF ikut naik di ketiganya: BLEU naik 17,26, 6,01, dan 33,26 poin. Besarnya kenaikan berbeda antar jenis teks, jadi kami melaporkan ketiganya terpisah dan tidak membuat satu rata-rata. Hikayat paling dekat dengan data syair kami, sehingga NusaX dan FLORES lebih mewakili pemakaian sehari-hari.");

  // ================= 21 KLASIK VS NEURAL =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Hasil" });
  header(s, "Hasil", "Pendekatan klasik dan neural");
  hBars(s, { x: 0.6, y: 1.5, w: 7.9, h: 5.3, title: "chrF++ pada 400 kalimat uji NusaX", labels: ["Salin sumber (tanpa terjemah)", "Direct (kamus)", "Transfer (aturan)", "NLLB dasar", "NLLB fine-tuned"], values: [32.0, 35.5, 39.2, 38.7, 57.1], colors: [HEX.mist, HEX.slate, HEX.slate, HEX.mist, HEX.teal], max: 65, labelW: 3.0, fmt: (v) => nf(v, 1), fontSize: 14 });
  [["+3,5", "Direct dibanding menyalin sumber"], ["+3,7", "Transfer dibanding direct"], ["+17,9", "Neural fine-tuned dibanding transfer"]].forEach(([n, l], i) => {
    const y = 1.6 + i * 1.75; card(s, 8.9, y, 3.83, 1.55, "Kartu angka");
    T(s, n, { x: 9.15, y: y + 0.2, w: 3.4, h: 0.7, fontSize: 36, bold: true, color: C.accent1, fontFace: "Georgia" }); T(s, l, { x: 9.15, y: y + 0.95, w: 3.4, h: 0.5, fontSize: 13, color: C.accent5 });
  });
  s.addNotes("Ini menjawab pertanyaan dosen tentang pendekatan klasik. Menyalin teks Aceh tanpa diterjemahkan menghasilkan 32,0. Pendekatan direct dengan kamus kata demi kata mencapai 35,5. Dengan analisis dan aturan transfer menjadi 39,2. Model neural yang di-fine-tune mencapai 57,1. Catatan: pada BLEU, NLLB dasar (13,5) lebih tinggi dari transfer (9,1), dan direct (6,1) sedikit di bawah menyalin sumber (6,3). Kesamaan huruf dan kesesuaian susunan kata tidak selalu naik bersama.");

  // ================= 22 DIRECT DAN TRANSFER =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Hasil" });
  header(s, "Teknik", "Direct dan transfer lebih dekat");
  card(s, 0.6, 1.55, 5.95, 3.1, "Kartu direct");
  T(s, "Pendekatan direct", { x: 0.9, y: 1.7, w: 5.4, h: 0.4, fontSize: 18, bold: true, color: C.accent1 });
  T(s, [{ text: "Cari tiap kata di daftar kamus 1985", options: { bullet: true, breakLine: true } }, { text: "Ambil arti pendek pertama", options: { bullet: true, breakLine: true } }, { text: "Urutan kata Aceh tetap", options: { bullet: true, breakLine: true } }, { text: "Kata yang tidak ada dibiarkan", options: { bullet: true } }], { x: 0.9, y: 2.2, w: 5.4, h: 2.3, fontSize: 16, paraSpaceAfter: 8 });
  card(s, 6.78, 1.55, 5.95, 3.1, "Kartu transfer");
  T(s, "Pendekatan transfer", { x: 7.08, y: 1.7, w: 5.4, h: 0.4, fontSize: 18, bold: true, color: C.accent1 });
  T(s, [{ text: "Analisis: pecah awalan ji-, geu-, neu-, ta- dan akhiran -jih", options: { bullet: true, breakLine: true } }, { text: "Transfer: 15 kata fungsi, mis. hana → tidak, nyang → yang, lon → saya", options: { bullet: true, breakLine: true } }, { text: "Hasil: susun dan beri huruf kapital", options: { bullet: true, breakLine: true } }, { text: "Tiap kata dipakai hanya jika NusaX mendukung (50%+ dari 20+ kalimat)", options: { bullet: true } }], { x: 7.08, y: 2.2, w: 5.4, h: 2.3, fontSize: 14, paraSpaceAfter: 6 });
  card(s, 0.6, 4.9, 12.13, 1.95, "Kartu contoh", C.text2);
  T(s, "Contoh nyata dari set uji NusaX", { x: 0.9, y: 5.0, w: 6, h: 0.35, fontSize: 14, bold: true, color: C.accent2 });
  [["Aceh", "Toe ngon hotel lon dom"], ["Direct", "Toe meuteumee hotel padam bermalam"], ["Transfer", "Toe dengan hotel saya bermalam"], ["Acuan", "Dekat dengan hotel saya menginap"]].forEach(([a, b], i) => {
    const x = 0.9 + (i % 2) * 6.0, y = 5.4 + Math.floor(i / 2) * 0.62;
    T(s, a, { x, y, w: 1.2, h: 0.5, fontSize: 13, bold: true, color: C.accent6, valign: "middle" }); T(s, b, { x: x + 1.25, y, w: 4.6, h: 0.5, fontSize: 14, color: C.background1, valign: "middle" });
  });
  s.addNotes("Direct mencari tiap kata di kamus dan mempertahankan urutan. Transfer lebih dulu menganalisis kata Aceh: memecah awalan dan akhiran -jih, lalu memindahkan sejumlah kecil kata fungsi dengan aturan, lalu menyusun kalimat. Kami hanya memakai aturan yang didukung data latih NusaX. Pada contoh, direct mengubah 'lon' menjadi 'padam', sedangkan transfer memberi 'saya' yang benar.");

  // ================= 23 ANTARLINGUA =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Hasil" });
  header(s, "Teknik", "Pandangan antarlingua: ruang bersama");
  const fl = [["Teks Aceh", "Tag ace_Latn menandai bahasa sumber", HEX.slate], ["Encoder", "Membaca potongan kata dan membuat vektor makna", HEX.teal], ["Ruang bersama", "Satu representasi untuk sekitar 200 bahasa", HEX.gold], ["Decoder", "Menulis token satu per satu; tag ind_Latn memilih bahasa Indonesia", HEX.teal], ["Teks Indonesia", "Token digabung menjadi kalimat", HEX.slate]];
  fl.forEach(([t, d, col], i) => {
    const x = 0.6 + i * 2.45, tc = i === 2 ? HEX.ink : HEX.white;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.7, w: 2.2, h: 2.6, rectRadius: 0.12, fill: { color: col }, line: { color: col, width: 0 }, objectName: "Kotak alur" });
    T(s, t, { x: x + 0.15, y: 1.85, w: 1.9, h: 0.6, fontSize: 15, bold: true, color: tc, valign: "middle" }); T(s, d, { x: x + 0.15, y: 2.5, w: 1.9, h: 1.7, fontSize: 13, color: tc });
    if (i < 4) arrow(s, x + 2.2, 2.85);
  });
  const pt = [["FaGlobe", "Satu model bersama", "Semua bahasa melewati representasi yang sama. Ini versi yang dipelajari dari antarlingua buatan tangan."], ["FaEye", "Terlihat di aplikasi", "Panel 'Cara kerja model' menampilkan token encoder dan decoder yang sebenarnya."], ["FaExchangeAlt", "Dipilih lewat tag", "Tag bahasa memilih sumber dan tujuan, jadi model yang sama bisa menerjemahkan ke dua arah."]];
  for (let i = 0; i < 3; i++) { const x = 0.6 + i * 4.1; await badge(s, pt[i][0], x, 4.75, 0.7, C.accent1); T(s, pt[i][1], { x: x + 0.9, y: 4.72, w: 3.0, h: 0.4, fontSize: 15, bold: true }); T(s, pt[i][2], { x: x + 0.9, y: 5.15, w: 3.0, h: 1.7, fontSize: 13, color: C.accent5 }); }
  s.addNotes("Pada terjemahan antarlingua, kalimat sumber diubah menjadi makna yang tidak terikat bahasa, lalu kalimat tujuan ditulis dari makna itu. Sistem klasik membuat representasi itu dengan tangan. NLLB mempelajarinya: encoder-nya memetakan semua bahasa ke ruang bersama, dan decoder menulis bahasa tujuan dari ruang itu. Tag ace_Latn dan ind_Latn memilih sumber dan tujuan. Aplikasi kami menampilkan token encoder dan decoder yang sebenarnya.");

  // ================= 24 DISAMBIGUASI =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Hasil" });
  header(s, "Teknik", "Disambiguasi berbasis kamus");
  const ds = ["Cari tiap kata Aceh di antara 5.260 kata dalam Kamus Aceh-Indonesia (1985)", "Kumpulkan semua arti kata itu", "Beri skor tiap arti menurut kata yang sama dengan terjemahan model, tanpa kata hubung umum", "Beri tanda centang pada arti terbaik jika jelas unggul"];
  ds.forEach((t, i) => {
    const y = 1.6 + i * 1.2;
    s.addShape(pres.shapes.OVAL, { x: 0.6, y, w: 0.6, h: 0.6, fill: { color: C.accent1 }, line: { color: C.accent1, width: 0 }, objectName: "Nomor langkah" });
    T(s, String(i + 1), { x: 0.6, y, w: 0.6, h: 0.6, fontSize: 18, bold: true, color: C.background1, align: "center", valign: "middle" });
    T(s, t, { x: 1.45, y: y - 0.1, w: 5.5, h: 1.0, fontSize: 14, valign: "middle" });
  });
  card(s, 7.4, 1.55, 5.33, 3.4, "Kartu contoh", C.text2);
  T(s, "Contoh", { x: 7.7, y: 1.7, w: 3, h: 0.35, fontSize: 14, bold: true, color: C.accent2 });
  T(s, "Gobnyan jak u keude", { x: 7.7, y: 2.1, w: 4.8, h: 0.4, fontSize: 17, bold: true, color: C.background1 });
  T(s, "Terjemahan: Dia pergi ke toko", { x: 7.7, y: 2.55, w: 4.8, h: 0.4, fontSize: 14, color: C.background2 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.7, y: 3.15, w: 4.75, h: 0.75, rectRadius: 0.1, fill: { color: HEX.teal }, line: { color: HEX.teal, width: 0 }, objectName: "Arti terbaik" });
  s.addImage({ data: await icon("FaCheck", HEX.white), x: 7.9, y: 3.38, w: 0.3, h: 0.3, altText: "Tanda centang" });
  T(s, "keude: kedai, toko …", { x: 8.35, y: 3.15, w: 4.0, h: 0.75, fontSize: 14, bold: true, color: C.background1, valign: "middle" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.7, y: 4.05, w: 4.75, h: 0.7, rectRadius: 0.1, fill: { color: C.text1 }, line: { color: C.text1, width: 0 }, objectName: "Arti lain" });
  T(s, "keude: endapan sisa masakan berkuah", { x: 7.85, y: 4.05, w: 4.5, h: 0.7, fontSize: 14, color: C.background2, valign: "middle" });
  [["5.260", "kata di kamus"], ["266", "kata punya banyak arti"]].forEach(([n, l], i) => { const x = 7.4 + i * 2.75; card(s, x, 5.2, 2.58, 1.6, "Kartu angka"); T(s, n, { x: x + 0.2, y: 5.3, w: 2.2, h: 0.7, fontSize: 32, bold: true, color: C.accent1, fontFace: "Georgia" }); T(s, l, { x: x + 0.2, y: 6.0, w: 2.2, h: 0.6, fontSize: 13, color: C.accent5 }); });
  s.addNotes("Banyak kata Aceh punya lebih dari satu arti. Untuk tiap kata dalam kalimat, modul kami mencari semua artinya di daftar Kamus Aceh-Indonesia 1985. Setiap arti diberi skor menurut berapa banyak kata isinya yang sama dengan terjemahan model, lalu arti terbaik diberi tanda centang jika jelas unggul. Pada contoh, keude punya dua arti dan yang menyebut toko cocok dengan terjemahan. Ini tampil di aplikasi sebagai panel Kata per kata.");

  // ================= 25 CONTOH TERJEMAHAN =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Hasil" });
  header(s, "Hasil", "Contoh terjemahan dari model");
  const ex = [["Lon jak u peukan uroe nyoe.", "Saya pergi ke pasar hari ini.", null, null], ["Teuma troih le Abu Sammah, budak indah paraih rupa", "Lalu sampailah Abu Sammah, budak indah paras rupa", null, null],
              ["Nyo beutoi, jih teungoh jaga warong.", "Ini benar, dia sedang menjaga warung.", "Ini benar, karena dia sedang menjaga warganya.", "Iya benar, dia sedang jaga warung."]];
  const ys19 = [1.55, 3.1, 4.65], hs19 = [1.35, 1.35, 1.95];
  ex.forEach((e, i) => {
    const y = ys19[i]; card(s, 0.6, y, 12.13, hs19[i], "Kartu contoh");
    T(s, "Aceh", { x: 0.9, y: y + 0.18, w: 1.3, h: 0.4, fontSize: 12, bold: true, color: C.accent5, valign: "middle" }); T(s, e[0], { x: 2.2, y: y + 0.15, w: 10.3, h: 0.45, fontSize: 18, bold: true, valign: "middle" });
    T(s, "Model kami", { x: 0.9, y: y + 0.72, w: 1.3, h: 0.4, fontSize: 12, bold: true, color: C.accent1, valign: "middle" }); T(s, e[1], { x: 2.2, y: y + 0.7, w: 10.3, h: 0.45, fontSize: 18, color: C.accent1, bold: true, valign: "middle" });
    if (e[2]) { T(s, "NLLB dasar", { x: 0.9, y: y + 1.3, w: 1.3, h: 0.4, fontSize: 12, bold: true, color: C.accent5, valign: "middle" }); T(s, e[2], { x: 2.2, y: y + 1.28, w: 4.9, h: 0.45, fontSize: 14, color: C.accent5, valign: "middle" });
                T(s, "Acuan", { x: 7.3, y: y + 1.3, w: 1.2, h: 0.4, fontSize: 12, bold: true, color: C.accent5, valign: "middle" }); T(s, e[3], { x: 8.5, y: y + 1.28, w: 4.1, h: 0.45, fontSize: 14, color: C.accent5, valign: "middle" }); }
  });
  s.addNotes("Tiga keluaran nyata. Yang pertama kalimat sehari-hari sederhana. Yang kedua satu baris syair hikayat yang tidak ada dalam data latih; strukturnya terjaga. Yang ketiga dari set uji NusaX: model dasar salah mengartikan 'warong' menjadi 'warganya', sedangkan model kami menghasilkan 'warung' yang sesuai acuan manusia.");

  // ================= 26 ANALISIS KESALAHAN =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Hasil" });
  header(s, "Hasil", "Contoh: yang membaik dan yang dijaga");
  const er = [["FaCheckCircle", "Membaik: arti kata", "NusaX: \"Nyo beutoi, jih teungoh jaga warong.\" Model dasar menulis \"menjaga warganya\". Model kami menulis \"menjaga warung\", sesuai acuan.", HEX.teal],
              ["FaSearch", "Perlu dijaga: konteks", "NusaX: kalimat tentang aplikasi yang sedang dipelihara (jipeupah). Acuan membahas pemeliharaan, model kami memilih \"menyewa\".", HEX.gold],
              ["FaBalanceScale", "Perlu dijaga: arah makna", "FLORES (Shark Tank): penolakan pendanaan pada acuan berubah menjadi pemberian dana. Kesalahan seperti ini mengubah pesan utama.", HEX.slate]];
  for (let i = 0; i < 3; i++) {
    const x = 0.6 + i * 4.1; card(s, x, 1.6, 3.93, 3.5, "Kartu analisis");
    await badge(s, er[i][0], x + 0.3, 1.85, 0.75, er[i][3]);
    T(s, er[i][1], { x: x + 1.3, y: 1.85, w: 2.5, h: 0.75, fontSize: 16, bold: true, valign: "middle" });
    T(s, er[i][2], { x: x + 0.3, y: 2.85, w: 3.4, h: 2.15, fontSize: 15, color: C.accent5 });
  }
  card(s, 0.6, 5.4, 12.13, 1.4, "Kartu pesan", C.text2);
  T(s, "Skor naik di semua set uji, tetapi arti kata, negasi, dan konteks tetap perlu diperiksa penutur bahasa Aceh.", { x: 0.9, y: 5.4, w: 11.6, h: 1.4, fontSize: 18, color: C.background1, valign: "middle" });
  s.addNotes("Kami juga memeriksa contoh keluaran, bukan hanya skor. Model kami memperbaiki arti kata, misalnya warung. Tetapi masih ada kesalahan konteks, misalnya memilih menyewa untuk kata pemeliharaan, dan kesalahan arah makna pada contoh FLORES tentang Shark Tank. Ini analisis kualitatif terbatas pada contoh yang tersimpan, bukan penilaian manusia skala penuh. Karena itu pemeriksaan oleh penutur adalah langkah berikutnya.");

  // ================= 27 APLIKASI =================
  section("Aplikasi");
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Aplikasi" });
  header(s, "Aplikasi", "Aplikasi penerjemah");
  const af = [["FaWifi", "Lokal dan offline", "Berjalan di 127.0.0.1:7860, tanpa internet setelah start pertama"], ["FaLanguage", "Normalisasi sama", "Teks dibersihkan persis seperti data latih"], ["FaListOl", "Kalimat demi kalimat", "Tabel rincian: asli, normal, dan terjemahan"],
              ["FaProjectDiagram", "Cara kerja model", "Token encoder dan decoder tiap terjemahan"], ["FaBook", "Panel kamus", "Arti kata dengan tanda centang pada arti terbaik"], ["FaCheckCircle", "Panel akurasi", "Skor uji tampil di samping penerjemah"]];
  for (let i = 0; i < 6; i++) {
    const x = 0.6 + (i % 2) * 3.35, y = 1.55 + Math.floor(i / 2) * 1.5;
    card(s, x, y, 3.2, 1.35, "Kartu fitur");
    await badge(s, af[i][0], x + 0.15, y + 0.15, 0.55, C.accent1);
    T(s, af[i][1], { x: x + 0.82, y: y + 0.15, w: 2.3, h: 0.55, fontSize: 13, bold: true, valign: "middle" });
    T(s, af[i][2], { x: x + 0.15, y: y + 0.75, w: 2.95, h: 0.55, fontSize: 11, color: C.accent5 });
  }
  card(s, 7.45, 1.55, 5.28, 4.2, "Contoh tampilan", C.text2);
  T(s, "Penerjemah Aceh → Indonesia", { x: 7.75, y: 1.75, w: 4.7, h: 0.45, fontSize: 18, bold: true, color: C.background1 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.75, y: 2.35, w: 2.3, h: 1.5, rectRadius: 0.08, fill: { color: C.background1 }, line: { color: C.background1, width: 0 }, objectName: "Kotak masukan" });
  T(s, "Bahasa Aceh", { x: 7.85, y: 2.4, w: 2.1, h: 0.3, fontSize: 11, color: C.accent5 }); T(s, "Lon jak u peukan uroe nyoe.", { x: 7.85, y: 2.75, w: 2.1, h: 1.0, fontSize: 14, color: C.text1 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 10.3, y: 2.35, w: 2.15, h: 1.5, rectRadius: 0.08, fill: { color: C.background1 }, line: { color: C.background1, width: 0 }, objectName: "Kotak hasil" });
  T(s, "Bahasa Indonesia", { x: 10.4, y: 2.4, w: 1.95, h: 0.3, fontSize: 11, color: C.accent5 }); T(s, "Saya pergi ke pasar hari ini.", { x: 10.4, y: 2.75, w: 1.95, h: 1.0, fontSize: 14, bold: true, color: C.accent1 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.75, y: 4.1, w: 4.7, h: 0.6, rectRadius: 0.1, fill: { color: HEX.teal }, line: { color: HEX.teal, width: 0 }, objectName: "Tombol" });
  T(s, "Terjemahkan · Translate", { x: 7.75, y: 4.1, w: 4.7, h: 0.6, fontSize: 15, bold: true, color: C.background1, align: "center", valign: "middle" });
  T(s, "Cara kerja model  ·  Kata per kata  ·  Seberapa akurat?", { x: 7.75, y: 4.9, w: 4.7, h: 0.35, fontSize: 12, color: C.background2 });
  card(s, 0.6, 6.0, 12.13, 0.85, "Kartu cara jalan");
  T(s, "Jalankan: ./run_app.sh (Mac) · run_app.bat (Windows) · notebook demo Colab dengan tautan publik · model di Hugging Face", { x: 0.9, y: 6.0, w: 11.6, h: 0.85, fontSize: 13, valign: "middle" });
  s.addNotes("Aplikasi berjalan di komputer sendiri dan bisa dipakai tanpa internet setelah start pertama. Teks masukan dinormalkan seperti data latih, diterjemahkan kalimat demi kalimat, dan ada tabel rincian. Panel Cara kerja model menampilkan token encoder dan decoder, panel Kata per kata menampilkan arti kamus, dan panel akurasi menampilkan skor uji. Untuk demo, aplikasi juga bisa dijalankan di Colab dengan tautan publik sementara.");

  // ================= 28 KUALITAS =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Aplikasi" });
  header(s, "Kualitas", "Bisa diulang, diuji, dan terdokumentasi");
  [["91", "tes otomatis", "Pemeriksaan kebocoran, normalisasi, OCR, penyejajaran, pelatihan, aplikasi"], ["1", "perintah per tahap", "Tiap langkah jalan dari baris perintah acehid"], ["Git", "kode dan data di repositori", "Daftar sumber dan lisensi di config/sources.csv"]].forEach(([n, l, d], i) => {
    const x = 0.6 + i * 4.1; card(s, x, 1.6, 3.93, 2.5, "Kartu angka");
    T(s, n, { x: x + 0.3, y: 1.75, w: 3.3, h: 0.9, fontSize: 48, bold: true, color: C.accent1, fontFace: "Georgia" }); T(s, l, { x: x + 0.3, y: 2.65, w: 3.4, h: 0.4, fontSize: 15, bold: true }); T(s, d, { x: x + 0.3, y: 3.1, w: 3.4, h: 0.95, fontSize: 12, color: C.accent5 });
  });
  card(s, 0.6, 4.4, 6.0, 2.4, "Kartu alat");
  T(s, "Alat", { x: 0.9, y: 4.55, w: 5, h: 0.4, fontSize: 18, bold: true });
  T(s, "Python · PyTorch · Transformers 5.19 · sentencepiece · Gradio 6.29 · PyMuPDF · RapidOCR · rapidfuzz · datasketch · sacreBLEU · Google Colab", { x: 0.9, y: 5.05, w: 5.4, h: 1.6, fontSize: 15, color: C.accent5 });
  card(s, 6.83, 4.4, 5.9, 2.4, "Kartu AI", C.text2);
  T(s, "Bantuan AI", { x: 7.13, y: 4.55, w: 5, h: 0.4, fontSize: 18, bold: true, color: C.accent2 });
  T(s, "Kami memakai Claude, asisten AI, untuk membantu menulis banyak kode. Tim menentukan sumber data, aturan pembagian data, dan evaluasi, menjalankan pelatihan, serta memeriksa hasilnya.", { x: 7.13, y: 5.05, w: 5.3, h: 1.6, fontSize: 15, color: C.background1 });
  s.addNotes("Proyek ini bisa diulang: ada 91 tes otomatis, satu perintah untuk tiap tahap, dan semuanya ada di repositori Git. Kami juga ingin terbuka soal alat: kami memakai Claude, asisten AI, untuk membantu menulis kode. Tim memutuskan sumber data, aturan pembagian, dan evaluasi, serta menjalankan dan memeriksa hasilnya.");

  // ================= 29 LISENSI =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Aplikasi" });
  header(s, "Penggunaan bertanggung jawab", "Lisensi dan sumber");
  const lc = [["FaShieldAlt", "Model", "Bobot NLLB-200 berlisensi CC-BY-NC 4.0, jadi model kami untuk penelitian dan pengajaran, bukan komersial."], ["FaDatabase", "Data terbuka", "NusaX, FLORES, NLLB-Seed, dan Wikipedia berlisensi CC-BY-SA 4.0 dan disebut penulisnya."],
              ["FaBook", "Buku dan skripsi", "Depdikbud (Hikayat Abu Sammah), Inayati (Hikayat Malik Mawot), Kemenag dan Tgk. Mahjiddin Jusuf (Al-Qur'an), Balai Bahasa Aceh (Kamus Budaya)."], ["FaFileAlt", "Daftar sumber", "Tiap sumber, lisensinya, dan cara memakainya dicatat di config/sources.csv. Status lisensi sebagian sumber masih dikonfirmasi."]];
  for (let i = 0; i < 4; i++) {
    const x = 0.6 + (i % 2) * 6.15, y = 1.6 + Math.floor(i / 2) * 2.65;
    card(s, x, y, 5.98, 2.45, "Kartu kredit");
    await badge(s, lc[i][0], x + 0.3, y + 0.3, 0.75, C.accent1);
    T(s, lc[i][1], { x: x + 1.3, y: y + 0.35, w: 4.4, h: 0.5, fontSize: 18, bold: true, valign: "middle" });
    T(s, lc[i][2], { x: x + 0.3, y: y + 1.15, w: 5.4, h: 1.25, fontSize: 14, color: C.accent5 });
  }
  s.addNotes("Kami mencatat lisensi tiap sumber. Bobot model NLLB hanya untuk non-komersial, jadi model kami untuk penelitian dan pengajaran. Data terbuka berlisensi CC-BY-SA dan disebut penulisnya. Buku dan skripsi disebut penulis dan penerbitnya. Status lisensi sebagian sumber masih kami konfirmasi, dan daftarnya ada di repositori.");

  // ================= 30 KESIMPULAN =================
  section("Penutup");
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Penutup" });
  header(s, "Kesimpulan", "Hasil kami dan langkah berikutnya");
  card(s, 0.6, 1.55, 6.0, 5.25, "Kartu hasil");
  T(s, "Yang sudah kami capai", { x: 0.9, y: 1.7, w: 5, h: 0.45, fontSize: 20, bold: true, color: C.accent1 });
  T(s, ["Audit korpus AcehX dan 17.547 pasangan latih dari sembilan sumber", "Fine-tuning NLLB-200: chrF++ NusaX 38,7 → 57,1, FLORES 46,3 → 52,8, hikayat 24,0 → 60,9", "Perbandingan direct, transfer, dan neural di set uji yang sama", "Augmentasi pivot dan disambiguasi kamus", "Aplikasi lokal dengan tampilan encoder dan decoder"].map((t, k) => ({ text: t, options: { bullet: true, breakLine: k < 4 } })),
    { x: 0.9, y: 2.3, w: 5.4, h: 4.4, fontSize: 16, paraSpaceAfter: 12 });
  card(s, 6.83, 1.55, 5.9, 5.25, "Kartu langkah", C.text2);
  T(s, "Langkah berikutnya", { x: 7.13, y: 1.7, w: 5, h: 0.45, fontSize: 20, bold: true, color: C.accent2 });
  T(s, ["Tinjauan penutur untuk pasangan REVIEW dan terjemahan baru", "Uji ablasi: latih dengan dan tanpa tiap sumber, beberapa seed", "Kunci manifest dan konfigurasi agar mudah diulang", "Lengkapi dokumentasi lisensi dan data card Atlas Data AI", "Perluas augmentasi dengan back-translation dan versi aplikasi online"].map((t, k) => ({ text: t, options: { bullet: true, breakLine: k < 4 } })),
    { x: 7.13, y: 2.3, w: 5.3, h: 4.4, fontSize: 16, color: C.background1, paraSpaceAfter: 12 });
  s.addNotes("Kesimpulan: kami membangun alur lengkap dari sumber mentah sampai aplikasi, dan model hasil fine-tuning jelas lebih baik dari model dasar di ketiga set uji. Langkah berikutnya: tinjauan oleh penutur, uji ablasi untuk melihat sumbangan tiap sumber data dengan beberapa seed, mengunci manifest dan konfigurasi, melengkapi dokumentasi lisensi dan data card, serta memperluas augmentasi dan menyediakan versi online.");

  // ================= RUJUKAN =================
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Penutup" });
  header(s, "Rujukan", "Rujukan dari makalah kami");
  const rf = ["Vaswani dkk., \"Attention Is All You Need\", NeurIPS, 2017.", "NLLB Team dkk., \"No Language Left Behind: Scaling Human-Centered Machine Translation\", 2022.", "Winata dkk., \"NusaX: Multilingual Parallel Sentiment Dataset for 10 Indonesian Local Languages\", EACL, 2023.", "Papineni dkk., \"Bleu: a Method for Automatic Evaluation of Machine Translation\", ACL, 2002.", "Popović, \"chrF: character n-gram F-score for automatic MT evaluation\", WMT, 2015; \"chrF++: words helping character n-grams\", WMT, 2017.", "Post, \"A Call for Clarity in Reporting BLEU Scores\", WMT, 2018.", "Gebru dkk., \"Datasheets for Datasets\", Communications of the ACM, 2021.", "Meta AI, model card facebook/nllb-200-distilled-600M, Hugging Face."];
  rf.forEach((t, i) => {
    const y = 1.55 + i * 0.66; card(s, 0.6, y, 12.13, 0.58, "Kartu rujukan");
    T(s, String(i + 1), { x: 0.8, y, w: 0.5, h: 0.58, fontSize: 16, bold: true, color: C.accent1, fontFace: "Georgia", valign: "middle" });
    T(s, t, { x: 1.4, y, w: 11.2, h: 0.58, fontSize: 13, valign: "middle" });
  });
  s.addNotes("Rujukan utama dari makalah kami: Transformer, NLLB, NusaX, ukuran BLEU, chrF, dan chrF++, panduan pelaporan BLEU, Datasheets for Datasets, dan model card NLLB.");

  // ================= 31 TERIMA KASIH =================
  s = pres.addSlide({ masterName: "TITLE", sectionTitle: "Penutup" });
  s.addText("Terima kasih", { placeholder: "title" });
  s.addText("Pertanyaan dan diskusi", { placeholder: "body" });
  T(s, "Kode dan data: github.com/Mutaib-yye/aceh_code", { x: 0.8, y: 6.4, w: 8, h: 0.4, fontSize: 14, color: C.accent6 });
  for (const [x, y, d, col, tr] of [[8.9, 1.0, 3.6, HEX.teal, 25], [10.6, 3.2, 2.5, HEX.gold, 20], [8.6, 4.4, 2.2, HEX.teal, 45]]) s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: col, transparency: tr }, line: { color: col, width: 0 }, objectName: "Lingkaran hias" });
  s.addNotes("Terima kasih. Kami siap menjawab pertanyaan. Semua angka berasal dari run pelatihan kami di Colab, model disimpan secara privat di Hugging Face, dan repositori berisi semua perintah untuk mengulang alur ini.");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("selesai", OUT);
})();
