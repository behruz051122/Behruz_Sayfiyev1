// js/leaderboard.js
import { apiFetch } from "./api.js";
import { errorHtml, emptyHtml, skeletonRows } from "./components.js";

const MONTH_NAMES = [
  "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
  "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"
];

function formatAvgTime(totalSeconds) {
  const s = Math.round(totalSeconds || 0);
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}:${String(rem).padStart(2, "0")}`;
}

let activeLbPeriod = "all";

function initialLetter(name) {
  return (name || "?").trim().charAt(0).toUpperCase() || "?";
}

function renderPodium(top3) {
  const podium = document.getElementById("lbPodium");
  if (!top3 || top3.length === 0) {
    podium.innerHTML = "";
    return;
  }
  // Vizual tartib: 2-o'rin | 1-o'rin (markazda, eng baland) | 3-o'rin —
  // klassik "sovrinlar taxti" (podium) ko'rinishi.
  const order = [top3[1], top3[0], top3[2]];
  const ranks = [2, 1, 3];
  podium.innerHTML = order.map((u, i) => {
    if (!u) return `<div class="podium-slot"></div>`;
    const rank = ranks[i];
    return `
      <div class="podium-slot podium-${rank}">
        ${rank === 1 ? `<div class="podium-crown">👑</div>` : ""}
        <div class="podium-avatar">${initialLetter(u.first_name)}</div>
        <div class="podium-name">${u.first_name || "Foydalanuvchi"}</div>
        <div class="podium-coins">🪙 ${u.coins}</div>
        <div class="podium-bar podium-bar-${rank}">${rank}</div>
      </div>
    `;
  }).join("");
}

export async function loadLeaderboard(period) {
  if (period) activeLbPeriod = period;
  const box = document.getElementById("leaderboardList");
  const rankBox = document.getElementById("myRankBox");
  const listLabel = document.getElementById("lbListLabel");
  box.innerHTML = skeletonRows(6);
  document.querySelectorAll("#lbPeriodRow .filter-chip").forEach(c => {
    c.classList.toggle("active", c.getAttribute("data-period") === activeLbPeriod);
  });
  try {
    const res = await apiFetch(`/api/leaderboard?period=${activeLbPeriod}`);
    const data = await res.json();
    rankBox.innerHTML = `<div class="my-rank-label">Sizning o'rningiz</div><div class="my-rank-num">#${data.my_rank || "—"}</div>`;

    box.innerHTML = "";
    if (data.leaderboard.length === 0) {
      document.getElementById("lbPodium").innerHTML = "";
      listLabel.classList.add("hidden");
      box.innerHTML = emptyHtml("Hali hech kim coin to'plamagan — birinchi bo'ling!");
      return;
    }

    const top3 = data.leaderboard.slice(0, 3);
    const rest = data.leaderboard.slice(3);
    renderPodium(top3);
    listLabel.classList.toggle("hidden", rest.length === 0);

    rest.forEach((u, idx) => {
      const rank = idx + 4;
      const row = document.createElement("div");
      row.className = "leaderboard-row";
      row.innerHTML = `
        <span class="rank-num">${rank}</span>
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
          ${data.my_rank.avg_percent}% o'rtacha natija · ⏱ ${formatAvgTime(data.my_rank.avg_seconds)} o'rtacha vaqt · ${data.my_rank.attempts_count} ta test · ${data.my_rank.total_participants} ishtirokchi orasida
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
        <span class="lb-coins">${u.avg_percent}% · ⏱ ${formatAvgTime(u.avg_seconds)} · ${u.attempts_count} test</span>
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

  document.querySelectorAll("#lbPeriodRow .filter-chip").forEach(btn => {
    btn.addEventListener("click", () => loadLeaderboard(btn.getAttribute("data-period")));
  });
}
