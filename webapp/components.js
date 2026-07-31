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
