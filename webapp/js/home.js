// js/home.js
// Bosh sahifadagi 6 ta katakli menyu (Kurslar, Testlar, Reyting, Kitoblar,
// O'yinlar, Natijalar) — matn/belgi serverdan (admin panelida tahrirlanadi)
// olinadi, lekin QAYSI EKRANGA olib borishi va rangi FUNKSIONAL bog'lanish
// bo'lgani uchun shu yerda qattiq belgilangan (card_key -> {nav, color}).

import { publicFetch } from "./api.js";
import { navigateTo } from "./navigate.js";

const CARD_META = {
  courses: { nav: "courses", colorClass: "dc-teal" },
  tests: { nav: "tests", colorClass: "dc-blue" },
  rating: { nav: "leaderboard", colorClass: "dc-gold" },
  books: { nav: "books", colorClass: "dc-purple" },
  games: { nav: "games", colorClass: "dc-pink" },
  results: { nav: "student-results", colorClass: "dc-cyan" },
};

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

export async function loadDashboardCards() {
  const grid = document.getElementById("dashboardGrid");
  if (!grid) return;
  try {
    const res = await publicFetch(`/api/dashboard-cards`);
    const data = await res.json();
    const cards = data.cards || [];

    grid.innerHTML = cards.map(c => {
      const meta = CARD_META[c.card_key] || { nav: "home", colorClass: "dc-teal" };
      return `
        <button class="dashboard-card" data-nav="${meta.nav}">
          <div class="dc-icon ${meta.colorClass}">${escapeHtml(c.icon) || "✨"}</div>
          <div class="dc-title">${escapeHtml(c.title)}</div>
          <div class="dc-sub">${escapeHtml(c.subtitle)}</div>
          <div class="dc-arrow">›</div>
        </button>
      `;
    }).join("");

    grid.querySelectorAll("[data-nav]").forEach(btn => {
      btn.addEventListener("click", () => navigateTo(btn.getAttribute("data-nav")));
    });
  } catch (e) {
    console.error(e);
  }
}
