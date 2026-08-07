// js/chemGame.js
// ==========================================================================
//  KIMYO O'YINI — talaba interfeysi
// ==========================================================================
// Ekranlar zanjiri:
//   O'yinlar (fan) -> Kimyo HUB -> Kategoriya -> Level yo'lagi -> Level
//                                              -> O'yin (4 bosqich) -> Natija
//                  -> Moddalar lug'ati -> Modda kartasi
//
// DIZAYN QARORI: barcha 4 bosqich BITTA ekranda (`screen-chem-play`)
// ko'rsatiladi. Har bosqichning o'z render funksiyasi bor, lekin sarlavha,
// progress chizig'i va chiqish tugmasi umumiy — shunda o'quvchi bosqichdan
// bosqichga o'tganda interfeys "sakramaydi".

import { apiFetch, tg } from "./api.js";
import { showScreen } from "./navigate.js";
import { errorHtml, emptyHtml, skeletonCards } from "./components.js";

// Joriy holat. Bitta obyektda saqlanadi — ekranlar orasida sakraganda
// nima ochiq ekanini bilish uchun (masalan "orqaga" tugmasi).
const state = {
  categoryId: null,
  categoryTitle: "",
  levelId: null,
  levelTitle: "",
  play: null,        // {stage, items, index, answers, correct, boards, ...}
};

function esc(str) {
  const d = document.createElement("div");
  d.textContent = str == null ? "" : String(str);
  return d.innerHTML;
}

function haptic(kind) {
  try { tg.HapticFeedback && tg.HapticFeedback.notificationOccurred(kind); } catch (e) {}
}

function starsHtml(count, max = 3) {
  let out = "";
  for (let i = 0; i < max; i++) {
    out += `<span class="chem-star${i < count ? " filled" : ""}">★</span>`;
  }
  return out;
}

// ==========================================================================
//  1. O'YINLAR — fan tanlash
// ==========================================================================

export async function loadGameSubjects() {
  const box = document.getElementById("gameSubjectsList");
  box.innerHTML = skeletonCards(2);
  try {
    const res = await apiFetch(`/api/chem/hub`);
    const data = await res.json();
    const ready = (data.categories || []).filter(c => c.is_ready);
    const totalSub = ready.reduce((s, c) => s + (c.substance_count || 0), 0);

    box.innerHTML = `
      <div class="game-subject-card active" id="chemSubjectCard">
        <div class="game-subject-top">
          <div class="game-subject-icon">🧪</div>
          <div class="game-subject-badge">${data.earned_stars || 0} / ${data.total_stars || 0} ★</div>
        </div>
        <div class="game-subject-title">Kimyo</div>
        <div class="game-subject-desc">Modda nomlari, formulalar, ranglar, reaksiyalar</div>
        <div class="game-subject-chips">
          <span class="game-chip">Levellar</span>
          <span class="game-chip">Lug'at</span>
          <span class="game-chip">Battle</span>
        </div>
        <button class="game-subject-btn" type="button">O'ynash →</button>
      </div>

      <div class="game-subject-card bio" id="bioSubjectCard">
        <div class="game-subject-top">
          <div class="game-subject-icon">🧬</div>
          <div class="game-subject-badge" id="bioStarsBadge">0 / 0 ★</div>
        </div>
        <div class="game-subject-title">Biologiya</div>
        <div class="game-subject-desc">Hujayra, organ tizimlari, genetika, botanika</div>
        <div class="game-subject-chips">
          <span class="game-chip">Ketma-ketlik</span>
          <span class="game-chip">Guruhlash</span>
          <span class="game-chip">Kim men?</span>
        </div>
        <button class="game-subject-btn" type="button">O'ynash →</button>
      </div>`;

    if (totalSub === 0) {
      box.querySelector("#chemSubjectCard .game-subject-desc").textContent =
        "O'qituvchi moddalar bazasini to'ldirgach shu yerda levellar paydo bo'ladi.";
    }
    box.querySelector("#chemSubjectCard .game-subject-btn")
       .addEventListener("click", openChemHub);
    box.querySelector("#bioSubjectCard .game-subject-btn")
       .addEventListener("click", () => document.dispatchEvent(
         new CustomEvent("app:navigate", { detail: { target: "bio-hub" } })));

    // Biologiya yulduzlarini alohida so'rov bilan to'ldiramiz — kimyo
    // kartasi darhol ko'rinsin, biologiya biroz keyin yangilansin.
    apiFetch(`/api/bio/hub`).then(r => r.json()).then(b => {
      const badge = document.getElementById("bioStarsBadge");
      if (badge) badge.textContent = `${b.earned_stars || 0} / ${b.total_stars || 0} ★`;
    }).catch(() => {});
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml("O'yinlarni yuklab bo'lmadi.");
  }
}

// ==========================================================================
//  2. KIMYO HUB
// ==========================================================================

export async function openChemHub() {
  showScreen("chem-hub");
  const box = document.getElementById("chemHubContent");
  box.innerHTML = skeletonCards(3);
  try {
    // Ikkala so'rov birga — ekran ikki bosqichda "sakramasin".
    const [hubRes, ratRes] = await Promise.all([
      apiFetch(`/api/chem/hub`),
      apiFetch(`/api/chem/battle/me/rating`),
    ]);
    const data = await hubRes.json();
    const rat = await ratRes.json();
    const r = rat.rating || {};
    const mission = rat.daily_mission || { done: 0, target: 3 };
    const cats = data.categories || [];
    const readyCount = cats.filter(c => c.is_ready).length;

    box.innerHTML = `
      <button class="chem-elo-card" id="chemEloCard" type="button">
        <span class="chem-elo-value">${r.elo ?? 1000}</span>
        <span class="chem-elo-text">
          <span class="chem-elo-label">UMUMIY ELO</span>
          <span class="chem-elo-tier">${r.tier ? r.tier.icon + " " + r.tier.name : "🥉 Bronza"} · #${r.rank ?? "—"}</span>
          <span class="chem-elo-stats">${r.wins ?? 0} G'  ·  ${r.losses ?? 0} M  ·  ${r.win_rate ?? 0}%  ·  🔥${r.current_streak ?? 0}</span>
        </span>
        <span class="chem-hub-row-chev">›</span>
      </button>

      <div class="chem-mission">
        <span class="chem-mission-icon">✨</span>
        <span class="chem-mission-text">Kunlik missiya · ${mission.target} ta battle</span>
        <span class="chem-mission-count">${mission.done}/${mission.target}</span>
        <div class="chem-mission-bar">
          <div class="chem-mission-fill" style="width:${Math.round(mission.done / mission.target * 100)}%"></div>
        </div>
      </div>

      <div class="chem-hub-stars">
        <div class="chem-hub-stars-value">${data.earned_stars || 0}<span>/${data.total_stars || 0}</span></div>
        <div class="chem-hub-stars-label">YULDUZ TO'PLANDI</div>
        <div class="chem-hub-stars-bar">
          <div class="chem-hub-stars-fill" style="width:${data.total_stars ? Math.round(data.earned_stars / data.total_stars * 100) : 0}%"></div>
        </div>
      </div>

      <div class="section-label">O'RGANISH</div>
      <button class="chem-hub-row" id="chemLearnBtn" type="button">
        <span class="chem-hub-row-icon">🎯</span>
        <span class="chem-hub-row-text">
          <span class="chem-hub-row-title">Levellar bilan o'rganish</span>
          <span class="chem-hub-row-sub">${readyCount} ta kategoriya — oson→qiyin bosqichlar</span>
        </span>
        <span class="chem-hub-row-chev">›</span>
      </button>
      <button class="chem-hub-row" id="chemDictBtn" type="button">
        <span class="chem-hub-row-icon">📖</span>
        <span class="chem-hub-row-text">
          <span class="chem-hub-row-title">Moddalar lug'ati</span>
          <span class="chem-hub-row-sub">Formula, rang, cho'kma, reaksiyalar</span>
        </span>
        <span class="chem-hub-row-chev">›</span>
      </button>

      <button class="primary-btn chem-battle-cta" id="chemBattleCta" type="button">⚔️ Battle o'ynash</button>

      <div class="section-label">O'YIN REJIMLARI</div>
      <div class="chem-mode-grid">
        <button class="chem-mode-card" id="chemModeRanked" type="button"><span class="chem-mode-icon">⚔️</span>
          <span class="chem-mode-title">Battle 1v1</span>
          <span class="chem-mode-sub">Aralash savollar · ELO</span></button>
        <button class="chem-mode-card" id="chemModeInvite" type="button"><span class="chem-mode-icon">👥</span>
          <span class="chem-mode-title">Do'stga taklif</span>
          <span class="chem-mode-sub">Kod orqali</span></button>
        <button class="chem-mode-card" id="chemModeBot" type="button"><span class="chem-mode-icon">🤖</span>
          <span class="chem-mode-title">Bot bilan mashq</span>
          <span class="chem-mode-sub">ELO'siz, darhol</span></button>
        <button class="chem-mode-card" id="chemModeTournament" type="button"><span class="chem-mode-icon">🏆</span>
          <span class="chem-mode-title">Chempionat</span>
          <span class="chem-mode-sub">Saralash → setka → final</span></button>
        <button class="chem-mode-card wide" id="chemModeHistory" type="button"><span class="chem-mode-icon">📜</span>
          <span class="chem-mode-title">Mening janglarim</span>
          <span class="chem-mode-sub">Natijalar tarixi</span></button>
      </div>`;

    document.getElementById("chemLearnBtn")
      .addEventListener("click", () => openChemCategories(cats));
    document.getElementById("chemDictBtn")
      .addEventListener("click", () => openChemDictionary());
    document.getElementById("chemEloCard").addEventListener("click", openChemRating);
    document.getElementById("chemBattleCta").addEventListener("click", () => startBattle("ranked"));
    document.getElementById("chemModeRanked").addEventListener("click", () => startBattle("ranked"));
    document.getElementById("chemModeBot").addEventListener("click", () => startBattle("bot"));
    document.getElementById("chemModeInvite").addEventListener("click", openChemInvite);
    document.getElementById("chemModeTournament").addEventListener("click", openChemTournaments);
    document.getElementById("chemModeHistory").addEventListener("click", openChemHistory);
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml("O'yin ma'lumotini yuklab bo'lmadi.");
  }
}

// ==========================================================================
//  3. KATEGORIYA TANLASH
// ==========================================================================

async function openChemCategories(cached) {
  showScreen("chem-categories");
  const box = document.getElementById("chemCategoryList");
  box.innerHTML = skeletonCards(3);
  try {
    const cats = cached || (await (await apiFetch(`/api/chem/hub`)).json()).categories || [];
    if (!cats.length) {
      box.innerHTML = emptyHtml("Hozircha kategoriya yo'q.");
      return;
    }
    box.innerHTML = cats.map(c => c.is_ready ? `
      <button class="chem-cat-row" type="button" data-cat="${c.id}" data-title="${esc(c.title)}">
        <span class="chem-cat-icon">${esc(c.icon || "🧪")}</span>
        <span class="chem-cat-text">
          <span class="chem-cat-title">${esc(c.title)}</span>
          <span class="chem-cat-sub">${esc(c.subtitle || "")} · ${c.level_count} level</span>
        </span>
        <span class="chem-cat-stars">${c.earned_stars}/${c.total_stars} ★</span>
      </button>` : `
      <div class="chem-cat-row soon">
        <span class="chem-cat-icon">${esc(c.icon || "🧪")}</span>
        <span class="chem-cat-text">
          <span class="chem-cat-title">${esc(c.title)}</span>
          <span class="chem-cat-sub">Tayyorlanmoqda</span>
        </span>
        <span class="chem-cat-soon">TEZ ORADA</span>
      </div>`).join("");

    box.querySelectorAll("button[data-cat]").forEach(btn => {
      btn.addEventListener("click", () =>
        openChemPath(parseInt(btn.dataset.cat, 10), btn.dataset.title));
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml("Kategoriyalarni yuklab bo'lmadi.");
  }
}

// ==========================================================================
//  4. LEVEL YO'LAGI
// ==========================================================================

async function openChemPath(categoryId, title) {
  state.categoryId = categoryId;
  state.categoryTitle = title || "Levellar";
  showScreen("chem-path");
  document.getElementById("chemPathTitle").textContent = state.categoryTitle;

  const box = document.getElementById("chemPathContent");
  box.innerHTML = skeletonCards(4);
  try {
    const res = await apiFetch(`/api/chem/category/${categoryId}/path`);
    if (!res.ok) {
      box.innerHTML = errorHtml((await res.json()).detail || "Ochib bo'lmadi.");
      return;
    }
    const data = await res.json();
    if (!data.levels.length) {
      box.innerHTML = emptyHtml("Bu kategoriyada hali level yo'q.");
      return;
    }

    const summary = `
      <div class="chem-path-summary">
        <div class="chem-path-summary-title">${esc(data.category.title)}</div>
        <div class="chem-path-summary-sub">
          ${data.substance_count} modda · ${data.level_count} level · ${data.earned_stars}/${data.total_stars} yulduz
        </div>
      </div>`;

    const nodes = data.levels.map((lv, i) => {
      const cls = lv.completed ? "done" : (lv.unlocked ? "open" : "locked");
      const inner = lv.completed ? "✓" : (lv.unlocked ? (i + 1) : "🔒");
      return `
        <div class="chem-node-wrap">
          ${i > 0 ? '<div class="chem-node-line"></div>' : ""}
          <button class="chem-node ${cls}" type="button"
                  ${lv.unlocked ? `data-level="${lv.id}" data-title="${esc(lv.title)}"` : "disabled"}>
            ${inner}
          </button>
          <div class="chem-node-title ${lv.unlocked ? "" : "muted"}">${esc(lv.title)}
            <span class="chem-node-count">(${lv.substance_count})</span>
          </div>
          ${lv.completed ? `<div class="chem-node-stars">${starsHtml(lv.stars)}</div>` : ""}
        </div>`;
    }).join("");

    box.innerHTML = summary + `<div class="chem-path">${nodes}</div>`;
    box.querySelectorAll("button[data-level]").forEach(btn => {
      btn.addEventListener("click", () =>
        openChemLevel(parseInt(btn.dataset.level, 10), btn.dataset.title));
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml("Levellarni yuklab bo'lmadi.");
  }
}

// ==========================================================================
//  5. LEVEL ICHI — 4 bosqich
// ==========================================================================

const STAGE_ICONS = { 1: "📇", 2: "✅", 3: "🔗", 4: "✍️" };
const STAGE_SUBS = {
  1: "Moddalarni ko'rib yodlang",
  2: "Variantlardan to'g'risini tanlang",
  3: "Formula va nomni juftlang",
  4: "Formulani o'zingiz yozing",
};

async function openChemLevel(levelId, title) {
  state.levelId = levelId;
  state.levelTitle = title || "Level";
  showScreen("chem-level");
  document.getElementById("chemLevelHeading").textContent = state.levelTitle;

  const box = document.getElementById("chemLevelContent");
  box.innerHTML = skeletonCards(4);
  try {
    const res = await apiFetch(`/api/chem/level/${levelId}`);
    if (!res.ok) {
      box.innerHTML = errorHtml((await res.json()).detail || "Levelni ochib bo'lmadi.");
      return;
    }
    const d = await res.json();
    const extra = Math.max(0, d.substance_count - d.preview_formulas.length);

    const rows = d.stages.map(s => {
      const cls = s.done ? "done" : (s.unlocked ? "current" : "locked");
      const badge = s.done ? "BAJARILDI" : (s.unlocked ? "HOZIR" : "🔒");
      return `
        <button class="chem-stage-row ${cls}" type="button"
                ${s.unlocked ? `data-stage="${s.stage}"` : "disabled"}>
          <span class="chem-stage-icon">${STAGE_ICONS[s.stage]}</span>
          <span class="chem-stage-text">
            <span class="chem-stage-title">${s.stage}. ${esc(s.title)}</span>
            <span class="chem-stage-sub">${d.substance_count} ta · ${STAGE_SUBS[s.stage]}</span>
          </span>
          <span class="chem-stage-badge">${badge}</span>
        </button>`;
    }).join("");

    box.innerHTML = `
      <div class="chem-level-hero">
        <div class="chem-level-hero-icon">🧪</div>
        <div class="chem-level-hero-title">${esc(d.level.title)}</div>
        <div class="chem-level-hero-sub">${d.substance_count} ta moddani 4 bosqichda o'rganasiz</div>
        <div class="chem-level-hero-chips">
          ${d.preview_formulas.map(f => `<span class="chem-formula-chip">${esc(f)}</span>`).join("")}
          ${extra ? `<span class="chem-formula-chip">+${extra}</span>` : ""}
        </div>
      </div>
      ${rows}
      ${d.next_stage
        ? `<button class="primary-btn chem-start-btn" id="chemStartBtn" type="button">▶ ${d.next_stage}-bosqichni boshlash</button>`
        : `<div class="chem-level-done">🎉 Bu level to'liq yakunlandi. Yulduzni ko'tarish uchun bosqichlarni qayta o'ynashingiz mumkin.</div>`}`;

    box.querySelectorAll("button[data-stage]").forEach(btn => {
      btn.addEventListener("click", () => startStage(levelId, parseInt(btn.dataset.stage, 10)));
    });
    const startBtn = document.getElementById("chemStartBtn");
    if (startBtn) startBtn.addEventListener("click", () => startStage(levelId, d.next_stage));
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml("Levelni yuklab bo'lmadi.");
  }
}

// ==========================================================================
//  6. O'YIN — 4 bosqich
// ==========================================================================

async function startStage(levelId, stage) {
  showScreen("chem-play");
  const content = document.getElementById("chemPlayContent");
  const footer = document.getElementById("chemPlayFooter");
  content.innerHTML = skeletonCards(1);
  footer.innerHTML = "";

  try {
    const res = await apiFetch(`/api/chem/level/${levelId}/stage/${stage}`);
    if (!res.ok) {
      content.innerHTML = errorHtml((await res.json()).detail || "Bosqichni ochib bo'lmadi.");
      return;
    }
    const d = await res.json();
    document.getElementById("chemPlayLabel").textContent =
      `${stage}-BOSQICH · ${(d.stage_title || "").toUpperCase()}`;

    state.play = {
      levelId, stage, total: d.total, index: 0,
      answers: [], correct: 0,
      cards: d.cards || [], questions: d.questions || [], boards: d.boards || [],
      boardIndex: 0, selectedLeft: null, foundPairs: 0,
    };

    if (stage === 1) renderCard();
    else if (stage === 2) renderTestQuestion();
    else if (stage === 3) renderMatchBoard();
    else renderWriteQuestion();
  } catch (e) {
    console.error(e);
    content.innerHTML = errorHtml("Bosqichni yuklab bo'lmadi.");
  }
}

function setProgress(done, total) {
  const fill = document.getElementById("chemPlayProgress");
  fill.style.width = total ? `${Math.round(done / total * 100)}%` : "0%";
}

// ---------- 1-bosqich: O'RGANISH ----------

function renderCard() {
  const p = state.play;
  const card = p.cards[p.index];
  setProgress(p.index, p.total);

  document.getElementById("chemPlayContent").innerHTML = `
    <div class="chem-play-hint">Yodlab oling — keyin sinov bo'ladi</div>
    <div class="chem-play-counter">${p.index + 1} / ${p.total}</div>
    <div class="chem-card">
      <div class="chem-card-formula">${esc(card.formula)}</div>
      <div class="chem-card-name">${esc(card.name)}</div>
      ${card.extras.length ? `
        <div class="chem-card-extras">
          ${card.extras.map(x => `
            <div class="chem-card-extra">
              <span class="chem-card-extra-label">${esc(x.label)}</span>
              <span class="chem-card-extra-value">${esc(x.value)}</span>
            </div>`).join("")}
        </div>` : ""}
    </div>`;

  document.getElementById("chemPlayFooter").innerHTML = `
    ${p.index > 0 ? '<button class="chem-back-mini" id="chemCardBack" type="button">←</button>' : ""}
    <button class="primary-btn chem-next-btn" id="chemCardNext" type="button">O'rgandim ✓</button>`;

  const back = document.getElementById("chemCardBack");
  if (back) back.addEventListener("click", () => { p.index--; renderCard(); });
  document.getElementById("chemCardNext").addEventListener("click", () => {
    p.index++;
    if (p.index >= p.cards.length) finishStage();
    else renderCard();
  });
}

// ---------- 2-bosqich: TEST ----------

function renderTestQuestion() {
  const p = state.play;
  const q = p.questions[p.index];
  setProgress(p.index, p.total);
  document.getElementById("chemPlayFooter").innerHTML = "";

  document.getElementById("chemPlayContent").innerHTML = `
    <div class="chem-play-counter">Savol ${p.index + 1} / ${p.total}</div>
    <div class="chem-prompt">
      <div class="chem-prompt-label">${esc(q.prompt_label)}</div>
      <div class="chem-prompt-value">${esc(q.prompt_value)}</div>
      <div class="chem-prompt-question">${esc(q.question_text)}</div>
    </div>
    <div class="chem-options">
      ${q.options.map((o, i) => `
        <button class="chem-option" type="button" data-i="${i}">${esc(o)}</button>`).join("")}
    </div>`;

  document.querySelectorAll(".chem-option").forEach(btn => {
    btn.addEventListener("click", () => answerTest(parseInt(btn.dataset.i, 10)));
  });
}

function answerTest(chosen) {
  const p = state.play;
  const q = p.questions[p.index];
  const isCorrect = chosen === q.correct_index;

  p.answers.push({ substance_id: q.substance_id, type: q.type, answer: q.options[chosen] });
  if (isCorrect) p.correct++;
  haptic(isCorrect ? "success" : "error");

  const btns = document.querySelectorAll(".chem-option");
  btns.forEach((b, i) => {
    b.disabled = true;
    if (i === q.correct_index) b.classList.add("correct");
    if (i === chosen && !isCorrect) b.classList.add("wrong");
  });

  if (!isCorrect) {
    document.getElementById("chemPlayFooter").innerHTML =
      `<div class="chem-answer-bar">✗ To'g'ri javob: <b>${esc(q.correct_answer)}</b></div>`;
  }

  setTimeout(() => {
    p.index++;
    if (p.index >= p.questions.length) finishStage();
    else renderTestQuestion();
  }, isCorrect ? 450 : 1400);
}

// ---------- 3-bosqich: MOSLASHTIRISH ----------

function renderMatchBoard() {
  const p = state.play;
  const board = p.boards[p.boardIndex];
  setProgress(p.foundPairs, p.total);
  document.getElementById("chemPlayFooter").innerHTML = "";

  document.getElementById("chemPlayContent").innerHTML = `
    <div class="chem-play-hint">Avval formulani, keyin nomini bosing</div>
    <div class="chem-play-counter">
      ${p.boardIndex + 1}/${p.boards.length} taxta · ${p.foundPairs}/${p.total} juftlik topildi
    </div>
    <div class="chem-match">
      <div class="chem-match-col">
        ${board.left.map(x => `<button class="chem-match-item" type="button"
            data-side="left" data-sid="${x.substance_id}">${esc(x.text)}</button>`).join("")}
      </div>
      <div class="chem-match-col">
        ${board.right.map(x => `<button class="chem-match-item" type="button"
            data-side="right" data-sid="${x.substance_id}">${esc(x.text)}</button>`).join("")}
      </div>
    </div>`;

  document.querySelectorAll(".chem-match-item").forEach(btn => {
    btn.addEventListener("click", () => onMatchClick(btn));
  });
}

function onMatchClick(btn) {
  const p = state.play;
  if (btn.classList.contains("matched")) return;

  if (btn.dataset.side === "left") {
    document.querySelectorAll('.chem-match-item[data-side="left"]')
      .forEach(b => b.classList.remove("selected"));
    btn.classList.add("selected");
    p.selectedLeft = btn;
    return;
  }

  // O'ng ustun bosildi — juftlikni tekshiramiz
  if (!p.selectedLeft) return;
  const sid = p.selectedLeft.dataset.sid;

  if (sid === btn.dataset.sid) {
    haptic("success");
    p.selectedLeft.classList.remove("selected");
    p.selectedLeft.classList.add("matched");
    btn.classList.add("matched");
    p.foundPairs++;
    p.correct++;
    p.answers.push({ substance_id: parseInt(sid, 10), type: "match", answer: "1" });
    p.selectedLeft = null;
    setProgress(p.foundPairs, p.total);

    const left = document.querySelectorAll('.chem-match-item[data-side="left"]:not(.matched)');
    if (left.length === 0) {
      setTimeout(() => {
        p.boardIndex++;
        if (p.boardIndex >= p.boards.length) finishStage();
        else renderMatchBoard();
      }, 500);
    }
  } else {
    // Xato juftlik — qisqa qizil chaqnash, lekin jazolamaymiz:
    // moslashtirish bosqichi mashq, o'quvchi qayta urinib ko'radi.
    haptic("error");
    const wrongLeft = p.selectedLeft;
    btn.classList.add("wrong");
    wrongLeft.classList.add("wrong");
    setTimeout(() => {
      btn.classList.remove("wrong");
      wrongLeft.classList.remove("wrong", "selected");
    }, 450);
    p.selectedLeft = null;
  }
}

// ---------- 4-bosqich: YOZISH ----------

function renderWriteQuestion() {
  const p = state.play;
  const q = p.questions[p.index];
  setProgress(p.index, p.total);

  document.getElementById("chemPlayContent").innerHTML = `
    <div class="chem-play-counter">Savol ${p.index + 1} / ${p.total}</div>
    <div class="chem-prompt">
      <div class="chem-prompt-label">${esc(q.prompt_label)}</div>
      <div class="chem-prompt-value">${esc(q.prompt_value)}</div>
      <div class="chem-prompt-question">${esc(q.question_text)}</div>
    </div>
    <div class="chem-write-box">
      <input type="text" id="chemWriteInput" class="chem-write-input"
             placeholder="${esc(q.hint.first_char)}..." autocomplete="off"
             autocapitalize="off" spellcheck="false">
      <div class="chem-write-hint">${q.hint.length} ta belgi · indekslarni oddiy raqam bilan yozsangiz ham bo'ladi (H2SO4)</div>
    </div>
    <div id="chemWriteFeedback"></div>`;

  document.getElementById("chemPlayFooter").innerHTML =
    `<button class="primary-btn chem-next-btn" id="chemWriteBtn" type="button">Tekshirish</button>`;

  const input = document.getElementById("chemWriteInput");
  input.focus();
  input.addEventListener("keydown", e => { if (e.key === "Enter") checkWrite(); });
  document.getElementById("chemWriteBtn").addEventListener("click", checkWrite);
}

async function checkWrite() {
  const p = state.play;
  const q = p.questions[p.index];
  const input = document.getElementById("chemWriteInput");
  const value = input.value.trim();
  if (!value) return;

  const btn = document.getElementById("chemWriteBtn");
  btn.disabled = true;
  input.disabled = true;

  try {
    const res = await apiFetch(`/api/chem/level/${p.levelId}/stage/4/check`, {
      method: "POST",
      body: JSON.stringify({ substance_id: q.substance_id, answer: value }),
    });
    const d = await res.json();

    p.answers.push({ substance_id: q.substance_id, type: "write_formula", answer: value });
    if (d.correct) p.correct++;
    haptic(d.correct ? "success" : "error");

    input.classList.add(d.correct ? "correct" : "wrong");
    document.getElementById("chemWriteFeedback").innerHTML = d.correct
      ? `<div class="chem-answer-bar ok">✓ To'g'ri</div>`
      : `<div class="chem-answer-bar">✗ To'g'ri javob: <b>${esc(d.correct_answer)}</b></div>`;

    setTimeout(() => {
      p.index++;
      if (p.index >= p.questions.length) finishStage();
      else renderWriteQuestion();
    }, d.correct ? 700 : 1600);
  } catch (e) {
    console.error(e);
    btn.disabled = false;
    input.disabled = false;
  }
}

// ---------- Natija ----------

async function finishStage() {
  const p = state.play;
  setProgress(1, 1);
  const content = document.getElementById("chemPlayContent");
  const footer = document.getElementById("chemPlayFooter");
  footer.innerHTML = "";
  content.innerHTML = `<div class="chem-result-loading">Natija hisoblanmoqda...</div>`;

  try {
    const res = await apiFetch(`/api/chem/level/${p.levelId}/stage/${p.stage}/submit`, {
      method: "POST",
      body: JSON.stringify({ answers: p.answers }),
    });
    const d = await res.json();
    haptic(d.stars >= 2 ? "success" : "warning");

    content.innerHTML = `
      <div class="chem-result">
        <div class="chem-result-icon">${d.stars >= 2 ? "🏆" : "💪"}</div>
        <div class="chem-result-title">${d.stars >= 2 ? "Ajoyib!" : "Yaxshi urinish"}</div>
        <div class="chem-result-sub">Bosqichni yakunladingiz</div>
        <div class="chem-result-stars">${starsHtml(d.stars)}</div>
        ${d.coins_earned ? `<div class="chem-result-coins">+${d.coins_earned} coin</div>` : ""}
        <div class="chem-result-stats">
          <div class="chem-result-stat">
            <div class="chem-result-stat-value">${d.accuracy}%</div>
            <div class="chem-result-stat-label">ANIQLIK</div>
          </div>
          <div class="chem-result-stat">
            <div class="chem-result-stat-value">${d.correct}/${d.total}</div>
            <div class="chem-result-stat-label">TO'G'RI</div>
          </div>
        </div>
        ${d.level_completed ? `<div class="chem-result-note">🎉 Level to'liq yakunlandi — keyingisi ochildi!</div>` : ""}
      </div>`;

    footer.innerHTML = `
      ${d.next_stage
        ? `<button class="primary-btn chem-next-btn" id="chemResultNext" type="button">Davom etish →</button>`
        : `<button class="primary-btn chem-next-btn" id="chemResultDone" type="button">Yakunlash</button>`}
      <button class="secondary-btn chem-retry-btn" id="chemResultRetry" type="button">Yana o'ynash</button>`;

    const next = document.getElementById("chemResultNext");
    if (next) next.addEventListener("click", () => startStage(p.levelId, d.next_stage));
    const done = document.getElementById("chemResultDone");
    if (done) done.addEventListener("click", () => openChemPath(state.categoryId, state.categoryTitle));
    document.getElementById("chemResultRetry")
      .addEventListener("click", () => startStage(p.levelId, p.stage));
  } catch (e) {
    console.error(e);
    content.innerHTML = errorHtml("Natijani saqlab bo'lmadi.");
  }
}

// ==========================================================================
//  7. MODDALAR LUG'ATI
// ==========================================================================

let dictTimer = null;

async function openChemDictionary() {
  showScreen("chem-dictionary");
  loadDictionary("");
}

async function loadDictionary(query) {
  const box = document.getElementById("chemDictList");
  box.innerHTML = skeletonCards(4);
  try {
    const res = await apiFetch(`/api/chem/dictionary?q=${encodeURIComponent(query)}`);
    const d = await res.json();
    if (!d.items.length) {
      box.innerHTML = emptyHtml(query ? "Hech narsa topilmadi." : "Lug'at hali bo'sh.");
      return;
    }
    box.innerHTML = d.items.map(s => `
      <button class="chem-dict-row" type="button" data-id="${s.id}">
        <span class="chem-dict-chip">${esc((s.formula || "").slice(0, 4))}</span>
        <span class="chem-dict-text">
          <span class="chem-dict-formula">${esc(s.formula)}</span>
          <span class="chem-dict-name">${esc(s.name)}</span>
        </span>
      </button>`).join("");
    box.querySelectorAll("button[data-id]").forEach(btn => {
      btn.addEventListener("click", () => openSubstance(parseInt(btn.dataset.id, 10)));
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml("Lug'atni yuklab bo'lmadi.");
  }
}

async function openSubstance(id) {
  showScreen("chem-substance");
  const box = document.getElementById("chemSubstanceContent");
  box.innerHTML = skeletonCards(1);
  try {
    const s = await (await apiFetch(`/api/chem/substance/${id}`)).json();
    const chip = (label, value) => `
      <div class="chem-sub-chip">
        <div class="chem-sub-chip-label">${label}</div>
        <div class="chem-sub-chip-value">${esc(value || "yo'q")}</div>
      </div>`;
    const block = (label, value) => `
      <div class="chem-sub-block">
        <div class="chem-sub-block-label">${label}</div>
        <div class="chem-sub-block-value">${esc(value || "kiritilmagan")}</div>
      </div>`;

    box.innerHTML = `
      <div class="chem-sub-hero">
        <div class="chem-sub-formula">${esc(s.formula)}</div>
        <div class="chem-sub-name">${esc(s.name)}</div>
        ${s.historic_name ? `<div class="chem-sub-historic">Tarixiy nomi: <b>${esc(s.historic_name)}</b></div>` : ""}
      </div>
      <div class="chem-sub-chips">
        ${chip("SOF HOLDA", s.color_pure)}
        ${chip("ERITMADA", s.color_solution)}
        ${chip("CHO'KMA", s.color_precipitate)}
      </div>
      ${block("REAKSIYALAR", s.reactions)}
      ${block("QO'LLANILISHI", s.usage_text)}`;
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml("Moddani yuklab bo'lmadi.");
  }
}

// ==========================================================================
//  8. BATTLE (1v1 / bot / do'st)
// ==========================================================================

// Bitta o'yin holati. `api` — qaysi endpointlar ishlatilishi: shu tufayli
// AYNAN SHU ekran battle uchun ham, chempionat saralashi va setka o'yini
// uchun ham qayta ishlatiladi (kod takrorlanmaydi).
let battle = null;

async function startBattle(mode) {
  showScreen("chem-battle");
  const content = document.getElementById("chemBattleContent");
  document.getElementById("chemBattleScore").innerHTML = "";
  document.getElementById("chemBattleProgress").style.width = "0%";
  content.innerHTML = `<div class="chem-result-loading">Raqib qidirilmoqda...</div>`;

  try {
    const res = await apiFetch(`/api/chem/battle/start`, {
      method: "POST", body: JSON.stringify({ mode }),
    });
    if (!res.ok) {
      content.innerHTML = errorHtml((await res.json()).detail || "Jangni boshlab bo'lmadi.");
      return;
    }
    const d = await res.json();
    enterBattle(d);
  } catch (e) {
    console.error(e);
    content.innerHTML = errorHtml("Jangni boshlab bo'lmadi.");
  }
}

function enterBattle(d) {
  const id = d.battle_id;
  battle = {
    id, total: d.total, index: 0, myScore: 0,
    oppName: d.opponent_name, oppElo: d.opponent_elo,
    myElo: d.my_elo, mode: d.mode, busy: false,
    api: {
      question: `/api/chem/battle/${id}/question`,
      answer: `/api/chem/battle/${id}/answer`,
      finish: `/api/chem/battle/${id}/finish`,
    },
    onFinish: showBattleResult,
    retry: () => startBattle(d.mode === "bot" ? "bot" : "ranked"),
  };
  document.getElementById("chemBattleLabel").textContent =
    d.mode === "bot" ? "MASHQ · KIMYOBOT" : "BATTLE 1v1";
  renderBattleScore(0, null);
  nextBattleQuestion();
}

function renderBattleScore(mine, theirs) {
  const b = battle;
  document.getElementById("chemBattleScore").innerHTML = `
    <div class="chem-bs-side">
      <div class="chem-bs-name">Siz</div>
      <div class="chem-bs-elo">${b.myElo} ELO</div>
    </div>
    <div class="chem-bs-mid">
      <span class="chem-bs-score">${mine}</span>
      <span class="chem-bs-sep">:</span>
      <span class="chem-bs-score dim">${theirs == null ? "?" : theirs}</span>
    </div>
    <div class="chem-bs-side right">
      <div class="chem-bs-name">${esc(b.oppName || "Raqib kutilmoqda")}</div>
      <div class="chem-bs-elo">${b.oppElo ? b.oppElo + " ELO" : "—"}</div>
    </div>`;
}

async function nextBattleQuestion() {
  const content = document.getElementById("chemBattleContent");
  try {
    const d = await (await apiFetch(battle.api.question)).json();
    if (d.finished) return finishBattle();

    battle.index = d.index;
    battle.myScore = d.my_score;
    renderBattleScore(d.my_score, null);
    document.getElementById("chemBattleProgress").style.width =
      `${Math.round((d.index - 1) / d.total * 100)}%`;

    const q = d.question;
    const letters = ["A", "B", "C", "D", "E"];
    content.innerHTML = `
      <div class="chem-play-counter">Savol ${d.index} / ${d.total}</div>
      <div class="chem-prompt">
        <div class="chem-prompt-label">${esc(q.prompt_label)}</div>
        <div class="chem-prompt-value">${esc(q.prompt_value)}</div>
        <div class="chem-prompt-question">${esc(q.question_text)}</div>
      </div>
      <div class="chem-options">
        ${q.options.map((o, i) => `
          <button class="chem-option battle" type="button" data-a="${esc(o)}">
            <span class="chem-option-letter">${letters[i]}</span>${esc(o)}
          </button>`).join("")}
      </div>
      <div id="chemBattleFeedback" class="chem-battle-feedback"></div>`;

    battle.busy = false;
    content.querySelectorAll(".chem-option").forEach(btn => {
      btn.addEventListener("click", () => answerBattle(btn));
    });
  } catch (e) {
    console.error(e);
    content.innerHTML = errorHtml("Savolni yuklab bo'lmadi.");
  }
}

async function answerBattle(btn) {
  if (battle.busy) return;
  battle.busy = true;
  document.querySelectorAll(".chem-option").forEach(b => b.disabled = true);

  try {
    const d = await (await apiFetch(battle.api.answer, {
      method: "POST", body: JSON.stringify({ answer: btn.dataset.a }),
    })).json();

    haptic(d.correct ? "success" : "error");
    btn.classList.add(d.correct ? "correct" : "wrong");
    if (!d.correct) {
      document.querySelectorAll(".chem-option").forEach(b => {
        if (b.dataset.a === d.correct_answer) b.classList.add("correct");
      });
      document.getElementById("chemBattleFeedback").innerHTML =
        `<div class="chem-answer-bar">✗ To'g'ri javob: <b>${esc(d.correct_answer)}</b></div>`;
    }
    renderBattleScore(d.my_score, null);

    setTimeout(() => {
      if (d.finished) finishBattle();
      else nextBattleQuestion();
    }, d.correct ? 500 : 1300);
  } catch (e) {
    console.error(e);
    battle.busy = false;
  }
}

async function finishBattle() {
  document.getElementById("chemBattleProgress").style.width = "100%";
  document.getElementById("chemBattleContent").innerHTML =
    `<div class="chem-result-loading">Natija hisoblanmoqda...</div>`;
  try {
    const d = await (await apiFetch(battle.api.finish, { method: "POST" })).json();
    battle.onFinish(d);
  } catch (e) {
    console.error(e);
    document.getElementById("chemBattleContent").innerHTML =
      errorHtml("Natijani saqlab bo'lmadi.");
  }
}

function showBattleResult(d) {
  showScreen("chem-battle-result");
  const box = document.getElementById("chemBattleResultContent");

  // Raqib hali javob bermagan bo'lsa — jang "kutish" holatida qoladi.
  if (d.status !== "finished") {
    box.innerHTML = `
      <div class="chem-result">
        <div class="chem-result-icon">⏳</div>
        <div class="chem-result-title">Raqib kutilmoqda</div>
        <div class="chem-result-sub">Siz ${d.my_score}/${d.total} to'g'ri javob berdingiz.</div>
        <div class="chem-result-note">
          Raqib qo'shilishi bilan natija chiqadi va sizga Telegram orqali xabar keladi.
          10 daqiqada hech kim qo'shilmasa, Kimyobot bilan yakunlanadi.
        </div>
      </div>
      <button class="primary-btn chem-start-btn" id="chemBattleAgain" type="button">Yana o'ynash</button>`;
    document.getElementById("chemBattleAgain")
      .addEventListener("click", () => startBattle(d.mode === "bot" ? "bot" : "ranked"));
    return;
  }

  const icons = { win: "🏆", lose: "😔", draw: "🤝" };
  const titles = { win: "G'alaba!", lose: "Mag'lubiyat", draw: "Durang" };
  haptic(d.result === "win" ? "success" : (d.result === "draw" ? "warning" : "error"));

  const delta = d.elo_delta;
  const eloRow = d.mode === "bot"
    ? `<div class="chem-result-note">Mashq rejimi — ELO o'zgarmaydi.</div>`
    : `<div class="chem-elo-change ${delta > 0 ? "up" : (delta < 0 ? "down" : "")}">
         ELO: ${d.elo_before} → <b>${d.elo_after}</b> (${delta > 0 ? "+" : ""}${delta})
       </div>`;

  box.innerHTML = `
    <div class="chem-result">
      <div class="chem-result-icon">${icons[d.result] || "⚔️"}</div>
      <div class="chem-result-title">${titles[d.result] || "Natija"}</div>
      <div class="chem-result-sub">${esc(d.opponent_name || "Raqib")}${d.is_bot ? " 🤖" : ""}</div>
      <div class="chem-result-vs">
        <span class="chem-result-vs-num">${d.my_score}</span>
        <span class="chem-result-vs-sep">:</span>
        <span class="chem-result-vs-num">${d.opponent_score}</span>
      </div>
      ${eloRow}
      <div class="chem-result-tier">${d.my_tier.icon} ${d.my_tier.name} · ${d.my_elo} ELO</div>
    </div>
    <button class="primary-btn chem-start-btn" id="chemBattleAgain" type="button">Yana o'ynash</button>`;

  document.getElementById("chemBattleAgain")
    .addEventListener("click", () => startBattle(d.mode === "bot" ? "bot" : "ranked"));
}

// ---------- Do'stga taklif ----------

async function openChemInvite() {
  showScreen("chem-invite");
  const box = document.getElementById("chemInviteContent");
  box.innerHTML = skeletonCards(1);
  try {
    const d = await (await apiFetch(`/api/chem/battle/invite`, {
      method: "POST", body: JSON.stringify({}),
    })).json();
    if (d.detail) { box.innerHTML = errorHtml(d.detail); return; }

    box.innerHTML = `
      <div class="chem-invite-card">
        <div class="chem-invite-label">O'YIN KODI</div>
        <div class="chem-invite-code">${esc(d.code)}</div>
        <div class="chem-invite-hint">Do'stingiz shu kodni kiritsa o'yin boshlanadi</div>
      </div>
      <button class="primary-btn chem-start-btn" id="chemShareBtn" type="button">📤 Telegramda ulashish</button>
      <div class="chem-invite-or">YOKI</div>
      <div class="chem-invite-join">
        <input type="text" id="chemJoinCode" class="chem-write-input small"
               placeholder="Do'stingiz kodini kiriting" maxlength="6"
               autocomplete="off" autocapitalize="characters" spellcheck="false">
        <button class="secondary-btn" id="chemJoinBtn" type="button">Kod bilan qo'shilish</button>
      </div>
      <div id="chemJoinError"></div>`;

    document.getElementById("chemShareBtn").addEventListener("click", () => {
      const text = `Kimyo battle o'ynaymizmi? Kodim: ${d.code}`;
      const url = `https://t.me/share/url?url=${encodeURIComponent(text)}`;
      if (tg.openTelegramLink) tg.openTelegramLink(url); else window.open(url, "_blank");
    });

    const input = document.getElementById("chemJoinCode");
    input.addEventListener("input", () => { input.value = input.value.toUpperCase(); });
    document.getElementById("chemJoinBtn").addEventListener("click", async () => {
      const code = input.value.trim();
      const err = document.getElementById("chemJoinError");
      if (code.length !== 6) { err.innerHTML = errorHtml("Kod 6 ta belgidan iborat."); return; }
      err.innerHTML = "";
      const res = await apiFetch(`/api/chem/battle/join-code`, {
        method: "POST", body: JSON.stringify({ code }),
      });
      const j = await res.json();
      if (!res.ok) { err.innerHTML = errorHtml(j.detail || "Qo'shilib bo'lmadi."); return; }
      showScreen("chem-battle");
      document.getElementById("chemBattleScore").innerHTML = "";
      document.getElementById("chemBattleContent").innerHTML = "";
      enterBattle(j);
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml("Taklif kodini olishda xato.");
  }
}

// ---------- Reyting ----------

async function openChemRating() {
  showScreen("chem-rating");
  const box = document.getElementById("chemRatingContent");
  box.innerHTML = skeletonCards(4);
  try {
    const d = await (await apiFetch(`/api/chem/battle/leaderboard`)).json();
    const me = d.me;
    if (!d.leaders.length) {
      box.innerHTML = emptyHtml("Hali hech kim battle o'ynamagan — birinchi bo'ling!");
      return;
    }
    const rows = d.leaders.map(x => `
      <div class="chem-rank-row${x.telegram_id === me.telegram_id ? " me" : ""}">
        <span class="chem-rank-num">#${x.rank}</span>
        <span class="chem-rank-avatar">${esc((x.first_name || "?").slice(0, 1).toUpperCase())}</span>
        <span class="chem-rank-text">
          <span class="chem-rank-name">${esc(x.first_name || "O'quvchi")}</span>
          <span class="chem-rank-sub">${x.wins} g'alaba · ${x.losses} mag'lubiyat</span>
        </span>
        <span class="chem-rank-right">
          <span class="chem-rank-elo">${x.elo}</span>
          <span class="chem-rank-tier">${x.tier.name}</span>
        </span>
      </div>`).join("");

    box.innerHTML = rows + (me.in_list ? "" : `
      <div class="chem-rank-row me sticky">
        <span class="chem-rank-num">#${me.rank}</span>
        <span class="chem-rank-avatar">S</span>
        <span class="chem-rank-text"><span class="chem-rank-name">Siz</span></span>
        <span class="chem-rank-right">
          <span class="chem-rank-elo">${me.elo}</span>
          <span class="chem-rank-tier">${me.tier.name}</span>
        </span>
      </div>`);
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml("Reytingni yuklab bo'lmadi.");
  }
}

// ---------- Janglar tarixi ----------

async function openChemHistory() {
  showScreen("chem-history");
  const box = document.getElementById("chemHistoryContent");
  box.innerHTML = skeletonCards(3);
  try {
    const d = await (await apiFetch(`/api/chem/battle/me/history`)).json();
    if (!d.battles.length) {
      box.innerHTML = emptyHtml("Hali jang o'ynamagansiz.");
      return;
    }
    const label = { win: "G'alaba", lose: "Mag'lubiyat", draw: "Durang" };
    box.innerHTML = d.battles.map(b => `
      <div class="chem-history-row ${b.result || "pending"}">
        <span class="chem-history-badge">${b.result ? label[b.result] : "Kutilmoqda"}</span>
        <span class="chem-history-text">
          <span class="chem-history-name">${esc(b.opponent_name)}${b.is_bot ? " 🤖" : ""}</span>
          <span class="chem-history-score">${b.my_score ?? "—"} : ${b.opponent_score ?? "—"}</span>
        </span>
        ${b.elo_delta ? `<span class="chem-history-elo ${b.elo_delta > 0 ? "up" : "down"}">
          ${b.elo_delta > 0 ? "+" : ""}${b.elo_delta}</span>` : ""}
      </div>`).join("");
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml("Tarixni yuklab bo'lmadi.");
  }
}

// ==========================================================================
//  9. CHEMPIONAT
// ==========================================================================

let tournamentId = null;

async function openChemTournaments() {
  showScreen("chem-tournaments");
  document.getElementById("chemTournamentCreate").classList.add("hidden");
  const box = document.getElementById("chemTournamentList");
  box.innerHTML = skeletonCards(3);
  try {
    const d = await (await apiFetch(`/api/chem/tournament/list`)).json();
    const official = d.tournaments.filter(t => t.is_official);
    const student = d.tournaments.filter(t => !t.is_official);

    const card = t => {
      const startText = t.status !== "open"
        ? (t.status === "qualifying" ? "Saralash ketmoqda" : "Setka ketmoqda")
        : (t.start_mode === "count"
            ? `${t.player_count}/${t.start_count} kishi yig'ilganda boshlanadi`
            : `Boshlanish: ${esc(t.start_at || "")}`);
      return `
        <div class="chem-tour-card${t.is_official ? " official" : ""}">
          <div class="chem-tour-top">
            <span class="chem-tour-icon">🏆</span>
            <span class="chem-tour-text">
              <span class="chem-tour-title">${esc(t.title)}</span>
              <span class="chem-tour-sub">${t.creator_name ? esc(t.creator_name) + " yaratgan · " : ""}Aralash savollar</span>
            </span>
            <span class="chem-tour-badge${t.elo_counts ? "" : " off"}">${t.elo_counts ? "ELO" : "ELO YO'Q"}</span>
          </div>
          ${t.prize_text ? `<div class="chem-tour-prize">🎁 ${esc(t.prize_text)}</div>` : ""}
          <div class="chem-tour-meta">${t.player_count} kishi · ${startText}</div>
          <button class="primary-btn chem-tour-btn" type="button" data-tour="${t.id}">
            ${t.joined ? "Ochish →" : "Qatnashish — bepul"}
          </button>
        </div>`;
    };

    box.innerHTML = `
      <div class="section-label">RASMIY CHEMPIONATLAR · SOVRINLI</div>
      ${official.length ? official.map(card).join("") : `
        <div class="chem-tour-empty">
          Hozircha rasmiy chempionat yo'q.<br>
          <span>Sovrinli chempionat e'lon qilinganda shu yerda, eng tepada paydo bo'ladi.</span>
        </div>`}

      <div class="section-label">O'QUVCHILAR CHEMPIONATLARI · FAQAT ELO</div>
      ${student.length ? student.map(card).join("") : `
        <div class="chem-tour-empty">Hozircha yo'q — birinchi bo'lib yarating!</div>`}

      <button class="chem-hub-row" id="chemTourCreateBtn" type="button" ${d.can_create ? "" : "disabled"}>
        <span class="chem-hub-row-icon">＋</span>
        <span class="chem-hub-row-text">
          <span class="chem-hub-row-title">Chempionat yaratish</span>
          <span class="chem-hub-row-sub">${d.can_create
            ? "Bepul, sovrinsiz — faqat ELO raqobati"
            : "Bugun allaqachon yaratgansiz — ertaga urinib ko'ring"}</span>
        </span>
      </button>

      <p class="games-foot-note">
        Format: saralash (teng yarmi o'tadi) → setka → final.
        ELO faqat 8 va undan ko'p qatnashchi bo'lsa hisoblanadi.
      </p>`;

    box.querySelectorAll("[data-tour]").forEach(btn => {
      btn.addEventListener("click", () => openTournament(parseInt(btn.dataset.tour, 10)));
    });
    const createBtn = document.getElementById("chemTourCreateBtn");
    if (createBtn && d.can_create) {
      createBtn.addEventListener("click", () => {
        document.getElementById("chemTournamentCreate").classList.remove("hidden");
        document.getElementById("chemTournamentCreate").scrollIntoView({ behavior: "smooth" });
      });
    }
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml("Chempionatlarni yuklab bo'lmadi.");
  }
}

async function openTournament(id) {
  tournamentId = id;
  showScreen("chem-tournament");
  const box = document.getElementById("chemTournamentDetail");
  box.innerHTML = skeletonCards(3);
  try {
    const res = await apiFetch(`/api/chem/tournament/${id}`);
    if (!res.ok) { box.innerHTML = errorHtml((await res.json()).detail || "Ochib bo'lmadi."); return; }
    renderTournament(await res.json());
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml("Chempionatni yuklab bo'lmadi.");
  }
}

function renderTournament(d) {
  const t = d.tournament;
  document.getElementById("chemTournamentTitle").textContent = t.title;
  const box = document.getElementById("chemTournamentDetail");

  const statusText = {
    open: "Ro'yxatga olish ochiq",
    qualifying: "Saralash bosqichi",
    bracket: `Setka · ${t.round_no}-bosqich`,
    finished: "Yakunlandi",
  }[t.status] || t.status;

  // "Hozir nima qilishim kerak?" — bitta aniq harakat.
  const actions = {
    join: ["Qatnashish — bepul", "join"],
    qualify: ["▶ Saralashni boshlash", "qualify"],
    play_match: ["⚔️ O'yinni boshlash", "match"],
  };
  const act = actions[d.my_action];
  const waitMsg = {
    wait_opponent: "Siz javob berdingiz — raqib javobini kutmoqdamiz.",
    wait_round: "Bu bosqichda o'yiningiz yo'q — keyingi bosqichni kuting.",
    eliminated: "Siz chempionatdan chiqib ketdingiz. Keyingi safar omad!",
  }[d.my_action];

  const podium = t.status === "finished"
    ? d.players.filter(p => p.place).sort((a, b) => a.place - b.place)
    : [];

  box.innerHTML = `
    <div class="chem-tour-hero">
      <div class="chem-tour-hero-status">${statusText}</div>
      <div class="chem-tour-hero-meta">
        ${t.player_count} qatnashchi ·
        ${t.elo_counts ? "ELO hisoblanadi" : "ELO hisoblanmaydi (8 kishidan kam)"}
      </div>
    </div>

    ${podium.length ? `
      <div class="chem-podium">
        ${podium.map(p => `
          <div class="chem-podium-row place-${p.place}">
            <span class="chem-podium-medal">${["🥇","🥈","🥉"][p.place - 1] || "🏅"}</span>
            <span class="chem-podium-name">${esc(p.name)}${p.is_me ? " (siz)" : ""}</span>
          </div>`).join("")}
      </div>` : ""}

    ${act ? `<button class="primary-btn chem-start-btn" id="chemTourActionBtn"
              data-act="${act[1]}">${act[0]}</button>` : ""}
    ${waitMsg ? `<div class="chem-tour-wait">${waitMsg}</div>` : ""}

    ${d.bracket.length ? `
      <div class="section-label">SETKA</div>
      ${d.bracket.map(r => `
        <div class="chem-bracket-round">
          <div class="chem-bracket-round-label">${r.round_no}-bosqich</div>
          ${r.matches.map(m => `
            <div class="chem-bracket-match${m.status === "finished" ? " done" : ""}">
              <span class="chem-bracket-p${m.winner && m.winner === m.p1 ? " win" : ""}">
                ${esc(m.p1 || "—")}<b>${m.p1_score ?? ""}</b></span>
              <span class="chem-bracket-vs">vs</span>
              <span class="chem-bracket-p${m.winner && m.winner === m.p2 ? " win" : ""}">
                ${esc(m.p2 || "—")}<b>${m.p2_score ?? ""}</b></span>
            </div>`).join("")}
        </div>`).join("")}` : ""}

    <div class="section-label">QATNASHCHILAR</div>
    ${d.players.map((p, i) => `
      <div class="chem-rank-row${p.is_me ? " me" : ""}">
        <span class="chem-rank-num">${p.seed ? "#" + p.seed : i + 1}</span>
        <span class="chem-rank-avatar">${esc((p.name || "?").slice(0, 1).toUpperCase())}</span>
        <span class="chem-rank-text">
          <span class="chem-rank-name">${esc(p.name)}${p.is_me ? " (siz)" : ""}</span>
          <span class="chem-rank-sub">${
            p.place ? `${p.place}-o'rin`
            : p.eliminated_round !== null && p.eliminated_round !== undefined
              ? "chiqib ketdi"
              : p.qual_done ? `saralash: ${p.qual_score}/10` : "hali o'ynamagan"
          }</span>
        </span>
      </div>`).join("")}`;

  const btn = document.getElementById("chemTourActionBtn");
  if (btn) btn.addEventListener("click", () => runTournamentAction(btn.dataset.act, d));
}

async function runTournamentAction(kind, d) {
  if (kind === "join") {
    const res = await apiFetch(`/api/chem/tournament/${tournamentId}/join`, { method: "POST" });
    if (!res.ok) {
      const j = await res.json();
      if (tg.showAlert) tg.showAlert(j.detail || "Qo'shilib bo'lmadi."); else alert(j.detail);
      return;
    }
    openTournament(tournamentId);
    return;
  }

  // Saralash yoki setka o'yini — battle ekranini qayta ishlatamiz.
  const base = kind === "qualify"
    ? `/api/chem/tournament/${tournamentId}/qual`
    : `/api/chem/tournament/match/${d.my_match_id}`;

  showScreen("chem-battle");
  document.getElementById("chemBattleScore").innerHTML = "";
  document.getElementById("chemBattleProgress").style.width = "0%";
  document.getElementById("chemBattleContent").innerHTML = "";
  document.getElementById("chemBattleLabel").textContent =
    kind === "qualify" ? "CHEMPIONAT · SARALASH"
                       : `CHEMPIONAT · ${d.tournament.round_no}-BOSQICH`;

  battle = {
    id: tournamentId, total: 10, index: 0, myScore: 0,
    oppName: kind === "qualify" ? "Barcha qatnashchilar" : "Raqib",
    oppElo: null, myElo: null, mode: "tournament", busy: false,
    api: { question: `${base}/question`, answer: `${base}/answer`, finish: `${base}/finish` },
    onFinish: () => openTournament(tournamentId),
    retry: () => openTournament(tournamentId),
  };
  renderBattleScore(0, null);
  nextBattleQuestion();
}

async function createTournament() {
  const title = document.getElementById("chemTitleInput").value.trim();
  if (!title) {
    if (tg.showAlert) tg.showAlert("Chempionat nomini kiriting."); else alert("Nom kiriting.");
    return;
  }
  const count = parseInt(document.getElementById("chemStartCount").value, 10) || 8;
  const res = await apiFetch(`/api/chem/tournament/create`, {
    method: "POST",
    body: JSON.stringify({ title, start_mode: "count", start_count: count }),
  });
  const j = await res.json();
  if (!res.ok) {
    if (tg.showAlert) tg.showAlert(j.detail || "Yaratib bo'lmadi."); else alert(j.detail);
    return;
  }
  document.getElementById("chemTitleInput").value = "";
  document.getElementById("chemTournamentCreate").classList.add("hidden");
  openTournament(j.id);
}

// ==========================================================================
//  Ishga tushirish
// ==========================================================================

export function initChemGameModule() {
  // O'yindan chiqish — level ekraniga qaytaradi (progress saqlanmaydi,
  // shuning uchun tasdiqlash so'raymiz).
  document.getElementById("chemPlayExitBtn").addEventListener("click", () => {
    const done = () => openChemLevel(state.levelId, state.levelTitle);
    const msg = "O'yindan chiqasizmi? Shu bosqichdagi natija saqlanmaydi.";
    if (tg.showConfirm) tg.showConfirm(msg, ok => { if (ok) done(); });
    else if (confirm(msg)) done();
  });

  // Battle'dan chiqish — javob berilgan savollar saqlanib qoladi, lekin
  // jang tugallanmagan hisoblanadi, shuning uchun ogohlantiramiz.
  document.getElementById("chemBattleExitBtn").addEventListener("click", () => {
    const msg = "Jangdan chiqasizmi? Tugatilmagan jang mag'lubiyat sifatida hisoblanishi mumkin.";
    if (tg.showConfirm) tg.showConfirm(msg, ok => { if (ok) openChemHub(); });
    else if (confirm(msg)) openChemHub();
  });

  // Chempionat yaratish formasi
  const tSave = document.getElementById("chemTournamentSaveBtn");
  if (tSave) tSave.addEventListener("click", createTournament);
  const tCancel = document.getElementById("chemTournamentCancelBtn");
  if (tCancel) tCancel.addEventListener("click", () =>
    document.getElementById("chemTournamentCreate").classList.add("hidden"));

  // Lug'at qidiruvi — har harfda so'rov yubormaslik uchun kechiktiriladi.
  const search = document.getElementById("chemDictSearch");
  search.addEventListener("input", () => {
    clearTimeout(dictTimer);
    dictTimer = setTimeout(() => loadDictionary(search.value.trim()), 300);
  });

}

/** Chempionatlar ro'yxatini ochadi (main.js navigatsiyasi uchun). */
export function openTournamentsScreen() { openChemTournaments(); }

/** "Orqaga" bosilganda level yo'lagini JORIY kategoriya bilan qayta ochadi. */
export function reopenChemPath() {
  if (state.categoryId) openChemPath(state.categoryId, state.categoryTitle);
  else openChemHub();
}
