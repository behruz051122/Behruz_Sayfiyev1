// js/user.js
// Ilova yuklanganda bir marta chaqiriladigan asosiy ma'lumotlar: brend, joriy
// foydalanuvchi, admin holati. Coin balansini yangilash funksiyasi ham shu
// yerda, chunki u doim "joriy foydalanuvchi" tushunchasi bilan bog'liq va
// bir nechta modul (courses.js, tests.js) uni ishlatadi.

import { apiFetch, publicFetch } from "./api.js";

export let isAdmin = false;

/** Brend ma'lumoti (kurs.js, profile.js kabi modullar ham shundan foydalanadi). */
export const brandInfo = { botUsername: "", adminContact: "" };

export async function loadBrand() {
  try {
    const res = await publicFetch(`/api/brand`);
    const data = await res.json();
    document.getElementById("brandName").textContent = data.brand_name;
    document.getElementById("brandSub").textContent = data.brand_sub;
    brandInfo.botUsername = data.bot_username || "";
    brandInfo.adminContact = data.admin_contact || "";
    return data;
  } catch (e) {
    console.error(e);
    return null;
  }
}

// Bosh sahifadagi ko'rsatkichlar paneli. Yangi so'rov yubormaydi —
// /api/user ALLAQACHON qaytargan ma'lumotdan foydalanadi, shuning uchun
// ilova sekinlashmaydi.
function renderHomeStats(user) {
  const box = document.getElementById("homeStatsStrip");
  if (!box || !user) return;

  const streak = user.current_streak || 0;
  const coins = user.coins || 0;
  const rank = user.rank && user.rank.rank ? user.rank.rank : null;

  const items = [
    { icon: "🔥", value: streak, label: streak === 1 ? "kun ketma-ket" : "kun ketma-ket", tone: "warm" },
    { icon: "🪙", value: coins, label: "coin", tone: "teal" },
  ];
  if (rank) items.push({ icon: "🏆", value: `#${rank}`, label: "reytingda", tone: "violet" });

  box.innerHTML = items.map(i => `
    <div class="home-stat home-stat-${i.tone}">
      <span class="home-stat-icon">${i.icon}</span>
      <span class="home-stat-value">${i.value}</span>
      <span class="home-stat-label">${i.label}</span>
    </div>
  `).join("");
}

export async function loadUser() {
  try {
    const res = await apiFetch(`/api/user`);
    const user = await res.json();
    document.getElementById("helloName").textContent = `${user.first_name}, salom 👋`;
    document.getElementById("coinsBadge").textContent = `🪙 ${user.coins}`;
    renderHomeStats(user);
    return user;
  } catch (e) {
    console.error(e);
    return null;
  }
}

export async function refreshCoins() {
  const res = await apiFetch(`/api/user`);
  const user = await res.json();
  document.getElementById("coinsBadge").textContent = `🪙 ${user.coins}`;
  return user;
}

export async function checkIsAdmin() {
  try {
    const res = await apiFetch(`/api/is-admin`);
    const data = await res.json();
    isAdmin = data.is_admin;
    if (isAdmin) document.getElementById("adminGearBtn").classList.remove("hidden");
    return isAdmin;
  } catch (e) {
    console.error(e);
    return false;
  }
}
