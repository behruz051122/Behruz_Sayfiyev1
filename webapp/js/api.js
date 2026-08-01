// js/api.js
// Telegram Mini App global obyekti va serverga so'rov yuborish uchun
// markazlashtirilgan yordamchi funksiyalar. Har bir himoyalangan so'rovga
// Telegram initData avtomatik qo'shiladi — server buni auth.py orqali
// tekshiradi (1-bosqich, xavfsizlik yangilanishi).

export const tg = window.Telegram.WebApp;
tg.expand();

export const tgUser = tg.initDataUnsafe?.user || { id: 0, first_name: "Mehmon" };
export const API_BASE = window.location.origin;

/**
 * Himoyalangan (autentifikatsiya talab qiladigan) so'rov.
 * Har doim X-Telegram-Init-Data headerini avtomatik qo'shadi.
 * Server 401 qaytarsa — foydalanuvchiga tushunarli xabar ko'rsatadi.
 */
export async function apiFetch(path, options = {}) {
  const headers = Object.assign(
    { "Content-Type": "application/json" },
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
