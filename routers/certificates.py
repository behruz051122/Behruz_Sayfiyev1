# routers/certificates.py
from fastapi import APIRouter, Depends, HTTPException, Response

from config import BRAND_NAME
from routers.deps import get_verified_telegram_user
from certificate_pdf import generate_certificate_pdf
import database as db

router = APIRouter(prefix="/api", tags=["certificates"])


def _format_date(iso_str: str) -> str:
    """'2026-08-05 12:30:00' yoki ISO satrni 'DD.MM.YYYY' shakliga o'tkazadi."""
    try:
        date_part = iso_str.split(" ")[0].split("T")[0]
        year, month, day = date_part.split("-")
        return f"{day}.{month}.{year}"
    except Exception:
        return iso_str


@router.get("/course/{course_id}/certificate/status")
def api_certificate_status(course_id: int, user=Depends(get_verified_telegram_user)):
    course = db.get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Kurs topilmadi")

    telegram_id = user["telegram_id"]
    completion = db.get_course_completion(telegram_id, course_id)
    return {
        "course_id": course_id,
        "course_title": course["title"],
        **completion,
    }


@router.get("/course/{course_id}/certificate/download")
def api_certificate_download(course_id: int, user=Depends(get_verified_telegram_user)):
    course = db.get_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Kurs topilmadi")

    telegram_id = user["telegram_id"]
    cert = db.get_or_issue_certificate(telegram_id, course_id)
    if not cert:
        raise HTTPException(status_code=400, detail="Kurs hali 100% tugallanmagan")

    pdf_bytes = generate_certificate_pdf(
        student_name=user["first_name"],
        course_title=course["title"],
        brand_name=BRAND_NAME,
        certificate_number=cert["certificate_number"],
        issued_date=_format_date(cert["issued_at"]),
    )

    filename = f"sertifikat_{cert['certificate_number']}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/my-certificates")
def api_my_certificates(user=Depends(get_verified_telegram_user)):
    certs = db.get_my_certificates(user["telegram_id"])
    return {"certificates": certs}
