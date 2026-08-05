# routers/student_results.py
# "Natijalar" — o'quvchilarning kurs/dars haqidagi fikri va sertifikat
# natijalari lentasi. Bu reyting (leaderboard)dan BUTUNLAY ALOHIDA — admin
# qo'lda to'ldiradigan "muvaffaqiyat hikoyalari" (rasm + qisqa natija +
# fikr). O'QISH uchun ochiq (autentifikatsiyasiz) endpoint.

from fastapi import APIRouter

import database as db

router = APIRouter(prefix="/api", tags=["student-results"])


@router.get("/student-results")
def api_student_results():
    return {"results": db.get_student_results(only_active=True)}
