// js/profile.js
import { apiFetch, tg } from "./api.js";
import { loadingHtml, errorHtml } from "./components.js";
import { brandInfo } from "./user.js";

export async function loadProfile() {
  const content = document.getElementById("profileContent");
  content.innerHTML = loadingHtml();
  try {
    const [userRes, enrollRes] = await Promise.all([
      apiFetch(`/api/user`),
      apiFetch(`/api/my-enrollments`)
    ]);
    const user = await userRes.json();
    const enrollData = await enrollRes.json();

    let html = `
      <div class="profile-card">
        <div class="profile-avatar">${(user.first_name || "?").charAt(0).toUpperCase()}</div>
        <div class="profile-name">${user.first_name}</div>
        <div class="profile-id">Telegram ID: ${user.telegram_id}</div>
        <div class="profile-stats-row">
          <div class="profile-stat"><div class="num">🪙 ${user.coins}</div><div class="lbl">Coin</div></div>
          <div class="profile-stat"><div class="num">#${user.rank || "—"}</div><div class="lbl">Reyting</div></div>
          <div class="profile-stat"><div class="num">${user.confirmed_referrals}</div><div class="lbl">Takliflar</div></div>
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
        <p style="font-size:12px;color:var(--text-dim);">Savol yoki muammo bo'lsa, admin bilan bog'laning.</p>
        <button class="gold-btn" style="margin-top:10px;" id="contactAdminBtn">💬 Admin bilan bog'lanish</button>
      </div>
    `;

    content.innerHTML = html;

    const contactBtn = document.getElementById("contactAdminBtn");
    if (contactBtn) {
      contactBtn.addEventListener("click", () => {
        const url = `https://t.me/${brandInfo.adminContact}`;
        tg.openTelegramLink ? tg.openTelegramLink(url) : window.open(url, "_blank");
      });
    }
  } catch (e) {
    console.error(e);
    content.innerHTML = errorHtml();
  }
}
