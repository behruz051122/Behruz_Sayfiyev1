// app.js — Mini App logikasi

const tg = window.Telegram.WebApp;
tg.expand();

const tgUser = tg.initDataUnsafe?.user || { id: 0, first_name: "Mehmon" };
const API_BASE = window.location.origin;

let currentListType = "course"; // 'course' yoki 'book'
let currentCourseId = null;
let allCourses = [];

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
    document.getElementById("listTitle").textContent = "Kurslar";
    loadCourseList();
    showScreen("list");
  } else if (target === "books") {
    currentListType = "book";
    document.getElementById("listTitle").textContent = "Kitoblar";
    loadCourseList();
    showScreen("list");
  } else if (target === "referral") {
    loadReferral();
    showScreen("referral");
  } else if (target === "back-to-list") {
    showScreen("list");
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
    container.innerHTML = "";

    if (allCourses.length === 0) {
      container.innerHTML = `<div style="color:var(--text-dim);padding:20px;text-align:center;">Hozircha bo'sh</div>`;
      return;
    }

    allCourses.forEach(course => {
      const card = document.createElement("div");
      card.className = "course-card";
      card.innerHTML = `
        <div class="course-emoji">${course.thumbnail_emoji || "📘"}</div>
        <div class="course-info">
          <span class="course-tag">${course.subject}</span>
          <div class="course-title">${course.title}</div>
          <div class="course-desc">${course.description || ""}</div>
          <div class="course-meta">
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
  } catch (e) {
    console.error(e);
    container.innerHTML = `<div style="color:var(--text-dim);padding:20px;">Xatolik yuz berdi</div>`;
  }
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
          <p>Ushbu kursni ochish uchun ${course.required_referrals} kishini taklif qiling va ular kanalga obuna bo'lishi kerak.</p>
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
  if (url.includes("youtube.com") || url.includes("youtu.be")) {
    let videoId = "";
    if (url.includes("youtu.be/")) videoId = url.split("youtu.be/")[1].split("?")[0];
    else if (url.includes("watch?v=")) videoId = url.split("watch?v=")[1].split("&")[0];
    videoHtml = `<div class="video-wrap"><iframe src="https://www.youtube.com/embed/${videoId}" allowfullscreen></iframe></div>`;
  } else if (url) {
    videoHtml = `<div class="video-wrap"><video src="${url}" controls></video></div>`;
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
  } catch (e) { console.error(e); }
}

loadBrand();
loadUser();
showScreen("home");
