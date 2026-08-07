// js/adminBio.js
// ==========================================================================
//  ADMIN — BIOLOGIYA BAZASI
// ==========================================================================
// Ierarxiya:  Mavzu  ->  Level  ->  (Terminlar | Ketma-ketliklar | Rasmlar)
//
// MUHIM QOIDA: levelda qanday ma'lumot bo'lsa — o'quvchida SHU o'yinlar
// paydo bo'ladi. Shuning uchun level ro'yxatida har levelning yonida
// "qaysi o'yinlar ochilgan" ko'rsatiladi — o'qituvchi natijani darhol
// ko'radi va nima yetishmayotganini tushunadi.

import { apiFetch, tg } from "./api.js";

const state = {
  topicId: null, topicTitle: "", topicKey: "",
  levelId: null, levelTitle: "",
  tab: "terms",
  editingTermId: null,
  imageUrl: null, imageLabels: [],
};

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s == null ? "" : String(s);
  return d.innerHTML;
}
const val = id => (document.getElementById(id) || {}).value?.trim() || "";
const setVal = (id, v) => { const e = document.getElementById(id); if (e) e.value = v == null ? "" : v; };
const show = (id, v) => { const e = document.getElementById(id); if (e) e.classList.toggle("hidden", !v); };
const alertMsg = m => { if (tg.showAlert) tg.showAlert(m); else alert(m); };

async function post(path, options, errPrefix) {
  try {
    const res = await apiFetch(path, options);
    if (!res.ok) {
      let detail = "";
      try { detail = (await res.json()).detail || ""; } catch (e) {}
      alertMsg(`${errPrefix}: ${detail || `server ${res.status} xatolik qaytardi`}`);
      return null;
    }
    return await res.json();
  } catch (e) {
    console.error(e);
    alertMsg(`${errPrefix}: ${e.message || "tarmoq xatoligi"}`);
    return null;
  }
}

// --------------------------------------------------------------------------
//  Mavzular
// --------------------------------------------------------------------------

export async function loadAdminBioTopics() {
  const box = document.getElementById("adminBioTopicList");
  if (!box) return;
  try {
    const d = await (await apiFetch(`/api/admin/bio/topics`)).json();
    const topics = d.topics || [];
    if (!topics.length) { box.innerHTML = `<div class="admin-empty">Mavzu yo'q.</div>`; return; }

    box.innerHTML = topics.map(t => `
      <div class="admin-item${t.id === state.topicId ? " selected" : ""}">
        <div class="admin-item-main" data-topic="${t.id}" data-title="${esc(t.title)}" data-key="${esc(t.key)}">
          <div class="admin-item-title">${esc(t.icon || "🧬")} ${esc(t.title)}</div>
          <div class="admin-item-sub">
            ${t.level_count} level · ${t.term_count} termin · ${t.sequence_count} ketma-ketlik ·
            ${t.image_count} rasm · ${t.is_ready ? "<b>ochiq</b>" : "yopiq"}
          </div>
        </div>
        <button class="admin-mini-btn" data-toggle="${t.id}" data-ready="${t.is_ready ? 1 : 0}"
                title="${t.is_ready ? "Yopish" : "Ochish"}">${t.is_ready ? "👁" : "🚫"}</button>
      </div>`).join("");

    box.querySelectorAll("[data-topic]").forEach(el => el.addEventListener("click", () =>
      selectTopic(parseInt(el.dataset.topic, 10), el.dataset.title, el.dataset.key)));
    box.querySelectorAll("[data-toggle]").forEach(btn => btn.addEventListener("click", async () => {
      const r = await post(`/api/admin/bio/topics/${btn.dataset.toggle}`, {
        method: "PUT", body: JSON.stringify({ is_ready: btn.dataset.ready === "1" ? 0 : 1 }),
      }, "O'zgartirib bo'lmadi");
      if (r) loadAdminBioTopics();
    }));
  } catch (e) {
    console.error(e);
    box.innerHTML = `<div class="admin-empty">Yuklab bo'lmadi.</div>`;
  }
}

async function selectTopic(id, title, key) {
  Object.assign(state, { topicId: id, topicTitle: title, topicKey: key || "", levelId: null });
  ["adminBioContentBox", "adminBioTermForm", "adminBioSeqForm",
   "adminBioImgForm", "adminBioBulkForm"].forEach(x => show(x, false));
  await loadAdminBioTopics();
  await loadBioLevels();
  await refreshBioSeed();
}

async function refreshBioSeed() {
  if (!state.topicId) return;
  show("adminBioSeedBox", true);
  document.getElementById("bioSeedResult").innerHTML = "";
  try {
    const s = await (await apiFetch(
      `/api/admin/bio/seed/info?topic_key=${encodeURIComponent(state.topicKey)}`)).json();
    const btn = document.getElementById("bioSeedBtn");
    if (!s.available) {
      document.getElementById("bioSeedText").innerHTML =
        `<b>${esc(state.topicTitle)}</b> uchun tayyor namuna yo'q. Level qo'shib, ` +
        `terminlarni <b>Ommaviy</b> tugmasi orqali kiriting.`;
      btn.classList.add("hidden");
      return;
    }
    btn.classList.remove("hidden");
    document.getElementById("bioSeedText").innerHTML =
      `<b>${esc(state.topicTitle)}</b> mavzusiga ${s.level_count} level, ` +
      `${s.term_count} termin va ${s.sequence_count} ketma-ketlik qo'shiladi:<br>` +
      s.titles.map(t => `• ${esc(t)}`).join("<br>") +
      `<br><span class="chem-seed-note">Qayta bossangiz takrorlanmaydi.</span>`;
  } catch (e) { console.error(e); }
}

async function runBioSeed() {
  if (!state.topicId) { alertMsg("Avval mavzuni tanlang."); return; }
  const btn = document.getElementById("bioSeedBtn");
  btn.disabled = true;
  const r = await post(`/api/admin/bio/topics/${state.topicId}/seed`, { method: "POST" },
                       "Yuklab bo'lmadi");
  btn.disabled = false;
  if (!r) return;
  document.getElementById("bioSeedResult").innerHTML = r.added_levels
    ? `<div class="chem-bulk-result"><b>${r.added_levels} level, ${r.added_terms} termin,
         ${r.added_sequences} ketma-ketlik qo'shildi.</b></div>`
    : `<div class="chem-bulk-result">Hammasi allaqachon mavjud.</div>`;
  loadBioLevels();
  loadAdminBioTopics();
}

// --------------------------------------------------------------------------
//  Levellar
// --------------------------------------------------------------------------

async function loadBioLevels() {
  if (!state.topicId) return;
  show("adminBioLevelsBox", true);
  document.getElementById("adminBioLevelsTitle").textContent = `${state.topicTitle} — levellar`;

  const box = document.getElementById("adminBioLevelList");
  try {
    const d = await (await apiFetch(`/api/admin/bio/topics/${state.topicId}/levels`)).json();
    const levels = d.levels || [];
    if (!levels.length) {
      box.innerHTML = `<div class="admin-empty">Level yo'q — "+ Level" tugmasini bosing.</div>`;
      return;
    }
    box.innerHTML = levels.map(l => `
      <div class="admin-item${l.id === state.levelId ? " selected" : ""}">
        <div class="admin-item-main" data-level="${l.id}" data-title="${esc(l.title)}">
          <div class="admin-item-title">${l.sort_order}. ${esc(l.title)}</div>
          <div class="admin-item-sub">
            ${l.term_count} termin · ${l.sequence_count} ketma-ketlik · ${l.image_count} rasm
          </div>
          <div class="bio-stage-tags">
            ${(l.stages || []).map(s => `<span class="bio-stage-tag">${esc(s)}</span>`).join("")
              || '<span class="bio-stage-tag empty">hali o\'yin ochilmagan</span>'}
          </div>
        </div>
        <button class="admin-mini-btn danger" data-lvl-del="${l.id}">🗑</button>
      </div>`).join("");

    box.querySelectorAll("[data-level]").forEach(el => el.addEventListener("click", () =>
      selectLevel(parseInt(el.dataset.level, 10), el.dataset.title)));
    box.querySelectorAll("[data-lvl-del]").forEach(btn => btn.addEventListener("click", async () => {
      if (!confirm("Level va uning barcha mazmuni o'chiriladi. Davom etamizmi?")) return;
      const r = await post(`/api/admin/bio/levels/${btn.dataset.lvlDel}`, { method: "DELETE" },
                           "O'chirib bo'lmadi");
      if (r) {
        if (state.levelId === parseInt(btn.dataset.lvlDel, 10)) {
          state.levelId = null;
          show("adminBioContentBox", false);
        }
        loadBioLevels(); loadAdminBioTopics();
      }
    }));
  } catch (e) {
    console.error(e);
    box.innerHTML = `<div class="admin-empty">Yuklab bo'lmadi.</div>`;
  }
}

async function selectLevel(id, title) {
  state.levelId = id;
  state.levelTitle = title;
  ["adminBioTermForm", "adminBioSeqForm", "adminBioImgForm", "adminBioBulkForm"]
    .forEach(x => show(x, false));
  await loadBioLevels();
  await loadBioItems();
}

// --------------------------------------------------------------------------
//  Level mazmuni (3 tab)
// --------------------------------------------------------------------------

async function loadBioItems() {
  if (!state.levelId) return;
  show("adminBioContentBox", true);
  document.getElementById("adminBioContentTitle").textContent = state.levelTitle;
  document.querySelectorAll("[data-biotab]").forEach(b =>
    b.classList.toggle("active", b.dataset.biotab === state.tab));

  const box = document.getElementById("adminBioItemList");
  const bulkBtn = document.getElementById("adminBioBulkBtn");
  bulkBtn.classList.toggle("hidden", state.tab !== "terms");

  try {
    if (state.tab === "terms") {
      const d = await (await apiFetch(`/api/admin/bio/levels/${state.levelId}/terms`)).json();
      const items = d.terms || [];
      box.innerHTML = items.length ? items.map(t => `
        <div class="admin-item">
          <div class="admin-item-main">
            <div class="admin-item-title">${esc(t.term)}</div>
            <div class="admin-item-sub">
              ${esc(t.definition || "ta'rifsiz")}
              ${t.group_name ? ` · <b>${esc(t.group_name)}</b>` : ""}
              ${(t.clues || []).length ? ` · 🕵️ ${t.clues.length} ipucha` : ""}
            </div>
          </div>
          <button class="admin-mini-btn" data-term-edit="${t.id}">✏️</button>
          <button class="admin-mini-btn danger" data-term-del="${t.id}">🗑</button>
        </div>`).join("") : `<div class="admin-empty">Termin yo'q — "Ommaviy" eng tezi.</div>`;

      box.querySelectorAll("[data-term-edit]").forEach(b => b.addEventListener("click", () =>
        openTermForm(items.find(x => x.id === parseInt(b.dataset.termEdit, 10)))));
      box.querySelectorAll("[data-term-del]").forEach(b => b.addEventListener("click", async () => {
        if (!confirm("Bu terminni o'chirasizmi?")) return;
        if (await post(`/api/admin/bio/terms/${b.dataset.termDel}`, { method: "DELETE" },
                       "O'chirib bo'lmadi")) { loadBioItems(); loadBioLevels(); }
      }));

    } else if (state.tab === "sequences") {
      const d = await (await apiFetch(`/api/admin/bio/levels/${state.levelId}/sequences`)).json();
      const items = d.sequences || [];
      box.innerHTML = items.length ? items.map(s => `
        <div class="admin-item">
          <div class="admin-item-main">
            <div class="admin-item-title">🔢 ${esc(s.title)}</div>
            <div class="admin-item-sub">${(s.steps || []).length} bosqich:
              ${(s.steps || []).slice(0, 3).map(esc).join(" → ")}${(s.steps || []).length > 3 ? " → ..." : ""}</div>
          </div>
          <button class="admin-mini-btn danger" data-seq-del="${s.id}">🗑</button>
        </div>`).join("") : `<div class="admin-empty">Ketma-ketlik yo'q — qo'shsangiz o'quvchida "Ketma-ketlik" o'yini ochiladi.</div>`;

      box.querySelectorAll("[data-seq-del]").forEach(b => b.addEventListener("click", async () => {
        if (!confirm("Bu ketma-ketlikni o'chirasizmi?")) return;
        if (await post(`/api/admin/bio/sequences/${b.dataset.seqDel}`, { method: "DELETE" },
                       "O'chirib bo'lmadi")) { loadBioItems(); loadBioLevels(); }
      }));

    } else {
      const d = await (await apiFetch(`/api/admin/bio/levels/${state.levelId}/images`)).json();
      const items = d.tasks || [];
      box.innerHTML = items.length ? items.map(t => `
        <div class="admin-item">
          <div class="admin-item-main">
            <div class="admin-item-title">🖼 ${esc(t.title)}</div>
            <div class="admin-item-sub">${(t.labels || []).length} nuqta:
              ${(t.labels || []).slice(0, 3).map(l => esc(l.name)).join(", ")}</div>
          </div>
          <button class="admin-mini-btn danger" data-img-del="${t.id}">🗑</button>
        </div>`).join("") : `<div class="admin-empty">Rasm yo'q — qo'shsangiz "Rasm bo'yicha" o'yini ochiladi.</div>`;

      box.querySelectorAll("[data-img-del]").forEach(b => b.addEventListener("click", async () => {
        if (!confirm("Bu rasm topshirig'ini o'chirasizmi?")) return;
        if (await post(`/api/admin/bio/images/${b.dataset.imgDel}`, { method: "DELETE" },
                       "O'chirib bo'lmadi")) { loadBioItems(); loadBioLevels(); }
      }));
    }
  } catch (e) {
    console.error(e);
    box.innerHTML = `<div class="admin-empty">Yuklab bo'lmadi.</div>`;
  }
}

// --------------------------------------------------------------------------
//  Formalar
// --------------------------------------------------------------------------

function openTermForm(t) {
  state.editingTermId = t ? t.id : null;
  document.getElementById("bioTermFormTitle").textContent = t ? `Tahrirlash: ${t.term}` : "Yangi termin";
  setVal("bioTermName", t ? t.term : "");
  setVal("bioTermDef", t ? t.definition : "");
  setVal("bioTermFunc", t ? t.function_text : "");
  setVal("bioTermGroup", t ? t.group_name : "");
  setVal("bioTermClues", t && t.clues ? t.clues.join("\n") : "");
  setVal("bioTermFact", t ? t.extra_fact : "");
  show("adminBioTermForm", true);
  ["adminBioSeqForm", "adminBioImgForm", "adminBioBulkForm"].forEach(x => show(x, false));
  document.getElementById("adminBioTermForm").scrollIntoView({ behavior: "smooth" });
}

async function saveTerm() {
  if (!state.levelId) return;
  const term = val("bioTermName");
  if (!term) { alertMsg("Termin nomi majburiy."); return; }
  const body = JSON.stringify({
    term,
    definition: val("bioTermDef"),
    function_text: val("bioTermFunc"),
    group_name: val("bioTermGroup"),
    clues: val("bioTermClues"),
    extra_fact: val("bioTermFact"),
  });
  const r = state.editingTermId
    ? await post(`/api/admin/bio/terms/${state.editingTermId}`, { method: "PUT", body }, "Saqlab bo'lmadi")
    : await post(`/api/admin/bio/levels/${state.levelId}/terms`, { method: "POST", body }, "Qo'shib bo'lmadi");
  if (r) {
    show("adminBioTermForm", false);
    state.editingTermId = null;
    loadBioItems(); loadBioLevels(); loadAdminBioTopics();
  }
}

async function saveSequence() {
  if (!state.levelId) return;
  const title = val("bioSeqTitle");
  const steps = val("bioSeqSteps");
  if (!title || steps.split("\n").filter(s => s.trim()).length < 2) {
    alertMsg("Jarayon nomi va kamida 2 ta bosqich kerak.");
    return;
  }
  const r = await post(`/api/admin/bio/levels/${state.levelId}/sequences`, {
    method: "POST",
    body: JSON.stringify({ title, description: val("bioSeqDesc"), steps }),
  }, "Saqlab bo'lmadi");
  if (r) {
    setVal("bioSeqTitle", ""); setVal("bioSeqDesc", ""); setVal("bioSeqSteps", "");
    show("adminBioSeqForm", false);
    loadBioItems(); loadBioLevels(); loadAdminBioTopics();
  }
}

// ---------- Rasm: yuklash va nuqta belgilash ----------

async function uploadBioImage(file) {
  const fd = new FormData();
  fd.append("file", file);
  const res = await apiFetch(`/api/admin/upload-image`, { method: "POST", body: fd });
  if (!res.ok) { alertMsg("Rasmni yuklab bo'lmadi."); return null; }
  const d = await res.json();
  return d.url || d.image_url || null;
}

function renderImageEditor() {
  show("bioImgEditor", true);
  document.getElementById("bioImgWrap").innerHTML = `
    <img src="${esc(state.imageUrl)}" alt="" class="bio-img-editor-img" id="bioImgPreview">
    ${state.imageLabels.map((l, i) => `
      <span class="bio-img-dot" style="left:${l.x}%; top:${l.y}%">${i + 1}</span>`).join("")}`;

  document.getElementById("bioImgLabels").innerHTML = state.imageLabels.length
    ? state.imageLabels.map((l, i) => `
        <div class="bio-img-label-row">
          <span class="bio-img-label-num">${i + 1}</span>
          <span class="bio-img-label-name">${esc(l.name)}</span>
          <span class="bio-img-label-pos">${l.x}% · ${l.y}%</span>
          <button class="admin-mini-btn danger" data-lbl-del="${i}">🗑</button>
        </div>`).join("")
    : `<div class="admin-empty">Hali nuqta qo'yilmagan.</div>`;

  const img = document.getElementById("bioImgPreview");
  img.addEventListener("click", e => {
    const r = img.getBoundingClientRect();
    // Foizga aylantiramiz — rasm har xil o'lchamda ko'rsatilsa ham
    // nuqta joyida qoladi.
    const x = Math.round((e.clientX - r.left) / r.width * 100);
    const y = Math.round((e.clientY - r.top) / r.height * 100);
    const name = prompt("Bu nuqtaning nomi:");
    if (!name || !name.trim()) return;
    state.imageLabels.push({ name: name.trim(), x, y });
    renderImageEditor();
  });

  document.querySelectorAll("[data-lbl-del]").forEach(b => b.addEventListener("click", () => {
    state.imageLabels.splice(parseInt(b.dataset.lblDel, 10), 1);
    renderImageEditor();
  }));
}

async function saveImageTask() {
  if (!state.levelId) return;
  const title = val("bioImgTitle");
  if (!title || !state.imageUrl) { alertMsg("Sarlavha va rasm majburiy."); return; }
  if (!state.imageLabels.length) { alertMsg("Kamida bitta nuqta belgilang."); return; }

  const r = await post(`/api/admin/bio/levels/${state.levelId}/images`, {
    method: "POST",
    body: JSON.stringify({ title, image_url: state.imageUrl, labels: state.imageLabels }),
  }, "Saqlab bo'lmadi");
  if (r) {
    setVal("bioImgTitle", "");
    state.imageUrl = null; state.imageLabels = [];
    show("bioImgEditor", false);
    show("adminBioImgForm", false);
    loadBioItems(); loadBioLevels(); loadAdminBioTopics();
  }
}

async function bulkTerms() {
  if (!state.levelId) return;
  const text = val("bioBulkText");
  if (!text) { alertMsg("Matn bo'sh."); return; }
  const replace = document.getElementById("bioBulkReplace").checked;
  if (replace && !confirm("Levelning BARCHA eski terminlari o'chiriladi. Davom etamizmi?")) return;

  const r = await post(`/api/admin/bio/levels/${state.levelId}/terms/bulk`, {
    method: "POST", body: JSON.stringify({ text, replace }),
  }, "Yuklab bo'lmadi");
  if (!r) return;

  const skipped = r.skipped || [];
  document.getElementById("bioBulkResult").innerHTML = `
    <div class="chem-bulk-result">
      <b>${r.added} ta termin qo'shildi.</b> Levelda jami: ${r.total_now} ta.
      ${skipped.length ? `<div class="chem-bulk-skipped">
        <b>${skipped.length} ta qator o'tkazib yuborildi</b></div>` : ""}
    </div>`;
  setVal("bioBulkText", "");
  loadBioItems(); loadBioLevels(); loadAdminBioTopics();
}

// --------------------------------------------------------------------------
//  Ishga tushirish
// --------------------------------------------------------------------------

export function initAdminBioModule() {
  const on = (id, fn) => { const e = document.getElementById(id); if (e) e.addEventListener("click", fn); };

  on("bioSeedBtn", runBioSeed);

  on("adminBioLevelAddBtn", async () => {
    if (!state.topicId) { alertMsg("Avval mavzuni tanlang."); return; }
    const title = prompt("Level nomi (masalan: Hujayra organoidlari):");
    if (!title || !title.trim()) return;
    const r = await post(`/api/admin/bio/topics/${state.topicId}/levels`, {
      method: "POST", body: JSON.stringify({ title: title.trim() }),
    }, "Level qo'shib bo'lmadi");
    if (r) { loadBioLevels(); loadAdminBioTopics(); }
  });

  document.querySelectorAll("[data-biotab]").forEach(b => b.addEventListener("click", () => {
    state.tab = b.dataset.biotab;
    ["adminBioTermForm", "adminBioSeqForm", "adminBioImgForm", "adminBioBulkForm"]
      .forEach(x => show(x, false));
    loadBioItems();
  }));

  on("adminBioAddBtn", () => {
    if (!state.levelId) { alertMsg("Avval levelni tanlang."); return; }
    if (state.tab === "terms") openTermForm(null);
    else if (state.tab === "sequences") {
      show("adminBioSeqForm", true);
      document.getElementById("adminBioSeqForm").scrollIntoView({ behavior: "smooth" });
    } else {
      state.imageUrl = null; state.imageLabels = [];
      show("bioImgEditor", false);
      show("adminBioImgForm", true);
      document.getElementById("adminBioImgForm").scrollIntoView({ behavior: "smooth" });
    }
  });

  on("adminBioBulkBtn", () => {
    if (!state.levelId) { alertMsg("Avval levelni tanlang."); return; }
    document.getElementById("bioBulkResult").innerHTML = "";
    show("adminBioBulkForm", true);
    document.getElementById("adminBioBulkForm").scrollIntoView({ behavior: "smooth" });
  });

  on("bioTermSaveBtn", saveTerm);
  on("bioTermCancelBtn", () => { show("adminBioTermForm", false); state.editingTermId = null; });
  on("bioSeqSaveBtn", saveSequence);
  on("bioSeqCancelBtn", () => show("adminBioSeqForm", false));
  on("bioImgSaveBtn", saveImageTask);
  on("bioImgCancelBtn", () => show("adminBioImgForm", false));
  on("bioBulkSaveBtn", bulkTerms);
  on("bioBulkCancelBtn", () => show("adminBioBulkForm", false));

  const fileInput = document.getElementById("bioImgFile");
  if (fileInput) fileInput.addEventListener("change", async () => {
    const f = fileInput.files && fileInput.files[0];
    if (!f) return;
    const url = await uploadBioImage(f);
    if (!url) return;
    state.imageUrl = url;
    state.imageLabels = [];
    renderImageEditor();
  });
}
