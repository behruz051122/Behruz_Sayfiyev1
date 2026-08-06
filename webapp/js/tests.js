// js/tests.js
import { apiFetch, tg } from "./api.js";
import { showScreen, navigateTo } from "./navigate.js";
import {
  loadingHtml, errorHtml, emptyHtml, DIFFICULTY_LABELS, formatSeconds,
  openLightbox, skeletonCards, renderProgressChart, renderQuestionTables
} from "./components.js";
import { refreshCoins } from "./user.js";

// ---------- Oddiy testlar holati ----------
let allTests = [];
let testSearchQuery = "";
let myTestResults = [];
let currentTestMeta = null;

// ---------- Mavzuli test: fan -> guruh -> testlar (ko'p kishi ishlatishi
// uchun, bir marta ishlangan testni qayta ko'rsatmaslik maqsadida guruhlar
// KETMA-KET ochiladi) ----------
let practiceSubjectCards = [];
let practiceSubjectsLoaded = false;
let activePracticeSubject = null;
let practiceGroups = [];
let activePracticeGroup = null;

// ---------- Simulyator holati ----------
let allSimulators = [];
let simulatorsLoaded = false;
let currentSimulatorMeta = null;

// ---------- Nazorat testi holati ----------
let allControlTests = [];
let controlTestsLoaded = false;
let currentControlTestMeta = null;

// ---------- Attestatsiya holati ----------
let allAttestationTests = [];
let attestationTestsLoaded = false;
let currentAttestationMeta = null;

let activeTestsTab = "tests";

// ---------- Topshirish jarayoni (testlar VA simulyator uchun umumiy) ----------
// mode: "test" | "simulator"
let currentAttempt = null;

export function resetTestState() {
  stopTestTimer();
  currentAttempt = null;
  testSearchQuery = "";
  const searchInput = document.getElementById("testSearchInput");
  if (searchInput) searchInput.value = "";
  showTestsLanding();
}

function attemptApiBase() {
  return currentAttempt.mode === "simulator" ? "/api/simulator/attempt" : "/api/attempt";
}

// ================================================================
// TEST TURI TANLASH (landing) — Testlar ekrani avval 5 ta kategoriya
// kartasini ko'rsatadi (Mavzuli test, DTM Simulyatori, Nazorat testi va
// hozircha "tez orada" bo'lgan Milliy sertifikat/Attestatsiya), tanlangan
// kategoriya esa mavjud tab-larni (Testlar/Simulyator/Nazorat) ochadi.
// ================================================================

function showTestsLanding() {
  document.getElementById("testsCategoryLanding").classList.remove("hidden");
  document.getElementById("testsBackToLandingBtn").classList.add("hidden");
  document.getElementById("testsTabRow").classList.add("hidden");
  document.getElementById("testsTabContent").classList.add("hidden");
  document.getElementById("simulatorTabContent").classList.add("hidden");
  document.getElementById("controlTabContent").classList.add("hidden");
  document.getElementById("attestationTabContent").classList.add("hidden");
}

function openTestsCategory(tab) {
  document.getElementById("testsCategoryLanding").classList.add("hidden");
  document.getElementById("testsBackToLandingBtn").classList.remove("hidden");
  document.getElementById("testsTabRow").classList.remove("hidden");
  switchTestsTab(tab);
}

// ================================================================
// TAB ALMASHTIRISH (Testlar / Simulyator)
// ================================================================

function switchTestsTab(tab) {
  activeTestsTab = tab;
  document.getElementById("tabBtnTests").classList.toggle("active", tab === "tests");
  document.getElementById("tabBtnSimulator").classList.toggle("active", tab === "simulator");
  document.getElementById("tabBtnControl").classList.toggle("active", tab === "control");
  document.getElementById("tabBtnAttestation").classList.toggle("active", tab === "attestation");
  document.getElementById("testsTabContent").classList.toggle("hidden", tab !== "tests");
  document.getElementById("simulatorTabContent").classList.toggle("hidden", tab !== "simulator");
  document.getElementById("controlTabContent").classList.toggle("hidden", tab !== "control");
  document.getElementById("attestationTabContent").classList.toggle("hidden", tab !== "attestation");

  if (tab === "tests") {
    resetPracticeFlowToSubjects();
    loadPracticeSubjects();
  }
  if (tab === "simulator" && !simulatorsLoaded) {
    loadSimulatorList();
  }
  if (tab === "control" && !controlTestsLoaded) {
    loadControlTestList();
  }
  if (tab === "attestation" && !attestationTestsLoaded) {
    loadAttestationTestList();
  }
}

// ================================================================
// MAVZULI TEST: 1) FAN TANLASH -> 2) GURUH (ketma-ket ochiladi) -> 3) TESTLAR
// Ko'proq kishi foydalanishi va bir marta ishlangan testni qayta
// ko'rsatmaslik uchun — talaba avval fanni, keyin guruhni tanlaydi;
// guruhlar admin belgilagan tartib bo'yicha KETMA-KET ochiladi (oldingi
// guruhdagi barcha testlar tugatilmaguncha keyingisi qulflangan turadi).
// ================================================================

function resetPracticeFlowToSubjects() {
  document.getElementById("practiceSubjectLanding").classList.remove("hidden");
  document.getElementById("practiceGroupLanding").classList.add("hidden");
  document.getElementById("practiceTestListView").classList.add("hidden");
  activePracticeSubject = null;
  activePracticeGroup = null;
}

async function loadPracticeSubjects() {
  const grid = document.getElementById("practiceSubjectGrid");
  grid.innerHTML = skeletonCards(2);
  try {
    const res = await apiFetch(`/api/test-subject-cards`);
    const data = await res.json();
    practiceSubjectCards = data.cards;
    practiceSubjectsLoaded = true;
    renderPracticeSubjectCards();
  } catch (e) {
    console.error(e);
    grid.innerHTML = errorHtml();
  }
}

function renderPracticeSubjectCards() {
  const grid = document.getElementById("practiceSubjectGrid");
  grid.innerHTML = "";
  if (practiceSubjectCards.length === 0) {
    grid.innerHTML = emptyHtml("Hozircha fan qo'shilmagan");
    return;
  }
  practiceSubjectCards.forEach(card => {
    const el = document.createElement("button");
    el.className = `subject-card subject-${card.color_key || "teal"}`;
    el.innerHTML = `
      <div class="subject-card-icon">${card.icon || "📘"}</div>
      <div class="subject-card-body">
        <div class="subject-card-title">${card.title}</div>
        <div class="subject-card-sub">MAVZULI TEST</div>
        <div class="subject-card-cta">OCHISH →</div>
      </div>
    `;
    el.addEventListener("click", () => openPracticeGroups(card));
    grid.appendChild(el);
  });
}

async function openPracticeGroups(card) {
  activePracticeSubject = card;
  activePracticeGroup = null;
  document.getElementById("practiceSubjectLanding").classList.add("hidden");
  document.getElementById("practiceGroupLanding").classList.remove("hidden");
  document.getElementById("practiceTestListView").classList.add("hidden");
  document.getElementById("practiceGroupLandingTitle").textContent = `${card.icon || "📘"} ${card.title}`;
  const box = document.getElementById("practiceGroupList");
  box.innerHTML = skeletonCards(2);
  try {
    const res = await apiFetch(`/api/test-subject-cards/${card.id}/groups`);
    const data = await res.json();
    practiceGroups = data.groups;
    renderPracticeGroupList();
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

function renderPracticeGroupList() {
  const box = document.getElementById("practiceGroupList");
  box.innerHTML = "";
  if (practiceGroups.length === 0) {
    box.innerHTML = emptyHtml("Bu fan uchun hozircha guruh qo'shilmagan");
    return;
  }
  practiceGroups.forEach((g, i) => {
    const row = document.createElement("div");
    row.className = "module-item" + (g.unlocked ? "" : " module-locked");
    const metaText = g.total_count > 0
      ? `${g.completed_count}/${g.total_count} test tugallandi${g.is_done ? " · ✅ Tugallangan" : ""}`
      : "Hozircha test qo'shilmagan";
    row.innerHTML = `
      <div class="module-num">${g.unlocked ? (g.icon || (i + 1)) : "🔒"}</div>
      <div class="module-info">
        <div class="module-title">${g.title}</div>
        <div class="module-meta">${g.subtitle ? g.subtitle + " · " : ""}${metaText}</div>
      </div>
      <div class="module-arrow">${g.unlocked ? "›" : ""}</div>
    `;
    row.addEventListener("click", () => {
      if (!g.unlocked) {
        tg.showAlert ? tg.showAlert("🔒 Bu guruh hali ochilmagan — avvalgi guruhdagi barcha testlarni tugating") : alert("Bu guruh hali ochilmagan");
        return;
      }
      openPracticeGroupTests(g);
    });
    box.appendChild(row);
  });
}

async function openPracticeGroupTests(group) {
  activePracticeGroup = group;
  document.getElementById("practiceGroupLanding").classList.add("hidden");
  document.getElementById("practiceTestListView").classList.remove("hidden");
  document.getElementById("practiceTestListTitle").textContent = `${group.icon || "📂"} ${group.title}`;
  testSearchQuery = "";
  const searchInput = document.getElementById("testSearchInput");
  if (searchInput) searchInput.value = "";
  bindTestSearchInput();
  await refreshPracticeGroupTests();
}

// Testni tugatgach shu ro'yxatga qaytilganda ham chaqiriladi — natijalar
// (bajarilgan belgisi) va progress yangilanishi uchun.
async function refreshPracticeGroupTests() {
  if (!activePracticeGroup) return;
  const container = document.getElementById("testList");
  container.innerHTML = skeletonCards(3);
  try {
    const [testsRes, resultsRes] = await Promise.all([
      apiFetch(`/api/tests?group_id=${activePracticeGroup.id}`),
      apiFetch(`/api/my-test-results`)
    ]);
    allTests = (await testsRes.json()).tests;
    myTestResults = (await resultsRes.json()).results;
    renderTestList();
  } catch (e) {
    console.error(e);
    container.innerHTML = errorHtml();
  }
}

function bindTestSearchInput() {
  const input = document.getElementById("testSearchInput");
  if (!input || input.dataset.bound) return;
  input.dataset.bound = "true";
  input.addEventListener("input", () => {
    testSearchQuery = input.value.trim().toLowerCase();
    renderTestList();
  });
}

function bestResultForTest(testId) {
  return myTestResults.find(r => r.test_id === testId) || null;
}

function renderTestList() {
  const container = document.getElementById("testList");
  container.innerHTML = "";

  const filtered = allTests.filter(t => {
    if (testSearchQuery && !(`${t.title} ${t.subject}`.toLowerCase().includes(testSearchQuery))) return false;
    return true;
  });

  if (filtered.length === 0) {
    container.innerHTML = emptyHtml(testSearchQuery ? `"${testSearchQuery}" bo'yicha hech narsa topilmadi` : "Bu guruhda hozircha test yo'q");
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

const START_BTN_ID_BY_MODE = { control: "startControlBtn", attestation: "startAttestationBtn", test: "startTestBtn" };
const START_BTN_TEXT_BY_MODE = {
  control: "▶ Nazorat testini boshlash",
  attestation: "▶ Attestatsiyani boshlash",
  test: "▶ Testni boshlash",
};

async function startTest(test, mode = "test") {
  const btnId = START_BTN_ID_BY_MODE[mode] || "startTestBtn";
  const btnText = START_BTN_TEXT_BY_MODE[mode] || "▶ Testni boshlash";
  const btn = document.getElementById(btnId);
  if (btn) { btn.disabled = true; btn.textContent = "Tayyorlanmoqda..."; }
  try {
    const [startRes, fullTestRes] = await Promise.all([
      apiFetch(`/api/test/${test.id}/start`, { method: "POST" }),
      apiFetch(`/api/test/${test.id}`)
    ]);
    if (!startRes.ok) {
      const errData = await startRes.json().catch(() => ({}));
      tg.showAlert ? tg.showAlert(errData.detail || "Boshlab bo'lmadi") : alert(errData.detail || "Xatolik");
      if (btn) { btn.disabled = false; btn.textContent = btnText; }
      return;
    }
    const startData = await startRes.json();
    const fullTest = await fullTestRes.json();

    if (!fullTest.questions || fullTest.questions.length === 0) {
      tg.showAlert ? tg.showAlert("Bu testda hozircha savollar yo'q") : alert("Bu testda hozircha savollar yo'q");
      if (btn) { btn.disabled = false; btn.textContent = btnText; }
      return;
    }

    currentAttempt = {
      mode: mode,
      id: startData.attempt_id,
      test: fullTest,
      index: 0,
      answers: {}, // question_id -> tanlangan variant raqami (erkin o'zgartiriladi)
      flags: new Set(), // question_id lar — Attestatsiyada "Belgilash" bosilgan savollar
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
    if (btn) { btn.disabled = false; btn.textContent = btnText; }
  }
}

// ================================================================
// DTM SIMULYATORI RO'YXATI VA TAFSILOTI
// ================================================================

async function loadSimulatorList() {
  const container = document.getElementById("simulatorList");
  container.innerHTML = skeletonCards(2);
  try {
    const res = await apiFetch(`/api/simulators`);
    const data = await res.json();
    allSimulators = data.simulators;
    simulatorsLoaded = true;
    renderSimulatorList();
  } catch (e) {
    console.error(e);
    container.innerHTML = errorHtml();
  }
}

function renderSimulatorList() {
  const container = document.getElementById("simulatorList");
  container.innerHTML = "";

  if (allSimulators.length === 0) {
    container.innerHTML = emptyHtml("Hozircha DTM simulyatori qo'shilmagan");
    return;
  }

  allSimulators.forEach(sim => {
    const card = document.createElement("div");
    card.className = "test-card";
    const subjectsChips = sim.subjects.map(s => `<span class="simulator-subject-chip">${s.subject}: ${s.question_count} ta</span>`).join("");
    card.innerHTML = `
      <div class="test-card-top">
        <div class="test-card-title">${sim.title}</div>
        <span class="difficulty-badge difficulty-qiyin">DTM</span>
      </div>
      <div class="test-card-meta">
        <span>❓ ${sim.total_questions} savol</span>
        <span>⏱ ${formatSeconds(sim.time_limit_seconds)}</span>
      </div>
      <div class="simulator-subjects-row">${subjectsChips}</div>
    `;
    card.addEventListener("click", () => openSimulatorDetail(sim));
    container.appendChild(card);
  });
}

function openSimulatorDetail(sim) {
  currentSimulatorMeta = sim;
  const content = document.getElementById("simulatorDetailContent");
  const subjectsList = sim.subjects.map(s => `<div class="analytics-top-row"><span class="name">${s.subject}</span><span class="count">${s.question_count} ta savol</span></div>`).join("");

  content.innerHTML = `
    <div class="test-detail-hero">
      <span class="difficulty-badge difficulty-qiyin">DTM SIMULYATORI</span>
      <h1>${sim.title}</h1>
      ${sim.description ? `<p style="color:var(--text-dim);font-size:12px;margin-top:6px;">${sim.description}</p>` : ""}
      <div class="test-detail-stats">
        <div class="test-detail-stat"><div class="num">${sim.total_questions}</div><div class="lbl">savol</div></div>
        <div class="test-detail-stat"><div class="num">${formatSeconds(sim.time_limit_seconds)}</div><div class="lbl">vaqt</div></div>
      </div>
    </div>
    <div class="admin-section-head" style="margin:0 16px 8px;"><h3 style="font-size:12px;color:var(--text-dim);">Fanlar tarkibi</h3></div>
    <div style="margin:0 16px 16px;">${subjectsList}</div>
    <div class="test-detail-actions">
      <button class="gold-btn" id="startSimulatorBtn">▶ Simulyatorni boshlash</button>
    </div>
    <p style="text-align:center;color:var(--text-dim);font-size:11px;margin-top:14px;">
      Savollar har safar TASODIFIY tanlanadi — bir xil urinishni ikki marta topshirsangiz ham, savollar farqli bo'lishi mumkin.
      Vaqt tugasa, simulyator avtomatik yakunlanadi.
    </p>
  `;
  document.getElementById("startSimulatorBtn").addEventListener("click", () => startSimulator(sim));

  showScreen("simulator-detail");
}

async function startSimulator(sim) {
  const btn = document.getElementById("startSimulatorBtn");
  if (btn) { btn.disabled = true; btn.textContent = "Tayyorlanmoqda..."; }
  try {
    const startRes = await apiFetch(`/api/simulator/${sim.id}/start`, { method: "POST" });
    if (!startRes.ok) {
      const errData = await startRes.json().catch(() => ({}));
      tg.showAlert ? tg.showAlert(errData.detail || "Simulyatorni boshlab bo'lmadi") : alert(errData.detail || "Xatolik");
      if (btn) { btn.disabled = false; btn.textContent = "▶ Simulyatorni boshlash"; }
      return;
    }
    const startData = await startRes.json();

    const questionsRes = await apiFetch(`/api/simulator/attempt/${startData.attempt_id}/questions`);
    const questionsData = await questionsRes.json();

    currentAttempt = {
      mode: "simulator",
      id: startData.attempt_id,
      test: {
        title: startData.title,
        time_limit_seconds: startData.time_limit_seconds,
        questions: questionsData.questions,
      },
      index: 0,
      answers: {}, // question_id -> tanlangan variant raqami (erkin o'zgartiriladi)
      coinsEarned: 0,
      timeLeft: startData.time_limit_seconds,
      timerHandle: null,
      finished: false,
    };

    showScreen("test-taking");
    renderCurrentQuestion();
    startTestTimer();
  } catch (e) {
    console.error(e);
    if (btn) { btn.disabled = false; btn.textContent = "▶ Simulyatorni boshlash"; }
  }
}

// ================================================================
// NAZORAT TESTLARI RO'YXATI VA TAFSILOTI
// ================================================================

async function loadControlTestList() {
  const container = document.getElementById("controlTestList");
  container.innerHTML = skeletonCards(2);
  try {
    const res = await apiFetch(`/api/control-tests`);
    const data = await res.json();
    allControlTests = data.tests;
    controlTestsLoaded = true;
    renderControlTestList();
  } catch (e) {
    console.error(e);
    container.innerHTML = errorHtml();
  }
}

function renderControlTestList() {
  const container = document.getElementById("controlTestList");
  container.innerHTML = "";

  if (allControlTests.length === 0) {
    container.innerHTML = emptyHtml("Hozircha nazorat testi qo'shilmagan");
    return;
  }

  allControlTests.forEach(t => {
    const card = document.createElement("div");
    card.className = "test-card" + (t.unlocked ? "" : " locked-card");
    card.innerHTML = `
      <div class="test-card-top">
        <div class="test-card-title">${t.title}</div>
        <span class="difficulty-badge difficulty-${t.difficulty}">${DIFFICULTY_LABELS[t.difficulty] || t.difficulty}</span>
      </div>
      <div class="test-card-meta">
        <span class="course-tag">${t.subject}</span>
        <span>❓ ${t.question_count} savol</span>
        <span>⏱ ${formatSeconds(t.time_limit_seconds)}</span>
      </div>
      ${t.unlocked
        ? `<div class="unlock-badge">✅ Ochiq${t.access_reason === "assigned" ? " · sizga tayinlangan" : t.course_title ? " · " + t.course_title : ""}</div>`
        : `<div class="control-locked-note">🔒 Ustozingiz tomonidan tayinlanishi kerak${t.course_title ? ` (yoki "${t.course_title}" kursiga yozilish orqali)` : ""}</div>`}
    `;
    card.addEventListener("click", () => openControlTestDetail(t));
    container.appendChild(card);
  });
}

function openControlTestDetail(test) {
  currentControlTestMeta = test;
  const content = document.getElementById("controlDetailContent");

  if (!test.unlocked) {
    content.innerHTML = `
      <div class="test-detail-hero">
        <span class="difficulty-badge difficulty-qiyin">NAZORAT TESTI</span>
        <h1>${test.title}</h1>
      </div>
      <div class="locked-box">
        <div class="lock-emoji">🔒</div>
        <h3>Bu test hali yopiq</h3>
        <p>Bu nazorat testi faqat ustozingiz tomonidan tanlangan o'quvchilar uchun ochiq${test.course_title ? ` (yoki "${test.course_title}" kursiga yozilish orqali)` : ""}.</p>
        <button class="gold-btn" id="controlLockedContactBtn">Admin bilan bog'lanish</button>
      </div>
    `;
    const contactBtn = document.getElementById("controlLockedContactBtn");
    if (contactBtn) contactBtn.addEventListener("click", () => navigateTo("profile"));
    showScreen("control-detail");
    return;
  }

  content.innerHTML = `
    <div class="test-detail-hero">
      <span class="difficulty-badge difficulty-${test.difficulty}">${DIFFICULTY_LABELS[test.difficulty] || test.difficulty}</span>
      <h1>${test.title}</h1>
      <div class="test-detail-stats">
        <div class="test-detail-stat"><div class="num">${test.question_count}</div><div class="lbl">savol</div></div>
        <div class="test-detail-stat"><div class="num">${formatSeconds(test.time_limit_seconds)}</div><div class="lbl">vaqt</div></div>
      </div>
    </div>
    <div class="test-detail-actions">
      <button class="gold-btn" id="startControlBtn">▶ Nazorat testini boshlash</button>
    </div>
    <p style="text-align:center;color:var(--text-dim);font-size:11px;margin-top:14px;">
      Bu — rasmiy nazorat testi. Javob berayotganda to'g'ri/noto'g'ri darhol ko'rsatilmaydi —
      natijangizni faqat test yakunida to'liq ko'rasiz. Natijangiz oylik reytingga ta'sir qiladi.
    </p>
  `;
  document.getElementById("startControlBtn").addEventListener("click", () => startTest(test, "control"));

  showScreen("control-detail");
}

// ================================================================
// ATTESTATSIYA RO'YXATI VA TAFSILOTI
// (@biologiyamockbot tahlili asosida — erkin kirish, tayinlash shart emas)
// ================================================================

async function loadAttestationTestList() {
  const container = document.getElementById("attestationTestList");
  container.innerHTML = skeletonCards(2);
  try {
    const res = await apiFetch(`/api/attestation-tests`);
    const data = await res.json();
    allAttestationTests = data.tests;
    attestationTestsLoaded = true;
    renderAttestationTestList();
  } catch (e) {
    console.error(e);
    container.innerHTML = errorHtml();
  }
}

function renderAttestationTestList() {
  const container = document.getElementById("attestationTestList");
  container.innerHTML = "";

  if (allAttestationTests.length === 0) {
    container.innerHTML = emptyHtml("Hozircha attestatsiya testi qo'shilmagan");
    return;
  }

  allAttestationTests.forEach(t => {
    const card = document.createElement("div");
    card.className = "test-card";
    card.innerHTML = `
      <div class="test-card-top">
        <div class="test-card-title">${t.title}</div>
        <span class="difficulty-badge difficulty-${t.difficulty}">${DIFFICULTY_LABELS[t.difficulty] || t.difficulty}</span>
      </div>
      <div class="test-card-meta">
        <span class="course-tag">${t.subject}</span>
        <span>❓ ${t.question_count} savol</span>
        <span>⏱ ${formatSeconds(t.time_limit_seconds)}</span>
      </div>
      <div class="unlock-badge">🔓 Erkin kirish</div>
    `;
    card.addEventListener("click", () => openAttestationDetail(t));
    container.appendChild(card);
  });
}

function openAttestationDetail(test) {
  currentAttestationMeta = test;
  const content = document.getElementById("attestationDetailContent");

  content.innerHTML = `
    <div class="test-detail-hero">
      <span class="difficulty-badge difficulty-${test.difficulty}">${DIFFICULTY_LABELS[test.difficulty] || test.difficulty}</span>
      <h1>${test.title}</h1>
      <div class="test-detail-stats">
        <div class="test-detail-stat"><div class="num">${test.question_count}</div><div class="lbl">savol</div></div>
        <div class="test-detail-stat"><div class="num">${formatSeconds(test.time_limit_seconds)}</div><div class="lbl">vaqt</div></div>
      </div>
    </div>
    <div class="test-detail-actions">
      <button class="gold-btn" id="startAttestationBtn">▶ Attestatsiyani boshlash</button>
    </div>
    <p style="text-align:center;color:var(--text-dim);font-size:11px;margin-top:14px;">
      Bu — rasmiy attestatsiya sinovi. Har bir savolni "🚩 Belgilash" (keyinroq qaytish uchun) yoki
      "⚠️ E'tiroz bildirish" mumkin. Javob berayotganda to'g'ri/noto'g'ri darhol ko'rsatilmaydi —
      natijada ham to'g'ri javob ko'rsatilmaydi, faqat qaysi savollarga to'g'ri/noto'g'ri javob berganingiz.
      Natijangiz shu variant bo'yicha reytingga ta'sir qiladi.
    </p>
  `;
  document.getElementById("startAttestationBtn").addEventListener("click", () => startTest(test, "attestation"));

  showScreen("attestation-detail");
}

// ================================================================
// TOPSHIRISH JARAYONI (testlar VA simulyator uchun UMUMIY)
// ================================================================

function startTestTimer() {
  stopTestTimer();
  updateTimerDisplay();
  currentAttempt.timerHandle = setInterval(() => {
    currentAttempt.timeLeft -= 1;
    updateTimerDisplay();
    if (currentAttempt.timeLeft <= 0) {
      stopTestTimer();
      finishAttempt(true);
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

// Savollar orasida ERKIN harakatlanish (istalgan savolga to'g'ridan-to'g'ri
// o'tish, oldinga/orqaga qaytish) va javobni ISTALGANCHA o'zgartirish imkoni
// — variantni bosish faqat BELGILAYDI, hech qanday darhol to'g'ri/noto'g'ri
// ko'rsatilmaydi (buni oldin faqat nazorat testi qilardi, endi hammasi shu
// tarzda ishlaydi). Natija — to'g'ri/noto'g'ri/javobsiz — FAQAT testni
// yakunlagandan keyin, umumiy natija ekranida ko'rsatiladi.

function renderCurrentQuestion() {
  const { test, index, answers } = currentAttempt;
  const question = test.questions[index];
  const total = test.questions.length;
  const answeredCount = Object.keys(answers).length;

  document.getElementById("testProgressFill").style.width = `${(answeredCount / total) * 100}%`;

  const options = [
    ["1", question.option_1], ["2", question.option_2],
    ["3", question.option_3], ["4", question.option_4]
  ];

  const subjectSuffix = question.subject ? ` · ${question.subject}` : "";
  const selectedIndex = answers[question.id];

  const isAttestation = currentAttempt.mode === "attestation";
  const isFlagged = isAttestation && currentAttempt.flags.has(question.id);

  const navButtons = test.questions.map((q, i) => {
    const cls = ["qnav-btn"];
    if (i === index) cls.push("qnav-current");
    if (answers[q.id] !== undefined) cls.push("qnav-answered");
    if (isAttestation && currentAttempt.flags.has(q.id)) cls.push("qnav-flagged");
    return `<button type="button" class="${cls.join(" ")}" data-index="${i}">${i + 1}</button>`;
  }).join("");

  const attestationActions = isAttestation ? `
    <div class="attestation-actions">
      <button type="button" class="secondary-btn small ${isFlagged ? "flag-active" : ""}" id="flagQuestionBtn">
        ${isFlagged ? "🚩 Belgilangan" : "🏳 Belgilash"}
      </button>
      <button type="button" class="secondary-btn small" id="objectionBtn">⚠️ E'tiroz bildirish</button>
    </div>
  ` : "";

  const content = document.getElementById("testTakingContent");
  content.innerHTML = `
    <div class="question-counter">${index + 1} / ${total}-SAVOL${subjectSuffix} · ${answeredCount}/${total} javob berilgan</div>
    <div class="question-nav-grid">${navButtons}</div>
    <div class="question-card">
      <div class="question-text">${question.question_text}</div>
      ${question.image_url ? `<img class="question-image" src="${question.image_url}" alt="Savol rasmi">` : ""}
      ${renderQuestionTables(question.table_data)}
    </div>
    ${attestationActions}
    <div class="option-list" id="optionList">
      ${options.map(([idx, text]) => `
        <button class="option-btn ${parseInt(idx) === selectedIndex ? "option-selected-neutral" : ""}" data-option-index="${idx}">
          <span class="option-letter">${idx}</span><span>${text}</span>
        </button>
      `).join("")}
    </div>
    <div class="test-nav-actions">
      <button class="secondary-btn" id="prevQuestionBtn" ${index === 0 ? "disabled" : ""}>← Oldingi</button>
      <button class="secondary-btn" id="nextQuestionBtn" ${index === total - 1 ? "disabled" : ""}>Keyingi →</button>
    </div>
    <div class="finish-test-wrap">
      <button class="gold-btn" id="finishTestBtn">✅ Testni yakunlash</button>
    </div>
  `;

  const questionImg = content.querySelector(".question-image");
  if (questionImg) questionImg.addEventListener("click", () => openLightbox(questionImg.src));

  document.querySelectorAll("#optionList .option-btn").forEach(btn => {
    btn.addEventListener("click", () => selectOption(parseInt(btn.getAttribute("data-option-index"))));
  });

  content.querySelectorAll(".qnav-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      currentAttempt.index = parseInt(btn.getAttribute("data-index"));
      renderCurrentQuestion();
    });
  });

  const prevBtn = document.getElementById("prevQuestionBtn");
  prevBtn.addEventListener("click", () => {
    if (currentAttempt.index > 0) {
      currentAttempt.index -= 1;
      renderCurrentQuestion();
    }
  });

  const nextBtn = document.getElementById("nextQuestionBtn");
  nextBtn.addEventListener("click", () => {
    if (currentAttempt.index < total - 1) {
      currentAttempt.index += 1;
      renderCurrentQuestion();
    }
  });

  document.getElementById("finishTestBtn").addEventListener("click", () => {
    const remaining = total - Object.keys(currentAttempt.answers).length;
    if (remaining > 0) {
      const ok = confirm(`${remaining} ta savolga hali javob berilmagan. Baribir yakunlaysizmi?`);
      if (!ok) return;
    }
    finishAttempt(false);
  });

  if (isAttestation) {
    document.getElementById("flagQuestionBtn").addEventListener("click", () => toggleQuestionFlag(question.id));
    document.getElementById("objectionBtn").addEventListener("click", () => submitObjection(question.id));
  }
}

// "Belgilash" — savolni keyinroq qaytish uchun belgilash/bekor qilish
// (@biologiyamockbot'dagi kabi). Javob berilgan-berilmaganidan mustaqil.
async function toggleQuestionFlag(questionId) {
  const { id: attemptId, flags } = currentAttempt;
  const flagged = !flags.has(questionId);
  if (flagged) flags.add(questionId); else flags.delete(questionId);
  renderCurrentQuestion();
  try {
    await apiFetch(`/api/attempt/${attemptId}/flag`, {
      method: "POST",
      body: JSON.stringify({ question_id: questionId, flagged })
    });
  } catch (e) {
    console.error(e);
  }
}

// "E'tiroz bildirish" — savolga shikoyat/izoh yozish, admin panelda ko'riladi.
async function submitObjection(questionId) {
  const comment = (tg.showPopup || window.prompt) ? window.prompt("Bu savolga e'tirozingizni yozing:") : null;
  if (comment === null) return; // bekor qilindi
  const trimmed = comment.trim();
  if (!trimmed) {
    tg.showAlert ? tg.showAlert("E'tiroz matni bo'sh bo'lishi mumkin emas") : alert("E'tiroz matni bo'sh bo'lishi mumkin emas");
    return;
  }
  try {
    await apiFetch(`/api/attempt/${currentAttempt.id}/objection`, {
      method: "POST",
      body: JSON.stringify({ question_id: questionId, comment: trimmed })
    });
    tg.showAlert ? tg.showAlert("✅ E'tirozingiz yuborildi") : alert("E'tirozingiz yuborildi");
  } catch (e) {
    console.error(e);
  }
}

async function selectOption(selectedIndex) {
  const { test, index, id: attemptId } = currentAttempt;
  const question = test.questions[index];

  // Variantni bosish darhol YAKUNIY javob emas — shunchaki belgilaydi va
  // qayta chizadi (rang o'zgaradi), o'quvchi xohlagancha boshqa variantga
  // o'tishi mumkin. Backend'ga ham har safar jimgina (fon rejimida) yuboriladi.
  currentAttempt.answers[question.id] = selectedIndex;
  renderCurrentQuestion();

  try {
    const res = await apiFetch(`${attemptApiBase()}/${attemptId}/answer`, {
      method: "POST",
      body: JSON.stringify({ question_id: question.id, selected_index: selectedIndex })
    });
    const result = await res.json();
    if (result.coin_awarded) {
      currentAttempt.coinsEarned += 1;
      refreshCoins();
    }
  } catch (e) {
    console.error(e);
  }
}

async function finishAttempt(timedOut) {
  stopTestTimer();
  if (!currentAttempt || currentAttempt.finished) return;
  currentAttempt.finished = true;
  const mode = currentAttempt.mode;

  let finalResult = null;
  try {
    const res = await apiFetch(`${attemptApiBase()}/${currentAttempt.id}/finish`, { method: "POST" });
    finalResult = await res.json();
  } catch (e) {
    console.error(e);
  }

  const total = currentAttempt.test.questions.length;
  const score = finalResult ? finalResult.score : Object.keys(currentAttempt.answers).length;
  const percent = total > 0 ? Math.round((score / total) * 100) : 0;
  const countsForRanking = finalResult ? finalResult.counts_for_ranking : null;

  await renderAttemptResult(currentAttempt.id, mode, score, total, percent, timedOut, countsForRanking);
  showScreen("test-result");
  refreshCoins();
}

const RESULT_TITLE_BY_MODE = {
  test: "🎉 Test yakunlandi",
  simulator: "🎯 Simulyator yakunlandi",
  control: "🎓 Nazorat testi yakunlandi",
  attestation: "📋 Attestatsiya yakunlandi",
};

const BACK_LABEL_BY_MODE = {
  simulator: "Simulyatorlar ro'yxatiga qaytish",
  control: "Nazorat testlariga qaytish",
  attestation: "Attestatsiya ro'yxatiga qaytish",
  test: "Testlar ro'yxatiga qaytish",
};

async function renderAttemptResult(attemptId, mode, score, total, percent, timedOut, countsForRanking) {
  const content = document.getElementById("testResultContent");
  // Nazorat testini talaba mashq uchun xohlagancha qayta ishlashi mumkin —
  // faqat ENG BIRINCHI yakunlangan urinishi oylik reytingga hisoblanadi.
  const rankingNote = mode === "control"
    ? (countsForRanking
        ? `<div class="ranking-note ranking-note-yes">✅ Bu urinish oylik reytingga hisoblandi</div>`
        : `<div class="ranking-note ranking-note-no">ℹ️ Bu — mashq urinishi, reytingga ta'sir qilmaydi (birinchi urinishingiz allaqachon hisoblangan)</div>`)
    : "";
  const showRetake = true;

  content.innerHTML = `
    <div class="test-result-content">
      <div class="result-score-circle">
        <div class="score-num">${score}/${total}</div>
        <div class="score-total">${percent}%</div>
      </div>
      <div class="result-title">${timedOut ? "⏰ Vaqt tugadi" : (RESULT_TITLE_BY_MODE[mode] || "Yakunlandi")}</div>
      <div class="result-sub">${percentToComment(percent)}</div>
      ${currentAttempt.coinsEarned > 0 ? `<div class="result-coins-badge">+${currentAttempt.coinsEarned} 🪙 coin qo'lga kiritdingiz</div>` : ""}
      ${rankingNote}
      ${mode === "attestation" ? `<div id="attestationRankBox"></div>` : ""}
    </div>
    <div class="control-result-stats-row">
      <div class="control-stat correct"><div class="num">${score}</div><div class="lbl">To'g'ri</div></div>
      <div class="control-stat wrong"><div class="num">${total - score}</div><div class="lbl">Noto'g'ri/javobsiz</div></div>
      <div class="control-stat"><div class="num">${total}</div><div class="lbl">Jami savol</div></div>
    </div>
    <div class="control-grid-title" style="text-align:center;">Savollar natijasi</div>
    <p style="text-align:center;color:var(--text-dim);font-size:11px;margin-top:-8px;">To'g'ri javoblar ko'rsatilmaydi — faqat qaysi savolga to'g'ri/noto'g'ri javob berganingiz.</p>
    <div class="control-answers-grid" id="controlAnswersGrid"></div>
    <div class="result-actions" style="margin:16px;">
      ${showRetake ? `<button class="secondary-btn" id="retakeTestBtn">🔁 Qayta urinish</button>` : ""}
      <button class="secondary-btn" id="backToTestsBtn">${BACK_LABEL_BY_MODE[mode] || "Testlar ro'yxatiga qaytish"}</button>
    </div>
  `;

  try {
    const gridUrl = mode === "simulator" ? `/api/simulator/attempt/${attemptId}/grid` : `/api/attempt/${attemptId}/grid`;
    const res = await apiFetch(gridUrl);
    const data = await res.json();
    const gridBox = document.getElementById("controlAnswersGrid");
    gridBox.innerHTML = data.grid.map(g => {
      const cls = !g.answered ? "unanswered" : (g.is_correct ? "correct" : "wrong");
      return `<div class="control-grid-cell ${cls}">${g.question_number}</div>`;
    }).join("");
  } catch (e) {
    console.error(e);
  }

  if (mode === "attestation") {
    try {
      const rankRes = await apiFetch(`/api/attempt/${attemptId}/rank`);
      const rankData = await rankRes.json();
      const rankBox = document.getElementById("attestationRankBox");
      if (rankBox) {
        rankBox.innerHTML = rankData.rank
          ? `<div class="ranking-note ranking-note-yes">🏆 ${rankData.rank.rank}-o'rin / ${rankData.rank.total} talaba ichida</div>`
          : `<div class="ranking-note ranking-note-no">ℹ️ Bu — mashq urinishi, variant reytingiga ta'sir qilmaydi</div>`;
      }
    } catch (e) {
      console.error(e);
    }
  }

  if (showRetake) {
    document.getElementById("retakeTestBtn").addEventListener("click", () => {
      if (mode === "simulator") startSimulator(currentSimulatorMeta);
      else if (mode === "control") startTest(currentControlTestMeta, "control");
      else if (mode === "attestation") startTest(currentAttestationMeta, "attestation");
      else startTest(currentTestMeta);
    });
  }
  document.getElementById("backToTestsBtn").addEventListener("click", () => {
    // Mavzuli test (mode === "test") bo'lsa va talaba biror guruhdan kelgan
    // bo'lsa — to'liq "tests" ekraniga qaytib, fan tanlashdan boshlash
    // o'rniga, TO'G'RIDAN-TO'G'RI o'sha guruhning testlar ro'yxatiga
    // qaytamiz (yangi tugallangan test/ochilgan keyingi guruh ko'rinishi
    // uchun ro'yxat yangilanadi).
    if (mode === "test" && activePracticeGroup) {
      activeTestsTab = "tests";
      showScreen("tests");
      refreshPracticeGroupTests();
      return;
    }
    activeTestsTab = mode === "simulator" ? "simulator" : mode === "control" ? "control" : mode === "attestation" ? "attestation" : "tests";
    navigateTo("tests");
  });
}

function percentToComment(percent) {
  if (percent === 100) return "Ajoyib! Barcha savollarga to'g'ri javob berdingiz.";
  if (percent >= 80) return "Zo'r natija! Yana bir oz mashq qilsangiz — mukammal bo'ladi.";
  if (percent >= 50) return "Yaxshi urinish. Xato javoblaringizni qayta ko'rib chiqing.";
  return "Bu mavzuni yana bir bor o'rganib, qayta urinib ko'ring.";
}

// ================================================================
// MENING NATIJALARIM (testlar + simulyator + progress grafigi)
// ================================================================

async function loadMyResults() {
  showScreen("test-results");
  const chartBox = document.getElementById("progressChartWrap");
  const testBox = document.getElementById("testResultsList");
  const simBox = document.getElementById("simulatorResultsList");
  chartBox.innerHTML = loadingHtml();
  testBox.innerHTML = loadingHtml();
  simBox.innerHTML = loadingHtml();

  try {
    const [historyRes, testResultsRes, simResultsRes] = await Promise.all([
      apiFetch(`/api/my-progress-history`),
      apiFetch(`/api/my-test-results`),
      apiFetch(`/api/my-simulator-results`)
    ]);
    const history = (await historyRes.json()).history;
    const testResults = (await testResultsRes.json()).results;
    const simResults = (await simResultsRes.json()).results;

    chartBox.innerHTML = renderProgressChart(history);

    testBox.innerHTML = "";
    if (testResults.length === 0) {
      testBox.innerHTML = emptyHtml("Hali birorta test topshirmagansiz");
    } else {
      testResults.forEach(r => testBox.appendChild(buildResultRow(r.title, r.best_score, r.total_questions)));
    }

    simBox.innerHTML = "";
    if (simResults.length === 0) {
      simBox.innerHTML = emptyHtml("Hali birorta simulyator topshirmagansiz");
    } else {
      simResults.forEach(r => simBox.appendChild(buildResultRow(r.title, r.best_score, r.total_questions)));
    }
  } catch (e) {
    console.error(e);
    chartBox.innerHTML = errorHtml();
  }
}

function buildResultRow(title, bestScore, totalQuestions) {
  const percent = totalQuestions > 0 ? Math.round((bestScore / totalQuestions) * 100) : 0;
  const row = document.createElement("div");
  row.className = "test-result-row";
  row.innerHTML = `
    <div class="test-result-row-top">
      <div class="test-result-row-title">${title}</div>
      <div class="test-result-row-score">${bestScore}/${totalQuestions}</div>
    </div>
    <div class="score-bar-track"><div class="score-bar-fill" style="width:${percent}%"></div></div>
  `;
  return row;
}

// ================================================================
// Modulni ishga tushirish (bir marta chaqiriladi)
// ================================================================

export function initTestsModule() {
  document.getElementById("myResultsBtn").addEventListener("click", loadMyResults);

  document.querySelectorAll("#testsCategoryLanding [data-testtab]").forEach(btn => {
    btn.addEventListener("click", () => openTestsCategory(btn.getAttribute("data-testtab")));
  });
  document.getElementById("testsBackToLandingBtn").addEventListener("click", showTestsLanding);

  document.getElementById("tabBtnTests").addEventListener("click", () => switchTestsTab("tests"));
  document.getElementById("tabBtnSimulator").addEventListener("click", () => switchTestsTab("simulator"));
  document.getElementById("tabBtnControl").addEventListener("click", () => switchTestsTab("control"));
  document.getElementById("tabBtnAttestation").addEventListener("click", () => switchTestsTab("attestation"));

  document.getElementById("practiceBackToSubjectsBtn").addEventListener("click", () => resetPracticeFlowToSubjects());
  document.getElementById("practiceBackToGroupsBtn").addEventListener("click", () => {
    if (activePracticeSubject) openPracticeGroups(activePracticeSubject);
    else resetPracticeFlowToSubjects();
  });

  document.getElementById("exitTestBtn").addEventListener("click", () => {
    const ok = confirm("Testdan chiqmoqchimisiz? Joriy urinishingiz saqlanmaydi.");
    if (!ok) return;
    stopTestTimer();
    currentAttempt = null;
    navigateTo("tests");
  });
}
