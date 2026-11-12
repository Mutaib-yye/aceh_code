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
const flash = (btn, txt) => { const o = btn.textContent; btn.textContent = txt; setTimeout(() => btn.textContent = o, 1200); };
async function copy(text, btn) {
  try { await navigator.clipboard.writeText(text); flash(btn, "Disalin ✓"); }
  catch (e) { const t = el("textarea"); t.value = text; document.body.append(t); t.select(); document.execCommand("copy"); t.remove(); flash(btn, "Disalin ✓"); }
}
function save(name, text, type = "text/plain") {
  const a = el("a", { href: URL.createObjectURL(new Blob([text], { type: type + ";charset=utf-8" })), download: name });
  document.body.append(a); a.click(); a.remove();
}

/* ---------- theme + navigation ---------- */
const root = document.documentElement;
function setTheme(t) { root.setAttribute("data-theme", t); store.set("theme", t); }
setTheme(store.get("theme", "dark"));
$("theme").addEventListener("click", () => setTheme(root.getAttribute("data-theme") === "dark" ? "light" : "dark"));

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
    b.textContent = STATUS.finetuned ? "Fine-tuned model" : "Model dasar NLLB-200 · belum di-fine-tune";
    b.classList.toggle("warn", !STATUS.finetuned);
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
  $("translate").disabled = on; $("loading").hidden = !on; $("translate").textContent = on ? "Menerjemahkan…" : "Translate";
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

document.querySelectorAll(".mode").forEach(b => b.addEventListener("click", () => {
  document.querySelectorAll(".mode").forEach(x => x.classList.toggle("on", x === b));
  $("single").hidden = b.dataset.mode !== "single"; $("batch").hidden = b.dataset.mode !== "batch";
}));

/* ---------- word lookup, explain, feedback, alternatives cards ---------- */
function entryNode(e) {
  return el("div", { class: "entry" }, el("b", {}, e.word), e.variants && e.variants.length ? el("span", { class: "muted" }, "  (" + e.variants.join(", ") + ")") : null,
    e.status !== "unknown" ? el("span", { class: "tagpill" }, "belum divalidasi") : null, el("div", {}, e.meaning),
    e.page ? el("div", { class: "muted" }, `Kamus Aceh–Indonesia (1985), hlm. ${e.page}`) : null);
}
function dictResult(box, d) {
  box.replaceChildren();
  if (!d.loaded) { box.append(el("p", { class: "muted" }, "Kamus belum dimuat: letakkan data/raw/kamus/kamus_aceh_indonesia_1985.csv lalu mulai ulang aplikasi.")); return; }
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

/* ---------- batch ---------- */
let BATCH = [];
$("batchIn").addEventListener("input", () => { const n = $("batchIn").value.split("\n").filter(l => l.trim()).length; $("batchCount").textContent = `${n} baris`; });
async function doBatch() {
  showMsg($("batchMsg"), ""); const text = $("batchIn").value;
  if (!text.trim()) { showMsg($("batchMsg"), "Teks masih kosong · please enter some lines."); return; }
  $("batchGo").disabled = true; $("batchGo").textContent = "Menerjemahkan…";
  try {
    const d = await api("/api/batch", { text, normalize: $("optNorm").checked });
    BATCH = d.rows; const tb = $("batchRows"); tb.replaceChildren();
    d.rows.forEach((r, i) => tb.append(el("tr", {}, el("td", {}, r.src.trim() ? String(i + 1) : ""), el("td", {}, r.src), el("td", {}, r.tgt))));
    $("batchOut").hidden = false;
  } catch (e) { showMsg($("batchMsg"), e.message); }
  finally { $("batchGo").disabled = false; $("batchGo").textContent = "Translate"; }
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
  store.set(HK, h.slice(0, 500));
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
      el("button", { class: "chip", onclick: () => { store.set(HK, history().filter(y => y.id !== x.id)); renderHistory(); } }, "Hapus")))));
}
$("hq").addEventListener("input", renderHistory);
function clearAll() { if (confirm("Hapus semua riwayat terjemahan di browser ini? Tindakan ini tidak bisa dibatalkan.")) { store.set(HK, []); renderHistory(); } }
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

updateCount(); route(); loadStatus();
