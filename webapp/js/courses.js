// js/courses.js
import { apiFetch } from "./api.js";
import { showScreen, navigateTo } from "./navigate.js";
import { loadingHtml, errorHtml, emptyHtml, skeletonCards, showToast } from "./components.js";
import { refreshCoins } from "./user.js";

let currentListType = "course";
let currentCourse = null;
let currentParagraph = null;
let currentLesson = null;
let lessonKeyHandler = null;
let allCourses = [];
let activeStatusFilter = "all";
let activeSubjectFilter = "Hammasi";
let searchQuery = "";

// ---------- Kurslar: fan tanlash + Nazoratli/Mustaqil guruhlangan ro'yxat ----------
// (Kelajakmediklari_bot tahlili asosida — ikki bosqichli oqim: avval fan
// tanlanadi, keyin shu fan bo'yicha "Nazoratli"/"Mustaqil" kurslar ko'rinadi)
let allSubjectCourses = [];
let subjectCoursesLoaded = false;
let activeCourseSubject = null;
let activeCourseTypeFilter = "all";
let courseListSearchQuery = "";
// Kurs detali ekranidan "←" bosilganda qaysi ekranga qaytish kerakligini
// eslab qoladi — Kurslar oqimi (yangi, guruhlangan) va Kitoblar oqimi (eski,
// tekis ro'yxat) BITTA "screen-detail" ekranini ishlatadi, shuning uchun
// orqaga tugmasi kelgan joyiga qarab farqli ekranga qaytishi kerak.
let courseDetailReturnScreen = "list";

const SUBJECT_CARD_STYLES = [
  { cls: "subject-teal", glyph: "🧬" },
  { cls: "subject-orange", glyph: "🧪" },
  { cls: "subject-purple", glyph: "📘" },
  { cls: "subject-cyan", glyph: "🔬" },
];

export function getCourseDetailReturnScreen() {
  return courseDetailReturnScreen;
}

export function setListType(type) {
  currentListType = type;
  activeStatusFilter = "all";
  activeSubjectFilter = "Hammasi";
  searchQuery = "";
  // Bu eski, tekis ro'yxat orqali kirilganda (hozircha faqat Kitoblar
  // bo'limi) kurs detalidan "←" bosilsa shu tekis ro'yxatga qaytishi kerak.
  courseDetailReturnScreen = "list";
  const searchInput = document.getElementById("courseSearchInput");
  if (searchInput) searchInput.value = "";
  // Bosma kitoblar do'koniga o'tish banneri faqat "Kitoblar" ro'yxatida
  // ko'rinadi — bu RAQAMLI kitob/kurs kontentidan (courses jadvali) BUTUNLAY
  // ALOHIDA, yangi bosma-kitob-do'koni funksiyasi (book_products jadvali).
  const banner = document.getElementById("listBookShopBanner");
  if (banner) banner.classList.toggle("hidden", type !== "book");
}

export function getCurrentCourse() {
  return currentCourse;
}

export function getCurrentParagraph() {
  return currentParagraph;
}

// ================================================================
// KURSLAR: FAN TANLASH (landing)
// ================================================================

export async function loadCourseSubjects() {
  const grid = document.getElementById("subjectSelectGrid");
  grid.innerHTML = skeletonCards(2);
  try {
    const res = await apiFetch(`/api/courses?resource_type=course`);
    const data = await res.json();
    allSubjectCourses = data.courses;
    subjectCoursesLoaded = true;
    renderSubjectLandingCards();
  } catch (e) {
    console.error(e);
    grid.innerHTML = errorHtml();
  }
}

function getCourseSubjects() {
  return [...new Set(allSubjectCourses.map(c => c.subject))];
}

function renderSubjectLandingCards() {
  const grid = document.getElementById("subjectSelectGrid");
  const subjects = getCourseSubjects();
  grid.innerHTML = "";

  if (subjects.length === 0) {
    grid.innerHTML = emptyHtml("Hozircha kurslar qo'shilmagan");
    return;
  }

  subjects.forEach((subject, i) => {
    const count = allSubjectCourses.filter(c => c.subject === subject).length;
    const style = SUBJECT_CARD_STYLES[i % SUBJECT_CARD_STYLES.length];
    const card = document.createElement("button");
    card.className = `subject-card ${style.cls}`;
    card.innerHTML = `
      <div class="subject-card-icon">${style.glyph}</div>
      <div class="subject-card-body">
        <div class="subject-card-title">${subject}</div>
        <div class="subject-card-sub">${count} TA KURS</div>
        <div class="subject-card-cta">OCHISH →</div>
      </div>
    `;
    card.addEventListener("click", () => openSubjectCourseList(subject));
    grid.appendChild(card);
  });
}

// ================================================================
// KURSLAR: FAN BO'YICHA RO'YXAT (Nazoratli / Mustaqil guruhlar)
// ================================================================

function openSubjectCourseList(subject) {
  activeCourseSubject = subject;
  activeCourseTypeFilter = "all";
  courseListSearchQuery = "";
  const searchInput = document.getElementById("courseListSearchInput");
  if (searchInput) searchInput.value = "";
  document.getElementById("coursesBySubjectTitle").textContent = subject;
  renderCourseSubjectTabs();
  bindCourseTypeFilters();
  bindCourseListSearch();
  bindCoursesBySubjectStaticButtons();
  renderGroupedCourseList();
  showScreen("courses-by-subject");
}

function bindCoursesBySubjectStaticButtons() {
  const backBtn = document.getElementById("coursesBackToSubjectsBtn");
  if (backBtn && !backBtn.dataset.bound) {
    backBtn.dataset.bound = "true";
    backBtn.addEventListener("click", () => showScreen("courses-landing"));
  }
  const promoBtn = document.getElementById("promoCodeApplyBtn");
  if (promoBtn && !promoBtn.dataset.bound) {
    promoBtn.dataset.bound = "true";
    promoBtn.addEventListener("click", () => {
      showToast("Promo-kod tizimi tez orada ishga tushadi");
    });
  }
}

function renderCourseSubjectTabs() {
  const row = document.getElementById("courseSubjectTabRow");
  row.innerHTML = "";
  getCourseSubjects().forEach(subject => {
    const btn = document.createElement("button");
    btn.className = "tab-btn" + (subject === activeCourseSubject ? " active" : "");
    btn.textContent = subject;
    btn.addEventListener("click", () => openSubjectCourseList(subject));
    row.appendChild(btn);
  });
}

function bindCourseTypeFilters() {
  document.querySelectorAll("#courseTypeFilterRow .filter-chip").forEach(chip => {
    chip.classList.toggle("active", chip.getAttribute("data-ctype") === activeCourseTypeFilter);
    chip.onclick = () => {
      activeCourseTypeFilter = chip.getAttribute("data-ctype");
      document.querySelectorAll("#courseTypeFilterRow .filter-chip").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      renderGroupedCourseList();
    };
  });
}

function bindCourseListSearch() {
  const input = document.getElementById("courseListSearchInput");
  if (!input || input.dataset.bound) return;
  input.dataset.bound = "true";
  input.addEventListener("input", () => {
    courseListSearchQuery = input.value.trim().toLowerCase();
    renderGroupedCourseList();
  });
}

const COURSE_TYPE_GROUPS = [
  { key: "nazoratli", title: "Nazoratli", subtitle: "JURNAL · DAVOMAT · MENTOR", icon: "📖" },
  { key: "mustaqil", title: "Mustaqil", subtitle: "O'Z SUR'ATINGIZDA", icon: "🧑‍💻" },
];

function renderGroupedCourseList() {
  const container = document.getElementById("coursesGroupedList");
  container.innerHTML = "";

  const filtered = allSubjectCourses.filter(c => {
    if (c.subject !== activeCourseSubject) return false;
    const courseType = c.course_type || "mustaqil";
    if (activeCourseTypeFilter === "nazoratli" && courseType !== "nazoratli") return false;
    if (activeCourseTypeFilter === "mustaqil" && courseType !== "mustaqil") return false;
    if (activeCourseTypeFilter === "free" && !c.is_free) return false;
    if (courseListSearchQuery && !(`${c.title} ${c.description || ""}`.toLowerCase().includes(courseListSearchQuery))) return false;
    return true;
  });

  if (filtered.length === 0) {
    container.innerHTML = emptyHtml(courseListSearchQuery ? `"${courseListSearchQuery}" bo'yicha hech narsa topilmadi` : "Bu bo'limda hozircha kurs yo'q");
    return;
  }

  COURSE_TYPE_GROUPS.forEach(group => {
    const groupCourses = filtered.filter(c => (c.course_type || "mustaqil") === group.key);
    if (groupCourses.length === 0) return;

    const section = document.createElement("div");
    section.className = "course-group";
    section.innerHTML = `
      <div class="course-group-head">
        <div class="course-group-icon">${group.icon}</div>
        <div class="course-group-info">
          <div class="course-group-title">${group.title}</div>
          <div class="course-group-sub">${group.subtitle}</div>
        </div>
        <div class="course-group-count">${groupCourses.length}</div>
      </div>
      <div class="course-row-list"></div>
    `;
    const listEl = section.querySelector(".course-row-list");
    groupCourses.forEach(course => listEl.appendChild(buildCourseRowCard(course)));
    container.appendChild(section);
  });
}

function buildCourseRowCard(course) {
  const card = document.createElement("div");
  card.className = "course-row-card";
  const priceLabel = course.is_free ? "Bepul" : (course.price ? course.price.toLocaleString() + " so'm" : "Yopiq");
  const freeBadge = course.free_lessons_count > 0 ? `<span class="free-lessons-badge">${course.free_lessons_count} BEPUL</span>` : "";
  card.innerHTML = `
    <div class="course-row-icon">${course.thumbnail_emoji || "📘"}</div>
    <div class="course-row-info">
      <div class="course-row-title">${course.title}</div>
      <div class="course-row-meta">${course.duration_text ? `⏱ ${course.duration_text} · ` : ""}${course.lessons_count} dars</div>
      <div class="course-row-bottom">
        <span class="course-row-price">${priceLabel}</span>
        ${freeBadge}
      </div>
    </div>
    <div class="lesson-play">›</div>
  `;
  card.addEventListener("click", () => {
    courseDetailReturnScreen = "courses-by-subject";
    openCourseDetail(course.id);
  });
  return card;
}

// ---------- Kurslar ro'yxati ----------

export async function loadCourseList() {
  const container = document.getElementById("courseList");
  container.innerHTML = skeletonCards(3);
  bindSearchInput();
  try {
    const res = await apiFetch(`/api/courses?resource_type=${currentListType}`);
    const data = await res.json();
    allCourses = data.courses;
    buildSubjectFilters();
    bindStatusFilters();
    renderCourseList();
  } catch (e) {
    console.error(e);
    container.innerHTML = errorHtml();
  }
}

function bindSearchInput() {
  const input = document.getElementById("courseSearchInput");
  if (!input || input.dataset.bound) return;
  input.dataset.bound = "true";
  input.addEventListener("input", () => {
    searchQuery = input.value.trim().toLowerCase();
    renderCourseList();
  });
}

function bindStatusFilters() {
  document.querySelectorAll("#statusFilterRow .filter-chip").forEach(chip => {
    chip.classList.toggle("active", chip.getAttribute("data-filter") === activeStatusFilter);
    chip.onclick = () => {
      activeStatusFilter = chip.getAttribute("data-filter");
      document.querySelectorAll("#statusFilterRow .filter-chip").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      renderCourseList();
    };
  });
}

function buildSubjectFilters() {
  const row = document.getElementById("subjectFilterRow");
  const subjects = ["Hammasi", ...new Set(allCourses.map(c => c.subject))];
  row.innerHTML = "";
  subjects.forEach(subj => {
    const chip = document.createElement("button");
    chip.className = "filter-chip" + (subj === activeSubjectFilter ? " active" : "");
    chip.textContent = subj;
    chip.onclick = () => {
      activeSubjectFilter = subj;
      document.querySelectorAll("#subjectFilterRow .filter-chip").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      renderCourseList();
    };
    row.appendChild(chip);
  });
}

function renderCourseList() {
  const container = document.getElementById("courseList");
  container.innerHTML = "";

  let filtered = allCourses.filter(c => {
    if (activeStatusFilter === "free" && !c.is_free) return false;
    if (activeStatusFilter === "locked" && c.is_free) return false;
    if (activeSubjectFilter !== "Hammasi" && c.subject !== activeSubjectFilter) return false;
    if (searchQuery && !(`${c.title} ${c.subject} ${c.description || ""}`.toLowerCase().includes(searchQuery))) return false;
    return true;
  });

  if (filtered.length === 0) {
    container.innerHTML = emptyHtml(searchQuery ? `"${searchQuery}" bo'yicha hech narsa topilmadi` : "Bu bo'limda hozircha hech narsa yo'q");
    return;
  }

  filtered.forEach(course => {
    const card = document.createElement("div");
    card.className = "course-card" + (course.unlocked ? "" : " locked-card");
    let statusHtml = "";
    if (course.unlocked) {
      if (course.reason === "grace") statusHtml = `<div class="lock-badge">⏳ Obuna muddati tugadi — ${Math.abs(course.days_left)} kun ichida yangilang</div>`;
      else statusHtml = `<div class="unlock-badge">✅ Ochiq</div>`;
    } else if (course.reason === "expired") {
      statusHtml = `<div class="lock-badge">🔒 Obuna muddati tugagan</div>`;
    } else if (course.required_referrals > 0) {
      statusHtml = `<div class="lock-badge">🔒 ${course.confirmed_referrals || 0}/${course.required_referrals} taklif</div>`;
    } else {
      statusHtml = `<div class="lock-badge">🔒 ${course.price ? course.price.toLocaleString() + " so'm" : "Yopiq"}</div>`;
    }

    card.innerHTML = `
      ${course.is_free ? `<div class="course-free-tag">BEPUL</div>` : ""}
      <div class="course-emoji">${course.thumbnail_emoji || "📘"}</div>
      <div class="course-info">
        <span class="course-tag">${course.subject}</span>
        <div class="course-title">${course.title}</div>
        <div class="course-desc">${course.description || ""}</div>
        <div class="course-meta">
          ${course.students_count ? `<span>👥 ${course.students_count} o'tgan</span>` : ""}
          <span>📘 ${course.lessons_count} dars</span>
          ${course.duration_text ? `<span>🗓 ${course.duration_text}</span>` : ""}
        </div>
        ${statusHtml}
      </div>
    `;
    card.addEventListener("click", () => openCourseDetail(course.id));
    container.appendChild(card);
  });
}

// ---------- Kurs ichi (paragraflar) ----------

export async function openCourseDetail(courseId) {
  const content = document.getElementById("detailContent");
  content.innerHTML = loadingHtml();
  showScreen("detail");

  try {
    const res = await apiFetch(`/api/course/${courseId}`);
    const course = await res.json();
    currentCourse = course;
    document.getElementById("detailTitle").textContent = course.title;

    let html = `
      <div class="detail-hero">
        <span class="course-tag">${course.subject}</span>
        <h1>${course.title}</h1>
        <p>${course.description || ""}</p>
      </div>
      <div class="stat-boxes">
        <div class="stat-box"><div class="num">${course.paragraphs.reduce((a,p)=>a+p.lessons_count,0)}</div><div class="lbl">ta dars</div></div>
        <div class="stat-box"><div class="num">${course.paragraphs.length}</div><div class="lbl">bo'lim</div></div>
        <div class="stat-box"><div class="num">${course.unlocked ? "🔓" : "🔒"}</div><div class="lbl">${course.unlocked ? "Ochiq" : "Yopiq"}</div></div>
      </div>
    `;

    if (course.unlocked && course.reason === "grace") {
      html += `<div class="grace-banner">⏳ Obuna muddatingiz tugagan. ${course.days_left <= 0 ? Math.abs(course.days_left) : 0} kundan so'ng darslar avtomatik yopiladi — obunani yangilashni unutmang.</div>`;
    }

    // Kurs 100% tugallangan bo'lsa — sertifikat yuklab olish bannerini ko'rsatamiz.
    // To'liqlik darajasi mavjud paragraf/dars ma'lumotlaridan (client tomonda)
    // hisoblanadi — bu qo'shimcha API so'rovisiz tezkor ko'rsatish imkonini beradi;
    // yuklab olishda server o'zi yana bir bor tekshirib, sertifikatni "beradi".
    if (course.unlocked) {
      const totalLessons = course.paragraphs.reduce((a, p) => a + p.lessons_count, 0);
      const watchedLessons = course.paragraphs.reduce((a, p) => a + (p.lessons || []).filter(l => l.watched).length, 0);
      const isComplete = totalLessons > 0 && watchedLessons >= totalLessons;
      if (isComplete) {
        html += `
          <div class="certificate-banner">
            <div class="cert-banner-icon">🎓</div>
            <div class="cert-banner-info">
              <div class="cert-banner-title">Tabriklaymiz! Kurs 100% tugallandi</div>
              <div class="cert-banner-sub">Endi shaxsiy sertifikatingizni yuklab olishingiz mumkin</div>
            </div>
            <button class="gold-btn" id="downloadCertificateBtn">📄 Sertifikatni yuklab olish</button>
          </div>
        `;
      }
    }

    if (course.unlocked) {
      html += `<div class="paragraph-list">`;
      if (course.paragraphs.length === 0) {
        html += emptyHtml("Hozircha bo'limlar qo'shilmagan");
      } else {
        course.paragraphs.forEach((p, idx) => {
          const watchedCount = p.lessons.filter(l => l.watched).length;
          html += `
            <div class="paragraph-item" data-p-id="${p.id}">
              <div class="paragraph-num">${idx + 1}</div>
              <div class="paragraph-info">
                <div class="paragraph-title">${p.title}</div>
                <div class="paragraph-meta">${p.lessons_count} ta video · ${watchedCount}/${p.lessons_count} ko'rilgan</div>
              </div>
              <div class="lesson-play">›</div>
            </div>
          `;
        });
      }
      html += `</div>`;
    } else {
      const reasonText = course.reason === "expired"
        ? "Obuna muddatingiz tugagan. Davom ettirish uchun obunani yangilang."
        : course.required_referrals > 0
          ? `Ushbu kursni ochish uchun ${course.required_referrals} kishini taklif qiling.`
          : `Ushbu kurs pullik. Narxi: ${(course.price || 0).toLocaleString()} so'm${course.duration_text ? " / " + course.duration_text : ""}.`;

      // Kurs yopiq bo'lsa ham, admin "bepul namuna" deb belgilagan darslar
      // bor bo'lsa — ularni ro'yxatdan o'tmasdan ko'rish imkonini beramiz
      // (Kelajakmediklari_bot'dagi "N BEPUL" belgisi shu ma'noni bildiradi).
      const previewParagraphs = course.paragraphs.filter(p => (p.lessons || []).length > 0);
      if (previewParagraphs.length > 0) {
        html += `<p style="margin:0 16px 10px;font-size:11.5px;color:var(--text-dim);">🔓 Quyidagi darslarni ro'yxatdan o'tmasdan bepul ko'rishingiz mumkin:</p>`;
        html += `<div class="paragraph-list">`;
        previewParagraphs.forEach((p) => {
          html += `
            <div class="paragraph-item" data-p-id="${p.id}">
              <div class="paragraph-num">🔓</div>
              <div class="paragraph-info">
                <div class="paragraph-title">${p.title}</div>
                <div class="paragraph-meta">${p.lessons.length} ta bepul namuna video</div>
              </div>
              <div class="lesson-play">›</div>
            </div>
          `;
        });
        html += `</div>`;
      }

      html += `
        <div class="locked-box">
          <div class="lock-emoji">🔒</div>
          <h3>Bu kurs hali yopiq</h3>
          <p>${reasonText}</p>
          ${course.required_referrals > 0
            ? `<button class="gold-btn" id="lockedReferralBtn">Do'stlarni taklif qilish</button>`
            : `<button class="gold-btn" id="lockedContactBtn">Admin bilan bog'lanish</button>`}
        </div>
      `;
    }

    content.innerHTML = html;

    document.querySelectorAll(".paragraph-item").forEach(item => {
      item.addEventListener("click", () => openParagraph(parseInt(item.getAttribute("data-p-id"))));
    });

    const referralBtn = document.getElementById("lockedReferralBtn");
    if (referralBtn) referralBtn.addEventListener("click", () => navigateTo("referral"));
    const contactBtn = document.getElementById("lockedContactBtn");
    if (contactBtn) contactBtn.addEventListener("click", () => navigateTo("profile"));

    const certBtn = document.getElementById("downloadCertificateBtn");
    if (certBtn) certBtn.addEventListener("click", () => downloadCertificate(courseId, certBtn));
  } catch (e) {
    console.error(e);
    content.innerHTML = errorHtml();
  }
}

// ---------- Sertifikat yuklab olish ----------
// export qilingan — Profil ekranidagi "Mening sertifikatlarim" ro'yxati ham
// aynan shu funksiyadan foydalanadi (kod takrorlanmasin uchun).

export async function downloadCertificate(courseId, btnEl) {
  const originalText = btnEl.textContent;
  btnEl.disabled = true;
  btnEl.textContent = "Tayyorlanmoqda...";
  try {
    const res = await apiFetch(`/api/course/${courseId}/certificate/download`);
    if (!res.ok) throw new Error("Sertifikat yaratib bo'lmadi");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `sertifikat_${courseId}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
    showToast("🎓 Sertifikat yuklab olindi");
  } catch (e) {
    console.error(e);
    showToast("Sertifikatni yuklab bo'lmadi, qayta urinib ko'ring");
  } finally {
    btnEl.disabled = false;
    btnEl.textContent = originalText;
  }
}

// ---------- Paragraf ichi (video darslar) ----------

export function openParagraph(paragraphId) {
  const p = currentCourse.paragraphs.find(x => x.id === paragraphId);
  if (!p) return;
  currentParagraph = p;
  document.getElementById("paragraphTitle").textContent = p.title;

  const content = document.getElementById("paragraphContent");
  let html = `<div class="lesson-list">`;
  if (p.lessons.length === 0) {
    html += emptyHtml("Bu bo'limda hozircha video yo'q");
  } else {
    p.lessons.forEach((lesson, idx) => {
      html += `
        <div class="lesson-item" data-lesson-id="${lesson.id}">
          <div class="lesson-num ${lesson.watched ? "watched" : ""}">${lesson.watched ? "✓" : idx + 1}</div>
          <div class="lesson-title">${lesson.title}</div>
          <div class="lesson-play">▶</div>
        </div>
      `;
    });
  }
  html += `</div>`;
  content.innerHTML = html;

  document.querySelectorAll(".lesson-item").forEach(item => {
    item.addEventListener("click", () => {
      const lessonId = parseInt(item.getAttribute("data-lesson-id"));
      const lesson = p.lessons.find(l => l.id === lessonId);
      playLesson(lesson);
    });
  });

  showScreen("paragraph");
}

// ---------- Video pleyer ----------

function extractYoutubeId(url) {
  try {
    const patterns = [
      /youtu\.be\/([a-zA-Z0-9_-]{11})/,
      /[?&]v=([a-zA-Z0-9_-]{11})/,
      /\/embed\/([a-zA-Z0-9_-]{11})/,
      /\/shorts\/([a-zA-Z0-9_-]{11})/
    ];
    for (const p of patterns) {
      const m = url.match(p);
      if (m) return m[1];
    }
  } catch (e) {}
  return "";
}

function playLesson(lesson) {
  currentLesson = lesson;
  document.getElementById("lessonTitle").textContent = lesson.title;
  const content = document.getElementById("lessonContent");

  const lessons = currentParagraph ? currentParagraph.lessons : [lesson];
  const idx = lessons.findIndex(l => l.id === lesson.id);
  const total = lessons.length;
  const hasPrev = idx > 0;
  const hasNext = idx >= 0 && idx < total - 1;

  let videoHtml = "";
  const url = (lesson.video_url || "").trim();
  const isYoutube = url.includes("youtube.com") || url.includes("youtu.be");

  if (isYoutube) {
    const videoId = extractYoutubeId(url);
    if (!videoId) {
      videoHtml = `
        <div class="locked-box">
          <p>Bu videoni to'g'ridan-to'g'ri ko'rsatib bo'lmadi.</p>
          <button class="gold-btn" id="openYoutubeBtn">▶ YouTube'da ochish</button>
        </div>`;
    } else {
      // fs=0 — YouTube pleyerining o'z fullscreen tugmasini yashiradi. Bu
      // tugma Telegram ichida (ayniqsa mobil ilovada) ishlamaydi va faqat
      // chalkashlik keltirib chiqarardi — endi pastdagi bizning ⛶ tugmamiz
      // (haqiqatan ishlaydigan CSS-asosli fullscreen) yagona variant bo'ladi.
      const embedUrl = `https://www.youtube-nocookie.com/embed/${videoId}?rel=0&modestbranding=1&playsinline=1&fs=0`;
      videoHtml = `
        <div class="video-wrap" id="videoWrap">
          <iframe src="${embedUrl}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" ></iframe>
          <button class="fullscreen-btn" id="fullscreenBtn">⛶</button>
        </div>
        <div class="video-fallback">Video ochilmayaptimi? <a href="${url}" target="_blank" rel="noopener">To'g'ridan-to'g'ri YouTube'da ochish</a></div>`;
    }
  } else if (url) {
    videoHtml = `
      <div class="video-wrap" id="videoWrap">
        <video src="${url}" controls playsinline></video>
        <button class="fullscreen-btn" id="fullscreenBtn">⛶</button>
      </div>
      <div class="video-fallback">Video ochilmayaptimi? <a href="${url}" target="_blank" rel="noopener">Havolani to'g'ridan-to'g'ri ochish</a></div>`;
  } else {
    videoHtml = `<div class="locked-box"><p>Video manzili kiritilmagan</p></div>`;
  }

  content.innerHTML = `
    ${videoHtml}
    ${idx >= 0 ? `<div class="lesson-progress-text">${idx + 1} / ${total}-DARS</div>` : ""}
    <div class="detail-hero">
      <h1>${lesson.title}</h1>
      <p>${lesson.description || ""}</p>
    </div>
    <div class="lesson-nav-row">
      <button class="lesson-nav-btn" id="prevLessonBtn" ${hasPrev ? "" : "disabled"} aria-label="Oldingi dars">◀ Oldingi</button>
      <button class="lesson-nav-btn lesson-nav-list" id="lessonListBtn" aria-label="Darslar ro'yxati">📋</button>
      <button class="lesson-nav-btn" id="nextLessonBtn" ${hasNext ? "" : "disabled"} aria-label="Keyingi dars">Keyingi ▶</button>
    </div>
    <div style="margin:0 16px;" id="watchedBtnWrap">
      ${lesson.watched
        ? `<div class="watched-confirmed">✓ Bu dars ko'rildi — coin qo'shildi</div>`
        : `<button class="gold-btn" id="markWatchedBtn">✓ Ko'rib bo'ldim (+1 🪙)</button>`}
    </div>
  `;

  const youtubeBtn = document.getElementById("openYoutubeBtn");
  if (youtubeBtn) youtubeBtn.addEventListener("click", () => window.open(url, "_blank"));

  const fsBtn = document.getElementById("fullscreenBtn");
  if (fsBtn) {
    fsBtn.addEventListener("click", () => {
      const wrap = document.getElementById("videoWrap");
      const isActive = wrap.classList.toggle("fs-active");
      fsBtn.textContent = isActive ? "✕" : "⛶";
      document.body.classList.toggle("no-scroll", isActive);
      if (isActive && screen.orientation && screen.orientation.lock) {
        screen.orientation.lock("landscape").catch(() => {});
      } else if (!isActive && screen.orientation && screen.orientation.unlock) {
        try { screen.orientation.unlock(); } catch (e) {}
      }
    });
  }

  const markBtn = document.getElementById("markWatchedBtn");
  if (markBtn) {
    markBtn.addEventListener("click", async () => {
      markBtn.disabled = true;
      markBtn.textContent = "...";
      try {
        const res = await apiFetch(`/api/lesson/${lesson.id}/watched`, { method: "POST" });
        const data = await res.json();
        lesson.watched = true;
        document.getElementById("watchedBtnWrap").innerHTML = `<div class="watched-confirmed">✓ Bu dars ko'rildi — coin qo'shildi</div>`;
        refreshCoins();
        if (data.coin_awarded) {
          showToast("🎉 Tabriklaymiz! +1 coin oldingiz");
        }
      } catch (e) {
        console.error(e);
        markBtn.disabled = false;
        markBtn.textContent = "✓ Ko'rib bo'ldim (+1 🪙)";
      }
    });
  }

  // --- Oldingi / Keyingi / Ro'yxat navigatsiyasi ---
  const prevBtn = document.getElementById("prevLessonBtn");
  if (prevBtn) prevBtn.addEventListener("click", () => { if (hasPrev) playLesson(lessons[idx - 1]); });

  const nextBtn = document.getElementById("nextLessonBtn");
  if (nextBtn) nextBtn.addEventListener("click", () => { if (hasNext) playLesson(lessons[idx + 1]); });

  const listBtn = document.getElementById("lessonListBtn");
  if (listBtn) listBtn.addEventListener("click", () => openParagraph(currentParagraph.id));

  // --- Klaviatura bilan navigatsiya (asosan kompyuterda foydali) ---
  // Faqat "dars" ekrani ochiq bo'lganda va foydalanuvchi biror input maydoniga
  // yozmayotganda ishlaydi — boshqa ekranlarga yoki qidiruv maydonlariga
  // xalaqit bermaydi.
  if (lessonKeyHandler) document.removeEventListener("keydown", lessonKeyHandler);
  lessonKeyHandler = (e) => {
    const lessonScreen = document.getElementById("screen-lesson");
    if (!lessonScreen || lessonScreen.classList.contains("hidden")) return;
    const activeTag = document.activeElement ? document.activeElement.tagName : "";
    if (activeTag === "INPUT" || activeTag === "TEXTAREA") return;
    if (e.key === "ArrowLeft" && hasPrev) playLesson(lessons[idx - 1]);
    else if (e.key === "ArrowRight" && hasNext) playLesson(lessons[idx + 1]);
  };
  document.addEventListener("keydown", lessonKeyHandler);

  showScreen("lesson");
}
