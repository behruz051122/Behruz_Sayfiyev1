// js/profile.js
import { apiFetch, tg } from "./api.js";
import { loadingHtml, errorHtml } from "./components.js";
import { brandInfo } from "./user.js";
import { downloadCertificate } from "./courses.js";
import { navigateTo } from "./navigate.js";

export async function loadProfile() {
  const content = document.getElementById("profileContent");
  content.innerHTML = loadingHtml();
  try {
    const [userRes, enrollRes, achRes, certRes] = await Promise.all([
      apiFetch(`/api/user`),
      apiFetch(`/api/my-enrollments`),
      apiFetch(`/api/achievements`),
      apiFetch(`/api/my-certificates`)
    ]);
    const user = await userRes.json();
    const enrollData = await enrollRes.json();
    const achData = await achRes.json();
    const certData = await certRes.json();

    let html = `
      <div class="profile-card">
        <div class="profile-avatar">${(user.first_name || "?").charAt(0).toUpperCase()}</div>
        <div class="profile-name">${user.first_name}</div>
        <div class="profile-id">Telegram ID: ${user.telegram_id}</div>
        <div class="profile-stats-row">
          <div class="profile-stat"><div class="num">🪙 ${user.coins}</div><div class="lbl">Coin</div></div>
          <div class="profile-stat"><div class="num">#${user.rank || "—"}</div><div class="lbl">Reyting</div></div>
          <div class="profile-stat"><div class="num">${user.confirmed_referrals}</div><div class="lbl">Takliflar</div></div>
          <div class="profile-stat streak-stat"><div class="num">🔥 ${user.current_streak || 0}</div><div class="lbl">Kunlik streak</div></div>
        </div>
      </div>

      ${(user.current_streak || 0) >= 1 ? `
        <div class="streak-banner">
          🔥 <b>${user.current_streak} kun</b> ketma-ket faolsiz! Streakni uzmaslik uchun bugun ham kamida bitta dars yoki test bajaring.
          ${user.longest_streak > user.current_streak ? `<div class="streak-best">Eng yaxshi natijangiz: ${user.longest_streak} kun</div>` : ""}
        </div>
      ` : `
        <div class="streak-banner streak-banner-start">
          🔥 Har kuni kamida bitta dars yoki test bajarib, "streak"ingizni boshlang!
        </div>
      `}

      <div class="admin-section">
        <div class="admin-section-head">
          <h3>🏅 Yutuqlarim</h3>
          <span style="font-size:11px;color:var(--text-dim);font-weight:700;">${achData.earned_count}/${achData.total_count}</span>
        </div>
        <div class="achievement-grid">
          ${achData.achievements.map(a => `
            <div class="achievement-badge ${a.earned ? "earned" : "locked"}" title="${a.description}">
              <div class="achievement-icon">${a.earned ? a.icon : "🔒"}</div>
              <div class="achievement-title">${a.title}</div>
            </div>
          `).join("")}
        </div>
      </div>

      <div class="admin-section">
        <div class="admin-section-head"><h3>🎓 Mening sertifikatlarim</h3></div>
        <div id="myCertificatesList">
          ${certData.certificates.length === 0
            ? `<div class="empty-msg">Hali sertifikatingiz yo'q — kursni 100% tugating</div>`
            : certData.certificates.map(c => `
              <div class="admin-row">
                <div class="emoji">🎓</div>
                <div class="info"><div class="t">${c.course_title}</div><div class="s">${c.course_subject} · № ${c.certificate_number}</div></div>
                <button class="ghost-btn cert-download-btn" data-course-id="${c.course_id}">⬇️</button>
              </div>
            `).join("")}
        </div>
      </div>

      <div class="admin-section">
        <div class="admin-section-head"><h3>Mening obunalarim</h3></div>
    `;

    if (enrollData.enrollments.length === 0) {
      html += `<div class="empty-msg">Hali pullik kursga obuna emassiz</div>`;
    } else {
      enrollData.enrollments.forEach(e => {
        let expiryText = "Muddatsiz";
        if (e.expiry_date) {
          const expiry = new Date(e.expiry_date + "Z");
          const now = new Date();
          const daysLeft = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24));
          expiryText = daysLeft >= 0 ? `${daysLeft} kun qoldi` : `${Math.abs(daysLeft)} kun oldin tugagan`;
        }
        html += `
          <div class="admin-row">
            <div class="emoji">${e.thumbnail_emoji || "📘"}</div>
            <div class="info"><div class="t">${e.title}</div><div class="s">${e.subject} · ${expiryText}</div></div>
          </div>
        `;
      });
    }

    html += `</div>
      <div class="admin-section">
        <div class="admin-section-head"><h3>Yordam va aloqa</h3></div>
        <p style="font-size:12px;color:var(--text-dim);">Savol yoki muammo bo'lsa, avval FAQ bo'limini ko'ring yoki admin bilan bog'laning.</p>
        <button class="gold-btn" style="margin-top:10px;" id="openFaqBtn">❓ Ko'p so'raladigan savollar</button>
        <button class="gold-btn" style="margin-top:10px;background:var(--surface2);color:var(--gold);" id="contactAdminBtn">💬 Admin bilan bog'lanish</button>
      </div>
    `;

    content.innerHTML = html;

    const faqBtn = document.getElementById("openFaqBtn");
    if (faqBtn) faqBtn.addEventListener("click", () => navigateTo("faq"));

    const contactBtn = document.getElementById("contactAdminBtn");
    if (contactBtn) {
      contactBtn.addEventListener("click", () => {
        const url = `https://t.me/${brandInfo.adminContact}`;
        tg.openTelegramLink ? tg.openTelegramLink(url) : window.open(url, "_blank");
      });
    }

    document.querySelectorAll(".cert-download-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const courseId = parseInt(btn.getAttribute("data-course-id"));
        downloadCertificate(courseId, btn);
      });
    });
  } catch (e) {
    console.error(e);
    content.innerHTML = errorHtml();
  }
}
