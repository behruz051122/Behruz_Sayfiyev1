// js/homework.js
// "Vazifa topshirish" bo'limi — o'quvchi ishlangan masalalar yechimini
// rasmga tushirib yuklaydi.
//
// Uch bosqichli oqim:
//   1) Fan tanlash (Kimyo, Biologiya, ...) — faqat tegishli kursga
//      yozilgan o'quvchiga ochiq
//   2) Raqamlangan paragraflar ro'yxati — KETMA-KET ochiladi
//   3) Bitta paragraf: rasm yuklash paneli, "+" bilan yana rasm qo'shish
//      va "Vazifalar to'liq yuklandi" tugmasi bilan yakunlash

import { apiFetch, tg } from "./api.js";
import { showScreen } from "./navigate.js";
import { loadingHtml, errorHtml, emptyHtml, openLightbox, skeletonCards, showToast } from "./components.js";

let subjects = [];
let currentSubject = null;
let currentParagraph = null;
let currentPhotos = [];
let currentStatus = "empty";
let uploading = false;

function esc(str) {
  const d = document.createElement("div");
  d.textContent = str == null ? "" : String(str);
  return d.innerHTML;
}

// ================================================================
// 1-BOSQICH: FAN (BO'LIM) TANLASH
// ================================================================

export async function loadHomeworkSubjects() {
  showScreen("homework");
  const box = document.getElementById("homeworkSubjectList");
  box.innerHTML = skeletonCards(2);
  try {
    const res = await apiFetch(`/api/homework/subjects`);
    const data = await res.json();
    subjects = data.subjects || [];
    renderHomeworkSubjects();
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

function renderHomeworkSubjects() {
  const box = document.getElementById("homeworkSubjectList");
  box.innerHTML = "";

  if (!subjects.length) {
    box.innerHTML = emptyHtml("Hozircha bo'lim qo'shilmagan");
    return;
  }

  subjects.forEach(s => {
    const total = s.total_count || 0;
    const done = s.done_count || 0;
    const percent = total > 0 ? Math.round((done / total) * 100) : 0;

    const card = document.createElement("button");
    card.type = "button";
    card.className = `hw-subject-card${s.unlocked ? "" : " hw-subject-locked"}`;
    card.innerHTML = `
      <div class="hw-subject-icon">${esc(s.icon) || "🧪"}</div>
      <div class="hw-subject-body">
        <div class="hw-subject-title">${esc(s.title)}</div>
        <div class="hw-subject-sub">
          ${s.unlocked
            ? `${done}/${total} paragraf topshirilgan`
            : "🔒 Bu bo'lim uchun tegishli kursga yozilishingiz kerak"}
        </div>
        ${s.unlocked && total > 0 ? `
          <div class="hw-progress-track"><div class="hw-progress-fill" style="width:${percent}%"></div></div>
        ` : ""}
      </div>
      ${s.unlocked ? `<div class="hw-subject-arrow">›</div>` : `<div class="hw-subject-arrow">🔒</div>`}
    `;
    if (s.unlocked) card.addEventListener("click", () => openHomeworkParagraphs(s));
    else card.addEventListener("click", () => {
      const msg = "Bu bo'lim sizga ochiq emas — tegishli kursga yozilganingizdan so'ng ochiladi.";
      tg.showAlert ? tg.showAlert(msg) : alert(msg);
    });
    box.appendChild(card);
  });
}

// ================================================================
// 2-BOSQICH: PARAGRAFLAR RO'YXATI (ketma-ket ochiladi)
// ================================================================

async function openHomeworkParagraphs(subject) {
  currentSubject = subject;
  showScreen("homework-paragraphs");
  document.getElementById("homeworkParagraphsTitle").textContent = `${subject.icon || "🧪"} ${subject.title}`;
  const box = document.getElementById("homeworkParagraphList");
  const progressBox = document.getElementById("homeworkProgressBox");
  box.innerHTML = loadingHtml();
  progressBox.innerHTML = "";

  try {
    const res = await apiFetch(`/api/homework/subjects/${subject.id}/paragraphs`);
    if (!res.ok) {
      box.innerHTML = errorHtml("Bu bo'lim sizga ochiq emas");
      return;
    }
    const data = await res.json();
    renderHomeworkParagraphs(data.paragraphs || []);
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

function renderHomeworkParagraphs(paragraphs) {
  const box = document.getElementById("homeworkParagraphList");
  const progressBox = document.getElementById("homeworkProgressBox");
  box.innerHTML = "";

  if (!paragraphs.length) {
    progressBox.innerHTML = "";
    box.innerHTML = emptyHtml("Bu bo'limda hali paragraf belgilanmagan");
    return;
  }

  const done = paragraphs.filter(p => p.status === "submitted" || p.status === "graded").length;
  const total = paragraphs.length;
  const percent = Math.round((done / total) * 100);
  const graded = paragraphs.filter(p => p.status === "graded");
  const avg = graded.length
    ? (graded.reduce((s, p) => s + (p.teacher_score || 0), 0) / graded.length).toFixed(1)
    : null;

  progressBox.innerHTML = `
    <div class="hw-progress-card">
      <div class="hw-progress-head">
        <div>
          <div class="hw-progress-num">${done}<span>/${total}</span></div>
          <div class="hw-progress-lbl">topshirilgan</div>
        </div>
        ${avg !== null ? `
          <div class="hw-progress-avg">
            <div class="hw-progress-num">${avg}<span>/10</span></div>
            <div class="hw-progress-lbl">o'rtacha ball</div>
          </div>` : ""}
      </div>
      <div class="hw-progress-track"><div class="hw-progress-fill" style="width:${percent}%"></div></div>
    </div>
  `;

  box.innerHTML = renderHomeworkPathHtml(paragraphs);
  wireHomeworkPathEvents(paragraphs);
  scrollToCurrentNode();
}

// ================================================================
// VAZIFALAR YO'LI (o'yin uslubidagi ilonsimon xarita)
// ================================================================
//
// Oddiy ikki qatorli ro'yxat o'rniga — egri-bugri YO'L. Har bir
// paragraf yo'l ustidagi bekat; joriy bekat pulslanib turadi va
// "SIZ SHU YERDASIZ" deb belgilanadi; har 10-paragrafda esa
// "nazorat nuqtasi" bayrog'i chiqadi. Bu o'quvchiga o'z yo'lini
// ko'rish va oldinga intilish hissini beradi.

const PATH_W = 288;          // yo'lak kengligi (piksel, markazlashtirilgan)
const PATH_ROW_H = 96;       // bekatlar orasidagi vertikal masofa
const PATH_NODE = 68;        // bekat diametri
const PATH_AMPLITUDE = 82;   // ilonsimon egilish kengligi
const PATH_PAD_TOP = 30;
const PATH_PAD_BOTTOM = 40;

function nodeCenter(index) {
  // Sinus to'lqini — tabiiy, "qo'lda chizilgandek" egrilik beradi
  // (to'g'ri zigzagdan ko'ra yumshoqroq ko'rinadi).
  const x = PATH_W / 2 + Math.sin(index * 0.85) * PATH_AMPLITUDE;
  const y = PATH_PAD_TOP + index * PATH_ROW_H + PATH_NODE / 2;
  return { x, y };
}

// Nuqtalar orasidan SILLIQ egri chiziq o'tkazish (kvadratik Bezier
// bilan — har bir bekatda burchak hosil bo'lmaydi).
function buildSmoothPath(points) {
  if (points.length < 2) return "";
  let d = `M ${points[0].x} ${points[0].y}`;
  for (let i = 1; i < points.length - 1; i++) {
    const midX = (points[i].x + points[i + 1].x) / 2;
    const midY = (points[i].y + points[i + 1].y) / 2;
    d += ` Q ${points[i].x} ${points[i].y} ${midX} ${midY}`;
  }
  const last = points[points.length - 1];
  d += ` L ${last.x} ${last.y}`;
  return d;
}

function nodeVisual(p, isCurrent) {
  if (!p.unlocked) return { cls: "hw-node-locked", content: "🔒" };
  if (p.status === "graded") {
    return { cls: "hw-node-graded", content: p.teacher_score != null ? p.teacher_score : "★" };
  }
  if (p.status === "submitted") return { cls: "hw-node-submitted", content: "✓" };
  if (p.status === "rejected") return { cls: "hw-node-rejected", content: "↻" };
  if (p.status === "draft") return { cls: "hw-node-draft", content: "📷" };
  return { cls: isCurrent ? "hw-node-current" : "hw-node-open", content: p.paragraph_number };
}

function renderHomeworkPathHtml(paragraphs) {
  const points = paragraphs.map((_, i) => nodeCenter(i));
  const totalHeight = PATH_PAD_TOP + paragraphs.length * PATH_ROW_H + PATH_PAD_BOTTOM;

  // Bosib o'tilgan qism yo'lni "yoritib" boradi — qaytadan chizilgan
  // ikkinchi chiziq faqat tugallangan bekatlargacha boradi.
  const doneCount = paragraphs.filter(p => p.status === "submitted" || p.status === "graded").length;
  const litPoints = points.slice(0, Math.max(doneCount, 1));

  const currentIndex = paragraphs.findIndex(
    p => p.unlocked && p.status !== "submitted" && p.status !== "graded"
  );

  const svg = `
    <svg class="hw-path-svg" width="${PATH_W}" height="${totalHeight}" viewBox="0 0 ${PATH_W} ${totalHeight}" aria-hidden="true">
      <path class="hw-path-line" d="${buildSmoothPath(points)}" />
      ${litPoints.length > 1 ? `<path class="hw-path-line-done" d="${buildSmoothPath(litPoints)}" />` : ""}
    </svg>
  `;

  const nodes = paragraphs.map((p, i) => {
    const { x, y } = points[i];
    const isCurrent = i === currentIndex;
    const v = nodeVisual(p, isCurrent);
    const isMilestone = p.paragraph_number % 10 === 0;

    return `
      <div class="hw-node-wrap${isCurrent ? " hw-node-wrap-current" : ""}"
           style="left:${x}px; top:${y}px;"
           data-para="${p.paragraph_number}" data-locked="${p.unlocked ? "0" : "1"}">
        ${isCurrent ? `<div class="hw-node-tag">SIZ SHU YERDASIZ</div>` : ""}
        <div class="hw-node ${v.cls}">
          ${isCurrent ? `<span class="hw-node-ring"></span>` : ""}
          <span class="hw-node-inner">${v.content}</span>
          ${isMilestone ? `<span class="hw-node-flag">🏁</span>` : ""}
          ${p.status === "draft" && p.photo_count > 0
            ? `<span class="hw-node-count">${p.photo_count}</span>` : ""}
        </div>
        <div class="hw-node-label">${p.paragraph_number}-paragraf</div>
      </div>
    `;
  }).join("");

  return `
    <div class="hw-path" style="height:${totalHeight}px;">
      ${svg}
      ${nodes}
    </div>
    <div class="hw-path-legend">
      <span><i class="lg lg-current"></i> Navbatdagi</span>
      <span><i class="lg lg-done"></i> Topshirilgan</span>
      <span><i class="lg lg-graded"></i> Baholangan</span>
      <span><i class="lg lg-locked"></i> Yopiq</span>
    </div>
  `;
}

function wireHomeworkPathEvents(paragraphs) {
  document.querySelectorAll(".hw-node-wrap").forEach(el => {
    el.addEventListener("click", () => {
      const num = parseInt(el.getAttribute("data-para"), 10);
      if (el.getAttribute("data-locked") === "1") {
        const msg = `Avval ${num - 1}-paragraf vazifasini to'liq yuklab, yakunlang.`;
        tg.showAlert ? tg.showAlert(msg) : alert(msg);
        return;
      }
      openHomeworkSubmit(num);
    });
  });
}

// Ochilganda darhol JORIY bekatga olib boradi — o'quvchi 60 ta
// bekatni qo'lda aylantirib o'tirmasin.
function scrollToCurrentNode() {
  const current = document.querySelector(".hw-node-wrap-current");
  if (!current) return;
  requestAnimationFrame(() => {
    current.scrollIntoView({ behavior: "smooth", block: "center" });
  });
}

// ================================================================
// 3-BOSQICH: RASM YUKLASH VA YAKUNLASH
// ================================================================

async function openHomeworkSubmit(paragraphNumber) {
  currentParagraph = paragraphNumber;
  showScreen("homework-submit");
  document.getElementById("homeworkSubmitTitle").textContent =
    `${paragraphNumber}-paragraf vazifasi`;
  const box = document.getElementById("homeworkSubmitContent");
  box.innerHTML = loadingHtml();

  try {
    const res = await apiFetch(
      `/api/homework/subjects/${currentSubject.id}/paragraphs/${paragraphNumber}`
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      box.innerHTML = errorHtml(err.detail || "Ochib bo'lmadi");
      return;
    }
    const data = await res.json();
    currentPhotos = data.photos || [];
    currentStatus = data.status || "empty";
    renderHomeworkSubmit(data);
  } catch (e) {
    console.error(e);
    box.innerHTML = errorHtml();
  }
}

function renderHomeworkSubmit(data) {
  const box = document.getElementById("homeworkSubmitContent");
  const isGraded = currentStatus === "graded";
  const isSubmitted = currentStatus === "submitted";
  const isRejected = currentStatus === "rejected";
  const canEdit = !isGraded;

  let banner = "";
  if (isGraded) {
    banner = `
      <div class="hw-banner hw-banner-graded">
        <div class="hw-banner-score">${data.teacher_score}<span>/10</span></div>
        <div>
          <div class="hw-banner-title">Baholandi</div>
          ${data.teacher_comment ? `<div class="hw-banner-text">${esc(data.teacher_comment)}</div>` : ""}
        </div>
      </div>`;
  } else if (isSubmitted) {
    banner = `
      <div class="hw-banner hw-banner-submitted">
        <div class="hw-banner-icon">⏳</div>
        <div>
          <div class="hw-banner-title">Tekshirilmoqda</div>
          <div class="hw-banner-text">Vazifangiz o'qituvchiga yuborildi. Baholangach, ball shu yerda ko'rinadi.</div>
        </div>
      </div>`;
  } else if (isRejected) {
    banner = `
      <div class="hw-banner hw-banner-rejected">
        <div class="hw-banner-icon">↩️</div>
        <div>
          <div class="hw-banner-title">Qayta ishlash kerak</div>
          ${data.teacher_comment ? `<div class="hw-banner-text">${esc(data.teacher_comment)}</div>` : ""}
        </div>
      </div>`;
  }

  const photosHtml = currentPhotos.map((p, i) => `
    <div class="hw-photo-item">
      <img src="${p.photo_url}" alt="${i + 1}-rasm" data-photo-src="${p.photo_url}">
      ${canEdit ? `<button type="button" class="hw-photo-del" data-del="${p.id}" aria-label="O'chirish">✕</button>` : ""}
      <span class="hw-photo-num">${i + 1}</span>
    </div>
  `).join("");

  const addTile = canEdit ? `
    <button type="button" class="hw-photo-add" id="hwAddPhotoBtn">
      <span class="hw-photo-add-plus">+</span>
      <span class="hw-photo-add-lbl">${currentPhotos.length ? "Yana rasm" : "Rasm qo'shish"}</span>
    </button>` : "";

  box.innerHTML = `
    ${banner}
    <p class="hw-hint">
      Ishlangan masalalar yechimini rasmga tushiring. Mavzu katta bo'lsa —
      <b>+</b> tugmasi orqali xohlagancha rasm qo'shishingiz mumkin.
    </p>
    <div class="hw-photo-grid" id="hwPhotoGrid">
      ${photosHtml}
      ${addTile}
    </div>
    <div class="hw-upload-status" id="hwUploadStatus"></div>
    ${canEdit && !isSubmitted ? `
      <div class="hw-submit-wrap">
        <button class="gold-btn" id="hwSubmitBtn" ${currentPhotos.length ? "" : "disabled"}>
          ✅ Vazifalar to'liq yuklandi
        </button>
        <p class="hw-submit-note">
          Bu tugmani bosgach vazifa o'qituvchiga yuboriladi va
          <b>keyingi paragraf ochiladi</b>.
        </p>
      </div>` : ""}
  `;

  box.querySelectorAll("[data-photo-src]").forEach(img => {
    img.addEventListener("click", () => openLightbox(img.getAttribute("data-photo-src")));
  });
  box.querySelectorAll("[data-del]").forEach(btn => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      deleteHomeworkPhoto(parseInt(btn.getAttribute("data-del"), 10));
    });
  });
  const addBtn = document.getElementById("hwAddPhotoBtn");
  if (addBtn) addBtn.addEventListener("click", () => document.getElementById("homeworkFileInput").click());
  const submitBtn = document.getElementById("hwSubmitBtn");
  if (submitBtn) submitBtn.addEventListener("click", submitHomeworkParagraph);
}

async function uploadHomeworkPhoto(file) {
  if (uploading) return;
  uploading = true;
  const status = document.getElementById("hwUploadStatus");
  if (status) status.innerHTML = `<span class="hw-uploading">⏳ Yuklanmoqda...</span>`;
  try {
    const formData = new FormData();
    formData.append("file", file);
    const res = await apiFetch(
      `/api/homework/subjects/${currentSubject.id}/paragraphs/${currentParagraph}/photo`,
      { method: "POST", body: formData }
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Rasmni yuklab bo'lmadi");
    }
    await openHomeworkSubmit(currentParagraph);
    showToast("✅ Rasm yuklandi");
  } catch (e) {
    console.error(e);
    const msg = e.message || "Rasmni yuklab bo'lmadi";
    tg.showAlert ? tg.showAlert(msg) : alert(msg);
    if (status) status.innerHTML = "";
  } finally {
    uploading = false;
  }
}

async function deleteHomeworkPhoto(photoId) {
  if (!confirm("Bu rasmni o'chirmoqchimisiz?")) return;
  try {
    const res = await apiFetch(`/api/homework/photos/${photoId}`, { method: "DELETE" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "O'chirib bo'lmadi");
    }
    await openHomeworkSubmit(currentParagraph);
  } catch (e) {
    console.error(e);
    const msg = e.message || "O'chirib bo'lmadi";
    tg.showAlert ? tg.showAlert(msg) : alert(msg);
  }
}

async function submitHomeworkParagraph() {
  if (!currentPhotos.length) {
    const msg = "Avval kamida bitta rasm yuklang.";
    tg.showAlert ? tg.showAlert(msg) : alert(msg);
    return;
  }
  const ok = confirm(
    `${currentParagraph}-paragraf vazifasini yakunlaysizmi?\n\n` +
    `Yuborilgandan keyin keyingi paragraf ochiladi.`
  );
  if (!ok) return;

  const btn = document.getElementById("hwSubmitBtn");
  if (btn) { btn.disabled = true; btn.textContent = "Yuborilmoqda..."; }
  try {
    const res = await apiFetch(
      `/api/homework/subjects/${currentSubject.id}/paragraphs/${currentParagraph}/submit`,
      { method: "POST" }
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Topshirib bo'lmadi");
    }
    showToast("🎉 Vazifa topshirildi! Keyingi paragraf ochildi.");
    await openHomeworkParagraphs(currentSubject);
  } catch (e) {
    console.error(e);
    const msg = e.message || "Topshirib bo'lmadi";
    tg.showAlert ? tg.showAlert(msg) : alert(msg);
    if (btn) { btn.disabled = false; btn.textContent = "✅ Vazifalar to'liq yuklandi"; }
  }
}

// ================================================================
// Modulni ishga tushirish
// ================================================================

export function initHomeworkModule() {
  const fileInput = document.getElementById("homeworkFileInput");
  if (fileInput) {
    fileInput.addEventListener("change", async () => {
      const file = fileInput.files && fileInput.files[0];
      if (file) await uploadHomeworkPhoto(file);
      fileInput.value = "";
    });
  }
  const backBtn = document.getElementById("homeworkBackToParagraphs");
  if (backBtn) {
    backBtn.addEventListener("click", () => {
      if (currentSubject) openHomeworkParagraphs(currentSubject);
      else loadHomeworkSubjects();
    });
  }
}
