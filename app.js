// app.js — Mini App logikasi (v4.0 — paragraf tuzilishi, coin, reyting, obuna)

const tg = window.Telegram.WebApp;
tg.expand();

const tgUser = tg.initDataUnsafe?.user || { id: 0, first_name: "Mehmon" };
const API_BASE = window.location.origin;

let currentListType = "course";
let currentCourse = null;
let currentParagraph = null;
let currentLesson = null;
let allCourses = [];
let activeStatusFilter = "all";
let activeSubjectFilter = "Hammasi";
let botUsername = "";
let adminContact = "";

// ---------- Navigatsiya ----------

function showScreen(name) {
  document.querySelectorAll(".screen").forEach(s => s.classList.add("hidden"));
  document.getElementById("screen-" + name).classList.remove("hidden");

  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
  const navMap = { home: 0, courses: 1, tests: 2, leaderboard: 3, profile: 4 };
  const navBtns = document.querySelectorAll(".nav-item");
  if (navMap[name] !== undefined) navBtns[navMap[name]].classList.add("active");
}

document.querySelectorAll("[data-nav]").forEach(el => {
  el.addEventListener("click", () => handleNav(el.getAttribute("data-nav")));
});

function handleNav(target) {
  if (target === "home") showScreen("home");
  else if (target === "courses") {
    currentListType = "course"; activeStatusFilter = "all"; activeSubjectFilter = "Hammasi";
    document.getElementById("listTitle").textContent = "Kurslar";
    loadCourseList(); showScreen("list");
  } else if (target === "books") {
    currentListType = "book"; activeStatusFilter = "all"; activeSubjectFilter = "Hammasi";
    document.getElementById("listTitle").textContent = "Kitoblar";
    loadCourseList(); showScreen("list");
  } else if (target === "referral") { loadReferral(); showScreen("referral"); }
  else if (target === "tests") { showScreen("tests"); }
  else if (target === "leaderboard") { loadLeaderboard(); showScreen("leaderboard"); }
  else if (target === "profile") { loadProfile(); showScreen("profile"); }
  else if (target === "back-to-list") showScreen("list");
  else if (target === "back-to-course") openCourseDetail(currentCourse.id);
  else if (target === "back-to-paragraph") openParagraph(currentParagraph.id);
  else if (target === "admin") { loadAdminCourses(); showScreen("admin"); }
}

// ---------- Brand / user ----------

async function loadBrand() {
  try {
    const res = await fetch(`${API_BASE}/api/brand`);
    const data = await res.json();
    document.getElementById("brandName").textContent = data.brand_name;
    document.getElementById("brandSub").textContent = data.brand_sub;
    botUsername = data.bot_username || "";
    adminContact = data.admin_contact || "";
  } catch (e) { console.error(e); }
}

async function loadUser() {
  try {
    const res = await fetch(`${API_BASE}/api/user?telegram_id=${tgUser.id}&first_name=${encodeURIComponent(tgUser.first_name)}`);
    const user = await res.json();
    document.getElementById("helloName").textContent = `${user.first_name}, salom 👋`;
    document.getElementById("coinsBadge").textContent = `🪙 ${user.coins}`;
  } catch (e) { console.error(e); }
}

async function refreshCoins() {
  const res = await fetch(`${API_BASE}/api/user?telegram_id=${tgUser.id}&first_name=${encodeURIComponent(tgUser.first_name)}`);
  const user = await res.json();
  document.getElementById("coinsBadge").textContent = `🪙 ${user.coins}`;
}

// ---------- Kurslar ro'yxati ----------

async function loadCourseList() {
  const container = document.getElementById("courseList");
  container.innerHTML = `<div class="empty-msg">Yuklanmoqda...</div>`;
  try {
    const res = await fetch(`${API_BASE}/api/courses?resource_type=${currentListType}&telegram_id=${tgUser.id}`);
    const data = await res.json();
    allCourses = data.courses;
    buildSubjectFilters();
    bindStatusFilters();
    renderCourseList();
  } catch (e) {
    console.error(e);
    container.innerHTML = `<div class="empty-msg">Xatolik yuz berdi</div>`;
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
    container.innerHTML = `<div class="empty-msg">Bu bo'limda hozircha hech narsa yo'q</div>`;
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

async function openCourseDetail(courseId) {
  const content = document.getElementById("detailContent");
  content.innerHTML = `<div class="empty-msg">Yuklanmoqda...</div>`;
  showScreen("detail");

  try {
    const res = await fetch(`${API_BASE}/api/course/${courseId}?telegram_id=${tgUser.id}`);
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
        html += `<div class="empty-msg">Hozircha bo'limlar qo'shilmagan</div>`;
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
          ${course.required_referrals > 0 ? `<button class="gold-btn" onclick="handleNav('referral')">Do'stlarni taklif qilish</button>` : `<button class="gold-btn" onclick="handleNav('profile')">Admin bilan bog'lanish</button>`}
        </div>
      `;
    }

    content.innerHTML = html;

    document.querySelectorAll(".paragraph-item").forEach(item => {
      item.addEventListener("click", () => openParagraph(parseInt(item.getAttribute("data-p-id"))));
    });
  } catch (e) {
    console.error(e);
    content.innerHTML = `<div class="empty-msg">Xatolik yuz berdi</div>`;
  }
}

// ---------- Paragraf ichi (10 tadan video) ----------

function openParagraph(paragraphId) {
  const p = currentCourse.paragraphs.find(x => x.id === paragraphId);
  if (!p) return;
  currentParagraph = p;
  document.getElementById("paragraphTitle").textContent = p.title;

  const content = document.getElementById("paragraphContent");
  let html = `<div class="lesson-list">`;
  if (p.lessons.length === 0) {
    html += `<div class="empty-msg">Bu bo'limda hozircha video yo'q</div>`;
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

  let videoHtml = "";
  const url = (lesson.video_url || "").trim();
  const isYoutube = url.includes("youtube.com") || url.includes("youtu.be");

  if (isYoutube) {
    const videoId = extractYoutubeId(url);
    if (!videoId) {
      videoHtml = `
        <div class="locked-box">
          <p>Bu videoni to'g'ridan-to'g'ri ko'rsatib bo'lmadi.</p>
          <button class="gold-btn" onclick="window.open('${url}', '_blank')">▶ YouTube'da ochish</button>
        </div>`;
    } else {
      const embedUrl = `https://www.youtube-nocookie.com/embed/${videoId}?rel=0&modestbranding=1&playsinline=1`;
      videoHtml = `
        <div class="video-wrap" id="videoWrap">
          <iframe src="${embedUrl}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen" allowfullscreen></iframe>
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
    <div class="detail-hero">
      <h1>${lesson.title}</h1>
      <p>${lesson.description || ""}</p>
    </div>
    <div style="margin:0 16px;" id="watchedBtnWrap">
      ${lesson.watched
        ? `<div class="watched-confirmed">✓ Bu dars ko'rildi — coin qo'shildi</div>`
        : `<button class="gold-btn" id="markWatchedBtn">✓ Ko'rib bo'ldim (+1 🪙)</button>`}
    </div>
  `;

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
        const res = await fetch(`${API_BASE}/api/lesson/${lesson.id}/watched`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ telegram_id: tgUser.id })
        });
        const data = await res.json();
        lesson.watched = true;
        document.getElementById("watchedBtnWrap").innerHTML = `<div class="watched-confirmed">✓ Bu dars ko'rildi — coin qo'shildi</div>`;
        refreshCoins();
        if (data.coin_awarded) {
          tg.showAlert ? tg.showAlert("🎉 Tabriklaymiz! +1 coin oldingiz") : null;
        }
      } catch (e) {
        console.error(e);
        markBtn.disabled = false;
        markBtn.textContent = "✓ Ko'rib bo'ldim (+1 🪙)";
      }
    });
  }

  showScreen("lesson");
}

// ---------- Referal ----------

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
    (data.referrals || []).forEach(r => {
      const row = document.createElement("div");
      row.className = "referral-friend-row";
      row.innerHTML = `<span>${r.first_name || "Foydalanuvchi"}</span><span class="${r.confirmed ? "status-yes" : "status-no"}">${r.confirmed ? "✅ Tasdiqlangan" : "⏳ Kutilmoqda"}</span>`;
      listBox.appendChild(row);
    });
  } catch (e) { console.error(e); }
}

// ---------- Reyting (Natijalar) ----------

async function loadLeaderboard() {
  const box = document.getElementById("leaderboardList");
  const rankBox = document.getElementById("myRankBox");
  box.innerHTML = `<div class="empty-msg">Yuklanmoqda...</div>`;
  try {
    const res = await fetch(`${API_BASE}/api/leaderboard?telegram_id=${tgUser.id}`);
    const data = await res.json();
    rankBox.innerHTML = `<div class="my-rank-label">Sizning o'rningiz</div><div class="my-rank-num">#${data.my_rank || "—"}</div>`;

    box.innerHTML = "";
    if (data.leaderboard.length === 0) {
      box.innerHTML = `<div class="empty-msg">Hali hech kim coin to'plamagan — birinchi bo'ling!</div>`;
      return;
    }
    data.leaderboard.forEach((u, idx) => {
      const rank = idx + 1;
      let medal = `<span class="rank-num">${rank}</span>`;
      if (rank === 1) medal = `<span class="rank-medal gold-medal">👑</span>`;
      else if (rank === 2) medal = `<span class="rank-medal silver-medal">🥈</span>`;
      else if (rank === 3) medal = `<span class="rank-medal bronze-medal">🥉</span>`;

      const row = document.createElement("div");
      row.className = "leaderboard-row" + (rank <= 3 ? " top-rank" : "");
      row.innerHTML = `
        ${medal}
        <span class="lb-name">${u.first_name || "Foydalanuvchi"}</span>
        <span class="lb-coins">🪙 ${u.coins}</span>
      `;
      box.appendChild(row);
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = `<div class="empty-msg">Xatolik yuz berdi</div>`;
  }
}

// ---------- Profil ----------

async function loadProfile() {
  const content = document.getElementById("profileContent");
  content.innerHTML = `<div class="empty-msg">Yuklanmoqda...</div>`;
  try {
    const [userRes, enrollRes] = await Promise.all([
      fetch(`${API_BASE}/api/user?telegram_id=${tgUser.id}&first_name=${encodeURIComponent(tgUser.first_name)}`),
      fetch(`${API_BASE}/api/my-enrollments?telegram_id=${tgUser.id}`)
    ]);
    const user = await userRes.json();
    const enrollData = await enrollRes.json();

    let html = `
      <div class="profile-card">
        <div class="profile-avatar">${(user.first_name || "?").charAt(0).toUpperCase()}</div>
        <div class="profile-name">${user.first_name}</div>
        <div class="profile-id">Telegram ID: ${user.telegram_id}</div>
        <div class="profile-stats-row">
          <div class="profile-stat"><div class="num">🪙 ${user.coins}</div><div class="lbl">Coin</div></div>
          <div class="profile-stat"><div class="num">#${user.rank || "—"}</div><div class="lbl">Reyting</div></div>
          <div class="profile-stat"><div class="num">${user.confirmed_referrals}</div><div class="lbl">Takliflar</div></div>
        </div>
      </div>

      <div class="admin-section">
        <div class="admin-section-head"><h3>Mening obunalarim</h3></div>
    `;

    if (enrollData.enrollments.length === 0) {
      html += `<div class="empty-msg">Hali pullik kursga obuna emassiz</div>`;
    } else {
      enrollData.enrollments.forEach(e => {
        let expiryText = "Muddatsiz";
        if (e.expiry_date) {
          const expiry = new Date(e.expiry_date + "Z");
          const now = new Date();
          const daysLeft = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24));
          expiryText = daysLeft >= 0 ? `${daysLeft} kun qoldi` : `${Math.abs(daysLeft)} kun oldin tugagan`;
        }
        html += `
          <div class="admin-row">
            <div class="emoji">${e.thumbnail_emoji || "📘"}</div>
            <div class="info"><div class="t">${e.title}</div><div class="s">${e.subject} · ${expiryText}</div></div>
          </div>
        `;
      });
    }

    html += `</div>
      <div class="admin-section">
        <div class="admin-section-head"><h3>Yordam va aloqa</h3></div>
        <p style="font-size:12px;color:var(--text-dim);">Savol yoki muammo bo'lsa, admin bilan bog'laning.</p>
        <button class="gold-btn" style="margin-top:10px;" id="contactAdminBtn">💬 Admin bilan bog'lanish</button>
      </div>
    `;

    content.innerHTML = html;

    const contactBtn = document.getElementById("contactAdminBtn");
    if (contactBtn) {
      contactBtn.addEventListener("click", () => {
        const url = `https://t.me/${adminContact}`;
        tg.openTelegramLink ? tg.openTelegramLink(url) : window.open(url, "_blank");
      });
    }
  } catch (e) {
    console.error(e);
    content.innerHTML = `<div class="empty-msg">Xatolik yuz berdi</div>`;
  }
}

// ---------- ADMIN ----------

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
    if (isAdmin) document.getElementById("adminGearBtn").classList.remove("hidden");
  } catch (e) { console.error(e); }
}

async function loadAdminCourses() {
  document.getElementById("adminCourseForm").classList.add("hidden");
  document.getElementById("adminParagraphsPanel").classList.add("hidden");
  document.getElementById("adminLessonsPanel").classList.add("hidden");
  const box = document.getElementById("adminCoursesList");
  box.innerHTML = `<div class="empty-msg">Yuklanmoqda...</div>`;
  try {
    const res = await fetch(`${API_BASE}/api/admin/courses`, { headers: adminHeaders() });
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
    box.innerHTML = `<div class="empty-msg">Xatolik yuz berdi</div>`;
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

document.getElementById("adminNewCourseBtn").addEventListener("click", () => openAdminCourseForm(null));
document.getElementById("adminCloseCourseForm").addEventListener("click", () => document.getElementById("adminCourseForm").classList.add("hidden"));

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
  if (id) await fetch(`${API_BASE}/api/admin/courses/${id}`, { method: "PUT", headers: adminHeaders(), body: JSON.stringify(data) });
  else await fetch(`${API_BASE}/api/admin/courses`, { method: "POST", headers: adminHeaders(), body: JSON.stringify(data) });
  document.getElementById("adminCourseForm").classList.add("hidden");
  loadAdminCourses();
});

async function deleteAdminCourse(id) {
  if (!confirm("Bu kursni butunlay o'chirmoqchimisiz? Barcha bo'lim va darslar ham o'chadi.")) return;
  await fetch(`${API_BASE}/api/admin/courses/${id}`, { method: "DELETE", headers: adminHeaders() });
  loadAdminCourses();
}

// --- Admin paragraphs ---

let adminActiveCourseId = null;

document.getElementById("adminCloseParagraphs").addEventListener("click", () => document.getElementById("adminParagraphsPanel").classList.add("hidden"));

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
  const res = await fetch(`${API_BASE}/api/admin/courses/${courseId}/paragraphs`, { headers: adminHeaders() });
  const data = await res.json();
  const box = document.getElementById("adminParagraphsList");
  box.innerHTML = "";
  if (data.paragraphs.length === 0) box.innerHTML = `<div class="empty-msg">Hali bo'lim qo'shilmagan</div>`;
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
      await fetch(`${API_BASE}/api/admin/paragraphs/${p.id}`, { method: "DELETE", headers: adminHeaders() });
      renderAdminParagraphs(courseId);
      loadAdminCourses();
    };
    box.appendChild(row);
  });
}

document.getElementById("paragraphFormEl").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("ap_id").value;
  const courseId = document.getElementById("ap_course_id").value;
  const data = {
    course_id: parseInt(courseId),
    title: document.getElementById("ap_title").value,
    order_num: parseInt(document.getElementById("ap_order_num").value)
  };
  if (id) await fetch(`${API_BASE}/api/admin/paragraphs/${id}`, { method: "PUT", headers: adminHeaders(), body: JSON.stringify(data) });
  else await fetch(`${API_BASE}/api/admin/paragraphs`, { method: "POST", headers: adminHeaders(), body: JSON.stringify(data) });
  document.getElementById("ap_id").value = "";
  document.getElementById("ap_title").value = "";
  document.getElementById("ap_order_num").value = 0;
  renderAdminParagraphs(courseId);
  loadAdminCourses();
});

// --- Admin lessons ---

document.getElementById("adminCloseLessons").addEventListener("click", () => document.getElementById("adminLessonsPanel").classList.add("hidden"));

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
  const res = await fetch(`${API_BASE}/api/admin/paragraphs/${paragraphId}/lessons`, { headers: adminHeaders() });
  const data = await res.json();
  const box = document.getElementById("adminLessonsList");
  box.innerHTML = "";
  if (data.lessons.length === 0) box.innerHTML = `<div class="empty-msg">Hali video qo'shilmagan</div>`;
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
      await fetch(`${API_BASE}/api/admin/lessons/${l.id}`, { method: "DELETE", headers: adminHeaders() });
      renderAdminLessons(paragraphId);
      loadAdminCourses();
    };
    box.appendChild(row);
  });
}

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
  if (id) await fetch(`${API_BASE}/api/admin/lessons/${id}`, { method: "PUT", headers: adminHeaders(), body: JSON.stringify(data) });
  else await fetch(`${API_BASE}/api/admin/lessons`, { method: "POST", headers: adminHeaders(), body: JSON.stringify(data) });
  document.getElementById("al_id").value = "";
  document.getElementById("al_title").value = "";
  document.getElementById("al_video_url").value = "";
  document.getElementById("al_description").value = "";
  document.getElementById("al_order_num").value = 0;
  renderAdminLessons(paragraphId);
  loadAdminCourses();
});

// --- Admin enroll (obuna berish) ---

document.getElementById("enrollFormEl").addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = {
    telegram_id: parseInt(document.getElementById("en_telegram_id").value),
    course_id: parseInt(document.getElementById("en_course_id").value),
    duration_days: document.getElementById("en_duration_days").value || null
  };
  await fetch(`${API_BASE}/api/admin/enroll`, { method: "POST", headers: adminHeaders(), body: JSON.stringify(data) });
  tg.showAlert ? tg.showAlert("✅ Obuna berildi!") : alert("Obuna berildi!");
  document.getElementById("en_telegram_id").value = "";
  document.getElementById("en_duration_days").value = "";
});

// ---------- Boshlanish ----------

loadBrand();
loadUser();
checkIsAdmin();
showScreen("home");
