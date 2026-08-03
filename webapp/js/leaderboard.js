// js/leaderboard.js
import { apiFetch } from "./api.js";
import { errorHtml, emptyHtml, skeletonRows } from "./components.js";

const MONTH_NAMES = [
  "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
  "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"
];

export async function loadLeaderboard() {
  const box = document.getElementById("leaderboardList");
  const rankBox = document.getElementById("myRankBox");
  box.innerHTML = skeletonRows(6);
  try {
    const res = await apiFetch(`/api/leaderboard`);
    const data = await res.json();
    rankBox.innerHTML = `<div class="my-rank-label">Sizning o'rningiz</div><div class="my-rank-num">#${data.my_rank || "—"}</div>`;

    box.innerHTML = "";
    if (data.leaderboard.length === 0) {
      box.innerHTML = emptyHtml("Hali hech kim coin to'plamagan — birinchi bo'ling!");
      return;
    }
    data.leaderboard.forEach((u, idx) => {
      const rank = idx + 1;
      let medal = `<span class="rank-num">${rank}</span>`;
      if (rank === 1) medal = `<span class="rank-medal gold-medal">👑</span>`;
      else if (rank === 2) medal = `<span class="rank-medal silver-medal">🥈</span>`;
      else if (rank === 3) medal = `<span class="rank-medal bronze-medal">🥉</span>`;

      const row = document.createElement("div");
      row.className = "leaderboard-row" + (rank <= 3 ? " top-rank" : "");
      row.innerHTML = `
        ${medal}
        <span class="lb-name">${u.first_name || "Foydalanuvchi"}</span>
        <span class="lb-coins">🪙 ${u.coins}</span>
      `;
      box.appendChild(row);
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

// ---------- Nazorat testlari oylik reytingi ----------

let controlLbLoaded = false;

function switchLeaderboardTab(tab) {
  document.getElementById("tabBtnCoinLb").classList.toggle("active", tab === "coin");
  document.getElementById("tabBtnControlLb").classList.toggle("active", tab === "control");
  document.getElementById("coinLbTabContent").classList.toggle("hidden", tab !== "coin");
  document.getElementById("controlLbTabContent").classList.toggle("hidden", tab !== "control");

  if (tab === "control" && !controlLbLoaded) {
    loadControlLeaderboard();
  }
}

async function loadControlLeaderboard() {
  const rankBox = document.getElementById("myControlRankBox");
  const box = document.getElementById("controlLeaderboardList");
  const monthLabel = document.getElementById("controlLbMonthLabel");
  box.innerHTML = skeletonRows(6);
  try {
    const res = await apiFetch(`/api/control-test-leaderboard`);
    const data = await res.json();
    controlLbLoaded = true;
    monthLabel.textContent = `📅 ${MONTH_NAMES[data.month - 1]} ${data.year} — oylik reyting`;

    if (data.my_rank) {
      rankBox.innerHTML = `
        <div class="my-rank-label">Sizning o'rningiz</div>
        <div class="my-rank-num">#${data.my_rank.rank}</div>
        <div style="font-size:11px;color:var(--text-dim);margin-top:4px;">
          ${data.my_rank.avg_percent}% o'rtacha natija · ${data.my_rank.attempts_count} ta test · ${data.my_rank.total_participants} ishtirokchi orasida
        </div>
      `;
    } else {
      rankBox.innerHTML = `
        <div class="my-rank-label">Sizning o'rningiz</div>
        <div class="my-rank-num">—</div>
        <div style="font-size:11px;color:var(--text-dim);margin-top:4px;">Bu oy hali nazorat testi topshirmagansiz</div>
      `;
    }

    box.innerHTML = "";
    if (data.leaderboard.length === 0) {
      box.innerHTML = emptyHtml("Bu oy hali hech kim nazorat testi topshirmagan");
      return;
    }
    data.leaderboard.forEach((u, idx) => {
      const rank = idx + 1;
      let medal = `<span class="rank-num">${rank}</span>`;
      if (rank === 1) medal = `<span class="rank-medal gold-medal">👑</span>`;
      else if (rank === 2) medal = `<span class="rank-medal silver-medal">🥈</span>`;
      else if (rank === 3) medal = `<span class="rank-medal bronze-medal">🥉</span>`;

      const row = document.createElement("div");
      row.className = "leaderboard-row" + (rank <= 3 ? " top-rank" : "");
      row.innerHTML = `
        ${medal}
        <span class="lb-name">${u.first_name || "Foydalanuvchi"}</span>
        <span class="lb-coins">${u.avg_percent}% · ${u.attempts_count} test</span>
      `;
      box.appendChild(row);
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

export function initLeaderboardModule() {
  document.getElementById("tabBtnCoinLb").addEventListener("click", () => switchLeaderboardTab("coin"));
  document.getElementById("tabBtnControlLb").addEventListener("click", () => switchLeaderboardTab("control"));
}
