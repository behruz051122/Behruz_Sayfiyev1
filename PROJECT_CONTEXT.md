# PROJECT_CONTEXT.md

> **Behruz Sayfiyev — Onlayn ta'lim platformasi**
> Telegram bot + Telegram Mini App (FastAPI + SQLite + aiogram 3)
>
> Bu fayl loyihaning to'liq texnik xaritasi. Yangi ishni boshlashdan oldin
> shu faylni o'qish kifoya — qaysi fayl nima qilishi, ma'lumotlar bazasi
> qanday tuzilgani, qaysi API qaysi ekranga xizmat qilishi shu yerda.
>
> Oxirgi tahlil: `1797cb7` commit asosida.

---

## Mundarija

1. [Loyiha tuzilishi](#1-loyiha-tuzilishi)
2. [Texnik stack](#2-texnik-stack)
3. [Ma'lumotlar bazasi sxemasi](#3-malumotlar-bazasi-sxemasi)
4. [API endpointlar](#4-api-endpointlar)
5. [Mini App sahifalari va backend bog'lanishi](#5-mini-app-sahifalari-va-backend-boglanishi)
6. [Gamifikatsiya tizimi](#6-gamifikatsiya-tizimi)
7. [Deploy jarayoni](#7-deploy-jarayoni)
8. [Ma'lum muammolar va tugallanmagan qismlar](#8-malum-muammolar-va-tugallanmagan-qismlar)

---

## 1. Loyiha tuzilishi

### Papka daraxti

```
Behruz_Sayfiyev1/
│
├── server.py                  # ⭐ KIRISH NUQTASI — FastAPI app, middleware, routerlar, startup
├── bot.py                     # Telegram bot (aiogram) + 7 ta fon vazifasi (background loop)
├── database.py                # ⚠️ 7688 qator — 60 jadval + barcha SQL funksiyalari
├── db_pool.py                 # SQLite ulanishlar puli (8 ta ulanish, WAL rejimi)
├── config.py                  # .env dan sozlamalarni o'qish, majburiy qiymatlarni tekshirish
├── auth.py                    # Telegram initData HMAC tekshiruvi, admin JWT, bcrypt
├── access_control.py          # Telegram guruh a'zoligini Bot API orqali tekshirish
├── rate_limit.py              # Umumiy slowapi Limiter obyekti
├── certificate_pdf.py         # Sertifikat PDF generatsiyasi (reportlab)
├── docx_import.py             # Word (.docx) fayldan savollarni ommaviy import qilish
├── photo_urls.py              # Vazifa rasmlari URL'ini bezash (file_id -> proxy URL)
├── generate_password_hash.py  # Admin paroli uchun bcrypt hash yasovchi yordamchi skript
│
├── chem_questions.py          # Kimyo o'yini savol generatorlari (6 xil savol turi)
├── chem_seed_data.py          # Kimyo boshlang'ich kontenti (moddalar, cho'kmalar, ranglar)
├── bio_questions.py           # Biologiya o'yini savol generatorlari (5 xil savol turi)
├── bio_seed_data.py           # Biologiya boshlang'ich kontenti (hujayra, genetika, ...)
│
├── routers/                   # 🔷 API endpointlari — mavzular bo'yicha 36 ta fayl
│   ├── deps.py                #    Umumiy auth dependency'lari (foydalanuvchi / admin)
│   │
│   │   ── FOYDALANUVCHI ──
│   ├── user.py                #    /api/user, /api/is-admin, /api/leaderboard, /api/achievements
│   ├── dashboard.py           #    /api/dashboard-cards (bosh sahifa kartalari)
│   ├── brand.py               #    /api/brand (brend nomi, kanal havolasi)
│   ├── courses.py             #    Kurslar, darslar, dars ko'rish belgisi
│   ├── tests.py               #    Testlar, savollar, attempt (topshirish jarayoni)
│   ├── control_tests.py       #    Nazorat testlari + oylik reyting
│   ├── simulators.py          #    DTM/blok test simulyatori
│   ├── certificates.py        #    Kurs sertifikatlari (status, PDF yuklab olish)
│   ├── homework.py            #    Uy vazifasi (rasm yuklash, topshirish)
│   ├── bookshop.py            #    Bosma kitoblar do'koni
│   ├── student_results.py     #    O'quvchilar natijalari / fikrlari
│   ├── faq.py                 #    Yordam / savol-javob
│   │
│   │   ── O'YINLAR ──
│   ├── games.py               #    ⚠️ Universal 1x1 Battle (frontendga ULANMAGAN — 8-bo'limga qarang)
│   ├── chem_game.py           #    Kimyo: kategoriya -> level -> bosqichlar
│   ├── chem_battle.py         #    Kimyo 1x1 jang (ELO, kod bilan taklif)
│   ├── chem_tournament.py     #    Kimyo chempionati (saralash -> setka -> final)
│   ├── bio_game.py            #    Biologiya: mavzu -> level -> 7 xil o'yin turi
│   │
│   │   ── ADMIN ──
│   ├── admin_auth.py          #    Parol bilan login (JWT) — rate-limit: 5/15daq
│   ├── admin_courses.py       #    Kurslar, kategoriyalar, paragraf, dars, narx paketlari
│   ├── admin_tests.py         #    Testlar, fan kartalari, bosqich, guruh, savollar, e'tirozlar
│   ├── admin_control_tests.py #    Nazorat testiga talaba tayinlash, natijalar
│   ├── admin_simulators.py    #    Simulyator va uning fanlari
│   ├── admin_homework.py      #    Vazifa fanlari, baholash, kechikkanlar, xotira tozalash
│   ├── admin_chem.py          #    Kimyo kontenti + chempionatlar
│   ├── admin_bio.py           #    Biologiya kontenti
│   ├── admin_access.py        #    Telegram guruhlari orqali kirish nazorati
│   ├── admin_analytics.py     #    Umumiy statistika
│   ├── admin_dashboard.py     #    Bosh sahifa kartalarini tahrirlash
│   ├── admin_bookshop.py      #    Kitob mahsulotlari
│   ├── admin_faq.py           #    FAQ boshqaruvi
│   ├── admin_student_results.py #  Natijalar/fikrlar boshqaruvi
│   ├── admin_docx_import.py   #    .docx dan savol import
│   ├── uploads.py             #    Rasm yuklash (admin + o'quvchi yozma javobi)
│   └── diagnostics.py         #    /api/debug/db-info — baza holati diagnostikasi
│
├── webapp/                    # 🔷 Mini App frontend (StaticFiles orqali "/" ga mount qilinadi)
│   ├── index.html             #    1907 qator — barcha ekranlar bitta faylda (SPA)
│   ├── style.css              #    153 KB
│   ├── savol-shabloni.docx    #    Admin uchun .docx import shabloni
│   ├── logo*.svg / .png       #    Brend belgilari
│   └── js/                    #    ES modullar (import/export)
│       ├── main.js            #      Kirish nuqtasi, navigatsiya markazi (handleNav)
│       ├── navigate.js        #      Ekran almashish + CustomEvent orqali bog'lanish
│       ├── api.js             #      apiFetch/publicFetch, Telegram SDK, mavzu (dark/light)
│       ├── components.js      #      Umumiy UI bo'laklari (lightbox, bo'sh holat)
│       ├── user.js            #      Brend, foydalanuvchi, admin tekshiruvi
│       ├── home.js            #      Bosh sahifa 6-7 kartali grid
│       ├── courses.js         #      Kurslar oqimi (fan -> ro'yxat -> kurs -> paragraf -> dars)
│       ├── tests.js           #      70 KB — testlar, simulyator, nazorat testi, sertifikat
│       ├── chemGame.js        #      58 KB — kimyo o'yini + battle + chempionat
│       ├── bioGame.js         #      34 KB — biologiya o'yini
│       ├── homework.js        #      Vazifa topshirish
│       ├── leaderboard.js     #      Reyting (davr bo'yicha + nazorat testi oylik)
│       ├── profile.js         #      Profil, nishonlar, sertifikatlar, obunalar
│       ├── bookshop.js        #      Kitoblar do'koni
│       ├── studentResults.js  #      Natijalar bo'limi
│       ├── referral.js        #      Referal havolasi
│       ├── faq.js             #      Yordam bo'limi
│       ├── admin.js           #      127 KB — asosiy admin panel
│       ├── adminChem.js       #      Kimyo admin
│       ├── adminBio.js        #      Biologiya admin
│       └── adminAccess.js     #      Guruh orqali kirish admin
│
├── brend/                     # Brend materiallari (logotip, avatar, lockup — SVG/PNG)
│   └── README.md              #   Brend qo'llanmasi
│
├── .env.example               # Muhit o'zgaruvchilari namunasi (qiymatlarsiz)
├── .gitignore                 # .env, database.db, venv, __pycache__
├── requirements.txt           # 10 ta bog'liqlik
│
├── README.md                  # ⚠️ ESKIRGAN — "Kelajak mediklari" boshlang'ich qo'llanmasi
├── BATAFSIL_QOLLANMA.md       # Batafsil foydalanish qo'llanmasi
├── BIOLOGIYA_QOLLANMA.md      # Biologiya o'yini qo'llanmasi
├── OYINLAR_QOLLANMA.md        # O'yinlar qo'llanmasi
├── OYINLAR_TAHLIL.md          # O'yinlar dizayn tahlili
├── PULLIK_GURUH_QOLLANMA.md   # Guruh orqali kirish qo'llanmasi
├── NAZORAT_TESTI_TALABALAR.md # Nazorat testi qo'llanmasi
├── XAVFSIZLIK_YANGILANISHI.md # Xavfsizlik o'zgarishlari tarixi
├── QOLLANMA_v5_1.md           # v5.1 yangiliklari
├── YANGILANISH.md             # Yangilanishlar tarixi
│
└── ⚠️ ESKI / KERAKSIZ FAYLLAR (8-bo'limga qarang)
    ├── index.html             # webapp/index.html dan oldingi versiya (285 qator, o'lik)
    ├── app.js                 # webapp/js/ ga bo'linishdan oldingi monolit (36 KB, o'lik)
    ├── style.css              # webapp/style.css ning eski nusxasi (16 KB, o'lik)
    ├── kelajak-bot.zip        # 34 KB arxiv qoldig'i
    ├── database.db            # 86 KB — .gitignore da bor, lekin git'da kuzatilmoqda
    └── 39-NAZORAT (toza).docx # Test import namunasi
```

### Muhim arxitektura qarori: bot va API bitta jarayonda

`server.py` startup hodisasida Telegram bot polling **fon vazifasi** sifatida ishga
tushadi (`asyncio.create_task`). Shu sababli:

- Railway'da **alohida "bot" xizmati kerak emas** — bitta deploy yetarli
- Bot va API **bitta SQLite fayl** bilan ishlaydi (ikkita jarayon o'rtasida
  lock muammosi yo'q)
- `README.md` dagi "bot.py ni ikkinchi service qilib deploy qiling" ko'rsatmasi
  endi **eskirgan**

`server.py` da ishga tushadigan 7 ta fon halqasi:

| Halqa | Vazifasi |
|---|---|
| `start_polling_background()` | Telegram bot polling |
| `send_expiry_reminders_loop()` | Obuna muddati tugayotganlarga eslatma |
| `send_battle_result_notifications_loop()` | Battle natijasi haqida xabar |
| `send_homework_reminders_loop()` | Vazifani kechiktirganlarga eslatma |
| `cleanup_old_homework_photos_loop()` | Eski vazifa rasmlarini o'chirish |
| `chem_battle_maintenance_loop()` | Kutayotgan kimyo janglarini bot bilan yakunlash |
| `membership_refresh_loop()` | Guruh a'zoligini fon rejimida yangilash |

### `server.py` ning butun vazifasi

Bu faylda **hech qanday endpoint mantiqi yo'q**. U faqat:

1. `FastAPI()` yaratadi, `slowapi` rate-limit va CORS middleware'ini ulaydi
2. `startup` da: `db.init_db()` → `db.add_sample_courses()` → `_check_db_persistence()` → 7 ta fon vazifasi
3. 36 ta routerni `include_router()` qiladi
4. `/uploads` va `/` (webapp) statik papkalarini mount qiladi

> **Mount tartibi muhim:** `webapp` **eng oxirida** mount qilinadi, aks holda
> `StaticFiles(html=True)` barcha `/api/*` so'rovlarini ushlab qolgan bo'lardi.

### `_check_db_persistence()` — nima uchun kerak

Server ishga tushganda `DB_PATH` doimiy xotira yo'liga (`/data`, `/mnt`, `/vol`)
o'xshashini tekshiradi. O'xshamasa — Deploy Logs'ga katta ogohlantirish chiqaradi.
Sababi: noto'g'ri `DB_PATH` bilan ilova **xatosiz** ishga tushadi, lekin har
deploy'da barcha ma'lumotlar jimgina o'chib ketadi.

---

## 2. Texnik stack

### Backend

| Komponent | Tanlov | Izoh |
|---|---|---|
| Til | Python 3.10+ | |
| Web framework | **FastAPI 0.115.0** | Routerlarga bo'lingan, dependency injection |
| ASGI server | **uvicorn 0.30.6** | |
| Ma'lumotlar bazasi | **SQLite** | WAL rejimi, 8 ta ulanishli pul |
| Telegram bot | **aiogram 3.13.1** | Server bilan bitta jarayonda |
| Autentifikatsiya | **PyJWT 2.9.0** + **bcrypt 4.2.0** | Admin sessiyalari |
| Rate limiting | **slowapi 0.1.9** | IP bo'yicha |
| Fayl yuklash | **python-multipart 0.0.9** | |
| Word import | **python-docx 1.1.2** | Savollarni .docx dan import |
| PDF | **reportlab 4.2.5** | Sertifikatlar |
| Konfiguratsiya | **python-dotenv 1.0.1** | `.env` fayli |

### Frontend

| Komponent | Tanlov |
|---|---|
| Framework | **Yo'q** — vanilla JS (ES modullar) |
| Build tool | **Yo'q** — brauzer to'g'ridan-to'g'ri `<script type="module">` yuklaydi |
| CSS | Bitta `style.css` (153 KB), CSS o'zgaruvchilari orqali dark/light mavzu |
| Telegram SDK | `telegram-web-app.js` (CDN) |
| Ekranlar | Bitta `index.html` ichida `<section class="screen">` — SPA uslubi |

Frontend'da build bosqichi yo'qligi ataylab: Railway'da faqat `requirements.txt`
o'rnatiladi, `npm` umuman ishlatilmaydi.

### Xavfsizlik yondashuvi

| Qatlam | Mexanizm |
|---|---|
| Foydalanuvchi identifikatsiyasi | Telegram `initData` HMAC-SHA256 imzosi (`auth.py`) — frontenddan kelgan `telegram_id` ga **hech qachon ishonilmaydi** |
| Admin (1-usul) | Parol → bcrypt tekshiruvi → JWT sessiya tokeni |
| Admin (2-usul) | Tasdiqlangan `telegram_id` `ADMIN_TELEGRAM_IDS` ro'yxatida bo'lsa |
| Sirlar | `.env` faylida, `.gitignore` da |
| Brute-force | `/api/admin/login` → 5 urinish / 15 daqiqa |
| Kontentga kirish | Telegram yopiq guruh a'zoligi (`access_control.py`) yoki `enrollments` jadvali |

### Ulanishlar puli (`db_pool.py`)

```
POOL_SIZE = 8
PRAGMA foreign_keys = ON
PRAGMA journal_mode = WAL      # o'qish va yozish bir-biriga xalaqit bermaydi
PRAGMA busy_timeout = 5000     # baza band bo'lsa 5s kutadi, xato bermaydi
```

`database.py` dagi har bir funksiya `with get_connection() as conn:` orqali
puldan ulanish oladi va `finally` orqali avtomatik qaytaradi.

---

## 3. Ma'lumotlar bazasi sxemasi

**60 ta jadval**, hammasi `database.py:init_db()` ichida (1–1737 qator) yaratiladi.

### Migratsiya usuli

Yangi ustunlar `try: ALTER TABLE ... except sqlite3.OperationalError: pass`
naqshi orqali qo'shiladi. Ya'ni **migratsiya fayllari yo'q**, versiya raqami
yo'q — har ishga tushishda barcha ALTER'lar qayta urinib ko'riladi.

> ⚠️ Quyidagi ustun ro'yxatlari faqat `CREATE TABLE` dagi asosiy ustunlarni
> ko'rsatadi. Ko'p jadvallarda ALTER orqali qo'shilgan qo'shimcha ustunlar bor
> (masalan `tests` da `is_control_test`, `course_id`, `test_kind`,
> `test_group_id`; `courses` da `course_type`, `lessons_count_override`).

### 3.1. Foydalanuvchilar va gamifikatsiya

```
users (id, telegram_id UNIQUE, first_name, username, points, coins,
       referred_by, is_subscribed, created_at,
       + ALTER: current_streak, longest_streak, last_activity_date)
   │
   ├─< coin_history (id, telegram_id, amount, created_at)     ← davr bo'yicha reyting uchun
   ├─< user_achievements (id, telegram_id, achievement_key, earned_at)
   ├─< referrals (id, referrer_telegram_id, referred_telegram_id, confirmed, created_at)
   └─< certificates (id, telegram_id, course_id, certificate_number, issued_at)
```

`coin_history` alohida jadval bo'lishining sababi: `users.coins` faqat umumiy
yig'indini biladi, **qachon** berilganini bilmaydi. Haftalik/oylik reyting
uchun vaqt kerak.

### 3.2. Kurslar

```
course_categories ──< course_category_links >── courses
                                                   │
                              ┌────────────────────┼────────────────────┐
                              │                    │                    │
                    course_pricing_tiers      paragraphs           enrollments
                                                   │              (telegram_id, course_id,
                                                lessons            expiry_date,
                                                   │               + reminder_sent_at)
                                            lesson_progress
                                       (telegram_id, lesson_id, coin_awarded)
```

- `courses.resource_type` — `'course'` yoki `'book'` (raqamli kitob)
- `courses.course_type` — `'nazoratli'` yoki `'mustaqil'`
- `lessons.is_free_preview` — pulli kursda bepul ko'riladigan dars

### 3.3. Testlar — 4 bosqichli iyerarxiya

```
test_subject_cards  (fan kartasi: Kimyo, Biologiya, ...)
        │
     test_stages    (bosqich: Boshlang'ich, O'rta, Yuqori)
        │
     test_groups    (turkum: mavzu bo'yicha)
        │
      tests         (bitta test)
        │
   test_questions   (savol: 4 variant + image_url + table_data)
```

Topshirish oqimi:

```
test_attempts (telegram_id, test_id, score, total_questions, started_at, finished_at)
     │
     ├─< test_answers (attempt_id, question_id, selected_index, is_correct, + is_flagged)
     ├─< certificate_written_answers   ← Milliy sertifikat O2 (yozma ish, qo'lda baholanadi)
     └─< question_objections           ← o'quvchi savolga e'tiroz bildiradi

user_question_progress (telegram_id, question_id, coin_awarded)
     └── bir savol uchun coin FAQAT BIR MARTA beriladi
```

Nazorat testlari uchun qo'shimcha:

```
control_test_access        (test_id, telegram_id)   ← qo'lda tayinlash
control_test_course_links  (test_id, course_id)     ← kursga a'zolar avtomatik ko'radi
```

### 3.4. Simulyator (DTM / blok test)

```
simulators ──< simulator_subjects (simulator_id, subject, question_count)
     │
simulator_attempts ──< simulator_attempt_questions (attempt_id, question_id, subject)
                   └─< simulator_answers (attempt_id, question_id, selected_index, is_correct)
```

Simulyator **o'z savol bankiga ega emas** — `test_questions` dan fan bo'yicha
tasodifiy tanlab oladi.

### 3.5. Uy vazifasi

```
homework_subjects ──< homework_subject_courses (subject_id, course_id)  ← kimga ochiq
        │
homework_submissions (subject_id, telegram_id, paragraph_number, status,
                      teacher_score, teacher_comment, graded_by, graded_at)
        │
   homework_photos (submission_id, photo_url, order_num)

homework_student_start (subject_id, telegram_id, start_paragraph)
        └── har bir o'quvchi qaysi paragrafdan boshlashi
```

Paragraflar **ketma-ket ochiladi** — oldingisi topshirilmaguncha keyingisi yopiq.

### 3.6. O'yinlar

**Universal Battle** (⚠️ frontendga ulanmagan):
```
game_battles   (subject, question_ids, player1_*, player2_*, status, winner, elo_before/after)
game_ratings   (telegram_id, subject, elo, wins, losses, draws)
```

**Kimyo:**
```
chem_categories ──< chem_levels ──< chem_substances
                         │              (formula, name, historic_name,
                    chem_stage_progress   color_pure/solution/precipitate,
                    (telegram_id,          reactions, usage_text)
                     level_id, stage, stars)

chem_ratings   (telegram_id, elo, wins, losses, draws, current_streak, best_streak)
chem_battles   (category_id, mode, invite_code, questions, p1_*, p2_*, is_bot, bot_elo, ...)
chem_tournaments ──< chem_tournament_players (qual_score, seed, eliminated_round, place)
                 └─< chem_tournament_matches (round_no, slot, kind, p1/p2, winner)
```

**Biologiya:**
```
bio_topics ──< bio_levels ──┬─< bio_terms       (term, definition, function_text,
                            │                     group_name, clues, extra_fact)
                            ├─< bio_sequences   (title, steps)
                            └─< bio_image_tasks (image_url, labels)
                                    │
                            bio_stage_progress (telegram_id, level_id, stage_key, stars)
```

Biologiya `stage_key` **matn** (kimyoda `stage` — raqam), chunki har bir level
uchun mavjud bosqichlar to'plami kontentga qarab o'zgaradi
(`bio_available_stages()`).

### 3.7. Kirish nazorati (Telegram guruhlari orqali)

```
access_groups (title, chat_id, invite_link, is_active, last_error)
        │
content_access_links (content_type, content_id, group_id)
        └── content_type: 'course' | 'test' | 'homework' | ...

group_membership_cache (telegram_id, group_id, is_member, status, checked_at)
        └── Bot API chaqiruvini kamaytirish uchun kesh
```

Mantiq: o'quvchi pullik Telegram guruhiga qo'shilsa — bog'langan kontentga
**avtomatik** kirish ochiladi. Qo'lda `enrollment` berish shart emas.

### 3.8. Kontent va sozlamalar

```
dashboard_cards  (card_key PK, title, subtitle, icon, is_active, order_num)
book_products    (title, category, price, image_url, badge_text, is_bundle, contact_username)
faq_items        (question, answer, order_num, is_active)
student_results  (student_name, subject, image_url, result_text, feedback_text)
app_settings     (key PK, value, updated_at)
```

### ⚠️ FOREIGN KEY haqida muhim eslatma

`PRAGMA foreign_keys = ON` yoqilgan, lekin **atigi ~24 ta FK e'lon qilingan** —
asosan kurs iyerarxiyasi va test iyerarxiyasi ichida. `telegram_id` bo'yicha
bog'lanishlarning **hech biri** FK emas (`users` jadvaliga FK yo'q). Ya'ni
o'chirilgan foydalanuvchining `lesson_progress`, `test_attempts`,
`chem_ratings` yozuvlari baza darajasida avtomatik tozalanmaydi.

---

## 4. API endpointlar

**Jami: 194 ta endpoint** (36 ta routerda).

Barcha yo'llar `/api` bilan boshlanadi. Autentifikatsiya:
- 🔓 **Ochiq** — hech qanday header kerak emas
- 🔑 **Foydalanuvchi** — `X-Telegram-Init-Data` header (`get_verified_telegram_user`)
- 🛡️ **Admin** — `Authorization: Bearer <JWT>` yoki whitelist'dagi initData (`require_admin`)

### 4.1. Foydalanuvchi va bosh sahifa

| Method | Endpoint | Auth | Vazifasi |
|---|---|---|---|
| GET | `/api/brand` | 🔓 | Brend nomi, kanal havolasi, admin kontakti |
| GET | `/api/dashboard-cards` | 🔓 | Bosh sahifa kartalari (admin tahrirlaydi) |
| GET | `/api/user` | 🔑 | Profil: coin, streak, reyting o'rni |
| GET | `/api/is-admin` | 🔑 | Admin bo'limi ko'rinsinmi |
| GET | `/api/referral-link` | 🔑 | Shaxsiy referal havolasi + progress |
| GET | `/api/leaderboard` | 🔑 | Umumiy reyting (`?period=all\|week\|month`) |
| GET | `/api/my-enrollments` | 🔑 | Faol obunalar |
| GET | `/api/achievements` | 🔑 | 14 ta nishon + qo'lga kiritilgani |

### 4.2. Kurslar

| Method | Endpoint | Auth | Vazifasi |
|---|---|---|---|
| GET | `/api/course-categories` | 🔑 | Kurs bo'limlari |
| GET | `/api/courses` | 🔑 | Kurslar ro'yxati (`?resource_type=course\|book`) |
| GET | `/api/course/{id}` | 🔑 | Kurs tafsiloti + paragraflar + kirish holati |
| POST | `/api/lesson/{id}/watched` | 🔑 | Darsni ko'rilgan deb belgilash (**+1 coin**) |
| POST | `/api/access/refresh` | 🔑 | Guruh a'zoligini majburan qayta tekshirish |

### 4.3. Testlar

| Method | Endpoint | Auth | Vazifasi |
|---|---|---|---|
| GET | `/api/test-subject-cards` | 🔑 | Fan kartalari |
| GET | `/api/test-subject-cards/{id}/stages` | 🔑 | Bosqichlar + ochilish holati |
| GET | `/api/test-stages/{id}/groups` | 🔑 | Turkumlar + progress |
| GET | `/api/tests` | 🔑 | Testlar (`?group_id=`) |
| GET | `/api/attestation-tests` | 🔑 | Attestatsiya testlari |
| GET | `/api/certificate-tests` | 🔑 | Milliy sertifikat testlari |
| GET | `/api/test/{id}` | 🔑 | Test savollari (javoblarsiz) |
| POST | `/api/test/{id}/start` | 🔑 | Urinish (attempt) boshlash |
| POST | `/api/attempt/{id}/answer` | 🔑 | Javob yuborish (**birinchi to'g'ri javob → +1 coin**) |
| POST | `/api/attempt/{id}/finish` | 🔑 | Testni yakunlash, natija hisoblash |
| GET | `/api/attempt/{id}/grid` | 🔑 | Javoblar jadvali (to'g'ri/xato) |
| POST | `/api/attempt/{id}/flag` | 🔑 | Savolni "keyinroq qaytaman" deb belgilash |
| POST | `/api/attempt/{id}/objection` | 🔑 | Savolga e'tiroz bildirish |
| GET | `/api/attempt/{id}/rank` | 🔑 | Shu test bo'yicha o'rin |
| POST | `/api/attempt/{id}/written-answer` | 🔑 | Milliy sertifikat O2 — yozma ish rasmi |
| GET | `/api/attempt/{id}/written-answers` | 🔑 | Yozma javoblar + o'qituvchi bahosi |
| GET | `/api/my-test-results` | 🔑 | Barcha test natijalari |
| POST | `/api/upload-answer-image` | 🔑 | Yozma javob rasmini yuklash |

### 4.4. Nazorat testlari va simulyator

| Method | Endpoint | Auth | Vazifasi |
|---|---|---|---|
| GET | `/api/control-tests` | 🔑 | Menga ochiq nazorat testlari |
| GET | `/api/control-test-leaderboard` | 🔑 | Oylik nazorat reytingi |
| GET | `/api/simulators` | 🔑 | Simulyatorlar ro'yxati |
| POST | `/api/simulator/{id}/start` | 🔑 | Simulyator urinishi (savollar tasodifiy tanlanadi) |
| GET | `/api/simulator/attempt/{id}/questions` | 🔑 | Urinish savollari |
| POST | `/api/simulator/attempt/{id}/answer` | 🔑 | Javob (**+1 coin**) |
| POST | `/api/simulator/attempt/{id}/finish` | 🔑 | Yakunlash |
| GET | `/api/simulator/attempt/{id}/grid` | 🔑 | Javoblar jadvali |
| GET | `/api/my-simulator-results` | 🔑 | Natijalar |
| GET | `/api/my-progress-history` | 🔑 | Progress grafigi (oxirgi 30 urinish) |

### 4.5. Sertifikatlar, kitoblar, natijalar, FAQ

| Method | Endpoint | Auth | Vazifasi |
|---|---|---|---|
| GET | `/api/course/{id}/certificate/status` | 🔑 | Sertifikat berilishi mumkinmi |
| GET | `/api/course/{id}/certificate/download` | 🔑 | Sertifikat PDF (reportlab) |
| GET | `/api/my-certificates` | 🔑 | Olingan sertifikatlar |
| GET | `/api/book-products` | 🔑 | Bosma kitoblar do'koni |
| GET | `/api/student-results` | 🔑 | O'quvchilar natijalari / fikrlari |
| GET | `/api/faq` | 🔑 | Savol-javob |

### 4.6. Uy vazifasi

| Method | Endpoint | Auth | Vazifasi |
|---|---|---|---|
| GET | `/api/homework/subjects` | 🔑 | Vazifa fanlari (kirish huquqi bilan) |
| GET | `/api/homework/subjects/{id}/paragraphs` | 🔑 | Paragraflar + qulf holati |
| GET | `/api/homework/subjects/{id}/paragraphs/{n}` | 🔑 | Bitta paragraf tafsiloti |
| POST | `/api/homework/subjects/{id}/paragraphs/{n}/photo` | 🔑 | Rasm yuklash |
| POST | `/api/homework/subjects/{id}/paragraphs/{n}/submit` | 🔑 | Topshirish (keyingisi ochiladi) |
| DELETE | `/api/homework/photos/{id}` | 🔑 | Rasmni o'chirish |
| GET | `/api/homework/photo/{id}` | 🔑 | Rasm proxy (Telegram `file_id` orqali) |
| GET | `/api/homework/my-summary` | 🔑 | Umumiy natija |

### 4.7. O'yinlar

**Universal Battle** (`/api/games/*`) — ⚠️ frontendga ulanmagan:
`GET /subjects`, `POST /battle/join`, `POST /battle/{id}/submit`,
`GET /battle/{id}`, `GET /my-battles`, `GET /leaderboard/{subject}`

**Kimyo o'yini** (`/api/chem/*`):

| Method | Endpoint | Vazifasi |
|---|---|---|
| GET | `/hub` | Kimyo markazi (rating, missiya, kategoriyalar) |
| GET | `/category/{id}/path` | Levellar yo'lagi + yulduzlar |
| GET | `/level/{id}` | Level tafsiloti + bosqichlar |
| GET | `/level/{id}/stage/{n}` | Bosqich kontenti (kartalar / savollar) |
| POST | `/level/{id}/stage/{n}/check` | Yozma javobni tekshirish (4-bosqich) |
| POST | `/level/{id}/stage/{n}/submit` | Natija (**yulduz + coin**) |
| GET | `/dictionary` | Moddalar lug'ati (qidiruv) |
| GET | `/substance/{id}` | Modda kartochkasi |

**Kimyo Battle** (`/api/chem/battle/*`):
`POST /start`, `POST /invite`, `POST /join-code`, `GET /{id}/question`,
`POST /{id}/answer`, `POST /{id}/finish`, `GET /{id}/status`,
`GET /me/rating`, `GET /me/history`, `GET /leaderboard`

**Kimyo chempionati** (`/api/chem/tournament/*`):
`GET /list`, `POST /create`, `POST /{id}/join`, `GET /{id}`,
`GET|POST /{id}/qual/*` (saralash), `GET|POST /match/{id}/*` (setka o'yinlari)

**Biologiya o'yini** (`/api/bio/*`):
`GET /hub`, `GET /topic/{id}/path`, `GET /level/{id}`,
`GET /level/{id}/stage/{key}`, `POST /level/{id}/check/{sequence|group|whoami|image}`,
`POST /level/{id}/stage/{key}/submit`, `GET /dictionary`, `GET /term/{id}`

### 4.8. Admin endpointlari (🛡️)

| Router | Prefiks | Nima boshqaradi |
|---|---|---|
| `admin_auth` | `/api/admin/login` | Parol → JWT (rate-limit 5/15daq) |
| `admin_courses` | `/api/admin/...` | Kurs, kategoriya, narx paketi, paragraf, dars, qo'lda enroll |
| `admin_tests` | `/api/admin/...` | Test, fan kartasi, bosqich, guruh, savol, yozma ish baholash, e'tirozlar |
| `admin_control_tests` | `/api/admin/control-tests/...` | Talaba tayinlash, kurs bog'lash, natijalar |
| `admin_simulators` | `/api/admin/simulators` | Simulyator va fanlari |
| `admin_homework` | `/api/admin/homework/...` | Fan, baholash, kechikkanlar, eslatma, xotira, reyting |
| `admin_chem` | `/api/admin/chem/...` | Kategoriya, level, modda, ommaviy qo'shish, seed, chempionat |
| `admin_bio` | `/api/admin/bio/...` | Mavzu, level, termin, ketma-ketlik, rasm topshirig'i, seed |
| `admin_access` | `/api/admin/access/...` | Guruhlar, tekshirish (`/verify`), sinxronlash (`/sync`), bog'lanishlar |
| `admin_analytics` | `/api/admin/analytics` | Umumiy statistika |
| `admin_dashboard` | `/api/admin/dashboard-cards` | Bosh sahifa kartalari |
| `admin_bookshop` | `/api/admin/book-products` | Kitob mahsulotlari |
| `admin_faq` | `/api/admin/faq` | FAQ |
| `admin_student_results` | `/api/admin/student-results` | Natijalar / fikrlar |
| `admin_docx_import` | `/api/admin/tests/{id}/import-docx` | .docx dan savol import |
| `uploads` | `/api/admin/upload-image` | Rasm yuklash |
| `diagnostics` | `/api/debug/db-info` | Baza yo'li, hajmi, jadval sonlari |

---

## 5. Mini App sahifalari va backend bog'lanishi

### Navigatsiya arxitekturasi

`webapp/index.html` — bitta fayl, ichida `<section id="screen-*" class="screen">`
ko'rinishidagi ekranlar. `navigate.js:showScreen()` faqat bittasini ko'rsatadi.

Modullar bir-birini **to'g'ridan-to'g'ri import qilmaydi** — aylanma bog'liqlikning
oldini olish uchun `CustomEvent` ishlatiladi:

```
courses.js  ──navigateTo("referral")──>  document.dispatchEvent("app:navigate")
                                                      │
                                          main.js tinglaydi ──> handleNav() ──> showScreen()
```

Ekran almashganda `app:screenchanged` hodisasi yuboriladi (masalan `courses.js`
buni tinglab, ochiq video darsni to'xtatadi).

### Bosh sahifa (`home.js`)

`GET /api/dashboard-cards` → 7 ta karta. Matn/belgi **admin panelidan
tahrirlanadi**, lekin qaysi ekranga olib borishi frontendda qattiq belgilangan
(`CARD_META` — `card_key` → `nav` + rang):

| `card_key` | Karta | Qaysi ekranga |
|---|---|---|
| `courses` | 📚 Kurslar | `courses-landing` |
| `tests` | 📝 Testlar | `tests` |
| `rating` | 🏆 Reyting | `leaderboard` |
| `books` | 📗 Kitoblar | `book-shop` |
| `games` | 🎮 O'yinlar | `games` |
| `results` | 🏆 Natijalar | `student-results` |
| `homework` | 📸 Vazifa topshirish | `homework` |

### 5.1. Kurslar (`courses.js` — 41 KB)

Ikki bosqichli oqim: **fan tanlash → guruhlangan ro'yxat**.

```
courses-landing  ──> GET /api/course-categories
      │                  GET /api/courses?resource_type=course
      ↓
courses-by-subject (Nazoratli / Mustaqil / Bepul bo'yicha guruhlangan)
      │
      ↓
course-detail    ──> GET /api/course/{id}     (paragraflar + kirish holati)
      │              POST /api/access/refresh (guruh a'zoligini qayta tekshirish)
      ↓
paragraph        ──> darslar ro'yxati
      │
      ↓
lesson (video)   ──> POST /api/lesson/{id}/watched   → +1 coin
                     GET  /api/course/{id}/certificate/download → PDF
```

Backend: `routers/courses.py` → `database.get_all_courses()`,
`get_course()`, `compute_course_access()`, `mark_lesson_watched()`.

`compute_course_access()` — kirish huquqini 4 manbadan hisoblaydi: bepul kurs /
referal soni / `enrollments` yozuvi / Telegram guruh a'zoligi.

### 5.2. Testlar (`tests.js` — 70 KB, eng katta frontend modul)

Bitta modul **4 xil test rejimini** boshqaradi:

| Rejim | Kirish endpointi | Backend |
|---|---|---|
| **Mavzuli test** | `/api/test-subject-cards` → `/stages` → `/groups` → `/tests` | `routers/tests.py` |
| **Nazorat testi** | `/api/control-tests` | `routers/control_tests.py` |
| **Simulyator (DTM)** | `/api/simulators` → `/simulator/{id}/start` | `routers/simulators.py` |
| **Milliy sertifikat** | `/api/certificate-tests` | `routers/tests.py` |

Topshirish oqimi ikkala rejim uchun umumiy — `attemptApiBase()` funksiyasi
yo'l prefiksini dinamik tanlaydi (`/api/attempt` yoki `/api/simulator/attempt`):

```
POST {base}/{attemptId}/answer   → har bir javob
POST {base}/{attemptId}/finish   → yakunlash
GET  /api/attempt/{id}/rank      → o'rin
GET  /api/my-progress-history    → progress grafigi
```

Qo'shimcha imkoniyatlar: savolni belgilash (`/flag`), e'tiroz (`/objection`),
yozma ish rasmi (`/upload-answer-image` → `/written-answer`).

### 5.3. O'yinlar (`chemGame.js` 58 KB + `bioGame.js` 34 KB)

`screen-games` → `GET /api/chem/hub` va `GET /api/bio/hub` (ikkisi ham
`chemGame.js:loadGameSubjects()` dan chaqiriladi).

**Kimyo o'yini oqimi:**
```
chem-hub ──> GET /api/chem/hub          (rating, kunlik missiya, kategoriyalar)
   ├─> chem-categories ──> chem-path ──> GET /api/chem/category/{id}/path
   │                          │
   │                          └─> level ──> GET /api/chem/level/{id}/stage/{n}
   │                                        POST .../check  (yozma javob)
   │                                        POST .../submit (yulduz + coin)
   ├─> battle ──> POST /api/chem/battle/start | /invite | /join-code
   │              GET  /api/chem/battle/{id}/question
   │              POST /api/chem/battle/{id}/answer | /finish
   ├─> tournaments ──> GET /api/chem/tournament/list | /{id}
   │                   POST /api/chem/tournament/create | /{id}/join
   └─> dictionary ──> GET /api/chem/dictionary?q=
```

**Biologiya o'yini** — 7 xil o'yin turi (`bio_available_stages()` kontentga
qarab qaysilari mavjudligini aniqlaydi): kartochka, ta'rif→termin,
termin→ta'rif, vazifa, guruhlash, "men kimman", ketma-ketlik, rasm belgilash.

### 5.4. Reyting (`leaderboard.js`)

```
GET /api/leaderboard?period=all|week|month   → umumiy coin reytingi
GET /api/control-test-leaderboard            → nazorat testi oylik reytingi
```

`period` filtri `coin_history` jadvali orqali ishlaydi.
Nazorat reytingi **50/50 formula** bo'yicha: `get_combined_monthly_leaderboard()`
nazorat testi ballari va uy vazifasi ballarini teng ulushda birlashtiradi.

### 5.5. Kitoblar (`bookshop.js`)

`GET /api/book-products` → bosma kitoblar do'koni.
Bosh sahifadagi "Kitoblar" kartasi **to'g'ridan-to'g'ri** shu ekranga olib
boradi. Eski "raqamli kitoblar" ro'yxati (`resource_type='book'` kurslar)
faqat do'kon ichidagi kichik havola orqali ochiladi.

> ⚠️ To'lov tizimi (Payme/Click) **ulanmagan** — sotib olish
> `contact_username` orqali Telegram'da administratorga yozish bilan amalga
> oshadi.

### 5.6. Profil (`profile.js`)

```
GET /api/user            → ism, coin, streak, umumiy o'rin
GET /api/achievements    → 14 ta nishon devori (olingan / olinmagan)
GET /api/my-certificates → sertifikatlar
GET /api/my-enrollments  → faol obunalar va muddatlari
```

### 5.7. Boshqa ekranlar

| Ekran | Modul | Endpoint |
|---|---|---|
| Vazifa topshirish | `homework.js` | `/api/homework/*` |
| Natijalar | `studentResults.js` | `/api/student-results` |
| Yordam | `faq.js` | `/api/faq` |
| Referal | `referral.js` | `/api/referral-link` |
| Admin panel | `admin.js` + 3 ta yordamchi | `/api/admin/*` |

---

## 6. Gamifikatsiya tizimi

Loyihada **to'rt xil, bir-biridan mustaqil** motivatsiya mexanizmi ishlaydi.

### 6.1. Coin (tanga) — asosiy valyuta

**Coin qayerdan beriladi (aniq 5 ta joy):**

| Harakat | Miqdor | Kod |
|---|---|---|
| Darsni birinchi marta ko'rish | +1 | `database.py:2666` (`mark_lesson_watched`) |
| Test savoliga birinchi marta to'g'ri javob | +1 | `database.py:3651` (`submit_answer`) |
| Simulyator savoliga to'g'ri javob | +1 | `database.py:4463` (`submit_simulator_answer`) |
| Kimyo o'yini bosqichini yakunlash | o'zgaruvchan | `routers/chem_game.py:234` |
| Biologiya o'yini bosqichini yakunlash | o'zgaruvchan | `routers/bio_game.py:278` |

**Takroriy coin oldini olish:**
- Darslar uchun — `lesson_progress.coin_awarded` bayrog'i
- Savollar uchun — `user_question_progress (telegram_id, question_id, coin_awarded)`

Ya'ni bir savolni 10 marta yechsangiz ham coin **faqat bir marta** beriladi.

**Yozuv joyi:** har bir coin ikki joyga yoziladi —
`users.coins` (umumiy hisob) va `coin_history (telegram_id, amount, created_at)`
(davr bo'yicha reyting uchun). Bu `add_coins()` funksiyasida amalga oshadi.

### 6.2. Streak (ketma-ket kunlar)

`record_daily_activity(telegram_id)` — o'quvchi biror faol harakat qilganda
chaqiriladi. Mantiq (UTC sanasi bo'yicha):

```
last_activity_date == bugun     → hech narsa o'zgarmaydi
last_activity_date == kecha     → current_streak += 1
aks holda (uzilish / birinchi)  → current_streak = 1

longest_streak = max(longest_streak, current_streak)
```

Ustunlar: `users.current_streak`, `users.longest_streak`, `users.last_activity_date`.

### 6.3. ELO reytingi — ikkita mustaqil tizim

**Universal Battle** (`game_ratings`) — ⚠️ frontendga ulanmagan:

```
BATTLE_QUESTIONS_PER_ROUND = 5
BATTLE_ELO_K_FACTOR = 32
BATTLE_STARTING_ELO = 1000

Darajalar: Temir(0) → Bronza(900) → Kumush(1100) → Oltin(1300)
           → Platina(1500) → Olmos(1700)
```

Har bir **fan uchun alohida** ELO (`game_ratings.subject`). Savollar alohida
bank emas — `test_questions` dan fan bo'yicha tasodifiy tanlanadi, ya'ni
o'qituvchi qo'shimcha kontent tayyorlashi shart emas.

**Kimyo Battle** (`chem_ratings`) — ishlayotgan tizim:

```
BATTLE_QUESTION_COUNT = 10
BATTLE_STALE_MINUTES = 10     # raqib topilmasa, bot qo'shiladi
ELO_K = 32
Boshlang'ich ELO = 1000

Darajalar: Bronza 🥉(0) → Kumush 🥈(1100) → Oltin 🥇(1300)
           → Platina 🔷(1500) → Olmos 💎(1700)
```

ELO formulasi ikkalasida bir xil (standart shaxmat formulasi):

```python
expected = 1 / (1 + 10 ** ((opp_elo - my_elo) / 400))
delta = round(K * (score - expected))     # score: 1=g'alaba, 0.5=durang, 0=mag'lubiyat
```

Kimyo tizimida qo'shimcha: `current_streak` / `best_streak` (ketma-ket
g'alabalar), bot bilan o'ynash (raqib 10 daqiqada topilmasa), taklif kodi
(`invite_code`) orqali do'st bilan jang.

### 6.4. Kunlik missiya

```python
get_chem_daily_mission(telegram_id, target=3)
# Bugun nechta kimyo jangini yakunlagani → {"done": N, "target": 3, "completed": bool}
```

Hozircha **faqat kimyo battle** uchun mavjud. Biologiya yoki umumiy missiya yo'q.

### 6.5. Yulduzlar (o'yin bosqichlari)

Kimyo va biologiya levellarida har bir bosqich **1-3 yulduz** bilan baholanadi
(`chem_stars_for_accuracy(correct, total)`). Yulduzlar
`chem_stage_progress` / `bio_stage_progress` da saqlanadi va keyingi levelning
ochilishini belgilaydi (ketma-ket ochilish).

### 6.6. Nishonlar (achievements) — 14 ta

`ACHIEVEMENT_DEFS` ro'yxati (`database.py:1779`). Har biri:
`key`, `title`, `description`, `icon`, `check(stats) -> bool`.

| Kalit | Nishon | Shart |
|---|---|---|
| `first_lesson` | 🎬 Birinchi qadam | 1 dars ko'rilgan |
| `lessons_10` | 📚 Bilim ishqibozi | 10 dars |
| `lessons_50` | 🎓 Bilim changali | 50 dars |
| `first_test` | 📝 Birinchi sinov | 1 test yakunlangan |
| `tests_10` | 🏅 Test ustasi | 10 test |
| `perfect_score` | 💯 Mukammal natija | Biror testda 100% |
| `control_test_done` | 🎯 Nazoratdan o'tdi | 1 nazorat testi |
| `first_battle_win` | ⚔️ Jangchi | 1 Battle g'alaba ⚠️ |
| `battle_wins_10` | 🏆 Chempion | 10 Battle g'alaba ⚠️ |
| `coins_50` | 🪙 Tejamkor | 50 coin |
| `referrals_5` | 🎁 Do'stlar yetakchisi | 5 tasdiqlangan referal |
| `streak_3` | 🔥 Qizigan boshlanish | 3 kun ketma-ket |
| `streak_7` | 🔥 Haftalik intizom | 7 kun |
| `streak_30` | 🔥 Temir intizom | 30 kun |

⚠️ **`first_battle_win` va `battle_wins_10` hech qachon berilmaydi** —
`_gather_achievement_stats()` g'alabalarni `game_ratings` jadvalidan oladi,
lekin bu jadval frontend ulanmagani uchun hech qachon to'lmaydi. Kimyo battle
g'alabalari (`chem_ratings.wins`) hisobga olinmaydi.

`check_and_award_achievements()` har bir muhim harakatdan keyin chaqiriladi:
statistikani qayta hisoblab, hali berilmagan lekin shartga mos nishonlarni
beradi va **yangi berilganlar ro'yxatini** qaytaradi (frontend animatsiya
ko'rsatishi uchun).

### 6.7. Referal tizimi

```
create_pending_referral(referrer_id, referred_id)   → /start havolasi orqali
confirm_referral(referred_id)                        → kanalga obuna bo'lgach tasdiqlanadi
get_confirmed_referral_count(telegram_id)            → kursga kirish sharti
```

`courses.required_referrals` — kursni ochish uchun kerakli tasdiqlangan
referallar soni.

---

## 7. Deploy jarayoni

### Platforma: Railway

**Start Command:**
```
uvicorn server:app --host 0.0.0.0 --port $PORT
```

Railway `requirements.txt` ni avtomatik aniqlaydi va Python muhitini o'zi
tayyorlaydi. `Procfile`, `Dockerfile`, `railway.toml` — hech biri kerak emas.

**Alohida bot xizmati kerak emas** — bot `server.py` startup'ida fon vazifasi
sifatida ishga tushadi.

### ⚠️ Volume (doimiy xotira) — eng muhim sozlama

SQLite fayli konteyner ichida saqlanadi. Railway Volume ulanmasa, **har
deploy'da barcha ma'lumotlar o'chib ketadi.**

1. Railway → Service → **Volumes** → Mount path: `/data`
2. Variables → `DB_PATH=/data/database.db`

`UPLOADS_DIR` alohida sozlash **shart emas** — standart holatda `DB_PATH`
papkasining ichiga (`/data/uploads`) joylashadi.

Tekshirish: deploy'dan keyin **Deploy Logs** da:
```
[BAZA DIAGNOSTIKASI] DB_PATH = /data/database.db
[BAZA DIAGNOSTIKASI] ✅ Doimiy xotira (Volume) yo'liga o'xshaydi.
```
Agar ⚠️ ogohlantirish chiqsa — `DB_PATH` noto'g'ri sozlangan.

### Muhit o'zgaruvchilari

**Majburiy** (yo'q bo'lsa server `sys.exit()` bilan to'xtaydi):

| O'zgaruvchi | Nima | Qanday olinadi |
|---|---|---|
| `BOT_TOKEN` | Telegram bot tokeni | @BotFather |
| `ADMIN_PASSWORD_HASH` | Admin parolining bcrypt hash'i | `python generate_password_hash.py` |
| `JWT_SECRET_KEY` | JWT imzolash kaliti | `python3 -c "import secrets; print(secrets.token_hex(32))"` |

**Ixtiyoriy** (standart qiymati bor):

| O'zgaruvchi | Vazifasi |
|---|---|
| `DB_PATH` | SQLite fayl yo'li — **production'da albatta Volume yo'li** |
| `UPLOADS_DIR` | Yuklangan rasmlar papkasi (standart: `DB_PATH` papkasi + `/uploads`) |
| `ADMIN_TELEGRAM_IDS` | Parolsiz admin bo'ladigan Telegram ID'lar (vergul bilan) |
| `WEBAPP_URL` | Mini App HTTPS manzili (bot tugmasi uchun) |
| `BOT_USERNAME` | Bot username (referal havolasi uchun) |
| `CHANNEL_USERNAME` | Majburiy obuna kanali (`@...`) |
| `CHANNEL_URL` | Kanal havolasi |
| `BRAND_NAME` | Brend nomi |
| `BRAND_SUB` | Brend qo'shimcha matni |
| `ADMIN_CONTACT_USERNAME` | Kitob sotib olish uchun bog'lanish username'i |
| `HOMEWORK_ARCHIVE_CHAT_ID` | Vazifa rasmlari saqlanadigan yopiq kanal ID (`-100...`) |
| `HOMEWORK_PHOTO_RETENTION_DAYS` | Baholangan rasmlar necha kundan keyin o'chirilsin (standart 90) |

> Barcha qiymatlar `.env.example` da namuna sifatida ko'rsatilgan.
> `.env` fayli **hech qachon** commit qilinmaydi.

### `HOMEWORK_ARCHIVE_CHAT_ID` — nima uchun muhim

Vazifa rasmlari serverda saqlansa, xotira juda tez to'ladi
(50 o'quvchi × 120 paragraf × 3 rasm ≈ 36 GB).

Yechim: bot rasmni **yopiq Telegram kanalga** yuboradi, bazada esa faqat
Telegram bergan `file_id` satri (~80 bayt) qoladi — 2 MB o'rniga 80 bayt,
25 000 marta kam. Telegram fayllarni bepul va muddatsiz saqlaydi.

Sozlash: yopiq kanal oching → botni admin qiling → kanal ID sini
`HOMEWORK_ARCHIVE_CHAT_ID` ga yozing. **Sozlanmasa tizim to'xtamaydi** —
rasmlar avvalgidek diskka saqlanadi.

### Telegram tomonidagi sozlamalar

1. @BotFather → `/newbot` → token olish
2. Mini App **HTTPS** manzilda bo'lishi shart (Telegram `http` ni qabul qilmaydi)
3. `WEBAPP_URL` ni Railway bergan manzilga sozlash
4. Bot menyu tugmasi `setup_menu_button()` orqali avtomatik o'rnatiladi

### Deploy'dan keyin tekshirish ro'yxati

- [ ] Deploy Logs'da `✅ Doimiy xotira` xabari bormi
- [ ] `GET /api/debug/db-info` — jadval sonlari to'g'rimi
- [ ] Botga `/start` — Mini App tugmasi chiqadimi
- [ ] Mini App ichida Admin bo'limi ko'rinadimi (`ADMIN_TELEGRAM_IDS` to'g'rimi)

---

## 8. Ma'lum muammolar va tugallanmagan qismlar

### 🔴 Yuqori muhimlik

#### 8.1. `/api/games/*` — butun modul frontendga ulanmagan

`routers/games.py` (6 endpoint), `game_battles` va `game_ratings` jadvallari,
ELO hisoblash, bot xabarnomalari (`send_battle_result_notifications_loop`) —
hammasi yozilgan va ishlaydi, lekin `webapp/js/` da `api/games` satri
**umuman uchramaydi**.

Oqibatlari:
- `game_ratings` jadvali hech qachon to'lmaydi
- `first_battle_win` va `battle_wins_10` nishonlari **hech qachon berilmaydi**
- `send_battle_result_notifications_loop()` fon vazifasi doim bo'sh natija bilan aylanadi

Yechim variantlari: (a) frontendni ulash, (b) nishonlarni `chem_ratings` ga
qayta yo'naltirish, (c) modulni butunlay olib tashlash.

#### 8.2. Chempionat o'yin oqimi tugallanmagan

`/api/chem/tournament/list`, `/create`, `/{id}`, `/{id}/join` — **ulangan**.
Lekin haqiqiy o'ynash endpointlari frontendda chaqirilmaydi:
- `/{id}/qual/question`, `/{id}/qual/answer`, `/{id}/qual/finish` (saralash)
- `/match/{id}/question`, `/match/{id}/answer`, `/match/{id}/finish` (setka)

Ya'ni chempionat yaratish va unga qo'shilish ishlaydi, **o'ynab bo'lmaydi**.

#### 8.3. To'lov tizimi ulanmagan

Payme/Click integratsiyasi yo'q (`database.py:1666` da yozib qo'yilgan).
Kitob sotib olish `contact_username` orqali Telegram'da administratorga
yozish bilan amalga oshadi. `course_pricing_tiers` jadvalida narxlar bor,
lekin avtomatik to'lov yo'q — enrollment qo'lda beriladi.

#### 8.4. `database.db` git'da kuzatilmoqda

`.gitignore` da `database.db` ko'rsatilgan, lekin fayl allaqachon git'ga
qo'shilgani uchun kuzatilishda davom etmoqda (86 KB). Har o'zgarishda
commit'ga tushadi va **lokal test ma'lumotlari repo'ga kirib qoladi**.

Tuzatish: `git rm --cached database.db`

### 🟡 O'rta muhimlik

#### 8.5. `database.py` — 7688 qatorlik monolit

`server.py` izohida "har bir fayl 300 qatordan oshmaydi" tamoyili e'lon
qilingan, lekin bu faqat **routerlarga** qo'llanilgan. Baza qatlami hali
bitta fayl:

- `init_db()` — 1687 qator (faylning 23%i)
- Qolgan ~6000 qator — 15 ta mantiqiy bo'lim

Bo'limlar allaqachon izohlar bilan aniq ajratilgan, shuning uchun
`db/courses.py`, `db/tests.py`, `db/chem.py`, `db/homework.py`, `db/access.py`
ko'rinishida bo'lish nisbatan oson.

#### 8.6. Migratsiya `try/except pass` orqali

Har bir yangi ustun quyidagicha qo'shiladi:

```python
try:
    cur.execute("ALTER TABLE ... ADD COLUMN ...")
    conn.commit()
except sqlite3.OperationalError:
    pass
```

Muammolari:
- Haqiqiy xatolikni ham (masalan sintaksis xatosi, baza buzilgani) jimgina yutadi
- Versiya raqami yo'q — qaysi migratsiya bajarilgani nomaʼlum
- Har ishga tushishda barcha ALTER'lar qayta urinib ko'riladi
- `init_db()` ni 1687 qatorga cho'zgan

#### 8.7. FOREIGN KEY qamrovi to'liq emas

`PRAGMA foreign_keys = ON` yoqilgan, lekin atigi ~24 ta FK e'lon qilingan.
`telegram_id` bo'yicha bog'lanishlarning **hech biri** FK emas. Foydalanuvchi
o'chirilsa, uning `lesson_progress`, `test_attempts`, `chem_ratings`,
`homework_submissions` yozuvlari yetim qolib ketadi.

#### 8.8. CORS to'liq ochiq

```python
allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
```

Haqiqiy himoya `initData` HMAC tekshiruvida bo'lgani uchun bu **kritik emas**,
lekin `WEBAPP_URL` bilan cheklash yaxshiroq bo'lardi.

#### 8.9. Rate limit faqat bitta endpointda

Butun loyihada faqat `/api/admin/login` cheklangan (5/15daq). Qolgan 193
endpoint cheklanmagan — masalan `/api/chem/battle/start` yoki
`/api/upload-answer-image` ni ketma-ket chaqirish mumkin.

### 🟢 Past muhimlik / tozalash

#### 8.10. Eski fayllar repo ildizida

| Fayl | Holati |
|---|---|
| `index.html` (285 qator) | `webapp/index.html` (1907 qator) bilan almashtirilgan — **o'lik kod** |
| `app.js` (36 KB) | `webapp/js/` ga 21 ta modulga bo'lingan — **o'lik kod** |
| `style.css` (16 KB) | `webapp/style.css` (153 KB) bilan almashtirilgan — **o'lik kod** |
| `kelajak-bot.zip` (34 KB) | Arxiv qoldig'i |
| `39-NAZORAT (toza).docx` | Test import namunasi (`webapp/savol-shabloni.docx` bor) |

Server faqat `webapp/` papkasini mount qiladi, shuning uchun ildizdagi bu
fayllar hech qachon xizmat qilmaydi. Ular 2026-08-05 dagi bitta commit'dan
beri o'zgarmagan.

#### 8.11. `README.md` eskirgan

Hozirgi `README.md`:
- Loyihani "Kelajak mediklari" deb ataydi (brend o'zgargan)
- `config.py` ichiga token yozishni maslahat beradi (endi `.env` ishlatiladi)
- "bot.py ni ikkinchi service qilib deploy qiling" deydi (endi bitta jarayon)
- "Kurslar/Reyting/Testlar tugmalariga JS logikasini qo'shing (hozir faqat
  Bosh sahifa ishlaydi)" deydi — bularning hammasi allaqachon yozilgan
- Fayllar tuzilishida `routers/` va `webapp/js/` umuman ko'rsatilmagan

#### 8.12. Frontendga ulanmagan boshqa endpointlar

| Endpoint | Izoh |
|---|---|
| `/api/admin/login` | Parol bilan login ishlaydi, lekin admin panelda kirish formasi yo'q — faqat Telegram whitelist ishlatiladi |
| `/api/homework/my-summary` | Umumiy natija sahifasi yozilmagan |
| `/api/course/{id}/certificate/status` | Frontend to'g'ridan-to'g'ri `/download` ni chaqiradi |
| `/api/homework/photo/{id}` | Rasm proxy — `<img src>` orqali ishlatilishi mumkin, lekin JS'da uchramadi |
| `/api/chem/battle/{id}/status` | Jang holatini so'rash |
| `/api/admin/control-tests/{id}/courses` | Nazorat testini kursga bog'lash UI'si yo'q |
| `/api/debug/db-info` | Qo'lda diagnostika uchun (normal) |

#### 8.13. Frontend fayl hajmlari

Build tool yo'qligi sababli katta modullar to'liq yuklanadi:
`admin.js` 127 KB, `tests.js` 70 KB, `chemGame.js` 58 KB, `style.css` 153 KB.
Sekin internetda birinchi ochilish sezilarli (`main.js` da 6 soniyalik splash
fallback shu sababli qo'yilgan).

#### 8.14. Vaqt zonasi UTC

`record_daily_activity()` streak'ni **UTC sanasi** bo'yicha hisoblaydi.
O'zbekiston UTC+5 bo'lgani uchun, mahalliy vaqt bilan soat 05:00 gacha bo'lgan
faollik "kechagi kun"ga yoziladi. Kunlik missiya
(`DATE(finished_at) = DATE('now')`) ham SQLite'ning UTC sanasidan foydalanadi.

---

## Tez ma'lumot

| Ko'rsatkich | Qiymat |
|---|---|
| Backend Python fayllari | 16 ta (routers'siz) + 36 ta router |
| `database.py` | 7688 qator, 320 KB |
| Ma'lumotlar bazasi jadvallari | 60 ta |
| API endpointlar | 194 ta |
| Frontend JS modullari | 21 ta |
| Fon vazifalari (background loops) | 7 ta |
| Nishonlar | 14 ta |
| Bosh sahifa kartalari | 7 ta |
| Bog'liqliklar | 10 ta |
