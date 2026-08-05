// js/navigate.js
// Ekranlar orasida almashish uchun markazlashtirilgan modul.
//
// NEGA "CustomEvent" ISHLATILADI:
// courses.js, tests.js kabi modullar ba'zan o'zlari navigatsiya qilishi kerak
// bo'ladi (masalan "Do'stlarni taklif qilish" tugmasi bosilganda referal
// ekraniga o'tish). Agar ular buning uchun to'g'ridan-to'g'ri main.js'ni
// import qilishsa — "main.js -> courses.js -> main.js" AYLANMA BOG'LIQLIK
// (circular import) hosil bo'ladi, bu esa xato va tushunarsiz xatoliklarga
// olib kelishi mumkin. Shuning uchun modullar shunchaki "menga shu ekranga
// o'tishni so'rashyapti" degan hodisa (event) yuboradi, main.js esa buni
// tinglab, haqiqiy o'tishni bajaradi. Bu — modullarni bir-biridan mustaqil
// qiladigan standart dizayn andozasi.

const NAV_SCREEN_INDEX = {
  home: 0, courses: 1, "courses-landing": 1, "courses-by-subject": 1,
  tests: 2, "student-results": 3, profile: 4
};

export function showScreen(name) {
  document.querySelectorAll(".screen").forEach(s => s.classList.add("hidden"));
  document.getElementById("screen-" + name).classList.remove("hidden");

  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
  const navBtns = document.querySelectorAll(".nav-item");
  if (NAV_SCREEN_INDEX[name] !== undefined) navBtns[NAV_SCREEN_INDEX[name]].classList.add("active");
}

/** Boshqa modullardan navigatsiya so'rash uchun ishlatiladi. */
export function navigateTo(target) {
  document.dispatchEvent(new CustomEvent("app:navigate", { detail: { target } }));
}
