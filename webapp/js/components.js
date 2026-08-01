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
