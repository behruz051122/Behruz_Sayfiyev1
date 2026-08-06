# routers/admin_homework.py
# O'qituvchi uchun "Vazifa topshirish" boshqaruvi:
#   - fanlar (Kimyo, Biologiya, ...) va ularning paragraflar soni
#   - topshirilgan vazifalarni ko'rib, 0..10 ball qo'yish
#   - kechikkanlar ro'yxati va ogohlantirish yuborish
#   - oy yakunidagi UMUMLASHGAN reyting (nazorat testi + vazifa)

import datetime

from fastapi import APIRouter, Depends, Body, HTTPException

from routers.deps import require_admin
from photo_urls import decorate_photo_urls
import database as db

router = APIRouter(prefix="/api/admin/homework", tags=["admin-homework"])


# ---------- Fanlar ----------

@router.get("/subjects")
def admin_list_subjects(admin=Depends(require_admin)):
    subjects = db.get_homework_subjects(only_active=False)
    for s in subjects:
        s["course_ids"] = db.get_homework_subject_course_ids(s["id"])
    return {"subjects": subjects}


@router.post("/subjects")
def admin_create_subject(data: dict = Body(...), admin=Depends(require_admin)):
    if not (data.get("title") or "").strip():
        raise HTTPException(status_code=400, detail="Bo'lim nomini yozing")
    return {"id": db.create_homework_subject(data)}


@router.put("/subjects/{subject_id}")
def admin_update_subject(subject_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    db.update_homework_subject(subject_id, data)
    return {"ok": True}


@router.delete("/subjects/{subject_id}")
def admin_delete_subject(subject_id: int, admin=Depends(require_admin)):
    db.delete_homework_subject(subject_id)
    return {"ok": True}


# ---------- Boshlanish paragrafi (nechanchidan boshlansin) ----------

@router.post("/subjects/{subject_id}/apply-start")
def admin_apply_start_paragraph(subject_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    """"Hozirgi o'quvchilarga qo'llash" — aynan shu paytda kursda bo'lgan
    har bir o'quvchiga boshlanish paragrafini yozadi.

    Masalan o'qituvchi 60 ni belgilasa: hozirgi o'quvchilar 60-paragrafdan
    davom etadi (1–59 ularga umuman ko'rinmaydi), keyin qo'shiladigan
    YANGI o'quvchilar esa 1-paragrafdan boshlaydi."""
    subject = db.get_homework_subject(subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Fan topilmadi")
    start = int(data.get("start_paragraph") or 1)
    total = int(subject.get("paragraph_count") or 0)
    if start < 1 or (total and start > total):
        raise HTTPException(status_code=400, detail=f"1 dan {total} gacha son kiriting")
    return db.apply_homework_start_to_current_students(subject_id, start)


@router.get("/subjects/{subject_id}/starts")
def admin_list_student_starts(subject_id: int, admin=Depends(require_admin)):
    """Kim qaysi paragrafdan boshlagani ro'yxati."""
    return {"starts": db.get_homework_student_starts(subject_id)}


@router.put("/subjects/{subject_id}/starts/{telegram_id}")
def admin_set_student_start(subject_id: int, telegram_id: int, data: dict = Body(...),
                            admin=Depends(require_admin)):
    """Bitta o'quvchining boshlanish paragrafini alohida o'zgartirish."""
    return db.set_homework_student_start(subject_id, telegram_id, int(data.get("start_paragraph") or 1))


@router.delete("/subjects/{subject_id}/starts/{telegram_id}")
def admin_clear_student_start(subject_id: int, telegram_id: int, admin=Depends(require_admin)):
    """Shaxsiy nuqtani bekor qilish — o'quvchi yana 1-paragrafdan boshlaydi."""
    return db.clear_homework_student_start(subject_id, telegram_id)


# ---------- Baholash navbati ----------

@router.get("/pending")
def admin_pending_submissions(subject_id: int = None, admin=Depends(require_admin)):
    """Topshirilgan, lekin hali baholanmagan vazifalar (rasmlari bilan)."""
    submissions = db.get_homework_pending_submissions(subject_id)
    for s in submissions:
        decorate_photo_urls(s.get("photos"))
    return {"submissions": submissions}


@router.post("/grade")
def admin_grade_submission(data: dict = Body(...), admin=Depends(require_admin)):
    """0..10 ball qo'yish yoki qayta ishlashga qaytarish (reject=true)."""
    submission_id = int(data["submission_id"])
    reject = bool(data.get("reject"))
    teacher_score = data.get("teacher_score")
    if not reject and teacher_score is None:
        raise HTTPException(status_code=400, detail="Ball qo'ying yoki qayta ishlashga qaytaring")
    graded_by = admin.get("telegram_id") if isinstance(admin, dict) else None
    return db.grade_homework_submission(
        submission_id, teacher_score, data.get("teacher_comment") or "", graded_by, reject=reject
    )


# ---------- Kechikkanlar ----------

@router.get("/late")
def admin_late_students(subject_id: int = None, admin=Depends(require_admin)):
    """Vazifani belgilangan muddatda topshirmagan o'quvchilar."""
    return {"students": db.get_homework_late_students(subject_id)}


@router.post("/remind")
async def admin_send_reminder(data: dict = Body(...), admin=Depends(require_admin)):
    """Tanlangan o'quvchilarga (yoki barcha kechikkanlarga) Telegram
    orqali ogohlantirish yuboradi."""
    import bot as bot_module

    targets = data.get("students")
    if targets is None:
        targets = db.get_homework_late_students(data.get("subject_id"))

    sent, failed = 0, 0
    for s in targets:
        text = (
            f"⚠️ <b>Vazifa eslatmasi</b>\n\n"
            f"Hurmatli {s.get('first_name') or 'o‘quvchi'}, "
            f"<b>{s.get('subject_title', '')}</b> bo‘limi bo‘yicha "
            f"<b>{s.get('waiting_paragraph')}-paragraf</b> vazifasi hali topshirilmagan.\n\n"
            f"Iltimos, ishlangan masalalar yechimini rasmga tushirib, ilovaga yuklang."
        )
        try:
            await bot_module.bot.send_message(s["telegram_id"], text, parse_mode="HTML")
            db.mark_homework_reminder_sent(s["telegram_id"], s.get("subject_id"), s.get("waiting_paragraph"))
            sent += 1
        except Exception:
            failed += 1
    return {"ok": True, "sent": sent, "failed": failed}


# ---------- Rasm ombori: holat va tozalash ----------

@router.get("/storage")
def admin_storage_status(admin=Depends(require_admin)):
    """Rasmlar qayerda saqlanayotgani va qancha joy egallagani."""
    import bot as bot_module
    from config import HOMEWORK_PHOTO_RETENTION_DAYS
    stats = db.get_homework_storage_stats()
    stats["archive_enabled"] = bot_module.homework_archive_enabled()
    stats["retention_days"] = HOMEWORK_PHOTO_RETENTION_DAYS
    return stats


@router.post("/cleanup")
async def admin_cleanup_photos(data: dict = Body(default={}), admin=Depends(require_admin)):
    """Eski rasmlarni QO'LDA tozalash (avtomatik tozalash ham kuniga
    bir marta o'zi ishlaydi). Ball va izohlarga tegilmaydi."""
    import bot as bot_module
    days = data.get("retention_days")
    return await bot_module.cleanup_old_homework_photos(int(days) if days else None)


# ---------- Oy yakuniy umumlashgan reyting ----------

@router.get("/ranking")
def admin_combined_ranking(year: int = None, month: int = None, admin=Depends(require_admin)):
    """Nazorat testi (50%) + vazifa (50%) bo'yicha oylik umumiy reyting —
    chegirma beriladigan o'quvchilarni aniqlash uchun."""
    now = datetime.datetime.utcnow()
    y = year or now.year
    m = month or now.month
    return {
        "year": y, "month": m,
        "test_weight": db.RANKING_TEST_WEIGHT,
        "homework_weight": db.RANKING_HOMEWORK_WEIGHT,
        "ranking": db.get_combined_monthly_leaderboard(y, m),
    }
