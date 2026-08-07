// js/adminChem.js
// ==========================================================================
//  ADMIN — KIMYO O'YINI MODDALAR BAZASI
// ==========================================================================
// O'qituvchi bu yerda SAVOL YOZMAYDI — faqat MODDA kiritadi. Kartochka,
// variantli test, moslashtirish, formulani yozish va battle savollari
// shu bazadan avtomatik yasaladi (chem_questions.py).
//
// Ierarxiya:  Kategoriya  ->  Level  ->  Modda
//
// Eng ko'p ishlatiladigan yo'l — OMMAVIY YUKLASH: 12 ta moddani bitta
// matn maydoniga joylashtirib yuborish. 276 ta moddani bitta-bitta
// formadan kiritish real emas.

import { apiFetch, tg } from "./api.js";

const state = {
  categoryId: null, categoryTitle: "", categoryKey: "",
  levelId: null, levelTitle: "",
  editingSubstanceId: null,
};

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s == null ? "" : String(s);
  return d.innerHTML;
}

function val(id) {
  const el = document.getElementById(id);
  return el ? el.value.trim() : "";
}

function setVal(id, v) {
  const el = document.getElementById(id);
  if (el) el.value = v == null ? "" : v;
}

function show(id, visible) {
  const el = document.getElementById(id);
  if (el) el.classList.toggle("hidden", !visible);
}

function alertMsg(msg) {
  if (tg.showAlert) tg.showAlert(msg); else alert(msg);
}

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
//  Kategoriyalar
// --------------------------------------------------------------------------

export async function loadAdminChemCategories() {
  const box = document.getElementById("adminChemCategoryList");
  if (!box) return;
  try {
    const d = await (await apiFetch(`/api/admin/chem/categories`)).json();
    const cats = d.categories || [];
    if (!cats.length) {
      box.innerHTML = `<div class="admin-empty">Kategoriya yo'q.</div>`;
      return;
    }
    box.innerHTML = cats.map(c => `
      <div class="admin-item chem-admin-cat${c.id === state.categoryId ? " selected" : ""}">
        <div class="admin-item-main" data-cat="${c.id}" data-title="${esc(c.title)}" data-key="${esc(c.key)}">
          <div class="admin-item-title">${esc(c.icon || "🧪")} ${esc(c.title)}</div>
          <div class="admin-item-sub">
            ${c.level_count} level · ${c.substance_count} modda ·
            ${c.is_ready ? "<b>o'quvchilarga ochiq</b>" : "yopiq (tez orada)"}
          </div>
        </div>
        <button class="admin-mini-btn" data-toggle="${c.id}" data-ready="${c.is_ready ? 1 : 0}"
                title="${c.is_ready ? "Yopish" : "Ochish"}">${c.is_ready ? "👁" : "🚫"}</button>
      </div>`).join("");

    box.querySelectorAll("[data-cat]").forEach(el => {
      el.addEventListener("click", () =>
        selectCategory(parseInt(el.dataset.cat, 10), el.dataset.title, el.dataset.key));
    });
    box.querySelectorAll("[data-toggle]").forEach(btn => {
      btn.addEventListener("click", async () => {
        const id = parseInt(btn.dataset.toggle, 10);
        const nowReady = btn.dataset.ready === "1";
        const r = await post(`/api/admin/chem/categories/${id}`, {
          method: "PUT", body: JSON.stringify({ is_ready: nowReady ? 0 : 1 }),
        }, "O'zgartirib bo'lmadi");
        if (r) loadAdminChemCategories();
      });
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = `<div class="admin-empty">Yuklab bo'lmadi.</div>`;
  }
}

async function selectCategory(id, title, key) {
  state.categoryId = id;
  state.categoryTitle = title;
  state.categoryKey = key || "";
  state.levelId = null;
  show("adminChemSubstancesBox", false);
  show("adminChemSubstanceForm", false);
  show("adminChemBulkForm", false);
  await loadAdminChemCategories();
  await loadLevels();
  await refreshSeedBox();
}

// --------------------------------------------------------------------------
//  Namuna baza — "bo'sh ekrandan boshlamaslik" uchun
// --------------------------------------------------------------------------

async function refreshSeedBox() {
  const box = document.getElementById("adminChemSeedBox");
  if (!box || !state.categoryId) return;
  show("adminChemSeedBox", true);
  document.getElementById("chemSeedResult").innerHTML = "";
  try {
    const s = await (await apiFetch(
      `/api/admin/chem/seed/info?category_key=${encodeURIComponent(state.categoryKey)}`)).json();
    const btn = document.getElementById("chemSeedBtn");

    if (!s.available) {
      // Bu kategoriya uchun namuna hali yozilmagan — tugmani ko'rsatmaymiz,
      // lekin nima qilish kerakligini aytamiz.
      document.getElementById("chemSeedText").innerHTML =
        `<b>${esc(state.categoryTitle)}</b> uchun tayyor namuna hali yo'q. ` +
        `Level qo'shib, moddalarni <b>Ommaviy yuklash</b> orqali kiriting.`;
      btn.classList.add("hidden");
      return;
    }

    btn.classList.remove("hidden");
    document.getElementById("chemSeedText").innerHTML =
      `<b>${esc(state.categoryTitle)}</b> kategoriyasiga ${s.level_count} ta tayyor level va ` +
      `${s.substance_count} ta modda qo'shiladi:<br>` +
      s.titles.map(t => `• ${esc(t)}`).join("<br>") +
      `<br><span class="chem-seed-note">Tugmani bir necha marta bossangiz ham takrorlanmaydi.</span>`;
  } catch (e) { console.error(e); }
}

async function runSeed() {
  if (!state.categoryId) { alertMsg("Avval kategoriyani tanlang."); return; }
  const btn = document.getElementById("chemSeedBtn");
  btn.disabled = true;
  const r = await post(`/api/admin/chem/categories/${state.categoryId}/seed`,
                       { method: "POST" }, "Yuklab bo'lmadi");
  btn.disabled = false;
  if (!r) return;

  document.getElementById("chemSeedResult").innerHTML = r.added_levels
    ? `<div class="chem-bulk-result">
         <b>${r.added_levels} ta level va ${r.added_substances} ta modda qo'shildi.</b>
         Endi levelni bosib moddalarni ko'rishingiz mumkin.
       </div>`
    : `<div class="chem-bulk-result">
         Hammasi allaqachon mavjud — hech narsa takrorlanmadi.
       </div>`;
  loadLevels();
  loadAdminChemCategories();
}

// --------------------------------------------------------------------------
//  Levellar
// --------------------------------------------------------------------------

async function loadLevels() {
  if (!state.categoryId) return;
  show("adminChemLevelsBox", true);
  document.getElementById("adminChemLevelsTitle").textContent =
    `${state.categoryTitle} — levellar`;

  const box = document.getElementById("adminChemLevelList");
  try {
    const d = await (await apiFetch(`/api/admin/chem/categories/${state.categoryId}/levels`)).json();
    const levels = d.levels || [];
    if (!levels.length) {
      box.innerHTML = `<div class="admin-empty">Level yo'q — "+ Level" tugmasini bosing.</div>`;
      return;
    }
    box.innerHTML = levels.map(l => `
      <div class="admin-item${l.id === state.levelId ? " selected" : ""}">
        <div class="admin-item-main" data-level="${l.id}" data-title="${esc(l.title)}">
          <div class="admin-item-title">${l.sort_order}. ${esc(l.title)}</div>
          <div class="admin-item-sub">${l.substance_count} modda</div>
        </div>
        <button class="admin-mini-btn" data-lvl-edit="${l.id}" data-title="${esc(l.title)}">✏️</button>
        <button class="admin-mini-btn danger" data-lvl-del="${l.id}">🗑</button>
      </div>`).join("");

    box.querySelectorAll("[data-level]").forEach(el => {
      el.addEventListener("click", () =>
        selectLevel(parseInt(el.dataset.level, 10), el.dataset.title));
    });
    box.querySelectorAll("[data-lvl-edit]").forEach(btn => {
      btn.addEventListener("click", async () => {
        const t = prompt("Level nomi:", btn.dataset.title);
        if (t === null || !t.trim()) return;
        const r = await post(`/api/admin/chem/levels/${btn.dataset.lvlEdit}`, {
          method: "PUT", body: JSON.stringify({ title: t.trim() }),
        }, "Saqlab bo'lmadi");
        if (r) loadLevels();
      });
    });
    box.querySelectorAll("[data-lvl-del]").forEach(btn => {
      btn.addEventListener("click", async () => {
        if (!confirm("Level va uning barcha moddalari o'chiriladi. Davom etamizmi?")) return;
        const r = await post(`/api/admin/chem/levels/${btn.dataset.lvlDel}`,
                             { method: "DELETE" }, "O'chirib bo'lmadi");
        if (r) {
          if (state.levelId === parseInt(btn.dataset.lvlDel, 10)) {
            state.levelId = null;
            show("adminChemSubstancesBox", false);
          }
          loadLevels();
          loadAdminChemCategories();
        }
      });
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = `<div class="admin-empty">Yuklab bo'lmadi.</div>`;
  }
}

async function selectLevel(id, title) {
  state.levelId = id;
  state.levelTitle = title;
  show("adminChemSubstanceForm", false);
  show("adminChemBulkForm", false);
  await loadLevels();
  await loadSubstances();
}

// --------------------------------------------------------------------------
//  Moddalar
// --------------------------------------------------------------------------

async function loadSubstances() {
  if (!state.levelId) return;
  show("adminChemSubstancesBox", true);
  document.getElementById("adminChemSubstancesTitle").textContent =
    `${state.levelTitle} — moddalar`;

  const box = document.getElementById("adminChemSubstanceList");
  try {
    const d = await (await apiFetch(`/api/admin/chem/levels/${state.levelId}/substances`)).json();
    const items = d.substances || [];
    if (!items.length) {
      box.innerHTML = `<div class="admin-empty">Modda yo'q — "Ommaviy yuklash" eng tezi.</div>`;
      return;
    }
    box.innerHTML = items.map(s => `
      <div class="admin-item">
        <div class="admin-item-main">
          <div class="admin-item-title chem-admin-formula">${esc(s.formula)}</div>
          <div class="admin-item-sub">${esc(s.name)}${s.historic_name ? " · " + esc(s.historic_name) : ""}</div>
        </div>
        <button class="admin-mini-btn" data-sub-edit="${s.id}">✏️</button>
        <button class="admin-mini-btn danger" data-sub-del="${s.id}">🗑</button>
      </div>`).join("");

    box.querySelectorAll("[data-sub-edit]").forEach(btn => {
      btn.addEventListener("click", () => {
        const s = items.find(x => x.id === parseInt(btn.dataset.subEdit, 10));
        openSubstanceForm(s);
      });
    });
    box.querySelectorAll("[data-sub-del]").forEach(btn => {
      btn.addEventListener("click", async () => {
        if (!confirm("Bu moddani o'chirasizmi?")) return;
        const r = await post(`/api/admin/chem/substances/${btn.dataset.subDel}`,
                             { method: "DELETE" }, "O'chirib bo'lmadi");
        if (r) { loadSubstances(); loadAdminChemCategories(); }
      });
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = `<div class="admin-empty">Yuklab bo'lmadi.</div>`;
  }
}

function openSubstanceForm(s) {
  state.editingSubstanceId = s ? s.id : null;
  document.getElementById("adminChemSubstanceFormTitle").textContent =
    s ? `Tahrirlash: ${s.formula}` : "Yangi modda";
  setVal("chemFormula", s ? s.formula : "");
  setVal("chemName", s ? s.name : "");
  setVal("chemHistoric", s ? s.historic_name : "");
  setVal("chemColorPure", s ? s.color_pure : "");
  setVal("chemColorSolution", s ? s.color_solution : "");
  setVal("chemColorPrecipitate", s ? s.color_precipitate : "");
  setVal("chemReactions", s ? s.reactions : "");
  setVal("chemUsage", s ? s.usage_text : "");
  show("adminChemSubstanceForm", true);
  show("adminChemBulkForm", false);
  document.getElementById("adminChemSubstanceForm").scrollIntoView({ behavior: "smooth" });
}

async function saveSubstance() {
  if (!state.levelId) return;
  const formula = val("chemFormula");
  const name = val("chemName");
  if (!formula || !name) {
    alertMsg("Formula va nom majburiy.");
    return;
  }
  const body = JSON.stringify({
    formula, name,
    historic_name: val("chemHistoric"),
    color_pure: val("chemColorPure"),
    color_solution: val("chemColorSolution"),
    color_precipitate: val("chemColorPrecipitate"),
    reactions: val("chemReactions"),
    usage_text: val("chemUsage"),
  });

  const r = state.editingSubstanceId
    ? await post(`/api/admin/chem/substances/${state.editingSubstanceId}`,
                 { method: "PUT", body }, "Saqlab bo'lmadi")
    : await post(`/api/admin/chem/levels/${state.levelId}/substances`,
                 { method: "POST", body }, "Qo'shib bo'lmadi");

  if (r) {
    show("adminChemSubstanceForm", false);
    state.editingSubstanceId = null;
    loadSubstances();
    loadAdminChemCategories();
  }
}

// --------------------------------------------------------------------------
//  Ommaviy yuklash
// --------------------------------------------------------------------------

async function bulkUpload() {
  if (!state.levelId) return;
  const text = val("chemBulkText");
  if (!text) { alertMsg("Matn bo'sh."); return; }
  const replace = document.getElementById("chemBulkReplace").checked;
  if (replace && !confirm("Levelning BARCHA eski moddalari o'chiriladi. Davom etamizmi?")) return;

  const r = await post(`/api/admin/chem/levels/${state.levelId}/bulk`, {
    method: "POST", body: JSON.stringify({ text, replace }),
  }, "Yuklab bo'lmadi");
  if (!r) return;

  const skipped = r.skipped || [];
  document.getElementById("chemBulkResult").innerHTML = `
    <div class="chem-bulk-result">
      <b>${r.added} ta modda qo'shildi.</b> Levelda jami: ${r.total_now} ta.
      ${skipped.length ? `
        <div class="chem-bulk-skipped">
          <b>${skipped.length} ta qator o'tkazib yuborildi:</b>
          ${skipped.slice(0, 10).map(s =>
            `<div>${s.line}-qator: ${esc(s.text)} — ${esc(s.reason)}</div>`).join("")}
          ${skipped.length > 10 ? `<div>...va yana ${skipped.length - 10} ta</div>` : ""}
        </div>` : ""}
    </div>`;

  setVal("chemBulkText", "");
  loadSubstances();
  loadAdminChemCategories();
}

// --------------------------------------------------------------------------
//  Rasmiy (sovrinli) chempionat
// --------------------------------------------------------------------------

const TOUR_STATUS = {
  open: "Ro'yxatga olish ochiq",
  qualifying: "Saralash ketmoqda",
  bracket: "Setka ketmoqda",
  finished: "Yakunlandi",
};

export async function loadAdminTournaments() {
  const box = document.getElementById("adminTournamentList");
  if (!box) return;
  try {
    const d = await (await apiFetch(`/api/admin/chem/tournaments`)).json();
    const items = d.tournaments || [];
    if (!items.length) {
      box.innerHTML = `<div class="admin-empty">Faol chempionat yo'q.</div>`;
      return;
    }
    box.innerHTML = items.map(t => `
      <div class="admin-item">
        <div class="admin-item-main">
          <div class="admin-item-title">
            ${t.is_official ? "🏆" : "👥"} ${esc(t.title)}
          </div>
          <div class="admin-item-sub">
            ${t.is_official ? "sovrinli" : esc(t.creator_name || "o'quvchi") + " yaratgan"} ·
            ${t.player_count} kishi · ${TOUR_STATUS[t.status] || t.status}
            ${t.status === "bracket" ? ` (${t.round_no}-bosqich)` : ""}
            ${t.winner_name ? ` · g'olib: <b>${esc(t.winner_name)}</b>` : ""}
            ${t.elo_counts ? "" : " · <i>ELO hisoblanmaydi</i>"}
          </div>
        </div>
        <button class="admin-mini-btn danger" data-tour-del="${t.id}">🗑</button>
      </div>`).join("");

    box.querySelectorAll("[data-tour-del]").forEach(btn => {
      btn.addEventListener("click", async () => {
        if (!confirm("Chempionat va uning barcha o'yinlari o'chiriladi. Davom etamizmi?")) return;
        const r = await post(`/api/admin/chem/tournaments/${btn.dataset.tourDel}`,
                             { method: "DELETE" }, "O'chirib bo'lmadi");
        if (r) loadAdminTournaments();
      });
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = `<div class="admin-empty">Yuklab bo'lmadi.</div>`;
  }
}

async function saveTournament() {
  const title = val("admTourTitle");
  if (!title) { alertMsg("Chempionat nomini kiriting."); return; }

  const mode = document.getElementById("admTourMode").value;
  const body = {
    title,
    prize_text: val("admTourPrize"),
    start_mode: mode,
    start_count: parseInt(val("admTourCount"), 10) || 8,
    start_at: mode === "time" ? val("admTourAt") : null,
  };
  if (mode === "time" && !body.start_at) {
    alertMsg("Boshlanish vaqtini kiriting (masalan: 2026-08-15 20:00).");
    return;
  }

  const r = await post(`/api/admin/chem/tournaments`,
                       { method: "POST", body: JSON.stringify(body) },
                       "E'lon qilib bo'lmadi");
  if (!r) return;
  setVal("admTourTitle", "");
  setVal("admTourPrize", "");
  show("adminTournamentForm", false);
  loadAdminTournaments();
}

// --------------------------------------------------------------------------
//  Ishga tushirish
// --------------------------------------------------------------------------

export function initAdminChemModule() {
  const on = (id, fn) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("click", fn);
  };

  on("adminChemLevelAddBtn", async () => {
    if (!state.categoryId) { alertMsg("Avval kategoriyani tanlang."); return; }
    const title = prompt("Level nomi (masalan: Kislotalar 1 — kislorodsiz kislotalar):");
    if (!title || !title.trim()) return;
    const r = await post(`/api/admin/chem/categories/${state.categoryId}/levels`, {
      method: "POST", body: JSON.stringify({ title: title.trim() }),
    }, "Level qo'shib bo'lmadi");
    if (r) { loadLevels(); loadAdminChemCategories(); }
  });

  on("chemSeedBtn", runSeed);
  on("adminChemSubstanceAddBtn", () => openSubstanceForm(null));
  on("chemSubstanceSaveBtn", saveSubstance);
  on("chemSubstanceCancelBtn", () => {
    show("adminChemSubstanceForm", false);
    state.editingSubstanceId = null;
  });

  on("adminChemBulkBtn", () => {
    show("adminChemBulkForm", true);
    show("adminChemSubstanceForm", false);
    document.getElementById("chemBulkResult").innerHTML = "";
    document.getElementById("adminChemBulkForm").scrollIntoView({ behavior: "smooth" });
  });
  on("chemBulkSaveBtn", bulkUpload);
  on("chemBulkCancelBtn", () => show("adminChemBulkForm", false));

  // Chempionat formasi
  on("adminTourNewBtn", () => {
    show("adminTournamentForm", true);
    document.getElementById("adminTournamentForm").scrollIntoView({ behavior: "smooth" });
  });
  on("admTourSaveBtn", saveTournament);
  on("admTourCancelBtn", () => show("adminTournamentForm", false));

  // Boshlanish sharti o'zgarganda mos maydonni ko'rsatamiz — o'qituvchi
  // keraksiz maydonni to'ldirib o'tirmaydi.
  const modeSel = document.getElementById("admTourMode");
  if (modeSel) modeSel.addEventListener("change", () => {
    const byTime = modeSel.value === "time";
    show("admTourCountRow", !byTime);
    show("admTourTimeRow", byTime);
  });
}
