// js/referral.js
import { apiFetch, tg } from "./api.js";

export async function loadReferral() {
  try {
    const res = await apiFetch(`/api/referral-link`);
    const data = await res.json();
    document.getElementById("referralCount").textContent = data.confirmed_referrals;
    document.getElementById("referralLinkInput").value = data.link;

    document.getElementById("copyLinkBtn").onclick = () => {
      navigator.clipboard.writeText(data.link);
      tg.showAlert ? tg.showAlert("Havola nusxalandi!") : alert("Havola nusxalandi!");
    };
    document.getElementById("shareLinkBtn").onclick = () => {
      const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(data.link)}&text=${encodeURIComponent("Menga qo'shiling!")}`;
      tg.openTelegramLink ? tg.openTelegramLink(shareUrl) : window.open(shareUrl, "_blank");
    };

    const listBox = document.getElementById("referralFriendsList");
    listBox.innerHTML = "";
    (data.referrals || []).forEach(r => {
      const row = document.createElement("div");
      row.className = "referral-friend-row";
      row.innerHTML = `<span>${r.first_name || "Foydalanuvchi"}</span><span class="${r.confirmed ? "status-yes" : "status-no"}">${r.confirmed ? "✅ Tasdiqlangan" : "⏳ Kutilmoqda"}</span>`;
      listBox.appendChild(row);
    });
  } catch (e) { console.error(e); }
}
