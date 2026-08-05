// js/components.js
// Butun ilova bo'ylab qayta ishlatiladigan kichik UI yordamchilari. Masalan,
// "Yuklanmoqda..." matnini yoki uslubini o'zgartirmoqchi bo'lsangiz, shu
// faylni bir marta tahrirlashingiz kifoya — barcha ekranlarda yangilanadi.

export const DIFFICULTY_LABELS = { oson: "Oson", orta: "O'rta", qiyin: "Qiyin" };

export function loadingHtml(text = "Yuklanmoqda...") {
  return `<div class="empty-msg">${text}</div>`;
}

export function emptyHtml(text) {
  return `<div class="empty-msg">${text}</div>`;
}

export function errorHtml(text = "Xatolik yuz berdi") {
  return `<div class="empty-msg">${text}</div>`;
}

// ---------- Skeleton (yuklanish) placeholder'lari ----------
//
// "Yuklanmoqda..." matni o'rniga, ma'lumot qanday ko'rinishda kelishini
// oldindan ko'rsatadigan animatsion placeholder'lar. Bu foydalanuvchiga
// ilova "muallaqlab qolmagani", balki faol ishlayotganini his qildiradi —
// bugungi kunda ko'plab premium ilovalar shu usuldan foydalanadi.

export function skeletonCards(count = 3) {
  let html = "";
  for (let i = 0; i < count; i++) {
    html += `
      <div class="skeleton-card">
        <div class="skeleton-emoji skeleton-shimmer"></div>
        <div class="skeleton-lines">
          <div class="skeleton-line w-40 skeleton-shimmer"></div>
          <div class="skeleton-line w-90 skeleton-shimmer"></div>
          <div class="skeleton-line w-60 skeleton-shimmer"></div>
        </div>
      </div>
    `;
  }
  return html;
}

export function skeletonRows(count = 5) {
  let html = "";
  for (let i = 0; i < count; i++) {
    html += `
      <div class="skeleton-row">
        <div class="skeleton-circle skeleton-shimmer"></div>
        <div class="skeleton-line skeleton-shimmer"></div>
      </div>
    `;
  }
  return html;
}

// ---------- Natijalar dinamikasi (progress) grafigi ----------
//
// Hech qanday tashqi kutubxonasiz (dependency), sof SVG orqali chizilgan
// yengil chiziqli grafik — vaqt o'tishi bilan foydalanuvchi natijasi qanday
// o'zgarayotganini ko'rsatadi.

export function renderProgressChart(history) {
  if (!history || history.length === 0) {
    return `<div class="empty-msg">Hali natijalar tarixi yo'q — birinchi testni yeching!</div>`;
  }

  const width = 320, height = 130, padTop = 14, padBottom = 26, padSide = 10;
  const usableHeight = height - padTop - padBottom;
  const step = history.length > 1 ? (width - padSide * 2) / (history.length - 1) : 0;

  const points = history.map((h, i) => {
    const x = padSide + i * step;
    const y = padTop + usableHeight - (h.percent / 100) * usableHeight;
    return { x, y, percent: h.percent };
  });

  const pathD = points.map((p, i) => (i === 0 ? `M ${p.x.toFixed(1)} ${p.y.toFixed(1)}` : `L ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)).join(" ");
  const areaD = `${pathD} L ${points[points.length - 1].x.toFixed(1)} ${(padTop + usableHeight).toFixed(1)} L ${points[0].x.toFixed(1)} ${(padTop + usableHeight).toFixed(1)} Z`;
  const dots = points.map(p => `<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="3.5" fill="#0f766e" />`).join("");

  const first = history[0];
  const last = history[history.length - 1];

  return `
    <div class="progress-chart-wrap">
      <svg viewBox="0 0 ${width} ${height}" class="progress-chart-svg" preserveAspectRatio="none" role="img" aria-label="Natijalar dinamikasi grafigi">
        <line x1="${padSide}" y1="${padTop + usableHeight}" x2="${width - padSide}" y2="${padTop + usableHeight}" stroke="#e3e8ef" stroke-width="1" />
        <path d="${areaD}" fill="rgba(15,118,110,0.12)" stroke="none" />
        <path d="${pathD}" fill="none" stroke="#0f766e" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round" />
        ${dots}
      </svg>
      <div class="progress-chart-labels">
        <span>${first.percent}% (birinchi)</span>
        <span>${last.percent}% (so'nggi)</span>
      </div>
    </div>
  `;
}

export function formatSeconds(totalSeconds) {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

/**
 * Filtr chip'lari qatorini quradi (fan, holat va h.k. bo'yicha filtrlash uchun
 * kurslar, testlar ro'yxatlarida ishlatiladi — bitta joyda saqlanadi).
 */
export function buildFilterChips(container, items, activeItem, onSelect) {
  container.innerHTML = "";
  items.forEach(item => {
    const chip = document.createElement("button");
    chip.className = "filter-chip" + (item === activeItem ? " active" : "");
    chip.textContent = item;
    chip.onclick = () => onSelect(item);
    container.appendChild(chip);
  });
}

// ---------- Rasm lightbox (bir marta ulanadi, butun ilova ishlatadi) ----------

export function openLightbox(src) {
  document.getElementById("lightboxImg").src = src;
  document.getElementById("imageLightbox").classList.remove("hidden");
}

export function closeLightbox() {
  document.getElementById("imageLightbox").classList.add("hidden");
  document.getElementById("lightboxImg").src = "";
}

export function initLightbox() {
  document.getElementById("lightboxClose").addEventListener("click", closeLightbox);
  document.getElementById("imageLightbox").addEventListener("click", (e) => {
    if (e.target.id === "imageLightbox") closeLightbox();
  });
}

// ---------- Toast (o'zi avtomatik yopiladigan qisqa xabar) ----------
//
// Telegramning tg.showAlert() foydalanuvchidan majburan "OK/Закрыть"
// bosishni talab qiladi — coin berilgani kabi kichik, ijobiy xabarlar
// uchun bu ortiqcha to'siq. Shu funksiya o'rniga sahifaning o'zida
// bir necha soniyadan keyin o'zi yo'qoladigan xabar (toast) chiqaradi.

export function showToast(message, duration = 2600) {
  let container = document.getElementById("toastContainer");
  if (!container) {
    container = document.createElement("div");
    container.id = "toastContainer";
    container.className = "toast-container";
    document.body.appendChild(container);
  }
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  container.appendChild(toast);

  requestAnimationFrame(() => toast.classList.add("toast-visible"));
  setTimeout(() => {
    toast.classList.remove("toast-visible");
    setTimeout(() => toast.remove(), 250);
  }, duration);
}

// ---------- Savol jadvali (Word'dan import qilingan haqiqiy jadvallar) ----------
//
// Word (.docx) orqali ommaviy yuklangan savollarda ba'zan haqiqiy jadval
// (masalan davriy jadval ma'lumotlari, izotoplar foizi) bo'lishi mumkin.
// Buni matn shaklida emas, ASL katak-katak ko'rinishida ko'rsatish uchun
// backend "table_data" ustunida JSON qatorida saqlaydi — shu funksiya buni
// haqiqiy <table>ga aylantiradi.

function escapeHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function renderQuestionTables(tableDataJson) {
  if (!tableDataJson) return "";
  let parsed;
  try {
    parsed = typeof tableDataJson === "string" ? JSON.parse(tableDataJson) : tableDataJson;
  } catch (e) {
    return "";
  }
  const tables = parsed && parsed.tables ? parsed.tables : [];
  if (tables.length === 0) return "";

  return tables.map(t => {
    const rows = t.rows || [];
    if (rows.length === 0) return "";
    const [headerRow, ...bodyRows] = rows;
    const theadHtml = `<thead><tr>${headerRow.map(c => `<th>${escapeHtml(c)}</th>`).join("")}</tr></thead>`;
    const tbodyHtml = `<tbody>${bodyRows.map(r => `<tr>${r.map(c => `<td>${escapeHtml(c)}</td>`).join("")}</tr>`).join("")}</tbody>`;
    return `<div class="question-table-wrap"><table class="question-table">${theadHtml}${tbodyHtml}</table></div>`;
  }).join("");
}
