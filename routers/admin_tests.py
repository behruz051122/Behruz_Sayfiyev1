# routers/admin_tests.py
from fastapi import APIRouter, Depends, Body

from routers.deps import require_admin
import database as db

router = APIRouter(prefix="/api/admin", tags=["admin-tests"])


# ---------- Testlar ----------

@router.get("/tests")
def admin_list_tests(admin=Depends(require_admin)):
    tests = db.get_all_tests(only_active=False)
    for t in tests:
        t["question_count"] = db.count_test_questions(t["id"])
    return {"tests": tests}


@router.post("/tests")
def admin_create_test(data: dict = Body(...), admin=Depends(require_admin)):
    return {"id": db.create_test(data)}


@router.put("/tests/{test_id}")
def admin_update_test(test_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    db.update_test(test_id, data)
    return {"ok": True}


@router.delete("/tests/{test_id}")
def admin_delete_test(test_id: int, admin=Depends(require_admin)):
    db.delete_test(test_id)
    return {"ok": True}


# ---------- Savollar ----------

@router.get("/tests/{test_id}/questions")
def admin_list_questions(test_id: int, admin=Depends(require_admin)):
    return {"questions": db.get_questions(test_id)}


@router.post("/questions")
def admin_create_question(data: dict = Body(...), admin=Depends(require_admin)):
    return {"id": db.create_question(data)}


@router.put("/questions/{question_id}")
def admin_update_question(question_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    db.update_question(question_id, data)
    return {"ok": True}


@router.delete("/questions/{question_id}")
def admin_delete_question(question_id: int, admin=Depends(require_admin)):
    db.delete_question(question_id)
    return {"ok": True}
