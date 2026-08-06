# routers/uploads.py
# Admin panelda rasm (savol grafigi/jadvali va h.k.) fayl sifatida to'g'ridan-
# to'g'ri yuklash uchun. Bungacha admin faqat tashqi havola kirita olardi —
# ko'pincha bu havolalar (telefon galereyasi, Google linklar) to'g'ridan-
# to'g'ri rasmga ishora qilmagani uchun rasm ochilmay qolardi. Endi rasm
# to'g'ridan-to'g'ri serverning o'ziga saqlanadi va kafolatlangan holda ishlaydi.

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from routers.deps import require_admin, get_verified_telegram_user
from config import UPLOADS_DIR

router = APIRouter(prefix="/api/admin", tags=["uploads"])
public_router = APIRouter(prefix="/api", tags=["uploads"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB — savol rasmlari uchun yetarli va server xotirasini asraydi


def _save_uploaded_image(contents: bytes, ext: str, subdir: str = "") -> str:
    save_dir = os.path.join(UPLOADS_DIR, subdir) if subdir else UPLOADS_DIR
    os.makedirs(save_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(save_dir, filename)
    with open(filepath, "wb") as f:
        f.write(contents)
    url_path = f"/uploads/{subdir}/{filename}" if subdir else f"/uploads/{filename}"
    return url_path, filename


@router.post("/upload-image")
async def admin_upload_image(file: UploadFile = File(...), admin=Depends(require_admin)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Faqat rasm fayllari qabul qilinadi (JPG, PNG, WEBP yoki GIF)."
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Rasm hajmi 5 MB dan oshmasligi kerak.")
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Fayl bo'sh — boshqa rasm tanlang.")

    url, filename = _save_uploaded_image(contents, ext)
    return {"url": url, "filename": filename}


# ---------- Talaba tomonidan yuklanadigan rasmlar (masalan Milliy sertifikat
# yozma ish javobi — talaba qo'lda yozgan yechimni surat qilib yuboradi) ----------

@public_router.post("/upload-answer-image")
async def student_upload_answer_image(file: UploadFile = File(...), user=Depends(get_verified_telegram_user)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Faqat rasm fayllari qabul qilinadi (JPG, PNG, WEBP yoki GIF)."
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Rasm hajmi 5 MB dan oshmasligi kerak.")
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Fayl bo'sh — boshqa rasm tanlang.")

    url, filename = _save_uploaded_image(contents, ext, subdir="answers")
    return {"url": url, "filename": filename}
