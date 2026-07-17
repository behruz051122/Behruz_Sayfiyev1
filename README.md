# Kelajak mediklari — Bot + Mini App (boshlang'ich versiya)

Bu loyiha ikki qismdan iborat:
1. **bot.py** — Telegram bot (aiogram). `/start` bosilganda foydalanuvchini bazaga yozadi va Mini App'ni ochuvchi tugma yuboradi.
2. **server.py + webapp/** — Mini App'ning o'zi (FastAPI backend + HTML/CSS/JS frontend). Bu HTTPS orqali ochiladigan veb-sahifa, Telegram uni bot ichida ko'rsatadi.

Ikkalasi ham bitta `database.db` (SQLite) fayl bilan ishlaydi.

---

## 1-BOSQICH — Bot yaratish (BotFather)

1. Telegram'da **@BotFather** ga yozing.
2. `/newbot` buyrug'ini yuboring.
3. Bot uchun ism va username bering (username `bot` bilan tugashi kerak, masalan `kelajak_medik_bot`).
4. BotFather sizga **token** beradi — uni saqlab qo'ying, bu juda muhim va hech kimga bermang.

## 2-BOSQICH — Kompyuterda muhit tayyorlash

```bash
# Python 3.10+ o'rnatilgan bo'lishi kerak
cd kelajak-bot
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 3-BOSQICH — config.py ni to'ldirish

`config.py` faylini oching va:
```python
BOT_TOKEN = "BotFather bergan token"
WEBAPP_URL = "https://sizning-domeningiz.up.railway.app"  # hozircha bo'sh qoldiring, 5-bosqichda to'ldiramiz
```

## 4-BOSQICH — Mini App'ni (server.py) deploy qilish

Mini App HTTPS manzilda joylashgan bo'lishi **shart** (Telegram http'ni qabul qilmaydi). Eng oson bepul yo'l — **Railway.app**:

1. https://railway.app saytida ro'yxatdan o'ting (GitHub akkaunt bilan kirsangiz bo'ladi).
2. Loyihangizni GitHub'ga yuklang (`git init`, `git add .`, `git commit`, GitHub'da repo yaratib push qiling).
3. Railway'da **"New Project" → "Deploy from GitHub repo"** tanlang, repongizni tanlang.
4. Railway avtomatik `requirements.txt`ni ko'radi. **Start Command** qatoriga shuni yozing:
   ```
   uvicorn server:app --host 0.0.0.0 --port $PORT
   ```
5. Deploy tugagach, Railway sizga masalan `https://kelajak-bot-production.up.railway.app` kabi manzil beradi.
6. Shu manzilni nusxalab, `config.py` dagi `WEBAPP_URL` ga qo'ying.

> Muqobil variant: **Render.com** da ham xuddi shunday qilish mumkin (Web Service yarating, Start Command bir xil).

## 5-BOSQICH — Botni ishga tushirish

Kompyuteringizda (yoki alohida boshqa serverda, masalan shu Railway'da ikkinchi service sifatida):
```bash
python bot.py
```
Bot ishga tushgach, Telegram'da botingizga `/start` yozing — sizga "🚀 Platformaga o'tish" tugmasi chiqadi. Bosganingizda Mini App ochiladi.

> **Muhim:** `bot.py` va `server.py` — ikkita alohida jarayon. `bot.py` doim ishlab turishi kerak (kompyuteringiz yoqilganda yoki Railway/VPS'da alohida deploy qilinganda).

## 6-BOSQICH — Bot doim ishlab turishi uchun

Uy kompyuteringizni doim yoqib qo'yish shart emas. `bot.py` ni ham Railway'da **ikkinchi alohida service** sifatida deploy qiling, Start Command:
```
python bot.py
```

## Loyihani kengaytirish (keyingi qadamlar)

- `database.py` ichidagi `courses` jadvaliga haqiqiy kurslaringizni qo'shing (yoki admin panel yozing)
- `webapp/index.html` dagi pastki menyudagi "Kurslar", "Reyting", "Testlar", "Profilim" tugmalariga bosilganda mos sahifalar ko'rsatiladigan JS logikasini qo'shing (hozir faqat "Bosh sahifa" ishlaydi)
- To'lov tizimini ulash uchun Payme/Click API integratsiyasi kerak bo'ladi
- Foydalanuvchi progressini (qaysi darsni tugatgani) saqlash uchun `user_progress` jadvalini qo'shing

## Fayllar tuzilishi

```
kelajak-bot/
├── bot.py              # Telegram bot
├── server.py           # Mini App backend (FastAPI)
├── database.py         # SQLite funksiyalari
├── config.py           # Token va sozlamalar
├── requirements.txt    # Kutubxonalar
└── webapp/
    ├── index.html       # Mini App sahifasi
    ├── style.css        # Dizayn
    └── app.js           # Mini App logikasi
```
