// js/studentResults.js
// "Natijalar" — o'quvchilarning sertifikat natijalari va kurs haqidagi
// fikrlari lentasi. Reyting (leaderboard)dan BUTUNLAY ALOHIDA — bu yerdagi
// har bir yozuvni admin qo'lda qo'shadi (rasm + qisqa natija + fikr matni).

import { publicFetch } from "./api.js";
import { errorHtml, emptyHtml, skeletonCards, openLightbox } from "./components.js";

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str || "";
  return div.innerHTML;
}

export async function loadStudentResults() {
  const container = document.getElementById("studentResultsList");
  container.innerHTML = skeletonCards(3);
  try {
    const res = await publicFetch(`/api/student-results`);
    const data = await res.json();
    const results = data.results || [];

    if (results.length === 0) {
      container.innerHTML = emptyHtml("Hozircha natijalar qo'shilmagan");
      return;
    }

    container.innerHTML = results.map(r => `
      <div class="result-card">
        ${r.image_url
          ? `<img class="result-card-img" src="${r.image_url}" alt="${escapeHtml(r.student_name)}">`
          : ""}
        <div class="result-card-body">
          <div class="result-card-top">
            <div class="result-card-name">${escapeHtml(r.student_name)}</div>
            ${r.subject ? `<div class="result-card-subject">${escapeHtml(r.subject)}</div>` : ""}
          </div>
          ${r.result_text ? `<div class="result-card-stat">${escapeHtml(r.result_text)}</div>` : ""}
          ${r.feedback_text ? `<div class="result-card-quote">"${escapeHtml(r.feedback_text)}"</div>` : ""}
        </div>
      </div>
    `).join("");

    container.querySelectorAll(".result-card-img").forEach(img => {
      img.addEventListener("click", () => openLightbox(img.src));
    });
  } catch (e) {
    console.error(e);
    container.innerHTML = errorHtml();
  }
}
