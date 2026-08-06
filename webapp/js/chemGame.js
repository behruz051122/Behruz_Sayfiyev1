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

      <div class="game-subject-card soon">
        <div class="game-subject-top">
          <div class="game-subject-icon">🧬</div>
          <div class="game-subject-badge soon">TEZ KUNDA</div>
        </div>
        <div class="game-subject-title">Biologiya</div>
        <div class="game-subject-desc">Organlar, tizimlar, genetika — tayyorlanmoqda</div>
      </div>`;

    if (totalSub === 0) {
      box.querySelector(".game-subject-desc").textContent =
        "O'qituvchi moddalar bazasini to'ldirgach shu yerda levellar paydo bo'ladi.";
    }
    box.querySelector("#chemSubjectCard .game-subject-btn")
       .addEventListener("click", openChemHub);
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
    const res = await apiFetch(`/api/chem/hub`);
    const data = await res.json();
    const cats = data.categories || [];
    const readyCount = cats.filter(c => c.is_ready).length;

    box.innerHTML = `
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

      <div class="section-label">O'YIN REJIMLARI</div>
      <div class="chem-mode-grid">
        <div class="chem-mode-card soon"><span class="chem-mode-icon">⚔️</span>
          <span class="chem-mode-title">Battle 1v1</span>
          <span class="chem-mode-sub">Tez orada</span></div>
        <div class="chem-mode-card soon"><span class="chem-mode-icon">👥</span>
          <span class="chem-mode-title">Do'stga taklif</span>
          <span class="chem-mode-sub">Tez orada</span></div>
        <div class="chem-mode-card soon"><span class="chem-mode-icon">🏆</span>
          <span class="chem-mode-title">Chempionat</span>
          <span class="chem-mode-sub">Tez orada</span></div>
        <div class="chem-mode-card soon"><span class="chem-mode-icon">🤖</span>
          <span class="chem-mode-title">Bot bilan mashq</span>
          <span class="chem-mode-sub">Tez orada</span></div>
      </div>`;

    document.getElementById("chemLearnBtn")
      .addEventListener("click", () => openChemCategories(cats));
    document.getElementById("chemDictBtn")
      .addEventListener("click", () => openChemDictionary());
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

  // Lug'at qidiruvi — har harfda so'rov yubormaslik uchun kechiktiriladi.
  const search = document.getElementById("chemDictSearch");
  search.addEventListener("input", () => {
    clearTimeout(dictTimer);
    dictTimer = setTimeout(() => loadDictionary(search.value.trim()), 300);
  });

}

/** "Orqaga" bosilganda level yo'lagini JORIY kategoriya bilan qayta ochadi. */
export function reopenChemPath() {
  if (state.categoryId) openChemPath(state.categoryId, state.categoryTitle);
  else openChemHub();
}
