# server.py — ilova kirish nuqtasi (v4 — routerlarga bo'lingan arxitektura)
#
# ARXITEKTURA YANGILANISHI:
# Avval bu faylda 40+ endpoint bitta joyda, ~350 qatorda saqlanardi. Endi bu
# fayl faqat: (1) FastAPI ilovasini yaratadi, (2) middleware/rate-limit ulaydi,
# (3) har bir mavzu bo'yicha alohida "router" faylini ulaydi, (4) statik
# fayllarni (webapp/) ulaydi. Haqiqiy endpoint mantiqi routers/ papkasida.
#
# Bu nima beradi:
#   - Har bir fayl 300 qatordan oshmaydi, topish va tushunish osonlashadi
#   - Bir bo'lim ustida ishlaganda boshqasiga tegib ketish xavfi kamayadi
#   - Kelajakda yangi bo'lim (masalan "sertifikatlar") qo'shish — shunchaki
#     yangi routers/certificates.py yaratib, shu yerga bitta qator qo'shish

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import asyncio
import os

from rate_limit import limiter
import database as db
import bot as bot_module

from routers import (
    brand,
    user,
    courses,
    tests,
    simulators,
    control_tests,
    admin_auth,
    admin_courses,
    admin_tests,
    admin_control_tests,
    admin_analytics,
    admin_simulators,
    diagnostics,
)

app = FastAPI(title="Behruz Sayfiyev — Mini App API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _check_db_persistence():
    """
    Server ishga tushganda ma'lumotlar bazasi DOIMIY xotirada (Railway Volume)
    saqlanayotganini tekshiradi va natijani Deploy Logs'ga aniq chiqaradi.

    NEGA KERAK: Agar DB_PATH noto'g'ri sozlansa, ilova baribir xatosiz ishga
    tushadi — lekin har bir qayta deploy'da barcha ma'lumotlar (kurslar,
    testlar, foydalanuvchilar) jimgina o'chib ketadi. Bu xatoni oldindan,
    "sokin" ravishda emas, balki Deploy Logs'da katta va aniq ogohlantirish
    bilan ko'rsatish — soatlab sarflangan mehnatni yo'qotib qo'yishning oldini
    oladi.
    """
    path = db.DB_PATH
    abs_path = os.path.abspath(path)
    looks_persistent = path.startswith("/data") or path.startswith("/mnt") or path.startswith("/vol")

    print("=" * 66)
    print(f"[BAZA DIAGNOSTIKASI] DB_PATH = {path}")
    print(f"[BAZA DIAGNOSTIKASI] To'liq yo'l = {abs_path}")
    if looks_persistent:
        print("[BAZA DIAGNOSTIKASI] ✅ Doimiy xotira (Volume) yo'liga o'xshaydi.")
    else:
        print("[BAZA DIAGNOSTIKASI] ⚠️⚠️⚠️  DIQQAT — MUHIM OGOHLANTIRISH  ⚠️⚠️⚠️")
        print("[BAZA DIAGNOSTIKASI] ⚠️  DB_PATH doimiy Volume yo'liga o'xshamayapti!")
        print("[BAZA DIAGNOSTIKASI] ⚠️  Bu holatda HAR BIR qayta deploy'da BARCHA")
        print("[BAZA DIAGNOSTIKASI] ⚠️  ma'lumotlar (kurslar, testlar, foydalanuvchilar) O'CHIB KETADI!")
        print("[BAZA DIAGNOSTIKASI] ⚠️  Yechim: Railway -> Variables -> DB_PATH ni")
        print("[BAZA DIAGNOSTIKASI] ⚠️  Volume mount yo'lingizga (masalan /data/database.db) sozlang.")
    print("=" * 66)


@app.on_event("startup")
async def startup():
    db.init_db()
    db.add_sample_courses()
    _check_db_persistence()
    # Telegram botini Mini App backendi bilan BITTA jarayonda, fon vazifasi
    # (background task) sifatida ishga tushiramiz — shu sababli botni alohida
    # Railway xizmati qilib joylashtirish shart emas, va ikkalasi bitta
    # ma'lumotlar bazasidan foydalanadi.
    asyncio.create_task(bot_module.start_polling_background())
    # Obuna muddati tugayotgan foydalanuvchilarga avtomatik eslatma yuborish
    asyncio.create_task(bot_module.send_expiry_reminders_loop())


@app.on_event("shutdown")
async def shutdown():
    await bot_module.bot.session.close()


# ---------- Routerlarni ulash ----------

app.include_router(brand.router)
app.include_router(user.router)
app.include_router(courses.router)
app.include_router(tests.router)
app.include_router(simulators.router)
app.include_router(control_tests.router)
app.include_router(admin_auth.router)
app.include_router(admin_courses.router)
app.include_router(admin_tests.router)
app.include_router(admin_control_tests.router)
app.include_router(admin_analytics.router)
app.include_router(admin_simulators.router)
app.include_router(diagnostics.router)


# Mini App va admin panel statik fayllari (eng oxirida ulanadi —
# aks holda /api/* so'rovlarini "ushlab qolishi" mumkin)
app.mount("/", StaticFiles(directory="webapp", html=True), name="webapp")
