// admin.js — Admin panel logikasi

const API_BASE = window.location.origin;
let adminPassword = localStorage.getItem("admin_password") || "";
let currentCourses = [];
let activeCourseId = null;

function headers() {
  return { "Content-Type": "application/json", "X-Admin-Password": adminPassword };
}

async function tryLogin(password) {
  const res = await fetch(`${API_BASE}/api/admin/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password })
  });
  if (res.ok) {
    adminPassword = password;
    localStorage.setItem("admin_password", password);
    showAdmin();
  } else {
    document.getElementById("loginError").textContent = "Parol noto'g'ri";
  }
}

document.getElementById("loginBtn").addEventListener("click", () => {
  const pass = document.getElementById("passwordInput").value;
  tryLogin(pass);
});

document.getElementById("logoutBtn").addEventListener("click", () => {
  localStorage.removeItem("admin_password");
  adminPassword = "";
  document.getElementById("adminScreen").classList.add("hidden");
  document.getElementById("loginScreen").classList.remove("hidden");
});

function showAdmin() {
  document.getElementById("loginScreen").classList.add("hidden");
  document.getElementById("adminScreen").classList.remove("hidden");
  loadCourses();
}

async function loadCourses() {
  const res = await fetch(`${API_BASE}/api/admin/courses`, { headers: headers() });
  if (!res.ok) return;
  const data = await res.json();
  currentCourses = data.courses;
  renderCoursesTable();
}

function renderCoursesTable() {
  const box = document.getElementById("coursesTable");
  box.innerHTML = "";
  currentCourses.forEach(c => {
    const row = document.createElement("div");
    row.className = "course-row";
    row.innerHTML = `
      <div class="emoji">${c.thumbnail_emoji || "📘"}</div>
      <div class="info">
        <div class="t">${c.title} ${c.is_active ? "" : "(yashirin)"}</div>
        <div class="s">${c.subject} · ${c.resource_type === "book" ? "Kitob" : "Kurs"} · ${c.lessons_count} dars · ${c.is_free ? "Bepul" : c.required_referrals + " taklif kerak"}</div>
      </div>
      <div class="actions">
        <button data-action="lessons">Darslar</button>
        <button data-action="edit">Tahrirlash</button>
        <button data-action="delete" class="danger">O'chirish</button>
      </div>
    `;
    row.querySelector('[data-action="lessons"]').onclick = () => openLessons(c.id, c.title);
    row.querySelector('[data-action="edit"]').onclick = () => openCourseForm(c);
    row.querySelector('[data-action="delete"]').onclick = () => deleteCourse(c.id);
    box.appendChild(row);
  });
}

// ---------- Course form ----------

document.getElementById("newCourseBtn").addEventListener("click", () => openCourseForm(null));
document.getElementById("closeCourseForm").addEventListener("click", () => {
  document.getElementById("courseFormPanel").classList.add("hidden");
});

function openCourseForm(course) {
  document.getElementById("courseFormPanel").classList.remove("hidden");
  document.getElementById("lessonsPanel").classList.add("hidden");
  document.getElementById("courseFormTitle").textContent = course ? "Kursni tahrirlash" : "Yangi kurs";
  document.getElementById("courseId").value = course ? course.id : "";
  document.getElementById("f_title").value = course ? course.title : "";
  document.getElementById("f_subject").value = course ? course.subject : "";
  document.getElementById("f_resource_type").value = course ? course.resource_type : "course";
  document.getElementById("f_description").value = course ? (course.description || "") : "";
  document.getElementById("f_is_free").value = course ? String(course.is_free) : "1";
  document.getElementById("f_required_referrals").value = course ? course.required_referrals : 0;
  document.getElementById("f_duration_text").value = course ? (course.duration_text || "") : "";
  document.getElementById("f_thumbnail_emoji").value = course ? (course.thumbnail_emoji || "📘") : "📘";
  document.getElementById("f_order_num").value = course ? course.order_num : 0;
  document.getElementById("f_is_active").value = course ? String(course.is_active) : "1";
}

document.getElementById("courseForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("courseId").value;
  const data = {
    title: document.getElementById("f_title").value,
    subject: document.getElementById("f_subject").value,
    resource_type: document.getElementById("f_resource_type").value,
    description: document.getElementById("f_description").value,
    is_free: parseInt(document.getElementById("f_is_free").value),
    required_referrals: parseInt(document.getElementById("f_required_referrals").value),
    duration_text: document.getElementById("f_duration_text").value,
    thumbnail_emoji: document.getElementById("f_thumbnail_emoji").value,
    order_num: parseInt(document.getElementById("f_order_num").value),
    is_active: parseInt(document.getElementById("f_is_active").value)
  };

  if (id) {
    await fetch(`${API_BASE}/api/admin/courses/${id}`, { method: "PUT", headers: headers(), body: JSON.stringify(data) });
  } else {
    await fetch(`${API_BASE}/api/admin/courses`, { method: "POST", headers: headers(), body: JSON.stringify(data) });
  }
  document.getElementById("courseFormPanel").classList.add("hidden");
  loadCourses();
});

async function deleteCourse(id) {
  if (!confirm("Bu kursni butunlay o'chirmoqchimisiz? Barcha darslar ham o'chadi.")) return;
  await fetch(`${API_BASE}/api/admin/courses/${id}`, { method: "DELETE", headers: headers() });
  loadCourses();
}

// ---------- Lessons ----------

document.getElementById("closeLessonsPanel").addEventListener("click", () => {
  document.getElementById("lessonsPanel").classList.add("hidden");
});

async function openLessons(courseId, title) {
  activeCourseId = courseId;
  document.getElementById("lessonsPanel").classList.remove("hidden");
  document.getElementById("courseFormPanel").classList.add("hidden");
  document.getElementById("lessonsPanelTitle").textContent = `Darslar — ${title}`;
  document.getElementById("lessonCourseId").value = courseId;
  document.getElementById("lessonId").value = "";
  document.getElementById("l_title").value = "";
  document.getElementById("l_video_url").value = "";
  document.getElementById("l_description").value = "";
  document.getElementById("l_order_num").value = 0;
  await renderLessons(courseId);
}

async function renderLessons(courseId) {
  const res = await fetch(`${API_BASE}/api/admin/courses/${courseId}/lessons`, { headers: headers() });
  const data = await res.json();
  const box = document.getElementById("lessonsList");
  box.innerHTML = "";
  if (data.lessons.length === 0) {
    box.innerHTML = `<div style="color:var(--text-dim);font-size:12px;">Hali dars qo'shilmagan</div>`;
  }
  data.lessons.forEach((l, idx) => {
    const row = document.createElement("div");
    row.className = "lesson-row";
    row.innerHTML = `
      <div class="t">${idx + 1}. ${l.title}</div>
      <button data-action="edit">Tahrirlash</button>
      <button data-action="delete" class="danger">O'chirish</button>
    `;
    row.querySelector('[data-action="edit"]').onclick = () => {
      document.getElementById("lessonId").value = l.id;
      document.getElementById("l_title").value = l.title;
      document.getElementById("l_video_url").value = l.video_url || "";
      document.getElementById("l_description").value = l.description || "";
      document.getElementById("l_order_num").value = l.order_num;
    };
    row.querySelector('[data-action="delete"]').onclick = async () => {
      if (!confirm("Bu darsni o'chirmoqchimisiz?")) return;
      await fetch(`${API_BASE}/api/admin/lessons/${l.id}`, { method: "DELETE", headers: headers() });
      renderLessons(courseId);
      loadCourses();
    };
    box.appendChild(row);
  });
}

document.getElementById("lessonForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("lessonId").value;
  const courseId = document.getElementById("lessonCourseId").value;
  const data = {
    course_id: parseInt(courseId),
    title: document.getElementById("l_title").value,
    video_url: document.getElementById("l_video_url").value,
    description: document.getElementById("l_description").value,
    order_num: parseInt(document.getElementById("l_order_num").value)
  };

  if (id) {
    await fetch(`${API_BASE}/api/admin/lessons/${id}`, { method: "PUT", headers: headers(), body: JSON.stringify(data) });
  } else {
    await fetch(`${API_BASE}/api/admin/lessons`, { method: "POST", headers: headers(), body: JSON.stringify(data) });
  }

  document.getElementById("lessonId").value = "";
  document.getElementById("l_title").value = "";
  document.getElementById("l_video_url").value = "";
  document.getElementById("l_description").value = "";
  document.getElementById("l_order_num").value = 0;

  renderLessons(courseId);
  loadCourses();
});

// ---------- Boshlanish ----------

if (adminPassword) {
  tryLogin(adminPassword);
}
