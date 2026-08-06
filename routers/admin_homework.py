# routers/admin_homework.py
# O'qituvchi uchun "Vazifa topshirish" boshqaruvi:
#   - fanlar (Kimyo, Biologiya, ...) va ularning paragraflar soni
#   - topshirilgan vazifalarni ko'rib, 0..10 ball qo'yish
#   - kechikkanlar ro'yxati va ogohlantirish yuborish
#   - oy yakunidagi UMUMLASHGAN reyting (nazorat testi + vazifa)

import datetime

from fastapi import APIRouter, Depends, Body, HTTPException

from routers.deps import require_admin
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


# ---------- Baholash navbati ----------

@router.get("/pending")
def admin_pending_submissions(subject_id: int = None, admin=Depends(require_admin)):
    """Topshirilgan, lekin hali baholanmagan vazifalar (rasmlari bilan)."""
    return {"submissions": db.get_homework_pending_submissions(subject_id)}


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
