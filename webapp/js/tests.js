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

// ---------- Mavzuli test: fan -> bosqich -> turkum -> testlar (ko'p kishi
// ishlatishi uchun, bir marta ishlangan testni qayta ko'rsatmaslik
// maqsadida BOSQICHLAR ("1-bo'lim", "2-bo'lim"...) KETMA-KET ochiladi; har
// bir bosqich ICHIDA esa bir nechta turkum — masalan "Mavzulashtirilgan
// testlar", "Nazorat testlari" — bo'lishi mumkin, ular bir-biriga nisbatan
// qulflanmaydi) ----------
let practiceSubjectCards = [];
let practiceSubjectsLoaded = false;
let activePracticeSubject = null;
let practiceStages = [];
let activePracticeStage = null;
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

// ---------- Milliy sertifikat holati ----------
let allCertificateTests = [];
let certificateTestsLoaded = false;
let currentCertificateMeta = null;

const CERT_TYPE_LABELS = {
  Y1: "🔘 YOPIQ TEST — bitta to'g'ri javobni tanlang",
  Y2: "🔗 MOSLASHTIRISH — har biriga mos javobni tanlang",
  O1: "✍️ QISQA JAVOB — matn kiriting",
  O2: "📝 KENGAYTIRILGAN YOZMA ISH — qo'lda baholanadi",
};

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
  document.getElementById("certificateTabContent").classList.add("hidden");
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
  document.getElementById("tabBtnCertificate").classList.toggle("active", tab === "certificate");
  document.getElementById("testsTabContent").classList.toggle("hidden", tab !== "tests");
  document.getElementById("simulatorTabContent").classList.toggle("hidden", tab !== "simulator");
  document.getElementById("controlTabContent").classList.toggle("hidden", tab !== "control");
  document.getElementById("attestationTabContent").classList.toggle("hidden", tab !== "attestation");
  document.getElementById("certificateTabContent").classList.toggle("hidden", tab !== "certificate");

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
  if (tab === "certificate" && !certificateTestsLoaded) {
    loadCertificateTestList();
  }
}

// ================================================================
// MAVZULI TEST: 1) FAN TANLASH -> 2) BOSQICH (ketma-ket ochiladi) ->
// 3) TURKUM (bosqich ichida, qulflanmaydi) -> 4) TESTLAR
// Ko'proq kishi foydalanishi va bir marta ishlangan testni qayta
// ko'rsatmaslik uchun — talaba avval fanni, keyin bosqichni tanlaydi;
// bosqichlar admin belgilagan tartib bo'yicha KETMA-KET ochiladi (oldingi
// bosqichdagi barcha turkum/testlar tugatilmaguncha keyingisi qulflangan
// turadi). Bosqich ICHIDAGI turkumlar esa bir-biriga nisbatan erkin —
// bosqich ochiq bo'lsa, barcha turkumlar baravar ochiq.
// ================================================================

function resetPracticeFlowToSubjects() {
  document.getElementById("practiceSubjectLanding").classList.remove("hidden");
  document.getElementById("practiceStageLanding").classList.add("hidden");
  document.getElementById("practiceGroupLanding").classList.add("hidden");
  document.getElementById("practiceTestListView").classList.add("hidden");
  activePracticeSubject = null;
  activePracticeStage = null;
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
    el.addEventListener("click", () => openPracticeStages(card));
    grid.appendChild(el);
  });
}

// ---------- 2-bosqich: fan ichidagi BOSQICHLAR ("1-bo'lim", "2-bo'lim"...) ----------

async function openPracticeStages(card) {
  activePracticeSubject = card;
  activePracticeStage = null;
  activePracticeGroup = null;
  document.getElementById("practiceSubjectLanding").classList.add("hidden");
  document.getElementById("practiceStageLanding").classList.remove("hidden");
  document.getElementById("practiceGroupLanding").classList.add("hidden");
  document.getElementById("practiceTestListView").classList.add("hidden");
  document.getElementById("practiceStageLandingTitle").textContent = `${card.icon || "📘"} ${card.title}`;
  const box = document.getElementById("practiceStageList");
  box.innerHTML = skeletonCards(2);
  try {
    const res = await apiFetch(`/api/test-subject-cards/${card.id}/stages`);
    const data = await res.json();
    practiceStages = data.stages;
    renderPracticeStageList();
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

function renderPracticeStageList() {
  const box = document.getElementById("practiceStageList");
  box.innerHTML = "";
  if (practiceStages.length === 0) {
    box.innerHTML = emptyHtml("Bu fan uchun hozircha bosqich qo'shilmagan");
    return;
  }
  practiceStages.forEach((s, i) => {
    const row = document.createElement("div");
    row.className = "module-item" + (s.unlocked ? "" : " module-locked");
    const metaText = s.total_count > 0
      ? `${s.completed_count}/${s.total_count} test tugallandi${s.is_done ? " · ✅ Tugallangan" : ""}`
      : "Hozircha test qo'shilmagan";
    row.innerHTML = `
      <div class="module-num">${s.unlocked ? (s.icon || (i + 1)) : "🔒"}</div>
      <div class="module-info">
        <div class="module-title">${s.title}</div>
        <div class="module-meta">${s.subtitle ? s.subtitle + " · " : ""}${metaText}</div>
      </div>
      <div class="module-arrow">${s.unlocked ? "›" : ""}</div>
    `;
    row.addEventListener("click", () => {
      if (!s.unlocked) {
        const msg = s.needs_group
          ? `🔐 Bu testlar pullik bo'lim uchun. Ishlash uchun "${
              (s.access_groups || []).map(g => g.title).join(" yoki ") || "pullik"
            }" guruhiga qo'shiling.`
          : "🔒 Bu bo'lim hali ochilmagan — avvalgi bo'limdagi barcha testlarni tugating";
        tg.showAlert ? tg.showAlert(msg) : alert(msg);
        return;
      }
      openPracticeGroupsForStage(s);
    });
    box.appendChild(row);

    // Qulflangan bosqich ostiga — nega qulf ekanini tushuntiruvchi, chiroyli
    // alohida izoh qatori (foydalanuvchi so'ragan "pastiga izoh" ko'rinishi).
    if (!s.unlocked) {
      const hint = document.createElement("div");
      hint.className = "group-lock-hint";
      if (s.needs_group) {
        // Pullik guruh qulfi — o'quvchiga TO'G'RIDAN-TO'G'RI qo'shilish
        // havolasi beriladi, "kim bilan bog'lanay?" degan savol qolmaydi.
        const g = (s.access_groups || [])[0];
        hint.classList.add("need-group");
        hint.innerHTML = g && g.invite_link
          ? `🔐 Pullik bo'lim — <a href="${g.invite_link}" target="_blank" rel="noopener">"${g.title}" guruhiga qo'shiling</a>`
          : `🔐 Bu testlar pullik bo'lim uchun — ustoz bilan bog'laning`;
      } else {
        const prevStage = practiceStages[i - 1];
        hint.innerHTML = prevStage
          ? `🔒 Avval <strong>"${prevStage.title}"</strong> bo'limidagi barcha testlarni tugating`
          : `🔒 Bu bo'lim hali ochilmagan`;
      }
      box.appendChild(hint);
    }
  });
}

// ---------- 3-bosqich: tanlangan bosqich ICHIDAGI turkumlar (qulflanmaydi) ----------

async function openPracticeGroupsForStage(stage) {
  activePracticeStage = stage;
  activePracticeGroup = null;
  document.getElementById("practiceStageLanding").classList.add("hidden");
  document.getElementById("practiceGroupLanding").classList.remove("hidden");
  document.getElementById("practiceTestListView").classList.add("hidden");
  document.getElementById("practiceGroupLandingTitle").textContent = `${stage.icon || "📶"} ${stage.title}`;
  const box = document.getElementById("practiceGroupList");
  box.innerHTML = skeletonCards(2);
  try {
    const res = await apiFetch(`/api/test-stages/${stage.id}/groups`);
    const data = await res.json();
    practiceGroups = data.groups;
    renderPracticeGroupList();
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

function renderPracticeGroupList() {
  // Bosqich ICHIDAGI turkumlar bir-biriga nisbatan QULFLANMAYDI — bosqich
  // allaqachon ochilgan bo'lgani uchun barchasi baravar ochiq ko'rsatiladi.
  const box = document.getElementById("practiceGroupList");
  box.innerHTML = "";
  if (practiceGroups.length === 0) {
    box.innerHTML = emptyHtml("Bu bo'lim uchun hozircha turkum qo'shilmagan");
    return;
  }
  practiceGroups.forEach((g, i) => {
    const row = document.createElement("div");
    row.className = "module-item";
    const metaText = g.total_count > 0
      ? `${g.completed_count}/${g.total_count} test tugallandi${g.is_done ? " · ✅ Tugallangan" : ""}`
      : "Hozircha test qo'shilmagan";
    row.innerHTML = `
      <div class="module-num">${g.icon || (i + 1)}</div>
      <div class="module-info">
        <div class="module-title">${g.title}</div>
        <div class="module-meta">${g.subtitle ? g.subtitle + " · " : ""}${metaText}</div>
      </div>
      <div class="module-arrow">›</div>
    `;
    row.addEventListener("click", () => openPracticeGroupTests(g));
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

const START_BTN_ID_BY_MODE = {
  control: "startControlBtn", attestation: "startAttestationBtn", certificate: "startCertificateBtn", test: "startTestBtn",
};
const START_BTN_TEXT_BY_MODE = {
  control: "▶ Nazorat testini boshlash",
  attestation: "▶ Attestatsiyani boshlash",
  certificate: "▶ Sertifikatni boshlash",
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
      answers: {}, // question_id -> tanlangan variant raqami / "javob berilgan" belgisi (erkin o'zgartiriladi)
      flags: new Set(), // question_id lar — Attestatsiyada "Belgilash" bosilgan savollar
      // ---- Milliy sertifikat (Y2/O1/O2) uchun qo'shimcha holat ----
      matchAnswers: {}, // Y2: question_id -> {chapIndex: o'ngIndex}
      matchOrders: {}, // Y2: question_id -> o'ng ustun ko'rsatilish tartibi (aralashtirilgan)
      textAnswers: {}, // O1: question_id -> kiritilgan matn
      writtenDrafts: {}, // O2: question_id -> {photoUrls, textAnswer, saved}
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

// ================================================================
// MILLIY SERTIFIKAT RO'YXATI VA TAFSILOTI
// (Bilimni baholash agentligi rasmiy formati — 43 savol: Y1/Y2/O1/O2)
// ================================================================

async function loadCertificateTestList() {
  const container = document.getElementById("certificateTestList");
  container.innerHTML = skeletonCards(2);
  try {
    const res = await apiFetch(`/api/certificate-tests`);
    const data = await res.json();
    allCertificateTests = data.tests;
    certificateTestsLoaded = true;
    renderCertificateTestList();
  } catch (e) {
    console.error(e);
    container.innerHTML = errorHtml();
  }
}

function renderCertificateTestList() {
  const container = document.getElementById("certificateTestList");
  container.innerHTML = "";

  if (allCertificateTests.length === 0) {
    container.innerHTML = emptyHtml("Hozircha Milliy sertifikat testi qo'shilmagan");
    return;
  }

  allCertificateTests.forEach(t => {
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
    card.addEventListener("click", () => openCertificateDetail(t));
    container.appendChild(card);
  });
}

function openCertificateDetail(test) {
  currentCertificateMeta = test;
  const content = document.getElementById("certificateDetailContent");

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
      <button class="gold-btn" id="startCertificateBtn">▶ Sertifikatni boshlash</button>
    </div>
    <p style="text-align:center;color:var(--text-dim);font-size:11px;margin-top:14px;">
      Bu — Bilimni baholash agentligining rasmiy Milliy sertifikat imtihoni formatiga mos sinov: yopiq test,
      moslashtirish, qisqa javob va kengaytirilgan yozma ish. Yozma ish qismini o'qituvchi qo'lda baholaydi,
      shu sababli yakuniy natija darhol emas — baholangach ko'rinadi. Ko'rsatiladigan daraja (A+/A/B+...) —
      taxminiy, rasmiy Rash (IRT) natijasidan farq qilishi mumkin.
    </p>
  `;
  document.getElementById("startCertificateBtn").addEventListener("click", () => startTest(test, "certificate"));

  showScreen("certificate-detail");
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
  const qType = question.question_type || "Y1";

  document.getElementById("testProgressFill").style.width = `${(answeredCount / total) * 100}%`;

  const subjectSuffix = question.subject ? ` · ${question.subject}` : "";

  const isAttestation = currentAttempt.mode === "attestation";
  const isCertificate = currentAttempt.mode === "certificate";
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

  const certTypeBadge = isCertificate ? `<div class="cert-type-badge">${CERT_TYPE_LABELS[qType] || qType}</div>` : "";

  const content = document.getElementById("testTakingContent");
  content.innerHTML = `
    <div class="question-counter">${index + 1} / ${total}-SAVOL${subjectSuffix} · ${answeredCount}/${total} javob berilgan</div>
    <div class="question-nav-grid">${navButtons}</div>
    ${certTypeBadge}
    <div class="question-card">
      <div class="question-text">${question.question_text}</div>
      ${question.image_url ? `<img class="question-image" src="${question.image_url}" alt="Savol rasmi">` : ""}
      ${renderQuestionTables(question.table_data)}
    </div>
    ${attestationActions}
    <div id="answerArea">${renderAnswerAreaHtml(question, qType)}</div>
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

  wireAnswerAreaEvents(question, qType);

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

// ================================================================
// MILLIY SERTIFIKAT: savol turiga qarab javob maydoni (Y1/Y2/O1/O2)
// ================================================================

function escAttr(str) {
  return String(str == null ? "" : str)
    .replace(/&/g, "&amp;").replace(/"/g, "&quot;")
    .replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function fmtPoints(n) {
  const r = Math.round((n || 0) * 10) / 10;
  return Number.isInteger(r) ? String(r) : r.toFixed(1);
}

// Savol javob berilganda (yoki bekor qilinganda) faqat shu savolning
// navigatsiya tugmasi va progress-panelini yangilaydi — butun savolni
// qayta chizmaydi, shu bilan matn kiritish maydonidagi kursor/fokus
// yo'qolib qolmaydi (O1/O2 uchun muhim).
function updateNavButtonAnsweredState(questionId) {
  const { test } = currentAttempt;
  const i = test.questions.findIndex(q => q.id === questionId);
  if (i === -1) return;
  const btn = document.querySelector(`.qnav-btn[data-index="${i}"]`);
  if (btn) btn.classList.toggle("qnav-answered", currentAttempt.answers[questionId] !== undefined);
  const total = test.questions.length;
  const answeredCount = Object.keys(currentAttempt.answers).length;
  const fill = document.getElementById("testProgressFill");
  if (fill) fill.style.width = `${(answeredCount / total) * 100}%`;
  const counter = document.querySelector(".question-counter");
  if (counter) {
    const idx = currentAttempt.index;
    const q = test.questions[idx];
    const subjectSuffix = q.subject ? ` · ${q.subject}` : "";
    counter.textContent = `${idx + 1} / ${total}-SAVOL${subjectSuffix} · ${answeredCount}/${total} javob berilgan`;
  }
}

function renderAnswerAreaHtml(question, qType) {
  if (qType === "Y2") return renderY2MatchingHtml(question);
  if (qType === "O1") return renderO1TextInputHtml(question);
  if (qType === "O2") return renderO2WrittenAreaHtml(question);
  return renderY1OptionsHtml(question);
}

function wireAnswerAreaEvents(question, qType) {
  if (qType === "Y2") {
    document.querySelectorAll(".cert-match-select").forEach(sel => {
      sel.addEventListener("change", () => {
        const leftIndex = parseInt(sel.getAttribute("data-left-index"));
        const rightIndex = sel.value === "" ? null : parseInt(sel.value);
        submitMatchAnswer(question, leftIndex, rightIndex);
      });
    });
  } else if (qType === "O1") {
    wireO1Input(question);
  } else if (qType === "O2") {
    wireO2Events(question);
  } else {
    document.querySelectorAll("#optionList .option-btn").forEach(btn => {
      btn.addEventListener("click", () => selectOption(parseInt(btn.getAttribute("data-option-index"))));
    });
  }
}

// ---------- Y1: bitta to'g'ri javobli yopiq test (4 variant) ----------

function renderY1OptionsHtml(question) {
  const selectedIndex = currentAttempt.answers[question.id];
  const options = [
    ["1", question.option_1], ["2", question.option_2],
    ["3", question.option_3], ["4", question.option_4]
  ];
  return `
    <div class="option-list" id="optionList">
      ${options.map(([idx, text]) => `
        <button class="option-btn ${parseInt(idx) === selectedIndex ? "option-selected-neutral" : ""}" data-option-index="${idx}">
          <span class="option-letter">${idx}</span><span>${text}</span>
        </button>
      `).join("")}
    </div>
  `;
}

// ---------- Y2: moslashtirish (chap ustunga o'ng ustundan mos javob tanlanadi) ----------

function getMatchOrder(question) {
  if (!currentAttempt.matchOrders[question.id]) {
    const order = (question.right || []).map((_, i) => i);
    for (let i = order.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [order[i], order[j]] = [order[j], order[i]];
    }
    currentAttempt.matchOrders[question.id] = order;
  }
  return currentAttempt.matchOrders[question.id];
}

function renderY2MatchingHtml(question) {
  const order = getMatchOrder(question);
  const savedPairs = currentAttempt.matchAnswers[question.id] || {};
  const rows = (question.left || []).map((leftText, leftIdx) => {
    const selectedRight = savedPairs[leftIdx];
    const optionsHtml = order.map(rightIdx => `
      <option value="${rightIdx}" ${selectedRight === rightIdx ? "selected" : ""}>${escAttr(question.right[rightIdx])}</option>
    `).join("");
    return `
      <div class="cert-match-row">
        <div class="cert-match-left">${leftIdx + 1}. ${leftText}</div>
        <select class="cert-match-select ${selectedRight !== undefined ? "cert-match-filled" : ""}" data-left-index="${leftIdx}">
          <option value="">— tanlang —</option>
          ${optionsHtml}
        </select>
      </div>
    `;
  }).join("");
  return `
    <div class="cert-answer-block">
      <div class="cert-answer-label">Har bir chap ustundagi elementga mos o'ng ustundagi javobni tanlang:</div>
      ${rows}
    </div>
  `;
}

async function submitMatchAnswer(question, leftIndex, rightIndex) {
  const pairsMap = currentAttempt.matchAnswers[question.id] || (currentAttempt.matchAnswers[question.id] = {});
  if (rightIndex === null || Number.isNaN(rightIndex)) delete pairsMap[leftIndex];
  else pairsMap[leftIndex] = rightIndex;

  const totalLeft = (question.left || []).length;
  const filled = Object.keys(pairsMap).length;
  if (filled >= totalLeft && totalLeft > 0) currentAttempt.answers[question.id] = true;
  else delete currentAttempt.answers[question.id];

  renderCurrentQuestion();

  const pairsArray = Object.entries(pairsMap).map(([l, r]) => [parseInt(l), r]);
  try {
    const res = await apiFetch(`${attemptApiBase()}/${currentAttempt.id}/answer`, {
      method: "POST",
      body: JSON.stringify({ question_id: question.id, match_answer: pairsArray })
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

// ---------- O1: qisqa (ochiq) javobli matn kiritish ----------

function renderO1TextInputHtml(question) {
  const savedText = currentAttempt.textAnswers[question.id] || "";
  return `
    <div class="cert-answer-block">
      <div class="cert-answer-label">Javobingizni yozing:</div>
      <input type="text" class="cert-text-input" id="o1AnswerInput" placeholder="Javob..." value="${escAttr(savedText)}">
    </div>
  `;
}

let _o1DebounceTimer = null;

function wireO1Input(question) {
  const input = document.getElementById("o1AnswerInput");
  if (!input) return;
  input.addEventListener("input", () => {
    const text = input.value;
    currentAttempt.textAnswers[question.id] = text;
    if (text.trim()) currentAttempt.answers[question.id] = true;
    else delete currentAttempt.answers[question.id];
    updateNavButtonAnsweredState(question.id);
    clearTimeout(_o1DebounceTimer);
    _o1DebounceTimer = setTimeout(() => submitTextAnswer(question, text), 600);
  });
  input.addEventListener("blur", () => {
    clearTimeout(_o1DebounceTimer);
    submitTextAnswer(question, input.value);
  });
}

async function submitTextAnswer(question, text) {
  try {
    const res = await apiFetch(`${attemptApiBase()}/${currentAttempt.id}/answer`, {
      method: "POST",
      body: JSON.stringify({ question_id: question.id, answer_text: text })
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

// ---------- O2: kengaytirilgan javobli yozma ish (matn + rasm, qo'lda baholanadi) ----------

function renderO2WrittenAreaHtml(question) {
  const draft = currentAttempt.writtenDrafts[question.id] || (currentAttempt.writtenDrafts[question.id] = { photoUrls: [], textAnswer: "", saved: false });
  const maxScoreLabel = question.max_score ? `<div class="cert-answer-label">Maksimal ball: ${question.max_score}</div>` : "";
  const thumbs = draft.photoUrls.map((url, i) => `
    <div class="cert-photo-thumb-wrap">
      <img class="cert-photo-thumb" src="${url}" data-photo-index="${i}">
      <button type="button" class="cert-photo-remove" data-remove-index="${i}">×</button>
    </div>
  `).join("");
  return `
    <div class="cert-answer-block">
      <div class="cert-answer-label">Yechimingizni matn va/yoki rasm (qo'lda yozilgan ish surati) sifatida yuboring:</div>
      ${maxScoreLabel}
      <textarea class="cert-textarea" id="o2AnswerTextarea" placeholder="Yechimingizni shu yerga yozishingiz mumkin (ixtiyoriy)...">${escAttr(draft.textAnswer)}</textarea>
      <div class="cert-upload-row">
        <button type="button" class="cert-upload-btn" id="o2UploadBtn">📷 Rasm biriktirish</button>
        <input type="file" accept="image/*" id="o2FileInput" class="hidden">
      </div>
      <div class="cert-photo-thumbs" id="o2PhotoThumbs">${thumbs}</div>
      <div class="cert-o2-status ${draft.saved ? "cert-o2-saved" : ""}" id="o2Status">
        ${draft.saved ? "✅ Yuborildi — o'qituvchi tomonidan baholanadi" : "Hali yuborilmagan"}
      </div>
    </div>
  `;
}

let _o2DebounceTimer = null;

function wireO2Events(question) {
  const draft = currentAttempt.writtenDrafts[question.id];
  const textarea = document.getElementById("o2AnswerTextarea");
  if (textarea) {
    textarea.addEventListener("input", () => {
      draft.textAnswer = textarea.value;
      clearTimeout(_o2DebounceTimer);
      _o2DebounceTimer = setTimeout(() => submitWrittenAnswer(question), 700);
    });
    textarea.addEventListener("blur", () => {
      clearTimeout(_o2DebounceTimer);
      submitWrittenAnswer(question);
    });
  }
  const uploadBtn = document.getElementById("o2UploadBtn");
  const fileInput = document.getElementById("o2FileInput");
  if (uploadBtn && fileInput) {
    uploadBtn.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", async () => {
      const file = fileInput.files[0];
      if (!file) return;
      await uploadO2Photo(question, file);
      fileInput.value = "";
    });
  }
  document.querySelectorAll("#o2PhotoThumbs .cert-photo-thumb").forEach(img => {
    img.addEventListener("click", () => openLightbox(img.src));
  });
  document.querySelectorAll("#o2PhotoThumbs .cert-photo-remove").forEach(btn => {
    btn.addEventListener("click", () => removeO2Photo(question, parseInt(btn.getAttribute("data-remove-index"))));
  });
}

async function uploadO2Photo(question, file) {
  const status = document.getElementById("o2Status");
  if (status) status.textContent = "⏳ Yuklanmoqda...";
  try {
    const formData = new FormData();
    formData.append("file", file);
    const res = await apiFetch(`/api/upload-answer-image`, { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Rasmni yuklab bo'lmadi");
    }
    const data = await res.json();
    currentAttempt.writtenDrafts[question.id].photoUrls.push(data.url);
    await submitWrittenAnswer(question);
  } catch (e) {
    console.error(e);
    tg.showAlert ? tg.showAlert(e.message || "Rasmni yuklab bo'lmadi") : alert(e.message || "Xatolik yuz berdi");
  }
  renderCurrentQuestion();
}

function removeO2Photo(question, idx) {
  const draft = currentAttempt.writtenDrafts[question.id];
  draft.photoUrls.splice(idx, 1);
  submitWrittenAnswer(question);
  renderCurrentQuestion();
}

async function submitWrittenAnswer(question) {
  const draft = currentAttempt.writtenDrafts[question.id];
  const hasContent = draft.photoUrls.length > 0 || (draft.textAnswer && draft.textAnswer.trim());
  try {
    await apiFetch(`/api/attempt/${currentAttempt.id}/written-answer`, {
      method: "POST",
      body: JSON.stringify({ question_id: question.id, photo_urls: draft.photoUrls, text_answer: draft.textAnswer || null })
    });
    draft.saved = !!hasContent;
    if (hasContent) currentAttempt.answers[question.id] = true;
    else delete currentAttempt.answers[question.id];
    updateNavButtonAnsweredState(question.id);
    const status = document.getElementById("o2Status");
    if (status) {
      status.classList.toggle("cert-o2-saved", !!hasContent);
      status.textContent = hasContent ? "✅ Yuborildi — o'qituvchi tomonidan baholanadi" : "Hali yuborilmagan";
    }
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

  if (mode === "certificate") {
    await renderCertificateResult(finalResult, timedOut);
    showScreen("test-result");
    refreshCoins();
    return;
  }

  const total = currentAttempt.test.questions.length;
  const score = finalResult ? finalResult.score : Object.keys(currentAttempt.answers).length;
  const percent = total > 0 ? Math.round((score / total) * 100) : 0;
  const countsForRanking = finalResult ? finalResult.counts_for_ranking : null;

  await renderAttemptResult(currentAttempt.id, mode, score, total, percent, timedOut, countsForRanking);
  showScreen("test-result");
  refreshCoins();
}

// ---------- Milliy sertifikat: og'irliklangan ball + (taxminiy) daraja natijasi ----------

async function renderCertificateResult(finalResult, timedOut) {
  const content = document.getElementById("testResultContent");

  if (!finalResult) {
    content.innerHTML = `
      <div class="cert-pending-box">
        <div class="cert-pending-icon">⚠️</div>
        <div class="cert-pending-title">Natijani yuklab bo'lmadi</div>
        <div class="cert-pending-sub">Internet aloqasini tekshirib, "Mening natijalarim" bo'limidan qayta urinib ko'ring.</div>
      </div>
      <div class="result-actions" style="margin:16px;">
        <button class="secondary-btn" id="backToTestsBtn">${BACK_LABEL_BY_MODE.certificate}</button>
      </div>
    `;
    document.getElementById("backToTestsBtn").addEventListener("click", () => {
      activeTestsTab = "certificate";
      navigateTo("tests");
    });
    return;
  }

  const reviewStatus = finalResult.review_status;
  const rawScore = finalResult.raw_score_points || 0;
  const maxScore = finalResult.max_score_points || 0;
  const percent = maxScore > 0 ? Math.round((rawScore / maxScore) * 1000) / 10 : 0;
  const level = finalResult.certificate_level;

  if (reviewStatus === "pending_review") {
    content.innerHTML = `
      <div class="cert-pending-box">
        <div class="cert-pending-icon">⏳</div>
        <div class="cert-pending-title">Yozma ish tekshirilmoqda</div>
        <div class="cert-pending-sub">Kengaytirilgan javobli (yozma) qismingizni o'qituvchi qo'lda baholaydi. Baholangach, yakuniy ball va daraja shu yerda ko'rinadi.</div>
      </div>
      <div class="control-result-stats-row">
        <div class="control-stat"><div class="num">${fmtPoints(rawScore)}</div><div class="lbl">Avtomatik ball</div></div>
        <div class="control-stat"><div class="num">${fmtPoints(maxScore)}</div><div class="lbl">Jami maksimal ball</div></div>
      </div>
      <div class="result-actions" style="margin:16px;">
        <button class="secondary-btn" id="backToTestsBtn">${BACK_LABEL_BY_MODE.certificate}</button>
      </div>
    `;
  } else {
    content.innerHTML = `
      <div class="test-result-content">
        <div class="result-score-circle">
          <div class="score-num">${fmtPoints(rawScore)}/${fmtPoints(maxScore)}</div>
          <div class="score-total">${percent}%</div>
        </div>
        <div class="result-title">${timedOut ? "⏰ Vaqt tugadi" : (RESULT_TITLE_BY_MODE.certificate || "Yakunlandi")}</div>
        ${level ? `<div class="cert-level-badge">${level}</div>` : `<div class="result-sub">Sertifikat darajasiga hali yetmadingiz</div>`}
      </div>
      <p class="cert-level-caveat">⚠️ Bu — taxminiy daraja (jamlangan og'irliklangan ball asosida). Bilimni baholash agentligining rasmiy Rash (IRT) modeli natijasidan farq qilishi mumkin.</p>
      <div class="control-result-stats-row">
        <div class="control-stat"><div class="num">${fmtPoints(rawScore)}</div><div class="lbl">Olingan ball</div></div>
        <div class="control-stat"><div class="num">${fmtPoints(maxScore)}</div><div class="lbl">Maksimal ball</div></div>
        <div class="control-stat"><div class="num">${percent}%</div><div class="lbl">Foiz</div></div>
      </div>
      <div class="result-actions" style="margin:16px;">
        <button class="secondary-btn" id="retakeTestBtn">🔁 Qayta urinish</button>
        <button class="secondary-btn" id="backToTestsBtn">${BACK_LABEL_BY_MODE.certificate}</button>
      </div>
    `;
    const retakeBtn = document.getElementById("retakeTestBtn");
    if (retakeBtn) retakeBtn.addEventListener("click", () => startTest(currentCertificateMeta, "certificate"));
  }

  document.getElementById("backToTestsBtn").addEventListener("click", () => {
    activeTestsTab = "certificate";
    navigateTo("tests");
  });
}

const RESULT_TITLE_BY_MODE = {
  test: "🎉 Test yakunlandi",
  simulator: "🎯 Simulyator yakunlandi",
  control: "🎓 Nazorat testi yakunlandi",
  attestation: "📋 Attestatsiya yakunlandi",
  certificate: "🎓 Milliy sertifikat sinovi yakunlandi",
};

const BACK_LABEL_BY_MODE = {
  simulator: "Simulyatorlar ro'yxatiga qaytish",
  control: "Nazorat testlariga qaytish",
  attestation: "Attestatsiya ro'yxatiga qaytish",
  certificate: "Milliy sertifikat ro'yxatiga qaytish",
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
  document.getElementById("tabBtnCertificate").addEventListener("click", () => switchTestsTab("certificate"));

  document.getElementById("practiceBackToSubjectsBtn").addEventListener("click", () => resetPracticeFlowToSubjects());
  document.getElementById("practiceBackToStagesBtn").addEventListener("click", () => {
    if (activePracticeSubject) openPracticeStages(activePracticeSubject);
    else resetPracticeFlowToSubjects();
  });
  document.getElementById("practiceBackToGroupsBtn").addEventListener("click", () => {
    if (activePracticeStage) openPracticeGroupsForStage(activePracticeStage);
    else if (activePracticeSubject) openPracticeStages(activePracticeSubject);
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
