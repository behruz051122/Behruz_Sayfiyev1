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

export async function loadUser() {
  try {
    const res = await apiFetch(`/api/user`);
    const user = await res.json();
    document.getElementById("helloName").textContent = `${user.first_name}, salom 👋`;
    document.getElementById("coinsBadge").textContent = `🪙 ${user.coins}`;
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
