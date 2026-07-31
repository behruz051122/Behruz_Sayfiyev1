# 2-BOSQICH: Test tizimi — joylashtirish va foydalanish qo'llanmasi

## Nima qo'shildi

| Bo'lim | Tavsif |
|---|---|
| 📝 Testlar ro'yxati | Fan bo'yicha filtrlanadigan test kartalari — savollar soni, vaqt chegarasi, qiyinlik darajasi (Oson/O'rta/Qiyin) ko'rsatiladi |
| ⏱ Vaqtli test topshirish | Har bir test o'z vaqt chegarasiga ega (qiyinlik darajasiga qarab avtomatik: Oson=5, O'rta=10, Qiyin=15 daqiqa, yoki qo'lda belgilash mumkin). Vaqt tugasa — test avtomatik yakunlanadi |
| ✓ Darhol natija | Har bir savolga javob berilgach — to'g'ri/noto'g'ri darhol ko'rsatiladi, to'g'ri javob yashil rangda belgilanadi |
| 🖼 Savol rasmlari | Formula, diagramma yoki chizma qo'yish mumkin — bosilganda kattalashib ochiladi |
| 🔁 Qayta urinish | Testni istagancha marta qayta topshirish mumkin, faqat **eng yaxshi natija** saqlanadi |
| 📊 Mening natijalarim | Har bir test bo'yicha eng yaxshi natijangizni progress-bar bilan ko'rish |
| 🪙 Coin tizimi | Har bir savolga **birinchi marta** to'g'ri javob bersangiz — 1 coin (qayta urinishda coin qayta berilmaydi — bu adolatli, chunki avvalgi bosqichda tushuntirilgan `user_question_progress` jadvali orqali himoyalangan) |
| ⚙️ Admin: Testlar boshqaruvi | Test yaratish/tahrirlash/o'chirish, qiyinlik darajasi va vaqt belgilash |
| ⚙️ Admin: Savollar boshqaruvi | Har bir testga savol qo'shish — matn, ixtiyoriy rasm, 4 variant, to'g'ri javobni belgilash |

**Xavfsizlik:** Barcha yangi funksiyalar 1-bosqichda o'rnatilgan `initData` tekshiruvidan foydalanadi — birov boshqa birovning test urinishiga "javob qo'shib qo'yishi" mumkin emas (server har doim urinish egasini tekshiradi).

---

## QADAM 1 — Fayllarni joylashtirish

Bu safar fayllar **`webapp` papkasi ichiga** boradi (chunki bular Mini App'ning ko'rinadigan qismi):

```
kelajak-bot/
├── bot.py                     (tegmang)
├── server.py                  (tegmang — 1-bosqichda yangilangan)
├── database.py                (tegmang)
├── config.py                  (tegmang)
├── auth.py                    (tegmang)
├── ...
└── webapp/
    ├── index.html              ← ALMASHTIRING
    ├── style.css                ← ALMASHTIRING
    └── app.js                    ← ALMASHTIRING
```

Yuklab olgan 3 ta faylni (`index.html`, `style.css`, `app.js`) `kelajak-bot/webapp/` papkasi ichiga qo'yib, eskilarini almashtiring.

> ✅ Bu safar `server.py`, `config.py`, `database.py` va boshqa Python fayllarga **hech qanday o'zgartirish kiritilmadi** — chunki test tizimining backend (server) qismi loyihangizda allaqachon tayyor edi, biz faqat unga mos frontend (ko'rinadigan interfeys) qurdik.

## QADAM 2 — GitHub'ga yuklash

```bash
git add .
git commit -m "2-bosqich: to'liq test tizimi (UI, vaqt taymeri, natijalar)"
git push
```

Railway avtomatik qayta deploy qiladi (1-2 daqiqa kuting). Bu safar **Railway Variables'ga hech narsa qo'shish shart emas** — chunki maxfiy sozlamalar o'zgarmadi.

## QADAM 3 — Mini App'ni qayta oching

Telegram'da Mini App'ni **butunlay yoping** va qaytadan oching (eski versiyani keshdan olib qolmasligi uchun).

---

## QADAM 4 — Birinchi testingizni yarating (admin sifatida)

1. ⚙️ tugmasi orqali Admin panelga o'ting
2. Pastga tushib **"Testlar"** bo'limini toping, **"+ Yangi test"** tugmasini bosing
3. Formani to'ldiring:
   - **Fan:** masalan `Kimyo`
   - **Test nomi:** masalan `1-mavzu. Atom tuzilishi`
   - **Qiyinlik darajasi:** Oson / O'rta / Qiyin — bu vaqt chegarasini avtomatik belgilaydi
   - **Vaqt chegarasi:** xohlasangiz qo'lda ham kiritishingiz mumkin (soniyada, masalan 480 = 8 daqiqa)
4. **"Testni saqlash"** tugmasini bosing
5. Yangi test ro'yxatda paydo bo'ladi — endi uning yonidagi **"Savollar"** tugmasini bosing
6. Har bir savol uchun:
   - Savol matnini yozing
   - Xohlasangiz rasm havolasini qo'shing (masalan imgbb.com orqali yuklangan formula rasmi)
   - 4 ta variantni to'ldiring
   - **"To'g'ri javob"** ro'yxatidan to'g'risini tanlang
   - **"Savolni saqlash"**ni bosing
7. Shu tarzda kerakli sondagi savollarni qo'shib chiqing

Endi Mini App'ning "Testlar" bo'limiga o'tsangiz — yangi testingiz ro'yxatda ko'rinadi va uni topshirish mumkin bo'ladi.

---

## QADAM 5 — Sinab ko'rish (test checklist)

- [ ] "Testlar" bo'limiga kirganda ro'yxat ko'rinadi
- [ ] Fan bo'yicha filtr chip'lari ishlaydi
- [ ] Testni bosganda tafsilot sahifasi ochiladi (savollar soni, vaqt)
- [ ] "Testni boshlash" bosilganda birinchi savol chiqadi, yuqorida taymer ishga tushadi
- [ ] Javob tanlaganda darhol to'g'ri/noto'g'ri ko'rsatiladi, to'g'ri javob yashil bo'ladi
- [ ] Agar rasm qo'shilgan bo'lsa — bosilganda kattalashadi
- [ ] Barcha savollardan o'tgach — natija sahifasi (ball, foiz, coin) chiqadi
- [ ] "Qayta urinish" tugmasi ishlaydi
- [ ] "Mening natijalarim" bo'limida eng yaxshi natijangiz ko'rinadi
- [ ] Taymerni tugatib ko'ring (yoki qisqa vaqtli test yarating) — vaqt tugaganda test avtomatik yakunlanadimi tekshiring
- [ ] ✕ tugmasi bosilganda tasdiqlash so'raladi va chiqib ketish ishlaydi

---

## Bilib qo'yish kerak bo'lgan cheklov

Agar foydalanuvchi test o'rtasida ilovani yopib qo'ysa (masalan qo'ng'iroq kelsa), joriy urinish saqlanmaydi — u qaytib kirganda testni **qaytadan boshlashi** kerak bo'ladi (oldingi javoblari yo'qoladi, lekin bu uning coin balansiga yoki avvalgi eng yaxshi natijasiga ta'sir qilmaydi). Bu — keyingi bosqichlarda ("urinishni davom ettirish" funksiyasi) yaxshilanishi mumkin bo'lgan joy, hozircha ko'pchilik test tizimlari uchun odatiy va qabul qilinadigan xatti-harakat.

---

## Keyingi bosqichlar

- **3-bosqich:** Kod arxitekturasi — `server.py`ni routerlarga, `app.js`ni modullarga bo'lish, DB connection pooling
- **4-bosqich:** Premium UI polish — skeleton loading, qidiruv, accessibility
- **5-bosqich:** Push-eslatmalar, batafsil analitika, o'qituvchi dashboard
