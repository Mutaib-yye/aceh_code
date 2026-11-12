"use strict";
const $ = id => document.getElementById(id);
const store = {
  get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private mode: the app still works */ } },
};
function el(tag, props, ...kids) {                       // safe DOM builder: text is never parsed as HTML
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) { if (k === "class") n.className = v; else if (k.startsWith("on")) n.addEventListener(k.slice(2), v); else n.setAttribute(k, v); }
  for (const c of kids.flat()) if (c != null) n.append(c.nodeType ? c : document.createTextNode(c));
  return n;
}
async function api(path, body) {
  let r;
  try { r = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : undefined); }
  catch (e) { throw new Error("Tidak bisa terhubung ke server · network error. Pastikan aplikasi masih berjalan."); }
  let d = {}; try { d = await r.json(); } catch (e) { /* non-JSON body */ }
  if (!r.ok) throw new Error(d.error || `Server error (${r.status})`);
  return d;
}
const flash = (btn, txt) => {
  const t = [...btn.childNodes].reverse().find(n => n.nodeType === 3 && n.textContent.trim());
  if (!t) { const o = btn.textContent; btn.textContent = txt; setTimeout(() => btn.textContent = o, 1200); return; }
  const o = t.textContent; t.textContent = txt; setTimeout(() => t.textContent = o, 1200);
};
async function copy(text, btn) {
  try { await navigator.clipboard.writeText(text); flash(btn, "Disalin ✓"); }
  catch (e) { const t = el("textarea"); t.value = text; document.body.append(t); t.select(); document.execCommand("copy"); t.remove(); flash(btn, "Disalin ✓"); }
}
function save(name, text, type = "text/plain") {
  const a = el("a", { href: URL.createObjectURL(new Blob([text], { type: type + ";charset=utf-8" })), download: name });
  document.body.append(a); a.click(); a.remove();
}

/* ---------- icons ---------- */
const ICONS = {
  home: '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
  clock: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
  chart: '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
  info: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
  mic: '<path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/>',
  clipboard: '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/>',
  copy: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
  layers: '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
  trash: '<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/>',
  arrow: '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
  star: '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
  repeat: '<polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
  zap: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
  globe: '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
  spark: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>',
  kbd: '<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10"/>',
  chat: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  wave: '<line x1="4" y1="10" x2="4" y2="14"/><line x1="8" y1="6" x2="8" y2="18"/><line x1="12" y1="3" x2="12" y2="21"/><line x1="16" y1="7" x2="16" y2="17"/><line x1="20" y1="10" x2="20" y2="14"/>',
};
document.querySelectorAll("i[data-i]").forEach(n => { n.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[n.dataset.i] || ""}</svg>`; });

/* ---------- theme + navigation ---------- */
const root = document.documentElement;
function setTheme(t) { root.setAttribute("data-theme", t); store.set("theme", t); }
setTheme(store.get("theme", "dark"));
const flip = () => { setTheme(root.getAttribute("data-theme") === "dark" ? "light" : "dark"); $("theme2").textContent = root.getAttribute("data-theme") === "dark" ? "☾" : "☀"; };
$("theme").addEventListener("click", flip); $("theme2").addEventListener("click", flip);
$("theme2").textContent = root.getAttribute("data-theme") === "dark" ? "☾" : "☀";

const PAGES = ["translate", "dictionary", "history", "evaluation", "about"];
function route() {
  const p = PAGES.includes(location.hash.slice(1)) ? location.hash.slice(1) : "translate";
  PAGES.forEach(n => { $("page-" + n).hidden = n !== p; });
  document.querySelectorAll("#nav a").forEach(a => { a.classList.toggle("on", a.dataset.page === p); a.toggleAttribute("aria-current", a.dataset.page === p); });
  if (p === "history") renderHistory();
  if (p === "evaluation") loadEval();
  if (p === "dictionary") $("dq").focus();
}
addEventListener("hashchange", route);

/* ---------- status ---------- */
let STATUS = { max_chars: 5000, dictionary: {} };
async function loadStatus() {
  try {
    STATUS = await api("/api/status");
    const b = $("modelBadge");
    b.textContent = STATUS.finetuned ? "Fine-tuned Model" : "Model dasar NLLB-200 · belum di-fine-tune";
    b.parentElement.classList.toggle("warn", !STATUS.finetuned);
    const k = STATUS.dictionary || {};
    $("kEntries").textContent = k.loaded ? k.entries.toLocaleString("id-ID") : "–";
    $("kState").textContent = k.loaded ? "Aktif" : "Belum dimuat"; $("kState").classList.toggle("off", !k.loaded);
    $("aboutModel").textContent = `Model aktif: ${STATUS.model_id}.`;
    $("footModel").textContent = "· " + STATUS.model_id;
    $("inp").maxLength = STATUS.max_chars;
  } catch (e) { $("modelBadge").textContent = "Server tidak terhubung"; }
}

/* ---------- translate ---------- */
let LAST = null;                                          // {src, tgt, details}
const inp = $("inp");
const words = s => (s.trim().match(/\S+/g) || []).length;
function updateCount() {
  $("count").textContent = `${inp.value.length} / ${STATUS.max_chars} karakter · ${words(inp.value)} kata`;
  renderChips();
}
function showMsg(box, text, note) { box.hidden = !text; box.textContent = text || ""; box.classList.toggle("note", !!note); }
function busy(on) {
  $("translate").disabled = on; $("loading").hidden = !on; $("translate").querySelector("span").textContent = on ? "Menerjemahkan…" : "Translate";
  if (on) { $("outText").classList.add("placeholder"); }
}
function setOut(text) {
  const o = $("outText"); o.textContent = text || "Terjemahan akan muncul di sini…"; o.classList.toggle("placeholder", !text);
  $("copyOut").disabled = $("download").disabled = !text;
}
async function doTranslate() {
  showMsg($("msg"), ""); $("alts").hidden = true; $("normBox").hidden = true;
  const text = inp.value.trim();
  if (!text) { showMsg($("msg"), "Teks masih kosong · please enter some Acehnese text."); inp.focus(); return; }
  if (text.length > STATUS.max_chars) { showMsg($("msg"), `Teks terlalu panjang (maksimal ${STATUS.max_chars} karakter).`); return; }
  busy(true);
  try {
    const d = await api("/api/translate", { text, normalize: $("optNorm").checked, alternatives: $("optAlt").checked });
    LAST = { src: text, tgt: d.translation, details: d.details, norm: d.normalized };
    setOut(d.translation); $("outFoot").textContent = `${words(d.translation)} kata`;
    if (d.notes.length) showMsg($("msg"), d.notes.join(" "), true);
    $("viewNorm").hidden = !(d.normalize && d.normalized.trim() !== text.replace(/\s+/g, " "));
    $("normBox").textContent = d.normalized;
    renderAlts(d.alternatives);
    addHistory(text, d.translation);
    $("fbMsg").textContent = "";
  } catch (e) { setOut(""); showMsg($("msg"), e.message); }
  finally { busy(false); }
}
function renderAlts(list) {
  const ul = $("altList"); ul.replaceChildren();
  list.forEach(t => ul.append(el("li", {}, el("span", {}, t), el("span", {}, el("button", { class: "chip", onclick: e => copy(t, e.target) }, "Copy"), " ",
    el("button", { class: "chip", onclick: () => { setOut(t); LAST.tgt = t; } }, "Pakai")))));
  $("alts").hidden = !list.length;
}
$("translate").addEventListener("click", doTranslate);
addEventListener("keydown", e => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && !$("page-translate").hidden) { e.preventDefault(); ($("batch").hidden ? doTranslate : doBatch)(); } });
inp.addEventListener("input", updateCount);
$("clear").addEventListener("click", () => { inp.value = ""; LAST = null; setOut(""); $("outFoot").textContent = ""; ["msg", "alts", "normBox", "explain", "feed", "words"].forEach(i => $(i).hidden = true); $("viewNorm").hidden = true; updateCount(); inp.focus(); });
$("copyOut").addEventListener("click", e => copy($("outText").textContent, e.target));
$("copyIn").addEventListener("click", e => copy(inp.value, e.target));
$("download").addEventListener("click", () => save("terjemahan.txt", $("outText").textContent));
$("paste").addEventListener("click", async e => {
  try { inp.value = (await navigator.clipboard.readText()).slice(0, STATUS.max_chars); updateCount(); inp.focus(); }
  catch (err) { showMsg($("msg"), "Browser tidak mengizinkan akses papan klip. Tempel dengan Ctrl/⌘ + V.", true); }
});
$("viewNorm").addEventListener("click", () => { $("normBox").hidden = !$("normBox").hidden; });
$("optNorm").addEventListener("change", e => { store.set("normalize", e.target.checked); $("setNorm").checked = e.target.checked; });
$("setNorm").addEventListener("change", e => { store.set("normalize", e.target.checked); $("optNorm").checked = e.target.checked; });
$("optNorm").checked = $("setNorm").checked = store.get("normalize", true);

const showBatch = on => { $("single").hidden = on; $("batch").hidden = !on; if (on) $("batchIn").focus(); };
$("batchBtn").addEventListener("click", () => showBatch(true)); $("batchBack").addEventListener("click", () => showBatch(false));

/* ---------- word lookup, explain, feedback, alternatives cards ---------- */
function entryNode(e) {
  return el("div", { class: "entry" }, el("b", {}, e.word), e.variants && e.variants.length ? el("span", { class: "muted" }, "  (" + e.variants.join(", ") + ")") : null,
    e.status !== "unknown" ? el("span", { class: "tagpill" }, "belum divalidasi") : null, el("div", {}, e.meaning),
    e.page ? el("div", { class: "muted" }, `Kamus Aceh–Indonesia (1985), hlm. ${e.page}`) : null);
}
function dictResult(box, d) {
  box.replaceChildren();
  if (!d.loaded) { box.append(el("p", { class: "muted" }, "Kamus belum dimuat: file kamus_aceh_indonesia_1985.csv harus ada di folder data/glossary/ (aplikasi mengunduhnya otomatis bila ada koneksi internet). Mulai ulang aplikasi setelah file ada.")); return; }
  const sec = (title, list) => { if (list.length) box.append(el("h3", {}, title), ...list.map(entryNode)); };
  sec("Kata ditemukan", d.exact); sec("Kata yang diawali '" + d.q + "'", d.prefix); sec("Arti mengandung '" + d.q + "'", d.meaning);
  if (!d.found) box.append(el("p", { class: "muted" }, `Kata "${d.q}" tidak ada di kamus (kamus ini hanya mencakup A–L). Tidak ada arti yang dikarang.`));
}
async function lookup(word, box) {
  try { dictResult(box, await api("/api/dictionary?q=" + encodeURIComponent(word))); } catch (e) { box.replaceChildren(el("p", { class: "msg" }, e.message)); }
}
function renderChips() {
  const ws = [...new Set(inp.value.match(/[\p{L}\p{N}'’\-]+/gu) || [])].slice(0, 60);
  const c = $("chips"); c.replaceChildren(...ws.map(w => el("button", { class: "chip", type: "button", onclick: ev => {
    c.querySelectorAll(".chip").forEach(x => x.classList.remove("on")); ev.target.classList.add("on"); lookup(w, $("wordOut")); } }, w)));
}
$("cDict").addEventListener("click", () => {
  $("words").hidden = false; renderChips();
  const sel = inp.value.slice(inp.selectionStart, inp.selectionEnd).trim();
  if (sel && !/\s/.test(sel)) lookup(sel, $("wordOut")); else if (!inp.value.trim()) $("wordOut").replaceChildren(el("p", { class: "muted" }, "Tulis teks Aceh dulu, lalu klik sebuah kata. Atau buka halaman Dictionary."));
  $("words").scrollIntoView({ behavior: "smooth", block: "nearest" });
});
$("cAlt").addEventListener("click", () => { $("optAlt").checked = true; if (inp.value.trim()) doTranslate(); else showMsg($("msg"), "Tulis satu kalimat dulu; alternatif muncul setelah Translate.", true); });
$("cExplain").addEventListener("click", async () => {
  const box = $("explain");
  if (!LAST) { showMsg($("msg"), "Terjemahkan sesuatu dulu, lalu klik Translation Explanation.", true); return; }
  box.hidden = false; box.replaceChildren(el("span", { class: "spin" }), " Memuat…");
  try {
    const d = await api("/api/explain", { text: LAST.src, translation: LAST.tgt });
    box.replaceChildren(el("h3", {}, "Penjelasan terjemahan"),
      el("p", { class: "muted" }, "Ini penjelasan linguistik dari kamus dan token yang dibaca/ditulis model. Ini bukan “alasan internal” model, dan hanya kalimat pertama yang dijelaskan."),
      el("h3", {}, "Kosakata (dari kamus)"),
      ...(d.dictionary_loaded ? d.words.map(w => w.entries.length ? el("div", { class: "entry" }, el("b", {}, w.word), "  →  ", w.entries.map(x => x.meaning).join(" / "))
        : el("div", { class: "entry muted" }, w.word, ": tidak ada di kamus")) : [el("p", { class: "muted" }, "Kamus belum dimuat.")]),
      el("h3", {}, "Token yang dibaca model (Aceh)"), el("p", { class: "mono" }, d.src_tokens.join(" ")),
      el("h3", {}, "Token yang ditulis model (Indonesia)"), el("p", { class: "mono" }, d.tgt_tokens.join(" ")));
  } catch (e) { box.replaceChildren(el("p", { class: "msg" }, e.message)); }
});
$("cFeed").addEventListener("click", () => {
  if (!LAST) { showMsg($("msg"), "Terjemahkan sesuatu dulu, lalu beri masukan.", true); return; }
  $("feed").hidden = false; $("feed").scrollIntoView({ behavior: "smooth", block: "nearest" });
});
async function sendFeedback(rating) {
  if (!LAST) return;
  const consent = $("fbConsent").checked;
  try {
    const r = await api("/api/feedback", { rating, consent, source: LAST.src, translation: LAST.tgt, correction: $("fbFix").value, error_type: $("fbType").value });
    $("fbMsg").textContent = r.stored_text ? "Terima kasih! Masukan dan teks tersimpan untuk ditinjau." : "Terima kasih! Hanya penilaian yang disimpan (tanpa teks).";
  } catch (e) { $("fbMsg").textContent = e.message; }
}
$("up").addEventListener("click", () => sendFeedback("up"));
$("down").addEventListener("click", () => sendFeedback("down"));
$("fbSend").addEventListener("click", () => { if (!$("fbFix").value.trim()) { $("fbMsg").textContent = "Tulis koreksi dulu, atau pakai 👍/👎."; return; }
  if (!$("fbConsent").checked) { $("fbMsg").textContent = "Centang persetujuan agar koreksi disimpan."; return; } sendFeedback("down"); });

/* ---------- voice input (Meta MMS on this computer; experimental) ---------- */
const VOICE_MIN_MS = 400;
let rec = null;
const vmsg = t => showMsg($("voiceMsg"), t, true);
function wavFromFloat(pcm, sr) {
  const v = new DataView(new ArrayBuffer(44 + pcm.length * 2)), w = (o, t) => [...t].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
  w(0, "RIFF"); v.setUint32(4, 36 + pcm.length * 2, true); w(8, "WAVE"); w(12, "fmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, sr, true); v.setUint32(28, sr * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); w(36, "data"); v.setUint32(40, pcm.length * 2, true);
  for (let i = 0; i < pcm.length; i++) v.setInt16(44 + i * 2, Math.max(-1, Math.min(1, pcm[i])) * 32767, true);
  return new Blob([v], { type: "audio/wav" });
}
async function toWav16k(blob) {                                       // any browser format -> 16 kHz mono 16-bit WAV
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const audio = await ctx.decodeAudioData(await blob.arrayBuffer()); ctx.close();
  const off = new OfflineAudioContext(1, Math.max(1, Math.ceil(audio.duration * 16000)), 16000), src = off.createBufferSource();
  src.buffer = audio; src.connect(off.destination); src.start();
  return wavFromFloat((await off.startRendering()).getChannelData(0), 16000);
}
async function sendAudio(blob) {
  const first = !(STATUS.voice && STATUS.voice.loaded);
  vmsg(first ? "Memproses suara… Pertama kali model suara (±4 GB) diunduh dulu: bisa beberapa menit. · First use downloads the speech model." : "Memproses suara…");
  try {
    const r = await fetch("/api/transcribe", { method: "POST", headers: { "Content-Type": "audio/wav" }, body: await toWav16k(blob) });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.error || `Server error (${r.status})`);
    if (STATUS.voice) STATUS.voice.loaded = true;
    if (!d.text) { vmsg("Tidak ada ucapan yang dikenali. Coba bicara lebih jelas dan dekat dengan mikrofon."); return; }
    inp.value = (inp.value.trim() ? inp.value.trim() + "\n" : "") + d.text; updateCount(); inp.focus();
    vmsg("Teks dari suara (eksperimental, bisa salah dengar bahasa Aceh): periksa dan edit dulu sebelum menerjemahkan.");
  } catch (e) { showMsg($("voiceMsg"), "", true); showMsg($("msg"), e.message); }
}
async function toggleVoice() {
  if (rec) { rec.stop(); return; }
  if (!navigator.mediaDevices || !window.MediaRecorder) { showMsg($("msg"), "Browser ini tidak mendukung perekaman suara. Coba Chrome, Edge atau Firefox terbaru."); return; }
  if (!store.get("voiceOk", false)) {
    if (!confirm("Input suara (eksperimental)\n\n• Memakai model Meta MMS yang berjalan di komputer ini; audio tidak dikirim ke luar.\n• Pertama kali, model ±4 GB diunduh sekali.\n• Uji kecil: kesalahan huruf 12 %, kata 46 %. Selalu periksa dan edit teksnya sebelum menerjemahkan.\n\nLanjutkan dan izinkan mikrofon?")) return;
    store.set("voiceOk", true);
  }
  showMsg($("msg"), "");
  let stream;
  try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
  catch (e) { showMsg($("msg"), e.name === "NotFoundError" ? "Mikrofon tidak ditemukan." : "Izin mikrofon ditolak. Izinkan mikrofon di pengaturan browser lalu coba lagi."); return; }
  const chunks = [], mr = new MediaRecorder(stream), t0 = Date.now();
  rec = mr; $("mic").classList.add("rec"); vmsg("Merekam… klik mikrofon lagi untuk berhenti · recording, click again to stop.");
  const auto = setTimeout(() => mr.state === "recording" && mr.stop(), ((STATUS.voice && STATUS.voice.max_seconds) || 90) * 1000 - 500);
  mr.ondataavailable = e => e.data.size && chunks.push(e.data);
  mr.onstop = () => {
    clearTimeout(auto); stream.getTracks().forEach(t => t.stop()); $("mic").classList.remove("rec"); rec = null;
    if (Date.now() - t0 < VOICE_MIN_MS || !chunks.length) { vmsg("Rekaman terlalu pendek."); return; }
    sendAudio(new Blob(chunks, { type: mr.mimeType || "audio/webm" }));
  };
  mr.start();
}
$("mic").addEventListener("click", toggleVoice);
$("cVoice").addEventListener("click", toggleVoice);

/* ---------- batch ---------- */
let BATCH = [];
$("batchIn").addEventListener("input", () => { const n = $("batchIn").value.split("\n").filter(l => l.trim()).length; $("batchCount").textContent = `${n} baris`; });
async function doBatch() {
  showMsg($("batchMsg"), ""); const text = $("batchIn").value;
  if (!text.trim()) { showMsg($("batchMsg"), "Teks masih kosong · please enter some lines."); return; }
  $("batchGo").disabled = true; $("batchGo").querySelector("span").textContent = "Menerjemahkan…";
  try {
    const d = await api("/api/batch", { text, normalize: $("optNorm").checked });
    BATCH = d.rows; const tb = $("batchRows"); tb.replaceChildren();
    d.rows.forEach((r, i) => tb.append(el("tr", {}, el("td", {}, r.src.trim() ? String(i + 1) : ""), el("td", {}, r.src), el("td", {}, r.tgt))));
    $("batchOut").hidden = false;
  } catch (e) { showMsg($("batchMsg"), e.message); }
  finally { $("batchGo").disabled = false; $("batchGo").querySelector("span").textContent = "Translate"; }
}
$("batchGo").addEventListener("click", doBatch);
$("batchClear").addEventListener("click", () => { $("batchIn").value = ""; $("batchOut").hidden = true; $("batchCount").textContent = "0 baris"; showMsg($("batchMsg"), ""); });
$("batchCopy").addEventListener("click", e => copy(BATCH.map(r => r.tgt).join("\n"), e.target));
$("batchDl").addEventListener("click", () => {
  const q = s => '"' + s.replace(/"/g, '""') + '"';
  save("terjemahan-batch.csv", "aceh,indonesia\n" + BATCH.filter(r => r.src.trim()).map(r => q(r.src) + "," + q(r.tgt)).join("\n"), "text/csv");
});

/* ---------- history (browser only) ---------- */
const HK = "acehtranslate_history";
const history = () => store.get(HK, []);
function addHistory(src, tgt) {
  if (!store.get("keepHistory", true)) return;
  const h = history().filter(x => !(x.src === src && x.tgt === tgt));
  h.unshift({ id: Date.now() + Math.random(), src, tgt, t: new Date().toISOString() });
  store.set(HK, h.slice(0, 500)); renderRecent();
}
function renderHistory() {
  const q = $("hq").value.trim().toLowerCase(), box = $("hlist");
  const list = history().filter(x => !q || x.src.toLowerCase().includes(q) || x.tgt.toLowerCase().includes(q));
  box.replaceChildren();
  if (!list.length) { box.append(el("p", { class: "muted" }, q ? "Tidak ada hasil." : "Belum ada riwayat. Terjemahan Anda akan muncul di sini.")); return; }
  list.forEach(x => box.append(el("div", { class: "hitem" },
    el("div", { class: "t" }, new Date(x.t).toLocaleString()), el("div", { class: "src" }, x.src), el("div", {}, x.tgt),
    el("div", { class: "row", style: "margin-top:8px" },
      el("button", { class: "chip", onclick: () => { inp.value = x.src; location.hash = "translate"; updateCount(); setOut(x.tgt); LAST = { src: x.src, tgt: x.tgt, details: [] }; } }, "Buka"),
      el("button", { class: "chip", onclick: e => copy(x.tgt, e.target) }, "Copy"),
      el("button", { class: "chip", onclick: () => { store.set(HK, history().filter(y => y.id !== x.id)); renderHistory(); renderRecent(); } }, "Hapus")))));
}
$("hq").addEventListener("input", renderHistory);
function ago(iso) {
  const m = Math.max(0, Math.round((Date.now() - new Date(iso)) / 60000));
  return m < 1 ? "baru saja" : m < 60 ? `${m} mnt lalu` : m < 1440 ? `${Math.round(m / 60)} jam lalu` : `${Math.round(m / 1440)} hari lalu`;
}
function renderRecent() {
  const box = $("recent"), h = history().slice(0, 4); box.replaceChildren();
  if (!h.length) { box.append(el("p", { class: "muted" }, "Belum ada terjemahan. Hasil Anda muncul di sini (hanya di browser ini).")); return; }
  h.forEach(x => box.append(el("div", { class: "rrow" }, el("span", { title: x.src }, x.src), el("span", { class: "a arrow" }, "→"), el("span", { title: x.tgt }, x.tgt),
    el("button", { type: "button", "aria-label": "Copy terjemahan", onclick: e => copy(x.tgt, e.currentTarget) }, el("span", { class: "muted" }, ago(x.t)), "⧉"))));
}
function clearAll() { if (confirm("Hapus semua riwayat terjemahan di browser ini? Tindakan ini tidak bisa dibatalkan.")) { store.set(HK, []); renderHistory(); renderRecent(); } }
$("histClear").addEventListener("click", clearAll); $("setClear").addEventListener("click", clearAll);
$("setHist").checked = store.get("keepHistory", true);
$("setHist").addEventListener("change", e => store.set("keepHistory", e.target.checked));

/* ---------- dictionary page ---------- */
let dt; $("dq").addEventListener("input", () => { clearTimeout(dt); const v = $("dq").value.trim(); if (!v) { $("dres").replaceChildren(); return; } dt = setTimeout(() => lookup(v, $("dres")), 200); });

/* ---------- evaluation ---------- */
async function loadEval() {
  const box = $("evalBox");
  try {
    const d = await api("/api/evaluation");
    if (!d.available) { box.replaceChildren(el("div", { class: "box" }, "Belum ada hasil evaluasi untuk model ini. Skor muncul setelah pelatihan di Colab selesai (training_log.json).")); return; }
    box.replaceChildren(el("div", { class: "box" }, el("p", {}, `Model: ${d.model_id} · dilatih pada ${d.train_pairs ?? "?"} pasangan kalimat terjemahan manusia.`),
      el("table", { class: "tbl" }, el("thead", {}, el("tr", {}, ["Set uji (belum pernah dilihat model)", "Kalimat", "NLLB dasar (chrF++)", "Model ini (chrF++)"].map(h => el("th", {}, h)))),
        el("tbody", {}, d.rows.map(r => el("tr", {}, el("td", {}, r.set), el("td", {}, String(r.n)), el("td", {}, String(r.base)), el("td", {}, el("b", {}, String(r.model)))))))));
  } catch (e) { box.replaceChildren(el("p", { class: "msg" }, e.message)); }
}

async function loadQuality() {
  const box = $("qual");
  try {
    const d = await api("/api/evaluation");
    if (!d.available || !d.rows.length) { box.textContent = "Belum ada hasil evaluasi untuk model ini."; return; }
    const best = d.rows[0], pct = Math.max(0, Math.min(100, Number(best.model) || 0));
    box.className = ""; box.replaceChildren(el("div", { class: "qring" }, el("div", { class: "ring", style: `--p:${pct}` }, el("b", {}, String(best.model))),
      el("div", { class: "qlist" }, el("div", { class: "kv" }, el("span", {}, "Metrik"), el("b", {}, "chrF++")), el("div", { class: "kv" }, el("span", {}, "Set uji"), el("b", {}, best.set.split(" (")[0])),
        el("div", { class: "kv" }, el("span", {}, "NLLB dasar"), el("b", {}, String(best.base))))));
    const qb = $("qualBadge"); qb.hidden = false; qb.querySelector("span").textContent = `chrF++ ${best.model}`;
  } catch (e) { box.textContent = "Skor tidak bisa dimuat."; }
}
updateCount(); renderRecent(); route(); loadStatus(); loadQuality();
