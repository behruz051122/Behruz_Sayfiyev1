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

// ---------- Nazorat testi / Attestatsiya / Milliy sertifikat / Mavzuli testlar — oylik reytinglar ----------
//
// Ushbu 4 ta tab bir xil shaklga ega natija qaytaradi (leaderboard + my_rank),
// farqi faqat qaysi endpoint chaqirilishi va DOM elementlari qaysi id'ga ega
// ekanida — shuning uchun bitta generik funksiya orqali boshqariladi (nusxa
// ko'chirishning oldini oladi).
const KIND_TAB_CONFIG = {
  control: {
    endpoint: "/api/control-test-leaderboard",
    monthLabelId: "controlLbMonthLabel", rankBoxId: "myControlRankBox", listId: "controlLeaderboardList",
    emptyText: "Bu oy hali hech kim nazorat testi topshirmagan",
    noRankText: "Bu oy hali nazorat testi topshirmagansiz",
    metricLabel: "test",
  },
  attestation: {
    endpoint: "/api/test-kind-leaderboard?kind=attestation",
    monthLabelId: "attestationLbMonthLabel", rankBoxId: "myAttestationRankBox", listId: "attestationLeaderboardList",
    emptyText: "Bu oy hali hech kim attestatsiya testini topshirmagan",
    noRankText: "Bu oy hali attestatsiya testi topshirmagansiz",
    metricLabel: "test",
  },
  certificate: {
    endpoint: "/api/test-kind-leaderboard?kind=certificate",
    monthLabelId: "certificateLbMonthLabel", rankBoxId: "myCertificateRankBox", listId: "certificateLeaderboardList",
    emptyText: "Bu oy hali hech kim Milliy sertifikat testini topshirmagan",
    noRankText: "Bu oy hali Milliy sertifikat testi topshirmagansiz",
    metricLabel: "test",
  },
  practice: {
    endpoint: "/api/test-kind-leaderboard?kind=practice",
    monthLabelId: "practiceLbMonthLabel", rankBoxId: "myPracticeRankBox", listId: "practiceLeaderboardList",
    emptyText: "Bu oy hali hech kim mavzuli test topshirmagan",
    noRankText: "Bu oy hali mavzuli test topshirmagansiz",
    metricLabel: "test",
  },
};

const kindLbLoaded = {};

function switchLeaderboardTab(tab) {
  const allTabs = ["coin", "control", "attestation", "certificate", "practice"];
  const tabBtnIds = {
    coin: "tabBtnCoinLb", control: "tabBtnControlLb", attestation: "tabBtnAttestationLb",
    certificate: "tabBtnCertificateLb", practice: "tabBtnPracticeLb",
  };
  const tabContentIds = {
    coin: "coinLbTabContent", control: "controlLbTabContent", attestation: "attestationLbTabContent",
    certificate: "certificateLbTabContent", practice: "practiceLbTabContent",
  };
  allTabs.forEach(t => {
    document.getElementById(tabBtnIds[t]).classList.toggle("active", t === tab);
    document.getElementById(tabContentIds[t]).classList.toggle("hidden", t !== tab);
  });

  if (tab !== "coin" && !kindLbLoaded[tab]) {
    loadKindLeaderboard(tab);
  }
}

async function loadKindLeaderboard(kind) {
  const cfg = KIND_TAB_CONFIG[kind];
  const rankBox = document.getElementById(cfg.rankBoxId);
  const box = document.getElementById(cfg.listId);
  const monthLabel = document.getElementById(cfg.monthLabelId);
  box.innerHTML = skeletonRows(6);
  try {
    const res = await apiFetch(cfg.endpoint);
    const data = await res.json();
    kindLbLoaded[kind] = true;
    monthLabel.textContent = `📅 ${MONTH_NAMES[data.month - 1]} ${data.year} — oylik reyting`;

    if (data.my_rank) {
      rankBox.innerHTML = `
        <div class="my-rank-label">Sizning o'rningiz</div>
        <div class="my-rank-num">#${data.my_rank.rank}</div>
        <div style="font-size:11px;color:var(--text-dim);margin-top:4px;">
          ${data.my_rank.avg_percent}% o'rtacha natija · ⏱ ${formatAvgTime(data.my_rank.avg_seconds)} o'rtacha vaqt · ${data.my_rank.attempts_count} ta ${cfg.metricLabel} · ${data.my_rank.total_participants} ishtirokchi orasida
        </div>
      `;
    } else {
      rankBox.innerHTML = `
        <div class="my-rank-label">Sizning o'rningiz</div>
        <div class="my-rank-num">—</div>
        <div style="font-size:11px;color:var(--text-dim);margin-top:4px;">${cfg.noRankText}</div>
      `;
    }

    box.innerHTML = "";
    if (data.leaderboard.length === 0) {
      box.innerHTML = emptyHtml(cfg.emptyText);
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
        <span class="lb-coins">${u.avg_percent}% · ⏱ ${formatAvgTime(u.avg_seconds)} · ${u.attempts_count} ${cfg.metricLabel}</span>
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
  document.getElementById("tabBtnAttestationLb").addEventListener("click", () => switchLeaderboardTab("attestation"));
  document.getElementById("tabBtnCertificateLb").addEventListener("click", () => switchLeaderboardTab("certificate"));
  document.getElementById("tabBtnPracticeLb").addEventListener("click", () => switchLeaderboardTab("practice"));

  document.querySelectorAll("#lbPeriodRow .filter-chip").forEach(btn => {
    btn.addEventListener("click", () => loadLeaderboard(btn.getAttribute("data-period")));
  });
}
