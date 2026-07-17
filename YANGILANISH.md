# YANGILANISH — nima o'zgardi va qanday joylash kerak

## Nima qo'shildi

1. **Brend nomi** — endi "Kelajak mediklari" o'rniga "Behruz Sayfiyev" chiqadi
2. **Premium dizayn** — qora fon, oltin (gold) va binafsha ranglar bilan yangi ko'rinish
3. **Kitoblar bo'limi** — kurslardan alohida, o'zingiz yechgan masalalar to'plamlarini shu yerga joylaysiz
4. **Referal tizimi** — har bir foydalanuvchi o'zining shaxsiy havolasiga ega. Do'stlari shu havola orqali botga kirib, kanalingizga obuna bo'lsa — bu tasdiqlangan taklif sifatida hisoblanadi
5. **Har bir kurs uchun alohida talab** — masalan "Mavzulashtirilgan masala kursi" uchun 1 ta taklif, "Super nazariya" uchun 2 ta taklif kerak bo'lishi mumkin — buni admin panelda o'zingiz belgilaysiz
6. **Majburiy obuna** — bot foydalanuvchidan avval kanalingizga obuna bo'lishni so'raydi
7. **Admin panel** (`/admin.html` manzilida) — parol bilan himoyalangan, shu yerdan:
   - Cheksiz miqdorda kurs/kitob qo'shish
   - Har bir kursga cheksiz video dars qo'shish
   - Darslarni tahrirlash, o'chirish, tartibini o'zgartirish
   - Kursni bepul yoki referal-orqali qilib belgilash

---

## MUHIM — Joylashtirishdan oldin sozlang

`config.py` faylini oching va quyidagilarni albatta to'ldiring:

```python
CHANNEL_USERNAME = "@sizning_kanalingiz"      # kanalingiz username'i
CHANNEL_URL = "https://t.me/sizning_kanalingiz"  # kanalingiz havolasi
ADMIN_PASSWORD = "behruz2026admin"             # buni albatta o'zingizga xos parolga almashtiring!
```

**JUDA MUHIM:** Bot kanalingizda **admin** bo'lishi shart, aks holda u foydalanuvchilarning obuna bo'lgan-bo'lmaganini tekshira olmaydi.
- Kanalingizga o'ting → Administratorlar → Admin qo'shish → botingizni qidiring → admin qiling

---

## Joylashtirish bosqichlari

Fayllarni eski loyihangizdagi papkaga ustiga qo'ying (ya'ni eski `database.py`, `bot.py`, `server.py`, `webapp` papkasini shular bilan almashtiring), so'ng:

### 1. config.py ni to'ldiring (yuqoridagi 3 qatorni)

### 2. Terminalda ("YANGI BOT" papkasida):
```
git add .
git commit -m "yangi dizayn va referal tizimi"
git push
```
Railway avtomatik qayta deploy qiladi (1-2 daqiqa).

### 3. Botni qayta ishga tushiring:
Bot terminalida `Ctrl+C`, keyin:
```
python bot.py
```

### 4. Admin panelga kiring:
Brauzerda Railway domeningizga `/admin.html` qo'shib oching, masalan:
```
https://behruzsayfiyev1-production-4a0a.up.railway.app/admin.html
```
`config.py`dagi parolni kiriting.

### 5. Kurslaringizni qo'shing:
- "+ Yangi qo'shish" tugmasi bilan har bir kurs/kitobni kiriting
- "Nechta taklif kerak" maydoniga shu kurs uchun zarur referal sonini yozing (bepul bo'lsa 0 qoldiring va "Bepul" tanlang)
- Kursni saqlagandan keyin "Darslar" tugmasini bosib, video darslarni birma-bir qo'shing (YouTube havolasi eng oson variant)

---

## Referal tizimi qanday ishlaydi

1. Foydalanuvchi Mini App'dagi "Do'st taklif qiling" bo'limidan o'zining shaxsiy havolasini oladi
2. Bu havolani do'stiga yuboradi: `https://t.me/BOTINGIZ?start=ref_123456789`
3. Do'sti shu havola orqali botga kirsa, bot avtomatik uni "taklif qilingan" deb yozib qo'yadi
4. Agar u kanalingizga hali obuna bo'lmagan bo'lsa, bot undan obuna bo'lishni so'raydi
5. Obuna bo'lgach (yoki "✅ Men obuna bo'ldim" tugmasini bosgach), taklif **tasdiqlangan** hisoblanadi
6. Taklif qilgan foydalanuvchiga avtomatik xabar boradi, va Mini App'da tegishli kurslar ochiladi

---

## Eslatma

Bot hozircha faqat kompyuteringiz yoqilganda ishlaydi (`python bot.py` orqali). Uni doim ishlab turishi uchun, xohlasangiz, keyingi bosqichda `bot.py`ni ham Railway'ga alohida servis sifatida deploy qilib beraman — shunda kompyuteringiz o'chiq bo'lsa ham bot ishlab turadi.
