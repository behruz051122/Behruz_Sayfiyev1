// js/bioGame.js
// ==========================================================================
//  BIOLOGIYA O'YINI — talaba interfeysi
// ==========================================================================
// KIMYODAN FARQI:
//   1) Bosqichlar ro'yxati QAT'IY EMAS — server qaysi o'yinlar mumkinligini
//      aytadi, interfeys shunga qarab chiziladi.
//   2) Uchta yangi o'yin mexanikasi bor:
//        Ketma-ketlik — bosqichlarni tartibga solish (yuqori/past tugmalari
//                       bilan; drag&drop telefonda ishonchsiz ishlaydi)
//        Guruhlash    — elementni savatga tashlash
//        Kim men?     — ipuchalar ketma-ket ochiladi, ball kamayadi
//        Rasm         — surat ustidagi nuqtani bosib, nomini tanlash
//   3) Vizual til boshqacha: zumrad-siyan (kimyoda firuza-binafsha) —
//      o'quvchi qaysi fanda ekanini rangdan bilib turadi.

import { apiFetch, tg } from "./api.js";
import { showScreen } from "./navigate.js";
import { errorHtml, emptyHtml, skeletonCards } from "./components.js";

const state = { topicId: null, topicTitle: "", levelId: null, levelTitle: "", play: null };

function esc(s) {
  const d = document.createElement("div");
  d.textContent = s == null ? "" : String(s);
  return d.innerHTML;
}

function haptic(kind) {
  try { tg.HapticFeedback && tg.HapticFeedback.notificationOccurred(kind); } catch (e) {}
}

function stars(n, max = 3) {
  let out = "";
  for (let i = 0; i < max; i++) out += `<span class="chem-star${i < n ? " filled" : ""}">★</span>`;
  return out;
}

const STAGE_ICONS = {
  learn: "📇", test: "✅", match: "🔗",
  sequence: "🔢", group: "🗂", whoami: "🕵️", image: "🖼",
};

// ==========================================================================
//  HUB
// ==========================================================================

export async function openBioHub() {
  showScreen("bio-hub");
  const box = document.getElementById("bioHubContent");
  box.innerHTML = skeletonCards(3);
  try {
    const d = await (await apiFetch(`/api/bio/hub`)).json();
    const topics = d.topics || [];
    const pct = d.total_stars ? Math.round(d.earned_stars / d.total_stars * 100) : 0;

    box.innerHTML = `
      <div class="bio-hero">
        <div class="bio-hero-ring">
          <div class="bio-hero-value">${d.earned_stars || 0}</div>
          <div class="bio-hero-max">/ ${d.total_stars || 0}</div>
        </div>
        <div class="bio-hero-text">
          <div class="bio-hero-title">Yulduzlar to'plandi</div>
          <div class="bio-hero-sub">4 ta mavzu · 7 xil o'yin</div>
          <div class="bio-hero-bar"><div class="bio-hero-fill" style="width:${pct}%"></div></div>
        </div>
      </div>

      <div class="section-label">MAVZULAR</div>
      ${topics.map(t => t.is_ready ? `
        <button class="bio-topic-card" type="button" data-topic="${t.id}" data-title="${esc(t.title)}">
          <span class="bio-topic-icon">${esc(t.icon || "🧬")}</span>
          <span class="bio-topic-text">
            <span class="bio-topic-title">${esc(t.title)}</span>
            <span class="bio-topic-sub">${esc(t.subtitle || "")} · ${t.level_count} level · ${t.term_count} termin</span>
            <span class="bio-topic-bar">
              <span class="bio-topic-fill" style="width:${t.total_stars ? Math.round(t.earned_stars / t.total_stars * 100) : 0}%"></span>
            </span>
          </span>
          <span class="bio-topic-stars">${t.earned_stars}/${t.total_stars} ★</span>
        </button>` : `
        <div class="bio-topic-card soon">
          <span class="bio-topic-icon">${esc(t.icon || "🧬")}</span>
          <span class="bio-topic-text">
            <span class="bio-topic-title">${esc(t.title)}</span>
            <span class="bio-topic-sub">Tayyorlanmoqda</span>
          </span>
          <span class="chem-cat-soon">TEZ ORADA</span>
        </div>`).join("")}

      <div class="section-label">O'YIN TURLARI</div>
      <div class="bio-modes">
        ${[["📇", "O'rganish"], ["✅", "Test"], ["🔗", "Juftlash"], ["🔢", "Ketma-ketlik"],
           ["🗂", "Guruhlash"], ["🕵️", "Kim men?"], ["🖼", "Rasm bo'yicha"]]
          .map(([i, t]) => `<span class="bio-mode-pill">${i} ${t}</span>`).join("")}
      </div>
      <p class="bio-modes-note">
        Har levelda qaysi o'yinlar borligi kiritilgan ma'lumotga bog'liq —
        jarayon qo'shilsa "Ketma-ketlik", rasm qo'shilsa "Rasm bo'yicha" o'yini ochiladi.
      </p>

      <button class="chem-hub-row" id="bioDictBtn" type="button">
        <span class="chem-hub-row-icon">📖</span>
        <span class="chem-hub-row-text">
          <span class="chem-hub-row-title">Biologiya lug'ati</span>
          <span class="chem-hub-row-sub">Termin, ta'rif, vazifa</span>
        </span>
        <span class="chem-hub-row-chev">›</span>
      </button>`;

    box.querySelectorAll("[data-topic]").forEach(btn => {
      btn.addEventListener("click", () =>
        openBioPath(parseInt(btn.dataset.topic, 10), btn.dataset.title));
    });
    document.getElementById("bioDictBtn").addEventListener("click", openBioDictionary);
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml("Biologiya bo'limini yuklab bo'lmadi.");
  }
}

// ==========================================================================
//  Level yo'lagi
// ==========================================================================

async function openBioPath(topicId, title) {
  state.topicId = topicId;
  state.topicTitle = title || "Levellar";
  showScreen("bio-path");
  document.getElementById("bioPathTitle").textContent = state.topicTitle;

  const box = document.getElementById("bioPathContent");
  box.innerHTML = skeletonCards(4);
  try {
    const res = await apiFetch(`/api/bio/topic/${topicId}/path`);
    if (!res.ok) { box.innerHTML = errorHtml((await res.json()).detail || "Ochib bo'lmadi."); return; }
    const d = await res.json();
    if (!d.levels.length) { box.innerHTML = emptyHtml("Bu mavzuda hali level yo'q."); return; }

    box.innerHTML = `
      <div class="chem-path-summary">
        <div class="chem-path-summary-title">${esc(d.topic.title)}</div>
        <div class="chem-path-summary-sub">
          ${d.term_count} termin · ${d.level_count} level · ${d.earned_stars}/${d.total_stars} yulduz
        </div>
      </div>
      <div class="chem-path">
        ${d.levels.map((lv, i) => {
          const cls = lv.completed ? "done" : (lv.unlocked ? "open" : "locked");
          const inner = lv.completed ? "✓" : (lv.unlocked ? (i + 1) : "🔒");
          const badges = [
            lv.has_sequence ? '<span class="bio-node-badge">🔢</span>' : "",
            lv.has_image ? '<span class="bio-node-badge">🖼</span>' : "",
          ].join("");
          return `
            <div class="chem-node-wrap">
              ${i > 0 ? '<div class="chem-node-line"></div>' : ""}
              <button class="chem-node ${cls}" type="button"
                      ${lv.unlocked ? `data-level="${lv.id}" data-title="${esc(lv.title)}"` : "disabled"}>
                ${inner}
              </button>
              <div class="chem-node-title ${lv.unlocked ? "" : "muted"}">${esc(lv.title)}
                <span class="chem-node-count">(${lv.stage_count} o'yin)</span> ${badges}
              </div>
              ${lv.completed ? `<div class="chem-node-stars">${stars(lv.stars)}</div>` : ""}
            </div>`;
        }).join("")}
      </div>`;

    box.querySelectorAll("[data-level]").forEach(btn => {
      btn.addEventListener("click", () =>
        openBioLevel(parseInt(btn.dataset.level, 10), btn.dataset.title));
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml("Levellarni yuklab bo'lmadi.");
  }
}

export function reopenBioPath() {
  if (state.topicId) openBioPath(state.topicId, state.topicTitle);
  else openBioHub();
}

// ==========================================================================
//  Level ichi — dinamik bosqichlar
// ==========================================================================

async function openBioLevel(levelId, title) {
  state.levelId = levelId;
  state.levelTitle = title || "Level";
  showScreen("bio-level");
  document.getElementById("bioLevelHeading").textContent = state.levelTitle;

  const box = document.getElementById("bioLevelContent");
  box.innerHTML = skeletonCards(4);
  try {
    const res = await apiFetch(`/api/bio/level/${levelId}`);
    if (!res.ok) { box.innerHTML = errorHtml((await res.json()).detail || "Ochib bo'lmadi."); return; }
    const d = await res.json();

    box.innerHTML = `
      <div class="bio-level-hero">
        <div class="bio-level-hero-icon">🧬</div>
        <div class="bio-level-hero-title">${esc(d.level.title)}</div>
        <div class="bio-level-hero-sub">
          ${d.term_count} termin · ${d.stages.length} xil o'yin
        </div>
        <div class="chem-level-hero-chips">
          ${d.preview_terms.map(t => `<span class="bio-term-chip">${esc(t)}</span>`).join("")}
        </div>
      </div>
      ${d.stages.map((s, i) => {
        const cls = s.done ? "done" : (s.unlocked ? "current" : "locked");
        const badge = s.done ? "BAJARILDI" : (s.unlocked ? "HOZIR" : "🔒");
        return `
          <button class="chem-stage-row ${cls}" type="button"
                  ${s.unlocked ? `data-stage="${s.key}"` : "disabled"}>
            <span class="chem-stage-icon">${STAGE_ICONS[s.key] || "🎯"}</span>
            <span class="chem-stage-text">
              <span class="chem-stage-title">${i + 1}. ${esc(s.title)}</span>
              <span class="chem-stage-sub">${esc(s.subtitle)}</span>
            </span>
            <span class="chem-stage-badge">${badge}</span>
          </button>`;
      }).join("")}
      ${d.next_stage
        ? `<button class="primary-btn chem-start-btn" id="bioStartBtn" type="button">▶ Boshlash</button>`
        : `<div class="chem-level-done">🎉 Bu level to'liq yakunlandi.</div>`}`;

    box.querySelectorAll("[data-stage]").forEach(btn => {
      btn.addEventListener("click", () => startStage(levelId, btn.dataset.stage));
    });
    const start = document.getElementById("bioStartBtn");
    if (start) start.addEventListener("click", () => startStage(levelId, d.next_stage));
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml("Levelni yuklab bo'lmadi.");
  }
}

// ==========================================================================
//  O'yin
// ==========================================================================

async function startStage(levelId, stageKey) {
  showScreen("bio-play");
  const content = document.getElementById("bioPlayContent");
  const footer = document.getElementById("bioPlayFooter");
  content.innerHTML = skeletonCards(1);
  footer.innerHTML = "";

  try {
    const res = await apiFetch(`/api/bio/level/${levelId}/stage/${stageKey}`);
    if (!res.ok) { content.innerHTML = errorHtml((await res.json()).detail || "Ochib bo'lmadi."); return; }
    const d = await res.json();
    document.getElementById("bioPlayLabel").textContent = (d.stage_title || "").toUpperCase();

    state.play = {
      levelId, stage: stageKey, total: d.total, index: 0, correct: 0,
      answers: [], data: d, boardIndex: 0, selectedLeft: null, found: 0,
      order: [], clueIndex: 0, points: 0, taskIndex: 0, solvedPoints: [],
    };

    ({
      learn: renderCard, test: renderTest, match: renderMatch,
      sequence: renderSequence, group: renderGroup,
      whoami: renderWhoAmI, image: renderImage,
    })[stageKey]();
  } catch (e) {
    console.error(e);
    content.innerHTML = errorHtml("Bosqichni yuklab bo'lmadi.");
  }
}

function progress(done, total) {
  document.getElementById("bioPlayProgress").style.width =
    total ? `${Math.round(done / total * 100)}%` : "0%";
}

const $c = () => document.getElementById("bioPlayContent");
const $f = () => document.getElementById("bioPlayFooter");

// ---------- 1. O'rganish ----------

function renderCard() {
  const p = state.play, card = p.data.cards[p.index];
  progress(p.index, p.total);
  $c().innerHTML = `
    <div class="chem-play-hint">Yodlab oling — keyin sinov bo'ladi</div>
    <div class="chem-play-counter">${p.index + 1} / ${p.total}</div>
    <div class="bio-card">
      <div class="bio-card-term">${esc(card.term)}</div>
      ${card.definition ? `<div class="bio-card-def">${esc(card.definition)}</div>` : ""}
      ${card.extras.length ? `
        <div class="chem-card-extras">
          ${card.extras.map(x => `
            <div class="chem-card-extra">
              <span class="chem-card-extra-label">${esc(x.label)}</span>
              <span class="chem-card-extra-value">${esc(x.value)}</span>
            </div>`).join("")}
        </div>` : ""}
    </div>`;
  $f().innerHTML = `
    ${p.index > 0 ? '<button class="chem-back-mini" id="bioCardBack" type="button">←</button>' : ""}
    <button class="primary-btn chem-next-btn" id="bioCardNext" type="button">O'rgandim ✓</button>`;
  const back = document.getElementById("bioCardBack");
  if (back) back.addEventListener("click", () => { p.index--; renderCard(); });
  document.getElementById("bioCardNext").addEventListener("click", () => {
    p.index++;
    if (p.index >= p.data.cards.length) finish();
    else renderCard();
  });
}

// ---------- 2. Test ----------

function renderTest() {
  const p = state.play, q = p.data.questions[p.index];
  progress(p.index, p.total);
  $f().innerHTML = "";
  $c().innerHTML = `
    <div class="chem-play-counter">Savol ${p.index + 1} / ${p.total}</div>
    <div class="bio-prompt">
      <div class="chem-prompt-label">${esc(q.prompt_label)}</div>
      <div class="bio-prompt-value">${esc(q.prompt_value)}</div>
      <div class="chem-prompt-question">${esc(q.question_text)}</div>
    </div>
    <div class="chem-options">
      ${q.options.map((o, i) => `<button class="chem-option bio" type="button" data-i="${i}">${esc(o)}</button>`).join("")}
    </div>`;
  document.querySelectorAll(".chem-option").forEach(b =>
    b.addEventListener("click", () => answerTest(parseInt(b.dataset.i, 10))));
}

function answerTest(chosen) {
  const p = state.play, q = p.data.questions[p.index];
  const ok = chosen === q.correct_index;
  p.answers.push({ term_id: q.term_id, type: q.type, answer: q.options[chosen] });
  if (ok) p.correct++;
  haptic(ok ? "success" : "error");

  document.querySelectorAll(".chem-option").forEach((b, i) => {
    b.disabled = true;
    if (i === q.correct_index) b.classList.add("correct");
    if (i === chosen && !ok) b.classList.add("wrong");
  });
  if (!ok) $f().innerHTML = `<div class="chem-answer-bar">✗ To'g'ri javob: <b>${esc(q.correct_answer)}</b></div>`;

  setTimeout(() => {
    p.index++;
    if (p.index >= p.data.questions.length) finish();
    else renderTest();
  }, ok ? 450 : 1600);
}

// ---------- 3. Juftlash ----------

function renderMatch() {
  const p = state.play, board = p.data.boards[p.boardIndex];
  progress(p.found, p.total);
  $f().innerHTML = "";
  $c().innerHTML = `
    <div class="chem-play-hint">Avval terminni, keyin ta'rifini bosing</div>
    <div class="chem-play-counter">${p.boardIndex + 1}/${p.data.boards.length} taxta · ${p.found}/${p.total} juftlik</div>
    <div class="bio-match">
      <div class="chem-match-col">
        ${board.left.map(x => `<button class="chem-match-item bio-term" type="button"
            data-side="left" data-id="${x.term_id}">${esc(x.text)}</button>`).join("")}
      </div>
      <div class="chem-match-col">
        ${board.right.map(x => `<button class="chem-match-item bio-def" type="button"
            data-side="right" data-id="${x.term_id}">${esc(x.text)}</button>`).join("")}
      </div>
    </div>`;
  document.querySelectorAll(".chem-match-item").forEach(b =>
    b.addEventListener("click", () => onMatch(b)));
}

function onMatch(btn) {
  const p = state.play;
  if (btn.classList.contains("matched")) return;
  if (btn.dataset.side === "left") {
    document.querySelectorAll('.chem-match-item[data-side="left"]').forEach(b => b.classList.remove("selected"));
    btn.classList.add("selected");
    p.selectedLeft = btn;
    return;
  }
  if (!p.selectedLeft) return;

  if (p.selectedLeft.dataset.id === btn.dataset.id) {
    haptic("success");
    p.selectedLeft.classList.remove("selected");
    p.selectedLeft.classList.add("matched");
    btn.classList.add("matched");
    p.found++; p.correct++;
    p.answers.push({ term_id: parseInt(btn.dataset.id, 10), type: "match",
                     answer: p.selectedLeft.textContent.trim() });
    p.selectedLeft = null;
    progress(p.found, p.total);
    if (!document.querySelectorAll('.chem-match-item[data-side="left"]:not(.matched)').length) {
      setTimeout(() => {
        p.boardIndex++;
        if (p.boardIndex >= p.data.boards.length) finish();
        else renderMatch();
      }, 480);
    }
  } else {
    haptic("error");
    const left = p.selectedLeft;
    btn.classList.add("wrong"); left.classList.add("wrong");
    setTimeout(() => {
      btn.classList.remove("wrong");
      left.classList.remove("wrong", "selected");
    }, 450);
    p.selectedLeft = null;
  }
}

// ---------- 4. KETMA-KETLIK ----------

function renderSequence() {
  const p = state.play, task = p.data.tasks[p.taskIndex];
  progress(p.taskIndex, p.total);
  if (!p.order.length) p.order = task.shuffled_steps.slice();

  $c().innerHTML = `
    <div class="chem-play-counter">Jarayon ${p.taskIndex + 1} / ${p.total}</div>
    <div class="bio-seq-head">
      <div class="bio-seq-title">${esc(task.title)}</div>
      ${task.description ? `<div class="bio-seq-desc">${esc(task.description)}</div>` : ""}
      <div class="bio-seq-hint">O'q tugmalari bilan to'g'ri tartibga keltiring</div>
    </div>
    <div class="bio-seq-list" id="bioSeqList">
      ${p.order.map((s, i) => `
        <div class="bio-seq-item" data-i="${i}">
          <span class="bio-seq-num">${i + 1}</span>
          <span class="bio-seq-text">${esc(s)}</span>
          <span class="bio-seq-arrows">
            <button class="bio-seq-arrow" type="button" data-up="${i}" ${i === 0 ? "disabled" : ""}>▲</button>
            <button class="bio-seq-arrow" type="button" data-down="${i}" ${i === p.order.length - 1 ? "disabled" : ""}>▼</button>
          </span>
        </div>`).join("")}
    </div>
    <div id="bioSeqFeedback"></div>`;

  $f().innerHTML = `<button class="primary-btn chem-next-btn" id="bioSeqCheck" type="button">Tekshirish</button>`;

  document.querySelectorAll("[data-up]").forEach(b => b.addEventListener("click", () => {
    const i = parseInt(b.dataset.up, 10);
    [p.order[i - 1], p.order[i]] = [p.order[i], p.order[i - 1]];
    renderSequence();
  }));
  document.querySelectorAll("[data-down]").forEach(b => b.addEventListener("click", () => {
    const i = parseInt(b.dataset.down, 10);
    [p.order[i + 1], p.order[i]] = [p.order[i], p.order[i + 1]];
    renderSequence();
  }));
  document.getElementById("bioSeqCheck").addEventListener("click", checkSequence);
}

async function checkSequence() {
  const p = state.play, task = p.data.tasks[p.taskIndex];
  const btn = document.getElementById("bioSeqCheck");
  btn.disabled = true;
  try {
    const r = await (await apiFetch(`/api/bio/level/${p.levelId}/check/sequence`, {
      method: "POST",
      body: JSON.stringify({ sequence_id: task.sequence_id, order: p.order }),
    })).json();

    haptic(r.correct ? "success" : "error");
    if (r.correct) {
      p.correct++;
      document.querySelectorAll(".bio-seq-item").forEach(el => el.classList.add("ok"));
      document.getElementById("bioSeqFeedback").innerHTML =
        `<div class="chem-answer-bar ok">✓ To'g'ri tartib!</div>`;
    } else {
      // Xato bo'lsa to'g'ri tartibni KO'RSATAMIZ — bu mashq, o'quvchi
      // taqqoslab o'rganishi kerak (musobaqa emas).
      document.querySelectorAll(".bio-seq-item").forEach((el, i) => {
        el.classList.add(p.order[i] === r.correct_order[i] ? "ok" : "bad");
      });
      document.getElementById("bioSeqFeedback").innerHTML = `
        <div class="chem-answer-bar">${r.in_place}/${r.total} tasi joyida</div>
        <div class="bio-seq-answer">
          <div class="bio-seq-answer-label">TO'G'RI TARTIB</div>
          ${r.correct_order.map((s, i) => `<div>${i + 1}. ${esc(s)}</div>`).join("")}
        </div>`;
    }

    $f().innerHTML = `<button class="primary-btn chem-next-btn" id="bioSeqNext" type="button">
      ${p.taskIndex + 1 >= p.total ? "Yakunlash" : "Keyingisi →"}</button>`;
    document.getElementById("bioSeqNext").addEventListener("click", () => {
      p.taskIndex++; p.order = [];
      if (p.taskIndex >= p.data.tasks.length) finish();
      else renderSequence();
    });
  } catch (e) {
    console.error(e);
    btn.disabled = false;
  }
}

// ---------- 5. GURUHLASH ----------

function renderGroup() {
  const p = state.play, task = p.data.task;
  if (!p.remaining) p.remaining = task.items.slice();
  progress(p.correct, p.total);

  if (!p.remaining.length) return finish();
  const item = p.remaining[0];

  $c().innerHTML = `
    <div class="chem-play-counter">${p.total - p.remaining.length + 1} / ${p.total}</div>
    <div class="bio-group-card">
      <div class="bio-group-label">BU QAYSI GURUHGA KIRADI?</div>
      <div class="bio-group-term">${esc(item.text)}</div>
    </div>
    <div class="bio-group-baskets">
      ${task.groups.map(g => `
        <button class="bio-basket" type="button" data-group="${esc(g)}">
          <span class="bio-basket-icon">🗂</span>
          <span class="bio-basket-name">${esc(g)}</span>
        </button>`).join("")}
    </div>
    <div id="bioGroupFeedback"></div>`;
  $f().innerHTML = "";

  document.querySelectorAll("[data-group]").forEach(b =>
    b.addEventListener("click", () => answerGroup(b, item)));
}

async function answerGroup(btn, item) {
  const p = state.play;
  document.querySelectorAll(".bio-basket").forEach(b => b.disabled = true);
  try {
    const r = await (await apiFetch(`/api/bio/level/${p.levelId}/check/group`, {
      method: "POST",
      body: JSON.stringify({ term_id: item.term_id, group: btn.dataset.group }),
    })).json();

    haptic(r.correct ? "success" : "error");
    btn.classList.add(r.correct ? "correct" : "wrong");
    if (r.correct) p.correct++;
    else {
      document.querySelectorAll(".bio-basket").forEach(b => {
        if (b.dataset.group === r.correct_group) b.classList.add("correct");
      });
      document.getElementById("bioGroupFeedback").innerHTML =
        `<div class="chem-answer-bar">✗ To'g'risi: <b>${esc(r.correct_group)}</b></div>`;
    }

    setTimeout(() => {
      p.remaining.shift();
      renderGroup();
    }, r.correct ? 500 : 1500);
  } catch (e) {
    console.error(e);
    document.querySelectorAll(".bio-basket").forEach(b => b.disabled = false);
  }
}

// ---------- 6. KIM MEN? ----------

function renderWhoAmI() {
  const p = state.play, task = p.data.tasks[p.taskIndex];
  progress(p.taskIndex, p.total);
  p.clueIndex = p.clueIndex || 0;
  const shown = task.clues.slice(0, p.clueIndex + 1);
  const possible = Math.max(1, (task.max_points || 4) - p.clueIndex);

  $c().innerHTML = `
    <div class="chem-play-counter">${p.taskIndex + 1} / ${p.total}</div>
    <div class="bio-whoami-head">
      <div class="bio-whoami-title">🕵️ Kim men?</div>
      <div class="bio-whoami-points">Hozir topsangiz: <b>${possible}</b> ball</div>
    </div>
    <div class="bio-clues">
      ${shown.map((c, i) => `
        <div class="bio-clue${i === shown.length - 1 ? " new" : ""}">
          <span class="bio-clue-num">${i + 1}</span>${esc(c)}
        </div>`).join("")}
    </div>
    ${p.clueIndex < task.clues.length - 1
      ? `<button class="secondary-btn bio-clue-more" id="bioMoreClue" type="button">
           Yana ipucha (−1 ball)</button>` : ""}
    <div class="chem-options">
      ${task.options.map(o => `<button class="chem-option bio" type="button" data-a="${esc(o)}">${esc(o)}</button>`).join("")}
    </div>
    <div id="bioWhoFeedback"></div>`;
  $f().innerHTML = "";

  const more = document.getElementById("bioMoreClue");
  if (more) more.addEventListener("click", () => { p.clueIndex++; renderWhoAmI(); });
  document.querySelectorAll(".chem-option").forEach(b =>
    b.addEventListener("click", () => answerWhoAmI(b, task)));
}

async function answerWhoAmI(btn, task) {
  const p = state.play;
  document.querySelectorAll(".chem-option").forEach(b => b.disabled = true);
  try {
    const r = await (await apiFetch(`/api/bio/level/${p.levelId}/check/whoami`, {
      method: "POST",
      body: JSON.stringify({ term_id: task.term_id, answer: btn.dataset.a,
                             clue_index: p.clueIndex }),
    })).json();

    haptic(r.correct ? "success" : "error");
    btn.classList.add(r.correct ? "correct" : "wrong");
    if (r.correct) {
      p.correct++;
      p.points += r.points;
      document.getElementById("bioWhoFeedback").innerHTML =
        `<div class="chem-answer-bar ok">✓ To'g'ri! +${r.points} ball</div>`;
    } else {
      document.querySelectorAll(".chem-option").forEach(b => {
        if (b.dataset.a === r.correct_answer) b.classList.add("correct");
      });
      document.getElementById("bioWhoFeedback").innerHTML =
        `<div class="chem-answer-bar">✗ To'g'risi: <b>${esc(r.correct_answer)}</b></div>`;
    }

    setTimeout(() => {
      p.taskIndex++; p.clueIndex = 0;
      if (p.taskIndex >= p.data.tasks.length) finish();
      else renderWhoAmI();
    }, r.correct ? 900 : 1700);
  } catch (e) {
    console.error(e);
    document.querySelectorAll(".chem-option").forEach(b => b.disabled = false);
  }
}

// ---------- 7. RASM BO'YICHA ----------

function renderImage() {
  const p = state.play, task = p.data.tasks[p.taskIndex];
  if (!p.solved) p.solved = [];
  progress(p.correct, p.total);

  $c().innerHTML = `
    <div class="chem-play-counter">${esc(task.title)} · ${p.solved.length}/${task.total}</div>
    <div class="bio-image-wrap">
      <img src="${esc(task.image_url)}" alt="${esc(task.title)}" class="bio-image">
      ${task.points.map(pt => `
        <button class="bio-point${p.solved.includes(pt.index) ? " solved" : ""}"
                type="button" data-point="${pt.index}"
                style="left:${pt.x}%; top:${pt.y}%">
          ${p.solved.includes(pt.index) ? "✓" : "?"}
        </button>`).join("")}
    </div>
    <div class="bio-image-hint">Nuqtani bosing, so'ng uning nomini tanlang</div>
    <div id="bioImageNames"></div>`;
  $f().innerHTML = "";

  document.querySelectorAll("[data-point]").forEach(b => {
    if (p.solved.includes(parseInt(b.dataset.point, 10))) return;
    b.addEventListener("click", () => pickImageName(parseInt(b.dataset.point, 10), task));
  });
}

function pickImageName(pointIndex, task) {
  document.querySelectorAll(".bio-point").forEach(b => b.classList.remove("active"));
  const dot = document.querySelector(`[data-point="${pointIndex}"]`);
  if (dot) dot.classList.add("active");

  document.getElementById("bioImageNames").innerHTML = `
    <div class="bio-name-list">
      ${task.names.map(n => `<button class="bio-name" type="button" data-n="${esc(n)}">${esc(n)}</button>`).join("")}
    </div>`;
  document.querySelectorAll(".bio-name").forEach(b =>
    b.addEventListener("click", () => answerImage(pointIndex, b, task)));
}

async function answerImage(pointIndex, btn, task) {
  const p = state.play;
  document.querySelectorAll(".bio-name").forEach(b => b.disabled = true);
  try {
    const r = await (await apiFetch(`/api/bio/level/${p.levelId}/check/image`, {
      method: "POST",
      body: JSON.stringify({ task_id: task.task_id, point_index: pointIndex,
                             name: btn.dataset.n }),
    })).json();

    haptic(r.correct ? "success" : "error");
    btn.classList.add(r.correct ? "correct" : "wrong");
    if (r.correct) { p.correct++; p.solved.push(pointIndex); }

    setTimeout(() => {
      if (p.solved.length >= task.total) {
        p.taskIndex++;
        p.solved = [];
        if (p.taskIndex >= p.data.tasks.length) return finish();
      }
      renderImage();
    }, r.correct ? 600 : 1200);
  } catch (e) {
    console.error(e);
    document.querySelectorAll(".bio-name").forEach(b => b.disabled = false);
  }
}

// ---------- Natija ----------

async function finish() {
  const p = state.play;
  progress(1, 1);
  $f().innerHTML = "";
  $c().innerHTML = `<div class="chem-result-loading">Natija hisoblanmoqda...</div>`;

  const body = ["test", "match"].includes(p.stage)
    ? { answers: p.answers }
    : { correct: p.correct, total: p.total };

  try {
    const d = await (await apiFetch(`/api/bio/level/${p.levelId}/stage/${p.stage}/submit`, {
      method: "POST", body: JSON.stringify(body),
    })).json();
    haptic(d.stars >= 2 ? "success" : "warning");

    $c().innerHTML = `
      <div class="bio-result">
        <div class="chem-result-icon">${d.stars >= 2 ? "🎉" : "💪"}</div>
        <div class="bio-result-title">${d.stars >= 2 ? "Ajoyib!" : "Yaxshi urinish"}</div>
        <div class="chem-result-sub">${esc(p.data.stage_title)} bosqichi yakunlandi</div>
        <div class="chem-result-stars">${stars(d.stars)}</div>
        ${d.coins_earned ? `<div class="chem-result-coins">+${d.coins_earned} coin</div>` : ""}
        ${p.stage === "whoami" && p.points
          ? `<div class="bio-result-points">Ipucha ballari: <b>${p.points}</b></div>` : ""}
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

    $f().innerHTML = `
      ${d.next_stage
        ? `<button class="primary-btn chem-next-btn" id="bioNext" type="button">Davom etish →</button>`
        : `<button class="primary-btn chem-next-btn" id="bioDone" type="button">Yakunlash</button>`}
      <button class="secondary-btn chem-retry-btn" id="bioRetry" type="button">Yana</button>`;

    const next = document.getElementById("bioNext");
    if (next) next.addEventListener("click", () => startStage(p.levelId, d.next_stage));
    const done = document.getElementById("bioDone");
    if (done) done.addEventListener("click", reopenBioPath);
    document.getElementById("bioRetry")
      .addEventListener("click", () => startStage(p.levelId, p.stage));
  } catch (e) {
    console.error(e);
    $c().innerHTML = errorHtml("Natijani saqlab bo'lmadi.");
  }
}

// ==========================================================================
//  Lug'at
// ==========================================================================

let dictTimer = null;

function openBioDictionary() {
  showScreen("bio-dictionary");
  loadBioDict("");
}

async function loadBioDict(query) {
  const box = document.getElementById("bioDictList");
  box.innerHTML = skeletonCards(4);
  try {
    const d = await (await apiFetch(`/api/bio/dictionary?q=${encodeURIComponent(query)}`)).json();
    if (!d.items.length) {
      box.innerHTML = emptyHtml(query ? "Hech narsa topilmadi." : "Lug'at hali bo'sh.");
      return;
    }
    box.innerHTML = d.items.map(t => `
      <button class="chem-dict-row" type="button" data-id="${t.id}">
        <span class="bio-dict-chip">${esc((t.term || "?").slice(0, 2))}</span>
        <span class="chem-dict-text">
          <span class="bio-dict-term">${esc(t.term)}</span>
          <span class="chem-dict-name">${esc(t.definition || t.level_title || "")}</span>
        </span>
      </button>`).join("");
    box.querySelectorAll("[data-id]").forEach(b =>
      b.addEventListener("click", () => openBioTerm(parseInt(b.dataset.id, 10))));
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml("Lug'atni yuklab bo'lmadi.");
  }
}

async function openBioTerm(id) {
  showScreen("bio-term");
  const box = document.getElementById("bioTermContent");
  box.innerHTML = skeletonCards(1);
  try {
    const t = await (await apiFetch(`/api/bio/term/${id}`)).json();
    const block = (label, value) => value ? `
      <div class="chem-sub-block">
        <div class="chem-sub-block-label">${label}</div>
        <div class="chem-sub-block-value">${esc(value)}</div>
      </div>` : "";
    box.innerHTML = `
      <div class="bio-term-hero">
        <div class="bio-term-name">${esc(t.term)}</div>
        ${t.group_name ? `<div class="bio-term-group">${esc(t.group_name)}</div>` : ""}
      </div>
      ${block("TA'RIFI", t.definition)}
      ${block("VAZIFASI", t.function_text)}
      ${block("QIZIQARLI FAKT", t.extra_fact)}`;
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml("Terminni yuklab bo'lmadi.");
  }
}

// ==========================================================================
//  Ishga tushirish
// ==========================================================================

export function initBioGameModule() {
  const exit = document.getElementById("bioPlayExitBtn");
  if (exit) exit.addEventListener("click", () => {
    const done = () => openBioLevel(state.levelId, state.levelTitle);
    const msg = "O'yindan chiqasizmi? Shu bosqichdagi natija saqlanmaydi.";
    if (tg.showConfirm) tg.showConfirm(msg, ok => { if (ok) done(); });
    else if (confirm(msg)) done();
  });

  const search = document.getElementById("bioDictSearch");
  if (search) search.addEventListener("input", () => {
    clearTimeout(dictTimer);
    dictTimer = setTimeout(() => loadBioDict(search.value.trim()), 300);
  });
}
