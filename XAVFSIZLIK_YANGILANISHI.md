# 1-BOSQICH: Xavfsizlik yangilanishi — joylashtirish qo'llanmasi

## Nima o'zgardi (qisqacha)

| Muammo | Avval | Endi |
|---|---|---|
| Bot tokeni, admin paroli | `config.py` ichida ochiq matn, GitHub'da ko'rinadi | `.env` faylida, GitHub'ga yuklanmaydi (`.gitignore`) |
| Admin tekshiruvi | Klient yuborgan `X-Telegram-Id` headeriga so'zsiz ishoniladi — **soxtalashtirish mumkin edi** | Telegram imzolagan `initData` HMAC-SHA256 orqali tekshiriladi — soxtalashtirib bo'lmaydi |
| Foydalanuvchi ma'lumotlari (coin, obuna, referal) | `telegram_id` oddiy query-parametr — boshqa birovning ma'lumotini so'rash mumkin edi | Har bir so'rovda `initData` orqali haqiqiy identifikatsiya tasdiqlanadi |
| Test topshirish | Attempt egasi tekshirilmagan — birov boshqaning testiga javob "qo'shib qo'yishi" mumkin edi | Har bir javob/yakunlash so'rovida attempt egasi tekshiriladi |
| Admin paroli | Oddiy matn solishtirish, cheksiz urinish | bcrypt xesh + JWT sessiya (12 soat) + login uchun rate-limit (15 daqiqada 5 urinish) |

## Joylashtirish qadamlari

### 1. Yangi fayllarni ko'chiring

Quyidagi fayllarni loyihangiz papkasiga (eskilarini almashtirib) qo'ying:

```
config.py          (almashtiring)
server.py          (almashtiring)
auth.py            (YANGI fayl)
generate_password_hash.py   (YANGI fayl)
requirements.txt   (almashtiring)
.gitignore          (YANGI fayl — agar mavjud bo'lsa, .env qatorini qo'shing)
.env                (YANGI fayl — lokal test uchun, real qiymatlar bilan tayyor)
.env.example        (YANGI fayl — GitHub uchun namuna)
webapp/app.js       (almashtiring)
```

`bot.py`, `database.py`, `index.html`, `style.css` — **o'zgarmadi**, tegmang.

### 2. Kutubxonalarni yangilang

```bash
pip install -r requirements.txt --break-system-packages
```
(yoki venv ichida bo'lsangiz oddiy `pip install -r requirements.txt`)

### 3. `.env` faylini tekshiring

`.env` fayli sizning **joriy** bot tokeningiz va joriy parolingizning (`behruz_2026`) xeshi bilan tayyor qilindi — hech narsa buzilmaydi, bot xuddi avvalgidek ishlayveradi.

**Lekin tavsiya:** parolni albatta yangilang:
```bash
python generate_password_hash.py
```
Chiqqan qatorni `.env` faylidagi `ADMIN_PASSWORD_HASH=` ga qo'ying.

### 4. GitHub'ga yuklash

```bash
git rm --cached config.py 2>nul
git add .
git commit -m "xavfsizlik: initData tasdiqlash, .env, admin JWT sessiya"
git push
```

`.env` fayli `.gitignore`da bo'lgani uchun **GitHub'ga hech qachon yuklanmaydi** — bu to'g'ri va kerakli holat.

### 5. Railway'da muhit o'zgaruvchilarini kiriting — ENG MUHIM QADAM

Railway'da kod `.env` faylini o'qimaydi (chunki u Git'ga yuklanmagan). Shuning uchun **Railway Dashboard → sizning service → Variables** bo'limiga `.env` faylidagi har bir qatorni qo'lda kiritishingiz kerak:

```
BOT_TOKEN=8949426843:AAGMfLmX3NObg8v5gn3BFPieI62-35HoVhA
ADMIN_PASSWORD_HASH=(yangi hash yoki .env dagi tayyor qiymat)
JWT_SECRET_KEY=352b76a19d78c960390e6fcc911a91982ea40c0088a4090d67b4e56ddfbffad7
ADMIN_TELEGRAM_IDS=7558364715
WEBAPP_URL=https://behruzsayfiyev1-production-4a0a.up.railway.app
BOT_USERNAME=Behruz_Sayfiyev1bot
CHANNEL_USERNAME=@Behruz_Sayfiyev1
CHANNEL_URL=https://t.me/Behruz_Sayfiyev1
BRAND_NAME=Behruz Sayfiyev
BRAND_SUB=ONLINE TA'LIM PLATFORMASI
ADMIN_CONTACT_USERNAME=BehruzSayfiyev
```

Saqlagach, Railway avtomatik qayta deploy qiladi.

> ⚠️ Agar bu qadam bajarilmasa, server ishga tushmaydi — chunki `config.py` endi majburiy o'zgaruvchilar topilmasa aniq xatolik bilan to'xtaydigan qilib yozilgan (bu ham qasddan qilingan xavfsizlik — noto'liq sozlama bilan "yashirin ishlab" xatolikka olib kelmasligi uchun).

### 6. Botni qayta ishga tushiring

Agar `bot.py`ni alohida joyda (masalan o'z kompyuteringizda yoki Railway'ning ikkinchi service'ida) ishga tushirgan bo'lsangiz, uni ham to'xtatib qayta ishga tushiring — u ham endi `.env`/muhit o'zgaruvchisidan token o'qiydi.

### 7. Tekshirish (test checklist)

- [ ] Botga `/start` yozganda xatosiz javob keladi
- [ ] Mini App ochiladi, ismingiz va coin ko'rinadi
- [ ] Kurslar ro'yxati, kurs ichi, video pleyer ishlaydi
- [ ] "Ko'rib bo'ldim" tugmasi bosilganda coin qo'shiladi
- [ ] Referal havolasi ko'rinadi va nusxalanadi
- [ ] Reyting (leaderboard) ro'yxati chiqadi
- [ ] Profil sahifasida obunalar ko'rinadi
- [ ] Admin bo'lsangiz — ⚙️ tugma ko'rinadi, admin panelga kirasiz, kurs/bo'lim/dars qo'shish-o'chirish ishlaydi
- [ ] **Xavfsizlik tekshiruvi:** brauzer konsolida quyidagini ishga tushirib ko'ring — endi 401 xatolik qaytarishi kerak:
  ```js
  fetch(location.origin + "/api/admin/courses", {
    headers: { "X-Telegram-Id": "7558364715" }
  }).then(r => console.log(r.status)) // 401 chiqishi SHART
  ```
  Agar `200` chiqsa — nimadir noto'g'ri joylashtirilgan, menga xabar bering.

## Keyingi bosqichlar (hali qilinmagan, keyingi safar tanlaysiz)

- **2-bosqich:** To'liq test topshirish interfeysi (vaqt taймeri, savol-javob ekrani, natija sahifasi) — hozir backend tayyor, frontend yo'q
- **3-bosqich:** Kod arxitekturasi — `server.py`ni routerlarga, `app.js`ni modullarga bo'lish, DB connection pooling
- **4-bosqich:** Premium UI polish — skeleton loading, qidiruv, accessibility
- **5-bosqich:** Push-eslatmalar, batafsil analitika, o'qituvchi dashboard
