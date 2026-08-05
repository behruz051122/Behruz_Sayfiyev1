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

export function setListType(type) {
  currentListType = type;
  activeStatusFilter = "all";
  activeSubjectFilter = "Hammasi";
  searchQuery = "";
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
  } catch (e) {
    console.error(e);
    content.innerHTML = errorHtml();
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
