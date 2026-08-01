// js/tests.js
import { apiFetch, tg } from "./api.js";
import { showScreen, navigateTo } from "./navigate.js";
import { loadingHtml, errorHtml, emptyHtml, DIFFICULTY_LABELS, formatSeconds, openLightbox } from "./components.js";
import { refreshCoins } from "./user.js";

let allTests = [];
let activeTestSubjectFilter = "Hammasi";
let myTestResults = [];
let currentTestMeta = null;      // ro'yxatdagi test kartasi ma'lumoti
let currentAttempt = null;       // { id, test, index, correctCount, coinsEarned, timeLeft, timerHandle, finished }

export function resetTestState() {
  stopTestTimer();
  currentAttempt = null;
  activeTestSubjectFilter = "Hammasi";
}

// ---------- Testlar ro'yxati ----------

export async function loadTestList() {
  const container = document.getElementById("testList");
  container.innerHTML = loadingHtml();
  try {
    const [testsRes, resultsRes] = await Promise.all([
      apiFetch(`/api/tests`),
      apiFetch(`/api/my-test-results`)
    ]);
    const testsData = await testsRes.json();
    const resultsData = await resultsRes.json();
    allTests = testsData.tests;
    myTestResults = resultsData.results;
    buildTestSubjectFilters();
    renderTestList();
  } catch (e) {
    console.error(e);
    container.innerHTML = errorHtml();
  }
}

function buildTestSubjectFilters() {
  const row = document.getElementById("testSubjectFilterRow");
  const subjects = ["Hammasi", ...new Set(allTests.map(t => t.subject))];
  row.innerHTML = "";
  subjects.forEach(subj => {
    const chip = document.createElement("button");
    chip.className = "filter-chip" + (subj === activeTestSubjectFilter ? " active" : "");
    chip.textContent = subj;
    chip.onclick = () => {
      activeTestSubjectFilter = subj;
      document.querySelectorAll("#testSubjectFilterRow .filter-chip").forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      renderTestList();
    };
    row.appendChild(chip);
  });
}

function bestResultForTest(testId) {
  return myTestResults.find(r => r.test_id === testId) || null;
}

function renderTestList() {
  const container = document.getElementById("testList");
  container.innerHTML = "";

  const filtered = activeTestSubjectFilter === "Hammasi"
    ? allTests
    : allTests.filter(t => t.subject === activeTestSubjectFilter);

  if (filtered.length === 0) {
    container.innerHTML = emptyHtml("Bu fan bo'yicha hozircha test yo'q");
    return;
  }

  filtered.forEach(test => {
    const best = bestResultForTest(test.id);
    const card = document.createElement("div");
    card.className = "test-card";
    card.innerHTML = `
      <div class="test-card-top">
        <div class="test-card-title">${test.title}</div>
        <span class="difficulty-badge difficulty-${test.difficulty}">${DIFFICULTY_LABELS[test.difficulty] || test.difficulty}</span>
      </div>
      <div class="test-card-meta">
        <span class="course-tag">${test.subject}</span>
        <span>❓ ${test.question_count} savol</span>
        <span>⏱ ${formatSeconds(test.time_limit_seconds)}</span>
      </div>
      ${best ? `<div class="test-card-best">🏆 Eng yaxshi natija: ${best.best_score}/${best.total_questions}</div>` : ""}
    `;
    card.addEventListener("click", () => openTestDetail(test));
    container.appendChild(card);
  });
}

// ---------- Test tafsiloti ----------

function openTestDetail(test) {
  currentTestMeta = test;
  document.getElementById("testDetailTitle").textContent = test.subject;
  const best = bestResultForTest(test.id);

  const content = document.getElementById("testDetailContent");
  content.innerHTML = `
    <div class="test-detail-hero">
      <span class="difficulty-badge difficulty-${test.difficulty}">${DIFFICULTY_LABELS[test.difficulty] || test.difficulty}</span>
      <h1>${test.title}</h1>
      <div class="test-detail-stats">
        <div class="test-detail-stat"><div class="num">${test.question_count}</div><div class="lbl">savol</div></div>
        <div class="test-detail-stat"><div class="num">${formatSeconds(test.time_limit_seconds)}</div><div class="lbl">vaqt</div></div>
      </div>
    </div>
    ${best ? `<div class="test-detail-prev-best">🏆 Oldingi eng yaxshi natijangiz: ${best.best_score}/${best.total_questions}</div>` : ""}
    <div class="test-detail-actions">
      <button class="gold-btn" id="startTestBtn">${best ? "🔁 Qayta urinish" : "▶ Testni boshlash"}</button>
    </div>
    <p style="text-align:center;color:var(--text-dim);font-size:11px;margin-top:14px;">
      Har bir savolga birinchi marta to'g'ri javob bersangiz — 1 🪙 coin olasiz. Vaqt tugasa, test avtomatik yakunlanadi.
    </p>
  `;
  document.getElementById("startTestBtn").addEventListener("click", () => startTest(test));

  showScreen("test-detail");
}

// ---------- Testni boshlash va topshirish ----------

async function startTest(test) {
  const btn = document.getElementById("startTestBtn");
  if (btn) { btn.disabled = true; btn.textContent = "Tayyorlanmoqda..."; }
  try {
    const [startRes, fullTestRes] = await Promise.all([
      apiFetch(`/api/test/${test.id}/start`, { method: "POST" }),
      apiFetch(`/api/test/${test.id}`)
    ]);
    const startData = await startRes.json();
    const fullTest = await fullTestRes.json();

    if (!fullTest.questions || fullTest.questions.length === 0) {
      tg.showAlert ? tg.showAlert("Bu testda hozircha savollar yo'q") : alert("Bu testda hozircha savollar yo'q");
      if (btn) { btn.disabled = false; btn.textContent = "▶ Testni boshlash"; }
      return;
    }

    currentAttempt = {
      id: startData.attempt_id,
      test: fullTest,
      index: 0,
      correctCount: 0,
      coinsEarned: 0,
      timeLeft: fullTest.time_limit_seconds,
      timerHandle: null,
      finished: false,
    };

    showScreen("test-taking");
    renderCurrentQuestion();
    startTestTimer();
  } catch (e) {
    console.error(e);
    if (btn) { btn.disabled = false; btn.textContent = "▶ Testni boshlash"; }
  }
}

function startTestTimer() {
  stopTestTimer();
  updateTimerDisplay();
  currentAttempt.timerHandle = setInterval(() => {
    currentAttempt.timeLeft -= 1;
    updateTimerDisplay();
    if (currentAttempt.timeLeft <= 0) {
      stopTestTimer();
      finishTest(true);
    }
  }, 1000);
}

function stopTestTimer() {
  if (currentAttempt && currentAttempt.timerHandle) {
    clearInterval(currentAttempt.timerHandle);
    currentAttempt.timerHandle = null;
  }
}

function updateTimerDisplay() {
  const el = document.getElementById("testTimer");
  if (!el || !currentAttempt) return;
  el.textContent = formatSeconds(Math.max(0, currentAttempt.timeLeft));
  el.classList.toggle("timer-warning", currentAttempt.timeLeft <= 30);
}

function renderCurrentQuestion() {
  const { test, index } = currentAttempt;
  const question = test.questions[index];
  const total = test.questions.length;

  document.getElementById("testProgressFill").style.width = `${(index / total) * 100}%`;

  const options = [
    ["1", question.option_1], ["2", question.option_2],
    ["3", question.option_3], ["4", question.option_4]
  ];

  const content = document.getElementById("testTakingContent");
  content.innerHTML = `
    <div class="question-counter">${index + 1} / ${total}-SAVOL</div>
    <div class="question-card">
      <div class="question-text">${question.question_text}</div>
      ${question.image_url ? `<img class="question-image" src="${question.image_url}" alt="Savol rasmi">` : ""}
    </div>
    <div class="option-list" id="optionList">
      ${options.map(([idx, text]) => `
        <button class="option-btn" data-option-index="${idx}">
          <span class="option-letter">${idx}</span><span>${text}</span>
        </button>
      `).join("")}
    </div>
    <div id="answerFeedbackWrap"></div>
    <div class="next-question-wrap hidden" id="nextQuestionWrap">
      <button class="gold-btn" id="nextQuestionBtn">${index + 1 === total ? "Yakunlash →" : "Keyingi savol →"}</button>
    </div>
  `;

  const questionImg = content.querySelector(".question-image");
  if (questionImg) questionImg.addEventListener("click", () => openLightbox(questionImg.src));

  document.querySelectorAll("#optionList .option-btn").forEach(btn => {
    btn.addEventListener("click", () => selectOption(parseInt(btn.getAttribute("data-option-index"))));
  });

  const nextBtn = document.getElementById("nextQuestionBtn");
  nextBtn.addEventListener("click", () => {
    currentAttempt.index += 1;
    if (currentAttempt.index >= total) finishTest(false);
    else renderCurrentQuestion();
  });
}

async function selectOption(selectedIndex) {
  const { test, index, id: attemptId } = currentAttempt;
  const question = test.questions[index];

  document.querySelectorAll("#optionList .option-btn").forEach(b => b.disabled = true);

  let result;
  try {
    const res = await apiFetch(`/api/attempt/${attemptId}/answer`, {
      method: "POST",
      body: JSON.stringify({ question_id: question.id, selected_index: selectedIndex })
    });
    result = await res.json();
  } catch (e) {
    console.error(e);
    document.querySelectorAll("#optionList .option-btn").forEach(b => b.disabled = false);
    return;
  }

  if (result.correct) currentAttempt.correctCount += 1;
  if (result.coin_awarded) currentAttempt.coinsEarned += 1;

  document.querySelectorAll("#optionList .option-btn").forEach(btn => {
    const idx = parseInt(btn.getAttribute("data-option-index"));
    if (idx === selectedIndex) btn.classList.add(result.correct ? "option-correct" : "option-wrong");
    else if (idx === result.correct_index) btn.classList.add("option-correct");
    else btn.classList.add("option-dim");
  });

  document.getElementById("answerFeedbackWrap").innerHTML = `
    <div class="answer-feedback ${result.correct ? "feedback-correct" : "feedback-wrong"}">
      ${result.correct ? "✓ To'g'ri javob!" + (result.coin_awarded ? " (+1 🪙)" : "") : "✗ Noto'g'ri. To'g'ri javob yashil rangda ko'rsatildi."}
    </div>
  `;
  document.getElementById("nextQuestionWrap").classList.remove("hidden");

  if (result.coin_awarded) refreshCoins();
}

async function finishTest(timedOut) {
  stopTestTimer();
  if (!currentAttempt || currentAttempt.finished) return;
  currentAttempt.finished = true;

  let finalResult = null;
  try {
    const res = await apiFetch(`/api/attempt/${currentAttempt.id}/finish`, { method: "POST" });
    finalResult = await res.json();
  } catch (e) {
    console.error(e);
  }

  const total = currentAttempt.test.questions.length;
  const score = finalResult ? finalResult.score : currentAttempt.correctCount;
  const percent = total > 0 ? Math.round((score / total) * 100) : 0;

  const content = document.getElementById("testResultContent");
  content.innerHTML = `
    <div class="test-result-content">
      <div class="result-score-circle">
        <div class="score-num">${score}/${total}</div>
        <div class="score-total">${percent}%</div>
      </div>
      <div class="result-title">${timedOut ? "⏰ Vaqt tugadi" : "🎉 Test yakunlandi"}</div>
      <div class="result-sub">${percentToComment(percent)}</div>
      ${currentAttempt.coinsEarned > 0 ? `<div class="result-coins-badge">+${currentAttempt.coinsEarned} 🪙 coin qo'lga kiritdingiz</div>` : ""}
      <div class="result-actions">
        <button class="gold-btn" id="retakeTestBtn">🔁 Qayta urinish</button>
        <button class="secondary-btn" id="backToTestsBtn">Testlar ro'yxatiga qaytish</button>
      </div>
    </div>
  `;

  document.getElementById("retakeTestBtn").addEventListener("click", () => startTest(currentTestMeta));
  document.getElementById("backToTestsBtn").addEventListener("click", () => navigateTo("tests"));

  showScreen("test-result");
  refreshCoins();
}

function percentToComment(percent) {
  if (percent === 100) return "Ajoyib! Barcha savollarga to'g'ri javob berdingiz.";
  if (percent >= 80) return "Zo'r natija! Yana bir oz mashq qilsangiz — mukammal bo'ladi.";
  if (percent >= 50) return "Yaxshi urinish. Xato javoblaringizni qayta ko'rib chiqing.";
  return "Bu mavzuni yana bir bor o'rganib, qayta urinib ko'ring.";
}

// ---------- Mening natijalarim ----------

async function loadMyResults() {
  showScreen("test-results");
  const box = document.getElementById("testResultsList");
  box.innerHTML = loadingHtml();
  try {
    const res = await apiFetch(`/api/my-test-results`);
    const data = await res.json();
    myTestResults = data.results;
    box.innerHTML = "";
    if (myTestResults.length === 0) {
      box.innerHTML = emptyHtml("Hali birorta test topshirmagansiz");
      return;
    }
    myTestResults.forEach(r => {
      const percent = r.total_questions > 0 ? Math.round((r.best_score / r.total_questions) * 100) : 0;
      const row = document.createElement("div");
      row.className = "test-result-row";
      row.innerHTML = `
        <div class="test-result-row-top">
          <div class="test-result-row-title">${r.title}</div>
          <div class="test-result-row-score">${r.best_score}/${r.total_questions}</div>
        </div>
        <div class="score-bar-track"><div class="score-bar-fill" style="width:${percent}%"></div></div>
      `;
      box.appendChild(row);
    });
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

// ---------- Modulni ishga tushirish (bir marta chaqiriladi) ----------

export function initTestsModule() {
  document.getElementById("myResultsBtn").addEventListener("click", loadMyResults);

  document.getElementById("exitTestBtn").addEventListener("click", () => {
    const ok = confirm("Testdan chiqmoqchimisiz? Joriy urinishingiz saqlanmaydi.");
    if (!ok) return;
    stopTestTimer();
    currentAttempt = null;
    navigateTo("tests");
  });
}
