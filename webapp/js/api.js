// js/api.js
// Telegram Mini App global obyekti va serverga so'rov yuborish uchun
// markazlashtirilgan yordamchi funksiyalar. Har bir himoyalangan so'rovga
// Telegram initData avtomatik qo'shiladi — server buni auth.py orqali
// tekshiradi (1-bosqich, xavfsizlik yangilanishi).

export const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// Kompyuterda (Telegram Desktop) ilova standart holatda kichik "popup"
// panelda ochiladi — expand() faqat shu panel ICHIDA balandlikni to'ldiradi,
// panelning o'zini kattalashtirmaydi. requestFullscreen() (Bot API 8.0+)
// ilovani butun Telegram oynasiga (yoki butun ekranga) yoyadi — kompyuter
// hajmiga to'liq moslashuv shu orqali amalga oshadi. Eski Telegram
// versiyalarida bu funksiya yo'q, shuning uchun avval tekshirib olamiz.
if (tg.isVersionAtLeast && tg.isVersionAtLeast("8.0")) {
  try { tg.requestFullscreen(); } catch (e) { /* qo'llab-quvvatlanmasa jim o'tkazib yuboramiz */ }
}
if (tg.disableVerticalSwipes) {
  try { tg.disableVerticalSwipes(); } catch (e) {}
}

// ---------- MAVZU (qorong'i / ochiq) ----------
// Ilova Telegram'dagi tanlovga moslashadi: foydalanuvchi ochiq mavzuda
// bo'lsa — ilova ham ochiq ko'rinishga o'tadi. Aniqlash tartibi:
//   1) Telegram bergan colorScheme ("dark" | "light") — eng ishonchlisi
//   2) u bo'lmasa — qurilmaning tizim sozlamasi (prefers-color-scheme)
//   3) ikkalasi ham noma'lum bo'lsa — qorong'i (asosiy brend ko'rinishi)
//
// Foydalanuvchi Telegram sozlamasini ilova OCHIQ turganda o'zgartirsa,
// "themeChanged" hodisasi orqali darhol qayta qo'llanadi.
function applyTelegramTheme() {
  let scheme = null;
  try {
    scheme = tg.colorScheme || null;
  } catch (e) { /* eski Telegram versiyasi */ }

  if (scheme !== "light" && scheme !== "dark") {
    const prefersLight = window.matchMedia
      && window.matchMedia("(prefers-color-scheme: light)").matches;
    scheme = prefersLight ? "light" : "dark";
  }

  document.documentElement.setAttribute("data-theme", scheme);

  // Telegram oynasining yuqori/pastki chizig'ini ham moslaymiz — ilova
  // Telegram ichiga "quyilgandek" ko'rinadi, chekkalarda begona rang qolmaydi.
  const shellColor = scheme === "light" ? "#f6f8fb" : "#0a0f1c";
  try { tg.setHeaderColor && tg.setHeaderColor(shellColor); } catch (e) {}
  try { tg.setBackgroundColor && tg.setBackgroundColor(shellColor); } catch (e) {}
}

applyTelegramTheme();
try { tg.onEvent && tg.onEvent("themeChanged", applyTelegramTheme); } catch (e) {}
if (window.matchMedia) {
  try {
    window.matchMedia("(prefers-color-scheme: light)")
      .addEventListener("change", applyTelegramTheme);
  } catch (e) { /* eski brauzerlar addEventListener'ni qo'llab-quvvatlamaydi */ }
}

export const tgUser = tg.initDataUnsafe?.user || { id: 0, first_name: "Mehmon" };
export const API_BASE = window.location.origin;

/**
 * Himoyalangan (autentifikatsiya talab qiladigan) so'rov.
 * Har doim X-Telegram-Init-Data headerini avtomatik qo'shadi.
 * Server 401 qaytarsa — foydalanuvchiga tushunarli xabar ko'rsatadi.
 */
export async function apiFetch(path, options = {}) {
  // Fayl yuklashda (FormData) "Content-Type"ni QO'LDA qo'yish mumkin emas —
  // brauzer o'zi to'g'ri "multipart/form-data; boundary=..." headerini
  // qo'yishi kerak. Shuning uchun body FormData bo'lsa, standart JSON
  // Content-Type'ni qo'shmaymiz.
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  const baseHeaders = isFormData ? {} : { "Content-Type": "application/json" };
  const headers = Object.assign(
    baseHeaders,
    options.headers || {},
    { "X-Telegram-Init-Data": tg.initData || "" }
  );
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    const msg = "Xavfsizlik tekshiruvidan o'tmadi. Ilovani Telegram ichida qayta oching.";
    if (tg.showAlert) tg.showAlert(msg); else alert(msg);
    throw new Error("Unauthorized (401)");
  }
  return res;
}

/** Autentifikatsiyasiz ochiq so'rov (masalan /api/brand). */
export async function publicFetch(path, options = {}) {
  return fetch(`${API_BASE}${path}`, options);
}
