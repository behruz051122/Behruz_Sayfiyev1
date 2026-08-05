# routers/admin_docx_import.py
# Admin Word (.docx) fayl yuklab, o'nlab savolni bir zumda (rasmlari bilan
# birga) testga qo'shishi uchun. Bittalab yozish o'rniga — bitta fayl.

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from routers.deps import require_admin
from config import UPLOADS_DIR
import database as db
from docx_import import parse_docx, IMAGE_EXT_BY_CONTENT_TYPE

router = APIRouter(prefix="/api/admin", tags=["docx-import"])

CORRECT_INDEX_BY_LETTER = {"A": 1, "B": 2, "C": 3, "D": 4}


@router.post("/tests/{test_id}/import-docx")
async def admin_import_docx(test_id: int, file: UploadFile = File(...), admin=Depends(require_admin)):
    test = db.get_test(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test topilmadi")

    if not (file.filename or "").lower().endswith(".docx"):
        raise HTTPException(
            status_code=400,
            detail="Faqat .docx fayl qabul qilinadi. Word'da faylni 'Saqlash' qilganda formatini '.docx' deb tanlang."
        )

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Fayl bo'sh.")

    try:
        parsed_questions = parse_docx(contents)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Faylni o'qib bo'lmadi — fayl buzilgan yoki .docx formatida emas ({e})"
        )

    if not parsed_questions:
        raise HTTPException(
            status_code=400,
            detail="Faylda birorta ham savol topilmadi. Har bir savol \"1. \", \"2. \" kabi raqam bilan boshlanishi kerak — namuna shablonga qarang."
        )

    os.makedirs(UPLOADS_DIR, exist_ok=True)

    imported = 0
    skipped = []
    order_cursor = db.count_test_questions(test_id)

    for q in parsed_questions:
        if not q.is_complete():
            skipped.append({
                "order_num": q.order_num,
                "text": (q.question_text or "(matn topilmadi)")[:70],
                "reason": q.missing_summary(),
            })
            continue

        image_url = ""
        if q.image_bytes:
            ext = IMAGE_EXT_BY_CONTENT_TYPE.get(q.image_content_type)
            if ext:
                filename = f"{uuid.uuid4().hex}{ext}"
                with open(os.path.join(UPLOADS_DIR, filename), "wb") as f:
                    f.write(q.image_bytes)
                image_url = f"/uploads/{filename}"

        order_cursor += 1
        db.create_question({
            "test_id": test_id,
            "question_text": q.question_text,
            "image_url": image_url,
            "option_1": q.options.get("A", ""),
            "option_2": q.options.get("B", ""),
            "option_3": q.options.get("C", ""),
            "option_4": q.options.get("D", ""),
            "correct_index": CORRECT_INDEX_BY_LETTER[q.effective_correct_letter],
            "order_num": order_cursor,
            "table_data": q.table_data_json(),
        })
        imported += 1

    return {
        "imported": imported,
        "total_found": len(parsed_questions),
        "skipped": skipped,
    }
