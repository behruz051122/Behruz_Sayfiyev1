# routers/uploads.py
# Admin panelda rasm (savol grafigi/jadvali va h.k.) fayl sifatida to'g'ridan-
# to'g'ri yuklash uchun. Bungacha admin faqat tashqi havola kirita olardi —
# ko'pincha bu havolalar (telefon galereyasi, Google linklar) to'g'ridan-
# to'g'ri rasmga ishora qilmagani uchun rasm ochilmay qolardi. Endi rasm
# to'g'ridan-to'g'ri serverning o'ziga saqlanadi va kafolatlangan holda ishlaydi.

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from routers.deps import require_admin
from config import UPLOADS_DIR

router = APIRouter(prefix="/api/admin", tags=["uploads"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB — savol rasmlari uchun yetarli va server xotirasini asraydi


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

    os.makedirs(UPLOADS_DIR, exist_ok=True)
    # Tasodifiy nom — ikkita admin bir vaqtda bir xil nomli rasm yuklasa ham
    # ustma-ust yozilib ketmasligi uchun.
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOADS_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(contents)

    return {"url": f"/uploads/{filename}", "filename": filename}
