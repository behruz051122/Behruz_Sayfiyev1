# routers/homework.py
# "Vazifa topshirish" bo'limi — o'quvchi ishlangan masalalar yechimini
# rasmga tushirib yuboradi. Paragraflar KETMA-KET ochiladi: o'quvchi
# navbatdagi paragrafni "Vazifalar to'liq yuklandi" deb yakunlamaguncha
# keyingisi ochilmaydi.
#
# XAVFSIZLIK: qulf tekshiruvi FAQAT frontendda emas, shu yerda ham
# bajariladi — brauzer konsolidan to'g'ridan-to'g'ri so'rov yuborilsa
# ham tartibni buzib bo'lmaydi.

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File, Response

from routers.deps import get_verified_telegram_user
from config import UPLOADS_DIR
from photo_urls import decorate_photo_urls
import database as db

router = APIRouter(prefix="/api/homework", tags=["homework"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
MAX_FILE_SIZE_BYTES = 8 * 1024 * 1024  # 8 MB — telefon kamerasidagi surat uchun yetarli


def _remove_local_upload(photo_url: str):
    """/uploads/... yo'lidagi faylni diskdan o'chiradi (xavfsiz — papkadan
    tashqariga chiqadigan yo'llarga ruxsat bermaydi)."""
    if not photo_url or not photo_url.startswith("/uploads/"):
        return
    rel = photo_url[len("/uploads/"):]
    target = os.path.normpath(os.path.join(UPLOADS_DIR, rel))
    if not target.startswith(os.path.normpath(UPLOADS_DIR)):
        return
    try:
        os.remove(target)
    except OSError:
        pass


def _ensure_subject_access(telegram_id: int, subject_id: int) -> dict:
    subject = db.get_homework_subject(subject_id)
    if not subject or not subject.get("is_active"):
        raise HTTPException(status_code=404, detail="Bo'lim topilmadi")
    if not db.user_can_access_homework_subject(telegram_id, subject_id):
        raise HTTPException(status_code=403, detail="Bu bo'lim sizga ochiq emas — tegishli kursga yozilishingiz kerak")
    return subject


def _ensure_paragraph_unlocked(telegram_id: int, subject_id: int, paragraph_number: int, subject: dict):
    total = int(subject.get("paragraph_count") or 0)
    if paragraph_number < 1 or paragraph_number > total:
        raise HTTPException(status_code=404, detail="Bunday paragraf yo'q")
    if not db.is_homework_paragraph_unlocked(telegram_id, subject_id, paragraph_number):
        raise HTTPException(
            status_code=403,
            detail=f"Avval {paragraph_number - 1}-paragraf vazifasini to'liq yuklab, yakunlang"
        )


@router.get("/subjects")
def api_homework_subjects(user=Depends(get_verified_telegram_user)):
    """O'quvchiga ko'rinadigan fanlar — har biri uchun kirish huquqi va
    umumiy progress (nechta paragrafdan nechtasi topshirilgan)."""
    telegram_id = user["telegram_id"]
    result = []
    for subject in db.get_homework_subjects(only_active=True):
        unlocked = db.user_can_access_homework_subject(telegram_id, subject["id"])
        item = dict(subject)
        item["unlocked"] = unlocked
        if unlocked:
            paragraphs = db.compute_homework_paragraphs(telegram_id, subject["id"])
            done = sum(1 for p in paragraphs if p["status"] in ("submitted", "graded"))
            item["done_count"] = done
            item["total_count"] = len(paragraphs)
            nxt = next((p for p in paragraphs if p["unlocked"] and p["status"] not in ("submitted", "graded")), None)
            item["next_paragraph"] = nxt["paragraph_number"] if nxt else None
        else:
            item["done_count"] = 0
            item["total_count"] = int(subject.get("paragraph_count") or 0)
            item["next_paragraph"] = None
        result.append(item)
    return {"subjects": result}


@router.get("/subjects/{subject_id}/paragraphs")
def api_homework_paragraphs(subject_id: int, user=Depends(get_verified_telegram_user)):
    """Fandagi barcha paragraflar — qulf holati va topshirish holati bilan."""
    telegram_id = user["telegram_id"]
    subject = _ensure_subject_access(telegram_id, subject_id)
    return {
        "subject": subject,
        "paragraphs": db.compute_homework_paragraphs(telegram_id, subject_id),
    }


@router.get("/subjects/{subject_id}/paragraphs/{paragraph_number}")
def api_homework_paragraph_detail(subject_id: int, paragraph_number: int,
                                  user=Depends(get_verified_telegram_user)):
    """Bitta paragraf tafsiloti — yuklangan rasmlar va o'qituvchi bahosi."""
    telegram_id = user["telegram_id"]
    subject = _ensure_subject_access(telegram_id, subject_id)
    _ensure_paragraph_unlocked(telegram_id, subject_id, paragraph_number, subject)

    submission = db.get_homework_submission(subject_id, telegram_id, paragraph_number)
    photos = decorate_photo_urls(db.get_homework_photos(submission["id"])) if submission else []
    return {
        "subject": subject,
        "paragraph_number": paragraph_number,
        "status": submission["status"] if submission else "empty",
        "teacher_score": submission.get("teacher_score") if submission else None,
        "teacher_comment": submission.get("teacher_comment") if submission else None,
        "photos": photos,
    }


@router.post("/subjects/{subject_id}/paragraphs/{paragraph_number}/photo")
async def api_homework_upload_photo(subject_id: int, paragraph_number: int,
                                    file: UploadFile = File(...),
                                    user=Depends(get_verified_telegram_user)):
    """Ishlangan masala yechimining suratini yuklash. Bitta paragrafga
    xohlagancha rasm qo'shish mumkin ("+" tugmasi)."""
    telegram_id = user["telegram_id"]
    subject = _ensure_subject_access(telegram_id, subject_id)
    _ensure_paragraph_unlocked(telegram_id, subject_id, paragraph_number, subject)

    submission = db.get_homework_submission(subject_id, telegram_id, paragraph_number)
    if submission and submission["status"] == "graded":
        raise HTTPException(status_code=400, detail="Bu vazifa allaqachon baholangan — o'zgartirib bo'lmaydi")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Faqat rasm fayllari qabul qilinadi (JPG, PNG, WEBP, HEIC)")

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Fayl bo'sh — boshqa rasm tanlang")
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Rasm hajmi 8 MB dan oshmasligi kerak")

    db.get_or_create_user(telegram_id, user["first_name"], user.get("username"))

    # ---- 1-usul (asosiy): rasmni TELEGRAM arxiv kanaliga yuborish ----
    # Server xotirasi (Railway Volume) to'lib ketmasligi uchun fayl diskda
    # SAQLANMAYDI — bazada faqat qisqa file_id qoladi.
    import bot as bot_module
    if bot_module.homework_archive_enabled():
        caption = (
            f"{subject.get('title', '')} · {paragraph_number}-paragraf\n"
            f"{user.get('first_name') or ''} "
            f"{('@' + user['username']) if user.get('username') else ''} "
            f"(ID {telegram_id})"
        ).strip()
        archived = await bot_module.upload_homework_photo_to_archive(
            contents, filename=f"p{paragraph_number}{ext or '.jpg'}", caption=caption
        )
        if archived:
            db.add_homework_photo(
                subject_id, telegram_id, paragraph_number,
                # Ustun NOT NULL bo'lgani uchun bo'sh satr yoziladi — rasm
                # diskda emas, Telegramda ekanini `storage`/`telegram_file_id`
                # ko'rsatadi.
                photo_url="",
                telegram_file_id=archived["file_id"],
                telegram_message_id=archived["message_id"],
                storage="telegram",
            )
            return {"ok": True, "storage": "telegram"}

    # ---- 2-usul (zaxira): arxiv kanal sozlanmagan yoki yuborib bo'lmadi ----
    # Tizim to'xtamaydi — rasm avvalgidek diskka saqlanadi.
    save_dir = os.path.join(UPLOADS_DIR, "homework")
    os.makedirs(save_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(save_dir, filename), "wb") as f:
        f.write(contents)
    url = f"/uploads/homework/{filename}"

    db.add_homework_photo(subject_id, telegram_id, paragraph_number, url, storage="local")
    return {"ok": True, "url": url, "storage": "local"}


@router.get("/photo/{photo_id}")
async def api_homework_photo(photo_id: int, e: int = 0, s: str = ""):
    """Telegramda saqlangan vazifa rasmini ko'rsatadi.

    XAVFSIZLIK: havola IMZOLANGAN bo'lishi shart (?e=muddat&s=imzo).
    Imzo faqat rasmlar ro'yxati berilayotganda — kirish huquqi
    tekshirilgandan keyin — hosil qilinadi va 24 soatdan keyin kuchini
    yo'qotadi. Telegram file_id hech qachon brauzerga chiqmaydi.

    (Header orqali himoya qilib bo'lmaydi, chunki <img src="..."> tegi
    maxsus header yubormaydi.)"""
    from config import JWT_SECRET_KEY
    from auth import verify_photo_token

    if not verify_photo_token(photo_id, e, s, JWT_SECRET_KEY):
        raise HTTPException(status_code=403, detail="Havola yaroqsiz yoki muddati o'tgan")

    record = db.get_homework_photo_record(photo_id)
    if not record:
        raise HTTPException(status_code=404, detail="Rasm topilmadi")

    file_id = record.get("telegram_file_id")
    if not file_id:
        raise HTTPException(status_code=404, detail="Bu rasm Telegramda saqlanmagan")

    import bot as bot_module
    data = await bot_module.fetch_telegram_file(file_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Rasmni yuklab bo'lmadi (o'chirilgan bo'lishi mumkin)")

    # Rasm o'zgarmaydi — brauzer keshiga qo'yamiz, shunda takroriy
    # ochishlarda Telegramga qayta murojaat qilinmaydi.
    return Response(
        content=data,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.delete("/photos/{photo_id}")
async def api_homework_delete_photo(photo_id: int, user=Depends(get_verified_telegram_user)):
    """Noto'g'ri chiqqan rasmni o'chirish (faqat o'z rasmini va faqat
    baholanmagan vazifadan). Arxiv kanaldagi nusxasi va diskdagi fayl
    ham tozalanadi — keraksiz ma'lumot qolib ketmaydi."""
    result = db.delete_homework_photo(photo_id, user["telegram_id"])
    if not result.get("ok"):
        raise HTTPException(status_code=403, detail=result.get("detail", "O'chirib bo'lmadi"))

    if result.get("telegram_message_id"):
        import bot as bot_module
        await bot_module.delete_archive_message(result["telegram_message_id"])
    if result.get("photo_url"):
        _remove_local_upload(result["photo_url"])
    return {"ok": True}


@router.post("/subjects/{subject_id}/paragraphs/{paragraph_number}/submit")
def api_homework_submit(subject_id: int, paragraph_number: int,
                        user=Depends(get_verified_telegram_user)):
    """"Vazifalar to'liq yuklandi" tugmasi — topshiriqni yakunlaydi va
    shu bilan KEYINGI paragraf ochiladi."""
    telegram_id = user["telegram_id"]
    subject = _ensure_subject_access(telegram_id, subject_id)
    _ensure_paragraph_unlocked(telegram_id, subject_id, paragraph_number, subject)

    result = db.submit_homework_paragraph(subject_id, telegram_id, paragraph_number)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("detail", "Topshirib bo'lmadi"))
    return result


@router.get("/my-summary")
def api_homework_my_summary(user=Depends(get_verified_telegram_user)):
    """O'quvchining o'z vazifa ko'rsatkichi."""
    return db.get_user_homework_summary(user["telegram_id"])
