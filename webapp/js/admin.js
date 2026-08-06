// js/admin.js
import { apiFetch, tg } from "./api.js";
import { errorHtml, emptyHtml, DIFFICULTY_LABELS, formatSeconds, skeletonCards,
         loadingHtml, openLightbox, showToast } from "./components.js";

const DIFFICULTY_DEFAULT_SECONDS = { oson: 300, orta: 600, qiyin: 900 };

// Vaqt chegarasini soniya o'rniga soat+daqiqa ko'rinishida kiritish/ko'rsatish
// uchun yordamchi funksiyalar (o'qituvchi uchun 86400 kabi sonlarni qo'lda
// hisoblashdan ko'ra ancha qulay).
function secondsToHoursMinutes(totalSeconds) {
  const s = parseInt(totalSeconds) || 0;
  return { hours: Math.floor(s / 3600), minutes: Math.floor((s % 3600) / 60) };
}
function hoursMinutesToSeconds(hoursStr, minutesStr) {
  const h = parseInt(hoursStr) || 0;
  const m = parseInt(minutesStr) || 0;
  return h * 3600 + m * 60;
}

// Maydondan BUTUN SON o'qish — maydon bo'sh qoldirilgan bo'lsa ham hech
// qachon NaN qaytarmaydi.
//
// NEGA KERAK: oddiy parseInt("") — NaN beradi, JSON.stringify(NaN) esa
// "null" ga aylanadi. Server tomonida int(None) chaqirilib, so'rov 500
// xatolik bilan yiqilardi. Natijada admin, masalan, "Tartib raqami"
// maydonini tozalab qo'ysa — "Testni saqlash" bosilganda hech narsa
// saqlanmasdan, hech qanday xabar ham ko'rsatilmasdan forma yopilib
// ketardi ("bir necha marta urinsam ishlaydi" muammosining asl sababi).
function intVal(elementId, fallback = 0) {
  const el = document.getElementById(elementId);
  const n = parseInt(el ? el.value : "", 10);
  return Number.isNaN(n) ? fallback : n;
}

// Admin formalarini saqlash uchun umumiy yordamchi: so'rov muvaffaqiyatsiz
// bo'lsa — endi JIMGINA o'tib ketmaydi, aniq xabar ko'rsatadi va false
// qaytaradi (chaqiruvchi forma yopilmasligi/ro'yxat yangilanmasligi uchun).
async function saveOrAlert(path, options, errorPrefix = "Saqlab bo'lmadi") {
  try {
    const res = await apiFetch(path, options);
    if (!res.ok) {
      let detail = "";
      try {
        const data = await res.json();
        detail = data && data.detail ? (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)) : "";
      } catch (e) { /* javob JSON bo'lmasligi mumkin */ }
      const msg = `${errorPrefix}: ${detail || `server ${res.status} xatolik qaytardi`}`;
      tg.showAlert ? tg.showAlert(msg) : alert(msg);
      return false;
    }
    return true;
  } catch (e) {
    console.error(e);
    const msg = `${errorPrefix}: ${e.message || "tarmoq xatoligi"}`;
    tg.showAlert ? tg.showAlert(msg) : alert(msg);
    return false;
  }
}

let currentAdminCourses = [];
let currentAdminCourseCategories = [];
let currentAdminTests = [];
let currentTestSubjectCards = [];
let currentTestStages = [];
let currentTestGroups = [];
let objectionsStatusFilter = "pending";

// ---------- Statistika (dashboard) ----------

export async function loadAdminAnalytics() {
  const statsGrid = document.getElementById("analyticsStatsGrid");
  const topLists = document.getElementById("analyticsTopLists");
  statsGrid.innerHTML = skeletonCards(1);
  topLists.innerHTML = "";
  try {
    const res = await apiFetch(`/api/admin/analytics`);
    const a = await res.json();

    statsGrid.innerHTML = `
      <div class="analytics-stat-card"><div class="num">${a.total_users}</div><div class="lbl">Foydalanuvchilar</div></div>
      <div class="analytics-stat-card"><div class="num">🪙 ${a.total_coins}</div><div class="lbl">Berilgan coinlar</div></div>
      <div class="analytics-stat-card"><div class="num">${a.total_lessons_watched}</div><div class="lbl">Ko'rilgan darslar</div></div>
      <div class="analytics-stat-card"><div class="num">${a.total_test_attempts}</div><div class="lbl">Test urinishlari</div></div>
      <div class="analytics-stat-card"><div class="num">${a.avg_test_score_percent}%</div><div class="lbl">O'rtacha test natijasi</div></div>
      <div class="analytics-stat-card"><div class="num">${a.confirmed_referrals}</div><div class="lbl">Tasdiqlangan takliflar</div></div>
      <div class="analytics-stat-card"><div class="num">${a.paid_enrollments_count}</div><div class="lbl">Pullik obunalar</div></div>
      <div class="analytics-stat-card"><div class="num">${(a.estimated_revenue || 0).toLocaleString()}</div><div class="lbl">Taxminiy tushum (so'm)</div></div>
    `;

    let html = "";
    if (a.top_courses.length > 0) {
      html += `<div class="analytics-top-block"><h4>📘 Eng ko'p ko'rilgan kurslar</h4>`;
      a.top_courses.forEach(c => {
        html += `<div class="analytics-top-row"><span class="name">${c.title}</span><span class="count">${c.watch_count} marta</span></div>`;
      });
      html += `</div>`;
    }
    if (a.top_tests.length > 0) {
      html += `<div class="analytics-top-block"><h4>📝 Eng ko'p topshirilgan testlar</h4>`;
      a.top_tests.forEach(t => {
        html += `<div class="analytics-top-row"><span class="name">${t.title}</span><span class="count">${t.attempt_count} marta</span></div>`;
      });
      html += `</div>`;
    }
    topLists.innerHTML = html;
  } catch (e) {
    console.error(e);
    statsGrid.innerHTML = errorHtml();
  }
}

// ---------- Bosh sahifa kartalari (Kurslar/Testlar/Reyting/Kitoblar/O'yinlar/Natijalar) ----------

export async function loadAdminDashboardCards() {
  document.getElementById("adminDashboardCardForm").classList.add("hidden");
  const box = document.getElementById("adminDashboardCardsList");
  box.innerHTML = skeletonCards(2);
  try {
    const res = await apiFetch(`/api/admin/dashboard-cards`);
    const data = await res.json();
    box.innerHTML = "";
    data.cards.forEach(c => {
      const row = document.createElement("div");
      row.className = "admin-row";
      row.innerHTML = `
        <div class="emoji">${c.icon || "✨"}</div>
        <div class="info">
          <div class="t">${c.title}${c.is_active ? "" : " (yashirin)"}</div>
          <div class="s">${c.subtitle || ""}</div>
        </div>
        <div class="row-actions">
          <button data-a="edit">Tahrirlash</button>
        </div>
      `;
      row.querySelector('[data-a="edit"]').onclick = () => openAdminDashboardCardForm(c);
      box.appendChild(row);
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

function openAdminDashboardCardForm(card) {
  document.getElementById("adminDashboardCardForm").classList.remove("hidden");
  document.getElementById("adminDashboardCardFormTitle").textContent = `Kartani tahrirlash — ${card.title}`;
  document.getElementById("dc_key").value = card.card_key;
  document.getElementById("dc_title").value = card.title;
  document.getElementById("dc_subtitle").value = card.subtitle || "";
  document.getElementById("dc_icon").value = card.icon || "";
  document.getElementById("dc_order_num").value = card.order_num;
  document.getElementById("dc_is_active").value = String(card.is_active);
}

// ---------- Kitoblar do'koni (bosma kitoblar) ----------
// E'TIBOR: bu Kurslar/Kitoblar (raqamli o'qish kontenti) dan BUTUNLAY
// ALOHIDA — bu yerda bosma, pochta orqali yetkaziladigan kitoblar
// boshqariladi (book_products jadvali).

export async function loadAdminBookProducts() {
  document.getElementById("adminBookProductForm").classList.add("hidden");
  const box = document.getElementById("adminBookProductsList");
  box.innerHTML = skeletonCards(2);
  try {
    const res = await apiFetch(`/api/admin/book-products`);
    const data = await res.json();
    box.innerHTML = "";
    if (data.products.length === 0) box.innerHTML = emptyHtml("Hali mahsulot qo'shilmagan");
    data.products.forEach(p => {
      const row = document.createElement("div");
      row.className = "admin-row";
      const priceLabel = p.price ? `${p.price.toLocaleString()} so'm` : "Narxi ko'rsatilmagan";
      row.innerHTML = `
        <div class="emoji">📘</div>
        <div class="info">
          <div class="t">${p.title}${p.is_active ? "" : " (yashirin)"}</div>
          <div class="s">${p.category || "Kategoriyasiz"} · ${priceLabel}</div>
        </div>
        <div class="row-actions">
          <button data-a="edit">Tahrirlash</button>
          <button data-a="delete" class="danger">O'chirish</button>
        </div>
      `;
      row.querySelector('[data-a="edit"]').onclick = () => openAdminBookProductForm(p);
      row.querySelector('[data-a="delete"]').onclick = async () => {
        if (!confirm("Bu mahsulotni butunlay o'chirmoqchimisiz?")) return;
        await apiFetch(`/api/admin/book-products/${p.id}`, { method: "DELETE" });
        loadAdminBookProducts();
      };
      box.appendChild(row);
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

function openAdminBookProductForm(product) {
  document.getElementById("adminBookProductForm").classList.remove("hidden");
  document.getElementById("adminBookProductFormTitle").textContent = product ? "Mahsulotni tahrirlash" : "Yangi mahsulot";
  document.getElementById("bp_id").value = product ? product.id : "";
  document.getElementById("bp_title").value = product ? product.title : "";
  document.getElementById("bp_subtitle").value = product ? (product.subtitle || "") : "";
  document.getElementById("bp_description").value = product ? (product.description || "") : "";
  document.getElementById("bp_category").value = product ? (product.category || "") : "";
  document.getElementById("bp_price").value = product ? (product.price || 0) : 0;
  document.getElementById("bp_image_file").value = "";
  document.getElementById("bpImageUploadStatus").textContent = "";
  showBookProductImagePreview(product ? (product.image_url || "") : "");
  document.getElementById("bp_badge_text").value = product ? (product.badge_text || "") : "";
  document.getElementById("bp_is_bundle").value = product ? String(product.is_bundle) : "0";
  document.getElementById("bp_contact_username").value = product ? (product.contact_username || "") : "";
  populateBookProductCourseSelect(product ? product.linked_course_id : null);
  document.getElementById("bp_order_num").value = product ? product.order_num : 0;
  document.getElementById("bp_is_active").value = product ? String(product.is_active) : "1";
}

function populateBookProductCourseSelect(selectedCourseId) {
  const select = document.getElementById("bp_linked_course_id");
  select.innerHTML = `<option value="">— Bog'lanmagan —</option>`;
  currentAdminCourses.forEach(c => {
    const opt = document.createElement("option");
    opt.value = c.id;
    opt.textContent = `${c.title} (${c.subject})`;
    select.appendChild(opt);
  });
  select.value = selectedCourseId ? String(selectedCourseId) : "";
}

function showBookProductImagePreview(url) {
  document.getElementById("bp_image_url").value = url || "";
  const wrap = document.getElementById("bpImagePreviewWrap");
  const img = document.getElementById("bpImagePreview");
  if (url) {
    img.src = url;
    wrap.classList.remove("hidden");
  } else {
    img.src = "";
    wrap.classList.add("hidden");
  }
}

async function uploadBookProductImage(file) {
  const status = document.getElementById("bpImageUploadStatus");
  status.textContent = "⏳ Yuklanmoqda...";
  try {
    const formData = new FormData();
    formData.append("file", file);
    const res = await apiFetch(`/api/admin/upload-image`, { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Yuklab bo'lmadi");
    }
    const data = await res.json();
    showBookProductImagePreview(data.url);
    status.textContent = "✅ Rasm yuklandi";
  } catch (e) {
    console.error(e);
    status.textContent = `❌ ${e.message || "Xatolik yuz berdi"}`;
    document.getElementById("bp_image_file").value = "";
  }
}

// ---------- FAQ / Yordam savollari ----------

export async function loadAdminFaq() {
  document.getElementById("adminFaqForm").classList.add("hidden");
  const box = document.getElementById("adminFaqList");
  box.innerHTML = skeletonCards(2);
  try {
    const res = await apiFetch(`/api/admin/faq`);
    const data = await res.json();
    box.innerHTML = "";
    if (data.items.length === 0) box.innerHTML = emptyHtml("Hali savol qo'shilmagan");
    data.items.forEach(item => {
      const row = document.createElement("div");
      row.className = "admin-row";
      row.innerHTML = `
        <div class="emoji">❓</div>
        <div class="info">
          <div class="t">${item.question}${item.is_active ? "" : " (yashirin)"}</div>
          <div class="s">${(item.answer || "").slice(0, 60)}${item.answer.length > 60 ? "…" : ""}</div>
        </div>
        <div class="row-actions">
          <button data-a="edit">Tahrirlash</button>
          <button data-a="delete" class="danger">O'chirish</button>
        </div>
      `;
      row.querySelector('[data-a="edit"]').onclick = () => openAdminFaqForm(item);
      row.querySelector('[data-a="delete"]').onclick = async () => {
        if (!confirm("Bu savolni butunlay o'chirmoqchimisiz?")) return;
        await apiFetch(`/api/admin/faq/${item.id}`, { method: "DELETE" });
        loadAdminFaq();
      };
      box.appendChild(row);
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

function openAdminFaqForm(item) {
  document.getElementById("adminFaqForm").classList.remove("hidden");
  document.getElementById("adminFaqFormTitle").textContent = item ? "Savolni tahrirlash" : "Yangi savol";
  document.getElementById("faq_id").value = item ? item.id : "";
  document.getElementById("faq_question").value = item ? item.question : "";
  document.getElementById("faq_answer").value = item ? item.answer : "";
  document.getElementById("faq_order_num").value = item ? item.order_num : 0;
  document.getElementById("faq_is_active").value = item ? String(item.is_active) : "1";
}

// ---------- Natijalar (o'quvchi fikri + sertifikat natijalari) ----------
// E'TIBOR: bu Reyting (leaderboard)dan BUTUNLAY ALOHIDA — bu yerdagi har
// bir yozuvni admin qo'lda qo'shadi (rasm + qisqa natija + fikr).

export async function loadAdminStudentResults() {
  document.getElementById("adminStudentResultForm").classList.add("hidden");
  const box = document.getElementById("adminStudentResultsList");
  box.innerHTML = skeletonCards(2);
  try {
    const res = await apiFetch(`/api/admin/student-results`);
    const data = await res.json();
    box.innerHTML = "";
    if (data.results.length === 0) box.innerHTML = emptyHtml("Hali natija qo'shilmagan");
    data.results.forEach(r => {
      const row = document.createElement("div");
      row.className = "admin-row";
      row.innerHTML = `
        <div class="emoji">🏆</div>
        <div class="info">
          <div class="t">${r.student_name}${r.is_active ? "" : " (yashirin)"}</div>
          <div class="s">${r.subject || "Fansiz"} · ${r.result_text || "Natija matni yo'q"}</div>
        </div>
        <div class="row-actions">
          <button data-a="edit">Tahrirlash</button>
          <button data-a="delete" class="danger">O'chirish</button>
        </div>
      `;
      row.querySelector('[data-a="edit"]').onclick = () => openAdminStudentResultForm(r);
      row.querySelector('[data-a="delete"]').onclick = async () => {
        if (!confirm("Bu natijani butunlay o'chirmoqchimisiz?")) return;
        await apiFetch(`/api/admin/student-results/${r.id}`, { method: "DELETE" });
        loadAdminStudentResults();
      };
      box.appendChild(row);
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

function openAdminStudentResultForm(result) {
  document.getElementById("adminStudentResultForm").classList.remove("hidden");
  document.getElementById("adminStudentResultFormTitle").textContent = result ? "Natijani tahrirlash" : "Yangi natija";
  document.getElementById("sr_id").value = result ? result.id : "";
  document.getElementById("sr_student_name").value = result ? result.student_name : "";
  document.getElementById("sr_subject").value = result ? (result.subject || "") : "";
  document.getElementById("sr_image_file").value = "";
  document.getElementById("srImageUploadStatus").textContent = "";
  showStudentResultImagePreview(result ? (result.image_url || "") : "");
  document.getElementById("sr_result_text").value = result ? (result.result_text || "") : "";
  document.getElementById("sr_feedback_text").value = result ? (result.feedback_text || "") : "";
  document.getElementById("sr_order_num").value = result ? result.order_num : 0;
  document.getElementById("sr_is_active").value = result ? String(result.is_active) : "1";
}

function showStudentResultImagePreview(url) {
  document.getElementById("sr_image_url").value = url || "";
  const wrap = document.getElementById("srImagePreviewWrap");
  const img = document.getElementById("srImagePreview");
  if (url) {
    img.src = url;
    wrap.classList.remove("hidden");
  } else {
    img.src = "";
    wrap.classList.add("hidden");
  }
}

async function uploadStudentResultImage(file) {
  const status = document.getElementById("srImageUploadStatus");
  status.textContent = "⏳ Yuklanmoqda...";
  try {
    const formData = new FormData();
    formData.append("file", file);
    const res = await apiFetch(`/api/admin/upload-image`, { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Yuklab bo'lmadi");
    }
    const data = await res.json();
    showStudentResultImagePreview(data.url);
    status.textContent = "✅ Rasm yuklandi";
  } catch (e) {
    console.error(e);
    status.textContent = `❌ ${e.message || "Xatolik yuz berdi"}`;
    document.getElementById("sr_image_file").value = "";
  }
}

// ---------- Nazorat testi natijalari (bitta test bo'yicha talabalar ballari) ----------

async function openAdminControlResults(testId, title) {
  document.getElementById("adminControlResultsPanel").classList.remove("hidden");
  document.getElementById("adminTestForm").classList.add("hidden");
  document.getElementById("adminQuestionsPanel").classList.add("hidden");
  document.getElementById("adminControlAccessPanel").classList.add("hidden");
  document.getElementById("adminControlResultsTitle").textContent = `Natijalar — ${title}`;

  const box = document.getElementById("controlResultsList");
  box.innerHTML = skeletonCards(2);
  try {
    const res = await apiFetch(`/api/admin/control-tests/${testId}/results`);
    const data = await res.json();
    if (data.results.length === 0) {
      box.innerHTML = emptyHtml("Hali hech kim bu testni ishlamagan");
      return;
    }
    box.innerHTML = "";
    data.results.forEach((r, i) => {
      const row = document.createElement("div");
      row.className = "admin-row";
      const name = r.first_name || "Noma'lum";
      const usernamePart = r.username ? ` · @${r.username}` : "";
      row.innerHTML = `
        <div class="info">
          <div class="t">${i + 1}. ${name}${usernamePart}</div>
          <div class="s">✅ ${r.score}/${r.total_questions} to'g'ri (${r.percent}%) · ID: ${r.telegram_id}</div>
        </div>
      `;
      box.appendChild(row);
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

// ---------- DTM Simulyatorlari ----------

let currentAdminSimulators = [];

export async function loadAdminSimulators() {
  document.getElementById("adminSimulatorForm").classList.add("hidden");
  document.getElementById("adminSimSubjectsPanel").classList.add("hidden");
  const box = document.getElementById("adminSimulatorsList");
  box.innerHTML = skeletonCards(2);
  try {
    const res = await apiFetch(`/api/admin/simulators`);
    const data = await res.json();
    currentAdminSimulators = data.simulators;
    box.innerHTML = "";
    if (currentAdminSimulators.length === 0) box.innerHTML = emptyHtml("Hali simulyator qo'shilmagan");
    currentAdminSimulators.forEach(s => {
      const totalQ = s.subjects.reduce((a, x) => a + x.question_count, 0);
      const row = document.createElement("div");
      row.className = "admin-row";
      row.innerHTML = `
        <div class="info">
          <div class="t">${s.title}${s.is_active ? "" : " (yashirin)"}</div>
          <div class="s">${s.subjects.length} ta fan · ${totalQ} savol · ${formatSeconds(s.time_limit_seconds)}</div>
        </div>
        <div class="row-actions">
          <button data-a="subjects">Fanlar</button>
          <button data-a="edit">Tahrirlash</button>
          <button data-a="delete" class="danger">O'chirish</button>
        </div>
      `;
      row.querySelector('[data-a="subjects"]').onclick = () => openAdminSimSubjects(s.id, s.title);
      row.querySelector('[data-a="edit"]').onclick = () => openAdminSimulatorForm(s);
      row.querySelector('[data-a="delete"]').onclick = () => deleteAdminSimulator(s.id);
      box.appendChild(row);
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

function openAdminSimulatorForm(sim) {
  document.getElementById("adminSimulatorForm").classList.remove("hidden");
  document.getElementById("adminSimSubjectsPanel").classList.add("hidden");
  document.getElementById("adminSimulatorFormTitle").textContent = sim ? "Simulyatorni tahrirlash" : "Yangi simulyator";
  document.getElementById("as_id").value = sim ? sim.id : "";
  document.getElementById("as_title").value = sim ? sim.title : "";
  document.getElementById("as_description").value = sim ? (sim.description || "") : "";
  {
    const { hours, minutes } = secondsToHoursMinutes(sim ? sim.time_limit_seconds : 10800);
    document.getElementById("as_time_limit_hours").value = hours || "";
    document.getElementById("as_time_limit_minutes").value = minutes || "";
  }
  document.getElementById("as_order_num").value = sim ? sim.order_num : 0;
  document.getElementById("as_is_active").value = sim ? String(sim.is_active) : "1";
}

async function deleteAdminSimulator(id) {
  if (!confirm("Bu simulyatorni butunlay o'chirmoqchimisiz? Fanlar tarkibi ham o'chadi.")) return;
  await apiFetch(`/api/admin/simulators/${id}`, { method: "DELETE" });
  loadAdminSimulators();
}

// ---------- Simulyator fanlari tarkibi ----------

let currentSimSubjectsSimId = null;

async function openAdminSimSubjects(simulatorId, title) {
  currentSimSubjectsSimId = simulatorId;
  document.getElementById("adminSimSubjectsPanel").classList.remove("hidden");
  document.getElementById("adminSimulatorForm").classList.add("hidden");
  document.getElementById("adminSimSubjectsTitle").textContent = `Fanlar tarkibi — ${title}`;
  document.getElementById("ass_simulator_id").value = simulatorId;
  document.getElementById("ass_subject").value = "";
  document.getElementById("ass_question_count").value = 10;
  document.getElementById("ass_order_num").value = 0;
  await renderAdminSimSubjects(simulatorId);
}

async function renderAdminSimSubjects(simulatorId) {
  const res = await apiFetch(`/api/admin/simulators/${simulatorId}/subjects`);
  const data = await res.json();
  const box = document.getElementById("adminSimSubjectsList");
  box.innerHTML = "";

  const poolMap = {};
  data.subject_pools.forEach(p => { poolMap[p.subject.trim().toLowerCase()] = p.question_count; });

  const datalist = document.getElementById("subjectPoolOptions");
  datalist.innerHTML = data.subject_pools.map(p => `<option value="${p.subject}">`).join("");

  if (data.subjects.length === 0) box.innerHTML = emptyHtml("Hali fan qo'shilmagan");
  data.subjects.forEach(s => {
    const available = poolMap[s.subject.trim().toLowerCase()] || 0;
    const isEnough = available >= s.question_count;
    const row = document.createElement("div");
    row.className = "admin-row";
    row.innerHTML = `
      <div class="info">
        <div class="t">${s.subject}</div>
        <div class="s">${s.question_count} ta so'raladi · pool'da ${available} ta bor ${isEnough ? "✅" : "⚠️ YETARLI EMAS"}</div>
      </div>
      <div class="row-actions">
        <button data-a="delete" class="danger">O'chirish</button>
      </div>
    `;
    row.querySelector('[data-a="delete"]').onclick = async () => {
      if (!confirm(`"${s.subject}" fanini simulyatordan o'chirmoqchimisiz?`)) return;
      await apiFetch(`/api/admin/simulator-subjects/${s.id}`, { method: "DELETE" });
      renderAdminSimSubjects(simulatorId);
      loadAdminSimulators();
    };
    box.appendChild(row);
  });
}

// ---------- Kurslar ----------

export async function loadAdminCourses() {
  document.getElementById("adminCourseForm").classList.add("hidden");
  document.getElementById("adminParagraphsPanel").classList.add("hidden");
  document.getElementById("adminLessonsPanel").classList.add("hidden");
  document.getElementById("adminPricingTiersPanel").classList.add("hidden");
  document.getElementById("adminCourseCategoriesPanel").classList.add("hidden");
  const box = document.getElementById("adminCoursesList");
  box.innerHTML = skeletonCards(2);
  try {
    const [coursesRes, categoriesRes] = await Promise.all([
      apiFetch(`/api/admin/courses`),
      apiFetch(`/api/admin/course-categories`)
    ]);
    const data = await coursesRes.json();
    const categoriesData = await categoriesRes.json();
    currentAdminCourses = data.courses;
    currentAdminCourseCategories = categoriesData.categories;
    const categoryById = Object.fromEntries(currentAdminCourseCategories.map(c => [c.id, c]));
    box.innerHTML = "";
    currentAdminCourses.forEach(c => {
      const row = document.createElement("div");
      row.className = "admin-row";
      const accessLabel = c.is_free ? "Bepul" : (c.price > 0 ? c.price.toLocaleString() + " so'm" : c.required_referrals + " taklif");
      const categoryBadges = (c.category_ids || [])
        .map(cid => categoryById[cid])
        .filter(Boolean)
        .map(cat => `<span class="control-badge">${cat.icon || "📁"} ${cat.title.toUpperCase()}</span>`)
        .join("");
      const pricingBtn = !c.is_free ? `<button data-a="pricing">💳 Paketlar</button>` : "";
      row.innerHTML = `
        <div class="emoji">${c.thumbnail_emoji || "📘"}</div>
        <div class="info">
          <div class="t">${c.title}${c.is_active ? "" : " (yashirin)"}${categoryBadges}</div>
          <div class="s">${c.subject} · ${c.resource_type === "book" ? "Kitob" : "Kurs"} · ${c.lessons_count} dars${c.lessons_count_override ? " (qo'lda)" : ""} · ${accessLabel}</div>
        </div>
        <div class="row-actions">
          <button data-a="paragraphs">Bo'limlar</button>
          ${pricingBtn}
          <button data-a="edit">Tahrirlash</button>
          <button data-a="delete" class="danger">O'chirish</button>
        </div>
      `;
      row.querySelector('[data-a="paragraphs"]').onclick = () => openAdminParagraphs(c.id, c.title);
      if (pricingBtn) row.querySelector('[data-a="pricing"]').onclick = () => openAdminPricingTiers(c.id, c.title);
      row.querySelector('[data-a="edit"]').onclick = () => openAdminCourseForm(c);
      row.querySelector('[data-a="delete"]').onclick = () => deleteAdminCourse(c.id);
      box.appendChild(row);
    });
    populateEnrollCourseSelect();
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

function populateEnrollCourseSelect() {
  const select = document.getElementById("en_course_id");
  select.innerHTML = "";
  currentAdminCourses.filter(c => !c.is_free).forEach(c => {
    const opt = document.createElement("option");
    opt.value = c.id;
    opt.textContent = `${c.title} (${c.subject})`;
    select.appendChild(opt);
  });
}

function openAdminCourseForm(course) {
  document.getElementById("adminCourseForm").classList.remove("hidden");
  document.getElementById("adminParagraphsPanel").classList.add("hidden");
  document.getElementById("adminLessonsPanel").classList.add("hidden");
  document.getElementById("adminPricingTiersPanel").classList.add("hidden");
  document.getElementById("adminCourseCategoriesPanel").classList.add("hidden");
  document.getElementById("adminCourseFormTitle").textContent = course ? "Kursni tahrirlash" : "Yangi kurs";
  document.getElementById("ac_id").value = course ? course.id : "";
  document.getElementById("ac_title").value = course ? course.title : "";
  document.getElementById("ac_subject").value = course ? course.subject : "";
  document.getElementById("ac_resource_type").value = course ? course.resource_type : "course";
  document.getElementById("ac_description").value = course ? (course.description || "") : "";
  document.getElementById("ac_is_free").value = course ? String(course.is_free) : "1";
  document.getElementById("ac_required_referrals").value = course ? course.required_referrals : 0;
  document.getElementById("ac_price").value = course ? (course.price || 0) : 0;
  document.getElementById("ac_duration_days").value = course && course.duration_days ? course.duration_days : "";
  document.getElementById("ac_students_count").value = course ? (course.students_count || 0) : 0;
  document.getElementById("ac_duration_text").value = course ? (course.duration_text || "") : "";
  document.getElementById("ac_lessons_override").value = course && course.lessons_count_override ? course.lessons_count_override : "";
  document.getElementById("ac_thumbnail_emoji").value = course ? (course.thumbnail_emoji || "📘") : "📘";
  document.getElementById("ac_order_num").value = course ? course.order_num : 0;
  document.getElementById("ac_is_active").value = course ? String(course.is_active) : "1";
  renderCourseCategoryCheckboxes(course ? (course.category_ids || []) : []);
}

function renderCourseCategoryCheckboxes(selectedIds) {
  const box = document.getElementById("ac_category_checkboxes");
  box.innerHTML = "";
  if (currentAdminCourseCategories.length === 0) {
    box.innerHTML = `<div class="admin-checkbox-list-empty">Hali guruh yaratilmagan — yuqoridagi "🗂 Guruhlar" tugmasi orqali qo'shing.</div>`;
    return;
  }
  currentAdminCourseCategories.forEach(cat => {
    const label = document.createElement("label");
    label.className = "checkbox-label";
    label.innerHTML = `<input type="checkbox" value="${cat.id}" ${selectedIds.includes(cat.id) ? "checked" : ""}><span>${cat.icon || "📁"} ${cat.title}</span>`;
    box.appendChild(label);
  });
}

async function deleteAdminCourse(id) {
  if (!confirm("Bu kursni butunlay o'chirmoqchimisiz? Barcha bo'lim va darslar ham o'chadi.")) return;
  await apiFetch(`/api/admin/courses/${id}`, { method: "DELETE" });
  loadAdminCourses();
}

// ---------- Narx paketlari ----------

let adminActivePricingCourseId = null;

async function openAdminPricingTiers(courseId, title) {
  adminActivePricingCourseId = courseId;
  document.getElementById("adminPricingTiersPanel").classList.remove("hidden");
  document.getElementById("adminCourseForm").classList.add("hidden");
  document.getElementById("adminParagraphsPanel").classList.add("hidden");
  document.getElementById("adminLessonsPanel").classList.add("hidden");
  document.getElementById("adminPricingTiersTitle").textContent = `Narx paketlari — ${title}`;
  document.getElementById("pt_course_id").value = courseId;
  resetPricingTierForm();
  await renderAdminPricingTiers(courseId);
}

function resetPricingTierForm() {
  document.getElementById("pt_id").value = "";
  document.getElementById("pt_label").value = "";
  document.getElementById("pt_price").value = 0;
  document.getElementById("pt_original_price").value = "";
  document.getElementById("pt_duration_text").value = "";
  document.getElementById("pt_order_num").value = 0;
  document.getElementById("pt_is_active").value = "1";
}

async function renderAdminPricingTiers(courseId) {
  const res = await apiFetch(`/api/admin/courses/${courseId}/pricing-tiers`);
  const data = await res.json();
  const box = document.getElementById("adminPricingTiersList");
  box.innerHTML = "";
  if (data.tiers.length === 0) box.innerHTML = emptyHtml("Hali paket qo'shilmagan — bo'lmasa talabaga oddiy narx ko'rsatiladi");
  data.tiers.forEach(t => {
    const row = document.createElement("div");
    row.className = "admin-row";
    const priceText = t.original_price
      ? `${t.price.toLocaleString()} so'm (avvalgisi ${t.original_price.toLocaleString()})`
      : `${t.price.toLocaleString()} so'm`;
    row.innerHTML = `
      <div class="info">
        <div class="t">${t.label}${t.is_active ? "" : " (yashirin)"}</div>
        <div class="s">${priceText}${t.duration_text ? " · " + t.duration_text : ""}</div>
      </div>
      <div class="row-actions">
        <button data-a="edit">Tahrirlash</button>
        <button data-a="delete" class="danger">O'chirish</button>
      </div>
    `;
    row.querySelector('[data-a="edit"]').onclick = () => {
      document.getElementById("pt_id").value = t.id;
      document.getElementById("pt_label").value = t.label;
      document.getElementById("pt_price").value = t.price;
      document.getElementById("pt_original_price").value = t.original_price || "";
      document.getElementById("pt_duration_text").value = t.duration_text || "";
      document.getElementById("pt_order_num").value = t.order_num;
      document.getElementById("pt_is_active").value = String(t.is_active);
    };
    row.querySelector('[data-a="delete"]').onclick = async () => {
      if (!confirm("Bu paketni o'chirmoqchimisiz?")) return;
      await apiFetch(`/api/admin/pricing-tiers/${t.id}`, { method: "DELETE" });
      renderAdminPricingTiers(courseId);
    };
    box.appendChild(row);
  });
}

// ---------- Kurs guruhlari (kategoriyalari) ----------
// Admin o'zi istalgan nomda guruh yaratadi (masalan "Nazoratli", "Mustaqil",
// "Bepul kurs") va kurs formasida har bir kursni bir nechta guruhga baravar
// biriktiradi. Bu barcha kurslar uchun umumiy (global) ro'yxat.

async function openAdminCourseCategories() {
  document.getElementById("adminCourseCategoriesPanel").classList.remove("hidden");
  document.getElementById("adminCourseForm").classList.add("hidden");
  document.getElementById("adminParagraphsPanel").classList.add("hidden");
  document.getElementById("adminLessonsPanel").classList.add("hidden");
  document.getElementById("adminPricingTiersPanel").classList.add("hidden");
  resetCourseCategoryForm();
  await renderAdminCourseCategories();
}

function resetCourseCategoryForm() {
  document.getElementById("cc_id").value = "";
  document.getElementById("cc_title").value = "";
  document.getElementById("cc_subtitle").value = "";
  document.getElementById("cc_icon").value = "📁";
  document.getElementById("cc_order_num").value = 0;
  document.getElementById("cc_is_active").value = "1";
}

async function renderAdminCourseCategories() {
  const res = await apiFetch(`/api/admin/course-categories`);
  const data = await res.json();
  currentAdminCourseCategories = data.categories;
  const box = document.getElementById("adminCourseCategoriesList");
  box.innerHTML = "";
  if (data.categories.length === 0) box.innerHTML = emptyHtml("Hali guruh qo'shilmagan");
  data.categories.forEach(cat => {
    const row = document.createElement("div");
    row.className = "admin-row";
    row.innerHTML = `
      <div class="emoji">${cat.icon || "📁"}</div>
      <div class="info">
        <div class="t">${cat.title}${cat.is_active ? "" : " (yashirin)"}</div>
        <div class="s">${cat.subtitle || ""}</div>
      </div>
      <div class="row-actions">
        <button data-a="edit">Tahrirlash</button>
        <button data-a="delete" class="danger">O'chirish</button>
      </div>
    `;
    row.querySelector('[data-a="edit"]').onclick = () => {
      document.getElementById("cc_id").value = cat.id;
      document.getElementById("cc_title").value = cat.title;
      document.getElementById("cc_subtitle").value = cat.subtitle || "";
      document.getElementById("cc_icon").value = cat.icon || "📁";
      document.getElementById("cc_order_num").value = cat.order_num;
      document.getElementById("cc_is_active").value = String(cat.is_active);
    };
    row.querySelector('[data-a="delete"]').onclick = async () => {
      if (!confirm(`"${cat.title}" guruhini o'chirmoqchimisiz? Unga bog'langan kurslardan ham bu guruh olib tashlanadi (kurslarning o'zi o'chmaydi).`)) return;
      await apiFetch(`/api/admin/course-categories/${cat.id}`, { method: "DELETE" });
      renderAdminCourseCategories();
    };
    box.appendChild(row);
  });
}

// ---------- Bo'limlar (paragraflar) ----------

let adminActiveCourseId = null;

async function openAdminParagraphs(courseId, title) {
  adminActiveCourseId = courseId;
  document.getElementById("adminParagraphsPanel").classList.remove("hidden");
  document.getElementById("adminCourseForm").classList.add("hidden");
  document.getElementById("adminLessonsPanel").classList.add("hidden");
  document.getElementById("adminPricingTiersPanel").classList.add("hidden");
  document.getElementById("adminParagraphsTitle").textContent = `Bo'limlar — ${title}`;
  document.getElementById("ap_course_id").value = courseId;
  document.getElementById("ap_id").value = "";
  document.getElementById("ap_title").value = "";
  document.getElementById("ap_order_num").value = 0;
  document.getElementById("ap_topic_count").value = 0;
  await renderAdminParagraphs(courseId);
}

async function renderAdminParagraphs(courseId) {
  const res = await apiFetch(`/api/admin/courses/${courseId}/paragraphs`);
  const data = await res.json();
  const box = document.getElementById("adminParagraphsList");
  box.innerHTML = "";
  if (data.paragraphs.length === 0) box.innerHTML = emptyHtml("Hali bo'lim qo'shilmagan");
  data.paragraphs.forEach((p, idx) => {
    const row = document.createElement("div");
    row.className = "admin-row";
    row.innerHTML = `
      <div class="info"><div class="t">${idx + 1}. ${p.title}</div><div class="s">${p.lessons_count} ta video${p.topic_count ? ` · ${p.topic_count} ta mavzu` : ""}</div></div>
      <div class="row-actions">
        <button data-a="lessons">Videolar</button>
        <button data-a="edit">Tahrirlash</button>
        <button data-a="delete" class="danger">O'chirish</button>
      </div>
    `;
    row.querySelector('[data-a="lessons"]').onclick = () => openAdminLessons(p.id, p.title);
    row.querySelector('[data-a="edit"]').onclick = () => {
      document.getElementById("ap_id").value = p.id;
      document.getElementById("ap_title").value = p.title;
      document.getElementById("ap_order_num").value = p.order_num;
      document.getElementById("ap_topic_count").value = p.topic_count || 0;
    };
    row.querySelector('[data-a="delete"]').onclick = async () => {
      if (!confirm("Bu bo'limni o'chirmoqchimisiz? Ichidagi videolar ham o'chadi.")) return;
      await apiFetch(`/api/admin/paragraphs/${p.id}`, { method: "DELETE" });
      renderAdminParagraphs(courseId);
      loadAdminCourses();
    };
    box.appendChild(row);
  });
}

// ---------- Darslar ----------

async function openAdminLessons(paragraphId, title) {
  document.getElementById("adminLessonsPanel").classList.remove("hidden");
  document.getElementById("adminLessonsTitle").textContent = `Videolar — ${title}`;
  document.getElementById("al_paragraph_id").value = paragraphId;
  document.getElementById("al_id").value = "";
  document.getElementById("al_title").value = "";
  document.getElementById("al_video_url").value = "";
  document.getElementById("al_description").value = "";
  document.getElementById("al_order_num").value = 0;
  document.getElementById("al_is_free_preview").checked = false;
  await renderAdminLessons(paragraphId);
}

async function renderAdminLessons(paragraphId) {
  const res = await apiFetch(`/api/admin/paragraphs/${paragraphId}/lessons`);
  const data = await res.json();
  const box = document.getElementById("adminLessonsList");
  box.innerHTML = "";
  if (data.lessons.length === 0) box.innerHTML = emptyHtml("Hali video qo'shilmagan");
  data.lessons.forEach((l, idx) => {
    const row = document.createElement("div");
    row.className = "admin-row";
    const previewBadge = l.is_free_preview ? `<span class="unlock-badge" style="display:inline-block;margin-left:6px;">🔓 BEPUL NAMUNA</span>` : "";
    row.innerHTML = `
      <div class="info"><div class="t">${idx + 1}. ${l.title}${previewBadge}</div></div>
      <div class="row-actions">
        <button data-a="edit">Tahrirlash / Almashtirish</button>
        <button data-a="delete" class="danger">O'chirish</button>
      </div>
    `;
    row.querySelector('[data-a="edit"]').onclick = () => {
      document.getElementById("al_id").value = l.id;
      document.getElementById("al_title").value = l.title;
      document.getElementById("al_video_url").value = l.video_url || "";
      document.getElementById("al_description").value = l.description || "";
      document.getElementById("al_order_num").value = l.order_num;
      document.getElementById("al_is_free_preview").checked = Boolean(l.is_free_preview);
    };
    row.querySelector('[data-a="delete"]').onclick = async () => {
      if (!confirm("Bu videoni o'chirmoqchimisiz?")) return;
      await apiFetch(`/api/admin/lessons/${l.id}`, { method: "DELETE" });
      renderAdminLessons(paragraphId);
      loadAdminCourses();
    };
    box.appendChild(row);
  });
}

// ---------- Testlar ----------

export async function loadAdminTests() {
  document.getElementById("adminTestForm").classList.add("hidden");
  document.getElementById("adminQuestionsPanel").classList.add("hidden");
  document.getElementById("adminControlAccessPanel").classList.add("hidden");
  document.getElementById("adminControlResultsPanel").classList.add("hidden");
  document.getElementById("adminTestSubjectCardsPanel").classList.add("hidden");
  document.getElementById("adminTestStagesPanel").classList.add("hidden");
  document.getElementById("adminTestGroupsPanel").classList.add("hidden");
  document.getElementById("adminCertReviewPanel").classList.add("hidden");
  const box = document.getElementById("adminTestsList");
  box.innerHTML = skeletonCards(2);
  try {
    // Kurslarni ham shu yerda yuklaymiz — nazorat testi qaysi guruhlarga
    // bog'langanini ko'rsatish va formadagi katakchalarni chizish uchun
    // kerak. Aks holda bu ro'yxat kurslar moduli yuklanish tartibiga
    // bog'liq bo'lib qolardi.
    const [testsRes, cardsRes, stagesRes, groupsRes, coursesRes] = await Promise.all([
      apiFetch(`/api/admin/tests`),
      apiFetch(`/api/admin/test-subject-cards`),
      apiFetch(`/api/admin/test-stages`),
      apiFetch(`/api/admin/test-groups`),
      apiFetch(`/api/admin/courses`)
    ]);
    const data = await testsRes.json();
    currentAdminTests = data.tests;
    currentTestSubjectCards = (await cardsRes.json()).cards;
    currentTestStages = (await stagesRes.json()).stages;
    currentTestGroups = (await groupsRes.json()).groups;
    try {
      const coursesData = await coursesRes.json();
      if (coursesData && Array.isArray(coursesData.courses)) currentAdminCourses = coursesData.courses;
    } catch (e) { /* kurslar yuklanmasa ham testlar ro'yxati ko'rinaversin */ }
    const groupById = Object.fromEntries(currentTestGroups.map(g => [g.id, g]));
    box.innerHTML = "";
    if (currentAdminTests.length === 0) box.innerHTML = emptyHtml("Hali test qo'shilmagan");
    currentAdminTests.forEach(t => {
      const row = document.createElement("div");
      row.className = "admin-row";
      const controlBadge = t.is_control_test ? `<span class="control-badge">🎓 NAZORAT</span>` : "";
      const attestationBadge = t.test_kind === "attestation" ? `<span class="control-badge">📋 ATTESTATSIYA</span>` : "";
      const group = t.test_group_id ? groupById[t.test_group_id] : null;
      const groupBadge = group ? `<span class="control-badge">${group.icon || "📂"} ${group.subject_title} · ${group.stage_title} · ${group.title}</span>` : "";
      const accessBtn = t.is_control_test ? `<button data-a="access">👥 Talabalar</button>` : "";
      const resultsBtn = t.is_control_test ? `<button data-a="results">📊 Natijalar</button>` : "";
      // Nazorat testi qaysi guruhlarga bog'langani — bir qarashda ko'rinib tursin.
      const linkedIds = Array.isArray(t.course_ids) ? t.course_ids : (t.course_id ? [t.course_id] : []);
      const linkedTitles = linkedIds
        .map(cid => (currentAdminCourses.find(c => Number(c.id) === Number(cid)) || {}).title)
        .filter(Boolean);
      const autoBadge = (t.is_control_test && linkedTitles.length)
        ? `<span class="auto-access-badge">⚡ Avtomatik: ${linkedTitles.join(", ")}</span>`
        : (t.is_control_test ? `<span class="auto-access-badge">Faqat qo'lda tayinlash</span>` : "");
      row.innerHTML = `
        <div class="info">
          <div class="t">${t.title}${t.is_active ? "" : " (yashirin)"}${controlBadge}${attestationBadge}${groupBadge}</div>
          <div class="s">${t.subject} · ${DIFFICULTY_LABELS[t.difficulty] || t.difficulty} · ${t.question_count} savol · ${formatSeconds(t.time_limit_seconds)}</div>
          ${autoBadge ? `<div class="s">${autoBadge}</div>` : ""}
        </div>
        <div class="row-actions">
          <button data-a="questions">Savollar</button>
          ${accessBtn}
          ${resultsBtn}
          <button data-a="edit">Tahrirlash</button>
          <button data-a="delete" class="danger">O'chirish</button>
        </div>
      `;
      row.querySelector('[data-a="questions"]').onclick = () => openAdminQuestions(t.id, t.title);
      if (t.is_control_test) {
        row.querySelector('[data-a="access"]').onclick = () => openAdminControlAccess(t.id, t.title);
        row.querySelector('[data-a="results"]').onclick = () => openAdminControlResults(t.id, t.title);
      }
      row.querySelector('[data-a="edit"]').onclick = () => openAdminTestForm(t);
      row.querySelector('[data-a="delete"]').onclick = () => deleteAdminTest(t.id);
      box.appendChild(row);
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

// Nazorat testini KO'P kurs/guruhga bog'lash uchun katakchalar ro'yxati.
// selectedIds — oldindan belgilanadigan kurs ID lari.
function populateControlCourseCheckboxes(selectedIds) {
  const box = document.getElementById("atCourseCheckboxList");
  const selected = new Set((selectedIds || []).map(Number));
  box.innerHTML = "";

  if (!currentAdminCourses.length) {
    box.innerHTML = emptyHtml("Hozircha kurs yo'q — avval 'Kurslar' bo'limidan kurs qo'shing");
    return;
  }

  // Fan bo'yicha guruhlab ko'rsatamiz — kurslar ko'payganda topish oson bo'lsin.
  const bySubject = {};
  currentAdminCourses.forEach(c => {
    const key = c.subject || "Boshqa";
    (bySubject[key] = bySubject[key] || []).push(c);
  });

  Object.keys(bySubject).sort().forEach(subject => {
    const head = document.createElement("div");
    head.className = "course-checkbox-group-title";
    head.textContent = subject;
    box.appendChild(head);

    bySubject[subject].forEach(c => {
      const label = document.createElement("label");
      label.className = "course-checkbox-item";
      const priceTag = c.is_free ? "bepul" : (c.price > 0 ? `${c.price.toLocaleString("uz-UZ")} so'm` : "—");
      label.innerHTML = `
        <input type="checkbox" class="at-course-cb" value="${c.id}" ${selected.has(Number(c.id)) ? "checked" : ""}>
        <span><b>${c.title}</b> <span class="course-checkbox-meta">${priceTag}</span></span>
      `;
      box.appendChild(label);
    });
  });
}

function getSelectedControlCourseIds() {
  return Array.from(document.querySelectorAll(".at-course-cb:checked")).map(cb => parseInt(cb.value, 10));
}

function populateTestGroupSelect(selectedId) {
  // Uch bosqichli tanlov: Fan -> Bosqich -> Turkum. HTML <optgroup> ichma-ich
  // bo'lolmagani uchun har bir optgroup nomini "Fan — Bosqich" qilib
  // birlashtiramiz, ostidagi variantlar esa shu bosqichdagi turkumlar.
  const select = document.getElementById("at_test_group_id");
  select.innerHTML = `<option value="">— Turkumga bog'lamaslik —</option>`;
  const cardById = Object.fromEntries(currentTestSubjectCards.map(c => [c.id, c]));
  currentTestStages.forEach(stage => {
    const groups = currentTestGroups.filter(g => g.stage_id === stage.id);
    if (groups.length === 0) return;
    const card = cardById[stage.subject_card_id];
    const optgroup = document.createElement("optgroup");
    optgroup.label = `${card ? (card.icon || "📘") + " " + card.title : "Fan"} — ${stage.icon || "📶"} ${stage.title}`;
    groups.forEach(g => {
      const opt = document.createElement("option");
      opt.value = g.id;
      opt.textContent = g.title;
      optgroup.appendChild(opt);
    });
    select.appendChild(optgroup);
  });
  select.value = selectedId ? String(selectedId) : "";
}

function updatePracticeGroupVisibility() {
  const testKind = document.getElementById("at_test_kind").value;
  const isControl = document.getElementById("at_is_control_test").checked;
  document.getElementById("atPracticeGroupWrap").classList.toggle("hidden", testKind !== "practice" || isControl);
}

function openAdminTestForm(test) {
  document.getElementById("adminTestForm").classList.remove("hidden");
  document.getElementById("adminQuestionsPanel").classList.add("hidden");
  document.getElementById("adminControlAccessPanel").classList.add("hidden");
  document.getElementById("adminControlResultsPanel").classList.add("hidden");
  document.getElementById("adminTestSubjectCardsPanel").classList.add("hidden");
  document.getElementById("adminTestStagesPanel").classList.add("hidden");
  document.getElementById("adminTestGroupsPanel").classList.add("hidden");
  document.getElementById("adminTestFormTitle").textContent = test ? "Testni tahrirlash" : "Yangi test";
  document.getElementById("at_id").value = test ? test.id : "";
  document.getElementById("at_subject").value = test ? test.subject : "";
  document.getElementById("at_title").value = test ? test.title : "";
  document.getElementById("at_difficulty").value = test ? test.difficulty : "orta";
  if (test && test.time_limit_seconds) {
    const { hours, minutes } = secondsToHoursMinutes(test.time_limit_seconds);
    document.getElementById("at_time_limit_hours").value = hours || "";
    document.getElementById("at_time_limit_minutes").value = minutes || "";
  } else {
    document.getElementById("at_time_limit_hours").value = "";
    document.getElementById("at_time_limit_minutes").value = "";
  }
  document.getElementById("at_order_num").value = test ? test.order_num : 0;
  document.getElementById("at_is_active").value = test ? String(test.is_active) : "1";
  document.getElementById("at_test_kind").value = (test && test.test_kind) ? test.test_kind : "practice";

  // Bog'langan kurslar: yangi ko'p-kursli ro'yxat (course_ids). Eski, bitta
  // kursli yozuvlar uchun (course_id) — orqaga moslik saqlanadi.
  let linkedCourseIds = [];
  if (test) {
    if (Array.isArray(test.course_ids) && test.course_ids.length) linkedCourseIds = test.course_ids;
    else if (test.course_id) linkedCourseIds = [test.course_id];
  }
  populateControlCourseCheckboxes(linkedCourseIds);
  populateTestGroupSelect(test ? test.test_group_id : null);
  const isControl = test ? Boolean(test.is_control_test) : false;
  document.getElementById("at_is_control_test").checked = isControl;
  document.getElementById("atControlCourseWrap").classList.toggle("hidden", !isControl);
  updatePracticeGroupVisibility();
}

async function deleteAdminTest(id) {
  if (!confirm("Bu testni butunlay o'chirmoqchimisiz? Barcha savollar ham o'chadi.")) return;
  await apiFetch(`/api/admin/tests/${id}`, { method: "DELETE" });
  loadAdminTests();
}

// ---------- Mavzuli test: Fan kartalari ----------

async function openAdminTestSubjectCards() {
  document.getElementById("adminTestSubjectCardsPanel").classList.remove("hidden");
  document.getElementById("adminTestStagesPanel").classList.add("hidden");
  document.getElementById("adminTestGroupsPanel").classList.add("hidden");
  document.getElementById("adminTestForm").classList.add("hidden");
  resetTestSubjectCardForm();
  await renderAdminTestSubjectCards();
}

function resetTestSubjectCardForm() {
  document.getElementById("tsc_id").value = "";
  document.getElementById("tsc_title").value = "";
  document.getElementById("tsc_icon").value = "📘";
  document.getElementById("tsc_color_key").value = "teal";
  document.getElementById("tsc_order_num").value = 0;
  document.getElementById("tsc_is_active").value = "1";
}

async function renderAdminTestSubjectCards() {
  const res = await apiFetch(`/api/admin/test-subject-cards`);
  const data = await res.json();
  currentTestSubjectCards = data.cards;
  const box = document.getElementById("adminTestSubjectCardsList");
  box.innerHTML = "";
  if (data.cards.length === 0) box.innerHTML = emptyHtml("Hali fan qo'shilmagan");
  data.cards.forEach(card => {
    const row = document.createElement("div");
    row.className = "admin-row";
    row.innerHTML = `
      <div class="emoji">${card.icon || "📘"}</div>
      <div class="info">
        <div class="t">${card.title}${card.is_active ? "" : " (yashirin)"}</div>
        <div class="s">Rang: ${card.color_key}</div>
      </div>
      <div class="row-actions">
        <button data-a="edit">Tahrirlash</button>
        <button data-a="delete" class="danger">O'chirish</button>
      </div>
    `;
    row.querySelector('[data-a="edit"]').onclick = () => {
      document.getElementById("tsc_id").value = card.id;
      document.getElementById("tsc_title").value = card.title;
      document.getElementById("tsc_icon").value = card.icon || "📘";
      document.getElementById("tsc_color_key").value = card.color_key || "teal";
      document.getElementById("tsc_order_num").value = card.order_num;
      document.getElementById("tsc_is_active").value = String(card.is_active);
    };
    row.querySelector('[data-a="delete"]').onclick = async () => {
      if (!confirm(`"${card.title}" fanini o'chirmoqchimisiz? Uning barcha guruhlari ham o'chadi.`)) return;
      await apiFetch(`/api/admin/test-subject-cards/${card.id}`, { method: "DELETE" });
      renderAdminTestSubjectCards();
    };
    box.appendChild(row);
  });
}

// ---------- Mavzuli test: Bosqichlar ----------

async function openAdminTestStages() {
  document.getElementById("adminTestStagesPanel").classList.remove("hidden");
  document.getElementById("adminTestSubjectCardsPanel").classList.add("hidden");
  document.getElementById("adminTestGroupsPanel").classList.add("hidden");
  document.getElementById("adminTestForm").classList.add("hidden");
  resetTestStageForm();
  populateSubjectCardSelectForStageForm();
  await renderAdminTestStages();
}

function populateSubjectCardSelectForStageForm() {
  const select = document.getElementById("ts_subject_card_id");
  select.innerHTML = "";
  currentTestSubjectCards.forEach(card => {
    const opt = document.createElement("option");
    opt.value = card.id;
    opt.textContent = `${card.icon || "📘"} ${card.title}`;
    select.appendChild(opt);
  });
}

function resetTestStageForm() {
  document.getElementById("ts_id").value = "";
  document.getElementById("ts_title").value = "";
  document.getElementById("ts_subtitle").value = "";
  document.getElementById("ts_icon").value = "📶";
  document.getElementById("ts_order_num").value = 0;
  document.getElementById("ts_is_active").value = "1";
}

async function renderAdminTestStages() {
  const res = await apiFetch(`/api/admin/test-stages`);
  const data = await res.json();
  currentTestStages = data.stages;
  const box = document.getElementById("adminTestStagesList");
  box.innerHTML = "";
  if (data.stages.length === 0) box.innerHTML = emptyHtml("Hali bosqich qo'shilmagan");
  data.stages.forEach(s => {
    const row = document.createElement("div");
    row.className = "admin-row";
    row.innerHTML = `
      <div class="emoji">${s.icon || "📶"}</div>
      <div class="info">
        <div class="t">${s.title}${s.is_active ? "" : " (yashirin)"}</div>
        <div class="s">${s.subject_title} · tartib: ${s.order_num}${s.subtitle ? " · " + s.subtitle : ""}</div>
      </div>
      <div class="row-actions">
        <button data-a="edit">Tahrirlash</button>
        <button data-a="delete" class="danger">O'chirish</button>
      </div>
    `;
    row.querySelector('[data-a="edit"]').onclick = () => {
      document.getElementById("ts_id").value = s.id;
      document.getElementById("ts_subject_card_id").value = String(s.subject_card_id);
      document.getElementById("ts_title").value = s.title;
      document.getElementById("ts_subtitle").value = s.subtitle || "";
      document.getElementById("ts_icon").value = s.icon || "📶";
      document.getElementById("ts_order_num").value = s.order_num;
      document.getElementById("ts_is_active").value = String(s.is_active);
    };
    row.querySelector('[data-a="delete"]').onclick = async () => {
      if (!confirm(`"${s.title}" bosqichini o'chirmoqchimisiz? Ichidagi barcha turkumlar ham o'chadi.`)) return;
      await apiFetch(`/api/admin/test-stages/${s.id}`, { method: "DELETE" });
      renderAdminTestStages();
    };
    box.appendChild(row);
  });
}

// ---------- Mavzuli test: Turkumlar (guruhlar) ----------

async function openAdminTestGroups() {
  document.getElementById("adminTestGroupsPanel").classList.remove("hidden");
  document.getElementById("adminTestSubjectCardsPanel").classList.add("hidden");
  document.getElementById("adminTestStagesPanel").classList.add("hidden");
  document.getElementById("adminTestForm").classList.add("hidden");
  resetTestGroupForm();
  await populateStageSelectForGroupForm();
  await renderAdminTestGroups();
}

async function populateStageSelectForGroupForm() {
  // Bosqichlar ro'yxati hali yuklanmagan bo'lishi mumkin (masalan admin
  // to'g'ridan-to'g'ri "🗂 Turkumlar" tugmasini bossa) — shu holatda yangilab olamiz.
  if (currentTestStages.length === 0) {
    const res = await apiFetch(`/api/admin/test-stages`);
    currentTestStages = (await res.json()).stages;
  }
  const select = document.getElementById("tg_stage_id");
  select.innerHTML = "";
  const cardById = Object.fromEntries(currentTestSubjectCards.map(c => [c.id, c]));
  if (currentTestStages.length === 0) {
    select.innerHTML = `<option value="">— Avval "📶 Bosqichlar" bo'limida bosqich yarating —</option>`;
    return;
  }
  currentTestStages.forEach(stage => {
    const card = cardById[stage.subject_card_id];
    const opt = document.createElement("option");
    opt.value = stage.id;
    opt.textContent = `${card ? card.title : "Fan"} — ${stage.icon || "📶"} ${stage.title}`;
    select.appendChild(opt);
  });
}

function resetTestGroupForm() {
  document.getElementById("tg_id").value = "";
  document.getElementById("tg_title").value = "";
  document.getElementById("tg_subtitle").value = "";
  document.getElementById("tg_icon").value = "📂";
  document.getElementById("tg_order_num").value = 0;
  document.getElementById("tg_is_active").value = "1";
}

async function renderAdminTestGroups() {
  const res = await apiFetch(`/api/admin/test-groups`);
  const data = await res.json();
  currentTestGroups = data.groups;
  const box = document.getElementById("adminTestGroupsList");
  box.innerHTML = "";
  if (data.groups.length === 0) box.innerHTML = emptyHtml("Hali turkum qo'shilmagan");
  data.groups.forEach(g => {
    const row = document.createElement("div");
    row.className = "admin-row";
    row.innerHTML = `
      <div class="emoji">${g.icon || "📂"}</div>
      <div class="info">
        <div class="t">${g.title}${g.is_active ? "" : " (yashirin)"}</div>
        <div class="s">${g.subject_title} · ${g.stage_title} · tartib: ${g.order_num}${g.subtitle ? " · " + g.subtitle : ""}</div>
      </div>
      <div class="row-actions">
        <button data-a="edit">Tahrirlash</button>
        <button data-a="delete" class="danger">O'chirish</button>
      </div>
    `;
    row.querySelector('[data-a="edit"]').onclick = async () => {
      await populateStageSelectForGroupForm();
      document.getElementById("tg_id").value = g.id;
      document.getElementById("tg_stage_id").value = String(g.stage_id);
      document.getElementById("tg_title").value = g.title;
      document.getElementById("tg_subtitle").value = g.subtitle || "";
      document.getElementById("tg_icon").value = g.icon || "📂";
      document.getElementById("tg_order_num").value = g.order_num;
      document.getElementById("tg_is_active").value = String(g.is_active);
    };
    row.querySelector('[data-a="delete"]').onclick = async () => {
      if (!confirm(`"${g.title}" turkumini o'chirmoqchimisiz?`)) return;
      await apiFetch(`/api/admin/test-groups/${g.id}`, { method: "DELETE" });
      renderAdminTestGroups();
    };
    box.appendChild(row);
  });
}

// ---------- Attestatsiya: E'tirozlar ----------

export async function loadAdminObjections() {
  const box = document.getElementById("adminObjectionsList");
  if (!box) return;
  box.innerHTML = skeletonCards(2);
  try {
    const qs = objectionsStatusFilter ? `?status=${objectionsStatusFilter}` : "";
    const res = await apiFetch(`/api/admin/objections${qs}`);
    const data = await res.json();
    const objections = data.objections;
    box.innerHTML = "";
    if (objections.length === 0) {
      box.innerHTML = emptyHtml("Bu bo'limda e'tiroz yo'q");
      return;
    }
    objections.forEach(o => {
      const row = document.createElement("div");
      row.className = "admin-row";
      const studentName = o.first_name || (o.username ? "@" + o.username : `ID ${o.telegram_id}`);
      const statusBadge = o.status === "pending"
        ? `<span class="control-badge">⏳ KUTILMOQDA</span>`
        : `<span class="unlock-badge" style="display:inline-block;">✅ Ko'rib chiqilgan</span>`;
      row.innerHTML = `
        <div class="info">
          <div class="t">${o.test_title || "Test"} — ${studentName} ${statusBadge}</div>
          <div class="s">Savol: ${(o.question_text || "").slice(0, 90)}${(o.question_text || "").length > 90 ? "..." : ""}</div>
          <div class="s" style="margin-top:4px;color:var(--text);">💬 ${o.comment}</div>
        </div>
        <div class="row-actions">
          ${o.status === "pending" ? `<button data-a="review">✅ Ko'rib chiqildi deb belgilash</button>` : ""}
        </div>
      `;
      const reviewBtn = row.querySelector('[data-a="review"]');
      if (reviewBtn) {
        reviewBtn.onclick = async () => {
          await apiFetch(`/api/admin/objections/${o.id}`, { method: "PUT", body: JSON.stringify({ status: "reviewed" }) });
          loadAdminObjections();
        };
      }
      box.appendChild(row);
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

// ---------- Savollar ----------

async function openAdminQuestions(testId, title) {
  document.getElementById("adminQuestionsPanel").classList.remove("hidden");
  document.getElementById("adminTestForm").classList.add("hidden");
  document.getElementById("adminControlAccessPanel").classList.add("hidden");
  document.getElementById("adminControlResultsPanel").classList.add("hidden");
  document.getElementById("adminCertReviewPanel").classList.add("hidden");
  document.getElementById("adminQuestionsTitle").textContent = `Savollar — ${title}`;
  document.getElementById("aq_test_id").value = testId;
  document.getElementById("aq_docx_file").value = "";
  document.getElementById("docxImportStatus").textContent = "";
  document.getElementById("docxImportResult").innerHTML = "";
  resetQuestionForm();
  await renderAdminQuestions(testId);
}

async function importQuestionsFromDocx(testId, file) {
  const status = document.getElementById("docxImportStatus");
  const resultBox = document.getElementById("docxImportResult");
  resultBox.innerHTML = "";
  status.textContent = "⏳ Fayl o'qilmoqda va savollar qo'shilmoqda...";
  try {
    const formData = new FormData();
    formData.append("file", file);
    const res = await apiFetch(`/api/admin/tests/${testId}/import-docx`, { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Yuklab bo'lmadi");

    status.textContent = "";
    let html = `<div class="watched-confirmed" style="margin-bottom:8px;">✅ ${data.imported} ta savol muvaffaqiyatli qo'shildi (jami ${data.total_found} ta topildi)</div>`;
    if (data.skipped && data.skipped.length > 0) {
      html += `<div class="grace-banner" style="margin:0 0 8px;">⚠️ ${data.skipped.length} ta savol o'tkazib yuborildi:</div>`;
      data.skipped.forEach(s => {
        html += `<div class="admin-row" style="margin-bottom:6px;"><div class="info"><div class="t">${s.order_num}. ${s.text}</div><div class="s">${s.reason}</div></div></div>`;
      });
    }
    resultBox.innerHTML = html;
    document.getElementById("aq_docx_file").value = "";
    renderAdminQuestions(testId);
    loadAdminTests();
  } catch (e) {
    console.error(e);
    status.textContent = `❌ ${e.message || "Xatolik yuz berdi"}`;
    document.getElementById("aq_docx_file").value = "";
  }
}

// ---------- Nazorat testi: talabalarni tayinlash ----------

let acaSearchDebounce = null;

async function openAdminControlAccess(testId, title) {
  document.getElementById("adminControlAccessPanel").classList.remove("hidden");
  document.getElementById("adminTestForm").classList.add("hidden");
  document.getElementById("adminQuestionsPanel").classList.add("hidden");
  document.getElementById("adminControlResultsPanel").classList.add("hidden");
  document.getElementById("adminControlAccessTitle").textContent = `Talabalarni tayinlash — ${title}`;
  document.getElementById("aca_test_id").value = testId;
  document.getElementById("aca_search_input").value = "";
  await Promise.all([
    renderAssignedStudents(testId),
    searchAndRenderStudents(testId, "")
  ]);
}

async function renderAssignedStudents(testId) {
  const box = document.getElementById("acaAssignedList");
  box.innerHTML = skeletonCards(1);
  try {
    const res = await apiFetch(`/api/admin/control-tests/${testId}/access`);
    const data = await res.json();
    box.innerHTML = "";
    if (data.access.length === 0) {
      box.innerHTML = emptyHtml("Hali hech kim tayinlanmagan — qidiruv orqali talaba qo'shing");
      return;
    }
    data.access.forEach(u => {
      const row = document.createElement("div");
      row.className = "admin-row";
      row.innerHTML = `
        <div class="info">
          <div class="t">${u.first_name || "Foydalanuvchi"}${u.username ? " · @" + u.username : ""}</div>
          <div class="s">Telegram ID: ${u.telegram_id}</div>
        </div>
        <div class="row-actions">
          <button data-a="remove" class="danger">O'chirish</button>
        </div>
      `;
      row.querySelector('[data-a="remove"]').onclick = async () => {
        await apiFetch(`/api/admin/control-tests/${testId}/access/${u.telegram_id}`, { method: "DELETE" });
        renderAssignedStudents(testId);
      };
      box.appendChild(row);
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

async function searchAndRenderStudents(testId, query) {
  const box = document.getElementById("acaSearchResults");
  box.innerHTML = skeletonCards(1);
  try {
    const res = await apiFetch(`/api/admin/users/search?q=${encodeURIComponent(query)}`);
    const data = await res.json();
    box.innerHTML = "";
    if (data.users.length === 0) {
      box.innerHTML = emptyHtml("Foydalanuvchi topilmadi");
      return;
    }
    data.users.forEach(u => {
      const row = document.createElement("div");
      row.className = "admin-row";
      row.innerHTML = `
        <div class="info">
          <div class="t">${u.first_name || "Foydalanuvchi"}${u.username ? " · @" + u.username : ""}</div>
          <div class="s">Telegram ID: ${u.telegram_id}</div>
        </div>
        <div class="row-actions">
          <button data-a="add">+ Tayinlash</button>
        </div>
      `;
      row.querySelector('[data-a="add"]').onclick = async () => {
        await apiFetch(`/api/admin/control-tests/${testId}/access`, {
          method: "POST",
          body: JSON.stringify({ telegram_id: u.telegram_id, first_name: u.first_name, username: u.username })
        });
        renderAssignedStudents(testId);
      };
      box.appendChild(row);
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

// Milliy sertifikat: Y1 uchun Matematika spetsifikatsiyasidagi rasmiy
// formula (past=1, o'rta=2.2, yuqori=3 ball) DEFAULT sifatida qo'llanadi —
// Kimyo/Biologiya hujjatlarida bu aniq ko'rsatilmagan, admin xohlasa qo'lda
// o'zgartiradi.
const CERT_DEFAULT_POINTS = { past: 1, orta: 2.2, yuqori: 3 };

function updateQuestionTypeVisibility() {
  const qtype = document.getElementById("aq_question_type").value;
  document.getElementById("aqY1Fields").classList.toggle("hidden", qtype !== "Y1");
  document.getElementById("aqY2Fields").classList.toggle("hidden", qtype !== "Y2");
  document.getElementById("aqO1Fields").classList.toggle("hidden", qtype !== "O1");
  document.getElementById("aqO2Fields").classList.toggle("hidden", qtype !== "O2");
  document.getElementById("aqPointFields").classList.toggle("hidden", qtype === "O2");
  // Y1/Y2/O1 required qoidalari — Y1 bo'lmasa variant maydonlari majburiy emas
  document.getElementById("aq_option_1").required = qtype === "Y1";
  document.getElementById("aq_option_2").required = qtype === "Y1";
  document.getElementById("aq_option_3").required = qtype === "Y1";
  document.getElementById("aq_option_4").required = qtype === "Y1";
}

function suggestPointValue() {
  const qtype = document.getElementById("aq_question_type").value;
  if (qtype === "Y2") {
    document.getElementById("aq_point_value").value = 2.2;
    return;
  }
  const diff = document.getElementById("aq_difficulty_level").value;
  document.getElementById("aq_point_value").value = CERT_DEFAULT_POINTS[diff] ?? 1;
}

function resetQuestionForm() {
  document.getElementById("aq_id").value = "";
  document.getElementById("aq_question_type").value = "Y1";
  document.getElementById("aq_question_text").value = "";
  document.getElementById("aq_image_url").value = "";
  document.getElementById("aq_image_file").value = "";
  document.getElementById("aqImageUploadStatus").textContent = "";
  document.getElementById("aqImagePreviewWrap").classList.add("hidden");
  document.getElementById("aqImagePreview").src = "";
  document.getElementById("aq_option_1").value = "";
  document.getElementById("aq_option_2").value = "";
  document.getElementById("aq_option_3").value = "";
  document.getElementById("aq_option_4").value = "";
  document.getElementById("aq_correct_index").value = "1";
  document.getElementById("aq_match_left").value = "";
  document.getElementById("aq_match_right").value = "";
  document.getElementById("aq_correct_answer_text").value = "";
  document.getElementById("aq_max_score").value = 25;
  document.getElementById("aq_rubric_json").value = "";
  document.getElementById("aq_difficulty_level").value = "past";
  document.getElementById("aq_point_value").value = 1;
  document.getElementById("aq_order_num").value = 0;
  updateQuestionTypeVisibility();
}

function showQuestionImagePreview(url) {
  document.getElementById("aq_image_url").value = url || "";
  const wrap = document.getElementById("aqImagePreviewWrap");
  const img = document.getElementById("aqImagePreview");
  if (url) {
    img.src = url;
    wrap.classList.remove("hidden");
  } else {
    img.src = "";
    wrap.classList.add("hidden");
  }
}

async function uploadQuestionImage(file) {
  const status = document.getElementById("aqImageUploadStatus");
  status.textContent = "⏳ Yuklanmoqda...";
  try {
    const formData = new FormData();
    formData.append("file", file);
    const res = await apiFetch(`/api/admin/upload-image`, { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Yuklab bo'lmadi");
    }
    const data = await res.json();
    showQuestionImagePreview(data.url);
    status.textContent = "✅ Rasm yuklandi";
  } catch (e) {
    console.error(e);
    status.textContent = `❌ ${e.message || "Xatolik yuz berdi"}`;
    document.getElementById("aq_image_file").value = "";
  }
}

const QUESTION_TYPE_LABELS = {
  Y1: "Y1 · yopiq (bitta javob)", Y2: "Y2 · moslashtirish",
  O1: "O1 · qisqa ochiq javob", O2: "O2 · yozma ish"
};

async function renderAdminQuestions(testId) {
  const res = await apiFetch(`/api/admin/tests/${testId}/questions`);
  const data = await res.json();
  const box = document.getElementById("adminQuestionsList");
  box.innerHTML = "";
  if (data.questions.length === 0) box.innerHTML = emptyHtml("Hali savol qo'shilmagan");
  data.questions.forEach((q, idx) => {
    const qtype = q.question_type || "Y1";
    const typeBadge = `<span class="control-badge">${QUESTION_TYPE_LABELS[qtype] || qtype}</span>`;
    const metaText = qtype === "Y1" ? `To'g'ri javob: ${q.correct_index}-variant`
      : qtype === "O2" ? `Maksimal ball: ${q.max_score ?? 25}`
      : qtype === "Y2" ? "Moslashtirish topshirig'i"
      : `Kutilgan javob: ${q.correct_answer_text || "—"}`;
    const row = document.createElement("div");
    row.className = "admin-row";
    row.innerHTML = `
      <div class="info"><div class="t">${idx + 1}. ${q.question_text.slice(0, 60)}${q.question_text.length > 60 ? "…" : ""} ${typeBadge}</div><div class="s">${metaText}${qtype !== "O2" ? " · " + (q.point_value ?? 1) + " ball" : ""}</div></div>
      <div class="row-actions">
        <button data-a="edit">Tahrirlash</button>
        <button data-a="delete" class="danger">O'chirish</button>
      </div>
    `;
    row.querySelector('[data-a="edit"]').onclick = () => {
      document.getElementById("aq_id").value = q.id;
      document.getElementById("aq_question_type").value = qtype;
      document.getElementById("aq_question_text").value = q.question_text;
      document.getElementById("aq_image_file").value = "";
      document.getElementById("aqImageUploadStatus").textContent = "";
      showQuestionImagePreview(q.image_url || "");
      document.getElementById("aq_option_1").value = q.option_1 || "";
      document.getElementById("aq_option_2").value = q.option_2 || "";
      document.getElementById("aq_option_3").value = q.option_3 || "";
      document.getElementById("aq_option_4").value = q.option_4 || "";
      document.getElementById("aq_correct_index").value = String(q.correct_index || 1);
      let matchLeft = [], matchRight = [];
      if (qtype === "Y2" && q.match_data) {
        try {
          const md = JSON.parse(q.match_data);
          matchLeft = md.left || []; matchRight = md.right || [];
        } catch (e) { /* eskirgan/yaroqsiz JSON — bo'sh qoldiramiz */ }
      }
      document.getElementById("aq_match_left").value = matchLeft.join("\n");
      document.getElementById("aq_match_right").value = matchRight.join("\n");
      document.getElementById("aq_correct_answer_text").value = q.correct_answer_text || "";
      document.getElementById("aq_max_score").value = q.max_score ?? 25;
      document.getElementById("aq_rubric_json").value = q.rubric_json || "";
      document.getElementById("aq_difficulty_level").value = q.difficulty_level || "past";
      document.getElementById("aq_point_value").value = q.point_value ?? 1;
      document.getElementById("aq_order_num").value = q.order_num;
      updateQuestionTypeVisibility();
    };
    row.querySelector('[data-a="delete"]').onclick = async () => {
      if (!confirm("Bu savolni o'chirmoqchimisiz?")) return;
      await apiFetch(`/api/admin/questions/${q.id}`, { method: "DELETE" });
      renderAdminQuestions(testId);
      loadAdminTests();
    };
    box.appendChild(row);
  });
}

// ---------- Milliy sertifikat: yozma ish (O2) baholash navbati ----------

async function openAdminCertReview() {
  document.getElementById("adminCertReviewPanel").classList.remove("hidden");
  document.getElementById("adminTestForm").classList.add("hidden");
  document.getElementById("adminQuestionsPanel").classList.add("hidden");
  await renderAdminCertReview();
}

async function renderAdminCertReview() {
  const box = document.getElementById("adminCertReviewList");
  box.innerHTML = skeletonCards(2);
  try {
    const res = await apiFetch(`/api/admin/certificate/pending-review`);
    const data = await res.json();
    box.innerHTML = "";
    if (data.answers.length === 0) {
      box.innerHTML = emptyHtml("Hozircha baholanishi kerak bo'lgan yozma ish yo'q");
      return;
    }
    data.answers.forEach(a => {
      const name = a.first_name || (a.username ? "@" + a.username : `ID ${a.telegram_id}`);
      const photos = (() => { try { return JSON.parse(a.photo_urls || "[]"); } catch (e) { return []; } })();
      const photosHtml = photos.map(url => `<img src="${url}" alt="Javob surati" style="max-width:140px;border-radius:8px;margin:4px 6px 0 0;cursor:pointer;" data-photo="${url}">`).join("");
      const row = document.createElement("div");
      row.className = "admin-row";
      row.style.flexDirection = "column";
      row.style.alignItems = "stretch";
      row.innerHTML = `
        <div class="info">
          <div class="t">${a.test_title} · ${a.subject || ""} — ${a.question_text.slice(0, 70)}${a.question_text.length > 70 ? "…" : ""}</div>
          <div class="s">${name} · Maks ball: ${a.max_score ?? 25}${a.rubric_json ? " · Rubrika: " + a.rubric_json.slice(0, 80) : ""}</div>
        </div>
        <div style="display:flex;flex-wrap:wrap;margin:6px 0;">${photosHtml || '<span class="s">Rasm yuborilmagan</span>'}</div>
        ${a.text_answer ? `<div class="s" style="white-space:pre-wrap;margin-bottom:6px;">${a.text_answer}</div>` : ""}
        <div class="admin-form" style="margin:0;gap:8px;flex-direction:row;flex-wrap:wrap;align-items:flex-end;">
          <label style="flex:1;min-width:100px;">Ball <input type="number" step="0.1" min="0" max="${a.max_score ?? 25}" class="cert-score-input" value=""></label>
          <label style="flex:2;min-width:160px;">Izoh (ixtiyoriy) <input type="text" class="cert-comment-input"></label>
          <button type="button" class="gold-btn small cert-grade-btn">✅ Ball qo'yish</button>
        </div>
      `;
      row.querySelectorAll("[data-photo]").forEach(img => {
        img.addEventListener("click", () => window.open(img.getAttribute("data-photo"), "_blank"));
      });
      row.querySelector(".cert-grade-btn").onclick = async () => {
        const scoreInput = row.querySelector(".cert-score-input");
        const score = parseFloat(scoreInput.value);
        if (Number.isNaN(score)) {
          tg.showAlert ? tg.showAlert("Ball kiriting") : alert("Ball kiriting");
          return;
        }
        const comment = row.querySelector(".cert-comment-input").value;
        await apiFetch(`/api/admin/certificate/grade`, {
          method: "POST",
          body: JSON.stringify({ written_answer_id: a.id, teacher_score: score, teacher_comment: comment })
        });
        renderAdminCertReview();
      };
      box.appendChild(row);
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

// ---------- Modulni ishga tushirish (barcha forma va tugmalarni ulaydi) ----------

export function initAdminModule() {
  const objRow = document.getElementById("objectionsFilterRow");
  if (objRow) {
    objRow.querySelectorAll(".filter-chip").forEach(chip => {
      chip.addEventListener("click", () => {
        objectionsStatusFilter = chip.getAttribute("data-objstatus");
        objRow.querySelectorAll(".filter-chip").forEach(c => c.classList.remove("active"));
        chip.classList.add("active");
        loadAdminObjections();
      });
    });
  }

  document.getElementById("adminNewCourseBtn").addEventListener("click", () => openAdminCourseForm(null));
  document.getElementById("adminCloseCourseForm").addEventListener("click", () => document.getElementById("adminCourseForm").classList.add("hidden"));

  document.getElementById("courseFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("ac_id").value;
    const categoryIds = Array.from(document.querySelectorAll("#ac_category_checkboxes input:checked")).map(el => parseInt(el.value));
    const data = {
      title: document.getElementById("ac_title").value,
      subject: document.getElementById("ac_subject").value,
      resource_type: document.getElementById("ac_resource_type").value,
      description: document.getElementById("ac_description").value,
      is_free: intVal("ac_is_free", 0),
      required_referrals: intVal("ac_required_referrals", 0),
      price: intVal("ac_price", 0),
      duration_days: document.getElementById("ac_duration_days").value || null,
      students_count: intVal("ac_students_count", 0),
      duration_text: document.getElementById("ac_duration_text").value,
      lessons_count_override: document.getElementById("ac_lessons_override").value || null,
      thumbnail_emoji: document.getElementById("ac_thumbnail_emoji").value,
      order_num: intVal("ac_order_num", 0),
      is_active: intVal("ac_is_active", 0),
      category_ids: categoryIds
    };
    if (id) await apiFetch(`/api/admin/courses/${id}`, { method: "PUT", body: JSON.stringify(data) });
    else await apiFetch(`/api/admin/courses`, { method: "POST", body: JSON.stringify(data) });
    document.getElementById("adminCourseForm").classList.add("hidden");
    loadAdminCourses();
  });

  document.getElementById("adminManageCategoriesBtn").addEventListener("click", () => openAdminCourseCategories());
  document.getElementById("adminCloseCourseCategories").addEventListener("click", () => document.getElementById("adminCourseCategoriesPanel").classList.add("hidden"));

  document.getElementById("courseCategoryFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("cc_id").value;
    const data = {
      title: document.getElementById("cc_title").value,
      subtitle: document.getElementById("cc_subtitle").value,
      icon: document.getElementById("cc_icon").value || "📁",
      order_num: intVal("cc_order_num", 0),
      is_active: intVal("cc_is_active", 0)
    };
    if (id) await apiFetch(`/api/admin/course-categories/${id}`, { method: "PUT", body: JSON.stringify(data) });
    else await apiFetch(`/api/admin/course-categories`, { method: "POST", body: JSON.stringify(data) });
    resetCourseCategoryForm();
    renderAdminCourseCategories();
  });

  document.getElementById("adminClosePricingTiers").addEventListener("click", () => document.getElementById("adminPricingTiersPanel").classList.add("hidden"));

  document.getElementById("pricingTierFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("pt_id").value;
    const courseId = document.getElementById("pt_course_id").value;
    const originalPriceRaw = document.getElementById("pt_original_price").value;
    const data = {
      course_id: parseInt(courseId),
      label: document.getElementById("pt_label").value,
      price: intVal("pt_price", 0),
      original_price: originalPriceRaw ? parseInt(originalPriceRaw) : null,
      duration_text: document.getElementById("pt_duration_text").value,
      order_num: intVal("pt_order_num", 0),
      is_active: intVal("pt_is_active", 0)
    };
    if (id) await apiFetch(`/api/admin/pricing-tiers/${id}`, { method: "PUT", body: JSON.stringify(data) });
    else await apiFetch(`/api/admin/pricing-tiers`, { method: "POST", body: JSON.stringify(data) });
    resetPricingTierForm();
    renderAdminPricingTiers(courseId);
  });

  document.getElementById("adminCloseParagraphs").addEventListener("click", () => document.getElementById("adminParagraphsPanel").classList.add("hidden"));

  document.getElementById("paragraphFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("ap_id").value;
    const courseId = document.getElementById("ap_course_id").value;
    const data = {
      course_id: parseInt(courseId),
      title: document.getElementById("ap_title").value,
      order_num: intVal("ap_order_num", 0),
      topic_count: intVal("ap_topic_count", 0)
    };
    if (id) await apiFetch(`/api/admin/paragraphs/${id}`, { method: "PUT", body: JSON.stringify(data) });
    else await apiFetch(`/api/admin/paragraphs`, { method: "POST", body: JSON.stringify(data) });
    document.getElementById("ap_id").value = "";
    document.getElementById("ap_title").value = "";
    document.getElementById("ap_order_num").value = 0;
    document.getElementById("ap_topic_count").value = 0;
    renderAdminParagraphs(courseId);
    loadAdminCourses();
  });

  document.getElementById("adminCloseLessons").addEventListener("click", () => document.getElementById("adminLessonsPanel").classList.add("hidden"));

  document.getElementById("lessonFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("al_id").value;
    const paragraphId = document.getElementById("al_paragraph_id").value;
    const data = {
      paragraph_id: parseInt(paragraphId),
      title: document.getElementById("al_title").value,
      video_url: document.getElementById("al_video_url").value,
      description: document.getElementById("al_description").value,
      order_num: intVal("al_order_num", 0),
      is_free_preview: document.getElementById("al_is_free_preview").checked ? 1 : 0
    };
    if (id) await apiFetch(`/api/admin/lessons/${id}`, { method: "PUT", body: JSON.stringify(data) });
    else await apiFetch(`/api/admin/lessons`, { method: "POST", body: JSON.stringify(data) });
    document.getElementById("al_id").value = "";
    document.getElementById("al_title").value = "";
    document.getElementById("al_video_url").value = "";
    document.getElementById("al_description").value = "";
    document.getElementById("al_order_num").value = 0;
    document.getElementById("al_is_free_preview").checked = false;
    renderAdminLessons(paragraphId);
    loadAdminCourses();
  });

  document.getElementById("enrollFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = {
      telegram_id: intVal("en_telegram_id", 0),
      course_id: intVal("en_course_id", 0),
      duration_days: document.getElementById("en_duration_days").value || null
    };
    await apiFetch(`/api/admin/enroll`, { method: "POST", body: JSON.stringify(data) });
    tg.showAlert ? tg.showAlert("✅ Obuna berildi!") : alert("Obuna berildi!");
    document.getElementById("en_telegram_id").value = "";
    document.getElementById("en_duration_days").value = "";
  });

  document.getElementById("adminNewTestBtn").addEventListener("click", () => openAdminTestForm(null));
  document.getElementById("adminCloseTestForm").addEventListener("click", () => document.getElementById("adminTestForm").classList.add("hidden"));

  document.getElementById("adminManageTestSubjectsBtn").addEventListener("click", () => openAdminTestSubjectCards());
  document.getElementById("adminCloseTestSubjectCards").addEventListener("click", () => document.getElementById("adminTestSubjectCardsPanel").classList.add("hidden"));

  document.getElementById("testSubjectCardFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("tsc_id").value;
    const data = {
      title: document.getElementById("tsc_title").value,
      icon: document.getElementById("tsc_icon").value || "📘",
      color_key: document.getElementById("tsc_color_key").value,
      order_num: intVal("tsc_order_num", 0),
      is_active: intVal("tsc_is_active", 0)
    };
    if (id) await apiFetch(`/api/admin/test-subject-cards/${id}`, { method: "PUT", body: JSON.stringify(data) });
    else await apiFetch(`/api/admin/test-subject-cards`, { method: "POST", body: JSON.stringify(data) });
    resetTestSubjectCardForm();
    renderAdminTestSubjectCards();
  });

  document.getElementById("adminManageTestStagesBtn").addEventListener("click", () => openAdminTestStages());
  document.getElementById("adminCloseTestStages").addEventListener("click", () => document.getElementById("adminTestStagesPanel").classList.add("hidden"));

  document.getElementById("testStageFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("ts_id").value;
    const data = {
      subject_card_id: intVal("ts_subject_card_id", 0),
      title: document.getElementById("ts_title").value,
      subtitle: document.getElementById("ts_subtitle").value,
      icon: document.getElementById("ts_icon").value || "📶",
      order_num: intVal("ts_order_num", 0),
      is_active: intVal("ts_is_active", 0)
    };
    if (id) await apiFetch(`/api/admin/test-stages/${id}`, { method: "PUT", body: JSON.stringify(data) });
    else await apiFetch(`/api/admin/test-stages`, { method: "POST", body: JSON.stringify(data) });
    resetTestStageForm();
    renderAdminTestStages();
  });

  document.getElementById("adminManageTestGroupsBtn").addEventListener("click", () => openAdminTestGroups());
  document.getElementById("adminCloseTestGroups").addEventListener("click", () => document.getElementById("adminTestGroupsPanel").classList.add("hidden"));

  document.getElementById("testGroupFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("tg_id").value;
    const data = {
      stage_id: intVal("tg_stage_id", 0),
      title: document.getElementById("tg_title").value,
      subtitle: document.getElementById("tg_subtitle").value,
      icon: document.getElementById("tg_icon").value || "📂",
      order_num: intVal("tg_order_num", 0),
      is_active: intVal("tg_is_active", 0)
    };
    if (id) await apiFetch(`/api/admin/test-groups/${id}`, { method: "PUT", body: JSON.stringify(data) });
    else await apiFetch(`/api/admin/test-groups`, { method: "POST", body: JSON.stringify(data) });
    resetTestGroupForm();
    renderAdminTestGroups();
  });

  document.getElementById("at_is_control_test").addEventListener("change", (e) => {
    document.getElementById("atControlCourseWrap").classList.toggle("hidden", !e.target.checked);
    updatePracticeGroupVisibility();
  });
  document.getElementById("at_test_kind").addEventListener("change", () => updatePracticeGroupVisibility());

  document.getElementById("testFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("at_id").value;
    const difficulty = document.getElementById("at_difficulty").value;
    const hoursVal = document.getElementById("at_time_limit_hours").value;
    const minutesVal = document.getElementById("at_time_limit_minutes").value;
    const rawTimeLimit = hoursMinutesToSeconds(hoursVal, minutesVal);
    const isControlTest = document.getElementById("at_is_control_test").checked;
    const rawGroupId = document.getElementById("at_test_group_id").value;
    // Nazorat testi qaysi kurs/guruhlarga bog'langani — shu guruhlarga
    // qo'shilgan o'quvchilarga test AVTOMATIK ochiladi (birma-bir qo'lda
    // qo'shish shart emas).
    const courseIds = isControlTest ? getSelectedControlCourseIds() : [];
    const data = {
      subject: document.getElementById("at_subject").value,
      title: document.getElementById("at_title").value,
      difficulty: difficulty,
      time_limit_seconds: rawTimeLimit > 0 ? rawTimeLimit : DIFFICULTY_DEFAULT_SECONDS[difficulty],
      order_num: intVal("at_order_num", 0),
      is_active: intVal("at_is_active", 0),
      is_control_test: isControlTest ? 1 : 0,
      course_ids: courseIds,
      test_kind: document.getElementById("at_test_kind").value,
      test_group_id: (!isControlTest && rawGroupId) ? parseInt(rawGroupId) : null
    };
    if (!data.subject.trim() || !data.title.trim()) {
      const msg = "Fan va Test nomi to'ldirilishi shart.";
      tg.showAlert ? tg.showAlert(msg) : alert(msg);
      return;
    }

    const saveBtn = e.target.querySelector('button[type="submit"]');
    if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = "Saqlanmoqda..."; }

    const ok = id
      ? await saveOrAlert(`/api/admin/tests/${id}`, { method: "PUT", body: JSON.stringify(data) }, "Testni yangilab bo'lmadi")
      : await saveOrAlert(`/api/admin/tests`, { method: "POST", body: JSON.stringify(data) }, "Testni saqlab bo'lmadi");

    if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = "Testni saqlash"; }

    // Xatolik bo'lsa — formani YOPMAYMIZ, admin kiritgan ma'lumotlari
    // yo'qolmasin va xato sababini ko'rib, tuzatib qayta yubora olsin.
    if (!ok) return;

    document.getElementById("adminTestForm").classList.add("hidden");
    loadAdminTests();
  });

  document.getElementById("adminCloseQuestions").addEventListener("click", () => document.getElementById("adminQuestionsPanel").classList.add("hidden"));

  document.getElementById("aq_image_file").addEventListener("change", (e) => {
    const file = e.target.files && e.target.files[0];
    if (file) uploadQuestionImage(file);
  });

  document.getElementById("aq_docx_file").addEventListener("change", (e) => {
    const file = e.target.files && e.target.files[0];
    const testId = document.getElementById("aq_test_id").value;
    if (file && testId) importQuestionsFromDocx(testId, file);
  });

  document.getElementById("aqRemoveImageBtn").addEventListener("click", () => {
    document.getElementById("aq_image_file").value = "";
    document.getElementById("aqImageUploadStatus").textContent = "";
    showQuestionImagePreview("");
  });

  document.getElementById("adminCloseControlAccess").addEventListener("click", () => document.getElementById("adminControlAccessPanel").classList.add("hidden"));
  document.getElementById("adminCloseControlResults").addEventListener("click", () => document.getElementById("adminControlResultsPanel").classList.add("hidden"));

  document.getElementById("aca_search_input").addEventListener("input", (e) => {
    const testId = document.getElementById("aca_test_id").value;
    const query = e.target.value;
    clearTimeout(acaSearchDebounce);
    acaSearchDebounce = setTimeout(() => searchAndRenderStudents(testId, query), 300);
  });

  document.getElementById("aq_question_type").addEventListener("change", () => {
    updateQuestionTypeVisibility();
    suggestPointValue();
  });
  document.getElementById("aq_difficulty_level").addEventListener("change", suggestPointValue);

  document.getElementById("questionFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("aq_id").value;
    const testId = document.getElementById("aq_test_id").value;
    const qtype = document.getElementById("aq_question_type").value;
    const data = {
      test_id: parseInt(testId),
      question_type: qtype,
      question_text: document.getElementById("aq_question_text").value,
      image_url: document.getElementById("aq_image_url").value,
      order_num: intVal("aq_order_num", 0)
    };
    if (qtype === "Y1") {
      data.option_1 = document.getElementById("aq_option_1").value;
      data.option_2 = document.getElementById("aq_option_2").value;
      data.option_3 = document.getElementById("aq_option_3").value;
      data.option_4 = document.getElementById("aq_option_4").value;
      data.correct_index = intVal("aq_correct_index", 1); // variantlar 1..4, shuning uchun zaxira qiymat 1
      data.difficulty_level = document.getElementById("aq_difficulty_level").value;
      data.point_value = parseFloat(document.getElementById("aq_point_value").value) || 1;
    } else if (qtype === "Y2") {
      const left = document.getElementById("aq_match_left").value.split("\n").map(s => s.trim()).filter(Boolean);
      const right = document.getElementById("aq_match_right").value.split("\n").map(s => s.trim()).filter(Boolean);
      if (left.length !== right.length || left.length === 0) {
        tg.showAlert ? tg.showAlert("Chap va o'ng ustunlar bir xil sondagi qatorlardan iborat bo'lishi va bo'sh bo'lmasligi kerak") : alert("Chap/o'ng ustun sonlari mos kelmayapti");
        return;
      }
      data.match_data = JSON.stringify({ left, right, correct_pairs: left.map((_, i) => [i, i]) });
      data.point_value = parseFloat(document.getElementById("aq_point_value").value) || 2.2;
    } else if (qtype === "O1") {
      data.correct_answer_text = document.getElementById("aq_correct_answer_text").value;
      data.difficulty_level = document.getElementById("aq_difficulty_level").value;
      data.point_value = parseFloat(document.getElementById("aq_point_value").value) || 1;
    } else if (qtype === "O2") {
      data.max_score = parseFloat(document.getElementById("aq_max_score").value) || 25;
      data.rubric_json = document.getElementById("aq_rubric_json").value;
    }
    if (id) await apiFetch(`/api/admin/questions/${id}`, { method: "PUT", body: JSON.stringify(data) });
    else await apiFetch(`/api/admin/questions`, { method: "POST", body: JSON.stringify(data) });
    resetQuestionForm();
    renderAdminQuestions(testId);
    loadAdminTests();
  });

  document.getElementById("adminManageCertReviewBtn").addEventListener("click", () => openAdminCertReview());
  document.getElementById("adminCloseCertReview").addEventListener("click", () => document.getElementById("adminCertReviewPanel").classList.add("hidden"));

  // --- Bosh sahifa kartalari ---

  document.getElementById("adminCloseDashboardCardForm").addEventListener("click", () => document.getElementById("adminDashboardCardForm").classList.add("hidden"));

  document.getElementById("dashboardCardFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const key = document.getElementById("dc_key").value;
    const data = {
      title: document.getElementById("dc_title").value,
      subtitle: document.getElementById("dc_subtitle").value,
      icon: document.getElementById("dc_icon").value,
      order_num: intVal("dc_order_num", 0),
      is_active: intVal("dc_is_active", 0)
    };
    await apiFetch(`/api/admin/dashboard-cards/${key}`, { method: "PUT", body: JSON.stringify(data) });
    document.getElementById("adminDashboardCardForm").classList.add("hidden");
    loadAdminDashboardCards();
  });

  // --- Kitoblar do'koni (bosma kitoblar) ---

  document.getElementById("adminNewBookProductBtn").addEventListener("click", () => openAdminBookProductForm(null));
  document.getElementById("adminCloseBookProductForm").addEventListener("click", () => document.getElementById("adminBookProductForm").classList.add("hidden"));

  document.getElementById("bp_image_file").addEventListener("change", (e) => {
    const file = e.target.files && e.target.files[0];
    if (file) uploadBookProductImage(file);
  });

  document.getElementById("bpRemoveImageBtn").addEventListener("click", () => {
    document.getElementById("bp_image_file").value = "";
    document.getElementById("bpImageUploadStatus").textContent = "";
    showBookProductImagePreview("");
  });

  document.getElementById("bookProductFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("bp_id").value;
    const data = {
      title: document.getElementById("bp_title").value,
      subtitle: document.getElementById("bp_subtitle").value,
      description: document.getElementById("bp_description").value,
      category: document.getElementById("bp_category").value,
      price: intVal("bp_price", 0),
      image_url: document.getElementById("bp_image_url").value,
      badge_text: document.getElementById("bp_badge_text").value,
      is_bundle: intVal("bp_is_bundle", 0),
      contact_username: document.getElementById("bp_contact_username").value,
      linked_course_id: document.getElementById("bp_linked_course_id").value ? intVal("bp_linked_course_id", 0) : null,
      order_num: intVal("bp_order_num", 0),
      is_active: intVal("bp_is_active", 0)
    };
    if (id) await apiFetch(`/api/admin/book-products/${id}`, { method: "PUT", body: JSON.stringify(data) });
    else await apiFetch(`/api/admin/book-products`, { method: "POST", body: JSON.stringify(data) });
    document.getElementById("adminBookProductForm").classList.add("hidden");
    loadAdminBookProducts();
  });

  // --- FAQ / Yordam savollari ---

  document.getElementById("adminNewFaqBtn").addEventListener("click", () => openAdminFaqForm(null));
  document.getElementById("adminCloseFaqForm").addEventListener("click", () => document.getElementById("adminFaqForm").classList.add("hidden"));

  document.getElementById("faqFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("faq_id").value;
    const data = {
      question: document.getElementById("faq_question").value,
      answer: document.getElementById("faq_answer").value,
      order_num: intVal("faq_order_num", 0),
      is_active: intVal("faq_is_active", 0)
    };
    if (id) await apiFetch(`/api/admin/faq/${id}`, { method: "PUT", body: JSON.stringify(data) });
    else await apiFetch(`/api/admin/faq`, { method: "POST", body: JSON.stringify(data) });
    document.getElementById("adminFaqForm").classList.add("hidden");
    loadAdminFaq();
  });

  // --- Natijalar (o'quvchi fikri + sertifikat natijalari) ---

  document.getElementById("adminNewStudentResultBtn").addEventListener("click", () => openAdminStudentResultForm(null));
  document.getElementById("adminCloseStudentResultForm").addEventListener("click", () => document.getElementById("adminStudentResultForm").classList.add("hidden"));

  document.getElementById("sr_image_file").addEventListener("change", (e) => {
    const file = e.target.files && e.target.files[0];
    if (file) uploadStudentResultImage(file);
  });

  document.getElementById("srRemoveImageBtn").addEventListener("click", () => {
    document.getElementById("sr_image_file").value = "";
    document.getElementById("srImageUploadStatus").textContent = "";
    showStudentResultImagePreview("");
  });

  document.getElementById("studentResultFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("sr_id").value;
    const data = {
      student_name: document.getElementById("sr_student_name").value,
      subject: document.getElementById("sr_subject").value,
      image_url: document.getElementById("sr_image_url").value,
      result_text: document.getElementById("sr_result_text").value,
      feedback_text: document.getElementById("sr_feedback_text").value,
      order_num: intVal("sr_order_num", 0),
      is_active: intVal("sr_is_active", 0)
    };
    if (id) await apiFetch(`/api/admin/student-results/${id}`, { method: "PUT", body: JSON.stringify(data) });
    else await apiFetch(`/api/admin/student-results`, { method: "POST", body: JSON.stringify(data) });
    document.getElementById("adminStudentResultForm").classList.add("hidden");
    loadAdminStudentResults();
  });

  // --- DTM Simulyatorlari ---

  document.getElementById("adminNewSimulatorBtn").addEventListener("click", () => openAdminSimulatorForm(null));
  document.getElementById("adminCloseSimulatorForm").addEventListener("click", () => document.getElementById("adminSimulatorForm").classList.add("hidden"));

  document.getElementById("simulatorFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("as_id").value;
    const asHours = document.getElementById("as_time_limit_hours").value;
    const asMinutes = document.getElementById("as_time_limit_minutes").value;
    const asSeconds = hoursMinutesToSeconds(asHours, asMinutes);
    const data = {
      title: document.getElementById("as_title").value,
      description: document.getElementById("as_description").value,
      time_limit_seconds: asSeconds > 0 ? asSeconds : 10800,
      order_num: intVal("as_order_num", 0),
      is_active: intVal("as_is_active", 0)
    };
    if (id) await apiFetch(`/api/admin/simulators/${id}`, { method: "PUT", body: JSON.stringify(data) });
    else await apiFetch(`/api/admin/simulators`, { method: "POST", body: JSON.stringify(data) });
    document.getElementById("adminSimulatorForm").classList.add("hidden");
    loadAdminSimulators();
  });

  document.getElementById("adminCloseSimSubjects").addEventListener("click", () => document.getElementById("adminSimSubjectsPanel").classList.add("hidden"));

  document.getElementById("simSubjectFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const simulatorId = intVal("ass_simulator_id", 0);
    const data = {
      simulator_id: simulatorId,
      subject: document.getElementById("ass_subject").value.trim(),
      question_count: intVal("ass_question_count", 10),
      order_num: intVal("ass_order_num", 0)
    };
    await apiFetch(`/api/admin/simulator-subjects`, { method: "POST", body: JSON.stringify(data) });
    document.getElementById("ass_subject").value = "";
    document.getElementById("ass_question_count").value = 10;
    document.getElementById("ass_order_num").value = 0;
    renderAdminSimSubjects(simulatorId);
    loadAdminSimulators();
  });
}

// ================================================================
// VAZIFA TOPSHIRISH (admin boshqaruvi)
// ================================================================

let currentHwSubjects = [];

function hideHwPanels() {
  ["adminHwSubjectForm", "adminHwReviewPanel", "adminHwLatePanel", "adminHwRankingPanel"]
    .forEach(id => document.getElementById(id).classList.add("hidden"));
}

export async function loadAdminHomeworkSubjects() {
  const box = document.getElementById("adminHwSubjectsList");
  if (!box) return;
  box.innerHTML = skeletonCards(1);
  try {
    const res = await apiFetch(`/api/admin/homework/subjects`);
    const data = await res.json();
    currentHwSubjects = data.subjects || [];
    renderAdminHomeworkSubjects();
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

function renderAdminHomeworkSubjects() {
  const box = document.getElementById("adminHwSubjectsList");
  box.innerHTML = "";
  if (!currentHwSubjects.length) {
    box.innerHTML = emptyHtml("Hali bo'lim qo'shilmagan — '+ Bo'lim' tugmasini bosing");
    return;
  }
  currentHwSubjects.forEach(s => {
    const titles = (s.course_ids || [])
      .map(cid => (currentAdminCourses.find(c => Number(c.id) === Number(cid)) || {}).title)
      .filter(Boolean);
    const groupsLine = titles.length
      ? `<span class="auto-access-badge">⚡ ${titles.join(", ")}</span>`
      : `<span class="auto-access-badge">Hammaga ochiq</span>`;
    const row = document.createElement("div");
    row.className = "admin-row";
    row.innerHTML = `
      <div class="info">
        <div class="t">${s.icon || "🧪"} ${s.title}${s.is_active ? "" : " (yashirin)"}</div>
        <div class="s">${s.paragraph_count} ta paragraf · ${s.deadline_days} kun muddat</div>
        <div class="s">${groupsLine}</div>
      </div>
      <div class="row-actions">
        <button data-a="edit">Tahrirlash</button>
        <button data-a="delete" class="danger">O'chirish</button>
      </div>
    `;
    row.querySelector('[data-a="edit"]').onclick = () => openHwSubjectForm(s);
    row.querySelector('[data-a="delete"]').onclick = async () => {
      if (!confirm(`"${s.title}" bo'limini o'chirasizmi? Barcha topshirilgan vazifalar ham o'chadi.`)) return;
      await apiFetch(`/api/admin/homework/subjects/${s.id}`, { method: "DELETE" });
      loadAdminHomeworkSubjects();
    };
    box.appendChild(row);
  });
}

function populateHwCourseCheckboxes(selectedIds) {
  const box = document.getElementById("hwsCourseCheckboxList");
  const selected = new Set((selectedIds || []).map(Number));
  box.innerHTML = "";
  if (!currentAdminCourses.length) {
    box.innerHTML = emptyHtml("Kurs yo'q — bo'lim hammaga ochiq bo'ladi");
    return;
  }
  const bySubject = {};
  currentAdminCourses.forEach(c => {
    const key = c.subject || "Boshqa";
    (bySubject[key] = bySubject[key] || []).push(c);
  });
  Object.keys(bySubject).sort().forEach(subject => {
    const head = document.createElement("div");
    head.className = "course-checkbox-group-title";
    head.textContent = subject;
    box.appendChild(head);
    bySubject[subject].forEach(c => {
      const label = document.createElement("label");
      label.className = "course-checkbox-item";
      label.innerHTML = `
        <input type="checkbox" class="hws-course-cb" value="${c.id}" ${selected.has(Number(c.id)) ? "checked" : ""}>
        <span><b>${c.title}</b></span>
      `;
      box.appendChild(label);
    });
  });
}

function openHwSubjectForm(subject) {
  hideHwPanels();
  document.getElementById("adminHwSubjectForm").classList.remove("hidden");
  document.getElementById("adminHwSubjectFormTitle").textContent = subject ? "Bo'limni tahrirlash" : "Yangi bo'lim";
  document.getElementById("hws_id").value = subject ? subject.id : "";
  document.getElementById("hws_title").value = subject ? subject.title : "";
  document.getElementById("hws_subtitle").value = subject ? (subject.subtitle || "") : "";
  document.getElementById("hws_icon").value = subject ? (subject.icon || "🧪") : "🧪";
  document.getElementById("hws_paragraph_count").value = subject ? subject.paragraph_count : 0;
  document.getElementById("hws_deadline_days").value = subject ? subject.deadline_days : 7;
  document.getElementById("hws_order_num").value = subject ? subject.order_num : 0;
  document.getElementById("hws_is_active").value = subject ? String(subject.is_active) : "1";
  populateHwCourseCheckboxes(subject ? subject.course_ids : []);
}

// ---------- Baholash navbati ----------

async function openHwReview() {
  hideHwPanels();
  document.getElementById("adminHwReviewPanel").classList.remove("hidden");
  const box = document.getElementById("adminHwReviewList");
  box.innerHTML = loadingHtml();
  try {
    const res = await apiFetch(`/api/admin/homework/pending`);
    const data = await res.json();
    const items = data.submissions || [];
    box.innerHTML = "";
    if (!items.length) {
      box.innerHTML = emptyHtml("Tekshirilishi kerak bo'lgan vazifa yo'q 🎉");
      return;
    }
    items.forEach(s => {
      const card = document.createElement("div");
      card.className = "hw-review-card";
      const uname = s.username ? `@${s.username}` : `ID ${s.telegram_id}`;
      card.innerHTML = `
        <div class="hw-review-head">
          <div>
            <div class="hw-review-student">${s.first_name || "Foydalanuvchi"} <span style="font-weight:600;color:var(--text-dim);font-size:12px;">${uname}</span></div>
            <div class="hw-review-meta">${s.subject_icon || "🧪"} ${s.subject_title} · ${s.paragraph_number}-paragraf · ${s.photos.length} ta rasm</div>
          </div>
        </div>
        <div class="hw-review-photos">
          ${s.photos.map(p => `<img src="${p.photo_url}" data-src="${p.photo_url}" alt="vazifa">`).join("")}
        </div>
        <div class="hw-grade-row">
          <input type="number" min="0" max="10" step="0.5" placeholder="Ball" class="hw-score-input">
          <input type="text" placeholder="Izoh (ixtiyoriy)" class="hw-comment-input">
          <button class="gold-btn small" data-a="grade">✅ Ball qo'yish</button>
          <button class="secondary-btn small" data-a="reject">↩️ Qaytarish</button>
        </div>
      `;
      card.querySelectorAll("[data-src]").forEach(img => {
        img.addEventListener("click", () => openLightbox(img.getAttribute("data-src")));
      });
      const scoreInput = card.querySelector(".hw-score-input");
      const commentInput = card.querySelector(".hw-comment-input");
      card.querySelector('[data-a="grade"]').onclick = async () => {
        const score = parseFloat(scoreInput.value);
        if (Number.isNaN(score) || score < 0 || score > 10) {
          const msg = "0 dan 10 gacha ball kiriting.";
          tg.showAlert ? tg.showAlert(msg) : alert(msg);
          return;
        }
        const ok = await saveOrAlert(`/api/admin/homework/grade`, {
          method: "POST",
          body: JSON.stringify({ submission_id: s.id, teacher_score: score, teacher_comment: commentInput.value }),
        }, "Ball qo'yib bo'lmadi");
        if (ok) openHwReview();
      };
      card.querySelector('[data-a="reject"]').onclick = async () => {
        if (!commentInput.value.trim()) {
          const msg = "Qaytarish sababini izoh maydoniga yozing.";
          tg.showAlert ? tg.showAlert(msg) : alert(msg);
          return;
        }
        const ok = await saveOrAlert(`/api/admin/homework/grade`, {
          method: "POST",
          body: JSON.stringify({ submission_id: s.id, reject: true, teacher_comment: commentInput.value }),
        }, "Qaytarib bo'lmadi");
        if (ok) openHwReview();
      };
      box.appendChild(card);
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

// ---------- Kechikkanlar ----------

async function openHwLate() {
  hideHwPanels();
  document.getElementById("adminHwLatePanel").classList.remove("hidden");
  const box = document.getElementById("adminHwLateList");
  box.innerHTML = loadingHtml();
  try {
    const res = await apiFetch(`/api/admin/homework/late`);
    const data = await res.json();
    const items = data.students || [];
    box.innerHTML = "";
    if (!items.length) {
      box.innerHTML = emptyHtml("Kechikkan o'quvchi yo'q 🎉");
      return;
    }
    items.forEach(s => {
      const row = document.createElement("div");
      row.className = "admin-row";
      const uname = s.username ? `@${s.username}` : `ID ${s.telegram_id}`;
      row.innerHTML = `
        <div class="info">
          <div class="t">${s.first_name} <span style="font-weight:600;color:var(--text-dim);font-size:12px;">${uname}</span></div>
          <div class="s">${s.subject_title} · ${s.waiting_paragraph}-paragraf kutilmoqda · ${s.days_idle} kundan beri harakat yo'q</div>
        </div>
        <div class="row-actions">
          <button data-a="remind">📨 Ogohlantirish</button>
        </div>
      `;
      row.querySelector('[data-a="remind"]').onclick = async () => {
        const ok = await saveOrAlert(`/api/admin/homework/remind`, {
          method: "POST", body: JSON.stringify({ students: [s] }),
        }, "Yuborib bo'lmadi");
        if (ok) showToast("📨 Ogohlantirish yuborildi");
      };
      box.appendChild(row);
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

// ---------- Oylik umumlashgan reyting ----------

async function loadHwRanking() {
  const box = document.getElementById("adminHwRankingContent");
  box.innerHTML = loadingHtml();
  const year = intVal("hwRankYear", new Date().getFullYear());
  const month = intVal("hwRankMonth", new Date().getMonth() + 1);
  try {
    const res = await apiFetch(`/api/admin/homework/ranking?year=${year}&month=${month}`);
    const data = await res.json();
    const rows = data.ranking || [];
    if (!rows.length) {
      box.innerHTML = emptyHtml("Bu oyda hali natija yo'q");
      return;
    }
    const medal = i => (i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : "");
    box.innerHTML = `
      <table class="hw-rank-table">
        <thead>
          <tr>
            <th>#</th><th>O'quvchi</th>
            <th class="num">Test</th><th class="num">Vazifa</th><th class="num">Umumiy</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((r, i) => `
            <tr class="${i < 3 ? "hw-rank-row-top" : ""}">
              <td><span class="hw-rank-medal">${medal(i) || r.rank}</span></td>
              <td>${r.first_name}${r.username ? ` <span style="color:var(--text-dim);font-size:11px;">@${r.username}</span>` : ""}</td>
              <td class="num">${r.test_percent}%</td>
              <td class="num">${r.homework_percent}%<br><span style="font-size:10px;color:var(--text-dim);">${r.homework_graded} ta</span></td>
              <td class="num hw-rank-total">${r.total_score}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

export function initHomeworkAdminModule() {
  document.getElementById("adminHwNewSubjectBtn").addEventListener("click", () => openHwSubjectForm(null));
  document.getElementById("adminHwCloseSubjectForm").addEventListener("click",
    () => document.getElementById("adminHwSubjectForm").classList.add("hidden"));
  document.getElementById("adminHwReviewBtn").addEventListener("click", openHwReview);
  document.getElementById("adminHwCloseReview").addEventListener("click",
    () => document.getElementById("adminHwReviewPanel").classList.add("hidden"));
  document.getElementById("adminHwLateBtn").addEventListener("click", openHwLate);
  document.getElementById("adminHwCloseLate").addEventListener("click",
    () => document.getElementById("adminHwLatePanel").classList.add("hidden"));

  document.getElementById("adminHwRankingBtn").addEventListener("click", () => {
    hideHwPanels();
    document.getElementById("adminHwRankingPanel").classList.remove("hidden");
    const now = new Date();
    document.getElementById("hwRankYear").value = now.getFullYear();
    document.getElementById("hwRankMonth").value = now.getMonth() + 1;
    loadHwRanking();
  });
  document.getElementById("adminHwCloseRanking").addEventListener("click",
    () => document.getElementById("adminHwRankingPanel").classList.add("hidden"));
  document.getElementById("adminHwLoadRankingBtn").addEventListener("click", loadHwRanking);

  document.getElementById("adminHwRemindAllBtn").addEventListener("click", async () => {
    if (!confirm("Barcha kechikkan o'quvchilarga ogohlantirish yuborilsinmi?")) return;
    const ok = await saveOrAlert(`/api/admin/homework/remind`, {
      method: "POST", body: JSON.stringify({}),
    }, "Yuborib bo'lmadi");
    if (ok) { showToast("📨 Ogohlantirishlar yuborildi"); openHwLate(); }
  });

  document.getElementById("hwSubjectFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("hws_id").value;
    const title = document.getElementById("hws_title").value.trim();
    if (!title) {
      const msg = "Bo'lim nomini yozing.";
      tg.showAlert ? tg.showAlert(msg) : alert(msg);
      return;
    }
    const data = {
      title,
      subtitle: document.getElementById("hws_subtitle").value,
      icon: document.getElementById("hws_icon").value || "🧪",
      paragraph_count: intVal("hws_paragraph_count", 0),
      deadline_days: intVal("hws_deadline_days", 7),
      order_num: intVal("hws_order_num", 0),
      is_active: intVal("hws_is_active", 1),
      course_ids: Array.from(document.querySelectorAll(".hws-course-cb:checked")).map(cb => parseInt(cb.value, 10)),
    };
    const btn = e.target.querySelector('button[type="submit"]');
    if (btn) { btn.disabled = true; btn.textContent = "Saqlanmoqda..."; }
    const ok = id
      ? await saveOrAlert(`/api/admin/homework/subjects/${id}`, { method: "PUT", body: JSON.stringify(data) }, "Saqlab bo'lmadi")
      : await saveOrAlert(`/api/admin/homework/subjects`, { method: "POST", body: JSON.stringify(data) }, "Saqlab bo'lmadi");
    if (btn) { btn.disabled = false; btn.textContent = "Bo'limni saqlash"; }
    if (!ok) return;
    document.getElementById("adminHwSubjectForm").classList.add("hidden");
    loadAdminHomeworkSubjects();
  });
}
