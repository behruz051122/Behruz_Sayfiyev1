# v5.1 — Yechim rasmlari (PDF/JPG) qo'shildi

## Nima qo'shildi

Endi har bir video darsga (asosan kitoblar bo'limidagi "variant"lar uchun) **video bilan birga yechim rasmini** ham yuklashingiz mumkin.

- Agar darsga rasm yuklasangiz — o'quvchiga video ostida **"📄 Yechimni ko'rish"** tugmasi chiqadi
- Agar rasm yuklamasangiz (masalan Kimyo darslarida) — bu tugma **umuman ko'rinmaydi**, hech qanday noqulaylik keltirmaydi
- Yechim rasmini ochganda: yuqorida **－ / ＋** tugmalari bilan kattalashtirish/kichraytirish, kompyuterda sichqoncha bilan sudrab ko'rish, telefonda barmoq bilan tabiiy scroll
- Pastdagi "Oldingi/Keyingi/Barcha darslar" tugmalari — endi yechimlar orasida ham to'g'ridan-to'g'ri harakatlanadi

## Eski ma'lumotlaringiz xavfsiz

Bazaga yangi ustun avtomatik, xavfsiz qo'shiladi — bu men real test bilan tekshirdim: eski (rasmsiz) darslaringiz **hech qanday zarar ko'rmaydi**, ular oddiy davom etaveradi.

---

## Joylashtirish (4 ta fayl)

- `database.py`
- `webapp/index.html`
- `webapp/app.js`
- `webapp/style.css`

*(`server.py`, `config.py`, `bot.py` ga tegmang)*

```
git add .
git commit -m "v5.1 - yechim rasmlari"
git push
```
90 soniya kutib, botni qayta ishga tushiring, Mini App'ni butunlay yopib qayta oching.

---

## Rasmni qanday yuklash kerak

1. Yechim sahifasini (masalan telefon kamerasi bilan olingan yoki skaner qilingan rasmni) biror bepul rasm-hosting saytiga yuklang (masalan **imgbb.com** — ro'yxatdan o'tmasdan ham yuklash mumkin, rasm havolasini beradi)
2. O'sha havolani nusxalab oling
3. ⚙️ → kurs → Bo'limlar → Videolar → darsni tahrirlang (yoki yangi qo'shing)
4. **"Yechim rasmi havolasi"** maydoniga shu havolani qo'ying
5. Saqlang

Admin panel pastida endi **"v5.1"** yozuvi chiqishi kerak.
