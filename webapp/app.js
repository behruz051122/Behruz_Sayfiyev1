// app.js — Mini App logikasi (v3.0)

const tg = window.Telegram.WebApp;
tg.expand();

const tgUser = tg.initDataUnsafe?.user || { id: 0, first_name: "Mehmon" };
const API_BASE = window.location.origin;

let currentListType = "course"; // 'course' yoki 'book'
let currentCourseId = null;
let allCourses = [];
let activeStatusFilter = "all";
let activeSubjectFilter = "Hammasi";

// ---------- Navigatsiya ----------

function showScreen(name) {
  document.querySelectorAll(".screen").forEach(s => s.classList.add("hidden"));
  document.getElementById("screen-" + name).classList.remove("hidden");

  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
  const navMap = { home: 0, courses: 1, referral: 2, books: 3 };
  const navBtns = document.querySelectorAll(".nav-item");
  if (name === "list") {
    const idx = currentListType === "book" ? navMap.books : navMap.courses;
    navBtns[idx]?.classList.add("active");
  } else if (navMap[name] !== undefined) {
    navBtns[navMap[name]].classList.add("active");
  }
}

document.querySelectorAll("[data-nav]").forEach(el => {
  el.addEventListener("click", () => {
    const target = el.getAttribute("data-nav");
    handleNav(target);
  });
});

function handleNav(target) {
  if (target === "home") {
    showScreen("home");
  } else if (target === "courses") {
    currentListType = "course";
    activeStatusFilter = "all";
    activeSubjectFilter = "Hammasi";
    document.getElementById("listTitle").textContent = "Kurslar";
    loadCourseList();
    showScreen("list");
  } else if (target === "books") {
    currentListType = "book";
    activeStatusFilter = "all";
    activeSubjectFilter = "Hammasi";
    document.getElementById("listTitle").textContent = "Kitoblar";
    loadCourseList();
    showScreen("list");
  } else if (target === "referral") {
    loadReferral();
    showScreen("referral");
  } else if (target === "back-to-list") {
    showScreen("list");
  } else if (target === "admin") {
    loadAdminCourses();
    showScreen("admin");
  }
}

// ---------- Ma'lumot yuklash ----------

async function loadBrand() {
  try {
    const res = await fetch(`${API_BASE}/api/brand`);
    const data = await res.json();
    document.getElementById("brandName").textContent = data.brand_name;
    document.getElementById("brandSub").textContent = data.brand_sub;
  } catch (e) { console.error(e); }
}

async function loadUser() {
  try {
    const res = await fetch(`${API_BASE}/api/user?telegram_id=${tgUser.id}&first_name=${encodeURIComponent(tgUser.first_name)}`);
    const user = await res.json();
    document.getElementById("helloName").textContent = `${user.first_name}, salom 👋`;
    document.getElementById("pointsBadge").textContent = `⚡ ${user.points}`;
    document.getElementById("coinsBadge").textContent = `🪙 ${user.coins}`;
  } catch (e) { console.error(e); }
}

async function loadCourseList() {
  const container = document.getElementById("courseList");
  container.innerHTML = `<div style="color:var(--text-dim);padding:20px;text-align:center;">Yuklanmoqda...</div>`;
  try {
    const res = await fetch(`${API_BASE}/api/courses?resource_type=${currentListType}&telegram_id=${tgUser.id}`);
    const data = await res.json();
    allCourses = data.courses;
    buildSubjectFilters();
    bindStatusFilters();
    renderCourseList();
  } catch (e) {
    console.error(e);
    container.innerHTML = `<div style="color:var(--text-dim);padding:20px;">Xatolik yuz berdi</div>`;
  }
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
    return true;
  });

  if (filtered.length === 0) {
    container.innerHTML = `<div style="color:var(--text-dim);padding:20px;text-align:center;">Bu bo'limda hozircha hech narsa yo'q</div>`;
    return;
  }

  filtered.forEach(course => {
    const card = document.createElement("div");
    card.className = "course-card" + (course.unlocked ? "" : " locked-card");
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
        ${course.unlocked
          ? `<div class="unlock-badge">✅ Ochiq</div>`
          : `<div class="lock-badge">🔒 ${course.user_referrals}/${course.required_referrals} taklif</div>`}
      </div>
    `;
    card.addEventListener("click", () => openCourseDetail(course.id));
    container.appendChild(card);
  });
}

async function openCourseDetail(courseId) {
  currentCourseId = courseId;
  const content = document.getElementById("detailContent");
  content.innerHTML = `<div style="color:var(--text-dim);padding:20px;text-align:center;">Yuklanmoqda...</div>`;
  showScreen("detail");

  try {
    const res = await fetch(`${API_BASE}/api/course/${courseId}?telegram_id=${tgUser.id}`);
    const course = await res.json();
    document.getElementById("detailTitle").textContent = course.title;

    let html = `
      <div class="detail-hero">
        <span class="course-tag">${course.subject}</span>
        <h1>${course.title}</h1>
        <p>${course.description || ""}</p>
      </div>
      <div class="stat-boxes">
        <div class="stat-box"><div class="num">${course.lessons.length || "—"}</div><div class="lbl">ta dars</div></div>
        <div class="stat-box"><div class="num">${course.duration_text || "—"}</div><div class="lbl">muddat</div></div>
        <div class="stat-box"><div class="num">${course.unlocked ? "🔓" : "🔒"}</div><div class="lbl">${course.unlocked ? "Ochiq" : "Yopiq"}</div></div>
      </div>
    `;

    if (course.unlocked) {
      html += `<div class="lesson-list">`;
      if (course.lessons.length === 0) {
        html += `<div style="color:var(--text-dim);padding:10px;">Hozircha darslar qo'shilmagan</div>`;
      } else {
        course.lessons.forEach((lesson, idx) => {
          html += `
            <div class="lesson-item" data-lesson-id="${lesson.id}">
              <div class="lesson-num">${idx + 1}</div>
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
          const lessonId = item.getAttribute("data-lesson-id");
          const lesson = course.lessons.find(l => String(l.id) === lessonId);
          playLesson(lesson, course);
        });
      });
    } else {
      html += `
        <div class="locked-box">
          <div class="lock-emoji">🔒</div>
          <h3>Bu kurs hali yopiq</h3>
          <p>Ushbu kursni ochish uchun ${course.required_referrals} kishini taklif qiling va ular kanalimizga obuna bo'lishi kerak.</p>
          <div class="progress-text">${course.user_referrals} / ${course.required_referrals} taklif</div>
          <button class="gold-btn" onclick="handleNav('referral')">Do'stlarni taklif qilish</button>
        </div>
      `;
      content.innerHTML = html;
    }
  } catch (e) {
    console.error(e);
    content.innerHTML = `<div style="color:var(--text-dim);padding:20px;">Xatolik yuz berdi</div>`;
  }
}

function playLesson(lesson, course) {
  const content = document.getElementById("detailContent");
  document.getElementById("detailTitle").textContent = lesson.title;

  let videoHtml = "";
  const url = lesson.video_url || "";
  const isYoutube = url.includes("youtube.com") || url.includes("youtu.be");

  if (isYoutube) {
    let videoId = "";
    if (url.includes("youtu.be/")) videoId = url.split("youtu.be/")[1].split("?")[0];
    else if (url.includes("watch?v=")) videoId = url.split("watch?v=")[1].split("&")[0];
    else if (url.includes("/embed/")) videoId = url.split("/embed/")[1].split("?")[0];

    // rel=0 va modestbranding=1 — video tugagach faqat shu kanaldan tavsiya chiqadi,
    // youtube-nocookie domeni orqali chalg'ituvchi tavsiyalar yanada kamayadi.
    const embedUrl = `https://www.youtube-nocookie.com/embed/${videoId}?rel=0&modestbranding=1&playsinline=1`;
    videoHtml = `
      <div class="video-wrap" id="videoWrap">
        <iframe src="${embedUrl}"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen"
          allowfullscreen></iframe>
        <button class="fullscreen-btn" id="fullscreenBtn">⛶</button>
      </div>`;
  } else if (url) {
    videoHtml = `
      <div class="video-wrap" id="videoWrap">
        <video src="${url}" controls playsinline></video>
        <button class="fullscreen-btn" id="fullscreenBtn">⛶</button>
      </div>`;
  } else {
    videoHtml = `<div class="locked-box"><p>Video manzili kiritilmagan</p></div>`;
  }

  content.innerHTML = `
    ${videoHtml}
    <div class="detail-hero">
      <h1>${lesson.title}</h1>
      <p>${lesson.description || ""}</p>
    </div>
    <div style="margin:0 16px;">
      <button class="gold-btn" onclick="openCourseDetail(${course.id})">← Darslar ro'yxatiga qaytish</button>
    </div>
  `;

  const fsBtn = document.getElementById("fullscreenBtn");
  if (fsBtn) {
    fsBtn.addEventListener("click", () => {
      const wrap = document.getElementById("videoWrap");
      if (wrap.requestFullscreen) wrap.requestFullscreen();
      else if (wrap.webkitRequestFullscreen) wrap.webkitRequestFullscreen();
    });
  }
}

async function loadReferral() {
  try {
    const res = await fetch(`${API_BASE}/api/referral-link?telegram_id=${tgUser.id}`);
    const data = await res.json();
    document.getElementById("referralCount").textContent = data.confirmed_referrals;
    document.getElementById("referralLinkInput").value = data.link;

    document.getElementById("copyLinkBtn").onclick = () => {
      navigator.clipboard.writeText(data.link);
      tg.showAlert ? tg.showAlert("Havola nusxalandi!") : alert("Havola nusxalandi!");
    };

    document.getElementById("shareLinkBtn").onclick = () => {
      const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(data.link)}&text=${encodeURIComponent("Menga qo'shiling!")}`;
      tg.openTelegramLink ? tg.openTelegramLink(shareUrl) : window.open(shareUrl, "_blank");
    };

    const listBox = document.getElementById("referralFriendsList");
    listBox.innerHTML = "";
    if (data.referrals && data.referrals.length > 0) {
      data.referrals.forEach(r => {
        const row = document.createElement("div");
        row.className = "referral-friend-row";
        row.innerHTML = `
          <span>${r.first_name || "Foydalanuvchi"}</span>
          <span class="${r.confirmed ? "status-yes" : "status-no"}">${r.confirmed ? "✅ Tasdiqlangan" : "⏳ Kutilmoqda"}</span>
        `;
        listBox.appendChild(row);
      });
    }
  } catch (e) { console.error(e); }
}

// ---------- ADMIN (Mini App ichida) ----------

let isAdmin = false;
let currentAdminCourses = [];

function adminHeaders() {
  return { "Content-Type": "application/json", "X-Telegram-Id": String(tgUser.id) };
}

async function checkIsAdmin() {
  try {
    const res = await fetch(`${API_BASE}/api/is-admin?telegram_id=${tgUser.id}`);
    const data = await res.json();
    isAdmin = data.is_admin;
    if (isAdmin) {
      document.getElementById("adminGearBtn").classList.remove("hidden");
    }
  } catch (e) { console.error(e); }
}

async function loadAdminCourses() {
  document.getElementById("adminCourseForm").classList.add("hidden");
  document.getElementById("adminLessonsPanel").classList.add("hidden");
  const box = document.getElementById("adminCoursesList");
  box.innerHTML = `<div style="color:var(--text-dim);font-size:12px;">Yuklanmoqda...</div>`;
  try {
    const res = await fetch(`${API_BASE}/api/admin/courses`, { headers: adminHeaders() });
    const data = await res.json();
    currentAdminCourses = data.courses;
    box.innerHTML = "";
    currentAdminCourses.forEach(c => {
      const row = document.createElement("div");
      row.className = "admin-row";
      row.innerHTML = `
        <div class="emoji">${c.thumbnail_emoji || "📘"}</div>
        <div class="info">
          <div class="t">${c.title}${c.is_active ? "" : " (yashirin)"}</div>
          <div class="s">${c.subject} · ${c.resource_type === "book" ? "Kitob" : "Kurs"} · ${c.lessons_count} dars · ${c.is_free ? "Bepul" : c.required_referrals + " taklif"}</div>
        </div>
        <div class="row-actions">
          <button data-a="lessons">Darslar</button>
          <button data-a="edit">Tahrirlash</button>
          <button data-a="delete" class="danger">O'chirish</button>
        </div>
      `;
      row.querySelector('[data-a="lessons"]').onclick = () => openAdminLessons(c.id, c.title);
      row.querySelector('[data-a="edit"]').onclick = () => openAdminCourseForm(c);
      row.querySelector('[data-a="delete"]').onclick = () => deleteAdminCourse(c.id);
      box.appendChild(row);
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = `<div style="color:var(--text-dim);">Xatolik yuz berdi</div>`;
  }
}

document.getElementById("adminNewCourseBtn").addEventListener("click", () => openAdminCourseForm(null));
document.getElementById("adminCloseCourseForm").addEventListener("click", () => {
  document.getElementById("adminCourseForm").classList.add("hidden");
});

function openAdminCourseForm(course) {
  document.getElementById("adminCourseForm").classList.remove("hidden");
  document.getElementById("adminLessonsPanel").classList.add("hidden");
  document.getElementById("adminCourseFormTitle").textContent = course ? "Kursni tahrirlash" : "Yangi kurs";
  document.getElementById("ac_id").value = course ? course.id : "";
  document.getElementById("ac_title").value = course ? course.title : "";
  document.getElementById("ac_subject").value = course ? course.subject : "";
  document.getElementById("ac_resource_type").value = course ? course.resource_type : "course";
  document.getElementById("ac_description").value = course ? (course.description || "") : "";
  document.getElementById("ac_is_free").value = course ? String(course.is_free) : "1";
  document.getElementById("ac_required_referrals").value = course ? course.required_referrals : 0;
  document.getElementById("ac_students_count").value = course ? (course.students_count || 0) : 0;
  document.getElementById("ac_duration_text").value = course ? (course.duration_text || "") : "";
  document.getElementById("ac_thumbnail_emoji").value = course ? (course.thumbnail_emoji || "📘") : "📘";
  document.getElementById("ac_order_num").value = course ? course.order_num : 0;
  document.getElementById("ac_is_active").value = course ? String(course.is_active) : "1";
}

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
    students_count: parseInt(document.getElementById("ac_students_count").value),
    duration_text: document.getElementById("ac_duration_text").value,
    thumbnail_emoji: document.getElementById("ac_thumbnail_emoji").value,
    order_num: parseInt(document.getElementById("ac_order_num").value),
    is_active: parseInt(document.getElementById("ac_is_active").value)
  };
  if (id) {
    await fetch(`${API_BASE}/api/admin/courses/${id}`, { method: "PUT", headers: adminHeaders(), body: JSON.stringify(data) });
  } else {
    await fetch(`${API_BASE}/api/admin/courses`, { method: "POST", headers: adminHeaders(), body: JSON.stringify(data) });
  }
  document.getElementById("adminCourseForm").classList.add("hidden");
  loadAdminCourses();
});

async function deleteAdminCourse(id) {
  if (!confirm("Bu kursni butunlay o'chirmoqchimisiz? Barcha darslar ham o'chadi.")) return;
  await fetch(`${API_BASE}/api/admin/courses/${id}`, { method: "DELETE", headers: adminHeaders() });
  loadAdminCourses();
}

document.getElementById("adminCloseLessons").addEventListener("click", () => {
  document.getElementById("adminLessonsPanel").classList.add("hidden");
});

async function openAdminLessons(courseId, title) {
  document.getElementById("adminLessonsPanel").classList.remove("hidden");
  document.getElementById("adminCourseForm").classList.add("hidden");
  document.getElementById("adminLessonsTitle").textContent = `Darslar — ${title}`;
  document.getElementById("al_course_id").value = courseId;
  document.getElementById("al_id").value = "";
  document.getElementById("al_title").value = "";
  document.getElementById("al_video_url").value = "";
  document.getElementById("al_description").value = "";
  document.getElementById("al_order_num").value = 0;
  await renderAdminLessons(courseId);
}

async function renderAdminLessons(courseId) {
  const res = await fetch(`${API_BASE}/api/admin/courses/${courseId}/lessons`, { headers: adminHeaders() });
  const data = await res.json();
  const box = document.getElementById("adminLessonsList");
  box.innerHTML = "";
  if (data.lessons.length === 0) {
    box.innerHTML = `<div style="color:var(--text-dim);font-size:11px;">Hali dars qo'shilmagan</div>`;
  }
  data.lessons.forEach((l, idx) => {
    const row = document.createElement("div");
    row.className = "admin-row";
    row.innerHTML = `
      <div class="info"><div class="t">${idx + 1}. ${l.title}</div></div>
      <div class="row-actions">
        <button data-a="edit">Tahrirlash</button>
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
      if (!confirm("Bu darsni o'chirmoqchimisiz?")) return;
      await fetch(`${API_BASE}/api/admin/lessons/${l.id}`, { method: "DELETE", headers: adminHeaders() });
      renderAdminLessons(courseId);
      loadAdminCourses();
    };
    box.appendChild(row);
  });
}

document.getElementById("lessonFormEl").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("al_id").value;
  const courseId = document.getElementById("al_course_id").value;
  const data = {
    course_id: parseInt(courseId),
    title: document.getElementById("al_title").value,
    video_url: document.getElementById("al_video_url").value,
    description: document.getElementById("al_description").value,
    order_num: parseInt(document.getElementById("al_order_num").value)
  };
  if (id) {
    await fetch(`${API_BASE}/api/admin/lessons/${id}`, { method: "PUT", headers: adminHeaders(), body: JSON.stringify(data) });
  } else {
    await fetch(`${API_BASE}/api/admin/lessons`, { method: "POST", headers: adminHeaders(), body: JSON.stringify(data) });
  }
  document.getElementById("al_id").value = "";
  document.getElementById("al_title").value = "";
  document.getElementById("al_video_url").value = "";
  document.getElementById("al_description").value = "";
  document.getElementById("al_order_num").value = 0;
  renderAdminLessons(courseId);
  loadAdminCourses();
});

// ---------- Boshlanish ----------

loadBrand();
loadUser();
checkIsAdmin();
showScreen("home");
