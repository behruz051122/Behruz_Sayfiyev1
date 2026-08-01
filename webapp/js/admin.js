// js/admin.js
import { apiFetch, tg } from "./api.js";
import { errorHtml, emptyHtml, DIFFICULTY_LABELS, formatSeconds, skeletonCards } from "./components.js";

const DIFFICULTY_DEFAULT_SECONDS = { oson: 300, orta: 600, qiyin: 900 };

let currentAdminCourses = [];
let currentAdminTests = [];

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
      row.innerHTML = `
        <div class="info">
          <div class="t">${t.title}${t.is_active ? "" : " (yashirin)"}</div>
          <div class="s">${t.subject} · ${DIFFICULTY_LABELS[t.difficulty] || t.difficulty} · ${t.question_count} savol · ${formatSeconds(t.time_limit_seconds)}</div>
        </div>
        <div class="row-actions">
          <button data-a="questions">Savollar</button>
          <button data-a="edit">Tahrirlash</button>
          <button data-a="delete" class="danger">O'chirish</button>
        </div>
      `;
      row.querySelector('[data-a="questions"]').onclick = () => openAdminQuestions(t.id, t.title);
      row.querySelector('[data-a="edit"]').onclick = () => openAdminTestForm(t);
      row.querySelector('[data-a="delete"]').onclick = () => deleteAdminTest(t.id);
      box.appendChild(row);
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

function openAdminTestForm(test) {
  document.getElementById("adminTestForm").classList.remove("hidden");
  document.getElementById("adminQuestionsPanel").classList.add("hidden");
  document.getElementById("adminTestFormTitle").textContent = test ? "Testni tahrirlash" : "Yangi test";
  document.getElementById("at_id").value = test ? test.id : "";
  document.getElementById("at_subject").value = test ? test.subject : "";
  document.getElementById("at_title").value = test ? test.title : "";
  document.getElementById("at_difficulty").value = test ? test.difficulty : "orta";
  document.getElementById("at_time_limit").value = test ? test.time_limit_seconds : "";
  document.getElementById("at_order_num").value = test ? test.order_num : 0;
  document.getElementById("at_is_active").value = test ? String(test.is_active) : "1";
}

async function deleteAdminTest(id) {
  if (!confirm("Bu testni butunlay o'chirmoqchimisiz? Barcha savollar ham o'chadi.")) return;
  await apiFetch(`/api/admin/tests/${id}`, { method: "DELETE" });
  loadAdminTests();
}

// ---------- Savollar ----------

async function openAdminQuestions(testId, title) {
  document.getElementById("adminQuestionsPanel").classList.remove("hidden");
  document.getElementById("adminTestForm").classList.add("hidden");
  document.getElementById("adminQuestionsTitle").textContent = `Savollar — ${title}`;
  document.getElementById("aq_test_id").value = testId;
  resetQuestionForm();
  await renderAdminQuestions(testId);
}

function resetQuestionForm() {
  document.getElementById("aq_id").value = "";
  document.getElementById("aq_question_text").value = "";
  document.getElementById("aq_image_url").value = "";
  document.getElementById("aq_option_1").value = "";
  document.getElementById("aq_option_2").value = "";
  document.getElementById("aq_option_3").value = "";
  document.getElementById("aq_option_4").value = "";
  document.getElementById("aq_correct_index").value = "1";
  document.getElementById("aq_order_num").value = 0;
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
      document.getElementById("aq_image_url").value = q.image_url || "";
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

  document.getElementById("testFormEl").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("at_id").value;
    const difficulty = document.getElementById("at_difficulty").value;
    const rawTimeLimit = document.getElementById("at_time_limit").value;
    const data = {
      subject: document.getElementById("at_subject").value,
      title: document.getElementById("at_title").value,
      difficulty: difficulty,
      time_limit_seconds: rawTimeLimit ? parseInt(rawTimeLimit) : DIFFICULTY_DEFAULT_SECONDS[difficulty],
      order_num: parseInt(document.getElementById("at_order_num").value),
      is_active: parseInt(document.getElementById("at_is_active").value)
    };
    if (id) await apiFetch(`/api/admin/tests/${id}`, { method: "PUT", body: JSON.stringify(data) });
    else await apiFetch(`/api/admin/tests`, { method: "POST", body: JSON.stringify(data) });
    document.getElementById("adminTestForm").classList.add("hidden");
    loadAdminTests();
  });

  document.getElementById("adminCloseQuestions").addEventListener("click", () => document.getElementById("adminQuestionsPanel").classList.add("hidden"));

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
}
