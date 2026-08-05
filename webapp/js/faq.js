// js/faq.js
import { apiFetch } from "./api.js";
import { loadingHtml, errorHtml, emptyHtml } from "./components.js";

export async function loadFaq() {
  const content = document.getElementById("faqContent");
  content.innerHTML = loadingHtml();
  try {
    const res = await apiFetch(`/api/faq`);
    const data = await res.json();

    if (data.items.length === 0) {
      content.innerHTML = emptyHtml("Hozircha savollar qo'shilmagan");
      return;
    }

    content.innerHTML = `
      <div class="faq-list">
        ${data.items.map((item, idx) => `
          <div class="faq-item" data-idx="${idx}">
            <button class="faq-question">
              <span>${item.question}</span>
              <span class="faq-toggle">＋</span>
            </button>
            <div class="faq-answer"><div class="faq-answer-inner">${item.answer}</div></div>
          </div>
        `).join("")}
      </div>
    `;

    content.querySelectorAll(".faq-item").forEach(el => {
      const btn = el.querySelector(".faq-question");
      btn.addEventListener("click", () => {
        const isOpen = el.classList.toggle("open");
        el.querySelector(".faq-toggle").textContent = isOpen ? "－" : "＋";
      });
    });
  } catch (e) {
    console.error(e);
    content.innerHTML = errorHtml();
  }
}
