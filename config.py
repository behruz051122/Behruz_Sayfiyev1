# config.py
# MUHIM O'ZGARISH (Xavfsizlik yangilanishi):
# Endi maxfiy qiymatlar (token, parol hash, JWT kaliti) shu faylda EMAS,
# balki loyiha papkasidagi ".env" faylida saqlanadi. ".env" fayli hech qachon
# GitHub'ga yuklanmaydi (.gitignore ichida). Shu fayl faqat ularni o'qib oladi.
#
# Birinchi marta sozlash uchun ".env.example" faylini ".env" nomiga
# nusxalab, ichidagi qiymatlarni to'ldiring.

import os
import sys
from dotenv import load_dotenv

load_dotenv()  # loyiha papkasidagi .env faylini o'qiydi (agar mavjud bo'lsa)


def _require_env(key: str) -> str:
    """Majburiy muhit o'zgaruvchisini o'qiydi. Topilmasa — aniq xatolik bilan to'xtaydi
    (noto'g'ri/bo'sh sozlama bilan production'da ishga tushishning oldini oladi)."""
    value = os.environ.get(key)
    if not value:
        sys.exit(
            f"\n[XATOLIK] '{key}' muhit o'zgaruvchisi topilmadi.\n"
            f"Loyiha papkasida '.env' fayl borligini va unda {key}=... qatori "
            f"to'ldirilganini tekshiring. Namuna uchun '.env.example' fayliga qarang.\n"
        )
    return value


# ---------- MAJBURIY MAXFIY QIYMATLAR (.env ichida) ----------

BOT_TOKEN = _require_env("BOT_TOKEN")

# Parolning o'zi emas — bcrypt bilan xeshlangan varianti saqlanadi.
# Yangi parol hosil qilish uchun generate_password_hash.py skriptini ishlating.
ADMIN_PASSWORD_HASH = _require_env("ADMIN_PASSWORD_HASH")

# Admin sessiya tokenlarini (JWT) imzolash uchun tasodifiy maxfiy kalit.
JWT_SECRET_KEY = _require_env("JWT_SECRET_KEY")


# ---------- ODDIY (maxfiy bo'lmagan) SOZLAMALAR ----------

WEBAPP_URL = os.environ.get(
    "WEBAPP_URL",
    "https://behruzsayfiyev1-production-4a0a.up.railway.app"
)

BOT_USERNAME = os.environ.get("BOT_USERNAME", "Behruz_Sayfiyev1bot")

CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "@Behruz_Sayfiyev1")
CHANNEL_URL = os.environ.get("CHANNEL_URL", "https://t.me/Behruz_Sayfiyev1")

BRAND_NAME = os.environ.get("BRAND_NAME", "Behruz Sayfiyev")
BRAND_SUB = os.environ.get("BRAND_SUB", "ONLINE TA'LIM PLATFORMASI")

ADMIN_CONTACT_USERNAME = os.environ.get("ADMIN_CONTACT_USERNAME", "BehruzSayfiyev")

# Mini App ichida "Admin" bo'limini avtomatik ko'radigan (parolsiz) Telegram ID'lar.
# Bu ID'lar initData orqali KRIPTOGRAFIK TASDIQLANGANDAN keyingina ishonch bilan
# qabul qilinadi (auth.py -> get_verified_telegram_user). Shuning uchun bu yerda
# oddiy ro'yxat sifatida qolishi xavfsiz — headerdan o'g'irlab bo'lmaydi.
_admin_ids_raw = os.environ.get("ADMIN_TELEGRAM_IDS", "7558364715")
ADMIN_TELEGRAM_IDS = [int(x.strip()) for x in _admin_ids_raw.split(",") if x.strip()]

DB_PATH = os.environ.get("DB_PATH", "database.db")

# Admin panelda yuklangan rasmlar (savol grafigi/jadvali va h.k.) shu papkada
# saqlanadi. Standart holatda DB_PATH bilan BIR XIL papkada joylashadi —
# shunday qilib, agar DB_PATH allaqachon Railway Volume'ga (masalan
# /data/database.db) to'g'ri sozlangan bo'lsa, yuklangan rasmlar ham
# avtomatik o'sha doimiy xotirada saqlanadi va qayta deploy'da yo'qolmaydi.
# Alohida sozlash shart emas — lekin xohlasangiz UPLOADS_DIR orqali
# ustidan yozib qo'yish mumkin.
UPLOADS_DIR = os.environ.get("UPLOADS_DIR", os.path.join(os.path.dirname(DB_PATH) or ".", "uploads"))


# ---------- VAZIFA RASMLARINI TELEGRAMDA SAQLASH ----------
# MUAMMO: o'quvchilar yuboradigan uy vazifasi suratlari (har biri 2-4 MB)
# serverning doimiy xotirasini (Railway Volume) tez to'ldiradi va xarajatni
# oshiradi. Masalan 50 o'quvchi x 120 paragraf x 3 rasm = ~36 GB.
#
# YECHIM: rasm serverda SAQLANMAYDI. Bot uni siz ochgan YOPIQ KANALGA
# yuboradi, bazada esa faqat Telegram bergan qisqa "file_id" satri
# (~80 bayt) qoladi — ya'ni 2 MB o'rniga 80 bayt, 25 000 marta kam.
# Telegram bu fayllarni bepul va muddatsiz saqlaydi.
#
# SOZLASH (bir marta):
#   1) Telegramda YOPIQ kanal oching (masalan "Vazifalar arxivi")
#   2) Botingizni o'sha kanalga ADMIN qilib qo'shing
#   3) Kanal ID sini oling (odatda -100 bilan boshlanadi)
#   4) Railway -> Variables -> HOMEWORK_ARCHIVE_CHAT_ID = -100xxxxxxxxxx
#
# Agar sozlanmagan bo'lsa — tizim ishlashdan TO'XTAMAYDI, rasmlar
# avvalgidek diskka saqlanadi (faqat joy egallaydi).
HOMEWORK_ARCHIVE_CHAT_ID = os.environ.get("HOMEWORK_ARCHIVE_CHAT_ID", "").strip()

# Baholangan vazifa rasmlari necha kundan keyin o'chirilsin.
# Ball va o'qituvchi izohi HECH QACHON o'chirilmaydi — faqat rasm fayli.
HOMEWORK_PHOTO_RETENTION_DAYS = int(os.environ.get("HOMEWORK_PHOTO_RETENTION_DAYS", "90"))
