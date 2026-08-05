// js/games.js
// O'yinlar — 1x1 Battle (ELO reytingli, ASINXRON). Ikkala o'yinchi bir
// vaqtda onlayn bo'lishi shart emas: "Jang qiling" bosilganda, agar
// kutayotgan raqib bo'lsa — o'shanga qo'shilib DARHOL natija chiqadi;
// bo'lmasa, yangi jang boshlanadi va siz javob berib bo'lgach, "raqib
// qidirilmoqda" holatida qolasiz — raqib keyinroq qo'shilganda natija
// "Mening janglarim" bo'limida ko'rinadi (va Telegram orqali xabar
// yuboriladi).

import { apiFetch, tg } from "./api.js";
import { showScreen, navigateTo } from "./navigate.js";
import { errorHtml, emptyHtml, skeletonCards, renderQuestionTables } from "./components.js";

let allSubjects = [];
let currentQuiz = null; // { battleId, subject, questions, index, answers, startedAt }

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

// ================================================================
// FAN TANLASH (bosh O'yinlar ekrani)
// ================================================================

export async function loadGameSubjects() {
  const box = document.getElementById("gameSubjectsList");
  box.innerHTML = skeletonCards(2);
  try {
    const res = await apiFetch(`/api/games/subjects`);
    const data = await res.json();
    allSubjects = data.subjects || [];
    box.innerHTML = "";
    if (allSubjects.length === 0) {
      box.innerHTML = emptyHtml("Hozircha battle uchun yetarli savol yo'q — o'qituvchi testlar qo'shgach shu yerda paydo bo'ladi.");
      return;
    }
    allSubjects.forEach(s => {
      const row = document.createElement("div");
      row.className = "admin-row";
      row.innerHTML = `
        <div class="emoji">⚔️</div>
        <div class="info">
          <div class="t">${escapeHtml(s.subject)}</div>
          <div class="s">🏅 ${s.elo} ELO · ${escapeHtml(s.tier)} · ${s.wins}G/${s.losses}M/${s.draws}D</div>
        </div>
        <div class="row-actions">
          <button data-a="play">⚔️ Jang qiling</button>
        </div>
      `;
      row.querySelector('[data-a="play"]').addEventListener("click", () => startBattle(s.subject));
      box.appendChild(row);
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

async function startBattle(subject) {
  try {
    const res = await apiFetch(`/api/games/battle/join`, {
      method: "POST",
      body: JSON.stringify({ subject })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Jangga qo'shilib bo'lmadi");
    }
    const data = await res.json();
    currentQuiz = {
      battleId: data.battle_id,
      subject,
      questions: data.questions,
      index: 0,
      answers: {},
      startedAt: Date.now(),
    };
    showScreen("game-quiz");
    renderQuizQuestion();
  } catch (e) {
    console.error(e);
    if (tg.showAlert) tg.showAlert(e.message || "Xatolik yuz berdi");
    else alert(e.message || "Xatolik yuz berdi");
  }
}

// ================================================================
// BATTLE SAVOLLARI
// ================================================================

function renderQuizQuestion() {
  const { questions, index, answers } = currentQuiz;
  const total = questions.length;
  const question = questions[index];
  const answeredCount = Object.keys(answers).length;

  document.getElementById("gameQuizProgressFill").style.width = `${(answeredCount / total) * 100}%`;

  const options = [
    ["1", question.option_1], ["2", question.option_2],
    ["3", question.option_3], ["4", question.option_4]
  ];
  const selectedIndex = answers[question.id];

  const navButtons = questions.map((q, i) => {
    const cls = ["qnav-btn"];
    if (i === index) cls.push("qnav-current");
    if (answers[q.id] !== undefined) cls.push("qnav-answered");
    return `<button type="button" class="${cls.join(" ")}" data-index="${i}">${i + 1}</button>`;
  }).join("");

  const content = document.getElementById("gameQuizContent");
  content.innerHTML = `
    <div class="question-counter">${index + 1} / ${total}-SAVOL · ${answeredCount}/${total} javob berilgan</div>
    <div class="question-nav-grid">${navButtons}</div>
    <div class="question-card">
      <div class="question-text">${question.question_text}</div>
      ${question.image_url ? `<img class="question-image" src="${question.image_url}" alt="Savol rasmi">` : ""}
      ${renderQuestionTables(question.table_data)}
    </div>
    <div class="option-list" id="gameOptionList">
      ${options.map(([idx, text]) => `
        <button class="option-btn ${parseInt(idx) === selectedIndex ? "option-selected-neutral" : ""}" data-option-index="${idx}">
          <span class="option-letter">${idx}</span><span>${text}</span>
        </button>
      `).join("")}
    </div>
    <div class="test-nav-actions">
      <button class="secondary-btn" id="gamePrevBtn" ${index === 0 ? "disabled" : ""}>← Oldingi</button>
      <button class="secondary-btn" id="gameNextBtn" ${index === total - 1 ? "disabled" : ""}>Keyingi →</button>
    </div>
    <div class="finish-test-wrap">
      <button class="gold-btn" id="gameFinishBtn" ${answeredCount < total ? "disabled" : ""}>⚔️ Javoblarni yuborish</button>
    </div>
  `;

  document.querySelectorAll("#gameOptionList .option-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      currentQuiz.answers[question.id] = parseInt(btn.getAttribute("data-option-index"));
      renderQuizQuestion();
    });
  });

  document.getElementById("gamePrevBtn").addEventListener("click", () => {
    if (currentQuiz.index > 0) { currentQuiz.index -= 1; renderQuizQuestion(); }
  });
  document.getElementById("gameNextBtn").addEventListener("click", () => {
    if (currentQuiz.index < total - 1) { currentQuiz.index += 1; renderQuizQuestion(); }
  });
  document.getElementById("gameFinishBtn").addEventListener("click", submitQuiz);
}

async function submitQuiz() {
  const timeSeconds = Math.round((Date.now() - currentQuiz.startedAt) / 1000);
  try {
    const res = await apiFetch(`/api/games/battle/${currentQuiz.battleId}/submit`, {
      method: "POST",
      body: JSON.stringify({ answers: currentQuiz.answers, time_seconds: timeSeconds })
    });
    const battle = await res.json();
    renderBattleResult(battle);
    showScreen("game-result");
  } catch (e) {
    console.error(e);
    if (tg.showAlert) tg.showAlert("Natijani yuborib bo'lmadi. Qayta urinib ko'ring.");
  }
}

// ================================================================
// NATIJA / KUTISH EKRANI
// ================================================================

function renderBattleResult(battle) {
  const content = document.getElementById("gameResultContent");

  if (battle.status !== "finished") {
    content.innerHTML = `
      <div class="test-detail-hero">
        <div style="font-size:40px;margin-bottom:10px;">⏳</div>
        <h3>Raqib qidirilmoqda...</h3>
        <p style="color:var(--text-dim);font-size:13px;margin-top:8px;">
          Sizning javoblaringiz saqlandi (${battle.my_score}/${battle.questions_count || 5} to'g'ri).
          Raqib topilib jang yakunlangach, "Mening janglarim" bo'limida natijani ko'rasiz —
          shuningdek Telegram orqali ham xabar beramiz.
        </p>
        <button class="gold-btn" style="margin-top:16px;" id="gameResultToBattlesBtn">⚔️ Mening janglarim</button>
      </div>
    `;
    document.getElementById("gameResultToBattlesBtn").addEventListener("click", () => navigateTo("game-battles"));
    return;
  }

  const resultLabel = { win: "🏆 G'ALABA!", lose: "😔 Mag'lubiyat", draw: "🤝 Durrang" }[battle.result] || "";
  const eloDiff = (battle.my_elo_after ?? 0) - (battle.my_elo_before ?? 0);
  const eloSign = eloDiff > 0 ? "+" : "";
  const eloColor = eloDiff > 0 ? "var(--success)" : eloDiff < 0 ? "var(--danger)" : "var(--text-dim)";

  content.innerHTML = `
    <div class="test-detail-hero">
      <h3>${resultLabel}</h3>
      <p style="color:var(--text-dim);font-size:13px;margin-top:6px;">
        ${escapeHtml(battle.opponent_name || "Raqib")}ga qarshi · ${battle.subject}
      </p>
      <div style="display:flex; justify-content:center; gap:24px; margin-top:18px;">
        <div><div style="font-size:22px;font-weight:800;">${battle.my_score}</div><div style="font-size:11px;color:var(--text-dim);">Siz</div></div>
        <div style="font-size:22px;font-weight:800;color:var(--text-dim);">:</div>
        <div><div style="font-size:22px;font-weight:800;">${battle.opponent_score}</div><div style="font-size:11px;color:var(--text-dim);">Raqib</div></div>
      </div>
      <div style="margin-top:16px; font-weight:800; font-size:15px; color:${eloColor};">
        ELO: ${battle.my_elo_before} → ${battle.my_elo_after} (${eloSign}${eloDiff})
      </div>
      <button class="gold-btn" style="margin-top:18px;" id="gameResultPlayAgainBtn">⚔️ Yana o'ynash</button>
    </div>
  `;
  document.getElementById("gameResultPlayAgainBtn").addEventListener("click", () => navigateTo("games"));
}

// ================================================================
// MENING JANGLARIM
// ================================================================

export async function loadMyBattles() {
  const box = document.getElementById("gameBattlesList");
  box.innerHTML = skeletonCards(3);
  try {
    const res = await apiFetch(`/api/games/my-battles`);
    const data = await res.json();
    box.innerHTML = "";
    if (data.battles.length === 0) {
      box.innerHTML = emptyHtml("Hali jang qilmagansiz — O'yinlar bo'limidan fan tanlab boshlang!");
      return;
    }
    data.battles.forEach(b => {
      const row = document.createElement("div");
      row.className = "admin-row";
      let statusLabel;
      if (b.status !== "finished") {
        statusLabel = "⏳ Raqib kutilmoqda";
      } else {
        const labels = { win: "🏆 G'alaba", lose: "😔 Mag'lubiyat", draw: "🤝 Durrang" };
        const eloDiff = (b.my_elo_after ?? 0) - (b.my_elo_before ?? 0);
        const sign = eloDiff > 0 ? "+" : "";
        statusLabel = `${labels[b.result] || ""} · ELO ${sign}${eloDiff}`;
      }
      row.innerHTML = `
        <div class="emoji">⚔️</div>
        <div class="info">
          <div class="t">${escapeHtml(b.subject)} ${b.opponent_name ? "vs " + escapeHtml(b.opponent_name) : ""}</div>
          <div class="s">${statusLabel}</div>
        </div>
      `;
      row.addEventListener("click", async () => {
        const res2 = await apiFetch(`/api/games/battle/${b.id}`);
        const fresh = await res2.json();
        renderBattleResult(fresh);
        navigateTo("game-result");
      });
      box.appendChild(row);
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

// ================================================================
// Modulni ishga tushirish
// ================================================================

export function initGamesModule() {
  document.getElementById("myBattlesBtn").addEventListener("click", () => {
    loadMyBattles();
    navigateTo("game-battles");
  });
  document.getElementById("exitGameQuizBtn").addEventListener("click", () => {
    const ok = confirm("Jangdan chiqmoqchimisiz? Joriy javoblaringiz saqlanmaydi.");
    if (!ok) return;
    currentQuiz = null;
    navigateTo("games");
  });
}
