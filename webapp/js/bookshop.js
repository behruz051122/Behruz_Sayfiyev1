// js/bookshop.js
// Kitoblar do'koni — BOSMA (pochta orqali yetkaziladigan) kitoblarni
// ko'rsatish. E'TIBOR: bu courses.js'dagi RAQAMLI "Kitoblar" (bo'lim/dars
// strukturasi bilan o'qiladigan kontent) dan BUTUNLAY ALOHIDA funksiya.
//
// To'lov tizimi (Payme/Click) hali ULANMAGAN — "Xarid qilish" tugmasi
// talabani shu kitobga biriktirilgan (yoki bo'sh bo'lsa umumiy) admin
// Telegram kontaktiga olib boradi, xarid o'sha yerda qo'lda kelishiladi.
// Real to'lov integratsiyasi keyinroq, admin Payme/Click merchant
// hisobini ochgach qo'shiladi.

import { tg, publicFetch } from "./api.js";
import { errorHtml, emptyHtml, skeletonCards } from "./components.js";
import { brandInfo } from "./user.js";
import * as Courses from "./courses.js";

let allProducts = [];
let activeCategory = "Hammasi";
let searchQuery = "";

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

export async function loadBookShop() {
  const container = document.getElementById("bookShopList");
  container.innerHTML = skeletonCards(3);
  bindBookShopSearch();
  try {
    const res = await publicFetch(`/api/book-products`);
    const data = await res.json();
    allProducts = data.products || [];
    buildCategoryFilters();
    renderBookShopList();
  } catch (e) {
    console.error(e);
    container.innerHTML = errorHtml();
  }
}

function bindBookShopSearch() {
  const input = document.getElementById("bookShopSearchInput");
  if (!input || input.dataset.bound) return;
  input.dataset.bound = "true";
  input.addEventListener("input", () => {
    searchQuery = input.value.trim().toLowerCase();
    renderBookShopList();
  });
}

function buildCategoryFilters() {
  const row = document.getElementById("bookShopCategoryRow");
  const categories = ["Hammasi", ...new Set(allProducts.map(p => p.category).filter(Boolean))];
  row.innerHTML = "";
  categories.forEach(cat => {
    const chip = document.createElement("button");
    chip.className = "filter-chip" + (cat === activeCategory ? " active" : "");
    chip.textContent = cat;
    chip.onclick = () => {
      activeCategory = cat;
      document.querySelectorAll("#bookShopCategoryRow .filter-chip").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      renderBookShopList();
    };
    row.appendChild(chip);
  });
}

function openContact(username) {
  const handle = (username || brandInfo.adminContact || "").replace(/^@/, "").trim();
  if (!handle) {
    if (tg.showAlert) tg.showAlert("Bog'lanish uchun kontakt ko'rsatilmagan.");
    return;
  }
  const url = `https://t.me/${handle}`;
  if (tg.openTelegramLink) tg.openTelegramLink(url);
  else window.open(url, "_blank");
}

// "Video yechim" tugmasi — admin har bir kitob mahsulotiga miniappdagi
// biror kursni ("bo'lim") bog'lab qo'ygan bo'lsa, o'quvchi shu yerdan
// to'g'ridan-to'g'ri o'sha kursning ichiga o'tadi. "Orqaga" tugmasi
// mazmunli ishlashi uchun avval Kurslar ro'yxatini (fonda) yuklab qo'yamiz.
async function openVideoSolution(courseId) {
  Courses.setListType("course");
  const listTitle = document.getElementById("listTitle");
  if (listTitle) listTitle.textContent = "Kurslar";
  try {
    await Courses.loadCourseList();
  } catch (e) {
    console.error(e);
  }
  Courses.openCourseDetail(courseId);
}

function renderBookShopList() {
  const container = document.getElementById("bookShopList");
  container.innerHTML = "";

  const filtered = allProducts.filter(p => {
    if (activeCategory !== "Hammasi" && p.category !== activeCategory) return false;
    if (searchQuery && !(`${p.title} ${p.subtitle}`.toLowerCase().includes(searchQuery))) return false;
    return true;
  });

  if (filtered.length === 0) {
    container.innerHTML = emptyHtml(searchQuery ? `"${searchQuery}" bo'yicha hech narsa topilmadi` : "Hozircha mahsulot qo'shilmagan");
    return;
  }

  filtered.forEach(p => {
    const card = document.createElement("div");
    card.className = "book-product-card";
    const categoryTag = p.is_bundle ? "KOMPLEKT" : (p.category || "");
    card.innerHTML = `
      ${p.badge_text ? `<div class="book-product-badge">${escapeHtml(p.badge_text)}</div>` : ""}
      ${p.image_url
        ? `<img class="book-product-img" src="${p.image_url}" alt="${escapeHtml(p.title)}">`
        : `<div class="book-product-img book-product-img-placeholder">📘</div>`}
      <div class="book-product-body">
        ${categoryTag ? `<div class="book-product-category">${escapeHtml(categoryTag)}</div>` : ""}
        <div class="book-product-title">${escapeHtml(p.title)}</div>
        ${p.subtitle ? `<div class="book-product-sub">${escapeHtml(p.subtitle)}</div>` : ""}
        <div class="book-product-bottom">
          <div class="book-product-price">${p.price ? p.price.toLocaleString() + " so'm" : "Narxi so'ralsin"}</div>
          <button class="book-product-buy">🛒 Xarid qilish</button>
          ${p.linked_course_id ? `<button class="book-product-video">🎥 Video yechim</button>` : ""}
        </div>
      </div>
    `;
    card.querySelector(".book-product-buy").addEventListener("click", () => openContact(p.contact_username));
    const videoBtn = card.querySelector(".book-product-video");
    if (videoBtn) videoBtn.addEventListener("click", () => openVideoSolution(p.linked_course_id));
    container.appendChild(card);
  });
}
