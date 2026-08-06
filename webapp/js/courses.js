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
// Kurs "guruhlari" (kategoriyalari) — admin panelidan o'zi yaratadigan,
// moslashuvchan bo'limlar ro'yxati (masalan "Nazoratli", "Mustaqil", "Bepul
// kurs"). Avvalgi qattiq belgilangan Nazoratli/Mustaqil massiv o'rnini oldi.
let courseCategories = [];
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
    const [coursesRes, categoriesRes] = await Promise.all([
      apiFetch(`/api/courses?resource_type=course`),
      apiFetch(`/api/course-categories`)
    ]);
    const data = await coursesRes.json();
    const categoriesData = await categoriesRes.json();
    allSubjectCourses = data.courses;
    courseCategories = categoriesData.categories;
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
  renderCourseTypeFilters();
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

// Filter chip qatori endi admin o'zi yaratgan guruhlar asosida DINAMIK
// quriladi ("Barchasi" va "Bepul" doim bor, o'rtada har bir faol guruh).
function renderCourseTypeFilters() {
  const row = document.getElementById("courseTypeFilterRow");
  row.innerHTML = "";

  const makeChip = (value, label) => {
    const chip = document.createElement("button");
    chip.className = "filter-chip" + (activeCourseTypeFilter === value ? " active" : "");
    chip.textContent = label;
    chip.onclick = () => {
      activeCourseTypeFilter = value;
      renderCourseTypeFilters();
      renderGroupedCourseList();
    };
    return chip;
  };

  row.appendChild(makeChip("all", "Barchasi"));
  courseCategories.forEach(cat => {
    row.appendChild(makeChip(String(cat.id), `${cat.icon || ""} ${cat.title}`.trim()));
  });
  row.appendChild(makeChip("free", "Bepul"));
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

function renderGroupedCourseList() {
  const container = document.getElementById("coursesGroupedList");
  container.innerHTML = "";

  const filtered = allSubjectCourses.filter(c => {
    if (c.subject !== activeCourseSubject) return false;
    const categoryIds = c.category_ids || [];
    if (activeCourseTypeFilter === "free" && !c.is_free) return false;
    if (activeCourseTypeFilter !== "all" && activeCourseTypeFilter !== "free") {
      if (!categoryIds.includes(parseInt(activeCourseTypeFilter))) return false;
    }
    if (courseListSearchQuery && !(`${c.title} ${c.description || ""}`.toLowerCase().includes(courseListSearchQuery))) return false;
    return true;
  });

  if (filtered.length === 0) {
    container.innerHTML = emptyHtml(courseListSearchQuery ? `"${courseListSearchQuery}" bo'yicha hech narsa topilmadi` : "Bu bo'limda hozircha kurs yo'q");
    return;
  }

  // Bitta kurs bir nechta guruhga tegishli bo'lishi mumkin — shuning uchun
  // har bir faol guruh o'ziga tegishli kurslarni ALOHIDA bo'lim sifatida
  // ko'rsatadi (kurs bir nechta bo'limda takrorlanishi mumkin).
  courseCategories.forEach(group => {
    const groupCourses = filtered.filter(c => (c.category_ids || []).includes(group.id));
    if (groupCourses.length === 0) return;

    const section = document.createElement("div");
    section.className = "course-group";
    section.innerHTML = `
      <div class="course-group-head">
        <div class="course-group-icon">${group.icon || "📁"}</div>
        <div class="course-group-info">
          <div class="course-group-title">${group.title}</div>
          ${group.subtitle ? `<div class="course-group-sub">${group.subtitle}</div>` : ""}
        </div>
        <div class="course-group-count">${groupCourses.length}</div>
      </div>
      <div class="course-row-list"></div>
    `;
    const listEl = section.querySelector(".course-row-list");
    groupCourses.forEach(course => listEl.appendChild(buildCourseRowCard(course)));
    container.appendChild(section);
  });

  // Hech qanday guruhga biriktirilmagan kurslar yo'qolib qolmasligi uchun
  // "Boshqa" degan qo'shimcha bo'limda ko'rsatiladi.
  const uncategorized = filtered.filter(c => (c.category_ids || []).length === 0);
  if (uncategorized.length > 0) {
    const section = document.createElement("div");
    section.className = "course-group";
    section.innerHTML = `
      <div class="course-group-head">
        <div class="course-group-icon">📁</div>
        <div class="course-group-info">
          <div class="course-group-title">Boshqa</div>
          <div class="course-group-sub">GURUHGA BIRIKTIRILMAGAN</div>
        </div>
        <div class="course-group-count">${uncategorized.length}</div>
      </div>
      <div class="course-row-list"></div>
    `;
    const listEl = section.querySelector(".course-row-list");
    uncategorized.forEach(course => listEl.appendChild(buildCourseRowCard(course)));
    container.appendChild(section);
  }
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
// (Kelajakmediklari_bot tahlili asosida — yorqin gradient hero, "Bepul
// sinab ko'ring" banneri, "Kurs rejasi" va "Paket tanlang" bilan)

let selectedTierId = null;

function buildCourseHero(course, totalLessons) {
  // Kurs guruhlari endi admin o'zi yaratgan moslashuvchan ro'yxatdan keladi
  // (course_type kabi qattiq belgilangan 2 variant o'rniga) — kurs bir
  // nechta guruhga tegishli bo'lsa, HAMMASI badge sifatida ko'rsatiladi.
  const categoryBadges = (course.categories || [])
    .map(cat => `<span class="hero-badge hero-badge-accent">${cat.icon || "📁"} ${cat.title.toUpperCase()}</span>`)
    .join("");
  const tiers = (course.pricing_tiers || []).filter(t => t.is_active);
  const thirdPill = course.is_free
    ? { num: "🔓", lbl: "Bepul kirish" }
    : { num: String(tiers.length > 0 ? tiers.length : 1), lbl: tiers.length > 1 ? "paket" : "paket" };

  return `
    <div class="course-hero">
      <div class="hero-badges">
        ${categoryBadges}
        <span class="hero-badge">${course.subject}</span>
      </div>
      <h1 class="hero-title">${course.title}</h1>
      ${course.description ? `<p class="hero-sub">${course.description}</p>` : ""}
      <div class="hero-pills">
        <div class="hero-pill"><div class="hero-pill-num">${totalLessons}</div><div class="hero-pill-lbl">ta dars</div></div>
        <div class="hero-pill"><div class="hero-pill-num">${course.duration_text || "—"}</div><div class="hero-pill-lbl">davomiyligi</div></div>
        <div class="hero-pill"><div class="hero-pill-num">${thirdPill.num}</div><div class="hero-pill-lbl">${thirdPill.lbl}</div></div>
      </div>
    </div>
  `;
}

function buildModuleList(course) {
  if (course.paragraphs.length === 0) return emptyHtml("Hozircha bo'limlar qo'shilmagan");
  let html = `<div class="section-label">KURS REJASI</div><div class="module-list">`;
  course.paragraphs.forEach((p, idx) => {
    const watchedCount = p.lessons.filter(l => l.watched).length;
    const hasAnyAccess = course.unlocked || p.lessons.some(l => !l.locked);
    const metaParts = [`${p.lessons_count} ta dars`];
    if (p.topic_count) metaParts.push(`${p.topic_count} ta mavzu`);
    if (course.unlocked) metaParts.push(`${watchedCount}/${p.lessons_count} ko'rilgan`);
    html += `
      <div class="module-item ${hasAnyAccess ? "" : "module-locked"}" data-p-id="${p.id}">
        <div class="module-num">${String(idx + 1).padStart(2, "0")}</div>
        <div class="module-info">
          <div class="module-title">${p.title}</div>
          <div class="module-meta">${metaParts.join(" · ")}</div>
        </div>
        <div class="module-arrow">${hasAnyAccess ? "›" : "🔒"}</div>
      </div>
    `;
  });
  html += `</div>`;
  return html;
}

function buildPricingSection(course) {
  const tiers = (course.pricing_tiers || []).filter(t => t.is_active);
  if (tiers.length === 0) return "";
  if (selectedTierId === null || !tiers.some(t => t.id === selectedTierId)) {
    selectedTierId = tiers[0].id;
  }
  const cards = tiers.map(t => {
    const active = t.id === selectedTierId;
    const discount = t.original_price && t.original_price > t.price
      ? `<span class="tier-discount">-${Math.round((1 - t.price / t.original_price) * 100)}%</span>` : "";
    return `
      <div class="tier-card ${active ? "tier-card-active" : ""}" data-tier-id="${t.id}">
        <div class="tier-check">${active ? "✓" : ""}</div>
        <div class="tier-info">
          <div class="tier-label">${t.label}</div>
          <div class="tier-price">${t.price.toLocaleString()} so'm
            ${t.original_price ? `<span class="tier-original">${t.original_price.toLocaleString()}</span>` : ""}
            ${discount}
          </div>
        </div>
        ${t.duration_text ? `<div class="tier-duration">⏱ ${t.duration_text}</div>` : ""}
      </div>
    `;
  }).join("");
  return `
    <div class="section-label">PAKET TANLANG</div>
    <div class="tier-list">${cards}</div>
  `;
}

export async function openCourseDetail(courseId) {
  const content = document.getElementById("detailContent");
  content.innerHTML = loadingHtml();
  showScreen("detail");
  selectedTierId = null;

  try {
    const res = await apiFetch(`/api/course/${courseId}`);
    const course = await res.json();
    currentCourse = course;
    document.getElementById("detailTitle").textContent = course.title;

    // Haqiqiy (platformadagi) darslar soni — "tugallandi" hisobi shunga
    // asoslanadi. Hero'da ko'rsatiladigan son esa admin qo'lda kiritgan
    // lessons_count qiymati (agar berilgan bo'lsa) — server shuni allaqachon
    // hisoblab course.lessons_count'ga qo'ygan (aks holda haqiqiy son bilan bir xil).
    const realLessonsTotal = course.paragraphs.reduce((a, p) => a + p.lessons_count, 0);
    const displayLessonsTotal = course.lessons_count || realLessonsTotal;
    let html = buildCourseHero(course, displayLessonsTotal);

    // "Bepul sinab ko'ring" — kurs yopiq bo'lsa-yu, admin belgilagan bepul
    // namuna darslar bo'lsa (Kelajakmediklari_bot'dagi kabi).
    const freeLessonsTotal = course.paragraphs.reduce((a, p) => a + p.lessons.filter(l => l.is_free_preview).length, 0);
    if (!course.unlocked && freeLessonsTotal > 0) {
      html += `
        <div class="free-trial-banner">
          <div class="free-trial-title">🎁 Bepul sinab ko'ring — ${freeLessonsTotal} ta dars ochiq</div>
          <div class="free-trial-sub">To'lov qilmasdan birinchi darslarni ko'ring, kurs sizga yoqsa keyin sotib oling.</div>
          <button type="button" class="free-trial-btn" id="freeTrialBtn">▶ Bepul darslarni ko'rish</button>
        </div>
      `;
    }

    if (course.unlocked && course.reason === "grace") {
      html += `<div class="grace-banner">⏳ Obuna muddatingiz tugagan. ${course.days_left <= 0 ? Math.abs(course.days_left) : 0} kundan so'ng darslar avtomatik yopiladi — obunani yangilashni unutmang.</div>`;
    }

    // Kurs 100% tugallangan bo'lsa — sertifikat yuklab olish bannerini ko'rsatamiz.
    if (course.unlocked) {
      const watchedLessons = course.paragraphs.reduce((a, p) => a + p.lessons.filter(l => l.watched).length, 0);
      const isComplete = realLessonsTotal > 0 && watchedLessons >= realLessonsTotal;
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

    html += buildModuleList(course);

    if (!course.unlocked) {
      const reasonText = course.reason === "expired"
        ? "Obuna muddatingiz tugagan. Davom ettirish uchun obunani yangilang."
        : course.required_referrals > 0
          ? `Ushbu kursni ochish uchun ${course.required_referrals} kishini taklif qiling.`
          : `Ushbu kurs pullik. To'liq kirish uchun quyidagi paketlardan birini tanlab, admin bilan bog'laning.`;

      if (course.required_referrals > 0 || course.reason === "expired") {
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
      } else {
        html += buildPricingSection(course);
        const tiers = (course.pricing_tiers || []).filter(t => t.is_active);
        const buyPrice = tiers.length > 0
          ? (tiers.find(t => t.id === selectedTierId) || tiers[0]).price
          : (course.price || 0);
        html += `
          <div class="buy-bar">
            <button type="button" class="buy-bar-btn" id="buyCourseBtn">Sotib olish · ${buyPrice.toLocaleString()} so'm ›</button>
          </div>
        `;
      }
    }

    content.innerHTML = html;

    document.querySelectorAll(".module-item").forEach(item => {
      item.addEventListener("click", () => openParagraph(parseInt(item.getAttribute("data-p-id"))));
    });

    document.querySelectorAll(".tier-card").forEach(card => {
      card.addEventListener("click", () => {
        selectedTierId = parseInt(card.getAttribute("data-tier-id"));
        openCourseDetail(courseId);
      });
    });

    const freeTrialBtn = document.getElementById("freeTrialBtn");
    if (freeTrialBtn) {
      freeTrialBtn.addEventListener("click", () => {
        const firstPreview = course.paragraphs.find(p => p.lessons.some(l => l.is_free_preview));
        if (firstPreview) openParagraph(firstPreview.id);
      });
    }

    const referralBtn = document.getElementById("lockedReferralBtn");
    if (referralBtn) referralBtn.addEventListener("click", () => navigateTo("referral"));
    const contactBtn = document.getElementById("lockedContactBtn");
    if (contactBtn) contactBtn.addEventListener("click", () => navigateTo("profile"));
    const buyBtn = document.getElementById("buyCourseBtn");
    if (buyBtn) buyBtn.addEventListener("click", () => navigateTo("profile"));

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

// Darslar "yo'lak" (ilonsimon) ko'rinishi — Kelajakmediklari_bot tahlili
// asosida: har bir dars raqamli doira, ko'rilgan bo'lsa ✓ (yashil), bepul
// namuna bo'lsa "BEPUL" belgisi, qulflangan bo'lsa 🔒 (bosilmaydi).
//
// Tugunlar CSS margin/nth-child orqali emas, ANIQ hisoblangan X/Y
// piksel koordinatalar bilan joylashtiriladi (aks holda siljish juda
// sezilarsiz bo'lib, oddiy tekis ro'yxatga o'xshab qolardi). Har bir
// juft tugun orasiga aylantirilgan (rotate) chiziqcha chizib, haqiqiy
// ilonsimon (winding) yo'lak hosil qilinadi.
const PATH_ROW_HEIGHT = 108;   // tugunlar orasidagi vertikal masofa (px)
const PATH_CIRCLE_SIZE = 60;   // doira diametri (px) — CSS .path-circle bilan mos
const PATH_TOP_PADDING = 24;   // "BOSHLASH" belgisi kesilib qolmasligi uchun yuqori bo'shliq
// Markazdan chapga/o'ngga siljish naqshi (px) — davriy to'lqin hosil qiladi.
const PATH_OFFSET_PATTERN = [0, 58, 82, 58, 0, -58, -82, -58];

function buildLessonPathHtml(paragraph) {
  const lessons = paragraph.lessons;
  const nextIndex = lessons.findIndex(l => !l.locked && !l.watched);
  const totalHeight = PATH_TOP_PADDING + (lessons.length - 1) * PATH_ROW_HEIGHT + PATH_CIRCLE_SIZE + 50;

  let connectorsHtml = "";
  let nodesHtml = "";

  lessons.forEach((lesson, idx) => {
    const offset = PATH_OFFSET_PATTERN[idx % PATH_OFFSET_PATTERN.length];
    const top = PATH_TOP_PADDING + idx * PATH_ROW_HEIGHT;
    const centerY = top + PATH_CIRCLE_SIZE / 2;

    if (idx > 0) {
      const prevOffset = PATH_OFFSET_PATTERN[(idx - 1) % PATH_OFFSET_PATTERN.length];
      const prevCenterY = PATH_TOP_PADDING + (idx - 1) * PATH_ROW_HEIGHT + PATH_CIRCLE_SIZE / 2;
      const dx = offset - prevOffset;
      const dy = centerY - prevCenterY;
      const length = Math.sqrt(dx * dx + dy * dy);
      const angle = Math.atan2(dy, dx) * (180 / Math.PI);
      connectorsHtml += `<div class="path-connector" style="left:calc(50% + ${prevOffset}px); top:${prevCenterY}px; width:${length}px; transform: rotate(${angle}deg);"></div>`;
    }

    const isNext = idx === nextIndex;
    const circleCls = lesson.locked
      ? "path-circle-locked"
      : lesson.watched
        ? "path-circle-watched"
        : isNext
          ? "path-circle-current"
          : "path-circle-open";
    const circleContent = lesson.locked ? "🔒" : lesson.watched ? "✓" : (idx + 1);
    const freeBadge = (!currentCourse.unlocked && lesson.is_free_preview) ? `<span class="path-badge">BEPUL</span>` : "";

    nodesHtml += `
      <div class="path-node" data-lesson-id="${lesson.id}" data-locked="${lesson.locked ? "1" : "0"}" style="left:calc(50% + ${offset}px); top:${top}px;">
        ${isNext ? `<div class="path-start-tag">BOSHLASH</div>` : ""}
        <div class="path-circle ${circleCls}">
          ${freeBadge}
          <span>${circleContent}</span>
        </div>
        <div class="path-node-label">${lesson.title}</div>
      </div>
    `;
  });

  return `<div class="lesson-path" style="height:${totalHeight}px;">${connectorsHtml}${nodesHtml}</div>`;
}

export function openParagraph(paragraphId) {
  const p = currentCourse.paragraphs.find(x => x.id === paragraphId);
  if (!p) return;
  currentParagraph = p;
  document.getElementById("paragraphTitle").textContent = p.title;

  const content = document.getElementById("paragraphContent");
  const watchedCount = p.lessons.filter(l => l.watched).length;
  const total = p.lessons.length;
  const percent = total > 0 ? Math.round((watchedCount / total) * 100) : 0;

  let html = `
    <div class="path-progress-box">
      <div class="path-progress-top">
        <span>Umumiy progress</span>
        <span>${watchedCount}/${total} · ${percent}%</span>
      </div>
      <div class="score-bar-track"><div class="score-bar-fill" style="width:${percent}%"></div></div>
    </div>
  `;

  if (total === 0) {
    html += emptyHtml("Bu bo'limda hozircha video yo'q");
  } else {
    html += buildLessonPathHtml(p);
  }
  content.innerHTML = html;

  document.querySelectorAll(".path-node").forEach(item => {
    item.addEventListener("click", () => {
      if (item.getAttribute("data-locked") === "1") {
        showToast("🔒 Bu dars qulflangan — kursni sotib olgandan so'ng ochiladi");
        return;
      }
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
  // Oldingi/keyingi tugmalari yoki klaviatura orqali qulflangan darsga
  // o'tib qolinmasin (masalan bepul namunadan keyingi dars yopiq bo'lsa).
  if (lesson.locked) {
    showToast("🔒 Bu dars qulflangan — kursni sotib olgandan so'ng ochiladi");
    if (currentParagraph) openParagraph(currentParagraph.id);
    return;
  }
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

// Talaba video ko'rayotganda boshqa ekranga o'tsa (bosh sahifa, profil va
// h.k.), video FONDA ijro etilishda davom etib qolmasligi kerak — YouTube
// iframe/<video> DOM'dan olib tashlanmasa ham, ko'rinmas holda ovoz
// chiqarishda davom etadi. Shuning uchun "lesson" ekranidan BOSHQA istalgan
// ekranga o'tilganda pleyerni to'xtatamiz (iframe src'ini bo'shatib,
// <video> uchun pause() chaqirib).
function stopLessonVideo() {
  const content = document.getElementById("lessonContent");
  if (!content) return;
  const iframe = content.querySelector("iframe");
  if (iframe && iframe.src && iframe.src !== "about:blank") iframe.src = "about:blank";
  const video = content.querySelector("video");
  if (video) video.pause();
}

document.addEventListener("app:screenchanged", (e) => {
  if (e.detail && e.detail.name !== "lesson") stopLessonVideo();
});
