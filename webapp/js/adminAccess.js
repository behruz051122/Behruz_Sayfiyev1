// js/adminAccess.js
// ==========================================================================
//  ADMIN — PULLIK GURUHLAR VA AVTOMATIK KIRISH
// ==========================================================================
// MUAMMO: o'quvchini bittalab kursga biriktirish — o'quvchi ko'p bo'lganda
// real emas.
//
// YECHIM: o'qituvchining YOPIQ guruhida bo'lgan har kim avtomatik kirish
// oladi. Bu yerda o'qituvchi guruhni qo'shadi va qaysi kontent qaysi
// guruhga tegishli ekanini belgilaydi.
//
// ESKI USUL SAQLANADI: qo'lda biriktirish ham ishlayveradi — istisno
// holatlar uchun kerak.

import { apiFetch, tg } from "./api.js";

const state = { editingGroupId: null, tab: "course", links: null };

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
//  Guruhlar ro'yxati
// --------------------------------------------------------------------------

export async function loadAdminAccessGroups() {
  const box = document.getElementById("accGroupList");
  if (!box) return;
  try {
    const d = await (await apiFetch(`/api/admin/access/groups`)).json();
    const ttl = document.getElementById("accTtlText");
    if (ttl) ttl.textContent = d.ttl_minutes || 10;

    const groups = d.groups || [];
    show("accLinksBox", groups.length > 0);

    if (!groups.length) {
      box.innerHTML = `<div class="admin-empty">
        Guruh qo'shilmagan — hozircha eski tartib (qo'lda biriktirish) ishlayapti.
      </div>`;
      return;
    }

    box.innerHTML = groups.map(g => `
      <div class="admin-item acc-group${g.is_active ? "" : " off"}">
        <div class="admin-item-main">
          <div class="admin-item-title">${g.is_active ? "🔐" : "⏸"} ${esc(g.title)}</div>
          <div class="admin-item-sub">
            <code>${esc(g.chat_id)}</code> ·
            ${g.member_count} a'zo aniqlangan ·
            ${g.course_count} kurs, ${g.stage_count} bosqich
            ${g.invite_link ? "" : " · <b>taklif havolasi yo'q</b>"}
          </div>
          ${g.last_error ? `<div class="acc-group-error">⚠️ ${esc(g.last_error)}</div>` : ""}
          ${g.setup_broken ? `<div class="acc-group-warn">
             ℹ️ Sozlama buzuq — shuning uchun bu guruh <b>hech kimni qulflamayapti</b>.
             Kirish eski tartibda ishlayapti. chat_id ni to'g'rilang yoki 🔍 bosing.
           </div>` : ""}
        </div>
        <button class="admin-mini-btn" data-verify="${g.id}" title="Botni tekshirish">🔍</button>
        <button class="admin-mini-btn" data-sync="${g.id}" title="A'zolarni yangilash">🔄</button>
        <button class="admin-mini-btn" data-edit="${g.id}">✏️</button>
        <button class="admin-mini-btn danger" data-del="${g.id}">🗑</button>
      </div>`).join("");

    box.querySelectorAll("[data-verify]").forEach(b => b.addEventListener("click", async () => {
      b.disabled = true; b.textContent = "…";
      const r = await post(`/api/admin/access/groups/${b.dataset.verify}/verify`,
                           { method: "POST" }, "Tekshirib bo'lmadi");
      b.disabled = false; b.textContent = "🔍";
      if (!r) return;
      const typeText = r.chat_type === "group" ? "oddiy guruh"
        : r.chat_type === "supergroup" ? "superguruh"
        : r.chat_type === "channel" ? "kanal" : (r.chat_type || "—");
      alertMsg(r.ok
        ? `✅ Hammasi joyida.\n\nGuruh: ${r.title || "—"}\nTuri: ${typeText}\n` +
          `A'zolar: ${r.member_count ?? "—"}\nBot admin: ha` +
          (r.migrated_to ? `\n\n♻️ Guruh supergruhga aylangan — yangi ID avtomatik saqlandi.` : "") +
          (r.note ? `\n\nℹ️ ${r.note}` : "")
        : `❌ ${r.error || "Nomaʼlum xato"}`);
      loadAdminAccessGroups();
    }));

    box.querySelectorAll("[data-sync]").forEach(b => b.addEventListener("click", async () => {
      b.disabled = true; b.textContent = "…";
      const r = await post(`/api/admin/access/groups/${b.dataset.sync}/sync`,
                           { method: "POST" }, "Yangilab bo'lmadi");
      b.disabled = false; b.textContent = "🔄";
      if (r) {
        alertMsg(`🔄 ${r.checked} ta o'quvchi tekshirildi.\nGuruhda topilgani: ${r.members} ta.`);
        loadAdminAccessGroups();
      }
    }));

    box.querySelectorAll("[data-edit]").forEach(b => b.addEventListener("click", () =>
      openGroupForm(groups.find(x => x.id === parseInt(b.dataset.edit, 10)))));

    box.querySelectorAll("[data-del]").forEach(b => b.addEventListener("click", async () => {
      if (!confirm("Guruh va uning barcha bog'lanishlari o'chiriladi. Davom etamizmi?")) return;
      if (await post(`/api/admin/access/groups/${b.dataset.del}`, { method: "DELETE" },
                     "O'chirib bo'lmadi")) {
        loadAdminAccessGroups();
        loadAccessLinks();
      }
    }));

    loadAccessLinks();
  } catch (e) {
    console.error(e);
    box.innerHTML = `<div class="admin-empty">Yuklab bo'lmadi.</div>`;
  }
}

function openGroupForm(g) {
  state.editingGroupId = g ? g.id : null;
  document.getElementById("accGroupFormTitle").textContent =
    g ? `Tahrirlash: ${g.title}` : "Yangi guruh";
  setVal("accGroupTitle", g ? g.title : "");
  setVal("accGroupChatId", g ? g.chat_id : "");
  setVal("accGroupInvite", g ? g.invite_link : "");
  document.getElementById("accGroupFormResult").innerHTML = g ? "" : `
    <div class="acc-help">
      <b>chat_id ni qanday topish mumkin:</b><br>
      1. Botni guruhga qo'shing va <b>admin</b> qiling<br>
      2. Guruhdan istalgan xabarni <b>@userinfobot</b> ga forward qiling<br>
      3. U bergan MANFIY sonni shu yerga yozing — <b>minus bilan birga</b><br>
      <br>
      <b>Ikki xil ID bo'ladi, ikkalasi ham to'g'ri:</b><br>
      • <code>-1001234567890</code> — superguruh yoki kanal<br>
      • <code>-123456789</code> — oddiy guruh (bu ham ishlaydi)<br>
      <br>
      Guruh keyinchalik supergruhga aylansa ID o'zgaradi —
      <b>tizim buni o'zi sezib yangilaydi.</b>
    </div>`;
  show("accGroupForm", true);
  document.getElementById("accGroupForm").scrollIntoView({ behavior: "smooth" });
}

async function saveGroup() {
  const title = val("accGroupTitle");
  const chatId = val("accGroupChatId");
  if (!title || !chatId) { alertMsg("Guruh nomi va chat_id majburiy."); return; }

  const body = JSON.stringify({
    title, chat_id: chatId, invite_link: val("accGroupInvite"),
  });
  const r = state.editingGroupId
    ? await post(`/api/admin/access/groups/${state.editingGroupId}`,
                 { method: "PUT", body }, "Saqlab bo'lmadi")
    : await post(`/api/admin/access/groups`, { method: "POST", body }, "Qo'shib bo'lmadi");
  if (!r) return;

  const newId = state.editingGroupId || r.id;
  show("accGroupForm", false);
  state.editingGroupId = null;
  await loadAdminAccessGroups();

  // Yangi guruh qo'shilgach DARHOL tekshiramiz — o'qituvchi "bot admin
  // emas" muammosini keyin emas, hozir bilib olsin.
  const v = await post(`/api/admin/access/groups/${newId}/verify`,
                       { method: "POST" }, "Tekshirib bo'lmadi");
  if (v) {
    alertMsg(v.ok
      ? `✅ Guruh saqlandi va tekshirildi.\n\n${v.title || ""}\nA'zolar: ${v.member_count ?? "—"}`
      : `⚠️ Guruh saqlandi, lekin:\n\n${v.error}`);
    loadAdminAccessGroups();
  }
}

// --------------------------------------------------------------------------
//  Kontentni guruhga bog'lash
// --------------------------------------------------------------------------

async function loadAccessLinks() {
  const box = document.getElementById("accLinkList");
  if (!box) return;
  try {
    const d = await (await apiFetch(`/api/admin/access/links`)).json();
    state.links = d;
    renderLinks();
  } catch (e) {
    console.error(e);
    box.innerHTML = `<div class="admin-empty">Yuklab bo'lmadi.</div>`;
  }
}

function renderLinks() {
  const d = state.links;
  if (!d) return;
  const box = document.getElementById("accLinkList");
  document.querySelectorAll("[data-acctab]").forEach(b =>
    b.classList.toggle("active", b.dataset.acctab === state.tab));

  const items = state.tab === "course" ? d.courses : d.stages;
  const groups = d.groups || [];

  if (!groups.length) {
    box.innerHTML = `<div class="admin-empty">Avval faol guruh qo'shing.</div>`;
    return;
  }
  if (!items.length) {
    box.innerHTML = `<div class="admin-empty">Ro'yxat bo'sh.</div>`;
    return;
  }

  box.innerHTML = items.map(it => `
    <div class="admin-item acc-link-item">
      <div class="admin-item-main">
        <div class="admin-item-title">
          ${esc(it.title)}${it.is_free ? ' <span class="acc-free-tag">BEPUL</span>' : ""}
        </div>
        <div class="acc-chip-row">
          ${groups.map(g => `
            <label class="acc-chip${it.group_ids.includes(g.id) ? " on" : ""}">
              <input type="checkbox" data-content="${state.tab}" data-id="${it.id}"
                     data-group="${g.id}" ${it.group_ids.includes(g.id) ? "checked" : ""}>
              <span>${esc(g.title)}</span>
            </label>`).join("")}
        </div>
      </div>
    </div>`).join("");

  box.querySelectorAll("input[type=checkbox]").forEach(cb =>
    cb.addEventListener("change", () => saveLinks(cb.dataset.content, parseInt(cb.dataset.id, 10))));
}

async function saveLinks(contentType, contentId) {
  const ids = [...document.querySelectorAll(
    `input[data-content="${contentType}"][data-id="${contentId}"]:checked`)]
    .map(cb => parseInt(cb.dataset.group, 10));

  const r = await post(`/api/admin/access/links/${contentType}/${contentId}`, {
    method: "PUT", body: JSON.stringify({ group_ids: ids }),
  }, "Saqlab bo'lmadi");
  if (!r) return;

  // Mahalliy holatni yangilaymiz — butun ro'yxatni qayta yuklamasdan
  // (o'qituvchi bir nechta belgini ketma-ket qo'yishi mumkin).
  const list = contentType === "course" ? state.links.courses : state.links.stages;
  const item = list.find(x => x.id === contentId);
  if (item) item.group_ids = ids;
  document.querySelectorAll(
    `input[data-content="${contentType}"][data-id="${contentId}"]`).forEach(cb =>
      cb.closest(".acc-chip").classList.toggle("on", cb.checked));
}

// --------------------------------------------------------------------------
//  Ishga tushirish
// --------------------------------------------------------------------------

export function initAdminAccessModule() {
  const on = (id, fn) => { const e = document.getElementById(id); if (e) e.addEventListener("click", fn); };
  on("accGroupAddBtn", () => openGroupForm(null));
  on("accGroupSaveBtn", saveGroup);
  on("accGroupCancelBtn", () => { show("accGroupForm", false); state.editingGroupId = null; });

  document.querySelectorAll("[data-acctab]").forEach(b => b.addEventListener("click", () => {
    state.tab = b.dataset.acctab;
    renderLinks();
  }));
}
