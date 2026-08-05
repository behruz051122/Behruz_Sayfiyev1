// js/admin.js
import { apiFetch, tg } from "./api.js";
import { errorHtml, emptyHtml, DIFFICULTY_LABELS, formatSeconds, skeletonCards } from "./components.js";

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

let currentAdminCourses = [];
let currentAdminTests = [];
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
  const box = document.getElementById("adminCoursesList");
  box.innerHTML = skeletonCards(2);
  try {
    const res = await apiFetch(`/api/admin/courses`);
    const data = await res.json();
    currentAdminCourses = data.courses;
    box.innerHTML = "";
    currentAdminCourses.forEach(c => {
      const row = document.createElement("div");
      row.className = "admin-row";
      const accessLabel = c.is_free ? "Bepul" : (c.price > 0 ? c.price.toLocaleString() + " so'm" : c.required_referrals + " taklif");
      row.innerHTML = `
        <div class="emoji">${c.thumbnail_emoji || "📘"}</div>
        <div class="info">
          <div class="t">${c.title}${c.is_active ? "" : " (yashirin)"}</div>
          <div class="s">${c.subject} · ${c.resource_type === "book" ? "Kitob" : "Kurs"} · ${c.lessons_count} dars · ${accessLabel}</div>
        </div>
        <div class="row-actions">
          <button data-a="paragraphs">Bo'limlar</button>
          <button data-a="edit">Tahrirlash</button>
          <button data-a="delete" class="danger">O'chirish</button>
        </div>
      `;
      row.querySelector('[data-a="paragraphs"]').onclick = () => openAdminParagraphs(c.id, c.title);
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
  document.getElementById("ac_thumbnail_emoji").value = course ? (course.thumbnail_emoji || "📘") : "📘";
  document.getElementById("ac_order_num").value = course ? course.order_num : 0;
  document.getElementById("ac_is_active").value = course ? String(course.is_active) : "1";
}

async function deleteAdminCourse(id) {
  if (!confirm("Bu kursni butunlay o'chirmoqchimisiz? Barcha bo'lim va darslar ham o'chadi.")) return;
  await apiFetch(`/api/admin/courses/${id}`, { method: "DELETE" });
  loadAdminCourses();
}

// ---------- Bo'limlar (paragraflar) ----------

let adminActiveCourseId = null;

async function openAdminParagraphs(courseId, title) {
  adminActiveCourseId = courseId;
  document.getElementById("adminParagraphsPanel").classList.remove("hidden");
  document.getElementById("adminCourseForm").classList.add("hidden");
  document.getElementById("adminLessonsPanel").classList.add("hidden");
  document.getElementById("adminParagraphsTitle").textContent = `Bo'limlar — ${title}`;
  document.getElementById("ap_course_id").value = courseId;
  document.getElementById("ap_id").value = "";
  document.getElementById("ap_title").value = "";
  document.getElementById("ap_order_num").value = 0;
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
      <div class="info"><div class="t">${idx + 1}. ${p.title}</div><div class="s">${p.lessons_count} ta video</div></div>
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
    row.innerHTML = `
      <div class="info"><div class="t">${idx + 1}. ${l.title}</div></div>
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
  const box = document.getElementById("adminTestsList");
  box.innerHTML = skeletonCards(2);
  try {
    const res = await apiFetch(`/api/admin/tests`);
    const data = await res.json();
    currentAdminTests = data.tests;
    box.innerHTML = "";
    if (currentAdminTests.length === 0) box.innerHTML = emptyHtml("Hali test qo'shilmagan");
    currentAdminTests.forEach(t => {
      const row = document.createElement("div");
      row.className = "admin-row";
      const controlBadge = t.is_control_test ? `<span class="control-badge">🎓 NAZORAT</span>` : "";
      const attestationBadge = t.test_kind === "attestation" ? `<span class="control-badge">📋 ATTESTATSIYA</span>` : "";
      const accessBtn = t.is_control_test ? `<button data-a="access">👥 Talabalar</button>` : "";
      const resultsBtn = t.is_control_test ? `<button data-a="results">📊 Natijalar</button>` : "";
      row.innerHTML = `
        <div class="info">
          <div class="t">${t.title}${t.is_active ? "" : " (yashirin)"}${controlBadge}${attestationBadge}</div>
          <div class="s">${t.subject} · ${DIFFICULTY_LABELS[t.difficulty] || t.difficulty} · ${t.question_count} savol · ${formatSeconds(t.time_limit_seconds)}</div>
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

function populateControlCourseSelect() {
  const select = document.getElementById("at_course_id");
  select.innerHTML = `<option value="">— Kursga bog'lamaslik —</option>`;
  currentAdminCourses.forEach(c => {
    const opt = document.createElement("option");
    opt.value = c.id;
    opt.textContent = `${c.title} (${c.subject})`;
    select.appendChild(opt);
  });
}

function openAdminTestForm(test) {
  document.getElementById("adminTestForm").classList.remove("hidden");
  document.getElementById("adminQuestionsPanel").classList.add("hidden");
  document.getElementById("adminControlAccessPanel").classList.add("hidden");
  document.getElementById("adminControlResultsPanel").classList.add("hidden");
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

  populateControlCourseSelect();
  const isControl = test ? Boolean(test.is_control_test) : false;
  document.getElementById("at_is_control_test").checked = isControl;
  document.getElementById("atControlCourseWrap").classList.toggle("hidden", !isControl);
  if (test && test.course_id) document.getElementById("at_course_id").value = String(test.course_id);
}

async function deleteAdminTest(id) {
  if (!confirm("Bu testni butunlay o'chirmoqchimisiz? Barcha savollar ham o'chadi.")) return;
  await apiFetch(`/api/admin/tests/${id}`, { method: "DELETE" });
  loadAdminTests();
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

function resetQuestionForm() {
  document.getElementById("aq_id").value = "";
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
  document.getElementById("aq_order_num").value = 0;
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

async function renderAdminQuestions(testId) {
  const res = await apiFetch(`/api/admin/tests/${testId}/questions`);
  const data = await res.json();
  const box = document.getElementById("adminQuestionsList");
  box.innerHTML = "";
  if (data.questions.length === 0) box.innerHTML = emptyHtml("Hali savol qo'shilmagan");
  data.questions.forEach((q, idx) => {
    const row = document.createElement("div");
    row.className = "admin-row";
    row.innerHTML = `
      <div class="info"><div class="t">${idx + 1}. ${q.question_text.slice(0, 60)}${q.question_text.length > 60 ? "…" : ""}</div><div class="s">To'g'ri javob: ${q.correct_index}-variant</div></div>
      <div class="row-actions">
        <button data-a="edit">Tahrirlash</button>
        <button data-a="delete" class="danger">O'chirish</button>
      </div>
    `;
    row.querySelector('[data-a="edit"]').onclick = () => {
      document.getElementById("aq_id").value = q.id;
      document.getElementById("aq_question_text").value = q.question_text;
      document.getElementById("aq_image_file").value = "";
      document.getElementById("aqImageUploadStatus").textContent = "";
      showQuestionImagePreview(q.image_url || "");
      document.getElementById("aq_option_1").value = q.option_1 || "";
      document.getElementById("aq_option_2").value = q.option_2 || "";
      document.getElementById("aq_option_3").value = q.option_3 || "";
      document.getElementById("aq_option_4").value = q.option_4 || "";
      document.getElementById("aq_correct_index").value = String(q.correct_index);
      document.getElementById("aq_order_num").value = q.order_num;
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
    const data = {
      title: document.getElementById("ac_title").value,
      subject: document.getElementById("ac_subject").value,
      resource_type: document.getElementById("ac_resource_type").value,
      description: document.getElementById("ac_description").value,
      is_free: parseInt(document.getElementById("ac_is_free").value),
      required_referrals: parseInt(document.getElementById("ac_required_referrals").value),
      price: parseInt(document.getElementById("ac_price").value || 0),
      duration_days: document.getElementById("ac_duration_days").value || null,
      students_count: parseInt(document.getElementById("ac_students_count").value),
      duration_text: document.getElementById("ac_duration_text").value,
      thumbnail_emoji: document.getElementById("ac_thumbnail_emoji").value,
      order_num: parseInt(document.getElementById("ac_order_num").value),
      is_active: parseInt(document.getElementById("ac_is_active").value)
    };
    if (id) await apiFetch(`/api/admin/courses/${id}`, { method: "PUT", body: JSON.stringify(data) });
    else await apiFetch(`/api/admin/courses`, { method: "POST", body: JSON.stringify(data) });
    document.getElementById("adminCourseForm").classList.add("hidden");
    loadAdminCourses();
  });

  document.getElementById("adminCloseParagraphs").addEventListener("click", () => document.getElementById("adminParagraphsPanel").classList.add("hidden"));

  document.getElementById("paragraphFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("ap_id").value;
    const courseId = document.getElementById("ap_course_id").value;
    const data = {
      course_id: parseInt(courseId),
      title: document.getElementById("ap_title").value,
      order_num: parseInt(document.getElementById("ap_order_num").value)
    };
    if (id) await apiFetch(`/api/admin/paragraphs/${id}`, { method: "PUT", body: JSON.stringify(data) });
    else await apiFetch(`/api/admin/paragraphs`, { method: "POST", body: JSON.stringify(data) });
    document.getElementById("ap_id").value = "";
    document.getElementById("ap_title").value = "";
    document.getElementById("ap_order_num").value = 0;
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
      order_num: parseInt(document.getElementById("al_order_num").value)
    };
    if (id) await apiFetch(`/api/admin/lessons/${id}`, { method: "PUT", body: JSON.stringify(data) });
    else await apiFetch(`/api/admin/lessons`, { method: "POST", body: JSON.stringify(data) });
    document.getElementById("al_id").value = "";
    document.getElementById("al_title").value = "";
    document.getElementById("al_video_url").value = "";
    document.getElementById("al_description").value = "";
    document.getElementById("al_order_num").value = 0;
    renderAdminLessons(paragraphId);
    loadAdminCourses();
  });

  document.getElementById("enrollFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = {
      telegram_id: parseInt(document.getElementById("en_telegram_id").value),
      course_id: parseInt(document.getElementById("en_course_id").value),
      duration_days: document.getElementById("en_duration_days").value || null
    };
    await apiFetch(`/api/admin/enroll`, { method: "POST", body: JSON.stringify(data) });
    tg.showAlert ? tg.showAlert("✅ Obuna berildi!") : alert("Obuna berildi!");
    document.getElementById("en_telegram_id").value = "";
    document.getElementById("en_duration_days").value = "";
  });

  document.getElementById("adminNewTestBtn").addEventListener("click", () => openAdminTestForm(null));
  document.getElementById("adminCloseTestForm").addEventListener("click", () => document.getElementById("adminTestForm").classList.add("hidden"));

  document.getElementById("at_is_control_test").addEventListener("change", (e) => {
    document.getElementById("atControlCourseWrap").classList.toggle("hidden", !e.target.checked);
  });

  document.getElementById("testFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("at_id").value;
    const difficulty = document.getElementById("at_difficulty").value;
    const hoursVal = document.getElementById("at_time_limit_hours").value;
    const minutesVal = document.getElementById("at_time_limit_minutes").value;
    const rawTimeLimit = hoursMinutesToSeconds(hoursVal, minutesVal);
    const isControlTest = document.getElementById("at_is_control_test").checked;
    const rawCourseId = document.getElementById("at_course_id").value;
    const data = {
      subject: document.getElementById("at_subject").value,
      title: document.getElementById("at_title").value,
      difficulty: difficulty,
      time_limit_seconds: rawTimeLimit > 0 ? rawTimeLimit : DIFFICULTY_DEFAULT_SECONDS[difficulty],
      order_num: parseInt(document.getElementById("at_order_num").value),
      is_active: parseInt(document.getElementById("at_is_active").value),
      is_control_test: isControlTest ? 1 : 0,
      // Kurs ixtiyoriy — nazorat testi bo'lsa ham kursga bog'lamaslik mumkin,
      // chunki kirish huquqi endi asosan "Talabalar" ro'yxati orqali beriladi.
      course_id: (isControlTest && rawCourseId) ? parseInt(rawCourseId) : null,
      test_kind: document.getElementById("at_test_kind").value
    };
    if (id) await apiFetch(`/api/admin/tests/${id}`, { method: "PUT", body: JSON.stringify(data) });
    else await apiFetch(`/api/admin/tests`, { method: "POST", body: JSON.stringify(data) });
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

  document.getElementById("questionFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("aq_id").value;
    const testId = document.getElementById("aq_test_id").value;
    const data = {
      test_id: parseInt(testId),
      question_text: document.getElementById("aq_question_text").value,
      image_url: document.getElementById("aq_image_url").value,
      option_1: document.getElementById("aq_option_1").value,
      option_2: document.getElementById("aq_option_2").value,
      option_3: document.getElementById("aq_option_3").value,
      option_4: document.getElementById("aq_option_4").value,
      correct_index: parseInt(document.getElementById("aq_correct_index").value),
      order_num: parseInt(document.getElementById("aq_order_num").value)
    };
    if (id) await apiFetch(`/api/admin/questions/${id}`, { method: "PUT", body: JSON.stringify(data) });
    else await apiFetch(`/api/admin/questions`, { method: "POST", body: JSON.stringify(data) });
    resetQuestionForm();
    renderAdminQuestions(testId);
    loadAdminTests();
  });

  // --- Bosh sahifa kartalari ---

  document.getElementById("adminCloseDashboardCardForm").addEventListener("click", () => document.getElementById("adminDashboardCardForm").classList.add("hidden"));

  document.getElementById("dashboardCardFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const key = document.getElementById("dc_key").value;
    const data = {
      title: document.getElementById("dc_title").value,
      subtitle: document.getElementById("dc_subtitle").value,
      icon: document.getElementById("dc_icon").value,
      order_num: parseInt(document.getElementById("dc_order_num").value),
      is_active: parseInt(document.getElementById("dc_is_active").value)
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
      price: parseInt(document.getElementById("bp_price").value || 0),
      image_url: document.getElementById("bp_image_url").value,
      badge_text: document.getElementById("bp_badge_text").value,
      is_bundle: parseInt(document.getElementById("bp_is_bundle").value),
      contact_username: document.getElementById("bp_contact_username").value,
      linked_course_id: document.getElementById("bp_linked_course_id").value ? parseInt(document.getElementById("bp_linked_course_id").value) : null,
      order_num: parseInt(document.getElementById("bp_order_num").value),
      is_active: parseInt(document.getElementById("bp_is_active").value)
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
      order_num: parseInt(document.getElementById("faq_order_num").value),
      is_active: parseInt(document.getElementById("faq_is_active").value)
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
      order_num: parseInt(document.getElementById("sr_order_num").value),
      is_active: parseInt(document.getElementById("sr_is_active").value)
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
      order_num: parseInt(document.getElementById("as_order_num").value),
      is_active: parseInt(document.getElementById("as_is_active").value)
    };
    if (id) await apiFetch(`/api/admin/simulators/${id}`, { method: "PUT", body: JSON.stringify(data) });
    else await apiFetch(`/api/admin/simulators`, { method: "POST", body: JSON.stringify(data) });
    document.getElementById("adminSimulatorForm").classList.add("hidden");
    loadAdminSimulators();
  });

  document.getElementById("adminCloseSimSubjects").addEventListener("click", () => document.getElementById("adminSimSubjectsPanel").classList.add("hidden"));

  document.getElementById("simSubjectFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const simulatorId = parseInt(document.getElementById("ass_simulator_id").value);
    const data = {
      simulator_id: simulatorId,
      subject: document.getElementById("ass_subject").value.trim(),
      question_count: parseInt(document.getElementById("ass_question_count").value || 10),
      order_num: parseInt(document.getElementById("ass_order_num").value)
    };
    await apiFetch(`/api/admin/simulator-subjects`, { method: "POST", body: JSON.stringify(data) });
    document.getElementById("ass_subject").value = "";
    document.getElementById("ass_question_count").value = 10;
    document.getElementById("ass_order_num").value = 0;
    renderAdminSimSubjects(simulatorId);
    loadAdminSimulators();
  });
}
