# Botni ishga tushirish — TO'LIQ BATAFSIL QO'LLANMA (yangi boshlovchi uchun)

Bu qo'llanmada hech narsa bilmasangiz ham, faqat yozilganlarni ketma-ket bajarib borsangiz, bot ishlab ketadi. Shoshilmang, har bir qadamni tugatib, keyingisiga o'ting.

---

## TUSHUNCHA: nima nimaga kerak?

- **Bot** — foydalanuvchi bilan Telegram'da yozishadigan dastur (masalan `/start` yozganda javob beradi)
- **Mini App** — bot ichida ochiladigan veb-sahifa (rasmda ko'rgan "Kelajak mediklari" paneli aynan shu)
- **Server** — Mini App internetda "yashaydigan" joy. Kompyuteringiz o'chsa ham ishlab turishi uchun kerak
- **GitHub** — kodingizni saqlaydigan bepul sayt. Railway aynan shu yerdan kodni oladi
- **Railway** — kodingizni internetga bepul chiqarib beradigan xizmat

---

## QADAM 1 — Bot yaratish (BotFather)

1. Telefoningizda yoki kompyuteringizda Telegram'ni oching
2. Qidiruv qatoriga **BotFather** deb yozing, ko'k belgili (verified) hisobni tanlang
3. "Start" tugmasini bosing
4. `/newbot` deb yozib yuboring
5. Bot sizdan **ism** so'raydi — istalgan nom yozing, masalan: `Kelajak Mediklari`
6. Keyin **username** so'raydi — bu oxiri albatta `bot` bilan tugashi kerak, masalan: `kelajak_medik_bot`. Agar "band" desa, boshqa nom sinang
7. BotFather sizga uzun harf-raqamlardan iborat **TOKEN** yuboradi, masalan:
   `7123456789:AAHf3kL9dQmZ...`
8. Bu tokenni nusxalab, biror joyga (masalan Notepad'ga) vaqtincha saqlab qo'ying. **Bu tokenni hech kimga ko'rsatmang** — bu botingizning "paroli"

---

## QADAM 2 — Kompyuteringizga kerakli dasturlarni o'rnatish

Bularning barchasi **bepul** va bir marta o'rnatiladi.

### 2.1 — Python o'rnatish
1. https://www.python.org/downloads/ saytiga kiring
2. "Download Python" tugmasini bosib yuklab oling
3. O'rnatishda chiqadigan oynada pastdagi **"Add Python to PATH"** katagini albatta belgilang, keyin "Install Now" bosing

### 2.2 — Git o'rnatish (kodni GitHub'ga yuklash uchun)
1. https://git-scm.com/downloads saytiga kiring
2. Operatsion tizimingizga mos versiyani yuklab, o'rnating (hammasini "Next" bosib o'tsangiz bo'ladi)

### 2.3 — Kod muharriri (ixtiyoriy, lekin tavsiya qilinadi)
- https://code.visualstudio.com/ dan **VS Code**'ni yuklab o'rnating. Bu yerda fayllaringizni ko'rish va tahrirlash oson bo'ladi

---

## QADAM 3 — Loyiha fayllarini joylashtirish

1. Men bergan `kelajak-bot.zip` faylini kompyuteringizga yuklab oling
2. Uni istalgan joyga (masalan Ish stoli — Desktop) chiqaring (unzip/extract qiling — fayl ustida o'ng tugma bosib "Extract Here" yoki "Barchasini chiqarish")
3. Natijada `kelajak-bot` nomli papka hosil bo'ladi, ichida `bot.py`, `server.py` va boshqa fayllar turadi

---

## QADAM 4 — Terminal (buyruqlar oynasi) ochish

Terminal — bu kompyuterga matn orqali buyruq beradigan oyna. Qo'rqmang, faqat men aytgan buyruqlarni nusxalab qo'yasiz.

- **Windows**: `kelajak-bot` papkasini oching, papka ichida bo'sh joyga **Shift + o'ng tugma** bosing → "Open PowerShell window here" yoki "Terminal ochish" ni tanlang
- **Mac**: Terminal dasturini oching, so'ng `cd ` deb yozib (oxirida bo'shliq bilan), `kelajak-bot` papkasini terminalga sudrab tashlang, Enter bosing

Terminal ochilgach, papka ichida turganingizga ishonch hosil qiling.

---

## QADAM 5 — Kerakli kutubxonalarni o'rnatish

Terminalga quyidagilarni **birma-bir** yozib, har birida Enter bosing:

```bash
python -m venv venv
```
*(Bu "venv" nomli alohida toza muhit yaratadi — loyihalar bir-biriga aralashib ketmasligi uchun)*

Keyin muhitni yoqing:

- Windows'da:
```bash
venv\Scripts\activate
```
- Mac/Linux'da:
```bash
source venv/bin/activate
```

Muvaffaqiyatli bo'lsa, qator boshida `(venv)` degan yozuv paydo bo'ladi.

Endi kutubxonalarni o'rnating:
```bash
pip install -r requirements.txt
```
Bu 1-2 daqiqa vaqt oladi, kutib turing.

---

## QADAM 6 — Token'ni config.py fayliga yozish

1. VS Code'da (yoki oddiy Notepad'da) `kelajak-bot` papkasi ichidagi `config.py` faylini oching
2. Quyidagi qatorni topasiz:
   ```python
   BOT_TOKEN = "SIZNING_BOT_TOKENINGIZ"
   ```
3. Tirnoqlar ichiga QADAM 1'da olgan tokeningizni qo'ying, masalan:
   ```python
   BOT_TOKEN = "7123456789:AAHf3kL9dQmZ..."
   ```
4. Faylni saqlang (Ctrl+S)

`WEBAPP_URL` qatorini hozircha tegmasdan qoldiring — buni QADAM 9'da to'ldiramiz.

---

## QADAM 7 — Kodni GitHub'ga yuklash

GitHub kerak, chunki Railway xizmati kodingizni aynan shu yerdan oladi.

1. https://github.com saytida ro'yxatdan o'ting (email va parol bilan, bepul)
2. Kirgach, yuqori o'ng burchakdagi **"+"** belgisini bosib, **"New repository"** ni tanlang
3. Repository nomini yozing, masalan: `kelajak-bot`
4. "Public" tanlangan holda qoldiring, "Create repository" tugmasini bosing
5. Ochilgan sahifada GitHub sizga buyruqlar ko'rsatadi. Terminalingizga (hali `kelajak-bot` papkasida turganingizni tekshiring) quyidagilarni ketma-ket yozing:

```bash
git init
git add .
git commit -m "birinchi yuklash"
git branch -M main
git remote add origin https://github.com/FOYDALANUVCHI_NOMINGIZ/kelajak-bot.git
git push -u origin main
```

*(`FOYDALANUVCHI_NOMINGIZ` o'rniga GitHub'dagi haqiqiy username'ingizni yozing — bu manzilni GitHub sahifasidan nusxalab olishingiz mumkin)*

Agar login/parol so'rasa — GitHub username va maxsus "token" so'raydi (parol emas). Agar bu qismda xatolik chiqsa, xatolik matnini menga yuboring, birga hal qilamiz.

---

## QADAM 8 — Railway'da hisob ochish va deploy qilish

1. https://railway.app saytiga kiring
2. "Login" → "Login with GitHub" tanlang, GitHub hisobingiz bilan kiring, ruxsat bering
3. "New Project" tugmasini bosing
4. **"Deploy from GitHub repo"** ni tanlang
5. Ro'yxatdan `kelajak-bot` repongizni tanlang
6. Railway avtomatik loyihani skanerlaydi va deploy qila boshlaydi (1-3 daqiqa)
7. Deploy tugagach, loyiha ustiga bosing → **"Settings"** bo'limiga o'ting
8. **"Start Command"** deb yoziladigan joyni toping, uni tahrirlab shuni yozing:
   ```
   uvicorn server:app --host 0.0.0.0 --port $PORT
   ```
9. Yana **"Settings"** ichida **"Networking"** yoki **"Domains"** bo'limini toping, **"Generate Domain"** tugmasini bosing — sizga shunga o'xshash manzil chiqadi:
   `https://kelajak-bot-production.up.railway.app`
10. Shu manzilni to'liq nusxalab oling

---

## QADAM 9 — WEBAPP_URL'ni to'ldirish

1. Kompyuteringizda `config.py` faylini qayta oching
2. `WEBAPP_URL` qatoriga QADAM 8'da olgan manzilni yozing:
   ```python
   WEBAPP_URL = "https://kelajak-bot-production.up.railway.app"
   ```
3. Saqlang
4. O'zgargan faylni yana GitHub'ga yuboring (terminalda):
   ```bash
   git add .
   git commit -m "webapp url qoshildi"
   git push
   ```
   Railway o'zgarishni ko'rib, avtomatik qayta deploy qiladi (1-2 daqiqa kutib turing)

---

## QADAM 10 — Botni ishga tushirish

Terminalda (hali `(venv)` faol bo'lishi kerak) shuni yozing:

```bash
python bot.py
```

Agar ekranda `"Bot ishga tushdi..."` degan yozuv chiqsa — hammasi ishladi! 🎉

Endi Telegram'da botingizni toping (username orqali qidiring), `/start` yozing. Sizga xush kelibsiz xabari va **"🚀 Platformaga o'tish"** tugmasi chiqadi. Bosganingizda Mini App ochiladi.

> **Diqqat:** Terminalni yopsangiz, bot to'xtaydi. Botni doim ishlab turishi uchun uni ham Railway'ga (2-qadam) alohida deploy qilish kerak bo'ladi — buni keyingi bosqichda birga qilamiz, hozircha kompyuteringizda test qilib ko'ring.

---

## Nimadir ishlamasa nima qilish kerak?

Qaysi QADAM'da va qanday xatolik chiqqanini menga aynan shu matn bilan yuboring (masalan, terminaldagi qizil rangdagi xatolik matnini nusxalab yuboring) — men aynan o'sha joyni tuzataman.
