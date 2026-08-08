# database.py
# Barcha ma'lumotlar bazasi funksiyalari (v4 — ulanishlar puli bilan)
#
# XAVFSIZLIK/ARXITEKTURA YANGILANISHI:
# Endi har bir funksiya sqlite3.connect()/close() ni to'g'ridan-to'g'ri chaqirmaydi,
# buning o'rniga db_pool.get_connection() orqali puldagi tayyor ulanishlardan
# birini oladi va ishlatib bo'lgach avtomatik qaytaradi. Funksiyalarning tashqi
# xatti-harakati (qabul qiladigan parametrlar, qaytaradigan natijalar) BUTUNLAY
# O'ZGARMAGAN — faqat ulanish bilan ishlash usuli yaxshilandi.

import sqlite3
import datetime
import json

from db_pool import get_connection, init_pool
from config import DB_PATH


def safe_int(value, default: int = 0) -> int:
    """Kelgan qiymatni BUTUN SONGA xavfsiz aylantiradi.

    NEGA KERAK: admin panelidagi raqamli maydon bo'sh qoldirilsa, brauzer
    JavaScript'i uni `null` sifatida yuboradi (parseInt("") -> NaN ->
    JSON'da null). Oddiy int(None) esa TypeError beradi va butun so'rov
    500 xatolik bilan yiqiladi — admin uchun bu "tugmani bosdim, lekin
    hech narsa bo'lmadi" ko'rinishida namoyon bo'ladi. Shu funksiya
    orqali bunday hollarda standart qiymat ishlatiladi."""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

# Bosh sahifa kartalarining STANDART (birinchi marta ishga tushganda
# to'ldiriladigan) qiymatlari — (card_key, title, subtitle, icon, order_num).
# card_key HECH QACHON o'zgarmaydi (frontend shu bo'yicha qaysi ekranga
# olib borishni aniqlaydi), qolgan maydonlar admin panelidan tahrirlanadi.
DASHBOARD_CARD_DEFAULTS = [
    ("courses", "📚 Kurslar", "NAZORATLI · MUSTAQIL · BEPUL", "🎓", 1),
    ("tests", "📝 Testlar", "DTM · MAVZULI · SERTIFIKAT", "📄", 2),
    ("rating", "🏆 Reyting", "SIZNING O'RNINGIZ", "🥇", 3),
    ("books", "📗 Kitoblar", "DO'KON · PROMOKODLAR", "📖", 4),
    ("games", "🎮 O'yinlar", "TEZ ORADA", "🕹️", 5),
    ("results", "🏆 Natijalar", "SERTIFIKAT NATIJALARI · FIKRLAR", "📈", 6),
    ("homework", "📸 Vazifa topshirish", "ISHLANGAN MASALALAR RASMI", "✍️", 7),
]


def init_db():
    init_pool()
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                first_name TEXT,
                username TEXT,
                points INTEGER DEFAULT 10,
                coins INTEGER DEFAULT 0,
                referred_by INTEGER,
                is_subscribed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Kunlik faollik ("streak") ustunlari — o'quvchi ketma-ket necha kun
        # ilovada faol bo'lganini kuzatish uchun. Eski bazalarda bu ustunlar
        # yo'q bo'lgani sababli ALTER TABLE orqali (xatoni jimgina o'tkazib
        # yuborib) qo'shamiz — boshqa joylarda ishlatilgan uslub bilan bir xil.
        for alter_sql in (
            "ALTER TABLE users ADD COLUMN current_streak INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN longest_streak INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN last_activity_date TEXT",
        ):
            try:
                cur.execute(alter_sql)
                conn.commit()
            except sqlite3.OperationalError:
                pass  # ustun allaqachon mavjud — muammo emas

        cur.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                subject TEXT NOT NULL,
                resource_type TEXT DEFAULT 'course',
                description TEXT,
                is_free INTEGER DEFAULT 1,
                required_referrals INTEGER DEFAULT 0,
                price INTEGER DEFAULT 0,
                duration_days INTEGER,
                duration_text TEXT,
                students_count INTEGER DEFAULT 0,
                thumbnail_emoji TEXT DEFAULT '📘',
                order_num INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Kurs "turi" — Kelajakmediklari_bot tahlili asosida: 'nazoratli'
        # (jurnal/davomat/mentor bilan kuzatiladigan) yoki 'mustaqil' (o'z
        # sur'atida, kuzatuvsiz). Mavjud barcha kurslar avtomatik 'mustaqil'
        # bo'lib qoladi — admin xohlaganlarini keyin 'nazoratli'ga o'zgartiradi.
        try:
            cur.execute("ALTER TABLE courses ADD COLUMN course_type TEXT DEFAULT 'mustaqil'")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud — muammo emas

        cur.execute("""
            CREATE TABLE IF NOT EXISTS paragraphs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                order_num INTEGER DEFAULT 0,
                FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
            )
        """)

        # "Mavzu soni" — Kelajakmediklari_bot'dagi "30 ta dars · 42 ta mavzu"
        # ko'rinishidagi ikkinchi son. Bizda dars = mavzu (1:1) bo'lsa ham,
        # admin ba'zan kattaroq "mavzular" sonini alohida ko'rsatmoqchi
        # bo'lishi mumkin (masalan bitta darsda bir nechta mavzu qamrab
        # olingan bo'lsa) — shuning uchun darsdan MUSTAQIL, qo'lda
        # kiritiladigan ustun sifatida qo'shildi.
        try:
            cur.execute("ALTER TABLE paragraphs ADD COLUMN topic_count INTEGER DEFAULT 0")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud — muammo emas

        # Kurs narx paketlari ("PAKET TANLANG") — bir kursga bir nechta
        # muddat/narx variantini ko'rsatish imkonini beradi (masalan "1 oy —
        # 250 000 so'm", "3 oy — 650 000 so'm"). Bu FAQAT ko'rsatish/marketing
        # uchun — haqiqiy kirish huquqi hozirgidek admin tomonidan qo'lda
        # (grant_enrollment) beriladi, chunki ilovada onlayn to'lov integratsiyasi yo'q.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS course_pricing_tiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                label TEXT NOT NULL,
                price INTEGER DEFAULT 0,
                original_price INTEGER,
                duration_text TEXT,
                order_num INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
            )
        """)

        # "Jami darslar soni" — ba'zi kurslarda bir necha mavzu birlashib
        # bitta "dars" deb hisoblanadi, shuning uchun haqiqiy video-darslar
        # sonidan farq qilishi mumkin. Admin buni qo'lda kiritsa, hero'da
        # avtomatik hisoblangan son o'rniga shu ko'rsatiladi. Bo'sh/NULL
        # bo'lsa — avvalgidek platformadagi haqiqiy darslar soni ishlatiladi.
        try:
            cur.execute("ALTER TABLE courses ADD COLUMN lessons_count_override INTEGER")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud — muammo emas

        # Kurs "bo'limlari" (kategoriyalari) — avval qattiq belgilangan
        # 'nazoratli'/'mustaqil' course_type maydoni o'rniga, admin o'zi
        # istalgan nomda bo'lim (masalan "Nazoratli", "Mustaqil", "Bepul
        # kurs", "VIP") yaratib, har bir kursni BIR NECHTA bo'limga bir
        # vaqtda biriktira oladi (ko'p-ko'pga bog'lanish).
        cur.execute("""
            CREATE TABLE IF NOT EXISTS course_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                subtitle TEXT,
                icon TEXT DEFAULT '📁',
                order_num INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS course_category_links (
                course_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                PRIMARY KEY (course_id, category_id),
                FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES course_categories (id) ON DELETE CASCADE
            )
        """)
        conn.commit()

        # Ko'chirish (migration): agar hali birorta bo'lim yaratilmagan bo'lsa,
        # eski course_type ('nazoratli'/'mustaqil') asosida 2 ta default
        # bo'lim yaratamiz va mavjud barcha kurslarni ularga avtomatik
        # bog'laymiz — shunda hech qanday ma'lumot yo'qolmaydi va admin
        # keyinchalik ularni o'zgartirishi/qo'shishi mumkin.
        cur.execute("SELECT COUNT(*) as cnt FROM course_categories")
        if cur.fetchone()["cnt"] == 0:
            cur.execute("""
                INSERT INTO course_categories (title, subtitle, icon, order_num, is_active)
                VALUES ('Nazoratli', 'JURNAL · DAVOMAT · MENTOR', '📖', 1, 1)
            """)
            nazoratli_id = cur.lastrowid
            cur.execute("""
                INSERT INTO course_categories (title, subtitle, icon, order_num, is_active)
                VALUES ('Mustaqil', 'O''Z SUR''ATINGIZDA', '🧑‍💻', 2, 1)
            """)
            mustaqil_id = cur.lastrowid
            conn.commit()

            cur.execute("SELECT id, course_type FROM courses")
            for row in cur.fetchall():
                target_id = nazoratli_id if row["course_type"] == "nazoratli" else mustaqil_id
                try:
                    cur.execute(
                        "INSERT OR IGNORE INTO course_category_links (course_id, category_id) VALUES (?, ?)",
                        (row["id"], target_id)
                    )
                except sqlite3.OperationalError:
                    pass
            conn.commit()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paragraph_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                video_url TEXT,
                description TEXT,
                order_num INTEGER DEFAULT 0,
                FOREIGN KEY (paragraph_id) REFERENCES paragraphs (id) ON DELETE CASCADE
            )
        """)

        try:
            cur.execute("ALTER TABLE lessons ADD COLUMN image_url TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud — muammo emas

        # "Bepul namuna" dars — kurs pullik/yopiq bo'lsa ham, admin belgilagan
        # bunday darslarni talaba RO'YXATDAN O'TMASDAN ko'ra oladi
        # (Kelajakmediklari_bot'dagi "N BEPUL" belgisi shu ma'noni bildiradi).
        try:
            cur.execute("ALTER TABLE lessons ADD COLUMN is_free_preview INTEGER DEFAULT 0")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud — muammo emas

        cur.execute("""
            CREATE TABLE IF NOT EXISTS lesson_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                lesson_id INTEGER NOT NULL,
                coin_awarded INTEGER DEFAULT 0,
                watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(telegram_id, lesson_id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                expiry_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(telegram_id, course_id)
            )
        """)

        try:
            cur.execute("ALTER TABLE enrollments ADD COLUMN reminder_sent_at TIMESTAMP")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud — muammo emas

        cur.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_telegram_id INTEGER NOT NULL,
                referred_telegram_id INTEGER UNIQUE NOT NULL,
                confirmed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                title TEXT NOT NULL,
                difficulty TEXT DEFAULT 'orta',
                time_limit_seconds INTEGER DEFAULT 600,
                order_num INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Nazorat testlari — o'qituvchi tomonidan o'z kursiga yozilgan
        # o'quvchilar uchun beriladigan, alohida oylik reytingga ega maxsus
        # testlar. Bir xil "tests" jadvalidan foydalanadi, faqat shu ikki
        # ustun bilan ajratiladi.
        try:
            cur.execute("ALTER TABLE tests ADD COLUMN is_control_test INTEGER DEFAULT 0")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud — muammo emas

        try:
            cur.execute("ALTER TABLE tests ADD COLUMN course_id INTEGER")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud — muammo emas

        # Test "turi" — oddiy mavzuli testlardan tashqari, endi Attestatsiya
        # (o'qituvchilar uchun rasmiy attestatsiya sinovi, @biologiyamockbot
        # tahlili asosida qurilgan) ham shu "tests" jadvalidan foydalanadi.
        # 'practice' — oddiy/mavzuli test (standart), 'attestation' — Attestatsiya.
        # Kelajakda 'certificate' (Milliy sertifikat) uchun ham shu ustun ishlatiladi.
        try:
            cur.execute("ALTER TABLE tests ADD COLUMN test_kind TEXT DEFAULT 'practice'")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud — muammo emas

        # ---------- MAVZULI TEST: FAN KARTALARI + KETMA-KET OCHILADIGAN GURUHLAR ----------
        # Talaba ko'p bo'lishi uchun "Mavzuli test" bo'limi endi uch bosqichli:
        # Fan (Kimyo/Biologiya/...) -> shu fan ichidagi GURUH (masalan
        # "Mavzulashtirilgan testlar", "Aralash testlar" — admin o'zi
        # istagancha qo'shadi/nomlaydi) -> guruh ichidagi testlar. Guruhlar
        # order_num bo'yicha KETMA-KET ochiladi: talaba avvalgi guruhdagi
        # BARCHA testlarni tugatmaguncha keyingisi qulflangan turadi — bu
        # "bir marta ishlagan testni qayta ko'rsatmaslik" talabini ham
        # tabiiy ravishda ta'minlaydi (har guruhda YANGI testlar).
        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_subject_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                icon TEXT DEFAULT '📘',
                color_key TEXT DEFAULT 'teal',
                order_num INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_card_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                subtitle TEXT,
                icon TEXT DEFAULT '📂',
                order_num INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_card_id) REFERENCES test_subject_cards (id) ON DELETE CASCADE
            )
        """)
        conn.commit()

        try:
            cur.execute("ALTER TABLE tests ADD COLUMN test_group_id INTEGER")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud — muammo emas

        # Ichki sozlamalar jadvali — "bu migratsiya allaqachon bajarilgan"
        # kabi bir martalik belgilarni saqlash uchun.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        def _flag_done(key):
            cur.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            return cur.fetchone() is not None

        def _set_flag(key, value="1"):
            cur.execute("INSERT OR REPLACE INTO app_settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                        (key, value))
            conn.commit()

        # Fan kartasini nom bo'yicha topish — bo'shliq va katta/kichik
        # harf farqiga E'TIBOR BERMAYDI. Aks holda "Biologiya" va
        # "BIOLOGIYA" (yoki oxirida bo'shliqli "Biologiya ") alohida
        # kartalar bo'lib, ro'yxatda IKKI MARTA ko'rinib qolardi.
        def _find_subject_card(title):
            cur.execute("SELECT id FROM test_subject_cards WHERE LOWER(TRIM(title)) = LOWER(TRIM(?))", (title,))
            row = cur.fetchone()
            return row["id"] if row else None

        def _create_subject_card(title, order_num):
            icons = ["🧪", "🧬", "📘", "🔬", "📗", "📙"]
            colors = ["teal", "orange", "purple", "cyan"]
            cur.execute("""
                INSERT INTO test_subject_cards (title, icon, color_key, order_num, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (title.strip(), icons[order_num % len(icons)], colors[order_num % len(colors)], order_num))
            conn.commit()
            return cur.lastrowid

        # ---------- BIR MARTALIK boshlang'ich to'ldirish ----------
        # MUHIM: bu blok faqat BIRINCHI marta ishga tushganda bajariladi.
        #
        # Ilgari "Kimyo" va "Biologiya" kartalari HAR SAFAR server qayta
        # ishga tushganda qayta yaratilardi. Natijada o'qituvchi keraksiz
        # fanni o'chirsa ham, keyingi deploy'da u yana paydo bo'lardi.
        # Endi fan kartalarini FAQAT admin qo'shadi va o'chirgani
        # o'chirilganicha qoladi.
        if not _flag_done("test_subject_cards_seeded"):
            _seed_order = 0
            for _title in ("Kimyo", "Biologiya"):
                if _find_subject_card(_title) is None:
                    _create_subject_card(_title, _seed_order)
                _seed_order += 1

            cur.execute("""
                SELECT DISTINCT subject FROM tests
                WHERE (test_kind IS NULL OR test_kind = 'practice')
                  AND (is_control_test IS NULL OR is_control_test = 0)
                  AND subject IS NOT NULL AND subject != ''
            """)
            for row in cur.fetchall():
                subj = (row["subject"] or "").strip()
                if not subj or _find_subject_card(subj) is not None:
                    continue
                _create_subject_card(subj, _seed_order)
                _seed_order += 1

            # Har bir kartada kamida bitta guruh bo'lsin (mavjud testlarni
            # bog'lash uchun kerak) — bu ham faqat bir marta.
            cur.execute("SELECT id FROM test_subject_cards")
            for row in cur.fetchall():
                cur.execute("SELECT id FROM test_groups WHERE subject_card_id = ? LIMIT 1", (row["id"],))
                if cur.fetchone() is None:
                    cur.execute("""
                        INSERT INTO test_groups (subject_card_id, title, subtitle, icon, order_num, is_active)
                        VALUES (?, 'Barcha testlar', NULL, '📂', 1, 1)
                    """, (row["id"],))
            conn.commit()
            _set_flag("test_subject_cards_seeded")

        # ---------- Takrorlangan fan kartalarini BIRLASHTIRISH ----------
        # Eski xatolik tufayli bir xil nomli (masalan ikkita "Biologiya")
        # kartalar hosil bo'lgan bo'lishi mumkin. Eng eskisini (kichik id)
        # saqlab qolamiz, qolganlarining bosqich/turkumlarini unga
        # ko'chiramiz va dublikatni o'chiramiz — hech qanday test yo'qolmaydi.
        if not _flag_done("test_subject_cards_deduped"):
            cur.execute("""
                SELECT LOWER(TRIM(title)) AS norm, MIN(id) AS keep_id, COUNT(*) AS cnt
                FROM test_subject_cards GROUP BY norm HAVING cnt > 1
            """)
            for dup in cur.fetchall():
                keep_id = dup["keep_id"]
                cur.execute("""
                    SELECT id FROM test_subject_cards
                    WHERE LOWER(TRIM(title)) = ? AND id != ?
                """, (dup["norm"], keep_id))
                for extra in [r["id"] for r in cur.fetchall()]:
                    cur.execute("UPDATE test_stages SET subject_card_id = ? WHERE subject_card_id = ?", (keep_id, extra))
                    cur.execute("UPDATE test_groups SET subject_card_id = ? WHERE subject_card_id = ?", (keep_id, extra))
                    cur.execute("DELETE FROM test_subject_cards WHERE id = ?", (extra,))
                print(f"[MIGRATSIYA] Takrorlangan fan kartasi birlashtirildi: '{dup['norm']}' ({dup['cnt']} ta -> 1 ta)")
            conn.commit()
            _set_flag("test_subject_cards_deduped")


        # Guruhsiz (test_group_id IS NULL) testlarni mos fan kartasining
        # birinchi guruhiga bog'lash — bu XAVFSIZ va har safar ishlashi
        # mumkin, chunki YANGI karta/guruh YARATMAYDI, faqat bo'sh
        # bog'lanishni to'ldiradi (test talaba ko'zidan yo'qolmasligi uchun).
        cur.execute("SELECT id FROM test_subject_cards")
        default_group_id_by_card = {}
        for row in cur.fetchall():
            cur.execute("SELECT id FROM test_groups WHERE subject_card_id = ? ORDER BY order_num ASC, id ASC LIMIT 1",
                        (row["id"],))
            g = cur.fetchone()
            if g:
                default_group_id_by_card[row["id"]] = g["id"]

        cur.execute("SELECT id, title FROM test_subject_cards")
        card_id_by_title = {(row["title"] or "").strip().lower(): row["id"] for row in cur.fetchall()}

        cur.execute("""
            SELECT id, subject FROM tests
            WHERE test_group_id IS NULL
              AND (test_kind IS NULL OR test_kind = 'practice')
              AND (is_control_test IS NULL OR is_control_test = 0)
        """)
        ungrouped = cur.fetchall()
        for row in ungrouped:
            # Nomlarni bir xil ko'rinishga keltirib solishtiramiz (bo'shliq/registr farqi muhim emas)
            card_id = card_id_by_title.get((row["subject"] or "").strip().lower())
            if not card_id:
                continue
            group_id = default_group_id_by_card.get(card_id)
            if group_id:
                cur.execute("UPDATE tests SET test_group_id = ? WHERE id = ?", (group_id, row["id"]))
        conn.commit()

        # ---------- MAVZULI TEST: BOSQICHLAR ("1-bo'lim", "2-bo'lim"...) ----------
        # Foydalanuvchi aniqlab berdi: yuqoridagi test_groups aslida ikkinchi
        # QAVAT bo'lishi kerak edi — Fan ichida avval "1-bo'lim"/"2-bo'lim"
        # kabi KETMA-KET ochiladigan bosqichlar bo'lib, HAR BIR bosqich
        # ICHIDA "Mavzulashtirilgan testlar"/"Nazorat testlari" kabi
        # turkumlar (test_groups) joylashadi. Shuning uchun bosqich qatlami
        # (test_stages) qo'shildi va test_groups endi FAN'ga emas, BOSQICHGA
        # bog'lanadi (test_groups.stage_id). Ketma-ket ochilish mantiqi endi
        # BOSQICH darajasida ishlaydi (bir bosqichning barcha turkumlaridagi
        # BARCHA testlar tugagandan keyin keyingi bosqich ochiladi).
        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_stages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_card_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                subtitle TEXT,
                icon TEXT DEFAULT '📶',
                order_num INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subject_card_id) REFERENCES test_subject_cards (id) ON DELETE CASCADE
            )
        """)
        conn.commit()

        try:
            cur.execute("ALTER TABLE test_groups ADD COLUMN stage_id INTEGER REFERENCES test_stages (id) ON DELETE CASCADE")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud — muammo emas

        # Migratsiya: hali stage_id belgilanmagan (eski, to'g'ridan-to'g'ri
        # fanga bog'langan) turkumlarni — admin allaqachon qo'lda yaratgan
        # bo'lishi mumkin — har bir fan uchun avtomatik "1-bo'lim" bosqichiga
        # ko'chiramiz. Shu tarzda mavjud hech qanday turkum/test yo'qolmaydi,
        # admin keyin "2-bo'lim" va h.k. o'zi qo'sha oladi.
        cur.execute("SELECT DISTINCT subject_card_id FROM test_groups WHERE stage_id IS NULL")
        cards_needing_default_stage = [row["subject_card_id"] for row in cur.fetchall()]
        for card_id in cards_needing_default_stage:
            cur.execute(
                "SELECT id FROM test_stages WHERE subject_card_id = ? ORDER BY order_num ASC, id ASC LIMIT 1",
                (card_id,)
            )
            row = cur.fetchone()
            if row:
                default_stage_id = row["id"]
            else:
                cur.execute("""
                    INSERT INTO test_stages (subject_card_id, title, order_num, is_active)
                    VALUES (?, ?, 1, 1)
                """, (card_id, "1-bo'lim"))
                conn.commit()
                default_stage_id = cur.lastrowid
            cur.execute(
                "UPDATE test_groups SET stage_id = ? WHERE subject_card_id = ? AND stage_id IS NULL",
                (default_stage_id, card_id)
            )
            conn.commit()

        # Nazorat testiga TO'G'RIDAN-TO'G'RI (kursdan mustaqil) tayinlangan
        # o'quvchilar ro'yxati. Admin panelda o'qituvchi aynan qaysi
        # talabalarga shu nazorat testini topshirishga ruxsat berishni
        # birma-bir tanlaydi — bu kursga yozilishdan alohida, qo'shimcha
        # kirish yo'li (ikkalasi ham ishlaydi: kurs ORQALI yoki to'g'ridan-to'g'ri tayinlash orqali).
        cur.execute("""
            CREATE TABLE IF NOT EXISTS control_test_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER NOT NULL,
                telegram_id INTEGER NOT NULL,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(test_id, telegram_id),
                FOREIGN KEY (test_id) REFERENCES tests (id) ON DELETE CASCADE
            )
        """)

        # ---------- Nazorat testini KO'P KURSGA bog'lash ----------
        # Ilgari har bir nazorat testi faqat BITTA kursga (tests.course_id)
        # bog'lanardi. Amalda esa bitta nazorat testi bir nechta guruhga
        # kerak bo'ladi (masalan "Kuzgi milliy sertifikat" ham, "Biologiya
        # pullik" guruhi ham). Buning oqibatida o'qituvchi har bir testga
        # o'quvchilarni QO'LDA birma-bir qo'shishga majbur bo'lardi.
        #
        # Endi o'qituvchi test formasida bir nechta kursni belgilaydi va
        # o'sha kurslardan BIRORTASIGA yozilgan har bir o'quvchiga test
        # AVTOMATIK ochiladi. Qo'lda tayinlash (control_test_access) esa
        # mustaqil, qo'shimcha yo'l sifatida saqlanib qoladi — kursga
        # yozilmagan, faqat nazorat testiga qo'shilgan o'quvchilar uchun.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS control_test_course_links (
                test_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                PRIMARY KEY (test_id, course_id),
                FOREIGN KEY (test_id) REFERENCES tests (id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
            )
        """)
        conn.commit()

        # Eski BITTA kursli bog'lanishlarni (tests.course_id) yangi jadvalga
        # ko'chiramiz — mavjud sozlamalar YO'QOLMASLIGI uchun. INSERT OR
        # IGNORE tufayli qayta-qayta ishga tushsa ham dublikat hosil bo'lmaydi.
        try:
            cur.execute("""
                INSERT OR IGNORE INTO control_test_course_links (test_id, course_id)
                SELECT id, course_id FROM tests
                WHERE is_control_test = 1 AND course_id IS NOT NULL
            """)
            conn.commit()
        except sqlite3.OperationalError:
            # tests.course_id ustuni hali qo'shilmagan bo'lsa (juda eski baza) —
            # quyiroqdagi ALTER TABLE uni qo'shadi, migratsiya keyingi ishga
            # tushirishda amalga oshadi.
            pass

        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                image_url TEXT,
                option_1 TEXT,
                option_2 TEXT,
                option_3 TEXT,
                option_4 TEXT,
                correct_index INTEGER NOT NULL,
                order_num INTEGER DEFAULT 0,
                table_data TEXT,
                FOREIGN KEY (test_id) REFERENCES tests (id) ON DELETE CASCADE
            )
        """)

        # Word'dan ommaviy import qilinganda savol ichida haqiqiy Word jadvali
        # (masalan davriy jadval ma'lumotlari, izotoplar foizi) bo'lishi mumkin.
        # Buni matn sifatida qo'shib yubormasdan, JSON qatorlar ro'yxati
        # ({"tables": [{"rows": [[...], ...]}, ...]}) sifatida saqlaymiz — shunda
        # frontend uni ORIGINAL katak-katak jadval ko'rinishida chizadi. Fayl
        # yuqoridagi CREATE TABLE'da yangi o'rnatishlar uchun ustunni to'g'ridan
        # to'g'ri qo'shadi; ALLAQACHON DEPLOY QILINGAN (Railway'dagi) bazalarda
        # esa jadval CREATE TABLE bosqichida o'tkazib yuboriladi (IF NOT EXISTS),
        # shuning uchun bu yerda ALTER TABLE orqali qo'shib qo'yamiz.
        try:
            cur.execute("ALTER TABLE test_questions ADD COLUMN table_data TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud — muammo emas

        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                test_id INTEGER NOT NULL,
                score INTEGER DEFAULT 0,
                total_questions INTEGER DEFAULT 0,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                selected_index INTEGER,
                is_correct INTEGER DEFAULT 0,
                FOREIGN KEY (attempt_id) REFERENCES test_attempts (id) ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_question_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                coin_awarded INTEGER DEFAULT 0,
                UNIQUE(telegram_id, question_id)
            )
        """)

        # ---------- DTM/Milliy sertifikat SIMULYATORI ----------
        # Bir nechta fandan tasodifiy tanlangan savollarni birlashtirib,
        # yagona vaqtli imtihon sifatida topshirish tizimi.

        cur.execute("""
            CREATE TABLE IF NOT EXISTS simulators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                time_limit_seconds INTEGER DEFAULT 10800,
                order_num INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS simulator_subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulator_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                question_count INTEGER NOT NULL DEFAULT 10,
                order_num INTEGER DEFAULT 0,
                FOREIGN KEY (simulator_id) REFERENCES simulators (id) ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS simulator_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                simulator_id INTEGER NOT NULL,
                score INTEGER DEFAULT 0,
                total_questions INTEGER DEFAULT 0,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS simulator_attempt_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                order_num INTEGER DEFAULT 0,
                FOREIGN KEY (attempt_id) REFERENCES simulator_attempts (id) ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS simulator_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                selected_index INTEGER,
                is_correct INTEGER DEFAULT 0,
                FOREIGN KEY (attempt_id) REFERENCES simulator_attempts (id) ON DELETE CASCADE
            )
        """)

        # O'quvchi endi bitta savolga javobini ERKIN o'zgartira oladi (savollar
        # orasida ham erkin harakatlanadi) — shuning uchun bitta (urinish, savol)
        # juftligi uchun FAQAT BITTA javob qatori bo'lishi kerak (eskisi
        # yangisi bilan YANGILANADI, qayta qo'shilmaydi). Avval har bir
        # o'zgartirish YANGI qator sifatida qo'shilardi — bu endi noto'g'ri
        # (bir savol bir necha marta hisoblanib, ball noto'g'ri chiqishi
        # mumkin edi). Avval, agar eski (dublikat qatorli) ma'lumotlar bo'lsa,
        # ularni tozalab (har juftlik uchun faqat ENG OXIRGISINI qoldirib),
        # keyin UNIQUE indeks qo'yamiz — shundan keyin INSERT ... ON CONFLICT
        # DO UPDATE (upsert) ishlata olamiz.
        cur.execute("""
            DELETE FROM test_answers
            WHERE id NOT IN (SELECT MAX(id) FROM test_answers GROUP BY attempt_id, question_id)
        """)
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_test_answers_attempt_question
            ON test_answers(attempt_id, question_id)
        """)

        # "Belgilash" (flag) — Attestatsiya testida talaba savolni "keyinroq
        # qaytaman" deb belgilashi mumkin (@biologiyamockbot'dagi kabi).
        # Javob berilmasdan ham belgilanishi mumkin bo'lgani uchun
        # test_answers'ning o'zida (selected_index bo'sh bo'lishi mumkin).
        try:
            cur.execute("ALTER TABLE test_answers ADD COLUMN is_flagged INTEGER DEFAULT 0")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud — muammo emas

        # "E'tiroz bildirish" — talaba biror savolga e'tiroz/shikoyat
        # yozishi mumkin (@biologiyamockbot'dagi kabi), admin panelda
        # o'qituvchi bu e'tirozlarni ko'rib chiqadi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS question_objections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                telegram_id INTEGER NOT NULL,
                comment TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (attempt_id) REFERENCES test_attempts (id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES test_questions (id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            DELETE FROM simulator_answers
            WHERE id NOT IN (SELECT MAX(id) FROM simulator_answers GROUP BY attempt_id, question_id)
        """)
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_simulator_answers_attempt_question
            ON simulator_answers(attempt_id, question_id)
        """)

        # ---------- MILLIY SERTIFIKAT (Bilimni baholash agentligi rasmiy
        # spetsifikatsiyasiga muvofiq) ----------
        # Rasmiy imtihon 43 ta topshiriqdan iborat, 4 xil turda:
        #   Y1 — bitta to'g'ri javobli yopiq test (mavjud option_1-4/correct_index)
        #   Y2 — moslashtirishni talab qiladigan yopiq test (chap/o'ng ustunlar)
        #   O1 — qisqa javobli ochiq test (matn kiritiladi)
        #   O2 — kengaytirilgan javobli "yozma ish" (talaba rasm/matn
        #        yuklaydi, o'qituvchi band-band rubrika bo'yicha QO'LDA baholaydi)
        # Y1(1-32)/Y2(33-35)/O1(36-40) — Rash modeli asosida, qiyinlik
        # darajasiga qarab og'irliklangan ball (point_value) bilan;
        # O2(41-43) — rasmiy hujjatdagi M (metodika) / A (arifmetika)
        # bandlariga ko'ra, o'qituvchi tomonidan qo'lda ball qo'yiladi.
        try:
            cur.execute("ALTER TABLE test_questions ADD COLUMN question_type TEXT DEFAULT 'Y1'")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("ALTER TABLE test_questions ADD COLUMN difficulty_level TEXT DEFAULT 'past'")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        try:
            # Y1/Y2/O1 uchun XOM ball (admin tahrirlay oladi). Rasmiy
            # hujjatlarda Matematika uchun aniq ko'rsatilgan qiymat: past=1,
            # o'rta=2.2, yuqori=3 ball (Y2 uchun 2.2 ball) — Kimyo/Biologiya
            # hujjatlarida bu aniq ko'rsatilmagan (faqat "Rash modeli orqali
            # baholanadi" deyilgan), shuning uchun DEFAULT sifatida shu
            # standart formuladan foydalanamiz, admin xohlasa o'zgartiradi.
            cur.execute("ALTER TABLE test_questions ADD COLUMN point_value REAL DEFAULT 1")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        try:
            # Y2 (moslashtirish): {"left": [...], "right": [...], "correct_pairs": [[0,2],...]}
            cur.execute("ALTER TABLE test_questions ADD COLUMN match_data TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        try:
            # O1 (qisqa ochiq javob): kutilgan javob(lar) — bir nechta
            # to'g'ri variant "|" bilan ajratilishi mumkin, avtomatik
            # tekshiruv katta-kichik harf va bo'shliqqa sezgir emas.
            cur.execute("ALTER TABLE test_questions ADD COLUMN correct_answer_text TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        try:
            # O2 (yozma ish): shu topshiriq uchun maksimal ball (rasmiy
            # hujjatda masalan 41-topshiriq=30, 42=35, 43=10 kabi farqlanadi)
            cur.execute("ALTER TABLE test_questions ADD COLUMN max_score REAL DEFAULT 25")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        try:
            # O2 uchun band/rubrika tuzilishi — faqat o'qituvchiga
            # BAHOLASH VAQTIDA yo'l-yo'riq sifatida ko'rsatiladi (avtomatik
            # hisoblanmaydi): [{"label":"1-band","m_max":15,"a_max":6}, ...]
            cur.execute("ALTER TABLE test_questions ADD COLUMN rubric_json TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass

        # test_answers: Y1 dan tashqari turlar uchun ham javob saqlash va
        # OG'IRLIKLANGAN ball (points_earned) — eski oddiy is_correct=0/1
        # (1 ballik) tizimidan farqli, chunki milliy sertifikatda har bir
        # savol turli ball og'irligiga ega.
        try:
            cur.execute("ALTER TABLE test_answers ADD COLUMN answer_text TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("ALTER TABLE test_answers ADD COLUMN points_earned REAL DEFAULT 0")
            conn.commit()
        except sqlite3.OperationalError:
            pass

        # O2 (yozma ish) — talabaning rasm/matn ko'rinishidagi javobi va
        # o'qituvchining qo'lda qo'ygan bali shu yerda saqlanadi (oddiy
        # test_answers'dan alohida, chunki bu darhol emas, KEYINROQ
        # o'qituvchi tomonidan baholanadi).
        cur.execute("""
            CREATE TABLE IF NOT EXISTS certificate_written_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                photo_urls TEXT,
                text_answer TEXT,
                teacher_score REAL,
                teacher_comment TEXT,
                graded_by INTEGER,
                graded_at TIMESTAMP,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (attempt_id) REFERENCES test_attempts (id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES test_questions (id) ON DELETE CASCADE
            )
        """)
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_cert_written_attempt_question
            ON certificate_written_answers(attempt_id, question_id)
        """)

        # test_attempts: milliy sertifikat uchun og'irliklangan ball,
        # baholash holati (O2 hali qo'lda baholanmagan bo'lsa
        # 'pending_review') va taxminiy sertifikat darajasi.
        try:
            cur.execute("ALTER TABLE test_attempts ADD COLUMN raw_score_points REAL DEFAULT 0")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("ALTER TABLE test_attempts ADD COLUMN max_score_points REAL DEFAULT 0")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("ALTER TABLE test_attempts ADD COLUMN review_status TEXT DEFAULT 'auto'")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("ALTER TABLE test_attempts ADD COLUMN certificate_level TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass

        # ================================================================
        # VAZIFA TOPSHIRISH (uy vazifasi rasmlarini yuklash)
        # ================================================================
        # O'qituvchi pullik kursidagi o'quvchilardan ishlangan masalalar
        # yechimini RASMGA tushirib yuborishni talab qiladi. Bu bo'lim
        # o'sha jarayonni tartibga soladi:
        #   - fan (Kimyo, Biologiya, ...) — admin qo'shadi/tahrirlaydi
        #   - har bir fanda paragraflar soni admin tomonidan raqam bilan
        #     belgilanadi, mini-appda shuncha "N-paragraf vazifasi"
        #     bo'limi AVTOMATIK hosil bo'ladi
        #   - paragraflar KETMA-KET ochiladi: o'quvchi N-paragrafni
        #     "to'liq yukladim" deb yakunlamaguncha (N+1) ochilmaydi
        cur.execute("""
            CREATE TABLE IF NOT EXISTS homework_subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                subtitle TEXT,
                icon TEXT DEFAULT '🧪',
                color_key TEXT DEFAULT 'teal',
                paragraph_count INTEGER DEFAULT 0,
                deadline_days INTEGER DEFAULT 7,
                order_num INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Fan qaysi kurs(lar)ga bog'langan — o'quvchi shu kurslardan
        # BIRORTASIGA yozilgan bo'lsa, fan unga ochiq bo'ladi. Nazorat
        # testlaridagi bilan bir xil, isbotlangan yondashuv.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS homework_subject_courses (
                subject_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                PRIMARY KEY (subject_id, course_id),
                FOREIGN KEY (subject_id) REFERENCES homework_subjects (id) ON DELETE CASCADE,
                FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
            )
        """)

        # Bitta o'quvchining bitta paragraf bo'yicha topshirig'i.
        # status: 'draft'     — rasm yuklayapti, hali yakunlamagan
        #         'submitted' — "Vazifalar to'liq yuklandi" bosilgan
        #         'graded'    — o'qituvchi ball qo'ygan
        #         'rejected'  — o'qituvchi qayta ishlashga qaytargan
        cur.execute("""
            CREATE TABLE IF NOT EXISTS homework_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                telegram_id INTEGER NOT NULL,
                paragraph_number INTEGER NOT NULL,
                status TEXT DEFAULT 'draft',
                teacher_score REAL,
                teacher_comment TEXT,
                graded_by INTEGER,
                graded_at TIMESTAMP,
                submitted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(subject_id, telegram_id, paragraph_number),
                FOREIGN KEY (subject_id) REFERENCES homework_subjects (id) ON DELETE CASCADE
            )
        """)

        # Bir topshiriqqa bir nechta rasm — mavzu murakkabligiga qarab
        # o'quvchi "+" tugmasi orqali xohlagancha qo'sha oladi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS homework_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER NOT NULL,
                photo_url TEXT NOT NULL,
                order_num INTEGER DEFAULT 0,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (submission_id) REFERENCES homework_submissions (id) ON DELETE CASCADE
            )
        """)

        # Har bir o'quvchi uchun BOSHLANISH paragrafi.
        #
        # NEGA KERAK: o'qituvchi tizimni joriy qilganda o'quvchilar allaqachon,
        # masalan, 60-paragrafgacha vazifalarni qo'lda topshirib bo'lgan
        # bo'lishi mumkin. Ularni hammasini qaytadan yuklashga majburlash —
        # juda ko'p vaqt talab qiladi. Shuning uchun o'qituvchi "hozirgi
        # o'quvchilar 60-dan davom etsin" deb belgilay oladi: o'sha paytda
        # kursda bo'lgan har bir o'quvchiga shaxsiy boshlanish nuqtasi
        # yoziladi. KEYIN qo'shilgan yangi o'quvchilar esa avtomatik
        # 1-paragrafdan boshlaydi (ularda bu yozuv bo'lmaydi).
        cur.execute("""
            CREATE TABLE IF NOT EXISTS homework_student_start (
                subject_id INTEGER NOT NULL,
                telegram_id INTEGER NOT NULL,
                start_paragraph INTEGER NOT NULL DEFAULT 1,
                set_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (subject_id, telegram_id),
                FOREIGN KEY (subject_id) REFERENCES homework_subjects (id) ON DELETE CASCADE
            )
        """)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_hw_sub_user ON homework_submissions (telegram_id, subject_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_hw_photos_sub ON homework_photos (submission_id)")
        conn.commit()

        # Rasmni TELEGRAMDA saqlash uchun ustunlar (serverni to'ldirmaslik
        # uchun — batafsil izoh config.py da). storage: 'local' | 'telegram'.
        for _col, _ddl in [
            ("telegram_file_id", "ALTER TABLE homework_photos ADD COLUMN telegram_file_id TEXT"),
            ("telegram_message_id", "ALTER TABLE homework_photos ADD COLUMN telegram_message_id INTEGER"),
            ("storage", "ALTER TABLE homework_photos ADD COLUMN storage TEXT DEFAULT 'local'"),
        ]:
            try:
                cur.execute(_ddl)
                conn.commit()
            except sqlite3.OperationalError:
                pass

        # Fan darajasidagi standart boshlanish nuqtasi (shaxsiy yozuvi
        # bo'lmagan o'quvchilar uchun; odatda 1 bo'lib qoladi).
        try:
            cur.execute("ALTER TABLE homework_subjects ADD COLUMN default_start_paragraph INTEGER DEFAULT 1")
            conn.commit()
        except sqlite3.OperationalError:
            pass

        # Kechikkanlarga ogohlantirish YUBORILGANINI belgilash — bir xil
        # eslatma qayta-qayta yuborilmasligi uchun.
        try:
            cur.execute("ALTER TABLE homework_submissions ADD COLUMN reminder_sent_at TIMESTAMP")
            conn.commit()
        except sqlite3.OperationalError:
            pass

        # ---------- Bosh sahifa kartalari (dashboard) ----------
        # Bosh sahifadagi 6 ta katakli menyu (Kurslar, Testlar, Reyting,
        # Kitoblar, O'yinlar, Natijalar) — har birining SARLAVHASI, TEG
        # matni va belgisi (emoji) shu jadvalda saqlanadi va admin panelidan
        # o'zgartiriladi. Qaysi ekranga olib borishi (nav) esa FUNKSIONAL
        # bog'lanish bo'lgani uchun frontend kodida qattiq belgilangan —
        # faqat KO'RINISHI (matn/belgi) shu yerdan boshqariladi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dashboard_cards (
                card_key TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                subtitle TEXT DEFAULT '',
                icon TEXT DEFAULT '✨',
                is_active INTEGER DEFAULT 1,
                order_num INTEGER DEFAULT 0
            )
        """)
        for card_key, title, subtitle, icon, order_num in DASHBOARD_CARD_DEFAULTS:
            cur.execute("""
                INSERT OR IGNORE INTO dashboard_cards (card_key, title, subtitle, icon, is_active, order_num)
                VALUES (?, ?, ?, ?, 1, ?)
            """, (card_key, title, subtitle, icon, order_num))

        # Coin berilgan har bir hodisaning VAQT tarixi — Reyting bo'limida
        # "Haftalik"/"Oylik" davr bo'yicha reyting hisoblash uchun kerak
        # (batafsili izoh add_coins() ichida).
        cur.execute("""
            CREATE TABLE IF NOT EXISTS coin_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_coin_history_telegram_created
            ON coin_history(telegram_id, created_at)
        """)

        # ---------- O'YINLAR: 1x1 Battle (ELO reytingli, asinxron) ----------
        # "Asinxron" — ikkala o'yinchi BIR VAQTDA onlayn bo'lishi shart emas:
        # 1-o'yinchi "O'ynash"ni bosganda kutayotgan boshqa jang bo'lmasa,
        # yangi jang (savollar to'plami bilan) yaratiladi va DARHOL javob
        # beradi ("waiting" holatida qoladi); keyinroq 2-o'yinchi shu jangga
        # qo'shilib, xuddi shu savollarga javob beradi — shundan so'ng
        # natijalar taqqoslanib, ELO ikkalasi uchun ham yangilanadi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS game_battles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                question_ids TEXT NOT NULL,
                player1_telegram_id INTEGER NOT NULL,
                player1_score INTEGER,
                player1_time_seconds INTEGER,
                player1_finished_at TIMESTAMP,
                player2_telegram_id INTEGER,
                player2_score INTEGER,
                player2_time_seconds INTEGER,
                player2_finished_at TIMESTAMP,
                status TEXT DEFAULT 'waiting',
                winner_telegram_id INTEGER,
                player1_elo_before INTEGER,
                player1_elo_after INTEGER,
                player2_elo_before INTEGER,
                player2_elo_after INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP,
                notified INTEGER DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_game_battles_subject_status
            ON game_battles(subject, status)
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS game_ratings (
                telegram_id INTEGER NOT NULL,
                subject TEXT NOT NULL,
                elo INTEGER DEFAULT 1000,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                draws INTEGER DEFAULT 0,
                PRIMARY KEY (telegram_id, subject)
            )
        """)

        # ================================================================
        #  KIMYO O'YINI — "bitta baza, ko'p o'yin"
        # ================================================================
        # ASOSIY G'OYA: o'qituvchi SAVOL YOZMAYDI — u faqat MODDA kiritadi
        # (formula, nomi, rangi, cho'kmasi, reaksiyasi). Barcha savol turlari
        # — kartochka, variantli test, moslashtirish, formulani yozish va
        # battle savollari — shu bitta bazadan AVTOMATIK generatsiya qilinadi
        # (chem_questions.py). Shuning uchun 276 ta modda kiritilsa, o'n
        # minglab savol variantlari o'z-o'zidan paydo bo'ladi.
        #
        # Ierarxiya:  Kategoriya  ->  Level  ->  Modda
        #             (Modda nomlari)  (Kislotalar 1)  (HF, HCl, ...)

        # ---------- Kategoriya (o'yin turi bo'yicha bo'lim) ----------
        # is_ready=0 bo'lsa talabaga "TEZ ORADA" ko'rinishida xira ko'rsatiladi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chem_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                subtitle TEXT,
                icon TEXT DEFAULT '🧪',
                is_ready INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ---------- Level (kategoriya ichidagi bosqich) ----------
        # Har levelda odatda 12 ta modda bo'ladi va u 4 bosqichda o'rganiladi.
        # Level yakunlansa (4 bosqich ham) keyingisi ochiladi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chem_levels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES chem_categories(id)
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chem_levels_cat
            ON chem_levels(category_id, sort_order)
        """)

        # ---------- Modda (bazaning o'zagi) ----------
        # Rang maydonlari ("color_pure", "color_solution", "color_precipitate")
        # bo'sh bo'lsa — talabaga "yo'q" deb ko'rsatiladi va o'sha rang
        # savollari generatsiya qilinmaydi. Ya'ni bazani bosqichma-bosqich
        # to'ldirish mumkin: avval formula+nom, keyin ranglar, keyin reaksiyalar.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chem_substances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level_id INTEGER NOT NULL,
                formula TEXT NOT NULL,
                name TEXT NOT NULL,
                historic_name TEXT,
                color_pure TEXT,
                color_solution TEXT,
                color_precipitate TEXT,
                reactions TEXT,
                usage_text TEXT,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (level_id) REFERENCES chem_levels(id)
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chem_substances_level
            ON chem_substances(level_id, sort_order)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chem_substances_formula
            ON chem_substances(formula)
        """)

        # ---------- Bosqich natijasi (level progressi) ----------
        # Har bir (o'quvchi, level, bosqich) uchun ENG YAXSHI natija saqlanadi.
        # stage: 1=O'rganish, 2=Test, 3=Moslashtirish, 4=Yozish
        # stars: 0..3 — aniqlikka qarab (>=90% -> 3, >=70% -> 2, >=50% -> 1)
        # O'rganish bosqichi (1) har doim 3 yulduz beradi: u sinov emas.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chem_stage_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                level_id INTEGER NOT NULL,
                stage INTEGER NOT NULL,
                stars INTEGER DEFAULT 0,
                best_correct INTEGER DEFAULT 0,
                total_questions INTEGER DEFAULT 0,
                attempts INTEGER DEFAULT 0,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(telegram_id, level_id, stage)
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chem_stage_progress_user
            ON chem_stage_progress(telegram_id, level_id)
        """)

        # ---------- Battle (1v1 musobaqa) ----------
        # ASINXRON MODEL: ikkala o'yinchi bir vaqtda onlayn bo'lishi SHART EMAS.
        # 1-o'yinchi savollarga javob beradi va "raqib kutilmoqda" holatida
        # qoladi; keyinroq 2-o'yinchi AYNAN SHU savollarga javob beradi va
        # natijalar taqqoslanadi. Kichik guruh uchun bu yagona ishlaydigan
        # model — aks holda o'quvchi bo'sh xonada abadiy kutib qolardi.
        #
        # Agar 10 daqiqada hech kim qo'shilmasa, fon vazifasi jangni
        # "Kimyobot" bilan yakunlaydi (bot.py -> resolve_stale_chem_battles).
        #
        # `questions` — JSON, TO'G'RI JAVOBLARI BILAN. Mijozga hech qachon
        # to'liq yuborilmaydi: har savol alohida so'raladi va javob serverda
        # tekshiriladi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chem_battles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                mode TEXT DEFAULT 'ranked',
                invite_code TEXT,
                questions TEXT NOT NULL,
                p1_telegram_id INTEGER NOT NULL,
                p1_score INTEGER,
                p1_time_ms INTEGER,
                p1_finished_at TIMESTAMP,
                p2_telegram_id INTEGER,
                p2_score INTEGER,
                p2_time_ms INTEGER,
                p2_finished_at TIMESTAMP,
                is_bot INTEGER DEFAULT 0,
                bot_name TEXT,
                bot_elo INTEGER,
                status TEXT DEFAULT 'waiting',
                winner_telegram_id INTEGER,
                p1_elo_before INTEGER, p1_elo_after INTEGER,
                p2_elo_before INTEGER, p2_elo_after INTEGER,
                notified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chem_battles_wait
            ON chem_battles(category_id, status)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chem_battles_code
            ON chem_battles(invite_code)
        """)

        # ---------- Chempionat ----------
        # FORMAT: saralash -> setka (chiqib ketish) -> final + 3-o'rin.
        #
        #   1) SARALASH — barcha qatnashchilar AYNAN BIR XIL savollarga
        #      javob beradi. Ball (keyin vaqt) bo'yicha saralanadi.
        #   2) SETKA — yuqoridagi yarmi (2 ning darajasiga yaxlitlangan)
        #      o'tadi va juft-juft o'ynaydi. Har juftlik ham bir xil
        #      savollarga javob beradi — bu ASINXRON bo'lishiga imkon beradi
        #      (ikkalasi bir vaqtda onlayn bo'lishi shart emas).
        #   3) FINAL va 3-O'RIN o'yini.
        #
        # is_official=1 — o'qituvchi e'lon qilgan, sovrinli chempionat.
        # is_official=0 — o'quvchi yaratgan, faqat ELO uchun.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chem_tournaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                created_by INTEGER,
                is_official INTEGER DEFAULT 0,
                prize_text TEXT,
                start_mode TEXT DEFAULT 'count',
                start_count INTEGER DEFAULT 8,
                start_at TIMESTAMP,
                status TEXT DEFAULT 'open',
                qual_questions TEXT,
                round_no INTEGER DEFAULT 0,
                winner_telegram_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                finished_at TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chem_tournaments_status
            ON chem_tournaments(status, created_at)
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS chem_tournament_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                telegram_id INTEGER NOT NULL,
                qual_score INTEGER,
                qual_time_ms INTEGER,
                qual_done INTEGER DEFAULT 0,
                seed INTEGER,
                eliminated_round INTEGER,
                place INTEGER,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tournament_id, telegram_id)
            )
        """)

        # Setkadagi bitta juftlik. Ikkala o'yinchi bir xil savollarga
        # javob beradi, shuning uchun `questions` shu yerda saqlanadi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chem_tournament_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                round_no INTEGER NOT NULL,
                slot INTEGER NOT NULL,
                kind TEXT DEFAULT 'bracket',
                questions TEXT NOT NULL,
                p1_telegram_id INTEGER,
                p1_score INTEGER, p1_time_ms INTEGER, p1_done INTEGER DEFAULT 0,
                p2_telegram_id INTEGER,
                p2_score INTEGER, p2_time_ms INTEGER, p2_done INTEGER DEFAULT 0,
                winner_telegram_id INTEGER,
                status TEXT DEFAULT 'playing',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_chem_tmatches
            ON chem_tournament_matches(tournament_id, round_no)
        """)

        # ================================================================
        #  BIOLOGIYA O'YINI
        # ================================================================
        # NEGA KIMYODAN ALOHIDA TIZIM:
        # Kimyoda ma'lumot bir xil shaklda — har modda uchun formula, nom,
        # rang. Shuning uchun 4 ta bosqich hamma levelga bir xil to'g'ri
        # kelardi.
        #
        # Biologiyada esa ma'lumot TURLI SHAKLDA bo'ladi:
        #   - termin va uning vazifasi        (mitoxondriya -> ATP sintezi)
        #   - JARAYON bosqichlari             (mitoz: profaza -> metafaza -> ...)
        #   - TASNIF guruhlari                (prokariot / eukariot)
        #   - RASMDAGI qismlar                (hujayra tuzilishi)
        #
        # Shuning uchun bu yerda bosqichlar RO'YXATI QAT'IY EMAS: har level
        # o'zida qanday ma'lumot bo'lsa, shunga mos o'yinlarni ko'rsatadi.
        # Ketma-ketlik kiritilmagan levelda "Ketma-ketlik" bosqichi umuman
        # paydo bo'lmaydi.

        cur.execute("""
            CREATE TABLE IF NOT EXISTS bio_topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                subtitle TEXT,
                icon TEXT DEFAULT '🧬',
                is_ready INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS bio_levels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (topic_id) REFERENCES bio_topics(id)
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_bio_levels_topic
            ON bio_levels(topic_id, sort_order)
        """)

        # ---------- Termin (bazaning o'zagi) ----------
        # `group_name` — GURUHLASH o'yini uchun savat nomi
        #                (masalan "Prokariot" / "Eukariot").
        # `clues`      — "KIM MEN?" o'yini uchun ipuchalar, JSON ro'yxat.
        #                Umumiydan aniqqa tartibda yoziladi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bio_terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level_id INTEGER NOT NULL,
                term TEXT NOT NULL,
                definition TEXT,
                function_text TEXT,
                group_name TEXT,
                clues TEXT,
                extra_fact TEXT,
                image_url TEXT,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (level_id) REFERENCES bio_levels(id)
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_bio_terms_level
            ON bio_terms(level_id, sort_order)
        """)

        # ---------- Jarayon ketma-ketligi ----------
        # `steps` — JSON ro'yxat, TO'G'RI TARTIBDA saqlanadi. O'quvchiga
        # aralashtirilgan holda ko'rsatiladi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bio_sequences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                steps TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (level_id) REFERENCES bio_levels(id)
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_bio_sequences_level
            ON bio_sequences(level_id, sort_order)
        """)

        # ---------- Rasm bo'yicha belgilash ----------
        # `labels` — JSON: [{"name": "yadro", "x": 42, "y": 55}, ...]
        # x, y — rasmning FOIZ koordinatalari (0-100), shuning uchun rasm
        # istalgan o'lchamda ko'rsatilsa ham nuqtalar joyida qoladi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bio_image_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                image_url TEXT NOT NULL,
                labels TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (level_id) REFERENCES bio_levels(id)
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_bio_image_tasks_level
            ON bio_image_tasks(level_id, sort_order)
        """)

        # ---------- Bosqich natijasi ----------
        # `stage_key` — matn (kimyodagi raqamdan farqli), chunki bosqichlar
        # to'plami levelga qarab o'zgaradi: "learn", "test", "match",
        # "sequence", "group", "whoami", "image".
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bio_stage_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                level_id INTEGER NOT NULL,
                stage_key TEXT NOT NULL,
                stars INTEGER DEFAULT 0,
                best_correct INTEGER DEFAULT 0,
                total_questions INTEGER DEFAULT 0,
                attempts INTEGER DEFAULT 0,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(telegram_id, level_id, stage_key)
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_bio_stage_progress_user
            ON bio_stage_progress(telegram_id, level_id)
        """)

        # ---------- Boshlang'ich mavzular (bir marta) ----------
        if not _flag_done("bio_topics_seeded"):
            for _key, _title, _sub, _icon, _ready, _ord in (
                ("hujayra", "Hujayra va organoidlar", "Tuzilishi va vazifasi", "🔬", 1, 1),
                ("organ_tizimlari", "Odam organ tizimlari", "Hazm, nafas, qon aylanish...", "🫀", 0, 2),
                ("genetika", "Genetika va bo'linish", "Mitoz, meyoz, DNK, oqsil sintezi", "🧬", 0, 3),
                ("botanika_zoologiya", "Botanika va zoologiya", "O'simlik va hayvonlar olami", "🌿", 0, 4),
            ):
                cur.execute("SELECT id FROM bio_topics WHERE key = ?", (_key,))
                if cur.fetchone() is None:
                    cur.execute("""
                        INSERT INTO bio_topics (key, title, subtitle, icon, is_ready, sort_order)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (_key, _title, _sub, _icon, _ready, _ord))
            conn.commit()
            _set_flag("bio_topics_seeded")

        # ---------- ELO reytingi ----------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chem_ratings (
                telegram_id INTEGER PRIMARY KEY,
                elo INTEGER DEFAULT 1000,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                draws INTEGER DEFAULT 0,
                current_streak INTEGER DEFAULT 0,
                best_streak INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ---------- Kimyo o'yini: boshlang'ich kategoriyalar ----------
        # BIR MARTA yaratiladi. Keyin o'qituvchi ularni tahrirlaydi yoki
        # o'chiradi — qayta deploy'da tiklanib qolmaydi (fan kartalaridagi
        # xatoning aynan takrorlanmasligi uchun shu qoida saqlanadi).
        #
        # is_ready=0 — talabaga "TEZ ORADA" ko'rinishida chiqadi. O'qituvchi
        # moddalarni to'ldirib bo'lgach, uni admin panelidan yoqadi.
        if not _flag_done("chem_categories_seeded"):
            for _key, _title, _sub, _icon, _ready, _ord in (
                ("modda_nomlari", "Modda nomlari", "Formula ↔ nom", "🧪", 1, 1),
                ("moddalar_rangi", "Moddalar rangi", "Sof holda va eritmada", "🎨", 0, 2),
                ("chokmalar", "Cho'kmalar", "Cho'kma va uning rangi", "💧", 0, 3),
                ("reaksiyalar", "Reaksiyalar", "Reaksiya tenglamalari", "⚗️", 0, 4),
            ):
                cur.execute("SELECT id FROM chem_categories WHERE key = ?", (_key,))
                if cur.fetchone() is None:
                    cur.execute("""
                        INSERT INTO chem_categories (key, title, subtitle, icon, is_ready, sort_order)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (_key, _title, _sub, _icon, _ready, _ord))
            conn.commit()
            _set_flag("chem_categories_seeded")

        # ================================================================
        #  PULLIK GURUH ORQALI AVTOMATIK KIRISH
        # ================================================================
        # MUAMMO: o'qituvchi har bir o'quvchini qo'lda kursga biriktirishga
        # majbur edi. O'quvchi ko'p bo'lganda bu real emas.
        #
        # YECHIM: o'quvchining Telegram ID si o'qituvchining YOPIQ (pullik)
        # guruhida bor-yo'qligi avtomatik tekshiriladi. Guruhda bo'lsa —
        # unga bog'langan kurslar va testlar o'z-o'zidan ochiladi.
        #
        # MUHIM: eski usul (qo'lda biriktirish) SAQLANADI. Kirish ikkalasidan
        # BIRI bo'lsa beriladi — shuning uchun o'qituvchi istisno holatlarda
        # (masalan guruhga qo'shilmagan, lekin to'lagan o'quvchiga) qo'lda
        # ham bera oladi.

        cur.execute("""
            CREATE TABLE IF NOT EXISTS access_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                chat_id TEXT NOT NULL,
                invite_link TEXT,
                is_active INTEGER DEFAULT 1,
                last_error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Qaysi kontent qaysi guruhga bog'langan.
        # content_type: 'course' | 'test_stage'
        # Bitta kontentni bir nechta guruhga bog'lash mumkin — masalan
        # "Kimyo pullik" va "Umumiy VIP" guruhlaridan BIRIDA bo'lsa yetarli.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS content_access_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_type TEXT NOT NULL,
                content_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(content_type, content_id, group_id)
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_content_access_links
            ON content_access_links(content_type, content_id)
        """)

        # A'zolik KESHI.
        # NEGA KESH KERAK: har bir dars ochilganda Telegram API ga so'rov
        # yuborish ilovani sekinlashtiradi va Telegram limitiga urib qoladi.
        # Shuning uchun natija saqlanadi va TTL (10 daqiqa) o'tgach yangilanadi.
        # Shu sababli guruhdan chiqib ketgan o'quvchi ~10 daqiqada qulflanadi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_membership_cache (
                telegram_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                is_member INTEGER DEFAULT 0,
                status TEXT,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (telegram_id, group_id)
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_membership_checked
            ON group_membership_cache(checked_at)
        """)

        # ---------- Sertifikatlar (kurs 100% tugallanganda) ----------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS certificates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                certificate_number TEXT UNIQUE NOT NULL,
                issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(telegram_id, course_id)
            )
        """)

        # ---------- Yutuq nishonlari (achievements) ----------
        # Nishon TA'RIFLARI (nomi, tavsifi, sharti) kodda — ACHIEVEMENT_DEFS
        # ro'yxatida — saqlanadi (hozircha admin panelidan tahrirlanmaydi,
        # eng muhim ~10 ta standart yutuq bilan boshlaymiz). Bu jadval
        # faqat KIM QACHON qaysi nishonni QO'LGA KIRITGANINI saqlaydi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                achievement_key TEXT NOT NULL,
                earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(telegram_id, achievement_key)
            )
        """)

        # ---------- Kitoblar do'koni (bosma kitoblar) ----------
        # E'TIBOR: bu "courses" jadvalidagi resource_type='book' (RAQAMLI
        # o'qish kontenti — bo'lim/dars strukturasi bilan) dan BUTUNLAY
        # ALOHIDA tushuncha — bu yerda BOSMA (pochta orqali yetkaziladigan)
        # kitoblar sotiladi. Hozircha to'lov tizimi (Payme/Click) ULANMAGAN
        # — "Xarid qilish" tugmasi shunchaki talabani shu kitobga biriktirilgan
        # (yoki bo'sh bo'lsa umumiy) admin Telegram kontaktiga olib boradi,
        # xarid o'sha yerda qo'lda kelishiladi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS book_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                subtitle TEXT DEFAULT '',
                description TEXT DEFAULT '',
                category TEXT DEFAULT '',
                price INTEGER DEFAULT 0,
                image_url TEXT,
                badge_text TEXT DEFAULT '',
                is_bundle INTEGER DEFAULT 0,
                contact_username TEXT DEFAULT '',
                order_num INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # "Video yechim" bog'lanishi — kitob mahsuloti (bosma) bilan
        # courses jadvalidagi biror kursni ("bo'lim") bog'lash uchun.
        # Talaba do'konda "Video yechim" tugmasini bossa, aynan shu
        # kursning ichiga (miniappda) olib boriladi. Eski bazalarda bu ustun
        # yo'q bo'lgani uchun ALTER TABLE orqali (xatoni jimgina o'tkazib
        # yuborib) qo'shamiz.
        try:
            cur.execute("ALTER TABLE book_products ADD COLUMN linked_course_id INTEGER")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud — muammo emas

        # FAQ / Yordam bo'limi — tez-tez so'raladigan savol-javoblar, admin
        # paneldan to'liq boshqariladi (qo'shish/tahrirlash/o'chirish/tartib).
        cur.execute("""
            CREATE TABLE IF NOT EXISTS faq_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                order_num INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # "Natijalar" — o'quvchilarning kurs/dars haqidagi fikri va
        # sertifikat (masalan Milliy sertifikat, DTM) natijalari. Bu — reyting
        # (leaderboard)dan BUTUNLAY ALOHIDA, admin qo'lda to'ldiradigan
        # "muvaffaqiyat hikoyalari" lentasi (Kelajak Mediklari botidagi
        # "Natijalar" bo'limi kabi). Reyting endi faqat bosh sahifadagi
        # "🏆 Reyting" kartasi orqali ochiladi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS student_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                subject TEXT DEFAULT '',
                image_url TEXT,
                result_text TEXT DEFAULT '',
                feedback_text TEXT DEFAULT '',
                order_num INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Haftalik shaxsiy reyting xabari (nazorat testi + vazifa, 50/50)
        # bir hafta ichida bir martadan ortiq yuborilmasligi uchun.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS weekly_rank_notifications (
                telegram_id INTEGER NOT NULL,
                sent_year INTEGER NOT NULL,
                sent_week INTEGER NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (telegram_id, sent_year, sent_week)
            )
        """)

        # Pullik guruh a'zolariga kunlik (kechagi kun) natija xabari —
        # har foydalanuvchi uchun oxirgi yuborilgan sana saqlanadi, shu
        # orqali "har 2 kunda bir marta" qoidasi ta'minlanadi.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS paid_group_daily_notifications (
                telegram_id INTEGER PRIMARY KEY,
                last_sent_date TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
    print("Baza tayyor (v5 — DTM simulyatori bilan): users, courses, paragraphs, lessons, "
          "lesson_progress, enrollments, referrals, tests, simulators.")


# ---------- DASHBOARD CARDS (bosh sahifa kartalari) ----------

def get_dashboard_cards(only_active: bool = False):
    """Bosh sahifadagi 6 ta katakli menyu kartalarini tartib bo'yicha
    qaytaradi. only_active=True bo'lsa, faqat admin "faol" deb belgilagan
    kartalar qaytadi (student-facing Mini App shu variantdan foydalanadi)."""
    with get_connection() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM dashboard_cards"
        if only_active:
            query += " WHERE is_active = 1"
        query += " ORDER BY order_num ASC, card_key ASC"
        cur.execute(query)
        return [dict(row) for row in cur.fetchall()]


def update_dashboard_card(card_key: str, data: dict):
    """Bitta kartaning sarlavha/teg/belgi/faollik/tartib qiymatlarini
    yangilaydi. card_key o'zi o'zgarmaydi (jadvalning asosiy kaliti)."""
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        allowed = ["title", "subtitle", "icon", "is_active", "order_num"]
        for key in allowed:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        if fields:
            values.append(card_key)
            cur.execute(f"UPDATE dashboard_cards SET {', '.join(fields)} WHERE card_key = ?", values)
            conn.commit()


# ---------- YUTUQ NISHONLARI (achievements) ----------
#
# Har bir nishon: (key, title, description, icon, shart-funksiya). Shart-
# funksiya foydalanuvchi statistikasi (dict) qabul qilib, True/False
# qaytaradi. check_and_award_achievements() har safar muhim harakatdan
# keyin (dars ko'rish, test tugatish, Battle g'alaba, referal tasdiqlanishi)
# chaqiriladi — statistikani qayta hisoblab, hali berilmagan, LEKIN endi
# shartga mos nishonlarni avtomatik beradi.

ACHIEVEMENT_DEFS = [
    {"key": "first_lesson", "title": "Birinchi qadam", "description": "Birinchi darsni tomosha qildingiz",
     "icon": "🎬", "check": lambda s: s["lessons_watched"] >= 1},
    {"key": "lessons_10", "title": "Bilim ishqibozi", "description": "10 ta darsni tomosha qildingiz",
     "icon": "📚", "check": lambda s: s["lessons_watched"] >= 10},
    {"key": "lessons_50", "title": "Bilim changali", "description": "50 ta darsni tomosha qildingiz",
     "icon": "🎓", "check": lambda s: s["lessons_watched"] >= 50},
    {"key": "first_test", "title": "Birinchi sinov", "description": "Birinchi testni yakunladingiz",
     "icon": "📝", "check": lambda s: s["tests_finished"] >= 1},
    {"key": "tests_10", "title": "Test ustasi", "description": "10 ta testni yakunladingiz",
     "icon": "🏅", "check": lambda s: s["tests_finished"] >= 10},
    {"key": "perfect_score", "title": "Mukammal natija", "description": "Biror testda 100% natija ko'rsatdingiz",
     "icon": "💯", "check": lambda s: s["has_perfect_score"]},
    {"key": "control_test_done", "title": "Nazoratdan o'tdi", "description": "Birinchi nazorat testini topshirdingiz",
     "icon": "🎯", "check": lambda s: s["control_tests_finished"] >= 1},
    {"key": "first_battle_win", "title": "Jangchi", "description": "Birinchi Battle g'alabangiz",
     "icon": "⚔️", "check": lambda s: s["battle_wins"] >= 1},
    {"key": "battle_wins_10", "title": "Chempion", "description": "10 ta Battle g'alaba qozondingiz",
     "icon": "🏆", "check": lambda s: s["battle_wins"] >= 10},
    {"key": "coins_50", "title": "Tejamkor", "description": "50 ta coin to'pladingiz",
     "icon": "🪙", "check": lambda s: s["coins"] >= 50},
    {"key": "referrals_5", "title": "Do'stlar yetakchisi", "description": "5 ta do'stingizni taklif qildingiz",
     "icon": "🎁", "check": lambda s: s["confirmed_referrals"] >= 5},
    {"key": "streak_3", "title": "Qizigan boshlanish", "description": "3 kun ketma-ket faol bo'ldingiz",
     "icon": "🔥", "check": lambda s: s["longest_streak"] >= 3},
    {"key": "streak_7", "title": "Haftalik intizom", "description": "7 kun ketma-ket faol bo'ldingiz",
     "icon": "🔥", "check": lambda s: s["longest_streak"] >= 7},
    {"key": "streak_30", "title": "Temir intizom", "description": "30 kun ketma-ket faol bo'ldingiz",
     "icon": "🔥", "check": lambda s: s["longest_streak"] >= 30},
]


def _gather_achievement_stats(telegram_id: int) -> dict:
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) as c FROM lesson_progress WHERE telegram_id = ?", (telegram_id,))
        lessons_watched = cur.fetchone()["c"]

        cur.execute("""
            SELECT COUNT(*) as c FROM test_attempts ta JOIN tests t ON t.id = ta.test_id
            WHERE ta.telegram_id = ? AND ta.finished_at IS NOT NULL AND t.is_control_test = 0
        """, (telegram_id,))
        tests_finished = cur.fetchone()["c"]

        cur.execute("""
            SELECT COUNT(*) as c FROM test_attempts ta JOIN tests t ON t.id = ta.test_id
            WHERE ta.telegram_id = ? AND ta.finished_at IS NOT NULL AND t.is_control_test = 1
        """, (telegram_id,))
        control_tests_finished = cur.fetchone()["c"]

        cur.execute("""
            SELECT COUNT(*) as c FROM test_attempts
            WHERE telegram_id = ? AND finished_at IS NOT NULL AND total_questions > 0 AND score = total_questions
        """, (telegram_id,))
        has_perfect_score = cur.fetchone()["c"] > 0

        cur.execute("SELECT COALESCE(SUM(wins), 0) as w FROM game_ratings WHERE telegram_id = ?", (telegram_id,))
        battle_wins = cur.fetchone()["w"]

        cur.execute("SELECT coins, longest_streak FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cur.fetchone()
        coins = row["coins"] if row else 0
        longest_streak = (row["longest_streak"] or 0) if row else 0

        cur.execute("SELECT COUNT(*) as c FROM referrals WHERE referrer_telegram_id = ? AND confirmed = 1", (telegram_id,))
        confirmed_referrals = cur.fetchone()["c"]

        return {
            "lessons_watched": lessons_watched,
            "tests_finished": tests_finished,
            "control_tests_finished": control_tests_finished,
            "has_perfect_score": has_perfect_score,
            "battle_wins": battle_wins,
            "coins": coins,
            "confirmed_referrals": confirmed_referrals,
            "longest_streak": longest_streak,
        }


def check_and_award_achievements(telegram_id: int):
    """Statistikani qayta hisoblab, hali berilmagan lekin endi shartga mos
    nishonlarni beradi. Natija: YANGI berilgan nishonlar ro'yxati (bo'sh
    bo'lishi ham mumkin)."""
    stats = _gather_achievement_stats(telegram_id)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT achievement_key FROM user_achievements WHERE telegram_id = ?", (telegram_id,))
        already_earned = {r["achievement_key"] for r in cur.fetchall()}

        newly_earned = []
        for ach in ACHIEVEMENT_DEFS:
            if ach["key"] in already_earned:
                continue
            try:
                qualifies = ach["check"](stats)
            except Exception:
                qualifies = False
            if qualifies:
                cur.execute(
                    "INSERT OR IGNORE INTO user_achievements (telegram_id, achievement_key) VALUES (?, ?)",
                    (telegram_id, ach["key"])
                )
                newly_earned.append(ach)
        if newly_earned:
            conn.commit()
        return newly_earned


def get_user_achievements(telegram_id: int):
    """Barcha nishonlarni (qo'lga kiritilgan yoki yo'q) qaytaradi — Profil
    ekranida to'liq "nishonlar devori" ko'rsatish uchun."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT achievement_key, earned_at FROM user_achievements WHERE telegram_id = ?", (telegram_id,))
        earned_map = {r["achievement_key"]: r["earned_at"] for r in cur.fetchall()}

    result = []
    for ach in ACHIEVEMENT_DEFS:
        result.append({
            "key": ach["key"], "title": ach["title"], "description": ach["description"], "icon": ach["icon"],
            "earned": ach["key"] in earned_map,
            "earned_at": earned_map.get(ach["key"]),
        })
    return result


# ---------- USERS ----------

def get_or_create_user(telegram_id: int, first_name: str, username: str = None, referred_by: int = None):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cur.fetchone()
        if user is None:
            cur.execute(
                "INSERT INTO users (telegram_id, first_name, username, referred_by) VALUES (?, ?, ?, ?)",
                (telegram_id, first_name, username, referred_by)
            )
            conn.commit()
            cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            user = cur.fetchone()
        return dict(user)


def set_user_subscribed(telegram_id: int, value: bool = True):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET is_subscribed = ? WHERE telegram_id = ?", (1 if value else 0, telegram_id))
        conn.commit()


def record_daily_activity(telegram_id: int) -> dict:
    """O'quvchi biror "faol" harakat qilganda (dars ko'rish, test/simulyator
    yakunlash, o'yin o'ynash) chaqiriladi va kunlik "streak"ni yangilaydi:

    - Bugun allaqachon faol bo'lgan bo'lsa — hech narsa o'zgarmaydi.
    - Kecha faol bo'lgan bo'lsa — streak +1 (ketma-ketlik davom etadi).
    - Aks holda (uzilish yoki birinchi marta) — streak 1 dan boshlanadi.

    Sana UTC bo'yicha ('YYYY-MM-DD') solishtiriladi — bazadagi boshqa
    vaqt hisoblari (masalan coin_history) bilan bir xil andozada.
    """
    today = datetime.datetime.utcnow().date()
    today_str = today.isoformat()
    yesterday_str = (today - datetime.timedelta(days=1)).isoformat()

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT current_streak, longest_streak, last_activity_date FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        row = cur.fetchone()
        if row is None:
            return {"current_streak": 0, "longest_streak": 0}

        current_streak = row["current_streak"] or 0
        longest_streak = row["longest_streak"] or 0
        last_date = row["last_activity_date"]

        if last_date == today_str:
            pass  # bugun allaqachon hisoblangan
        elif last_date == yesterday_str:
            current_streak += 1
        else:
            current_streak = 1

        longest_streak = max(longest_streak, current_streak)

        cur.execute(
            "UPDATE users SET current_streak = ?, longest_streak = ?, last_activity_date = ? WHERE telegram_id = ?",
            (current_streak, longest_streak, today_str, telegram_id)
        )
        conn.commit()

    return {"current_streak": current_streak, "longest_streak": longest_streak}


def search_users(query: str, limit: int = 20):
    """Admin panelda nazorat testiga talaba tayinlash uchun foydalanuvchi
    qidiradi — ism, username yoki Telegram ID bo'yicha. Bo'sh so'rovda eng
    so'nggi ro'yxatdan o'tganlarni qaytaradi (ro'yxatni boshlash uchun qulay)."""
    query = (query or "").strip()
    with get_connection() as conn:
        cur = conn.cursor()
        if not query:
            cur.execute(
                "SELECT telegram_id, first_name, username FROM users ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            return [dict(r) for r in cur.fetchall()]

        if query.isdigit():
            cur.execute(
                """SELECT telegram_id, first_name, username FROM users
                   WHERE telegram_id = ? OR CAST(telegram_id AS TEXT) LIKE ?
                   ORDER BY id DESC LIMIT ?""",
                (int(query), f"%{query}%", limit)
            )
        else:
            like = f"%{query}%"
            cur.execute(
                """SELECT telegram_id, first_name, username FROM users
                   WHERE first_name LIKE ? OR username LIKE ?
                   ORDER BY id DESC LIMIT ?""",
                (like, like, limit)
            )
        return [dict(r) for r in cur.fetchall()]


def add_coins(telegram_id: int, amount: int = 1):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET coins = coins + ? WHERE telegram_id = ?", (amount, telegram_id))
        # Har bir coin berilishini VAQTI bilan birga alohida yozib boramiz
        # ("umumiy hisob"dan farqli) — shu orqali Reyting bo'limida
        # "Haftalik"/"Oylik" kabi DAVR bo'yicha reyting hisoblash mumkin
        # bo'ladi (users.coins faqat "Butun davr" umumiy yig'indisini bilar
        # edi, qachon berilganini bilmasdi).
        cur.execute(
            "INSERT INTO coin_history (telegram_id, amount) VALUES (?, ?)",
            (telegram_id, amount)
        )
        conn.commit()


# ---------- REFERRALS ----------

def create_pending_referral(referrer_id: int, referred_id: int):
    if referrer_id == referred_id:
        return
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM referrals WHERE referred_telegram_id = ?", (referred_id,))
        if cur.fetchone() is None:
            cur.execute(
                "INSERT INTO referrals (referrer_telegram_id, referred_telegram_id, confirmed) VALUES (?, ?, 0)",
                (referrer_id, referred_id)
            )
            conn.commit()


def confirm_referral(referred_id: int):
    newly_confirmed = False
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT referrer_telegram_id, confirmed FROM referrals WHERE referred_telegram_id = ?", (referred_id,))
        row = cur.fetchone()
        if row is None:
            return None
        if row["confirmed"] == 0:
            cur.execute("UPDATE referrals SET confirmed = 1 WHERE referred_telegram_id = ?", (referred_id,))
            conn.commit()
            newly_confirmed = True
        referrer_id = row["referrer_telegram_id"]

    if newly_confirmed:
        check_and_award_achievements(referrer_id)
    return referrer_id


def get_confirmed_referral_count(telegram_id: int) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM referrals WHERE referrer_telegram_id = ? AND confirmed = 1", (telegram_id,))
        return cur.fetchone()["c"]


def get_referral_progress(telegram_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT r.referred_telegram_id, r.confirmed, u.first_name
            FROM referrals r LEFT JOIN users u ON u.telegram_id = r.referred_telegram_id
            WHERE r.referrer_telegram_id = ? ORDER BY r.created_at DESC
        """, (telegram_id,))
        return [dict(r) for r in cur.fetchall()]


# ---------- COURSES ----------

def get_all_courses(resource_type: str = None, only_active: bool = True):
    with get_connection() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM courses WHERE 1=1"
        params = []
        if resource_type:
            query += " AND resource_type = ?"
            params.append(resource_type)
        if only_active:
            query += " AND is_active = 1"
        query += " ORDER BY order_num ASC, id ASC"
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def get_course(course_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def _normalize_lessons_override(value):
    """Bo'sh/0/None -> None (avtomatik hisoblanadi); aks holda butun son."""
    if value in (None, "", 0, "0"):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def create_course(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO courses (title, subject, resource_type, description, is_free,
                required_referrals, price, duration_days, duration_text, students_count,
                thumbnail_emoji, order_num, is_active, course_type, lessons_count_override)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("title", ""), data.get("subject", ""), data.get("resource_type", "course"),
            data.get("description", ""), int(data.get("is_free", 1)),
            int(data.get("required_referrals", 0)), int(data.get("price", 0)),
            data.get("duration_days") or None, data.get("duration_text", ""),
            int(data.get("students_count", 0)), data.get("thumbnail_emoji", "📘"),
            int(data.get("order_num", 0)), int(data.get("is_active", 1)),
            data.get("course_type") or "mustaqil",
            _normalize_lessons_override(data.get("lessons_count_override"))
        ))
        conn.commit()
        return cur.lastrowid


def update_course(course_id: int, data: dict):
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        allowed = ["title", "subject", "resource_type", "description", "is_free",
                   "required_referrals", "price", "duration_days", "duration_text",
                   "students_count", "thumbnail_emoji", "order_num", "is_active", "course_type"]
        for key in allowed:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key] if data[key] != "" else None)
        if "lessons_count_override" in data:
            fields.append("lessons_count_override = ?")
            values.append(_normalize_lessons_override(data["lessons_count_override"]))
        if fields:
            values.append(course_id)
            cur.execute(f"UPDATE courses SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()


def delete_course(course_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM courses WHERE id = ?", (course_id,))
        conn.commit()


# ---------- KITOBLAR DO'KONI (bosma kitoblar, courses'dan alohida) ----------

def get_book_products(category: str = None, only_active: bool = True):
    with get_connection() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM book_products WHERE 1=1"
        params = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if only_active:
            query += " AND is_active = 1"
        query += " ORDER BY order_num ASC, id DESC"
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def get_book_product(product_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM book_products WHERE id = ?", (product_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_book_product(data: dict) -> int:
    linked_course_id = data.get("linked_course_id")
    linked_course_id = int(linked_course_id) if linked_course_id not in (None, "", 0, "0") else None
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO book_products (title, subtitle, description, category, price,
                image_url, badge_text, is_bundle, contact_username, order_num, is_active,
                linked_course_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("title", ""), data.get("subtitle", ""), data.get("description", ""),
            data.get("category", ""), int(data.get("price", 0) or 0),
            data.get("image_url") or None, data.get("badge_text", ""),
            int(data.get("is_bundle", 0)), data.get("contact_username", ""),
            int(data.get("order_num", 0)), int(data.get("is_active", 1)),
            linked_course_id
        ))
        conn.commit()
        return cur.lastrowid


def update_book_product(product_id: int, data: dict):
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        allowed = ["title", "subtitle", "description", "category", "price", "image_url",
                   "badge_text", "is_bundle", "contact_username", "order_num", "is_active",
                   "linked_course_id"]
        for key in allowed:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key] if data[key] != "" else ("" if key in ("subtitle", "description", "category", "badge_text", "contact_username") else None))
        if fields:
            values.append(product_id)
            cur.execute(f"UPDATE book_products SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()


def delete_book_product(product_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM book_products WHERE id = ?", (product_id,))
        conn.commit()


# ---------- FAQ / YORDAM BO'LIMI ----------

def get_faq_items(only_active: bool = True):
    with get_connection() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM faq_items"
        if only_active:
            query += " WHERE is_active = 1"
        query += " ORDER BY order_num ASC, id ASC"
        cur.execute(query)
        return [dict(row) for row in cur.fetchall()]


def get_faq_item(faq_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM faq_items WHERE id = ?", (faq_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_faq_item(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO faq_items (question, answer, order_num, is_active)
            VALUES (?, ?, ?, ?)
        """, (
            data.get("question", ""), data.get("answer", ""),
            int(data.get("order_num", 0)), int(data.get("is_active", 1))
        ))
        conn.commit()
        return cur.lastrowid


def update_faq_item(faq_id: int, data: dict):
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        allowed = ["question", "answer", "order_num", "is_active"]
        for key in allowed:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        if fields:
            values.append(faq_id)
            cur.execute(f"UPDATE faq_items SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()


def delete_faq_item(faq_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM faq_items WHERE id = ?", (faq_id,))
        conn.commit()


# ---------- NATIJALAR (o'quvchi fikri + sertifikat natijalari) ----------

def get_student_results(only_active: bool = True):
    with get_connection() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM student_results"
        if only_active:
            query += " WHERE is_active = 1"
        query += " ORDER BY order_num ASC, id DESC"
        cur.execute(query)
        return [dict(row) for row in cur.fetchall()]


def get_student_result(result_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM student_results WHERE id = ?", (result_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_student_result(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO student_results (student_name, subject, image_url, result_text,
                feedback_text, order_num, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("student_name", ""), data.get("subject", ""),
            data.get("image_url") or None, data.get("result_text", ""),
            data.get("feedback_text", ""),
            int(data.get("order_num", 0)), int(data.get("is_active", 1))
        ))
        conn.commit()
        return cur.lastrowid


def update_student_result(result_id: int, data: dict):
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        allowed = ["student_name", "subject", "image_url", "result_text",
                   "feedback_text", "order_num", "is_active"]
        for key in allowed:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        if fields:
            values.append(result_id)
            cur.execute(f"UPDATE student_results SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()


def delete_student_result(result_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM student_results WHERE id = ?", (result_id,))
        conn.commit()


# ---------- PARAGRAPHS ----------

def get_paragraphs(course_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM paragraphs WHERE course_id = ? ORDER BY order_num ASC, id ASC", (course_id,))
        return [dict(r) for r in cur.fetchall()]


def get_paragraph(paragraph_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM paragraphs WHERE id = ?", (paragraph_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_paragraph(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO paragraphs (course_id, title, order_num, topic_count) VALUES (?, ?, ?, ?)", (
            int(data["course_id"]), data.get("title", ""), int(data.get("order_num", 0)),
            int(data.get("topic_count", 0) or 0)
        ))
        conn.commit()
        return cur.lastrowid


def update_paragraph(paragraph_id: int, data: dict):
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        for key in ["title", "order_num", "topic_count"]:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        if fields:
            values.append(paragraph_id)
            cur.execute(f"UPDATE paragraphs SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()


def delete_paragraph(paragraph_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM paragraphs WHERE id = ?", (paragraph_id,))
        conn.commit()


# ---------- KURS NARX PAKETLARI ----------

def get_pricing_tiers(course_id: int, only_active: bool = True):
    with get_connection() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM course_pricing_tiers WHERE course_id = ?"
        params = [course_id]
        if only_active:
            query += " AND is_active = 1"
        query += " ORDER BY order_num ASC, id ASC"
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]


def create_pricing_tier(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO course_pricing_tiers (course_id, label, price, original_price, duration_text, order_num, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            int(data["course_id"]), data.get("label", ""), int(data.get("price", 0) or 0),
            int(data["original_price"]) if data.get("original_price") else None,
            data.get("duration_text", ""), int(data.get("order_num", 0)), int(data.get("is_active", 1))
        ))
        conn.commit()
        return cur.lastrowid


def update_pricing_tier(tier_id: int, data: dict):
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        for key in ["label", "price", "original_price", "duration_text", "order_num", "is_active"]:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key] if data[key] != "" else None)
        if fields:
            values.append(tier_id)
            cur.execute(f"UPDATE course_pricing_tiers SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()


def delete_pricing_tier(tier_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM course_pricing_tiers WHERE id = ?", (tier_id,))
        conn.commit()


# ---------- KURS BO'LIMLARI (KATEGORIYALARI) ----------
# Admin o'zi istalgan nomda bo'lim yaratadi (masalan "Nazoratli", "Mustaqil",
# "Bepul kurs") va har bir kursni bir nechta bo'limga bir vaqtda biriktira
# oladi (course_category_links — ko'p-ko'pga jadval).

def get_course_categories(only_active: bool = True):
    with get_connection() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM course_categories WHERE 1=1"
        params = []
        if only_active:
            query += " AND is_active = 1"
        query += " ORDER BY order_num ASC, id ASC"
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]


def get_course_category(category_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM course_categories WHERE id = ?", (category_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_course_category(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO course_categories (title, subtitle, icon, order_num, is_active)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data.get("title", ""), data.get("subtitle", ""), data.get("icon") or "📁",
            int(data.get("order_num", 0)), int(data.get("is_active", 1))
        ))
        conn.commit()
        return cur.lastrowid


def update_course_category(category_id: int, data: dict):
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        for key in ["title", "subtitle", "icon", "order_num", "is_active"]:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        if fields:
            values.append(category_id)
            cur.execute(f"UPDATE course_categories SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()


def delete_course_category(category_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM course_categories WHERE id = ?", (category_id,))
        conn.commit()


def get_categories_for_course(course_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT cc.* FROM course_categories cc
            JOIN course_category_links l ON l.category_id = cc.id
            WHERE l.course_id = ?
            ORDER BY cc.order_num ASC, cc.id ASC
        """, (course_id,))
        return [dict(r) for r in cur.fetchall()]


def get_category_ids_for_courses(course_ids: list):
    """Bir nechta kurs uchun category_id'lar map'ini (course_id -> [id,...]) qaytaradi — N+1 so'rovlardan qochish uchun."""
    if not course_ids:
        return {}
    with get_connection() as conn:
        cur = conn.cursor()
        placeholders = ",".join("?" for _ in course_ids)
        cur.execute(f"SELECT course_id, category_id FROM course_category_links WHERE course_id IN ({placeholders})", course_ids)
        result = {cid: [] for cid in course_ids}
        for row in cur.fetchall():
            result[row["course_id"]].append(row["category_id"])
        return result


def set_course_categories(course_id: int, category_ids: list):
    """Kursning bo'lim bog'lanishlarini berilgan ro'yxat bilan TO'LIQ almashtiradi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM course_category_links WHERE course_id = ?", (course_id,))
        for cid in category_ids or []:
            try:
                cur.execute(
                    "INSERT OR IGNORE INTO course_category_links (course_id, category_id) VALUES (?, ?)",
                    (course_id, int(cid))
                )
            except (ValueError, TypeError):
                pass
        conn.commit()


# ---------- LESSONS ----------

def get_lessons(paragraph_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM lessons WHERE paragraph_id = ? ORDER BY order_num ASC, id ASC", (paragraph_id,))
        return [dict(r) for r in cur.fetchall()]


def get_lesson(lesson_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_lesson(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO lessons (paragraph_id, title, video_url, image_url, description, order_num, is_free_preview)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            int(data["paragraph_id"]), data.get("title", ""), data.get("video_url", ""),
            data.get("image_url", ""), data.get("description", ""), int(data.get("order_num", 0)),
            int(data.get("is_free_preview", 0))
        ))
        conn.commit()
        return cur.lastrowid


def update_lesson(lesson_id: int, data: dict):
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        for key in ["title", "video_url", "image_url", "description", "order_num", "is_free_preview"]:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        if fields:
            values.append(lesson_id)
            cur.execute(f"UPDATE lessons SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()


def delete_lesson(lesson_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))
        conn.commit()


def count_course_lessons(course_id: int) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as c FROM lessons l
            JOIN paragraphs p ON p.id = l.paragraph_id
            WHERE p.course_id = ?
        """, (course_id,))
        return cur.fetchone()["c"]


def count_free_preview_lessons(course_id: int) -> int:
    """Kurs qulflangan bo'lsa ham talaba ro'yxatdan o'tmasdan ko'ra oladigan
    "bepul namuna" darslar sonini qaytaradi (kurs kartasidagi "N BEPUL" belgisi uchun)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as c FROM lessons l
            JOIN paragraphs p ON p.id = l.paragraph_id
            WHERE p.course_id = ? AND l.is_free_preview = 1
        """, (course_id,))
        return cur.fetchone()["c"]


def get_free_preview_lesson_ids(course_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT l.id as id FROM lessons l
            JOIN paragraphs p ON p.id = l.paragraph_id
            WHERE p.course_id = ? AND l.is_free_preview = 1
        """, (course_id,))
        return {r["id"] for r in cur.fetchall()}


def count_paragraph_lessons(paragraph_id: int) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM lessons WHERE paragraph_id = ?", (paragraph_id,))
        return cur.fetchone()["c"]


# ---------- LESSON PROGRESS / COINS ----------

def mark_lesson_watched(telegram_id: int, lesson_id: int) -> bool:
    """Darsni 'ko'rildi' deb belgilaydi va agar birinchi marta bo'lsa 1 coin beradi.
    Coin berilgan bo'lsa True, avval berilgan bo'lsa False qaytaradi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT coin_awarded FROM lesson_progress WHERE telegram_id = ? AND lesson_id = ?",
                    (telegram_id, lesson_id))
        row = cur.fetchone()
        if row is not None:
            return False  # allaqachon ko'rilgan, qayta coin berilmaydi

        cur.execute("INSERT INTO lesson_progress (telegram_id, lesson_id, coin_awarded) VALUES (?, ?, 1)",
                    (telegram_id, lesson_id))
        conn.commit()

    add_coins(telegram_id, 1)  # oldingi 'with' bloki yopilgach — pooldan bo'sh ulanish oladi
    record_daily_activity(telegram_id)
    check_and_award_achievements(telegram_id)
    return True


def get_watched_lesson_ids(telegram_id: int, course_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT lp.lesson_id FROM lesson_progress lp
            JOIN lessons l ON l.id = lp.lesson_id
            JOIN paragraphs p ON p.id = l.paragraph_id
            WHERE lp.telegram_id = ? AND p.course_id = ?
        """, (telegram_id, course_id))
        return [r["lesson_id"] for r in cur.fetchall()]


# ---------- SERTIFIKATLAR (kurs 100% tugallanganda) ----------

def get_course_completion(telegram_id: int, course_id: int) -> dict:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as c FROM lessons l JOIN paragraphs p ON p.id = l.paragraph_id
            WHERE p.course_id = ?
        """, (course_id,))
        total = cur.fetchone()["c"]
    watched = len(get_watched_lesson_ids(telegram_id, course_id))
    percent = round((watched / total) * 100) if total > 0 else 0
    return {
        "total_lessons": total, "watched_lessons": watched,
        "percent": percent, "is_complete": total > 0 and watched >= total,
    }


def _generate_certificate_number(course_id: int) -> str:
    year = datetime.datetime.utcnow().year
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM certificates")
        seq = cur.fetchone()["c"] + 1
    return f"KM-{year}-{course_id:03d}{seq:05d}"


def get_or_issue_certificate(telegram_id: int, course_id: int):
    """Kurs 100% tugallangan bo'lsagina sertifikat 'beradi' — ALLAQACHON
    berilgan bo'lsa, ESKISINI qaytaradi (raqami o'zgarmaydi, qayta-qayta
    yuklab olganda ham HAR DOIM bir xil sertifikat raqami chiqishi kerak)."""
    completion = get_course_completion(telegram_id, course_id)
    if not completion["is_complete"]:
        return None

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM certificates WHERE telegram_id = ? AND course_id = ?",
            (telegram_id, course_id)
        )
        row = cur.fetchone()
        if row:
            return dict(row)

        cert_number = _generate_certificate_number(course_id)
        cur.execute(
            "INSERT INTO certificates (telegram_id, course_id, certificate_number) VALUES (?, ?, ?)",
            (telegram_id, course_id, cert_number)
        )
        conn.commit()
        cur.execute("SELECT * FROM certificates WHERE id = ?", (cur.lastrowid,))
        return dict(cur.fetchone())


def get_my_certificates(telegram_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.*, co.title as course_title, co.subject as course_subject
            FROM certificates c JOIN courses co ON co.id = c.course_id
            WHERE c.telegram_id = ?
            ORDER BY c.issued_at DESC
        """, (telegram_id,))
        return [dict(r) for r in cur.fetchall()]


# ---------- ENROLLMENTS (pullik obuna) ----------

def grant_enrollment(telegram_id: int, course_id: int, duration_days: int = None):
    """Foydalanuvchiga kursga obuna beradi (yoki mavjud obunani uzaytiradi).
    duration_days=None bo'lsa, muddatsiz (lifetime) obuna beriladi."""
    with get_connection() as conn:
        cur = conn.cursor()

        if duration_days is None:
            expiry = None
        else:
            cur.execute("SELECT expiry_date FROM enrollments WHERE telegram_id = ? AND course_id = ?",
                        (telegram_id, course_id))
            row = cur.fetchone()
            now = datetime.datetime.utcnow()
            if row and row["expiry_date"]:
                current_expiry = datetime.datetime.fromisoformat(row["expiry_date"])
                base = current_expiry if current_expiry > now else now
            else:
                base = now
            expiry = (base + datetime.timedelta(days=duration_days)).isoformat()

        cur.execute("""
            INSERT INTO enrollments (telegram_id, course_id, expiry_date)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id, course_id) DO UPDATE SET expiry_date = excluded.expiry_date
        """, (telegram_id, course_id, expiry))
        conn.commit()


def get_enrollment(telegram_id: int, course_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM enrollments WHERE telegram_id = ? AND course_id = ?", (telegram_id, course_id))
        row = cur.fetchone()
        return dict(row) if row else None


def get_user_enrollments(telegram_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT e.*, c.title, c.thumbnail_emoji, c.subject FROM enrollments e
            JOIN courses c ON c.id = e.course_id
            WHERE e.telegram_id = ? ORDER BY e.created_at DESC
        """, (telegram_id,))
        return [dict(r) for r in cur.fetchall()]


# ---------- OBUNA MUDDATI ESLATMALARI ----------

REMINDER_WINDOW_DAYS = 2  # muddat tugashiga shuncha kun (yoki kamroq) qolganda eslatma yuboriladi


def get_enrollments_needing_reminder():
    """Muddati tez orada tugaydigan (yoki yaqinda tugagan, grace muddatida)
    va hali eslatma yuborilmagan obunalarni topadi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT e.id, e.telegram_id, e.course_id, e.expiry_date, c.title as course_title
            FROM enrollments e
            JOIN courses c ON c.id = e.course_id
            WHERE e.expiry_date IS NOT NULL
              AND e.reminder_sent_at IS NULL
              AND julianday(e.expiry_date) - julianday('now') <= ?
        """, (REMINDER_WINDOW_DAYS,))
        return [dict(r) for r in cur.fetchall()]


def mark_reminder_sent(enrollment_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE enrollments SET reminder_sent_at = CURRENT_TIMESTAMP WHERE id = ?", (enrollment_id,))
        conn.commit()


# ---------- ANALITIKA (o'qituvchi dashboardi) ----------

def get_analytics_summary():
    with get_connection() as conn:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) as c FROM users")
        total_users = cur.fetchone()["c"]

        cur.execute("SELECT COALESCE(SUM(coins), 0) as s FROM users")
        total_coins = cur.fetchone()["s"]

        cur.execute("SELECT COUNT(*) as c FROM lesson_progress")
        total_lessons_watched = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) as c FROM test_attempts WHERE finished_at IS NOT NULL")
        total_test_attempts = cur.fetchone()["c"]

        cur.execute("""
            SELECT AVG(CAST(score AS FLOAT) / NULLIF(total_questions, 0)) as avg
            FROM test_attempts WHERE finished_at IS NOT NULL
        """)
        row = cur.fetchone()
        avg_test_score_percent = round((row["avg"] or 0) * 100, 1)

        cur.execute("SELECT COUNT(*) as c FROM referrals WHERE confirmed = 1")
        confirmed_referrals = cur.fetchone()["c"]

        cur.execute("""
            SELECT c.title, COUNT(lp.id) as watch_count
            FROM lesson_progress lp
            JOIN lessons l ON l.id = lp.lesson_id
            JOIN paragraphs p ON p.id = l.paragraph_id
            JOIN courses c ON c.id = p.course_id
            GROUP BY c.id ORDER BY watch_count DESC LIMIT 5
        """)
        top_courses = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT t.title, COUNT(a.id) as attempt_count
            FROM test_attempts a JOIN tests t ON t.id = a.test_id
            WHERE a.finished_at IS NOT NULL
            GROUP BY t.id ORDER BY attempt_count DESC LIMIT 5
        """)
        top_tests = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT COUNT(*) as cnt, COALESCE(SUM(c2.price), 0) as revenue
            FROM enrollments e JOIN courses c2 ON c2.id = e.course_id
            WHERE c2.price > 0
        """)
        row = cur.fetchone()

        return {
            "total_users": total_users,
            "total_coins": total_coins,
            "total_lessons_watched": total_lessons_watched,
            "total_test_attempts": total_test_attempts,
            "avg_test_score_percent": avg_test_score_percent,
            "confirmed_referrals": confirmed_referrals,
            "top_courses": top_courses,
            "top_tests": top_tests,
            "paid_enrollments_count": row["cnt"],
            "estimated_revenue": row["revenue"],
        }


GRACE_PERIOD_DAYS = 2


def compute_course_access(telegram_id: int, course: dict, member_group_ids=None):
    """Kurs uchun kirish holatini hisoblaydi.

    Qaytaradi: {'unlocked': bool,
                'reason': 'free'|'referral'|'group'|'enrolled'|'grace'|'expired'|'locked',
                'expiry_date': str|None, 'days_left': int|None,
                'access_groups': [...]}   # qulf bo'lsa — qaysi guruhga qo'shilish kerak

    KIRISH YO'LLARI (biri yetarli):
      1) kurs bepul
      2) yetarli referal
      3) PULLIK GURUH A'ZOLIGI — o'quvchining Telegram ID si o'qituvchining
         yopiq guruhida bo'lsa, kurs avtomatik ochiladi
      4) qo'lda biriktirish (eski usul — saqlangan)

    3-yo'l 4-dan OLDIN tekshiriladi, chunki u tezroq va muddatsiz.
    """
    gate = access_state_for(telegram_id, "course", course["id"], member_group_ids)

    if course["is_free"]:
        return {"unlocked": True, "reason": "free", "expiry_date": None,
                "days_left": None, "access_groups": []}

    if course.get("required_referrals", 0) > 0:
        refs = get_confirmed_referral_count(telegram_id)
        if refs >= course["required_referrals"]:
            return {"unlocked": True, "reason": "referral", "expiry_date": None,
                    "days_left": None, "access_groups": []}

    # Pullik guruh a'zoligi — asosiy yangi yo'l
    if gate["granted"]:
        return {"unlocked": True, "reason": "group", "expiry_date": None,
                "days_left": None, "access_groups": gate["groups"]}

    # Qo'lda biriktirish — ESKI USUL, saqlanadi. O'qituvchi istisno
    # holatlarda (guruhga qo'shilmagan, lekin to'lagan o'quvchi) qo'lda
    # ham kirish bera oladi.
    if course.get("price", 0) > 0:
        enrollment = get_enrollment(telegram_id, course["id"])
        if enrollment:
            if enrollment["expiry_date"] is None:
                return {"unlocked": True, "reason": "enrolled", "expiry_date": None,
                        "days_left": None, "access_groups": []}
            expiry = datetime.datetime.fromisoformat(enrollment["expiry_date"])
            now = datetime.datetime.utcnow()
            grace_end = expiry + datetime.timedelta(days=GRACE_PERIOD_DAYS)
            days_left = (expiry - now).days
            if now <= expiry:
                return {"unlocked": True, "reason": "enrolled",
                        "expiry_date": enrollment["expiry_date"],
                        "days_left": days_left, "access_groups": []}
            elif now <= grace_end:
                return {"unlocked": True, "reason": "grace",
                        "expiry_date": enrollment["expiry_date"],
                        "days_left": days_left, "access_groups": []}
            else:
                return {"unlocked": False, "reason": "expired",
                        "expiry_date": enrollment["expiry_date"],
                        "days_left": days_left, "access_groups": gate["groups"]}

    # Qulf. Agar kurs guruhga bog'langan bo'lsa — sababi "guruhga qo'shilmagan",
    # aks holda odatdagi "yopiq" (admin bilan bog'lanish kerak).
    return {"unlocked": False,
            "reason": "need_group" if gate["gated"] else "locked",
            "expiry_date": None, "days_left": None,
            "access_groups": gate["groups"]}


def access_state_for(telegram_id: int, content_type: str, content_id: int,
                     member_group_ids=None):
    """Kontentning guruh orqali kirish holati.

    access_control.py dagi bir xil funksiyaning DB qatlamidagi nusxasi —
    aylanma import (database <-> access_control) bo'lmasligi uchun shu
    yerda takrorlangan. Mantiq bitta joyda: has_group_access().
    """
    granted, groups = has_group_access(telegram_id, content_type, content_id,
                                       member_group_ids)
    return {
        "gated": bool(groups),
        "granted": granted,
        "groups": [{"id": g["id"], "title": g["title"],
                    "invite_link": g["invite_link"]} for g in groups],
    }


# ---------- LEADERBOARD ----------

# "Haftalik" — so'nggi 7 kun (aylanma oyna), "Oylik" — joriy oyning 1-kunidan
# beri (taqvim oyi, nazorat testi oylik reytingi bilan bir xil mantiq).
# "Butun davr" uchun users.coins jadvalidagi UMUMIY yig'indi ishlatiladi —
# chunki coin_history faqat shu funksiya qo'shilgan kundan boshlab yozib
# borilyapti, undan oldingi coinlar tarixda "yo'qolib qolmasin" uchun.
_PERIOD_SQL_FILTERS = {
    "week": "created_at >= datetime('now', '-7 days')",
    "month": "created_at >= datetime('now', 'start of month')",
}


def get_leaderboard(limit: int = 100, period: str = "all"):
    with get_connection() as conn:
        cur = conn.cursor()
        if period in _PERIOD_SQL_FILTERS:
            cur.execute(f"""
                SELECT u.telegram_id, u.first_name, COALESCE(SUM(ch.amount), 0) as coins
                FROM coin_history ch
                JOIN users u ON u.telegram_id = ch.telegram_id
                WHERE ch.{_PERIOD_SQL_FILTERS[period]}
                GROUP BY u.telegram_id
                HAVING coins > 0
                ORDER BY coins DESC, u.id ASC
                LIMIT ?
            """, (limit,))
        else:
            cur.execute("""
                SELECT telegram_id, first_name, coins FROM users
                WHERE coins > 0 ORDER BY coins DESC, id ASC LIMIT ?
            """, (limit,))
        return [dict(r) for r in cur.fetchall()]


def get_user_rank(telegram_id: int, period: str = "all"):
    with get_connection() as conn:
        cur = conn.cursor()
        if period in _PERIOD_SQL_FILTERS:
            cur.execute(f"""
                SELECT COALESCE(SUM(amount), 0) as coins FROM coin_history
                WHERE telegram_id = ? AND {_PERIOD_SQL_FILTERS[period]}
            """, (telegram_id,))
            row = cur.fetchone()
            my_coins = row["coins"] if row else 0
            if my_coins <= 0:
                return None
            cur.execute(f"""
                SELECT COUNT(*) as c FROM (
                    SELECT telegram_id, SUM(amount) as total FROM coin_history
                    WHERE {_PERIOD_SQL_FILTERS[period]}
                    GROUP BY telegram_id
                    HAVING total > ?
                )
            """, (my_coins,))
            return cur.fetchone()["c"] + 1

        cur.execute("SELECT coins FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cur.fetchone()
        if not row:
            return None
        my_coins = row["coins"]
        cur.execute("SELECT COUNT(*) as c FROM users WHERE coins > ?", (my_coins,))
        return cur.fetchone()["c"] + 1


# ---------- TESTLAR ----------

DIFFICULTY_TIME_SECONDS = {
    "oson": 300,      # 5 daqiqa
    "orta": 600,      # 10 daqiqa
    "qiyin": 900,     # 15 daqiqa
}


def get_all_tests(subject: str = None, only_active: bool = True, include_control: bool = True, test_kind: str = None):
    with get_connection() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM tests WHERE 1=1"
        params = []
        if subject:
            query += " AND subject = ?"
            params.append(subject)
        if only_active:
            query += " AND is_active = 1"
        if not include_control:
            query += " AND (is_control_test IS NULL OR is_control_test = 0)"
        if test_kind:
            if test_kind == "practice":
                # Eski (test_kind ustuni qo'shilishidan oldingi) testlar NULL
                # bo'lib qoladi — ularni ham "oddiy" hisoblaymiz.
                query += " AND (test_kind IS NULL OR test_kind = 'practice')"
            else:
                query += " AND test_kind = ?"
                params.append(test_kind)
        query += " ORDER BY order_num ASC, id ASC"
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def get_test(test_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM tests WHERE id = ?", (test_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def count_test_questions(test_id: int) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM test_questions WHERE test_id = ?", (test_id,))
        return cur.fetchone()["c"]


def create_test(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        difficulty = data.get("difficulty", "orta")
        time_limit = data.get("time_limit_seconds") or DIFFICULTY_TIME_SECONDS.get(difficulty, 600)
        cur.execute("""
            INSERT INTO tests (subject, title, difficulty, time_limit_seconds, order_num, is_active, is_control_test, course_id, test_kind, test_group_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("subject", ""), data.get("title", ""), difficulty,
            safe_int(time_limit, DIFFICULTY_TIME_SECONDS.get(difficulty, 600)),
            safe_int(data.get("order_num"), 0), safe_int(data.get("is_active"), 1),
            safe_int(data.get("is_control_test"), 0), data.get("course_id") or None,
            data.get("test_kind") or "practice",
            safe_int(data["test_group_id"]) if data.get("test_group_id") else None
        ))
        conn.commit()
        return cur.lastrowid


def update_test(test_id: int, data: dict):
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        # Raqamli ustunlar bo'sh/None kelib qolsa ham NULL yozib yubormaymiz —
        # standart qiymatga tushiramiz (aks holda, masalan, order_num NULL
        # bo'lib, keyin tartiblashda test ro'yxatdan "yo'qolib" qolardi).
        numeric_defaults = {"time_limit_seconds": 600, "order_num": 0, "is_active": 1, "is_control_test": 0}
        for key in ["subject", "title", "difficulty", "time_limit_seconds", "order_num", "is_active",
                    "is_control_test", "course_id", "test_kind"]:
            if key in data:
                fields.append(f"{key} = ?")
                if key in numeric_defaults:
                    values.append(safe_int(data[key], numeric_defaults[key]))
                else:
                    values.append(data[key] if data[key] != "" else None)
        if "test_group_id" in data:
            fields.append("test_group_id = ?")
            values.append(safe_int(data["test_group_id"]) if data["test_group_id"] else None)
        if fields:
            values.append(test_id)
            cur.execute(f"UPDATE tests SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()


def delete_test(test_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM tests WHERE id = ?", (test_id,))
        conn.commit()


# ---------- MAVZULI TEST: FAN KARTALARI VA GURUHLAR ----------

def get_test_subject_cards(only_active: bool = True):
    with get_connection() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM test_subject_cards WHERE 1=1"
        if only_active:
            query += " AND is_active = 1"
        query += " ORDER BY order_num ASC, id ASC"
        cur.execute(query)
        return [dict(r) for r in cur.fetchall()]


def get_test_subject_card(card_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM test_subject_cards WHERE id = ?", (card_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_test_subject_card(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO test_subject_cards (title, icon, color_key, order_num, is_active)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data.get("title", ""), data.get("icon") or "📘", data.get("color_key") or "teal",
            int(data.get("order_num", 0)), int(data.get("is_active", 1))
        ))
        conn.commit()
        return cur.lastrowid


def update_test_subject_card(card_id: int, data: dict):
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        for key in ["title", "icon", "color_key", "order_num", "is_active"]:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        if fields:
            values.append(card_id)
            cur.execute(f"UPDATE test_subject_cards SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()


def delete_test_subject_card(card_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM test_subject_cards WHERE id = ?", (card_id,))
        conn.commit()


def get_test_stages(subject_card_id: int, only_active: bool = True):
    with get_connection() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM test_stages WHERE subject_card_id = ?"
        params = [subject_card_id]
        if only_active:
            query += " AND is_active = 1"
        query += " ORDER BY order_num ASC, id ASC"
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]


def get_all_test_stages(only_active: bool = False):
    """Admin panel uchun — barcha bosqichlarni, fan nomi bilan birga qaytaradi."""
    with get_connection() as conn:
        cur = conn.cursor()
        query = """
            SELECT s.*, c.title AS subject_title FROM test_stages s
            JOIN test_subject_cards c ON c.id = s.subject_card_id
            WHERE 1=1
        """
        if only_active:
            query += " AND s.is_active = 1"
        query += " ORDER BY c.order_num ASC, s.order_num ASC, s.id ASC"
        cur.execute(query)
        return [dict(r) for r in cur.fetchall()]


def get_test_stage(stage_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM test_stages WHERE id = ?", (stage_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_test_stage(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO test_stages (subject_card_id, title, subtitle, icon, order_num, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            int(data["subject_card_id"]), data.get("title", ""), data.get("subtitle") or None,
            data.get("icon") or "📶", int(data.get("order_num", 0)), int(data.get("is_active", 1))
        ))
        conn.commit()
        return cur.lastrowid


def update_test_stage(stage_id: int, data: dict):
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        for key in ["subject_card_id", "title", "subtitle", "icon", "order_num", "is_active"]:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key] if data[key] != "" else None)
        if fields:
            values.append(stage_id)
            cur.execute(f"UPDATE test_stages SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()


def delete_test_stage(stage_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM test_stages WHERE id = ?", (stage_id,))
        conn.commit()


def get_test_groups(stage_id: int, only_active: bool = True):
    with get_connection() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM test_groups WHERE stage_id = ?"
        params = [stage_id]
        if only_active:
            query += " AND is_active = 1"
        query += " ORDER BY order_num ASC, id ASC"
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]


def get_all_test_groups(only_active: bool = False):
    """Admin panel uchun — barcha turkumlarni, bosqich va fan nomi bilan birga qaytaradi."""
    with get_connection() as conn:
        cur = conn.cursor()
        query = """
            SELECT g.*, s.title AS stage_title, s.subject_card_id AS subject_card_id,
                   c.title AS subject_title
            FROM test_groups g
            JOIN test_stages s ON s.id = g.stage_id
            JOIN test_subject_cards c ON c.id = s.subject_card_id
            WHERE 1=1
        """
        if only_active:
            query += " AND g.is_active = 1"
        query += " ORDER BY c.order_num ASC, s.order_num ASC, g.order_num ASC, g.id ASC"
        cur.execute(query)
        return [dict(r) for r in cur.fetchall()]


def get_test_group(group_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM test_groups WHERE id = ?", (group_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_test_group(data: dict) -> int:
    # ESLATMA: test_groups.subject_card_id ustuni eski (bir qavatli)
    # arxitekturadan meros qolgan va hamon NOT NULL — shuning uchun yangi
    # turkum yaratganda ham uni bosqichning fanidan avtomatik hisoblab,
    # birga saqlaymiz (talaba/admin buni ko'rmaydi ham, sezmaydi ham).
    stage = get_test_stage(int(data["stage_id"]))
    subject_card_id = stage["subject_card_id"] if stage else None
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO test_groups (stage_id, subject_card_id, title, subtitle, icon, order_num, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            int(data["stage_id"]), subject_card_id, data.get("title", ""), data.get("subtitle") or None,
            data.get("icon") or "📂", int(data.get("order_num", 0)), int(data.get("is_active", 1))
        ))
        conn.commit()
        return cur.lastrowid


def update_test_group(group_id: int, data: dict):
    # Bosqich o'zgarsa (turkum boshqa bosqichga ko'chirilsa), meros qolgan
    # subject_card_id ustunini ham yangi bosqichning fani bilan sinxronlab turamiz.
    if "stage_id" in data and data["stage_id"]:
        stage = get_test_stage(int(data["stage_id"]))
        if stage:
            data = dict(data)
            data["subject_card_id"] = stage["subject_card_id"]
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        for key in ["stage_id", "subject_card_id", "title", "subtitle", "icon", "order_num", "is_active"]:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key] if data[key] != "" else None)
        if fields:
            values.append(group_id)
            cur.execute(f"UPDATE test_groups SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()


def delete_test_group(group_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM test_groups WHERE id = ?", (group_id,))
        conn.commit()


def count_group_tests(group_id: int, only_active: bool = True) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        query = "SELECT COUNT(*) as c FROM tests WHERE test_group_id = ?"
        params = [group_id]
        if only_active:
            query += " AND is_active = 1"
        cur.execute(query, params)
        return cur.fetchone()["c"]


def has_student_completed_test(telegram_id: int, test_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT 1 FROM test_attempts WHERE telegram_id = ? AND test_id = ? AND finished_at IS NOT NULL LIMIT 1
        """, (telegram_id, test_id))
        return cur.fetchone() is not None


def compute_group_progress(telegram_id: int, group_id: int):
    """Berilgan guruhdagi FAOL testlardan nechtasi shu talaba tomonidan
    tugallanganini hisoblaydi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM tests WHERE test_group_id = ? AND is_active = 1", (group_id,))
        test_ids = [row["id"] for row in cur.fetchall()]
        total = len(test_ids)
        if total == 0:
            return {"completed": 0, "total": 0}
        placeholders = ",".join("?" for _ in test_ids)
        cur.execute(f"""
            SELECT COUNT(DISTINCT test_id) as c FROM test_attempts
            WHERE telegram_id = ? AND finished_at IS NOT NULL AND test_id IN ({placeholders})
        """, [telegram_id] + test_ids)
        completed = cur.fetchone()["c"]
        return {"completed": completed, "total": total}


def get_groups_with_progress(telegram_id: int, stage_id: int):
    """Bosqich ICHIDAGI turkumlarni (masalan 'Mavzulashtirilgan testlar',
    'Nazorat testlari') progress bilan qaytaradi. Bular bir-biriga nisbatan
    QULFLANMAYDI — bosqichning o'zi ochiq bo'lsa, ichidagi barcha turkumlar
    talaba uchun teng ravishda ochiq (parallel), faqat progress ko'rsatish
    uchun completed/total hisoblanadi."""
    groups = get_test_groups(stage_id, only_active=True)
    result = []
    for g in groups:
        progress = compute_group_progress(telegram_id, g["id"])
        g_out = dict(g)
        g_out["completed_count"] = progress["completed"]
        g_out["total_count"] = progress["total"]
        g_out["is_done"] = progress["total"] > 0 and progress["completed"] >= progress["total"]
        g_out["unlocked"] = True
        result.append(g_out)
    return result


def compute_stage_progress(telegram_id: int, stage_id: int):
    """Bosqich ICHIDAGI barcha turkumlardagi FAOL testlardan nechtasi shu
    talaba tomonidan tugallanganini hisoblaydi (turkumlar bo'yicha yig'indi)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.id FROM tests t
            JOIN test_groups g ON g.id = t.test_group_id
            WHERE g.stage_id = ? AND g.is_active = 1 AND t.is_active = 1
        """, (stage_id,))
        test_ids = [row["id"] for row in cur.fetchall()]
        total = len(test_ids)
        if total == 0:
            return {"completed": 0, "total": 0}
        placeholders = ",".join("?" for _ in test_ids)
        cur.execute(f"""
            SELECT COUNT(DISTINCT test_id) as c FROM test_attempts
            WHERE telegram_id = ? AND finished_at IS NOT NULL AND test_id IN ({placeholders})
        """, [telegram_id] + test_ids)
        completed = cur.fetchone()["c"]
        return {"completed": completed, "total": total}


def compute_stages_with_unlock(telegram_id: int, subject_card_id: int):
    """Fan ichidagi bosqichlarni ('1-bo'lim', '2-bo'lim'...) order_num
    bo'yicha qaytaradi, har biriga 'unlocked' va progress (completed/total)
    qo'shib. Birinchi bosqich doim ochiq. Keyingi bosqich — faqat
    oldingisidagi BARCHA turkumlardagi BARCHA (faol) testlar
    tugallangandan keyin ochiladi. Agar oldingi bosqichda hali umuman test
    bo'lmasa (admin hali qo'shmagan bo'lsa), u "tugallanmagan" hisoblanadi
    va keyingi bosqichni QULFLAGAN holda qoldiradi — bo'sh bosqich
    avtomatik "o'tib ketilgan" deb hisoblanmaydi (aks holda admin hali
    testlar qo'shib ulgurmagan bosqich ustidan keyingisi darrov ochilib
    qolar edi)."""
    stages = get_test_stages(subject_card_id, only_active=True)
    result = []
    prev_completed = True
    for s in stages:
        progress = compute_stage_progress(telegram_id, s["id"])
        unlocked = prev_completed
        s_out = dict(s)
        s_out["completed_count"] = progress["completed"]
        s_out["total_count"] = progress["total"]
        s_out["unlocked"] = unlocked
        s_out["is_done"] = progress["total"] > 0 and progress["completed"] >= progress["total"]
        result.append(s_out)
        # Keyingi bosqich uchun: shu bosqich tugallanganmi. E'TIBOR: bo'sh
        # bosqich (hali test qo'shilmagan) ENDI "tugallangan" deb
        # hisoblanmaydi — aks holda admin ulgurmagan bosqichdan keyingisi
        # talaba uchun darrov ochilib qolar edi.
        prev_completed = progress["total"] > 0 and progress["completed"] >= progress["total"]
    return result


# ---------- SAVOLLAR ----------

def get_questions(test_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM test_questions WHERE test_id = ? ORDER BY order_num ASC, id ASC", (test_id,))
        return [dict(r) for r in cur.fetchall()]


def get_question(question_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM test_questions WHERE id = ?", (question_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def _default_point_value(question_type: str, difficulty_level: str) -> float:
    """Milliy sertifikat Y1/Y2/O1 uchun DEFAULT xom ball — Matematika
    fanidan rasmiy spetsifikatsiyada aniq ko'rsatilgan formula (past=1,
    o'rta=2.2, yuqori=3 ball; Y2 doim 2.2 ball). Kimyo/Biologiya
    hujjatlarida bu aniq raqamlar ochiq e'lon qilinmagan (faqat "Rash
    modeli orqali baholanadi" deyilgan) — shuning uchun shu standart
    qiymat DEFAULT sifatida qo'llanadi, admin xohlasa savol formasida
    o'zgartira oladi."""
    if question_type == "Y2":
        return 2.2
    mapping = {"past": 1.0, "orta": 2.2, "yuqori": 3.0}
    return mapping.get(difficulty_level, 1.0)


def create_question(data: dict) -> int:
    question_type = data.get("question_type") or "Y1"
    difficulty_level = data.get("difficulty_level") or "past"
    point_value = data.get("point_value")
    if point_value in (None, ""):
        point_value = _default_point_value(question_type, difficulty_level)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO test_questions (
                test_id, question_text, image_url, option_1, option_2, option_3, option_4,
                correct_index, order_num, table_data,
                question_type, difficulty_level, point_value, match_data,
                correct_answer_text, max_score, rubric_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            int(data["test_id"]), data.get("question_text", ""), data.get("image_url", ""),
            data.get("option_1", ""), data.get("option_2", ""), data.get("option_3", ""), data.get("option_4", ""),
            # Y2/O1/O2 turlarida correct_index ishlatilmaydi — jadval ustuni
            # NOT NULL bo'lgani uchun 0 bilan to'ldiramiz (Y1 uchun haqiqiy qiymat keladi).
            int(data.get("correct_index", 1)) if question_type == "Y1" else 0,
            int(data.get("order_num", 0)), data.get("table_data") or None,
            question_type, difficulty_level, float(point_value), data.get("match_data") or None,
            data.get("correct_answer_text") or None, float(data.get("max_score") or 25),
            data.get("rubric_json") or None
        ))
        conn.commit()
        return cur.lastrowid


def update_question(question_id: int, data: dict):
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        for key in [
            "question_text", "image_url", "option_1", "option_2", "option_3", "option_4",
            "correct_index", "order_num", "table_data",
            "question_type", "difficulty_level", "point_value", "match_data",
            "correct_answer_text", "max_score", "rubric_json"
        ]:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        if fields:
            values.append(question_id)
            cur.execute(f"UPDATE test_questions SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()


def delete_question(question_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM test_questions WHERE id = ?", (question_id,))
        conn.commit()


# ---------- TEST TOPSHIRISH (attempt) ----------

def start_attempt(telegram_id: int, test_id: int) -> int:
    total = count_test_questions(test_id)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO test_attempts (telegram_id, test_id, total_questions) VALUES (?, ?, ?)
        """, (telegram_id, test_id, total))
        conn.commit()
        return cur.lastrowid


def submit_answer(telegram_id: int, attempt_id: int, question_id: int, selected_index: int = None,
                   answer_text: str = None, match_answer=None):
    """Javobni tekshiradi va yozib qo'yadi (yoki — agar bu savolga bu urinishda
    ALLAQACHON javob berilgan bo'lsa, uni YANGILAYDI, chunki o'quvchi savollar
    orasida erkin harakatlanib, javobini istalgancha o'zgartirishi mumkin).
    Agar bu savolga birinchi marta to'g'ri javob berilgan bo'lsa 1 coin
    beradi. {'correct': bool, 'correct_index': int, 'coin_awarded': bool}
    qaytaradi. Urinishning umumiy bali (score) BU YERDA emas — yakunlash
    (finish_attempt) vaqtida, barcha javoblar asosida qayta hisoblanadi.

    Milliy sertifikat savol turlari (question_type) uchun ham shu funksiya
    ishlatiladi: Y1 — selected_index, Y2 — match_answer (moslashtirilgan
    juftliklar ro'yxati), O1 — answer_text (qisqa javob, avtomatik,
    katta-kichik harf/bo'shliqqa sezgir emas). O2 (yozma ish) esa alohida
    submit_written_answer() orqali yuboriladi va o'qituvchi tomonidan
    QO'LDA baholanadi — bu yerga kelmaydi."""
    question = get_question(question_id)
    if not question:
        return {"correct": False, "correct_index": None, "coin_awarded": False}

    qtype = question.get("question_type") or "Y1"
    points_possible = float(question.get("point_value") or 1)
    stored_text = None

    if qtype == "Y2":
        correct_pairs = set()
        try:
            correct_pairs = {tuple(p) for p in json.loads(question.get("match_data") or "{}").get("correct_pairs", [])}
        except (ValueError, TypeError):
            correct_pairs = set()
        submitted_pairs = set()
        if match_answer is not None:
            try:
                raw = match_answer if isinstance(match_answer, list) else json.loads(match_answer)
                submitted_pairs = {tuple(p) for p in raw}
            except (ValueError, TypeError):
                submitted_pairs = set()
        is_correct = bool(correct_pairs) and submitted_pairs == correct_pairs
        stored_text = json.dumps(sorted(submitted_pairs)) if submitted_pairs else None
    elif qtype == "O1":
        expected_alts = [e.strip().lower() for e in (question.get("correct_answer_text") or "").split("|") if e.strip()]
        given = (answer_text or "").strip().lower()
        is_correct = bool(given) and given in expected_alts
        stored_text = answer_text
    else:  # Y1 (default) — bitta to'g'ri javobli yopiq test
        is_correct = selected_index is not None and int(selected_index) == int(question["correct_index"])

    points_earned = points_possible if is_correct else 0.0

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO test_answers (attempt_id, question_id, selected_index, is_correct, answer_text, points_earned)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(attempt_id, question_id)
            DO UPDATE SET selected_index = excluded.selected_index, is_correct = excluded.is_correct,
                          answer_text = excluded.answer_text, points_earned = excluded.points_earned
        """, (attempt_id, question_id, selected_index, 1 if is_correct else 0, stored_text, points_earned))
        conn.commit()

    coin_awarded = False
    if is_correct:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM user_question_progress WHERE telegram_id = ? AND question_id = ?",
                        (telegram_id, question_id))
            already = cur.fetchone()
            if already is None:
                cur.execute("INSERT INTO user_question_progress (telegram_id, question_id, coin_awarded) VALUES (?, ?, 1)",
                            (telegram_id, question_id))
                conn.commit()
                coin_awarded = True
        if coin_awarded:
            add_coins(telegram_id, 1)  # 'with' bloki yopilgach chaqiriladi — pool bandlanib qolmaydi

    return {"correct": is_correct, "correct_index": question["correct_index"], "coin_awarded": coin_awarded,
            "points_earned": points_earned}


# ---------- MILLIY SERTIFIKAT: O2 (yozma ish) yuborish va qo'lda baholash ----------

def submit_written_answer(attempt_id: int, question_id: int, photo_urls=None, text_answer: str = None):
    """O2 (kengaytirilgan javobli yozma ish) uchun — talaba yechimini rasm
    (bir nechta bo'lishi mumkin) va/yoki matn sifatida yuboradi. Bu DARHOL
    baholanmaydi — o'qituvchi keyinroq grade_written_answer() orqali
    band-band (M/A) ball qo'yadi."""
    photo_urls_json = json.dumps(photo_urls) if photo_urls else None
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO certificate_written_answers (attempt_id, question_id, photo_urls, text_answer)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(attempt_id, question_id)
            DO UPDATE SET photo_urls = excluded.photo_urls, text_answer = excluded.text_answer,
                          submitted_at = CURRENT_TIMESTAMP,
                          teacher_score = NULL, teacher_comment = NULL, graded_by = NULL, graded_at = NULL
        """, (attempt_id, question_id, photo_urls_json, text_answer))
        conn.commit()
    return {"ok": True}


def get_written_answer(attempt_id: int, question_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM certificate_written_answers WHERE attempt_id = ? AND question_id = ?",
            (attempt_id, question_id)
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_written_answers_for_attempt(attempt_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM certificate_written_answers WHERE attempt_id = ?", (attempt_id,))
        return [dict(r) for r in cur.fetchall()]


def get_pending_written_answers():
    """Admin panelda "Yozma ishlarni baholash" navbati — hali o'qituvchi
    ball qo'ymagan (teacher_score IS NULL) barcha O2 javoblari."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT wa.*, q.question_text, q.max_score, q.rubric_json, q.order_num,
                   t.id AS test_id, t.title AS test_title, t.subject AS subject,
                   a.telegram_id, u.first_name, u.username
            FROM certificate_written_answers wa
            JOIN test_questions q ON q.id = wa.question_id
            JOIN test_attempts a ON a.id = wa.attempt_id
            JOIN tests t ON t.id = q.test_id
            LEFT JOIN users u ON u.telegram_id = a.telegram_id
            WHERE wa.teacher_score IS NULL
            ORDER BY wa.submitted_at ASC
        """)
        return [dict(r) for r in cur.fetchall()]


def grade_written_answer(written_answer_id: int, teacher_score: float, teacher_comment: str, graded_by: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE certificate_written_answers
            SET teacher_score = ?, teacher_comment = ?, graded_by = ?, graded_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (teacher_score, teacher_comment, graded_by, written_answer_id))
        conn.commit()
        cur.execute("SELECT attempt_id FROM certificate_written_answers WHERE id = ?", (written_answer_id,))
        row = cur.fetchone()
    if row:
        _recompute_certificate_result(row["attempt_id"])
    return {"ok": True}


def set_answer_flag(attempt_id: int, question_id: int, flagged: bool):
    """Attestatsiya testida "Belgilash" — savolni javob berilgan-berilmaganidan
    qat'i nazar "keyinroq qaytaman" deb belgilash/bekor qilish. Agar bu
    savolga hali umuman javob yozilmagan bo'lsa ham ishlashi kerak, shuning
    uchun selected_index/is_correct'ni YO'QOTMASDAN (mavjud bo'lsa saqlab
    qolib) faqat is_flagged ustunini upsert qilamiz."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO test_answers (attempt_id, question_id, selected_index, is_correct, is_flagged)
            VALUES (?, ?, NULL, 0, ?)
            ON CONFLICT(attempt_id, question_id)
            DO UPDATE SET is_flagged = excluded.is_flagged
        """, (attempt_id, question_id, 1 if flagged else 0))
        conn.commit()
    return {"flagged": bool(flagged)}


def get_attempt_flags(attempt_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT question_id FROM test_answers
            WHERE attempt_id = ? AND is_flagged = 1
        """, (attempt_id,))
        return [r["question_id"] for r in cur.fetchall()]


# ---------- E'TIROZ BILDIRISH (savolga shikoyat) ----------

def create_objection(attempt_id: int, question_id: int, telegram_id: int, comment: str) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO question_objections (attempt_id, question_id, telegram_id, comment)
            VALUES (?, ?, ?, ?)
        """, (attempt_id, question_id, telegram_id, comment))
        conn.commit()
        return cur.lastrowid


def get_objections(status: str = None):
    with get_connection() as conn:
        cur = conn.cursor()
        query = """
            SELECT o.id as id, o.attempt_id as attempt_id, o.question_id as question_id,
                   o.telegram_id as telegram_id, o.comment as comment, o.status as status,
                   o.created_at as created_at,
                   q.question_text as question_text, t.id as test_id, t.title as test_title,
                   u.first_name as first_name, u.username as username
            FROM question_objections o
            LEFT JOIN test_questions q ON q.id = o.question_id
            LEFT JOIN tests t ON t.id = q.test_id
            LEFT JOIN users u ON u.telegram_id = o.telegram_id
            WHERE 1=1
        """
        params = []
        if status:
            query += " AND o.status = ?"
            params.append(status)
        query += " ORDER BY o.created_at DESC"
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]


def update_objection_status(objection_id: int, status: str):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE question_objections SET status = ? WHERE id = ?", (status, objection_id))
        conn.commit()


# Milliy sertifikat daraja chegaralari. A+/A/B+ — Bilimni baholash
# agentligining rasmiy e'lonlaridan tasdiqlangan (70/65/60 foiz). B/C+/C
# chegaralari rasmiy manbalarda ochiq e'lon qilinmagan — shu sababli bu
# yerda TAXMINIY, teng oraliqli qiymatlar qo'llanilgan. Natija ekranida
# talabaga bu "taxminiy daraja, rasmiy Rash natijasidan farq qilishi
# mumkin" deb aniq ko'rsatiladi.
CERTIFICATE_LEVEL_THRESHOLDS = [
    (70, "A+"), (65, "A"), (60, "B+"), (55, "B"), (50, "C+"), (46, "C"),
]


def certificate_level_from_percent(percent):
    for threshold, level in CERTIFICATE_LEVEL_THRESHOLDS:
        if percent >= threshold:
            return level
    return None  # sertifikat darajasiga yetmagan


def _certificate_max_score_points(test_id: int) -> float:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT question_type, point_value, max_score FROM test_questions
            WHERE test_id = ?
        """, (test_id,))
        total = 0.0
        for row in cur.fetchall():
            if row["question_type"] == "O2":
                total += float(row["max_score"] or 25)
            else:
                total += float(row["point_value"] or 1)
        return total


def _certificate_review_status(attempt_id: int, test_id: int) -> str:
    """O2 (yozma ish) savollari bo'lsa va ulardan birortasi hali o'qituvchi
    tomonidan baholanmagan bo'lsa — 'pending_review'. Aks holda 'reviewed'
    (O2 bor va hammasi baholangan) yoki 'auto' (bu testda O2 umuman yo'q)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM test_questions WHERE test_id = ? AND question_type = 'O2'", (test_id,))
        o2_ids = [r["id"] for r in cur.fetchall()]
        if not o2_ids:
            return "auto"
        placeholders = ",".join("?" for _ in o2_ids)
        cur.execute(f"""
            SELECT question_id, teacher_score FROM certificate_written_answers
            WHERE attempt_id = ? AND question_id IN ({placeholders})
        """, [attempt_id] + o2_ids)
        graded_by_qid = {r["question_id"]: r["teacher_score"] for r in cur.fetchall()}
        for qid in o2_ids:
            if graded_by_qid.get(qid) is None:
                return "pending_review"
        return "reviewed"


def _recompute_certificate_result(attempt_id: int):
    """Milliy sertifikat urinishi uchun og'irliklangan ballarni qayta
    hisoblaydi: Y1/Y2/O1 — test_answers.points_earned yig'indisi; O2 —
    o'qituvchi qo'ygan teacher_score yig'indisi (hali baholanmagan bo'lsa
    0 sifatida hisoblanadi, lekin review_status shuni aks ettiradi)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT test_id FROM test_attempts WHERE id = ?", (attempt_id,))
        row = cur.fetchone()
        if not row:
            return None
        test_id = row["test_id"]

        cur.execute("SELECT COALESCE(SUM(points_earned), 0) as s FROM test_answers WHERE attempt_id = ?", (attempt_id,))
        auto_points = cur.fetchone()["s"] or 0.0

        cur.execute("SELECT COALESCE(SUM(teacher_score), 0) as s FROM certificate_written_answers WHERE attempt_id = ? AND teacher_score IS NOT NULL", (attempt_id,))
        written_points = cur.fetchone()["s"] or 0.0

        raw_score = float(auto_points) + float(written_points)
        max_score = _certificate_max_score_points(test_id)
        review_status = _certificate_review_status(attempt_id, test_id)
        percent = round((raw_score / max_score) * 100, 1) if max_score > 0 else 0.0
        level = certificate_level_from_percent(percent) if review_status != "pending_review" else None

        cur.execute("""
            UPDATE test_attempts
            SET raw_score_points = ?, max_score_points = ?, review_status = ?, certificate_level = ?
            WHERE id = ?
        """, (raw_score, max_score, review_status, level, attempt_id))
        conn.commit()

        cur.execute("SELECT * FROM test_attempts WHERE id = ?", (attempt_id,))
        r = cur.fetchone()
        return dict(r) if r else None


def finish_attempt(attempt_id: int):
    """Urinishni yakunlaydi. Ball (score) aynan shu yerda, BARCHA saqlangan
    javoblar bo'yicha qayta hisoblanadi — chunki javoblar erkin o'zgartirilishi
    mumkin edi, oraliqda saqlangan "score" ustuni ishonchli emas.

    Milliy sertifikat testlari (test_kind='certificate') uchun oddiy
    "nechta to'g'ri" hisoblash o'rniga OG'IRLIKLANGAN ball (har savol o'z
    qiyinlik/rubrika bali bilan) qo'llaniladi, va agar testda O2 (yozma
    ish) bo'lsa, natija o'qituvchi baholaguncha 'pending_review' holatida
    turadi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT test_id FROM test_attempts WHERE id = ?", (attempt_id,))
        arow = cur.fetchone()
    if not arow:
        return None
    test = get_test(arow["test_id"])

    if test and test.get("test_kind") == "certificate":
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE test_attempts SET finished_at = CURRENT_TIMESTAMP WHERE id = ?", (attempt_id,))
            conn.commit()
        result = _recompute_certificate_result(attempt_id)
        if result:
            record_daily_activity(result["telegram_id"])
            check_and_award_achievements(result["telegram_id"])
        return result

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM test_answers WHERE attempt_id = ? AND is_correct = 1", (attempt_id,))
        score = cur.fetchone()["c"]
        cur.execute("UPDATE test_attempts SET score = ?, finished_at = CURRENT_TIMESTAMP WHERE id = ?", (score, attempt_id))
        conn.commit()
        cur.execute("SELECT * FROM test_attempts WHERE id = ?", (attempt_id,))
        row = cur.fetchone()
        result = dict(row) if row else None
    if result:
        record_daily_activity(result["telegram_id"])
        check_and_award_achievements(result["telegram_id"])
    return result


def is_first_finished_attempt(attempt_id: int) -> bool:
    """Nazorat testida talaba mashq uchun xohlagancha qayta ishlashi mumkin,
    LEKIN oylik REYTINGGA faqat shu (talaba, test) juftligi bo'yicha ENG
    BIRINCHI yakunlangan urinish hisoblanadi (keyingi urinishlar shaxsiy
    mashq — reytingga ta'sir qilmaydi). Shu funksiya berilgan urinish aynan
    o'sha "hisoblanadigan" birinchi urinishmi ekanini tekshiradi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT telegram_id, test_id FROM test_attempts WHERE id = ?", (attempt_id,))
        row = cur.fetchone()
        if not row:
            return False
        cur.execute("""
            SELECT id FROM test_attempts
            WHERE telegram_id = ? AND test_id = ? AND finished_at IS NOT NULL
            ORDER BY started_at ASC, id ASC LIMIT 1
        """, (row["telegram_id"], row["test_id"]))
        first = cur.fetchone()
        return bool(first and first["id"] == attempt_id)


def get_attempt(attempt_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM test_attempts WHERE id = ?", (attempt_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_user_test_results(telegram_id: int):
    """Foydalanuvchining har bir test bo'yicha eng yaxshi natijasini qaytaradi (Natijalar bo'limi uchun)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.id as test_id, t.title, t.subject, MAX(a.score) as best_score, a.total_questions
            FROM test_attempts a
            JOIN tests t ON t.id = a.test_id
            WHERE a.telegram_id = ? AND a.finished_at IS NOT NULL
            GROUP BY t.id
            ORDER BY t.order_num ASC
        """, (telegram_id,))
        return [dict(r) for r in cur.fetchall()]


# ---------- SAMPLE DATA ----------

def add_sample_courses():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM courses")
        count = cur.fetchone()["c"]
        if count == 0:
            cur.execute("""
                INSERT INTO courses (title, subject, resource_type, description, is_free,
                    required_referrals, price, duration_days, duration_text, students_count,
                    thumbnail_emoji, order_num, is_active)
                VALUES ('Mavzulashtirilgan masala kursi', 'Kimyo', 'course', '2000 dan ortiq masalalar',
                    0, 1, 0, NULL, '3 oy', 0, '🧪', 1, 1)
            """)
            course_id = cur.lastrowid
            cur.execute("INSERT INTO paragraphs (course_id, title, order_num) VALUES (?, ?, ?)",
                        (course_id, "1-§. Kirish", 1))
            conn.commit()


# ---------- O'YINLAR: 1x1 BATTLE (ELO reytingli, asinxron) ----------
#
# Savollar ALOHIDA bank sifatida saqlanmaydi — o'qituvchi allaqachon
# to'ldirgan "Testlar" bo'limidagi savol bazasidan, FAN bo'yicha tasodifiy
# tanlab olinadi. Shu sababli Battle rejimi ishlashi uchun o'qituvchi hech
# qanday QO'SHIMCHA kontent tayyorlashi shart emas.

BATTLE_QUESTIONS_PER_ROUND = 5
BATTLE_ELO_K_FACTOR = 32
BATTLE_STARTING_ELO = 1000

ELO_TIERS = [
    (0, "Temir"), (900, "Bronza"), (1100, "Kumush"),
    (1300, "Oltin"), (1500, "Platina"), (1700, "Olmos"),
]


def elo_tier_name(elo: int) -> str:
    name = ELO_TIERS[0][1]
    for threshold, tier in ELO_TIERS:
        if elo >= threshold:
            name = tier
    return name


def get_battle_subjects_with_pool():
    """Battle o'ynash mumkin bo'lgan fanlar ro'yxatini qaytaradi — ya'ni
    kamida BATTLE_QUESTIONS_PER_ROUND ta savoli bor fanlar (aks holda
    o'yin savolsiz qolib, buzilib qoladi)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.subject as subject, COUNT(q.id) as cnt
            FROM tests t JOIN test_questions q ON q.test_id = t.id
            WHERE t.is_active = 1
            GROUP BY t.subject
            HAVING cnt >= ?
        """, (BATTLE_QUESTIONS_PER_ROUND,))
        return [dict(r) for r in cur.fetchall()]


def _pick_random_question_ids(subject: str, count: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT q.id FROM test_questions q
            JOIN tests t ON t.id = q.test_id
            WHERE t.subject = ? AND t.is_active = 1
            ORDER BY RANDOM() LIMIT ?
        """, (subject, count))
        return [r["id"] for r in cur.fetchall()]


def get_or_create_rating(telegram_id: int, subject: str) -> dict:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM game_ratings WHERE telegram_id = ? AND subject = ?", (telegram_id, subject))
        row = cur.fetchone()
        if row:
            return dict(row)
        cur.execute(
            "INSERT INTO game_ratings (telegram_id, subject, elo) VALUES (?, ?, ?)",
            (telegram_id, subject, BATTLE_STARTING_ELO)
        )
        conn.commit()
        return {"telegram_id": telegram_id, "subject": subject, "elo": BATTLE_STARTING_ELO,
                "wins": 0, "losses": 0, "draws": 0}


def join_or_create_battle(telegram_id: int, subject: str) -> dict:
    """Shu fan bo'yicha kutayotgan (2-o'yinchisiz) jang bo'lsa (va u SHU
    o'yinchining o'zi yaratmagan bo'lsa) — o'shanga 2-o'yinchi sifatida
    qo'shiladi. Bo'lmasa, yangi jang (1-o'yinchi sifatida, yangi tasodifiy
    savollar bilan) yaratadi. Natija: {"battle_id", "role", "question_ids"}"""
    get_or_create_rating(telegram_id, subject)  # reyting yozuvi oldindan mavjud bo'lishini ta'minlaydi

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM game_battles
            WHERE subject = ? AND status = 'waiting' AND player1_telegram_id != ?
            ORDER BY created_at ASC LIMIT 1
        """, (subject, telegram_id))
        waiting = cur.fetchone()

        if waiting:
            cur.execute(
                "UPDATE game_battles SET player2_telegram_id = ? WHERE id = ?",
                (telegram_id, waiting["id"])
            )
            conn.commit()
            return {
                "battle_id": waiting["id"],
                "role": "player2",
                "question_ids": json.loads(waiting["question_ids"]),
            }

        question_ids = _pick_random_question_ids(subject, BATTLE_QUESTIONS_PER_ROUND)
        cur.execute("""
            INSERT INTO game_battles (subject, question_ids, player1_telegram_id, status)
            VALUES (?, ?, ?, 'waiting')
        """, (subject, json.dumps(question_ids), telegram_id))
        conn.commit()
        return {"battle_id": cur.lastrowid, "role": "player1", "question_ids": question_ids}


def _calc_elo(rating_a: int, rating_b: int, score_a: float) -> int:
    """Standart ELO formulasi. score_a: 1 (g'alaba), 0.5 (durrang), 0 (mag'lubiyat)."""
    expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    return round(rating_a + BATTLE_ELO_K_FACTOR * (score_a - expected_a))


def submit_battle_result(battle_id: int, telegram_id: int, score: int, time_seconds: int):
    """O'yinchining natijasini yozadi. Ikkala o'yinchi ham tugatgan bo'lsa,
    g'olibni aniqlab, ELO'ni ikkalasi uchun ham yangilaydi va jangni
    'finished' deb belgilaydi. Natija: yangilangan battle dict."""
    players_to_check_achievements = []
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM game_battles WHERE id = ?", (battle_id,))
        battle = cur.fetchone()
        if not battle:
            return None
        battle = dict(battle)

        if battle["player1_telegram_id"] == telegram_id:
            cur.execute("""
                UPDATE game_battles SET player1_score = ?, player1_time_seconds = ?,
                    player1_finished_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (score, time_seconds, battle_id))
        elif battle["player2_telegram_id"] == telegram_id:
            cur.execute("""
                UPDATE game_battles SET player2_score = ?, player2_time_seconds = ?,
                    player2_finished_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (score, time_seconds, battle_id))
        else:
            return None
        conn.commit()

        cur.execute("SELECT * FROM game_battles WHERE id = ?", (battle_id,))
        battle = dict(cur.fetchone())

        both_finished = (
            battle["player1_finished_at"] is not None
            and battle["player2_telegram_id"] is not None
            and battle["player2_finished_at"] is not None
        )
        if both_finished and battle["status"] == "waiting":
            p1, p2 = battle["player1_telegram_id"], battle["player2_telegram_id"]
            r1 = get_or_create_rating(p1, battle["subject"])
            r2 = get_or_create_rating(p2, battle["subject"])

            s1, t1 = battle["player1_score"], battle["player1_time_seconds"]
            s2, t2 = battle["player2_score"], battle["player2_time_seconds"]
            if s1 > s2 or (s1 == s2 and t1 < t2):
                winner, score_a = p1, 1
            elif s2 > s1 or (s2 == s1 and t2 < t1):
                winner, score_a = p2, 0
            else:
                winner, score_a = None, 0.5

            new_elo1 = _calc_elo(r1["elo"], r2["elo"], score_a)
            new_elo2 = _calc_elo(r2["elo"], r1["elo"], 1 - score_a)

            cur.execute("""
                UPDATE game_battles SET status = 'finished', winner_telegram_id = ?,
                    player1_elo_before = ?, player1_elo_after = ?,
                    player2_elo_before = ?, player2_elo_after = ?,
                    finished_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (winner, r1["elo"], new_elo1, r2["elo"], new_elo2, battle_id))

            cur.execute("""
                UPDATE game_ratings SET elo = ?,
                    wins = wins + ?, losses = losses + ?, draws = draws + ?
                WHERE telegram_id = ? AND subject = ?
            """, (
                new_elo1,
                1 if winner == p1 else 0, 1 if winner == p2 else 0, 1 if winner is None else 0,
                p1, battle["subject"]
            ))
            cur.execute("""
                UPDATE game_ratings SET elo = ?,
                    wins = wins + ?, losses = losses + ?, draws = draws + ?
                WHERE telegram_id = ? AND subject = ?
            """, (
                new_elo2,
                1 if winner == p2 else 0, 1 if winner == p1 else 0, 1 if winner is None else 0,
                p2, battle["subject"]
            ))
            conn.commit()

            cur.execute("SELECT * FROM game_battles WHERE id = ?", (battle_id,))
            battle = dict(cur.fetchone())
            players_to_check_achievements = [p1, p2]

    # Yutuq tekshiruvi ATAYLAB yuqoridagi 'with' bloki (va uning ulanishi)
    # yopilgandan KEYIN qilinadi — check_and_award_achievements() o'zi ham
    # pool'dan ulanish so'raydi, ikkalasini bir vaqtda ochiq ushlab turish
    # shart emas.
    for player_id in players_to_check_achievements:
        record_daily_activity(player_id)
        check_and_award_achievements(player_id)

    return battle


def get_battle(battle_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM game_battles WHERE id = ?", (battle_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_my_battles(telegram_id: int, limit: int = 20):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM game_battles
            WHERE player1_telegram_id = ? OR player2_telegram_id = ?
            ORDER BY created_at DESC LIMIT ?
        """, (telegram_id, telegram_id, limit))
        return [dict(r) for r in cur.fetchall()]


def get_my_ratings(telegram_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM game_ratings WHERE telegram_id = ?", (telegram_id,))
        return [dict(r) for r in cur.fetchall()]


def get_battles_needing_notification():
    """Endigina 'finished' bo'lgan, lekin ikkala o'yinchiga ham hali
    Telegram orqali xabar YUBORILMAGAN janglar — bot.py'dagi fon vazifasi
    (background loop) shularni topib, xabar yuborgach 'notified'ga
    belgilaydi (batafsili izoh bot.py'da)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM game_battles WHERE status = 'finished' AND notified = 0")
        return [dict(r) for r in cur.fetchall()]


def mark_battle_notified(battle_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE game_battles SET notified = 1 WHERE id = ?", (battle_id,))
        conn.commit()


def get_battle_leaderboard(subject: str, limit: int = 50):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT gr.telegram_id, u.first_name, gr.elo, gr.wins, gr.losses, gr.draws
            FROM game_ratings gr
            JOIN users u ON u.telegram_id = gr.telegram_id
            WHERE gr.subject = ?
            ORDER BY gr.elo DESC LIMIT ?
        """, (subject, limit))
        return [dict(r) for r in cur.fetchall()]


# ---------- DTM/MILLIY SERTIFIKAT SIMULYATORI ----------

def get_subject_pools():
    """Har bir fan bo'yicha savollar to'plamida jami nechta savol borligini
    qaytaradi — admin simulyator sozlashda "yetarlimi" ni ko'rish uchun.
    Fan nomlari registr va bo'shliqqa sezgir bo'lmasdan birlashtiriladi
    (masalan "Kimyo" va "kimyo " bir xil fan sifatida hisoblanadi)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT TRIM(t.subject) as subject, COUNT(q.id) as question_count
            FROM tests t JOIN test_questions q ON q.test_id = t.id
            GROUP BY LOWER(TRIM(t.subject)) ORDER BY subject
        """)
        return [dict(r) for r in cur.fetchall()]


def get_all_simulators(only_active: bool = True):
    with get_connection() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM simulators WHERE 1=1"
        if only_active:
            query += " AND is_active = 1"
        query += " ORDER BY order_num ASC, id ASC"
        cur.execute(query)
        return [dict(r) for r in cur.fetchall()]


def get_simulator(simulator_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM simulators WHERE id = ?", (simulator_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_simulator(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO simulators (title, description, time_limit_seconds, order_num, is_active)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data.get("title", ""), data.get("description", ""),
            int(data.get("time_limit_seconds", 10800)),
            int(data.get("order_num", 0)), int(data.get("is_active", 1))
        ))
        conn.commit()
        return cur.lastrowid


def update_simulator(simulator_id: int, data: dict):
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        for key in ["title", "description", "time_limit_seconds", "order_num", "is_active"]:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        if fields:
            values.append(simulator_id)
            cur.execute(f"UPDATE simulators SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()


def delete_simulator(simulator_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM simulators WHERE id = ?", (simulator_id,))
        conn.commit()


def get_simulator_subjects(simulator_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM simulator_subjects WHERE simulator_id = ? ORDER BY order_num ASC, id ASC
        """, (simulator_id,))
        return [dict(r) for r in cur.fetchall()]


def add_simulator_subject(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO simulator_subjects (simulator_id, subject, question_count, order_num)
            VALUES (?, ?, ?, ?)
        """, (
            int(data["simulator_id"]), data.get("subject", "").strip(),
            int(data.get("question_count", 10)), int(data.get("order_num", 0))
        ))
        conn.commit()
        return cur.lastrowid


def delete_simulator_subject(entry_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM simulator_subjects WHERE id = ?", (entry_id,))
        conn.commit()


def start_simulator_attempt(telegram_id: int, simulator_id: int):
    """Har bir fandan tasodifiy savollarni tanlab, yangi simulyator urinishini
    boshlaydi. Tanlangan savollar 'suratga olinadi' (snapshot) — shu bilan
    urinish davomida savollar o'zgarmasligi va to'g'ri baholash kafolatlanadi."""
    subjects = get_simulator_subjects(simulator_id)
    if not subjects:
        return None

    selected_questions = []  # [(question_id, subject), ...]
    with get_connection() as conn:
        cur = conn.cursor()
        for s in subjects:
            cur.execute("""
                SELECT q.id FROM test_questions q
                JOIN tests t ON t.id = q.test_id
                WHERE LOWER(TRIM(t.subject)) = LOWER(TRIM(?))
                ORDER BY RANDOM() LIMIT ?
            """, (s["subject"], s["question_count"]))
            for row in cur.fetchall():
                selected_questions.append((row["id"], s["subject"]))

        if not selected_questions:
            return None

        cur.execute("""
            INSERT INTO simulator_attempts (telegram_id, simulator_id, total_questions)
            VALUES (?, ?, ?)
        """, (telegram_id, simulator_id, len(selected_questions)))
        attempt_id = cur.lastrowid

        for idx, (question_id, subject) in enumerate(selected_questions):
            cur.execute("""
                INSERT INTO simulator_attempt_questions (attempt_id, question_id, subject, order_num)
                VALUES (?, ?, ?, ?)
            """, (attempt_id, question_id, subject, idx))
        conn.commit()

    return {"attempt_id": attempt_id, "total_questions": len(selected_questions)}


def get_simulator_attempt_questions(attempt_id: int):
    """Shu urinish uchun 'suratga olingan' savollarni, to'g'ri javobsiz, tartib
    bo'yicha qaytaradi (foydalanuvchiga ko'rsatish uchun xavfsiz)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT saq.order_num, saq.subject, q.id, q.question_text, q.image_url, q.table_data,
                   q.option_1, q.option_2, q.option_3, q.option_4
            FROM simulator_attempt_questions saq
            JOIN test_questions q ON q.id = saq.question_id
            WHERE saq.attempt_id = ?
            ORDER BY saq.order_num ASC
        """, (attempt_id,))
        return [dict(r) for r in cur.fetchall()]


def submit_simulator_answer(telegram_id: int, attempt_id: int, question_id: int, selected_index: int):
    """Oddiy testlardagi bilan bir xil mantiq — coin berish uchun ham xuddi
    shu 'user_question_progress' jadvali ishlatiladi, shuning uchun bir marta
    biror savolga (oddiy testda yoki simulyatorda) to'g'ri javob berilgan
    bo'lsa, ikkinchisida qayta coin berilmaydi (adolatli va izchil)."""
    question = get_question(question_id)
    if not question:
        return {"correct": False, "correct_index": None, "coin_awarded": False}

    is_correct = int(selected_index) == int(question["correct_index"])

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO simulator_answers (attempt_id, question_id, selected_index, is_correct)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(attempt_id, question_id)
            DO UPDATE SET selected_index = excluded.selected_index, is_correct = excluded.is_correct
        """, (attempt_id, question_id, selected_index, 1 if is_correct else 0))
        conn.commit()

    coin_awarded = False
    if is_correct:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM user_question_progress WHERE telegram_id = ? AND question_id = ?",
                        (telegram_id, question_id))
            already = cur.fetchone()
            if already is None:
                cur.execute("INSERT INTO user_question_progress (telegram_id, question_id, coin_awarded) VALUES (?, ?, 1)",
                            (telegram_id, question_id))
                conn.commit()
                coin_awarded = True
        if coin_awarded:
            add_coins(telegram_id, 1)

    return {"correct": is_correct, "correct_index": question["correct_index"], "coin_awarded": coin_awarded}


def finish_simulator_attempt(attempt_id: int):
    """Ball (score) shu yerda, BARCHA saqlangan javoblar bo'yicha qayta
    hisoblanadi — sabab test attempts bilan bir xil (javoblar erkin
    o'zgartirilishi mumkin edi)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM simulator_answers WHERE attempt_id = ? AND is_correct = 1", (attempt_id,))
        score = cur.fetchone()["c"]
        cur.execute("UPDATE simulator_attempts SET score = ?, finished_at = CURRENT_TIMESTAMP WHERE id = ?", (score, attempt_id))
        conn.commit()
        cur.execute("SELECT * FROM simulator_attempts WHERE id = ?", (attempt_id,))
        row = cur.fetchone()
        result = dict(row) if row else None
    if result:
        record_daily_activity(result["telegram_id"])
        check_and_award_achievements(result["telegram_id"])
    return result


def get_simulator_attempt_grid(attempt_id: int):
    """Simulyator urinishidagi HAR BIR savol (javob berilgan yoki
    berilmagan — o'quvchi endi savollarni o'tkazib yuborishi ham mumkin)
    bo'yicha to'g'ri/noto'g'ri/javobsiz holatini qaytaradi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT saq.order_num as order_num, sa.selected_index as selected_index, sa.is_correct as is_correct
            FROM simulator_attempt_questions saq
            LEFT JOIN simulator_answers sa ON sa.question_id = saq.question_id AND sa.attempt_id = saq.attempt_id
            WHERE saq.attempt_id = ?
            ORDER BY saq.order_num ASC
        """, (attempt_id,))
        rows = [dict(r) for r in cur.fetchall()]
    return [
        {
            "question_number": i + 1,
            "answered": r["selected_index"] is not None,
            "is_correct": bool(r["is_correct"]) if r["selected_index"] is not None else None,
        }
        for i, r in enumerate(rows)
    ]


def get_simulator_attempt(attempt_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM simulator_attempts WHERE id = ?", (attempt_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_user_simulator_results(telegram_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT s.id as simulator_id, s.title, MAX(a.score) as best_score, a.total_questions
            FROM simulator_attempts a
            JOIN simulators s ON s.id = a.simulator_id
            WHERE a.telegram_id = ? AND a.finished_at IS NOT NULL
            GROUP BY s.id
            ORDER BY s.order_num ASC
        """, (telegram_id,))
        return [dict(r) for r in cur.fetchall()]


# ---------- NATIJALAR DINAMIKASI (progress grafigi) ----------

def get_user_progress_history(telegram_id: int, limit: int = 30):
    """Oddiy testlar VA simulyator urinishlarini birlashtirib, xronologik
    tartibda (eng eskisidan eng yangisigacha) qaytaradi — 'natijalar
    dinamikasi' grafigini chizish uchun."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT a.finished_at as finished_at, a.score as score,
                   a.total_questions as total_questions, t.title as title, 'test' as kind
            FROM test_attempts a JOIN tests t ON t.id = a.test_id
            WHERE a.telegram_id = ? AND a.finished_at IS NOT NULL

            UNION ALL

            SELECT sa.finished_at as finished_at, sa.score as score,
                   sa.total_questions as total_questions, s.title as title, 'simulator' as kind
            FROM simulator_attempts sa JOIN simulators s ON s.id = sa.simulator_id
            WHERE sa.telegram_id = ? AND sa.finished_at IS NOT NULL

            ORDER BY finished_at ASC
            LIMIT ?
        """, (telegram_id, telegram_id, limit))
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            r["percent"] = round((r["score"] / r["total_questions"]) * 100, 1) if r["total_questions"] else 0
        return rows


# ---------- NAZORAT TESTLARI (talabaga tayinlangan va/yoki kursga bog'langan, oylik reytingli) ----------

def user_has_control_test_access(test_id: int, telegram_id: int) -> bool:
    """Ushbu talaba shu nazorat testiga ADMIN tomonidan to'g'ridan-to'g'ri
    tayinlanganmi (kursdan mustaqil)?"""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM control_test_access WHERE test_id = ? AND telegram_id = ?",
            (test_id, telegram_id)
        )
        return cur.fetchone() is not None


def get_control_test_course_ids(test_id: int):
    """Shu nazorat testi bog'langan kurslarning ID ro'yxati."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT course_id FROM control_test_course_links WHERE test_id = ?", (test_id,))
        return [r["course_id"] for r in cur.fetchall()]


def get_control_test_courses(test_id: int):
    """Bog'langan kurslarning to'liq ma'lumoti (admin panelda ko'rsatish uchun)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.title, c.subject, c.price, c.is_free
            FROM control_test_course_links l
            JOIN courses c ON c.id = l.course_id
            WHERE l.test_id = ?
            ORDER BY c.subject ASC, c.title ASC
        """, (test_id,))
        return [dict(r) for r in cur.fetchall()]


def set_control_test_courses(test_id: int, course_ids):
    """Testga bog'langan kurslar ro'yxatini TO'LIQ almashtiradi (o'qituvchi
    admin panelda belgilaganicha). Bo'sh ro'yxat berilsa — avtomatik ochilish
    o'chadi va test faqat qo'lda tayinlanganlarga ko'rinadi."""
    ids = []
    for cid in (course_ids or []):
        c = safe_int(cid, 0)
        if c > 0:
            ids.append(c)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM control_test_course_links WHERE test_id = ?", (test_id,))
        for cid in set(ids):
            cur.execute(
                "INSERT OR IGNORE INTO control_test_course_links (test_id, course_id) VALUES (?, ?)",
                (test_id, cid)
            )
        # Eski BITTA kursli maydonni ham mos holda yangilab qo'yamiz, shunda
        # eski kod/hisobotlar bilan moslik saqlanadi (birinchi tanlangan kurs).
        cur.execute("UPDATE tests SET course_id = ? WHERE id = ?", (ids[0] if ids else None, test_id))
        conn.commit()
    return {"ok": True, "count": len(set(ids))}


def compute_control_test_access(telegram_id: int, test: dict):
    """Nazorat testiga kirish huquqini hisoblaydi. IKKI MUSTAQIL YO'L bor —
    ulardan BIRI yetarli:

      1) QO'LDA TAYINLASH (control_test_access jadvali). Kursga umuman
         yozilmagan, faqat nazorat testiga qo'shilgan o'quvchilar uchun.
         Bu yo'l obuna muddatidan MUSTAQIL — admin bergan ruxsat o'z-o'zidan
         yopilib qolmaydi.

      2) KURS ORQALI AVTOMATIK. Test bir yoki bir nechta kursga bog'langan
         bo'lsa (control_test_course_links) va o'quvchi shu kurslardan
         BIRORTASIGA kirish huquqiga ega bo'lsa (bepul / referal / amaldagi
         pullik obuna) — test avtomatik ochiladi. Ya'ni o'qituvchi
         o'quvchini bir marta guruhga qo'shsa, shu guruhga bog'langan
         BARCHA nazorat testlari birdaniga ochiladi.
         Obuna muddati tugasa — bu yo'l bilan ochilgan huquq yopiladi
         (lekin 1-yo'l bilan berilgan ruxsat saqlanib qoladi).

    Qaytaradi: {'unlocked': bool, 'reason': 'assigned'|'course'|'locked',
                'course_title': str|None}
    """
    # 1-yo'l — qo'lda tayinlash (eng ustuvor)
    if user_has_control_test_access(test["id"], telegram_id):
        return {"unlocked": True, "reason": "assigned", "course_title": None}

    # 2-yo'l — bog'langan kurslardan birortasi ochiq bo'lsa yetarli.
    course_ids = get_control_test_course_ids(test["id"])
    # Eski (migratsiyadan oldingi) yozuvlar bilan moslik: agar bog'lanish
    # jadvali bo'sh, lekin eski tests.course_id to'ldirilgan bo'lsa — o'shani
    # ishlatamiz, shunda hech bir mavjud sozlama ishlamay qolmaydi.
    if not course_ids and test.get("course_id"):
        course_ids = [test["course_id"]]

    first_locked_title = None
    for cid in course_ids:
        course = get_course(cid)
        if not course:
            continue
        access = compute_course_access(telegram_id, course)
        if access["unlocked"]:
            return {"unlocked": True, "reason": "course", "course_title": course["title"]}
        if first_locked_title is None:
            first_locked_title = course["title"]

    return {"unlocked": False, "reason": "locked", "course_title": first_locked_title}


def get_control_tests_for_user(telegram_id: int):
    """Barcha faol nazorat testlarini, har biri uchun foydalanuvchining
    kirish huquqi bor-yo'qligini (tayinlash yoki kurs orqali) hisoblab qaytaradi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM tests
            WHERE is_control_test = 1 AND is_active = 1
            ORDER BY order_num ASC, id ASC
        """)
        rows = [dict(r) for r in cur.fetchall()]

    result = []
    for t in rows:
        access = compute_control_test_access(telegram_id, t)
        t["unlocked"] = access["unlocked"]
        t["access_reason"] = access["reason"]
        t["course_title"] = access["course_title"]
        t["question_count"] = count_test_questions(t["id"])
        result.append(t)
    return result


# ---------- NAZORAT TESTI — TALABALARNI TAYINLASH (admin) ----------

def assign_control_test_access(test_id: int, telegram_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO control_test_access (test_id, telegram_id) VALUES (?, ?)",
            (test_id, telegram_id)
        )
        conn.commit()


def revoke_control_test_access(test_id: int, telegram_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM control_test_access WHERE test_id = ? AND telegram_id = ?",
            (test_id, telegram_id)
        )
        conn.commit()


def get_control_test_access_list(test_id: int):
    """Shu nazorat testiga tayinlangan barcha talabalarni (ism/username bilan) qaytaradi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT ca.telegram_id as telegram_id, ca.assigned_at as assigned_at,
                   u.first_name as first_name, u.username as username
            FROM control_test_access ca
            LEFT JOIN users u ON u.telegram_id = ca.telegram_id
            WHERE ca.test_id = ?
            ORDER BY ca.assigned_at DESC
        """, (test_id,))
        return [dict(r) for r in cur.fetchall()]


def get_control_test_results(test_id: int):
    """Berilgan BITTA nazorat testini ishlagan har bir talabaning necha
    to'g'ri javob berganini qaytaradi. Talaba testni bir necha marta qayta
    ishlagan bo'lsa ham, faqat REYTINGGA hisoblangan (eng birinchi
    yakunlangan) urinishi ko'rsatiladi — qayta urinishlar (mashq) bu yerda
    hisobga olinmaydi. Natija — ball bo'yicha kamayish tartibida."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            WITH first_attempts AS (
                SELECT a.*,
                       ROW_NUMBER() OVER (
                           PARTITION BY a.telegram_id
                           ORDER BY a.started_at ASC, a.id ASC
                       ) as rn
                FROM test_attempts a
                WHERE a.test_id = ? AND a.finished_at IS NOT NULL
            )
            SELECT u.telegram_id as telegram_id, u.first_name as first_name, u.username as username,
                   fa.score as score, fa.total_questions as total_questions, fa.finished_at as finished_at
            FROM first_attempts fa
            JOIN users u ON u.telegram_id = fa.telegram_id
            WHERE fa.rn = 1
            ORDER BY fa.score DESC, fa.finished_at ASC
        """, (test_id,))
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            r["percent"] = round((r["score"] / r["total_questions"]) * 100, 1) if r["total_questions"] else 0
        return rows


def get_attempt_rank(attempt_id: int):
    """Berilgan (Attestatsiya) urinish uchun — shu variantni ishlagan
    barcha talabalar orasida nechanchi o'rinda ekanini qaytaradi
    (@biologiyamockbot'dagi "80-o'rin / 90 talaba ichida" bilan bir xil
    mantiq). get_control_test_results bilan bir xil "faqat birinchi
    yakunlangan urinish hisoblanadi" qoidasidan foydalanadi. Agar bu urinish
    reytingga hisoblanmasa (mashq/qayta urinish) — None qaytaradi."""
    attempt = get_attempt(attempt_id)
    if not attempt or not attempt.get("finished_at"):
        return None
    if not is_first_finished_attempt(attempt_id):
        return None
    ranked = get_control_test_results(attempt["test_id"])
    for i, r in enumerate(ranked):
        if r["telegram_id"] == attempt["telegram_id"]:
            return {"rank": i + 1, "total": len(ranked)}
    return None


def get_attempt_answers_grid(attempt_id: int):
    """Bitta urinishning HAR BIR savoli (javob berilgan yoki berilmagan —
    o'quvchi endi savollar orasida erkin harakatlanib, ba'zilarini
    o'tkazib yuborishi ham mumkin) bo'yicha to'g'ri/noto'g'ri/javobsiz
    holatini, savol tartib raqami bilan qaytaradi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT test_id FROM test_attempts WHERE id = ?", (attempt_id,))
        attempt_row = cur.fetchone()
        if not attempt_row:
            return []
        test_id = attempt_row["test_id"]
        cur.execute("""
            SELECT q.order_num as order_num, ta.selected_index as selected_index, ta.is_correct as is_correct
            FROM test_questions q
            LEFT JOIN test_answers ta ON ta.question_id = q.id AND ta.attempt_id = ?
            WHERE q.test_id = ?
            ORDER BY q.order_num ASC, q.id ASC
        """, (attempt_id, test_id))
        rows = [dict(r) for r in cur.fetchall()]
    return [
        {
            "question_number": i + 1,
            "answered": r["selected_index"] is not None,
            "is_correct": bool(r["is_correct"]) if r["selected_index"] is not None else None,
        }
        for i, r in enumerate(rows)
    ]


def get_control_test_monthly_leaderboard(year: int, month: int, limit: int = 100):
    """Berilgan oy uchun nazorat testlari reytingini qaytaradi.
    Talaba bitta nazorat testini MASHQ uchun xohlagancha qayta ishlashi
    mumkin — lekin REYTINGGA har (talaba, test) juftligi bo'yicha faqat ENG
    BIRINCHI yakunlangan urinish kiritiladi (ROW_NUMBER() bilan tanlanadi).
    Keyingi qayta urinishlar shaxsiy mashq hisoblanadi va natijaga ta'sir
    qilmaydi. Saralash mezoni: 1) o'rtacha foiz natija (yuqori — yaxshi),
    2) teng natijada — o'rtacha sarflangan vaqt (kam — yaxshi, ya'ni
    bir xil ball to'plagan ikki talaba orasida tezroq ishlagani yuqorida turadi)."""
    month_str = f"{year:04d}-{month:02d}"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            WITH first_attempts AS (
                SELECT a.*,
                       ROW_NUMBER() OVER (
                           PARTITION BY a.telegram_id, a.test_id
                           ORDER BY a.started_at ASC, a.id ASC
                       ) as rn
                FROM test_attempts a
                JOIN tests t ON t.id = a.test_id
                WHERE t.is_control_test = 1 AND a.finished_at IS NOT NULL
            )
            SELECT u.telegram_id as telegram_id, u.first_name as first_name,
                   AVG(CAST(fa.score AS FLOAT) / NULLIF(fa.total_questions, 0)) * 100 as avg_percent,
                   AVG((julianday(fa.finished_at) - julianday(fa.started_at)) * 86400) as avg_seconds,
                   COUNT(fa.id) as attempts_count
            FROM first_attempts fa
            JOIN users u ON u.telegram_id = fa.telegram_id
            WHERE fa.rn = 1
              AND strftime('%Y-%m', fa.finished_at) = ?
            GROUP BY u.telegram_id
            ORDER BY avg_percent DESC, avg_seconds ASC
            LIMIT ?
        """, (month_str, limit))
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            r["avg_percent"] = round(r["avg_percent"] or 0, 1)
            r["avg_seconds"] = round(r["avg_seconds"] or 0)
        return rows


def get_my_control_test_rank(telegram_id: int, year: int, month: int):
    """Foydalanuvchining shu oydagi nazorat testlari reytingidagi o'rnini
    topadi (agar u shu oy hech narsa topshirmagan bo'lsa — None)."""
    leaderboard = get_control_test_monthly_leaderboard(year, month, limit=100000)
    for idx, row in enumerate(leaderboard):
        if row["telegram_id"] == telegram_id:
            return {
                "rank": idx + 1,
                "avg_percent": row["avg_percent"],
                "avg_seconds": row["avg_seconds"],
                "attempts_count": row["attempts_count"],
                "total_participants": len(leaderboard),
            }
    return None


def get_test_kind_monthly_leaderboard(test_kind: str, year: int, month: int, limit: int = 100):
    """get_control_test_monthly_leaderboard bilan bir xil mantiq, lekin
    `is_control_test` o'rniga `test_kind` bo'yicha filtrlaydi — Attestatsiya
    (`attestation`), Milliy sertifikat (`certificate`) va Mavzuli testlar
    (`practice`) uchun alohida oylik reyting olish imkonini beradi."""
    month_str = f"{year:04d}-{month:02d}"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            WITH first_attempts AS (
                SELECT a.*,
                       ROW_NUMBER() OVER (
                           PARTITION BY a.telegram_id, a.test_id
                           ORDER BY a.started_at ASC, a.id ASC
                       ) as rn
                FROM test_attempts a
                JOIN tests t ON t.id = a.test_id
                WHERE t.test_kind = ? AND a.finished_at IS NOT NULL
            )
            SELECT u.telegram_id as telegram_id, u.first_name as first_name,
                   AVG(CAST(fa.score AS FLOAT) / NULLIF(fa.total_questions, 0)) * 100 as avg_percent,
                   AVG((julianday(fa.finished_at) - julianday(fa.started_at)) * 86400) as avg_seconds,
                   COUNT(fa.id) as attempts_count
            FROM first_attempts fa
            JOIN users u ON u.telegram_id = fa.telegram_id
            WHERE fa.rn = 1
              AND strftime('%Y-%m', fa.finished_at) = ?
            GROUP BY u.telegram_id
            ORDER BY avg_percent DESC, avg_seconds ASC
            LIMIT ?
        """, (test_kind, month_str, limit))
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            r["avg_percent"] = round(r["avg_percent"] or 0, 1)
            r["avg_seconds"] = round(r["avg_seconds"] or 0)
        return rows


def get_my_test_kind_rank(telegram_id: int, test_kind: str, year: int, month: int):
    """Foydalanuvchining shu oydagi (attestatsiya/sertifikat/mavzuli)
    reytingidagi o'rnini topadi."""
    leaderboard = get_test_kind_monthly_leaderboard(test_kind, year, month, limit=100000)
    for idx, row in enumerate(leaderboard):
        if row["telegram_id"] == telegram_id:
            return {
                "rank": idx + 1,
                "avg_percent": row["avg_percent"],
                "avg_seconds": row["avg_seconds"],
                "attempts_count": row["attempts_count"],
                "total_participants": len(leaderboard),
            }
    return None


# ================================================================
# VAZIFA TOPSHIRISH (uy vazifasi rasmlari)
# ================================================================

HOMEWORK_MAX_SCORE = 10.0  # bitta topshiriq uchun maksimal ball (o'qituvchi 0..10 qo'yadi)


# ---------- Fanlar (admin boshqaradi) ----------

def get_homework_subjects(only_active: bool = True):
    with get_connection() as conn:
        cur = conn.cursor()
        query = "SELECT * FROM homework_subjects"
        if only_active:
            query += " WHERE is_active = 1"
        query += " ORDER BY order_num ASC, id ASC"
        cur.execute(query)
        return [dict(r) for r in cur.fetchall()]


def get_homework_subject(subject_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM homework_subjects WHERE id = ?", (subject_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_homework_subject(data: dict) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO homework_subjects (title, subtitle, icon, color_key, paragraph_count,
                                           deadline_days, order_num, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("title", ""), data.get("subtitle") or "", data.get("icon") or "🧪",
            data.get("color_key") or "teal", safe_int(data.get("paragraph_count"), 0),
            safe_int(data.get("deadline_days"), 7), safe_int(data.get("order_num"), 0),
            safe_int(data.get("is_active"), 1),
        ))
        conn.commit()
        subject_id = cur.lastrowid
    if "course_ids" in data:
        set_homework_subject_courses(subject_id, data.get("course_ids") or [])
    return subject_id


def update_homework_subject(subject_id: int, data: dict):
    numeric = {"paragraph_count": 0, "deadline_days": 7, "order_num": 0, "is_active": 1,
               "default_start_paragraph": 1}
    with get_connection() as conn:
        cur = conn.cursor()
        fields, values = [], []
        for key in ["title", "subtitle", "icon", "color_key", "paragraph_count",
                    "deadline_days", "order_num", "is_active", "default_start_paragraph"]:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(safe_int(data[key], numeric[key]) if key in numeric else data[key])
        if fields:
            values.append(subject_id)
            cur.execute(f"UPDATE homework_subjects SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()
    if "course_ids" in data:
        set_homework_subject_courses(subject_id, data.get("course_ids") or [])


def delete_homework_subject(subject_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM homework_subjects WHERE id = ?", (subject_id,))
        conn.commit()


def get_homework_subject_course_ids(subject_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT course_id FROM homework_subject_courses WHERE subject_id = ?", (subject_id,))
        return [r["course_id"] for r in cur.fetchall()]


def set_homework_subject_courses(subject_id: int, course_ids):
    ids = {safe_int(c, 0) for c in (course_ids or []) if safe_int(c, 0) > 0}
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM homework_subject_courses WHERE subject_id = ?", (subject_id,))
        for cid in ids:
            cur.execute(
                "INSERT OR IGNORE INTO homework_subject_courses (subject_id, course_id) VALUES (?, ?)",
                (subject_id, cid)
            )
        conn.commit()
    return {"ok": True, "count": len(ids)}


def user_can_access_homework_subject(telegram_id: int, subject_id: int) -> bool:
    """O'quvchi shu fanga kira oladimi — bog'langan kurslardan BIRORTASIGA
    yozilgan bo'lsa yetarli. Hech qanday kurs bog'lanmagan bo'lsa, fan
    hammaga ochiq deb qaraladi (masalan bepul/ochiq guruh uchun)."""
    course_ids = get_homework_subject_course_ids(subject_id)
    if not course_ids:
        return True
    for cid in course_ids:
        course = get_course(cid)
        if course and compute_course_access(telegram_id, course)["unlocked"]:
            return True
    return False


# ---------- Topshiriqlar: ketma-ket ochilish va holat ----------

def get_homework_submission(subject_id: int, telegram_id: int, paragraph_number: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM homework_submissions
            WHERE subject_id = ? AND telegram_id = ? AND paragraph_number = ?
        """, (subject_id, telegram_id, paragraph_number))
        row = cur.fetchone()
        return dict(row) if row else None


def get_homework_photos(submission_id: int):
    """Topshiriq rasmlari (xom holda). Ko'rish havolasi (`view_url`) router
    qatlamida, imzo bilan qo'shiladi — chunki maxfiy kalit shu yerda emas."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, photo_url, order_num, telegram_file_id, storage
            FROM homework_photos
            WHERE submission_id = ? ORDER BY order_num ASC, id ASC
        """, (submission_id,))
        rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        r["in_telegram"] = bool(r.get("telegram_file_id"))
        r.pop("telegram_file_id", None)  # file_id hech qachon frontendga chiqmaydi
    return rows


def get_homework_photo_record(photo_id: int):
    """Bitta rasm yozuvi + kimga tegishli ekani (kirish huquqini tekshirish uchun)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.*, s.telegram_id AS owner_telegram_id, s.subject_id, s.paragraph_number
            FROM homework_photos p
            JOIN homework_submissions s ON s.id = p.submission_id
            WHERE p.id = ?
        """, (photo_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def _homework_submissions_map(subject_id: int, telegram_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM homework_submissions
            WHERE subject_id = ? AND telegram_id = ?
        """, (subject_id, telegram_id))
        return {r["paragraph_number"]: dict(r) for r in cur.fetchall()}


def get_homework_start_paragraph(telegram_id: int, subject_id: int) -> int:
    """O'quvchi shu fanda NECHANCHI paragrafdan boshlashi kerak.

    Avval shaxsiy yozuv qidiriladi (o'qituvchi "hozirgi o'quvchilarga
    qo'llash" tugmasi orqali yozgan bo'lishi mumkin). Topilmasa —
    fanning standart qiymati, u ham bo'lmasa 1."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT start_paragraph FROM homework_student_start
            WHERE subject_id = ? AND telegram_id = ?
        """, (subject_id, telegram_id))
        row = cur.fetchone()
    if row:
        return max(1, safe_int(row["start_paragraph"], 1))
    subject = get_homework_subject(subject_id)
    return max(1, safe_int((subject or {}).get("default_start_paragraph"), 1))


def set_homework_student_start(subject_id: int, telegram_id: int, start_paragraph: int):
    """Bitta o'quvchi uchun boshlanish paragrafini belgilaydi."""
    value = max(1, safe_int(start_paragraph, 1))
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO homework_student_start (subject_id, telegram_id, start_paragraph)
            VALUES (?, ?, ?)
            ON CONFLICT(subject_id, telegram_id)
            DO UPDATE SET start_paragraph = excluded.start_paragraph, set_at = CURRENT_TIMESTAMP
        """, (subject_id, telegram_id, value))
        conn.commit()
    return {"ok": True, "start_paragraph": value}


def clear_homework_student_start(subject_id: int, telegram_id: int):
    """Shaxsiy boshlanish nuqtasini bekor qiladi — o'quvchi yana fanning
    standart nuqtasidan (odatda 1-paragrafdan) boshlaydi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM homework_student_start WHERE subject_id = ? AND telegram_id = ?",
                    (subject_id, telegram_id))
        conn.commit()
    return {"ok": True}


def apply_homework_start_to_current_students(subject_id: int, start_paragraph: int):
    """AYNAN SHU PAYTDA fanga kirish huquqiga ega bo'lgan har bir
    o'quvchiga shaxsiy boshlanish nuqtasini yozadi.

    Shundan KEYIN qo'shilgan yangi o'quvchilarda bu yozuv bo'lmaydi va
    ular 1-paragrafdan boshlaydi — o'qituvchi aynan shuni xohlaydi:
    "hozirgilar 60-dan davom etsin, yangilari boshidan kelaversin"."""
    value = max(1, safe_int(start_paragraph, 1))
    course_ids = get_homework_subject_course_ids(subject_id)

    telegram_ids = set()
    with get_connection() as conn:
        cur = conn.cursor()
        if course_ids:
            placeholders = ",".join("?" for _ in course_ids)
            cur.execute(f"SELECT DISTINCT telegram_id FROM enrollments WHERE course_id IN ({placeholders})",
                        course_ids)
        else:
            # Fan hech qaysi kursga bog'lanmagan (hammaga ochiq) —
            # botdan foydalangan barcha o'quvchilar hisobga olinadi.
            cur.execute("SELECT telegram_id FROM users")
        telegram_ids = {r["telegram_id"] for r in cur.fetchall()}

    for tid in telegram_ids:
        set_homework_student_start(subject_id, tid, value)
    return {"ok": True, "applied_to": len(telegram_ids), "start_paragraph": value}


def get_homework_student_starts(subject_id: int):
    """Fan bo'yicha kim qaysi paragrafdan boshlagani (admin ro'yxati uchun)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT s.telegram_id, s.start_paragraph, s.set_at,
                   u.first_name, u.username
            FROM homework_student_start s
            LEFT JOIN users u ON u.telegram_id = s.telegram_id
            WHERE s.subject_id = ?
            ORDER BY s.start_paragraph DESC, u.first_name ASC
        """, (subject_id,))
        return [dict(r) for r in cur.fetchall()]


def compute_homework_paragraphs(telegram_id: int, subject_id: int):
    """Fandagi paragraflar ro'yxatini, har birining HOLATI va QULF
    holati bilan qaytaradi.

    BOSHLANISH NUQTASI: ro'yxat o'quvchining shaxsiy boshlanish
    paragrafidan boshlanadi (masalan 60-dan). Undan OLDINGILARI umuman
    qaytarilmaydi — o'quvchi ularni ko'rmaydi ham, chunki u mavzularni
    allaqachon (tizimdan tashqarida) topshirib bo'lgan.

    KETMA-KET OCHILISH QOIDASI O'ZGARMAYDI: boshlanish paragrafi doim
    ochiq, undan keyingisi esa faqat oldingisi "Vazifalar to'liq
    yuklandi" deb YAKUNLANGANDA ochiladi. O'qituvchi qayta ishlashga
    qaytargan (rejected) topshiriq yakunlangan hisoblanmaydi —
    keyingisi yopiladi.

    ESKI BOSHLANISH NUQTASI OSTIDA QOLGAN ISH YO'QOLMAYDI: agar admin
    boshlanish nuqtasini keyinroq PASAYTIRSA (masalan 61 dan 60 ga),
    yangi qo'shilgan 60-paragraf hech qachon so'ralmagani uchun bo'sh
    bo'ladi va oddiy zanjir bo'yicha undan keyingi (aslida allaqachon
    topshirilgan) 61-ni ham qulflab qo'yardi. Shu sababli paragraf N
    o'zining submission yozuviga ega bo'lsa — u zanjirdan qat'i nazar
    HAR DOIM ochiq hisoblanadi (ish "yo'qolib" ko'rinmasin)."""
    subject = get_homework_subject(subject_id)
    if not subject:
        return []
    total = safe_int(subject.get("paragraph_count"), 0)
    start = get_homework_start_paragraph(telegram_id, subject_id)
    if start > total:
        return []

    subs = _homework_submissions_map(subject_id, telegram_id)

    result = []
    prev_done = True  # boshlanish paragrafi doim ochiq
    for n in range(start, total + 1):
        sub = subs.get(n)
        status = sub["status"] if sub else "empty"
        is_done = status in ("submitted", "graded")
        unlocked = prev_done or (sub is not None)
        photo_count = len(get_homework_photos(sub["id"])) if sub else 0
        result.append({
            "paragraph_number": n,
            "status": status,
            "unlocked": unlocked,
            "photo_count": photo_count,
            "teacher_score": sub.get("teacher_score") if sub else None,
            "teacher_comment": sub.get("teacher_comment") if sub else None,
            "submitted_at": sub.get("submitted_at") if sub else None,
        })
        prev_done = is_done
    return result


def _ensure_homework_submission(subject_id: int, telegram_id: int, paragraph_number: int) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR IGNORE INTO homework_submissions (subject_id, telegram_id, paragraph_number, status)
            VALUES (?, ?, ?, 'draft')
        """, (subject_id, telegram_id, paragraph_number))
        conn.commit()
        cur.execute("""
            SELECT id FROM homework_submissions
            WHERE subject_id = ? AND telegram_id = ? AND paragraph_number = ?
        """, (subject_id, telegram_id, paragraph_number))
        return cur.fetchone()["id"]


def is_homework_paragraph_unlocked(telegram_id: int, subject_id: int, paragraph_number: int) -> bool:
    """Serverda ham qulfni tekshiramiz — frontend chetlab o'tilsa ham
    o'quvchi tartibni buzib, oldinga o'tib ketolmaydi.

    Boshlanish nuqtasidan OLDINGI paragraflar ham yopiq hisoblanadi
    (ular o'quvchiga umuman ko'rsatilmaydi)."""
    start = get_homework_start_paragraph(telegram_id, subject_id)
    if paragraph_number < start:
        return False
    if paragraph_number == start:
        return True
    prev = get_homework_submission(subject_id, telegram_id, paragraph_number - 1)
    return bool(prev and prev["status"] in ("submitted", "graded"))


def add_homework_photo(subject_id: int, telegram_id: int, paragraph_number: int, photo_url: str,
                       telegram_file_id: str = None, telegram_message_id: int = None,
                       storage: str = "local"):
    """Rasmni topshiriqqa qo'shadi.

    storage='telegram' bo'lsa — fayl serverda saqlanmaydi, faqat Telegram
    bergan file_id yoziladi (server xotirasi tejaladi). 'local' bo'lsa —
    eski usul: fayl diskda, photo_url orqali beriladi."""
    submission_id = _ensure_homework_submission(subject_id, telegram_id, paragraph_number)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(order_num), -1) + 1 AS nxt FROM homework_photos WHERE submission_id = ?",
                    (submission_id,))
        nxt = cur.fetchone()["nxt"]
        cur.execute("""
            INSERT INTO homework_photos (submission_id, photo_url, order_num,
                                         telegram_file_id, telegram_message_id, storage)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (submission_id, photo_url, nxt, telegram_file_id, telegram_message_id, storage))
        # Qayta ishlashga qaytarilgan topshiriqqa yangi rasm qo'shilsa —
        # u yana "yuklanmoqda" holatiga qaytadi.
        cur.execute("UPDATE homework_submissions SET status = 'draft' WHERE id = ? AND status = 'rejected'",
                    (submission_id,))
        conn.commit()
    return {"ok": True, "submission_id": submission_id}


def delete_homework_photo(photo_id: int, telegram_id: int):
    """Rasmni faqat EGASI o'chira oladi va faqat hali baholanmagan bo'lsa.
    Qaytaradi: {'ok': bool, 'telegram_message_id': int|None, 'photo_url': str|None}
    — chaqiruvchi kod arxivdagi xabarni va diskdagi faylni ham tozalaydi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.id, p.telegram_message_id, p.photo_url FROM homework_photos p
            JOIN homework_submissions s ON s.id = p.submission_id
            WHERE p.id = ? AND s.telegram_id = ? AND s.status != 'graded'
        """, (photo_id, telegram_id))
        row = cur.fetchone()
        if not row:
            return {"ok": False, "detail": "Bu rasmni o'chirib bo'lmaydi"}
        info = dict(row)
        cur.execute("DELETE FROM homework_photos WHERE id = ?", (photo_id,))
        conn.commit()
    return {"ok": True,
            "telegram_message_id": info.get("telegram_message_id"),
            "photo_url": info.get("photo_url")}


def get_expired_homework_photos(retention_days: int = 90):
    """Baholanganiga `retention_days` kundan ko'p vaqt o'tgan topshiriqlar
    RASMLARI. Ball va izoh tegilmaydi — faqat fayllar tozalanadi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.id, p.photo_url, p.telegram_message_id, p.storage
            FROM homework_photos p
            JOIN homework_submissions s ON s.id = p.submission_id
            WHERE s.status = 'graded'
              AND s.graded_at IS NOT NULL
              AND julianday('now') - julianday(s.graded_at) > ?
        """, (retention_days,))
        return [dict(r) for r in cur.fetchall()]


def delete_homework_photo_rows(photo_ids):
    if not photo_ids:
        return 0
    with get_connection() as conn:
        cur = conn.cursor()
        placeholders = ",".join("?" for _ in photo_ids)
        cur.execute(f"DELETE FROM homework_photos WHERE id IN ({placeholders})", list(photo_ids))
        conn.commit()
        return cur.rowcount


def submit_homework_paragraph(subject_id: int, telegram_id: int, paragraph_number: int):
    """O'quvchi "Vazifalar to'liq yuklandi" tugmasini bosdi — topshiriq
    yakunlanadi va shu bilan KEYINGI paragraf ochiladi."""
    submission_id = _ensure_homework_submission(subject_id, telegram_id, paragraph_number)
    if not get_homework_photos(submission_id):
        return {"ok": False, "detail": "Avval kamida bitta rasm yuklang"}
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE homework_submissions
            SET status = 'submitted', submitted_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (submission_id,))
        conn.commit()
    record_daily_activity(telegram_id)
    return {"ok": True, "status": "submitted"}


# ---------- O'qituvchi: baholash ----------

def get_homework_pending_submissions(subject_id: int = None):
    """Baholanmagan (topshirilgan) vazifalar navbati."""
    with get_connection() as conn:
        cur = conn.cursor()
        query = """
            SELECT s.*, hs.title AS subject_title, hs.icon AS subject_icon,
                   u.first_name, u.username
            FROM homework_submissions s
            JOIN homework_subjects hs ON hs.id = s.subject_id
            LEFT JOIN users u ON u.telegram_id = s.telegram_id
            WHERE s.status = 'submitted'
        """
        params = []
        if subject_id:
            query += " AND s.subject_id = ?"
            params.append(subject_id)
        query += " ORDER BY s.submitted_at ASC"
        cur.execute(query, params)
        rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        r["photos"] = get_homework_photos(r["id"])
    return rows


def grade_homework_submission(submission_id: int, teacher_score, teacher_comment: str,
                              graded_by: int, reject: bool = False):
    """O'qituvchi 0..10 ball qo'yadi yoki qayta ishlashga qaytaradi.

    Natijada shu submission haqida (telegram_id, fan nomi, paragraf raqami,
    ball, izoh) ma'lumotlarini ham qaytaradi — chaqiruvchi (admin_homework.py)
    shu asosda o'quvchiga Telegram orqali xabar yubora oladi."""
    with get_connection() as conn:
        cur = conn.cursor()
        if reject:
            cur.execute("""
                UPDATE homework_submissions
                SET status = 'rejected', teacher_comment = ?, graded_by = ?, graded_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (teacher_comment or "", graded_by, submission_id))
        else:
            score = max(0.0, min(HOMEWORK_MAX_SCORE, float(teacher_score or 0)))
            cur.execute("""
                UPDATE homework_submissions
                SET status = 'graded', teacher_score = ?, teacher_comment = ?,
                    graded_by = ?, graded_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (score, teacher_comment or "", graded_by, submission_id))
        conn.commit()
        cur.execute("""
            SELECT s.telegram_id AS telegram_id, s.subject_id AS subject_id,
                   s.paragraph_number AS paragraph_number, s.status AS status,
                   s.teacher_score AS teacher_score, s.teacher_comment AS teacher_comment,
                   hs.title AS subject_title
            FROM homework_submissions s
            JOIN homework_subjects hs ON hs.id = s.subject_id
            WHERE s.id = ?
        """, (submission_id,))
        row = cur.fetchone()
    result = dict(row) if row else {}
    result["ok"] = True
    return result


def get_user_homework_summary(telegram_id: int, subject_id: int = None):
    """O'quvchining vazifa bo'yicha umumiy ko'rsatkichi (o'z natijalari
    ekranida va reytingda ishlatiladi)."""
    with get_connection() as conn:
        cur = conn.cursor()
        query = """
            SELECT COUNT(*) AS submitted_count,
                   SUM(CASE WHEN status = 'graded' THEN 1 ELSE 0 END) AS graded_count,
                   AVG(CASE WHEN status = 'graded' THEN teacher_score END) AS avg_score
            FROM homework_submissions
            WHERE telegram_id = ? AND status IN ('submitted', 'graded')
        """
        params = [telegram_id]
        if subject_id:
            query += " AND subject_id = ?"
            params.append(subject_id)
        cur.execute(query, params)
        row = dict(cur.fetchone())
    return {
        "submitted_count": row["submitted_count"] or 0,
        "graded_count": row["graded_count"] or 0,
        "avg_score": round(row["avg_score"], 2) if row["avg_score"] is not None else None,
    }


# ---------- Kechikkanlar (ogohlantirish uchun) ----------

def get_homework_late_students(subject_id: int = None):
    """Vazifani KECHIKTIRGAN o'quvchilar ro'yxati.

    "Kechikkan" deb hisoblanadi: o'quvchi shu fanga kirish huquqiga ega
    (kursga yozilgan), lekin navbatdagi ochiq paragrafni belgilangan
    kun (deadline_days) ichida topshirmagan. Hech narsa boshlamagan
    o'quvchi ham — ro'yxatga kiradi (1-paragraf kutilmoqda)."""
    subjects = get_homework_subjects(only_active=True)
    if subject_id:
        subjects = [s for s in subjects if s["id"] == subject_id]

    now = datetime.datetime.utcnow()
    late = []
    for subject in subjects:
        deadline_days = safe_int(subject.get("deadline_days"), 7)
        course_ids = get_homework_subject_course_ids(subject["id"])
        # Fanga bog'langan kurslarga yozilgan barcha o'quvchilar
        candidates = {}
        with get_connection() as conn:
            cur = conn.cursor()
            if course_ids:
                placeholders = ",".join("?" for _ in course_ids)
                cur.execute(f"""
                    SELECT DISTINCT e.telegram_id, u.first_name, u.username
                    FROM enrollments e LEFT JOIN users u ON u.telegram_id = e.telegram_id
                    WHERE e.course_id IN ({placeholders})
                """, course_ids)
            else:
                cur.execute("""
                    SELECT DISTINCT s.telegram_id, u.first_name, u.username
                    FROM homework_submissions s LEFT JOIN users u ON u.telegram_id = s.telegram_id
                    WHERE s.subject_id = ?
                """, (subject["id"],))
            for r in cur.fetchall():
                candidates[r["telegram_id"]] = dict(r)

        for tid, info in candidates.items():
            paragraphs = compute_homework_paragraphs(tid, subject["id"])
            # Navbatdagi ochiq, lekin hali topshirilmagan paragraf
            pending = next((p for p in paragraphs
                            if p["unlocked"] and p["status"] not in ("submitted", "graded")), None)
            if not pending:
                continue  # hammasini topshirgan

            # Oxirgi faollik: shu fandagi eng so'nggi topshirish sanasi
            last = None
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT MAX(submitted_at) AS last_at FROM homework_submissions
                    WHERE subject_id = ? AND telegram_id = ? AND submitted_at IS NOT NULL
                """, (subject["id"], tid))
                row = cur.fetchone()
                last = row["last_at"] if row else None

            if last:
                try:
                    last_dt = datetime.datetime.fromisoformat(last)
                except ValueError:
                    last_dt = now
                days_idle = (now - last_dt).days
            else:
                days_idle = deadline_days + 1  # hech narsa topshirmagan — darhol kechikkan

            if days_idle >= deadline_days:
                late.append({
                    "telegram_id": tid,
                    "first_name": info.get("first_name") or "Foydalanuvchi",
                    "username": info.get("username"),
                    "subject_id": subject["id"],
                    "subject_title": subject["title"],
                    "waiting_paragraph": pending["paragraph_number"],
                    "days_idle": days_idle,
                    "last_submitted_at": last,
                })
    late.sort(key=lambda x: x["days_idle"], reverse=True)
    return late


# ---------- 50/50 UMUMLASHGAN OYLIK REYTING ----------

# Nazorat testi va vazifa natijasining reytingdagi ulushi (foizda).
# O'qituvchi kelishuviga ko'ra standart 50/50.
RANKING_TEST_WEIGHT = 50
RANKING_HOMEWORK_WEIGHT = 50


def get_homework_monthly_scores(year: int, month: int):
    """Berilgan oyda BAHOLANGAN vazifalar bo'yicha har bir o'quvchining
    o'rtacha foizi (0..100). O'qituvchi 0..10 ball qo'yadi, shuning uchun
    foizga aylantirish uchun 10 ga bo'lib 100 ga ko'paytiriladi."""
    month_str = f"{year:04d}-{month:02d}"
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT s.telegram_id,
                   AVG(s.teacher_score) AS avg_score,
                   COUNT(*) AS graded_count
            FROM homework_submissions s
            WHERE s.status = 'graded'
              AND s.teacher_score IS NOT NULL
              AND strftime('%Y-%m', COALESCE(s.submitted_at, s.graded_at)) = ?
            GROUP BY s.telegram_id
        """, (month_str,))
        rows = [dict(r) for r in cur.fetchall()]
    return {
        r["telegram_id"]: {
            "homework_percent": round((r["avg_score"] / HOMEWORK_MAX_SCORE) * 100, 1),
            "graded_count": r["graded_count"],
            "avg_score": round(r["avg_score"], 2),
        }
        for r in rows
    }


def get_combined_monthly_leaderboard(year: int, month: int, limit: int = 100):
    """OY YAKUNIY REYTINGI — nazorat testi va vazifa natijasini BIRLASHTIRIB
    hisoblaydi (standart 50% + 50%).

    Har bir o'quvchi uchun:
      test_percent     — shu oydagi nazorat testlarining o'rtacha foizi
      homework_percent — shu oyda baholangan vazifalarning o'rtacha foizi
      total_score      — ikkalasining og'irliklangan yig'indisi (0..100)

    Bir tomoni umuman yo'q bo'lsa (masalan test topshirmagan) — o'sha
    qism 0 deb olinadi, chunki reyting IKKALA mehnatni ham talab qiladi.
    Bu — chegirma berishda adolatli: faqat test ishlagan yoki faqat
    vazifa tashlagan o'quvchi to'liq bajarganidan yuqori turmaydi."""
    test_rows = get_control_test_monthly_leaderboard(year, month, limit=100000)
    test_by_id = {r["telegram_id"]: r for r in test_rows}
    hw_by_id = get_homework_monthly_scores(year, month)

    all_ids = set(test_by_id) | set(hw_by_id)

    # Ism/username ni bitta so'rovda olib qo'yamiz (har bir o'quvchi uchun
    # alohida so'rov yubormaslik uchun).
    users_by_id = {}
    if all_ids:
        with get_connection() as conn:
            cur = conn.cursor()
            placeholders = ",".join("?" for _ in all_ids)
            cur.execute(f"SELECT telegram_id, first_name, username FROM users WHERE telegram_id IN ({placeholders})",
                        list(all_ids))
            users_by_id = {r["telegram_id"]: dict(r) for r in cur.fetchall()}

    result = []
    for tid in all_ids:
        t = test_by_id.get(tid)
        h = hw_by_id.get(tid)
        test_percent = t["avg_percent"] if t else 0.0
        hw_percent = h["homework_percent"] if h else 0.0
        total = (test_percent * RANKING_TEST_WEIGHT + hw_percent * RANKING_HOMEWORK_WEIGHT) / 100.0

        user = users_by_id.get(tid, {})
        result.append({
            "telegram_id": tid,
            "first_name": (t or {}).get("first_name") or user.get("first_name") or "Foydalanuvchi",
            "username": user.get("username"),
            "test_percent": round(test_percent, 1),
            "test_attempts": (t or {}).get("attempts_count", 0),
            "homework_percent": round(hw_percent, 1),
            "homework_graded": (h or {}).get("graded_count", 0),
            "homework_avg_score": (h or {}).get("avg_score"),
            "total_score": round(total, 1),
        })

    # Saralash: umumiy ball -> vazifa soni -> test soni
    result.sort(key=lambda r: (-r["total_score"], -r["homework_graded"], -r["test_attempts"]))
    for idx, r in enumerate(result):
        r["rank"] = idx + 1
    return result[:limit]


def get_my_combined_monthly_rank(telegram_id: int, year: int, month: int):
    board = get_combined_monthly_leaderboard(year, month, limit=100000)
    for row in board:
        if row["telegram_id"] == telegram_id:
            row = dict(row)
            row["total_participants"] = len(board)
            return row
    return None


# ---------- HAFTALIK 50/50 REYTING (shaxsiy xabar uchun) ----------
#
# Yuqoridagi get_control_test_monthly_leaderboard / get_homework_monthly_scores /
# get_combined_monthly_leaderboard bilan AYNAN bir xil mantiq — farqi faqat
# "shu oy" o'rniga ISTALGAN SANA ORALIG'I (masalan bitta hafta) bo'yicha
# filtrlanishi. Har haftalik shaxsiy xabar (bot.py -> send_weekly_rank_loop)
# shu funksiyalardan foydalanadi.

def get_control_test_range_leaderboard(start_date: str, end_date: str, limit: int = 100000):
    """get_control_test_monthly_leaderboard bilan bir xil, lekin oy o'rniga
    [start_date, end_date] (YYYY-MM-DD, ikkalasi ham qamrab olinadi)
    oralig'i bo'yicha."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            WITH first_attempts AS (
                SELECT a.*,
                       ROW_NUMBER() OVER (
                           PARTITION BY a.telegram_id, a.test_id
                           ORDER BY a.started_at ASC, a.id ASC
                       ) as rn
                FROM test_attempts a
                JOIN tests t ON t.id = a.test_id
                WHERE t.is_control_test = 1 AND a.finished_at IS NOT NULL
            )
            SELECT u.telegram_id as telegram_id, u.first_name as first_name,
                   AVG(CAST(fa.score AS FLOAT) / NULLIF(fa.total_questions, 0)) * 100 as avg_percent,
                   AVG((julianday(fa.finished_at) - julianday(fa.started_at)) * 86400) as avg_seconds,
                   COUNT(fa.id) as attempts_count
            FROM first_attempts fa
            JOIN users u ON u.telegram_id = fa.telegram_id
            WHERE fa.rn = 1
              AND date(fa.finished_at) BETWEEN ? AND ?
            GROUP BY u.telegram_id
            ORDER BY avg_percent DESC, avg_seconds ASC
            LIMIT ?
        """, (start_date, end_date, limit))
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            r["avg_percent"] = round(r["avg_percent"] or 0, 1)
            r["avg_seconds"] = round(r["avg_seconds"] or 0)
        return rows


def get_homework_range_scores(start_date: str, end_date: str):
    """get_homework_monthly_scores bilan bir xil, lekin sana oralig'i bo'yicha."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT s.telegram_id,
                   AVG(s.teacher_score) AS avg_score,
                   COUNT(*) AS graded_count
            FROM homework_submissions s
            WHERE s.status = 'graded'
              AND s.teacher_score IS NOT NULL
              AND date(COALESCE(s.submitted_at, s.graded_at)) BETWEEN ? AND ?
            GROUP BY s.telegram_id
        """, (start_date, end_date))
        rows = [dict(r) for r in cur.fetchall()]
    return {
        r["telegram_id"]: {
            "homework_percent": round((r["avg_score"] / HOMEWORK_MAX_SCORE) * 100, 1),
            "graded_count": r["graded_count"],
            "avg_score": round(r["avg_score"], 2),
        }
        for r in rows
    }


def get_combined_range_leaderboard(start_date: str, end_date: str, limit: int = 100000):
    """get_combined_monthly_leaderboard bilan AYNAN bir xil mantiq
    (50/50 nazorat testi + vazifa), faqat oy o'rniga sana oralig'i bo'yicha."""
    test_rows = get_control_test_range_leaderboard(start_date, end_date, limit=100000)
    test_by_id = {r["telegram_id"]: r for r in test_rows}
    hw_by_id = get_homework_range_scores(start_date, end_date)

    all_ids = set(test_by_id) | set(hw_by_id)

    users_by_id = {}
    if all_ids:
        with get_connection() as conn:
            cur = conn.cursor()
            placeholders = ",".join("?" for _ in all_ids)
            cur.execute(f"SELECT telegram_id, first_name, username FROM users WHERE telegram_id IN ({placeholders})",
                        list(all_ids))
            users_by_id = {r["telegram_id"]: dict(r) for r in cur.fetchall()}

    result = []
    for tid in all_ids:
        t = test_by_id.get(tid)
        h = hw_by_id.get(tid)
        test_percent = t["avg_percent"] if t else 0.0
        hw_percent = h["homework_percent"] if h else 0.0
        total = (test_percent * RANKING_TEST_WEIGHT + hw_percent * RANKING_HOMEWORK_WEIGHT) / 100.0

        user = users_by_id.get(tid, {})
        result.append({
            "telegram_id": tid,
            "first_name": (t or {}).get("first_name") or user.get("first_name") or "Foydalanuvchi",
            "username": user.get("username"),
            "test_percent": round(test_percent, 1),
            "test_attempts": (t or {}).get("attempts_count", 0),
            "homework_percent": round(hw_percent, 1),
            "homework_graded": (h or {}).get("graded_count", 0),
            "homework_avg_score": (h or {}).get("avg_score"),
            "total_score": round(total, 1),
        })

    result.sort(key=lambda r: (-r["total_score"], -r["homework_graded"], -r["test_attempts"]))
    for idx, r in enumerate(result):
        r["rank"] = idx + 1
    return result[:limit]


def get_users_needing_weekly_rank_notification(iso_year: int, iso_week: int, start_date: str, end_date: str):
    """Shu haftada kamida bitta faollik (nazorat testi yoki baholangan
    vazifa) ko'rsatgan, lekin shu hafta uchun hali xabar OLMAGAN
    foydalanuvchilar ro'yxati (telegram_id)."""
    board = get_combined_range_leaderboard(start_date, end_date, limit=100000)
    candidate_ids = {r["telegram_id"] for r in board}
    if not candidate_ids:
        return set()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT telegram_id FROM weekly_rank_notifications
            WHERE sent_year = ? AND sent_week = ?
        """, (iso_year, iso_week))
        already_sent = {r["telegram_id"] for r in cur.fetchall()}
    return candidate_ids - already_sent


def mark_weekly_rank_sent(telegram_id: int, iso_year: int, iso_week: int):
    with get_connection() as conn:
        conn.cursor().execute("""
            INSERT OR IGNORE INTO weekly_rank_notifications (telegram_id, sent_year, sent_week)
            VALUES (?, ?, ?)
        """, (telegram_id, iso_year, iso_week))
        conn.commit()


# ---------- PULLIK GURUH — KUNLIK (KECHAGI) NATIJA HISOBOTI ----------
#
# "Pullik guruh a'zosi" — istalgan FAOL kirish guruhiga (access_groups,
# Telegram yopiq kanal/guruh) a'zo bo'lgan foydalanuvchi deb olinadi,
# qaysi aniq kurs/fanga bog'liqligidan qat'i nazar — o'qituvchi bilan
# kelishilgan taxmin (kerak bo'lsa keyinroq kurs/fan darajasida
# toraytirish mumkin).

def get_paid_group_member_ids():
    """Hozir kamida bitta FAOL pullik guruhga a'zo (kesh bo'yicha) barcha
    foydalanuvchilar."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT c.telegram_id
            FROM group_membership_cache c
            JOIN access_groups g ON g.id = c.group_id
            WHERE c.is_member = 1 AND g.is_active = 1
        """)
        return [r["telegram_id"] for r in cur.fetchall()]


def get_users_due_for_paid_group_report(today_str: str):
    """Pullik guruh a'zolaridan, HECH QACHON xabar OLMAGAN yoki oxirgi
    xabardan beri 2 KUN YOKI KO'PROQ o'tganlar ro'yxati — "har 2 kunda bir
    marta" qoidasini ta'minlaydi."""
    member_ids = get_paid_group_member_ids()
    if not member_ids:
        return []
    with get_connection() as conn:
        cur = conn.cursor()
        placeholders = ",".join("?" for _ in member_ids)
        cur.execute(f"""
            SELECT telegram_id, last_sent_date FROM paid_group_daily_notifications
            WHERE telegram_id IN ({placeholders})
        """, member_ids)
        last_sent = {r["telegram_id"]: r["last_sent_date"] for r in cur.fetchall()}

    today = datetime.date.fromisoformat(today_str)
    due = []
    for tid in member_ids:
        last = last_sent.get(tid)
        if not last or (today - datetime.date.fromisoformat(last)).days >= 2:
            due.append(tid)
    return due


def get_yesterday_control_test_results_for(telegram_id: int, day_str: str):
    """Shu foydalanuvchi KECHA yakunlagan barcha nazorat testi urinishlari
    (mashq/qayta urinish ham — bu shaxsiy kunlik hisobot, reyting emas,
    shuning uchun hech narsa chetlab o'tilmaydi)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.title AS test_title, a.score AS score, a.total_questions AS total_questions
            FROM test_attempts a
            JOIN tests t ON t.id = a.test_id
            WHERE a.telegram_id = ? AND t.is_control_test = 1
              AND a.finished_at IS NOT NULL AND date(a.finished_at) = ?
            ORDER BY a.finished_at ASC
        """, (telegram_id, day_str))
        rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        r["percent"] = round((r["score"] / r["total_questions"]) * 100, 1) if r["total_questions"] else 0
    return rows


def get_yesterday_homework_submissions_for(telegram_id: int, day_str: str):
    """Shu foydalanuvchi KECHA topshirgan (submitted yoki graded) vazifalar."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT hs.title AS subject_title, s.paragraph_number AS paragraph_number,
                   s.status AS status, s.teacher_score AS teacher_score
            FROM homework_submissions s
            JOIN homework_subjects hs ON hs.id = s.subject_id
            WHERE s.telegram_id = ? AND s.status IN ('submitted', 'graded')
              AND date(s.submitted_at) = ?
            ORDER BY s.submitted_at ASC
        """, (telegram_id, day_str))
        return [dict(r) for r in cur.fetchall()]


def mark_paid_group_report_sent(telegram_id: int, today_str: str):
    with get_connection() as conn:
        conn.cursor().execute("""
            INSERT INTO paid_group_daily_notifications (telegram_id, last_sent_date, sent_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(telegram_id) DO UPDATE SET
                last_sent_date = excluded.last_sent_date, sent_at = CURRENT_TIMESTAMP
        """, (telegram_id, today_str))
        conn.commit()


def mark_homework_reminder_sent(telegram_id: int, subject_id: int, paragraph_number: int):
    """Ogohlantirish yuborilganini belgilaydi — bir xil eslatma
    qayta-qayta yuborilmasligi uchun."""
    if not subject_id or not paragraph_number:
        return {"ok": False}
    submission_id = _ensure_homework_submission(subject_id, telegram_id, paragraph_number)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE homework_submissions SET reminder_sent_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (submission_id,))
        conn.commit()
    return {"ok": True}


def get_homework_students_needing_reminder(min_hours_between: int = 48):
    """Avtomatik eslatma uchun: kechikkan VA oxirgi ogohlantirish
    yuborilganiga belgilangan soatdan ko'p vaqt o'tgan o'quvchilar."""
    now = datetime.datetime.utcnow()
    result = []
    for s in get_homework_late_students():
        sub = get_homework_submission(s["subject_id"], s["telegram_id"], s["waiting_paragraph"])
        last_sent = sub.get("reminder_sent_at") if sub else None
        if last_sent:
            try:
                sent_dt = datetime.datetime.fromisoformat(last_sent)
            except ValueError:
                sent_dt = now
            if (now - sent_dt).total_seconds() < min_hours_between * 3600:
                continue
        result.append(s)
    return result


def get_homework_storage_stats():
    """Vazifa rasmlari bo'yicha statistika — admin panelda ko'rsatiladi
    (qancha rasm Telegramda, qanchasi hali serverda)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN telegram_file_id IS NOT NULL THEN 1 ELSE 0 END) AS in_telegram,
                SUM(CASE WHEN telegram_file_id IS NULL THEN 1 ELSE 0 END) AS on_server
            FROM homework_photos
        """)
        row = dict(cur.fetchone())
        cur.execute("""
            SELECT COUNT(*) AS c FROM homework_photos p
            JOIN homework_submissions s ON s.id = p.submission_id
            WHERE s.status = 'graded' AND s.graded_at IS NOT NULL
        """)
        row["graded_photos"] = cur.fetchone()["c"] or 0
    return {
        "total": row["total"] or 0,
        "in_telegram": row["in_telegram"] or 0,
        "on_server": row["on_server"] or 0,
        "graded_photos": row["graded_photos"],
    }


# ==========================================================================
#  KIMYO O'YINI — moddalar bazasi, levellar va progress
# ==========================================================================
# Bu bo'lim "bitta baza, ko'p o'yin" g'oyasini amalga oshiradi:
# o'qituvchi faqat MODDA kiritadi, savollar chem_questions.py'da
# shu moddalardan avtomatik yasaladi.

# Bosqich (stage) raqamlari — kodning boshqa joylarida ham shu nomlar
# ishlatiladi, "sehrli raqam" yozmaslik uchun.
CHEM_STAGE_LEARN = 1     # O'rganish — kartochkalar
CHEM_STAGE_TEST = 2      # Test — variantli savollar
CHEM_STAGE_MATCH = 3     # Moslashtirish — formula <-> nom juftlash
CHEM_STAGE_WRITE = 4     # Yozish — formulani qo'lda kiritish
CHEM_STAGES = (CHEM_STAGE_LEARN, CHEM_STAGE_TEST, CHEM_STAGE_MATCH, CHEM_STAGE_WRITE)

CHEM_STAGE_TITLES = {
    CHEM_STAGE_LEARN: "O'rganish",
    CHEM_STAGE_TEST: "Test",
    CHEM_STAGE_MATCH: "Moslashtirish",
    CHEM_STAGE_WRITE: "Yozish",
}


def chem_stars_for_accuracy(correct: int, total: int) -> int:
    """Aniqlikka qarab yulduz beradi (0..3).

    Chegaralar ataylab "mehribon": 50% dan past bo'lsa yulduz yo'q, lekin
    bosqich baribir yakunlangan hisoblanadi — o'quvchi qulflanib qolmaydi,
    faqat yulduzini keyin qayta o'ynab ko'taradi. Bu Duolingo mantiqi:
    ilgarilash to'xtamasin, lekin mukammallik uchun sabab bo'lsin.
    """
    if total <= 0:
        return 0
    ratio = correct / total
    if ratio >= 0.9:
        return 3
    if ratio >= 0.7:
        return 2
    if ratio >= 0.5:
        return 1
    return 0


# ---------- Kategoriya ----------

def get_chem_categories(only_ready: bool = False):
    """Kategoriyalar ro'yxati. only_ready=True bo'lsa faqat tayyorlari."""
    with get_connection() as conn:
        cur = conn.cursor()
        sql = "SELECT * FROM chem_categories"
        if only_ready:
            sql += " WHERE is_ready = 1"
        sql += " ORDER BY sort_order, id"
        cur.execute(sql)
        return [dict(r) for r in cur.fetchall()]


def get_chem_category(category_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM chem_categories WHERE id = ?", (category_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_chem_category(key: str, title: str, subtitle: str = "",
                         icon: str = "🧪", is_ready: int = 0, sort_order: int = 0):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO chem_categories (key, title, subtitle, icon, is_ready, sort_order)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (key, title, subtitle, icon, safe_int(is_ready), safe_int(sort_order)))
        conn.commit()
        return cur.lastrowid


def update_chem_category(category_id: int, **fields):
    allowed = ("title", "subtitle", "icon", "is_ready", "sort_order")
    sets, vals = [], []
    for k in allowed:
        if k in fields:
            sets.append(f"{k} = ?")
            vals.append(safe_int(fields[k]) if k in ("is_ready", "sort_order") else fields[k])
    if not sets:
        return False
    vals.append(category_id)
    with get_connection() as conn:
        conn.cursor().execute(
            f"UPDATE chem_categories SET {', '.join(sets)} WHERE id = ?", vals)
        conn.commit()
    return True


def delete_chem_category(category_id: int):
    """Kategoriyani va uning ichidagi hamma narsani o'chiradi.
    SQLite'da ON DELETE CASCADE yoqilmagani uchun qo'lda tozalaymiz."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM chem_levels WHERE category_id = ?", (category_id,))
        level_ids = [r["id"] for r in cur.fetchall()]
        for lid in level_ids:
            cur.execute("DELETE FROM chem_substances WHERE level_id = ?", (lid,))
            cur.execute("DELETE FROM chem_stage_progress WHERE level_id = ?", (lid,))
        cur.execute("DELETE FROM chem_levels WHERE category_id = ?", (category_id,))
        cur.execute("DELETE FROM chem_categories WHERE id = ?", (category_id,))
        conn.commit()
    return True


# ---------- Level ----------

def get_chem_levels(category_id: int, only_active: bool = True):
    """Kategoriyaning levellari + har biridagi modda soni."""
    with get_connection() as conn:
        cur = conn.cursor()
        sql = """
            SELECT l.*, (SELECT COUNT(*) FROM chem_substances s
                         WHERE s.level_id = l.id) AS substance_count
            FROM chem_levels l
            WHERE l.category_id = ?
        """
        if only_active:
            sql += " AND l.is_active = 1"
        sql += " ORDER BY l.sort_order, l.id"
        cur.execute(sql, (category_id,))
        return [dict(r) for r in cur.fetchall()]


def get_chem_level(level_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT l.*, c.title AS category_title, c.key AS category_key, c.icon AS category_icon
            FROM chem_levels l
            JOIN chem_categories c ON c.id = l.category_id
            WHERE l.id = ?
        """, (level_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_chem_level(category_id: int, title: str, sort_order: int = 0):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO chem_levels (category_id, title, sort_order)
            VALUES (?, ?, ?)
        """, (category_id, title, safe_int(sort_order)))
        conn.commit()
        return cur.lastrowid


def update_chem_level(level_id: int, **fields):
    allowed = ("title", "sort_order", "is_active")
    sets, vals = [], []
    for k in allowed:
        if k in fields:
            sets.append(f"{k} = ?")
            vals.append(safe_int(fields[k]) if k in ("sort_order", "is_active") else fields[k])
    if not sets:
        return False
    vals.append(level_id)
    with get_connection() as conn:
        conn.cursor().execute(
            f"UPDATE chem_levels SET {', '.join(sets)} WHERE id = ?", vals)
        conn.commit()
    return True


def delete_chem_level(level_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM chem_substances WHERE level_id = ?", (level_id,))
        cur.execute("DELETE FROM chem_stage_progress WHERE level_id = ?", (level_id,))
        cur.execute("DELETE FROM chem_levels WHERE id = ?", (level_id,))
        conn.commit()
    return True


# ---------- Modda ----------

def get_chem_substances(level_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM chem_substances WHERE level_id = ?
            ORDER BY sort_order, id
        """, (level_id,))
        return [dict(r) for r in cur.fetchall()]


def get_chem_substances_by_category(category_id: int):
    """Kategoriyadagi BARCHA moddalar — battle savollarini generatsiya
    qilishda va chalg'ituvchi variantlarni tanlashda kerak bo'ladi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT s.* FROM chem_substances s
            JOIN chem_levels l ON l.id = s.level_id
            WHERE l.category_id = ? AND l.is_active = 1
            ORDER BY l.sort_order, s.sort_order, s.id
        """, (category_id,))
        return [dict(r) for r in cur.fetchall()]


def get_chem_substance(substance_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT s.*, l.title AS level_title, l.category_id
            FROM chem_substances s
            JOIN chem_levels l ON l.id = s.level_id
            WHERE s.id = ?
        """, (substance_id,))
        row = cur.fetchone()
        return dict(row) if row else None


_SUBSTANCE_FIELDS = ("formula", "name", "historic_name", "color_pure",
                     "color_solution", "color_precipitate", "reactions",
                     "usage_text", "sort_order")


def create_chem_substance(level_id: int, formula: str, name: str, **fields):
    vals = {k: fields.get(k) for k in _SUBSTANCE_FIELDS}
    vals["formula"] = formula
    vals["name"] = name
    vals["sort_order"] = safe_int(vals.get("sort_order"))
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            INSERT INTO chem_substances (level_id, {', '.join(_SUBSTANCE_FIELDS)})
            VALUES (?, {', '.join(['?'] * len(_SUBSTANCE_FIELDS))})
        """, (level_id, *[vals[k] for k in _SUBSTANCE_FIELDS]))
        conn.commit()
        return cur.lastrowid


def update_chem_substance(substance_id: int, **fields):
    sets, vals = [], []
    for k in _SUBSTANCE_FIELDS:
        if k in fields:
            sets.append(f"{k} = ?")
            vals.append(safe_int(fields[k]) if k == "sort_order" else fields[k])
    if not sets:
        return False
    vals.append(substance_id)
    with get_connection() as conn:
        conn.cursor().execute(
            f"UPDATE chem_substances SET {', '.join(sets)} WHERE id = ?", vals)
        conn.commit()
    return True


def delete_chem_substance(substance_id: int):
    with get_connection() as conn:
        conn.cursor().execute("DELETE FROM chem_substances WHERE id = ?", (substance_id,))
        conn.commit()
    return True


def search_chem_substances(query: str = "", limit: int = 60, offset: int = 0):
    """Moddalar lug'ati uchun qidiruv — formula yoki nom bo'yicha.
    Bo'sh so'rovda eng oxirgi qo'shilganlar qaytadi."""
    q = (query or "").strip()
    with get_connection() as conn:
        cur = conn.cursor()
        if q:
            like = f"%{q}%"
            cur.execute("""
                SELECT s.*, l.title AS level_title FROM chem_substances s
                JOIN chem_levels l ON l.id = s.level_id
                WHERE s.formula LIKE ? OR s.name LIKE ? OR s.historic_name LIKE ?
                ORDER BY
                    CASE WHEN s.formula = ? THEN 0
                         WHEN s.formula LIKE ? THEN 1
                         ELSE 2 END,
                    s.formula
                LIMIT ? OFFSET ?
            """, (like, like, like, q, f"{q}%", limit, offset))
        else:
            cur.execute("""
                SELECT s.*, l.title AS level_title FROM chem_substances s
                JOIN chem_levels l ON l.id = s.level_id
                ORDER BY s.id DESC LIMIT ? OFFSET ?
            """, (limit, offset))
        return [dict(r) for r in cur.fetchall()]


# ---------- Progress (yulduzlar va ketma-ket ochilish) ----------

def get_chem_progress_map(telegram_id: int, category_id: int):
    """{level_id: {stage: {stars, best_correct, total_questions}}} ko'rinishida
    bitta so'rov bilan butun kategoriya progressini qaytaradi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.* FROM chem_stage_progress p
            JOIN chem_levels l ON l.id = p.level_id
            WHERE p.telegram_id = ? AND l.category_id = ?
        """, (telegram_id, category_id))
        out = {}
        for r in cur.fetchall():
            out.setdefault(r["level_id"], {})[r["stage"]] = {
                "stars": r["stars"],
                "best_correct": r["best_correct"],
                "total_questions": r["total_questions"],
                "attempts": r["attempts"],
            }
        return out


def save_chem_stage_result(telegram_id: int, level_id: int, stage: int,
                           correct: int, total: int):
    """Bosqich natijasini saqlaydi — FAQAT YAXSHILANSA yangilanadi.

    Qaytaradi: {"stars": .., "best_stars": .., "improved": bool, "attempts": ..}
    """
    stage = safe_int(stage)
    correct = safe_int(correct)
    total = safe_int(total)
    # O'rganish bosqichi sinov emas — ko'rib chiqilsa to'liq hisoblanadi.
    stars = 3 if stage == CHEM_STAGE_LEARN else chem_stars_for_accuracy(correct, total)

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM chem_stage_progress
            WHERE telegram_id = ? AND level_id = ? AND stage = ?
        """, (telegram_id, level_id, stage))
        row = cur.fetchone()

        if row is None:
            cur.execute("""
                INSERT INTO chem_stage_progress
                    (telegram_id, level_id, stage, stars, best_correct,
                     total_questions, attempts)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (telegram_id, level_id, stage, stars, correct, total))
            conn.commit()
            return {"stars": stars, "best_stars": stars, "improved": True, "attempts": 1}

        best_stars = max(row["stars"], stars)
        best_correct = max(row["best_correct"], correct)
        attempts = (row["attempts"] or 0) + 1
        cur.execute("""
            UPDATE chem_stage_progress
            SET stars = ?, best_correct = ?, total_questions = ?, attempts = ?,
                completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (best_stars, best_correct, total, attempts, row["id"]))
        conn.commit()
        return {
            "stars": stars,
            "best_stars": best_stars,
            "improved": stars > row["stars"],
            "attempts": attempts,
        }


def build_chem_level_path(telegram_id: int, category_id: int):
    """Talabaga ko'rsatiladigan level yo'lagi.

    Qulf qoidasi: birinchi level doim ochiq; keyingisi oldingi levelning
    BARCHA 4 bosqichi yakunlanganda ochiladi. Bu Duolingo mantiqi —
    o'quvchi tartib bilan yuradi, lekin orqaga qaytib yulduz yig'a oladi.
    """
    levels = get_chem_levels(category_id)
    progress = get_chem_progress_map(telegram_id, category_id)

    path, unlocked = [], True
    total_stars = earned_stars = 0
    for lvl in levels:
        stages = progress.get(lvl["id"], {})
        done_stages = sum(1 for s in CHEM_STAGES if s in stages)

        # Levelning yulduzi — UCHTA SINOV bosqichining (Test, Moslashtirish,
        # Yozish) o'rtachasi. O'rganish bosqichi hisobga olinmaydi, chunki u
        # sinov emas va har doim 3 yulduz beradi — aks holda u o'rtachani
        # sun'iy ko'tarib, yulduz haqiqiy bilimni ko'rsatmay qolardi.
        # Yarmi (masalan 2.5) YUQORIGA yaxlitlanadi — o'quvchi foydasiga.
        assessed = [stages[s]["stars"] for s in
                    (CHEM_STAGE_TEST, CHEM_STAGE_MATCH, CHEM_STAGE_WRITE) if s in stages]
        level_max_stars = 3
        level_stars = int(sum(assessed) / len(assessed) + 0.5) if assessed else 0
        level_stars = min(3, level_stars)

        total_stars += level_max_stars
        earned_stars += level_stars

        path.append({
            "id": lvl["id"],
            "title": lvl["title"],
            "substance_count": lvl["substance_count"],
            "unlocked": unlocked,
            "completed": done_stages == len(CHEM_STAGES),
            "stages_done": done_stages,
            "stars": level_stars,
        })
        # Keyingi levelning holati SHU levelning yakunlanishiga bog'liq.
        unlocked = done_stages == len(CHEM_STAGES)

    return {
        "levels": path,
        "total_stars": total_stars,
        "earned_stars": earned_stars,
        "level_count": len(path),
        "substance_count": sum(l["substance_count"] for l in path),
    }


def get_chem_level_detail(telegram_id: int, level_id: int):
    """Level ichidagi 4 bosqich holati (BAJARILDI / HOZIR / qulf)."""
    level = get_chem_level(level_id)
    if not level:
        return None
    substances = get_chem_substances(level_id)

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM chem_stage_progress
            WHERE telegram_id = ? AND level_id = ?
        """, (telegram_id, level_id))
        done = {r["stage"]: dict(r) for r in cur.fetchall()}

    stages, next_stage = [], None
    for s in CHEM_STAGES:
        is_done = s in done
        # Bosqich ochiq bo'ladi, agar u birinchi bo'lsa yoki oldingisi bajarilgan bo'lsa.
        prev_done = (s == CHEM_STAGE_LEARN) or ((s - 1) in done)
        if not is_done and prev_done and next_stage is None:
            next_stage = s
        stages.append({
            "stage": s,
            "title": CHEM_STAGE_TITLES[s],
            "done": is_done,
            "unlocked": prev_done,
            "stars": done.get(s, {}).get("stars", 0),
        })

    return {
        "level": level,
        "substances": substances,
        "stages": stages,
        "next_stage": next_stage,
        "all_done": next_stage is None,
    }


# ==========================================================================
#  KIMYO O'YINI — BATTLE va ELO
# ==========================================================================

BATTLE_QUESTION_COUNT = 10      # bitta jangdagi savollar soni
BATTLE_STALE_MINUTES = 10       # shundan keyin raqib kutilmaydi, bot qo'shiladi
ELO_K = 32                      # standart shaxmat koeffitsienti

# Darajalar. Chegaralar ataylab "keng": o'quvchi bir necha g'alaba bilan
# keyingi darajaga o'tsin, lekin bitta mag'lubiyatdan tushib ketmasin.
CHEM_TIERS = (
    (1700, "Olmos",   "💎"),
    (1500, "Platina", "🔷"),
    (1300, "Oltin",   "🥇"),
    (1100, "Kumush",  "🥈"),
    (0,    "Bronza",  "🥉"),
)


def chem_tier(elo: int):
    """ELO ballidan daraja nomini aniqlaydi."""
    for threshold, name, icon in CHEM_TIERS:
        if elo >= threshold:
            return {"name": name, "icon": icon, "min_elo": threshold}
    return {"name": "Bronza", "icon": "🥉", "min_elo": 0}


def get_chem_rating(telegram_id: int):
    """Reyting yozuvi — bo'lmasa 1000 ball bilan yaratiladi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM chem_ratings WHERE telegram_id = ?", (telegram_id,))
        row = cur.fetchone()
        if row is None:
            cur.execute("INSERT INTO chem_ratings (telegram_id) VALUES (?)", (telegram_id,))
            conn.commit()
            cur.execute("SELECT * FROM chem_ratings WHERE telegram_id = ?", (telegram_id,))
            row = cur.fetchone()
        data = dict(row)

        # Global o'rin — reytingda nechanchi ekani.
        cur.execute("SELECT COUNT(*) AS c FROM chem_ratings WHERE elo > ?", (data["elo"],))
        data["rank"] = (cur.fetchone()["c"] or 0) + 1
        cur.execute("SELECT COUNT(*) AS c FROM chem_ratings")
        data["total_players"] = cur.fetchone()["c"] or 0

    total = data["wins"] + data["losses"] + data["draws"]
    data["games"] = total
    data["win_rate"] = round(data["wins"] / total * 100) if total else 0
    data["tier"] = chem_tier(data["elo"])
    return data


def _elo_delta(my_elo: int, opp_elo: int, score: float) -> int:
    """Standart ELO formulasi. score: 1=g'alaba, 0.5=durang, 0=mag'lubiyat.

    Kuchliroq raqibni yenggan ko'proq ball oladi; kuchsizga yutqazgan
    ko'proq yo'qotadi — shu sababli reyting adolatli bo'ladi.
    """
    expected = 1 / (1 + 10 ** ((opp_elo - my_elo) / 400))
    return round(ELO_K * (score - expected))


def _apply_rating(telegram_id: int, delta: int, result: str):
    """Reytingni yangilaydi. result: 'win' | 'lose' | 'draw'."""
    r = get_chem_rating(telegram_id)
    new_elo = max(100, r["elo"] + delta)   # 100 dan pastga tushmaydi
    wins = r["wins"] + (1 if result == "win" else 0)
    losses = r["losses"] + (1 if result == "lose" else 0)
    draws = r["draws"] + (1 if result == "draw" else 0)
    streak = (r["current_streak"] + 1) if result == "win" else 0
    best = max(r["best_streak"], streak)

    with get_connection() as conn:
        conn.cursor().execute("""
            UPDATE chem_ratings
            SET elo = ?, wins = ?, losses = ?, draws = ?,
                current_streak = ?, best_streak = ?, updated_at = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
        """, (new_elo, wins, losses, draws, streak, best, telegram_id))
        conn.commit()
    return new_elo


# ---------- Jang yaratish va qo'shilish ----------

def find_waiting_chem_battle(category_id: int, exclude_telegram_id: int):
    """Shu kategoriyada raqib kutayotgan jangni topadi (o'zimniki bo'lmagan)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM chem_battles
            WHERE category_id = ? AND status = 'waiting'
              AND p1_telegram_id != ? AND p2_telegram_id IS NULL
              AND mode = 'ranked'
            ORDER BY created_at ASC LIMIT 1
        """, (category_id, exclude_telegram_id))
        row = cur.fetchone()
        return dict(row) if row else None


def create_chem_battle(category_id: int, telegram_id: int, questions: list,
                       mode: str = "ranked", invite_code: str = None,
                       is_bot: int = 0, bot_name: str = None, bot_elo: int = None):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO chem_battles
                (category_id, mode, invite_code, questions, p1_telegram_id,
                 is_bot, bot_name, bot_elo, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'waiting')
        """, (category_id, mode, invite_code, json.dumps(questions, ensure_ascii=False),
              telegram_id, is_bot, bot_name, bot_elo))
        conn.commit()
        return cur.lastrowid


def join_chem_battle(battle_id: int, telegram_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE chem_battles SET p2_telegram_id = ?, status = 'playing'
            WHERE id = ? AND p2_telegram_id IS NULL
        """, (telegram_id, battle_id))
        conn.commit()
        return cur.rowcount > 0


def get_chem_battle(battle_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM chem_battles WHERE id = ?", (battle_id,))
        row = cur.fetchone()
        if not row:
            return None
        b = dict(row)
        b["questions"] = json.loads(b["questions"])
        return b


def find_chem_battle_by_code(code: str):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM chem_battles
            WHERE invite_code = ? AND status = 'waiting' AND p2_telegram_id IS NULL
            ORDER BY id DESC LIMIT 1
        """, (code,))
        row = cur.fetchone()
        if not row:
            return None
        b = dict(row)
        b["questions"] = json.loads(b["questions"])
        return b


def save_chem_battle_run(battle_id: int, telegram_id: int, score: int, time_ms: int):
    """O'yinchining natijasini saqlaydi va ikkalasi tugagan bo'lsa yakunlaydi."""
    b = get_chem_battle(battle_id)
    if not b:
        return None
    is_p1 = b["p1_telegram_id"] == telegram_id
    col = "p1" if is_p1 else "p2"

    with get_connection() as conn:
        conn.cursor().execute(f"""
            UPDATE chem_battles
            SET {col}_score = ?, {col}_time_ms = ?, {col}_finished_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (score, time_ms, battle_id))
        conn.commit()

    b = get_chem_battle(battle_id)
    both_done = b["p1_score"] is not None and b["p2_score"] is not None
    if both_done and b["status"] != "finished":
        return finish_chem_battle(battle_id)
    return b


def finish_chem_battle(battle_id: int):
    """G'olibni aniqlaydi va ELO'ni ikkala tomon uchun yangilaydi.

    Tenglik holatida TEZROQ javob bergan yutadi — shu sababli o'quvchi
    faqat to'g'ri emas, tez ham javob berishga harakat qiladi.
    """
    b = get_chem_battle(battle_id)
    if not b or b["status"] == "finished":
        return b

    p1_id, p2_id = b["p1_telegram_id"], b["p2_telegram_id"]
    p1_score = b["p1_score"] or 0
    p2_score = b["p2_score"] or 0
    p1_time = b["p1_time_ms"] or 10 ** 9
    p2_time = b["p2_time_ms"] or 10 ** 9

    if p1_score != p2_score:
        winner_is_p1 = p1_score > p2_score
    elif p1_time != p2_time:
        winner_is_p1 = p1_time < p2_time
    else:
        winner_is_p1 = None   # to'liq durang

    p1_elo = get_chem_rating(p1_id)["elo"]
    p2_elo = get_chem_rating(p2_id)["elo"] if p2_id else (b["bot_elo"] or 1000)

    if winner_is_p1 is None:
        p1_res, p2_res, p1_s, p2_s = "draw", "draw", 0.5, 0.5
        winner_id = None
    elif winner_is_p1:
        p1_res, p2_res, p1_s, p2_s = "win", "lose", 1.0, 0.0
        winner_id = p1_id
    else:
        p1_res, p2_res, p1_s, p2_s = "lose", "win", 0.0, 1.0
        winner_id = p2_id

    # Mashq rejimida (bot bilan) ELO o'zgarmaydi — aks holda o'quvchi
    # botni yengib reytingni sun'iy ko'tarib olardi.
    ranked = b["mode"] in ("ranked", "friend")
    p1_delta = _elo_delta(p1_elo, p2_elo, p1_s) if ranked else 0
    p1_after = _apply_rating(p1_id, p1_delta, p1_res) if ranked else p1_elo

    p2_after = p2_elo
    if p2_id and ranked:
        p2_delta = _elo_delta(p2_elo, p1_elo, p2_s)
        p2_after = _apply_rating(p2_id, p2_delta, p2_res)

    with get_connection() as conn:
        conn.cursor().execute("""
            UPDATE chem_battles
            SET status = 'finished', winner_telegram_id = ?,
                p1_elo_before = ?, p1_elo_after = ?,
                p2_elo_before = ?, p2_elo_after = ?,
                finished_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (winner_id, p1_elo, p1_after, p2_elo, p2_after, battle_id))
        conn.commit()

    return get_chem_battle(battle_id)


def resolve_stale_chem_battles(minutes: int = BATTLE_STALE_MINUTES):
    """Uzoq kutgan janglarni "Kimyobot" bilan yakunlaydi.

    NEGA KERAK: kichik guruhda ayni damda boshqa o'ynayotgan odam
    bo'lmasligi mumkin. Natijasiz osilib qolgan jang o'quvchini
    ko'ngilsizlantiradi — shuning uchun bot raqib sifatida qo'shiladi.
    Bot bali o'quvchinikiga yaqin qilib tanlanadi, lekin tasodifiy —
    shunda natija oldindan ma'lum bo'lmaydi.
    """
    import random
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT id, p1_score, p1_telegram_id FROM chem_battles
            WHERE status = 'waiting' AND p2_telegram_id IS NULL
              AND p1_score IS NOT NULL
              AND created_at <= datetime('now', '-{int(minutes)} minutes')
        """)
        rows = [dict(r) for r in cur.fetchall()]

    resolved = []
    for r in rows:
        total = BATTLE_QUESTION_COUNT
        # Bot natijasi o'quvchinikiga yaqin: -2 dan +2 gacha, chegaralar ichida.
        bot_score = max(0, min(total, (r["p1_score"] or 0) + random.randint(-2, 2)))
        bot_time = random.randint(25000, 70000)
        elo = get_chem_rating(r["p1_telegram_id"])["elo"]
        with get_connection() as conn:
            conn.cursor().execute("""
                UPDATE chem_battles
                SET p2_score = ?, p2_time_ms = ?, p2_finished_at = CURRENT_TIMESTAMP,
                    is_bot = 1, bot_name = 'Kimyobot',
                    bot_elo = ?, status = 'playing'
                WHERE id = ?
            """, (bot_score, bot_time, max(600, elo + random.randint(-80, 80)), r["id"]))
            conn.commit()
        resolved.append(finish_chem_battle(r["id"]))
    return resolved


def get_my_chem_battles(telegram_id: int, limit: int = 20):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM chem_battles
            WHERE p1_telegram_id = ? OR p2_telegram_id = ?
            ORDER BY id DESC LIMIT ?
        """, (telegram_id, telegram_id, limit))
        out = []
        for r in cur.fetchall():
            b = dict(r)
            b.pop("questions", None)     # ro'yxatda savollar kerak emas
            out.append(b)
        return out


def get_unnotified_chem_battles():
    """Yakunlangan, lekin hali Telegram xabari yuborilmagan janglar."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, p1_telegram_id, p2_telegram_id, p1_score, p2_score,
                   winner_telegram_id, is_bot, bot_name,
                   p1_elo_before, p1_elo_after, p2_elo_before, p2_elo_after
            FROM chem_battles
            WHERE status = 'finished' AND notified = 0
        """)
        return [dict(r) for r in cur.fetchall()]


def mark_chem_battle_notified(battle_id: int):
    with get_connection() as conn:
        conn.cursor().execute(
            "UPDATE chem_battles SET notified = 1 WHERE id = ?", (battle_id,))
        conn.commit()


def get_chem_leaderboard(limit: int = 50):
    """ELO reytingi — ismlar bilan."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT r.telegram_id, r.elo, r.wins, r.losses, r.draws,
                   u.first_name, u.username
            FROM chem_ratings r
            LEFT JOIN users u ON u.telegram_id = r.telegram_id
            WHERE (r.wins + r.losses + r.draws) > 0
            ORDER BY r.elo DESC, r.wins DESC
            LIMIT ?
        """, (limit,))
        out = []
        for i, r in enumerate(cur.fetchall(), start=1):
            d = dict(r)
            d["rank"] = i
            d["tier"] = chem_tier(d["elo"])
            out.append(d)
        return out


def get_chem_daily_mission(telegram_id: int, target: int = 3):
    """Bugun nechta jang o'ynagani — kunlik missiya ko'rsatkichi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) AS c FROM chem_battles
            WHERE (p1_telegram_id = ? OR p2_telegram_id = ?)
              AND status = 'finished'
              AND DATE(finished_at) = DATE('now')
        """, (telegram_id, telegram_id))
        done = cur.fetchone()["c"] or 0
    return {"done": min(done, target), "target": target, "completed": done >= target}


# ==========================================================================
#  KIMYO O'YINI — CHEMPIONAT (saralash -> setka -> final)
# ==========================================================================

TOURNAMENT_MIN_PLAYERS = 4          # shundan kam bo'lsa setka yasab bo'lmaydi
TOURNAMENT_ELO_MIN_PLAYERS = 8      # ELO faqat shundan ko'p bo'lsa hisoblanadi
TOURNAMENT_QUESTION_COUNT = 10


def _pow2_floor(n: int) -> int:
    """n dan katta bo'lmagan eng katta 2 ning darajasi (4, 8, 16, ...)."""
    p = 1
    while p * 2 <= n:
        p *= 2
    return p


def create_chem_tournament(category_id: int, title: str, created_by: int,
                           start_mode: str = "count", start_count: int = 8,
                           start_at=None, is_official: int = 0, prize_text: str = None):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO chem_tournaments
                (category_id, title, created_by, is_official, prize_text,
                 start_mode, start_count, start_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (category_id, title, created_by, safe_int(is_official), prize_text,
              start_mode, max(TOURNAMENT_MIN_PLAYERS, safe_int(start_count, 8)), start_at))
        conn.commit()
        return cur.lastrowid


def get_chem_tournament(tournament_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM chem_tournaments WHERE id = ?", (tournament_id,))
        row = cur.fetchone()
        if not row:
            return None
        t = dict(row)
        cur.execute("""
            SELECT p.*, u.first_name FROM chem_tournament_players p
            LEFT JOIN users u ON u.telegram_id = p.telegram_id
            WHERE p.tournament_id = ?
            ORDER BY p.seed IS NULL, p.seed, p.qual_score DESC, p.qual_time_ms
        """, (tournament_id,))
        t["players"] = [dict(r) for r in cur.fetchall()]
        t["player_count"] = len(t["players"])
        return t


def list_chem_tournaments(limit: int = 30):
    """Ochiq va davom etayotgan chempionatlar — rasmiylari birinchi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.*, u.first_name AS creator_name,
                   (SELECT COUNT(*) FROM chem_tournament_players p
                    WHERE p.tournament_id = t.id) AS player_count
            FROM chem_tournaments t
            LEFT JOIN users u ON u.telegram_id = t.created_by
            WHERE t.status != 'finished'
            ORDER BY t.is_official DESC, t.created_at ASC
            LIMIT ?
        """, (limit,))
        return [dict(r) for r in cur.fetchall()]


def join_chem_tournament(tournament_id: int, telegram_id: int):
    t = get_chem_tournament(tournament_id)
    if not t:
        return {"ok": False, "error": "Chempionat topilmadi"}
    if t["status"] != "open":
        return {"ok": False, "error": "Ro'yxatga olish yopilgan — chempionat boshlanib bo'lgan"}
    if any(p["telegram_id"] == telegram_id for p in t["players"]):
        return {"ok": True, "already": True}

    with get_connection() as conn:
        conn.cursor().execute("""
            INSERT OR IGNORE INTO chem_tournament_players (tournament_id, telegram_id)
            VALUES (?, ?)
        """, (tournament_id, telegram_id))
        conn.commit()
    return {"ok": True, "already": False}


def start_chem_tournament(tournament_id: int, questions: list):
    """Saralash bosqichini boshlaydi — barchaga BIR XIL savollar beriladi."""
    t = get_chem_tournament(tournament_id)
    if not t or t["status"] != "open":
        return None
    if t["player_count"] < TOURNAMENT_MIN_PLAYERS:
        return None
    with get_connection() as conn:
        conn.cursor().execute("""
            UPDATE chem_tournaments
            SET status = 'qualifying', qual_questions = ?, round_no = 0,
                started_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (json.dumps(questions, ensure_ascii=False), tournament_id))
        conn.commit()
    return get_chem_tournament(tournament_id)


def save_chem_qual_result(tournament_id: int, telegram_id: int, score: int, time_ms: int):
    with get_connection() as conn:
        conn.cursor().execute("""
            UPDATE chem_tournament_players
            SET qual_score = ?, qual_time_ms = ?, qual_done = 1
            WHERE tournament_id = ? AND telegram_id = ?
        """, (score, time_ms, tournament_id, telegram_id))
        conn.commit()
    return maybe_advance_chem_tournament(tournament_id)


def maybe_advance_chem_tournament(tournament_id: int):
    """Bosqich tugagan bo'lsa keyingisini yasaydi.

    Bu funksiya har bir natija saqlangandan keyin chaqiriladi — shu sababli
    chempionat "o'z-o'zidan" oldinga siljiydi va hech kim qo'lda
    boshqarishi shart emas.
    """
    t = get_chem_tournament(tournament_id)
    if not t:
        return None

    if t["status"] == "qualifying":
        if not all(p["qual_done"] for p in t["players"]):
            return t
        return _build_bracket(tournament_id)

    if t["status"] == "bracket":
        matches = get_chem_tournament_matches(tournament_id, t["round_no"])
        if not matches or any(m["status"] != "finished" for m in matches):
            return t
        return _next_bracket_round(tournament_id)

    return t


def _build_bracket(tournament_id: int):
    """Saralashdan keyin setkani yasaydi: eng yaxshi 2^k o'yinchi o'tadi.

    Juftlash klassik: 1-o'rin oxirgi o'tgan bilan, 2-o'rin oxirgidan
    oldingisi bilan... Shunday qilib kuchli o'yinchilar finalgacha
    uchrashmaydi — musobaqa qiziqroq bo'ladi.
    """
    t = get_chem_tournament(tournament_id)
    ranked = sorted(
        [p for p in t["players"] if p["qual_done"]],
        key=lambda p: (-(p["qual_score"] or 0), p["qual_time_ms"] or 10 ** 9))

    size = _pow2_floor(len(ranked))
    if size < 2:
        with get_connection() as conn:
            conn.cursor().execute("""
                UPDATE chem_tournaments SET status = 'finished', finished_at = CURRENT_TIMESTAMP
                WHERE id = ?""", (tournament_id,))
            conn.commit()
        return get_chem_tournament(tournament_id)

    advancing = ranked[:size]
    eliminated = ranked[size:]

    with get_connection() as conn:
        cur = conn.cursor()
        for i, p in enumerate(advancing, start=1):
            cur.execute("UPDATE chem_tournament_players SET seed = ? WHERE id = ?", (i, p["id"]))
        for p in eliminated:
            cur.execute("""
                UPDATE chem_tournament_players SET eliminated_round = 0 WHERE id = ?
            """, (p["id"],))
        cur.execute("""
            UPDATE chem_tournaments SET status = 'bracket', round_no = 1 WHERE id = ?
        """, (tournament_id,))
        conn.commit()

    pairs = [(advancing[i], advancing[size - 1 - i]) for i in range(size // 2)]
    _create_matches(tournament_id, 1, pairs, t["category_id"])
    return get_chem_tournament(tournament_id)


def _create_matches(tournament_id: int, round_no: int, pairs, category_id: int,
                    kind: str = "bracket"):
    """Juftliklar uchun o'yin yozuvlarini yaratadi (savollar bilan)."""
    import chem_questions as cq
    pool = get_chem_substances_by_category(category_id)
    with get_connection() as conn:
        cur = conn.cursor()
        for slot, (a, b) in enumerate(pairs, start=1):
            qs = cq.build_battle_questions(pool, count=TOURNAMENT_QUESTION_COUNT)
            cur.execute("""
                INSERT INTO chem_tournament_matches
                    (tournament_id, round_no, slot, kind, questions,
                     p1_telegram_id, p2_telegram_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (tournament_id, round_no, slot, kind,
                  json.dumps(qs, ensure_ascii=False),
                  a["telegram_id"] if a else None,
                  b["telegram_id"] if b else None))
        conn.commit()


def get_chem_tournament_matches(tournament_id: int, round_no: int = None):
    with get_connection() as conn:
        cur = conn.cursor()
        if round_no is None:
            cur.execute("""
                SELECT * FROM chem_tournament_matches
                WHERE tournament_id = ? ORDER BY round_no, slot
            """, (tournament_id,))
        else:
            cur.execute("""
                SELECT * FROM chem_tournament_matches
                WHERE tournament_id = ? AND round_no = ? ORDER BY slot
            """, (tournament_id, round_no))
        out = []
        for r in cur.fetchall():
            m = dict(r)
            m["questions"] = json.loads(m["questions"])
            out.append(m)
        return out


def get_chem_match(match_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM chem_tournament_matches WHERE id = ?", (match_id,))
        row = cur.fetchone()
        if not row:
            return None
        m = dict(row)
        m["questions"] = json.loads(m["questions"])
        return m


def save_chem_match_result(match_id: int, telegram_id: int, score: int, time_ms: int):
    m = get_chem_match(match_id)
    if not m:
        return None
    col = "p1" if m["p1_telegram_id"] == telegram_id else "p2"
    with get_connection() as conn:
        conn.cursor().execute(f"""
            UPDATE chem_tournament_matches
            SET {col}_score = ?, {col}_time_ms = ?, {col}_done = 1
            WHERE id = ?
        """, (score, time_ms, match_id))
        conn.commit()

    m = get_chem_match(match_id)
    # Raqib bo'sh bo'lsa (toq son) — avtomatik o'tadi.
    both = (m["p1_done"] and m["p2_done"]) or \
           (m["p1_done"] and not m["p2_telegram_id"]) or \
           (m["p2_done"] and not m["p1_telegram_id"])
    if both and m["status"] != "finished":
        _finish_chem_match(match_id)
        maybe_advance_chem_tournament(m["tournament_id"])
    return get_chem_match(match_id)


def _finish_chem_match(match_id: int):
    m = get_chem_match(match_id)
    p1, p2 = m["p1_telegram_id"], m["p2_telegram_id"]
    if not p2:
        winner = p1
    elif not p1:
        winner = p2
    else:
        s1, s2 = m["p1_score"] or 0, m["p2_score"] or 0
        t1, t2 = m["p1_time_ms"] or 10 ** 9, m["p2_time_ms"] or 10 ** 9
        # Tenglikda TEZROQ javob bergan o'tadi — chempionatda durang bo'lmaydi.
        winner = p1 if (s1 > s2 or (s1 == s2 and t1 <= t2)) else p2

    with get_connection() as conn:
        conn.cursor().execute("""
            UPDATE chem_tournament_matches
            SET winner_telegram_id = ?, status = 'finished' WHERE id = ?
        """, (winner, match_id))
        conn.commit()

    loser = p2 if winner == p1 else p1
    if loser:
        with get_connection() as conn:
            conn.cursor().execute("""
                UPDATE chem_tournament_players SET eliminated_round = ?
                WHERE tournament_id = ? AND telegram_id = ?
            """, (m["round_no"], m["tournament_id"], loser))
            conn.commit()


def _next_bracket_round(tournament_id: int):
    """Joriy bosqich tugadi — keyingisini yasaydi yoki chempionatni yakunlaydi."""
    t = get_chem_tournament(tournament_id)
    matches = get_chem_tournament_matches(tournament_id, t["round_no"])

    # Final tugadi (bitta o'yin qolgan edi) -> chempion aniqlandi.
    bracket_matches = [m for m in matches if m["kind"] == "bracket"]
    if len(bracket_matches) == 1:
        final = bracket_matches[0]
        champ = final["winner_telegram_id"]
        runner = final["p2_telegram_id"] if champ == final["p1_telegram_id"] \
            else final["p1_telegram_id"]
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE chem_tournaments
                SET status = 'finished', winner_telegram_id = ?, finished_at = CURRENT_TIMESTAMP
                WHERE id = ?""", (champ, tournament_id))
            cur.execute("""UPDATE chem_tournament_players SET place = 1
                           WHERE tournament_id = ? AND telegram_id = ?""", (tournament_id, champ))
            if runner:
                cur.execute("""UPDATE chem_tournament_players SET place = 2
                               WHERE tournament_id = ? AND telegram_id = ?""", (tournament_id, runner))
            # 3-o'rin: shu bosqichda chiqib ketganlardan tezrog'i
            cur.execute("""
                SELECT telegram_id FROM chem_tournament_players
                WHERE tournament_id = ? AND eliminated_round = ?
                ORDER BY qual_score DESC, qual_time_ms LIMIT 1
            """, (tournament_id, t["round_no"] - 1))
            row = cur.fetchone()
            if row:
                cur.execute("""UPDATE chem_tournament_players SET place = 3
                               WHERE tournament_id = ? AND telegram_id = ?""",
                            (tournament_id, row["telegram_id"]))
            conn.commit()
        _award_tournament_elo(tournament_id)
        return get_chem_tournament(tournament_id)

    winners = [m["winner_telegram_id"] for m in bracket_matches if m["winner_telegram_id"]]
    if len(winners) < 2:
        with get_connection() as conn:
            conn.cursor().execute("""
                UPDATE chem_tournaments SET status = 'finished',
                       winner_telegram_id = ?, finished_at = CURRENT_TIMESTAMP
                WHERE id = ?""", (winners[0] if winners else None, tournament_id))
            conn.commit()
        return get_chem_tournament(tournament_id)

    next_round = t["round_no"] + 1
    pairs = [({"telegram_id": winners[i]}, {"telegram_id": winners[i + 1]})
             for i in range(0, len(winners) - 1, 2)]
    with get_connection() as conn:
        conn.cursor().execute("UPDATE chem_tournaments SET round_no = ? WHERE id = ?",
                              (next_round, tournament_id))
        conn.commit()
    _create_matches(tournament_id, next_round, pairs, t["category_id"])
    return get_chem_tournament(tournament_id)


def _award_tournament_elo(tournament_id: int):
    """Chempionat yakunida ELO beradi.

    QOIDA: qatnashchi TOURNAMENT_ELO_MIN_PLAYERS dan kam bo'lsa ELO
    o'zgarmaydi — aks holda 4 kishilik "uy chempionati" bilan reytingni
    sun'iy ko'tarib olish mumkin bo'lardi.
    """
    t = get_chem_tournament(tournament_id)
    if not t or t["player_count"] < TOURNAMENT_ELO_MIN_PLAYERS:
        return
    bonus = {1: 40, 2: 25, 3: 15}
    for p in t["players"]:
        delta = bonus.get(p["place"], 0)
        if not delta and p["eliminated_round"] is not None:
            delta = 5 if p["eliminated_round"] > 0 else 0   # setkaga chiqqanga kichik bonus
        if delta:
            _apply_rating(p["telegram_id"], delta, "win" if p["place"] == 1 else "draw")


def get_my_chem_match(tournament_id: int, telegram_id: int):
    """O'quvchining SHU BOSQICHDAGI o'yini (bo'lsa)."""
    t = get_chem_tournament(tournament_id)
    if not t or t["status"] != "bracket":
        return None
    for m in get_chem_tournament_matches(tournament_id, t["round_no"]):
        if telegram_id in (m["p1_telegram_id"], m["p2_telegram_id"]):
            return m
    return None


def get_startable_chem_tournaments():
    """Boshlanish sharti bajarilgan chempionatlar (fon vazifasi uchun)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.*, (SELECT COUNT(*) FROM chem_tournament_players p
                         WHERE p.tournament_id = t.id) AS player_count
            FROM chem_tournaments t
            WHERE t.status = 'open'
        """)
        rows = [dict(r) for r in cur.fetchall()]

    out = []
    for t in rows:
        if t["player_count"] < TOURNAMENT_MIN_PLAYERS:
            continue
        if t["start_mode"] == "count" and t["player_count"] >= t["start_count"]:
            out.append(t)
        elif t["start_mode"] == "time" and t["start_at"]:
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT datetime('now') <= ? AS future", (t["start_at"],))
                if not cur.fetchone()["future"]:
                    out.append(t)
    return out


def count_todays_tournaments_by(telegram_id: int) -> int:
    """Bugun shu o'quvchi nechta chempionat yaratgan (kuniga 1 ta chegara)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) AS c FROM chem_tournaments
            WHERE created_by = ? AND DATE(created_at) = DATE('now')
        """, (telegram_id,))
        return cur.fetchone()["c"] or 0


# ==========================================================================
#  BIOLOGIYA O'YINI
# ==========================================================================
# Kimyodan asosiy farq: BOSQICHLAR RO'YXATI QAT'IY EMAS.
# Har level o'zida qanday ma'lumot bo'lsa, shunga mos o'yinlarni beradi.
# Masalan levelda ketma-ketlik kiritilmagan bo'lsa — "Ketma-ketlik"
# bosqichi umuman ko'rinmaydi. Shu tufayli o'qituvchi bazani
# bosqichma-bosqich to'ldirsa ham, o'quvchi hech qachon bo'sh o'yinga
# tushib qolmaydi.

# Bosqich kalitlari va ular uchun kerakli ma'lumot.
BIO_STAGES = (
    ("learn",    "O'rganish",     "Kartochkalarni ko'rib yodlang"),
    ("test",     "Test",          "Variantlardan to'g'risini tanlang"),
    ("match",    "Juftlash",      "Termin va ta'rifni moslashtiring"),
    ("sequence", "Ketma-ketlik",  "Bosqichlarni to'g'ri tartibda joylang"),
    ("group",    "Guruhlash",     "Har elementni o'z guruhiga ajrating"),
    ("whoami",   "Kim men?",      "Ipuchalarga qarab toping"),
    ("image",    "Rasm bo'yicha", "Rasmdagi qismlarni belgilang"),
)
BIO_STAGE_TITLES = {k: t for k, t, _ in BIO_STAGES}
BIO_STAGE_SUBS = {k: s for k, _, s in BIO_STAGES}
BIO_STAGE_ORDER = [k for k, _, _ in BIO_STAGES]

# Baholanadigan bosqichlar (yulduz shulardan hisoblanadi).
# "learn" sinov emas — u har doim to'liq hisoblanadi.
BIO_ASSESSED_STAGES = ("test", "match", "sequence", "group", "whoami", "image")


def bio_stars_for_accuracy(correct: int, total: int) -> int:
    """Kimyodagi bilan bir xil qoida — o'quvchi ikki fanda bir xil
    mantiqni ko'radi, chalkashmaydi."""
    return chem_stars_for_accuracy(correct, total)


# ---------- Mavzular ----------

def get_bio_topics(only_ready: bool = False):
    with get_connection() as conn:
        cur = conn.cursor()
        sql = "SELECT * FROM bio_topics"
        if only_ready:
            sql += " WHERE is_ready = 1"
        sql += " ORDER BY sort_order, id"
        cur.execute(sql)
        return [dict(r) for r in cur.fetchall()]


def get_bio_topic(topic_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM bio_topics WHERE id = ?", (topic_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_bio_topic(key: str, title: str, subtitle: str = "", icon: str = "🧬",
                     is_ready: int = 0, sort_order: int = 0):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO bio_topics (key, title, subtitle, icon, is_ready, sort_order)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (key, title, subtitle, icon, safe_int(is_ready), safe_int(sort_order)))
        conn.commit()
        return cur.lastrowid


def update_bio_topic(topic_id: int, **fields):
    allowed = ("title", "subtitle", "icon", "is_ready", "sort_order")
    sets, vals = [], []
    for k in allowed:
        if k in fields:
            sets.append(f"{k} = ?")
            vals.append(safe_int(fields[k]) if k in ("is_ready", "sort_order") else fields[k])
    if not sets:
        return False
    vals.append(topic_id)
    with get_connection() as conn:
        conn.cursor().execute(f"UPDATE bio_topics SET {', '.join(sets)} WHERE id = ?", vals)
        conn.commit()
    return True


def delete_bio_topic(topic_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM bio_levels WHERE topic_id = ?", (topic_id,))
        for lid in [r["id"] for r in cur.fetchall()]:
            for t in ("bio_terms", "bio_sequences", "bio_image_tasks", "bio_stage_progress"):
                cur.execute(f"DELETE FROM {t} WHERE level_id = ?", (lid,))
        cur.execute("DELETE FROM bio_levels WHERE topic_id = ?", (topic_id,))
        cur.execute("DELETE FROM bio_topics WHERE id = ?", (topic_id,))
        conn.commit()
    return True


# ---------- Levellar ----------

def get_bio_levels(topic_id: int, only_active: bool = True):
    """Levellar + har birida QANDAY ma'lumot borligi (bosqichlarni
    aniqlash uchun bitta so'rovda sanab olamiz)."""
    with get_connection() as conn:
        cur = conn.cursor()
        sql = """
            SELECT l.*,
                (SELECT COUNT(*) FROM bio_terms t WHERE t.level_id = l.id) AS term_count,
                (SELECT COUNT(*) FROM bio_sequences s WHERE s.level_id = l.id) AS sequence_count,
                (SELECT COUNT(*) FROM bio_image_tasks i WHERE i.level_id = l.id) AS image_count,
                (SELECT COUNT(DISTINCT t.group_name) FROM bio_terms t
                 WHERE t.level_id = l.id AND t.group_name IS NOT NULL
                   AND TRIM(t.group_name) != '') AS group_count,
                (SELECT COUNT(*) FROM bio_terms t
                 WHERE t.level_id = l.id AND t.clues IS NOT NULL
                   AND TRIM(t.clues) NOT IN ('', '[]')) AS clue_count
            FROM bio_levels l
            WHERE l.topic_id = ?
        """
        if only_active:
            sql += " AND l.is_active = 1"
        sql += " ORDER BY l.sort_order, l.id"
        cur.execute(sql, (topic_id,))
        return [dict(r) for r in cur.fetchall()]


def get_bio_level(level_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT l.*, t.title AS topic_title, t.key AS topic_key, t.icon AS topic_icon
            FROM bio_levels l JOIN bio_topics t ON t.id = l.topic_id
            WHERE l.id = ?
        """, (level_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_bio_level(topic_id: int, title: str, sort_order: int = 0):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO bio_levels (topic_id, title, sort_order) VALUES (?, ?, ?)",
                    (topic_id, title, safe_int(sort_order)))
        conn.commit()
        return cur.lastrowid


def update_bio_level(level_id: int, **fields):
    allowed = ("title", "sort_order", "is_active")
    sets, vals = [], []
    for k in allowed:
        if k in fields:
            sets.append(f"{k} = ?")
            vals.append(safe_int(fields[k]) if k in ("sort_order", "is_active") else fields[k])
    if not sets:
        return False
    vals.append(level_id)
    with get_connection() as conn:
        conn.cursor().execute(f"UPDATE bio_levels SET {', '.join(sets)} WHERE id = ?", vals)
        conn.commit()
    return True


def delete_bio_level(level_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        for t in ("bio_terms", "bio_sequences", "bio_image_tasks", "bio_stage_progress"):
            cur.execute(f"DELETE FROM {t} WHERE level_id = ?", (level_id,))
        cur.execute("DELETE FROM bio_levels WHERE id = ?", (level_id,))
        conn.commit()
    return True


# ---------- Terminlar ----------

_BIO_TERM_FIELDS = ("term", "definition", "function_text", "group_name",
                    "clues", "extra_fact", "image_url", "sort_order")


def _decode_clues(row: dict):
    """clues JSON matnini ro'yxatga aylantiradi (buzuq bo'lsa bo'sh)."""
    raw = row.get("clues")
    if not raw:
        row["clues"] = []
        return row
    try:
        val = json.loads(raw)
        row["clues"] = val if isinstance(val, list) else []
    except (ValueError, TypeError):
        row["clues"] = []
    return row


def get_bio_terms(level_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM bio_terms WHERE level_id = ? ORDER BY sort_order, id",
                    (level_id,))
        return [_decode_clues(dict(r)) for r in cur.fetchall()]


def get_bio_terms_by_topic(topic_id: int):
    """Mavzudagi barcha terminlar — chalg'ituvchi variantlar uchun."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.* FROM bio_terms t
            JOIN bio_levels l ON l.id = t.level_id
            WHERE l.topic_id = ? AND l.is_active = 1
            ORDER BY l.sort_order, t.sort_order, t.id
        """, (topic_id,))
        return [_decode_clues(dict(r)) for r in cur.fetchall()]


def get_bio_term(term_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.*, l.title AS level_title, l.topic_id
            FROM bio_terms t JOIN bio_levels l ON l.id = t.level_id
            WHERE t.id = ?
        """, (term_id,))
        row = cur.fetchone()
        return _decode_clues(dict(row)) if row else None


def _encode_clues(value):
    """Ipuchalarni JSON matnga aylantiradi. Ro'yxat ham, qatorlarga
    bo'lingan matn ham qabul qilinadi — admin formasida yozish qulay."""
    if value is None or value == "":
        return None
    if isinstance(value, str):
        parts = [p.strip() for p in value.splitlines() if p.strip()]
        return json.dumps(parts, ensure_ascii=False) if parts else None
    if isinstance(value, (list, tuple)):
        parts = [str(p).strip() for p in value if str(p).strip()]
        return json.dumps(parts, ensure_ascii=False) if parts else None
    return None


def create_bio_term(level_id: int, term: str, **fields):
    vals = {k: fields.get(k) for k in _BIO_TERM_FIELDS}
    vals["term"] = term
    vals["clues"] = _encode_clues(fields.get("clues"))
    vals["sort_order"] = safe_int(vals.get("sort_order"))
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            INSERT INTO bio_terms (level_id, {', '.join(_BIO_TERM_FIELDS)})
            VALUES (?, {', '.join(['?'] * len(_BIO_TERM_FIELDS))})
        """, (level_id, *[vals[k] for k in _BIO_TERM_FIELDS]))
        conn.commit()
        return cur.lastrowid


def update_bio_term(term_id: int, **fields):
    sets, vals = [], []
    for k in _BIO_TERM_FIELDS:
        if k in fields:
            sets.append(f"{k} = ?")
            if k == "clues":
                vals.append(_encode_clues(fields[k]))
            elif k == "sort_order":
                vals.append(safe_int(fields[k]))
            else:
                vals.append(fields[k])
    if not sets:
        return False
    vals.append(term_id)
    with get_connection() as conn:
        conn.cursor().execute(f"UPDATE bio_terms SET {', '.join(sets)} WHERE id = ?", vals)
        conn.commit()
    return True


def delete_bio_term(term_id: int):
    with get_connection() as conn:
        conn.cursor().execute("DELETE FROM bio_terms WHERE id = ?", (term_id,))
        conn.commit()
    return True


def search_bio_terms(query: str = "", limit: int = 60, offset: int = 0):
    """Biologiya lug'ati — termin yoki ta'rif bo'yicha qidiruv."""
    q = (query or "").strip()
    with get_connection() as conn:
        cur = conn.cursor()
        if q:
            like = f"%{q}%"
            cur.execute("""
                SELECT t.*, l.title AS level_title FROM bio_terms t
                JOIN bio_levels l ON l.id = t.level_id
                WHERE t.term LIKE ? OR t.definition LIKE ? OR t.function_text LIKE ?
                ORDER BY CASE WHEN t.term = ? THEN 0
                              WHEN t.term LIKE ? THEN 1 ELSE 2 END, t.term
                LIMIT ? OFFSET ?
            """, (like, like, like, q, f"{q}%", limit, offset))
        else:
            cur.execute("""
                SELECT t.*, l.title AS level_title FROM bio_terms t
                JOIN bio_levels l ON l.id = t.level_id
                ORDER BY t.id DESC LIMIT ? OFFSET ?
            """, (limit, offset))
        return [_decode_clues(dict(r)) for r in cur.fetchall()]


# ---------- Ketma-ketliklar ----------

def get_bio_sequences(level_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM bio_sequences WHERE level_id = ? ORDER BY sort_order, id",
                    (level_id,))
        out = []
        for r in cur.fetchall():
            d = dict(r)
            try:
                d["steps"] = json.loads(d["steps"])
            except (ValueError, TypeError):
                d["steps"] = []
            out.append(d)
        return out


def create_bio_sequence(level_id: int, title: str, steps, description: str = None,
                        sort_order: int = 0):
    if isinstance(steps, str):
        steps = [s.strip() for s in steps.splitlines() if s.strip()]
    steps = [str(s).strip() for s in (steps or []) if str(s).strip()]
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO bio_sequences (level_id, title, description, steps, sort_order)
            VALUES (?, ?, ?, ?, ?)
        """, (level_id, title, description, json.dumps(steps, ensure_ascii=False),
              safe_int(sort_order)))
        conn.commit()
        return cur.lastrowid


def update_bio_sequence(sequence_id: int, **fields):
    sets, vals = [], []
    for k in ("title", "description", "sort_order"):
        if k in fields:
            sets.append(f"{k} = ?")
            vals.append(safe_int(fields[k]) if k == "sort_order" else fields[k])
    if "steps" in fields:
        steps = fields["steps"]
        if isinstance(steps, str):
            steps = [s.strip() for s in steps.splitlines() if s.strip()]
        steps = [str(s).strip() for s in (steps or []) if str(s).strip()]
        sets.append("steps = ?")
        vals.append(json.dumps(steps, ensure_ascii=False))
    if not sets:
        return False
    vals.append(sequence_id)
    with get_connection() as conn:
        conn.cursor().execute(f"UPDATE bio_sequences SET {', '.join(sets)} WHERE id = ?", vals)
        conn.commit()
    return True


def delete_bio_sequence(sequence_id: int):
    with get_connection() as conn:
        conn.cursor().execute("DELETE FROM bio_sequences WHERE id = ?", (sequence_id,))
        conn.commit()
    return True


# ---------- Rasm topshiriqlari ----------

def get_bio_image_tasks(level_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM bio_image_tasks WHERE level_id = ? ORDER BY sort_order, id",
                    (level_id,))
        out = []
        for r in cur.fetchall():
            d = dict(r)
            try:
                d["labels"] = json.loads(d["labels"])
            except (ValueError, TypeError):
                d["labels"] = []
            out.append(d)
        return out


def create_bio_image_task(level_id: int, title: str, image_url: str, labels,
                          sort_order: int = 0):
    labels = labels or []
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO bio_image_tasks (level_id, title, image_url, labels, sort_order)
            VALUES (?, ?, ?, ?, ?)
        """, (level_id, title, image_url, json.dumps(labels, ensure_ascii=False),
              safe_int(sort_order)))
        conn.commit()
        return cur.lastrowid


def update_bio_image_task(task_id: int, **fields):
    sets, vals = [], []
    for k in ("title", "image_url", "sort_order"):
        if k in fields:
            sets.append(f"{k} = ?")
            vals.append(safe_int(fields[k]) if k == "sort_order" else fields[k])
    if "labels" in fields:
        sets.append("labels = ?")
        vals.append(json.dumps(fields["labels"] or [], ensure_ascii=False))
    if not sets:
        return False
    vals.append(task_id)
    with get_connection() as conn:
        conn.cursor().execute(f"UPDATE bio_image_tasks SET {', '.join(sets)} WHERE id = ?", vals)
        conn.commit()
    return True


def delete_bio_image_task(task_id: int):
    with get_connection() as conn:
        conn.cursor().execute("DELETE FROM bio_image_tasks WHERE id = ?", (task_id,))
        conn.commit()
    return True


# ---------- Bosqichlarni ANIQLASH (biologiyaning o'ziga xosligi) ----------

def bio_available_stages(level_row: dict):
    """Level ichida QAYSI o'yinlar mumkinligini aniqlaydi.

    Har o'yin uchun minimal shart bor:
      learn/test/match — kamida 3 ta termin (aks holda variant yetmaydi)
      sequence         — kamida 1 ta ketma-ketlik
      group            — kamida 2 xil guruh
      whoami           — kamida 1 ta ipuchali termin
      image            — kamida 1 ta rasm topshirig'i

    Shart bajarilmasa, bosqich UMUMAN ko'rsatilmaydi — o'quvchi bo'sh
    o'yinga tushib qolmaydi.
    """
    terms = level_row.get("term_count", 0) or 0
    out = []
    if terms >= 3:
        out += ["learn", "test", "match"]
    elif terms >= 1:
        out += ["learn"]
    if (level_row.get("sequence_count") or 0) >= 1:
        out.append("sequence")
    if (level_row.get("group_count") or 0) >= 2:
        out.append("group")
    if (level_row.get("clue_count") or 0) >= 1:
        out.append("whoami")
    if (level_row.get("image_count") or 0) >= 1:
        out.append("image")
    # Doimiy tartibda qaytaramiz — o'quvchi har safar bir xil ketma-ketlik ko'radi.
    return [k for k in BIO_STAGE_ORDER if k in out]


def get_bio_level_stats(level_id: int):
    """Bitta level uchun sanoqlar (bosqichlarni aniqlash uchun)."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                (SELECT COUNT(*) FROM bio_terms WHERE level_id = ?) AS term_count,
                (SELECT COUNT(*) FROM bio_sequences WHERE level_id = ?) AS sequence_count,
                (SELECT COUNT(*) FROM bio_image_tasks WHERE level_id = ?) AS image_count,
                (SELECT COUNT(DISTINCT group_name) FROM bio_terms
                 WHERE level_id = ? AND group_name IS NOT NULL AND TRIM(group_name) != '') AS group_count,
                (SELECT COUNT(*) FROM bio_terms
                 WHERE level_id = ? AND clues IS NOT NULL AND TRIM(clues) NOT IN ('', '[]')) AS clue_count
        """, (level_id, level_id, level_id, level_id, level_id))
        return dict(cur.fetchone())


# ---------- Progress ----------

def get_bio_progress_map(telegram_id: int, topic_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.* FROM bio_stage_progress p
            JOIN bio_levels l ON l.id = p.level_id
            WHERE p.telegram_id = ? AND l.topic_id = ?
        """, (telegram_id, topic_id))
        out = {}
        for r in cur.fetchall():
            out.setdefault(r["level_id"], {})[r["stage_key"]] = {
                "stars": r["stars"], "best_correct": r["best_correct"],
                "total_questions": r["total_questions"], "attempts": r["attempts"],
            }
        return out


def save_bio_stage_result(telegram_id: int, level_id: int, stage_key: str,
                          correct: int, total: int):
    correct, total = safe_int(correct), safe_int(total)
    stars = 3 if stage_key == "learn" else bio_stars_for_accuracy(correct, total)

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM bio_stage_progress
            WHERE telegram_id = ? AND level_id = ? AND stage_key = ?
        """, (telegram_id, level_id, stage_key))
        row = cur.fetchone()

        if row is None:
            cur.execute("""
                INSERT INTO bio_stage_progress
                    (telegram_id, level_id, stage_key, stars, best_correct,
                     total_questions, attempts)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (telegram_id, level_id, stage_key, stars, correct, total))
            conn.commit()
            return {"stars": stars, "best_stars": stars, "improved": True, "attempts": 1}

        best_stars = max(row["stars"], stars)
        cur.execute("""
            UPDATE bio_stage_progress
            SET stars = ?, best_correct = ?, total_questions = ?, attempts = ?,
                completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (best_stars, max(row["best_correct"], correct), total,
              (row["attempts"] or 0) + 1, row["id"]))
        conn.commit()
        return {"stars": stars, "best_stars": best_stars,
                "improved": stars > row["stars"], "attempts": (row["attempts"] or 0) + 1}


def build_bio_level_path(telegram_id: int, topic_id: int):
    """Level yo'lagi. Qulf qoidasi kimyodagi bilan bir xil, LEKIN
    "yakunlangan" deganda shu levelda MAVJUD bosqichlar nazarda tutiladi."""
    levels = get_bio_levels(topic_id)
    progress = get_bio_progress_map(telegram_id, topic_id)

    path, unlocked = [], True
    total_stars = earned_stars = 0
    for lvl in levels:
        stages = bio_available_stages(lvl)
        done = progress.get(lvl["id"], {})
        done_count = sum(1 for s in stages if s in done)

        assessed = [done[s]["stars"] for s in stages
                    if s in done and s in BIO_ASSESSED_STAGES]
        level_stars = min(3, int(sum(assessed) / len(assessed) + 0.5)) if assessed else 0

        total_stars += 3
        earned_stars += level_stars

        path.append({
            "id": lvl["id"], "title": lvl["title"],
            "term_count": lvl["term_count"],
            "stage_count": len(stages),
            "stages_done": done_count,
            "unlocked": unlocked,
            "completed": bool(stages) and done_count == len(stages),
            "stars": level_stars,
            "has_sequence": (lvl["sequence_count"] or 0) > 0,
            "has_image": (lvl["image_count"] or 0) > 0,
        })
        unlocked = bool(stages) and done_count == len(stages)

    return {
        "levels": path,
        "total_stars": total_stars,
        "earned_stars": earned_stars,
        "level_count": len(path),
        "term_count": sum(l["term_count"] for l in path),
    }


def get_bio_level_detail(telegram_id: int, level_id: int):
    level = get_bio_level(level_id)
    if not level:
        return None
    stats = get_bio_level_stats(level_id)
    stage_keys = bio_available_stages(stats)

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM bio_stage_progress WHERE telegram_id = ? AND level_id = ?",
                    (telegram_id, level_id))
        done = {r["stage_key"]: dict(r) for r in cur.fetchall()}

    stages, next_stage = [], None
    for i, key in enumerate(stage_keys):
        is_done = key in done
        prev_done = (i == 0) or (stage_keys[i - 1] in done)
        if not is_done and prev_done and next_stage is None:
            next_stage = key
        stages.append({
            "key": key,
            "title": BIO_STAGE_TITLES[key],
            "subtitle": BIO_STAGE_SUBS[key],
            "done": is_done,
            "unlocked": prev_done,
            "stars": done.get(key, {}).get("stars", 0),
        })

    return {
        "level": level, "stats": stats, "stages": stages,
        "next_stage": next_stage,
        "all_done": bool(stage_keys) and next_stage is None,
    }


# ==========================================================================
#  PULLIK GURUH ORQALI AVTOMATIK KIRISH
# ==========================================================================

# A'zolik natijasi shuncha daqiqa "yangi" hisoblanadi. O'tgach qayta
# tekshiriladi — shu sababli guruhdan chiqqan o'quvchi taxminan shu
# vaqt ichida qulflanadi.
MEMBERSHIP_TTL_MINUTES = 10

# Telegram'da a'zo hisoblanadigan holatlar. 'restricted' ataylab
# kiritilgan: guruhda ovozi o'chirilgan bo'lsa ham u A'ZO — darsni
# ko'rish huquqi saqlanishi kerak.
TELEGRAM_MEMBER_STATUSES = ("creator", "administrator", "member", "restricted")


# ---------- Guruhlar ----------

def get_access_groups(only_active: bool = False):
    with get_connection() as conn:
        cur = conn.cursor()
        sql = "SELECT * FROM access_groups"
        if only_active:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY id"
        cur.execute(sql)
        return [dict(r) for r in cur.fetchall()]


def get_access_group(group_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM access_groups WHERE id = ?", (group_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_access_group(title: str, chat_id: str, invite_link: str = None):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO access_groups (title, chat_id, invite_link) VALUES (?, ?, ?)
        """, (title.strip(), str(chat_id).strip(), (invite_link or "").strip() or None))
        conn.commit()
        return cur.lastrowid


def update_access_group(group_id: int, **fields):
    allowed = ("title", "chat_id", "invite_link", "is_active", "last_error")
    sets, vals = [], []
    for k in allowed:
        if k in fields:
            sets.append(f"{k} = ?")
            vals.append(safe_int(fields[k]) if k == "is_active" else fields[k])
    if not sets:
        return False
    vals.append(group_id)
    with get_connection() as conn:
        conn.cursor().execute(f"UPDATE access_groups SET {', '.join(sets)} WHERE id = ?", vals)
        conn.commit()
    return True


def delete_access_group(group_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM content_access_links WHERE group_id = ?", (group_id,))
        cur.execute("DELETE FROM group_membership_cache WHERE group_id = ?", (group_id,))
        cur.execute("DELETE FROM access_groups WHERE id = ?", (group_id,))
        conn.commit()
    return True


# ---------- Kontentni guruhga bog'lash ----------

# Guruh sozlamasi BUZUQ ekanini bildiruvchi xato belgilari.
# Bunday guruh KIRISHNI CHEKLAMAYDI — pastdagi izohga qarang.
_BROKEN_SETUP_MARKERS = (
    "chat not found", "bot is not a member", "not enough rights",
    "chat_id is empty", "bot was kicked", "forbidden",
)


def is_group_setup_broken(group: dict) -> bool:
    low = (group.get("last_error") or "").lower()
    return any(m in low for m in _BROKEN_SETUP_MARKERS)


def get_content_groups(content_type: str, content_id: int, include_broken: bool = False):
    """Shu kontent qaysi guruhlarga bog'langan (faqat faollari).

    MUHIM QOIDA — BUZUQ SOZLAMA QULFLAMAYDI:
    Agar guruhning chat_id si noto'g'ri bo'lsa yoki bot guruhdan chiqarilgan
    bo'lsa, Telegram hech kimni "a'zo" deb ko'rsatolmaydi. Bunday holatda
    hamma o'quvchini qulflab qo'yish — o'qituvchining sozlash xatosi uchun
    o'quvchilarni jazolash bo'lardi.

    Shuning uchun BUZUQ guruh ro'yxatdan chiqarib tashlanadi: kontent
    qulflanmaydi va eski tartib (qo'lda biriktirish) ishlayveradi.
    Admin panelda esa katta qizil ogohlantirish chiqadi.

    `include_broken=True` — admin paneli uchun (u hammasini ko'rsatishi kerak).
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT g.* FROM content_access_links l
            JOIN access_groups g ON g.id = l.group_id
            WHERE l.content_type = ? AND l.content_id = ? AND g.is_active = 1
            ORDER BY g.id
        """, (content_type, content_id))
        groups = [dict(r) for r in cur.fetchall()]

    if include_broken:
        return groups
    return [g for g in groups if not is_group_setup_broken(g)]


def set_content_groups(content_type: str, content_id: int, group_ids):
    """Kontentning guruh bog'lanishlarini to'liq almashtiradi."""
    ids = [safe_int(g) for g in (group_ids or []) if safe_int(g)]
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM content_access_links WHERE content_type = ? AND content_id = ?",
                    (content_type, content_id))
        for gid in ids:
            cur.execute("""
                INSERT OR IGNORE INTO content_access_links (content_type, content_id, group_id)
                VALUES (?, ?, ?)
            """, (content_type, content_id, gid))
        conn.commit()
    return True


def get_all_content_links(content_type: str = None):
    """Admin paneli uchun — qaysi kontent qaysi guruhga bog'langan."""
    with get_connection() as conn:
        cur = conn.cursor()
        if content_type:
            cur.execute("""SELECT * FROM content_access_links WHERE content_type = ?""",
                        (content_type,))
        else:
            cur.execute("SELECT * FROM content_access_links")
        out = {}
        for r in cur.fetchall():
            out.setdefault((r["content_type"], r["content_id"]), []).append(r["group_id"])
        return out


# ---------- A'zolik keshi ----------

def save_membership(telegram_id: int, group_id: int, is_member: bool, status: str = None):
    with get_connection() as conn:
        conn.cursor().execute("""
            INSERT INTO group_membership_cache (telegram_id, group_id, is_member, status, checked_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(telegram_id, group_id) DO UPDATE SET
                is_member = excluded.is_member,
                status = excluded.status,
                checked_at = CURRENT_TIMESTAMP
        """, (telegram_id, group_id, 1 if is_member else 0, status))
        conn.commit()


def get_member_group_ids(telegram_id: int):
    """O'quvchi HOZIR a'zo bo'lgan guruhlar (keshi hali eskirmaganlari).

    Eskirgan yozuv HISOBGA OLINMAYDI — ya'ni tekshiruv o'tkazilmagan
    bo'lsa, kirish berilmaydi. Bu ataylab shunday: "ishonchsiz holatda
    yopiq" tamoyili, aks holda kesh eskirganda hamma narsa ochilib
    ketardi.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT c.group_id FROM group_membership_cache c
            JOIN access_groups g ON g.id = c.group_id
            WHERE c.telegram_id = ? AND c.is_member = 1 AND g.is_active = 1
              AND c.checked_at >= datetime('now', '-{int(MEMBERSHIP_TTL_MINUTES)} minutes')
        """, (telegram_id,))
        return {r["group_id"] for r in cur.fetchall()}


def get_stale_membership_groups(telegram_id: int):
    """Shu o'quvchi uchun QAYTA TEKSHIRISH kerak bo'lgan guruhlar.

    Yangi tekshirilgan (TTL ichidagi) guruhlar ro'yxatga kirmaydi —
    keraksiz Telegram so'rovlari yuborilmaydi.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT g.* FROM access_groups g
            WHERE g.is_active = 1 AND g.id NOT IN (
                SELECT c.group_id FROM group_membership_cache c
                WHERE c.telegram_id = ?
                  AND c.checked_at >= datetime('now', '-{int(MEMBERSHIP_TTL_MINUTES)} minutes')
            )
        """, (telegram_id,))
        return [dict(r) for r in cur.fetchall()]


def get_group_member_count(group_id: int):
    """Keshdagi a'zolar soni — admin panelida ko'rsatiladi."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) AS c FROM group_membership_cache
            WHERE group_id = ? AND is_member = 1
        """, (group_id,))
        return cur.fetchone()["c"] or 0


def get_users_needing_membership_refresh(limit: int = 200):
    """Fon vazifasi uchun: keshi eskirgan FAOL foydalanuvchilar.

    "Faol" — oxirgi 30 kunda ilovaga kirgan. Butun bazani tekshirish
    Telegram limitiga urib qo'yadi, shuning uchun faqat haqiqatan
    kerak bo'lganlar yangilanadi.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT DISTINCT u.telegram_id FROM users u
            WHERE EXISTS (SELECT 1 FROM access_groups g WHERE g.is_active = 1)
              AND (
                u.telegram_id IN (
                    SELECT telegram_id FROM group_membership_cache
                    WHERE checked_at < datetime('now', '-{int(MEMBERSHIP_TTL_MINUTES)} minutes')
                )
                OR u.telegram_id NOT IN (SELECT telegram_id FROM group_membership_cache)
              )
            ORDER BY u.id DESC LIMIT ?
        """, (limit,))
        return [r["telegram_id"] for r in cur.fetchall()]


# ---------- Kirish tekshiruvi ----------

def has_group_access(telegram_id: int, content_type: str, content_id: int,
                     member_group_ids=None):
    """Kontent guruh orqali ochilganmi?

    Qaytaradi: (ochiqmi, bog'langan_guruhlar)
      - Kontent hech qaysi guruhga bog'lanmagan bo'lsa -> (False, [])
        ya'ni bu tizim bu kontentga umuman ta'sir qilmaydi.
      - Bog'langan bo'lsa va o'quvchi shu guruhlardan BIRIDA bo'lsa -> (True, ...)
    """
    groups = get_content_groups(content_type, content_id)
    if not groups:
        return False, []
    if member_group_ids is None:
        member_group_ids = get_member_group_ids(telegram_id)
    ok = any(g["id"] in member_group_ids for g in groups)
    return ok, groups
