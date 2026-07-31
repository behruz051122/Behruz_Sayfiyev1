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

from rate_limit import limiter
import database as db

from routers import (
    brand,
    user,
    courses,
    tests,
    admin_auth,
    admin_courses,
    admin_tests,
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


@app.on_event("startup")
def startup():
    db.init_db()
    db.add_sample_courses()


# ---------- Routerlarni ulash ----------

app.include_router(brand.router)
app.include_router(user.router)
app.include_router(courses.router)
app.include_router(tests.router)
app.include_router(admin_auth.router)
app.include_router(admin_courses.router)
app.include_router(admin_tests.router)
app.include_router(diagnostics.router)


# Mini App va admin panel statik fayllari (eng oxirida ulanadi —
# aks holda /api/* so'rovlarini "ushlab qolishi" mumkin)
app.mount("/", StaticFiles(directory="webapp", html=True), name="webapp")
