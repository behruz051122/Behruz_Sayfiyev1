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


# ---------- Mavzuli test: fan kartalari va guruhlar ----------

@router.get("/test-subject-cards")
def admin_list_test_subject_cards(admin=Depends(require_admin)):
    return {"cards": db.get_test_subject_cards(only_active=False)}


@router.post("/test-subject-cards")
def admin_create_test_subject_card(data: dict = Body(...), admin=Depends(require_admin)):
    return {"id": db.create_test_subject_card(data)}


@router.put("/test-subject-cards/{card_id}")
def admin_update_test_subject_card(card_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    db.update_test_subject_card(card_id, data)
    return {"ok": True}


@router.delete("/test-subject-cards/{card_id}")
def admin_delete_test_subject_card(card_id: int, admin=Depends(require_admin)):
    db.delete_test_subject_card(card_id)
    return {"ok": True}


@router.get("/test-stages")
def admin_list_test_stages(admin=Depends(require_admin)):
    return {"stages": db.get_all_test_stages(only_active=False)}


@router.post("/test-stages")
def admin_create_test_stage(data: dict = Body(...), admin=Depends(require_admin)):
    return {"id": db.create_test_stage(data)}


@router.put("/test-stages/{stage_id}")
def admin_update_test_stage(stage_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    db.update_test_stage(stage_id, data)
    return {"ok": True}


@router.delete("/test-stages/{stage_id}")
def admin_delete_test_stage(stage_id: int, admin=Depends(require_admin)):
    db.delete_test_stage(stage_id)
    return {"ok": True}


@router.get("/test-groups")
def admin_list_test_groups(admin=Depends(require_admin)):
    return {"groups": db.get_all_test_groups(only_active=False)}


@router.post("/test-groups")
def admin_create_test_group(data: dict = Body(...), admin=Depends(require_admin)):
    return {"id": db.create_test_group(data)}


@router.put("/test-groups/{group_id}")
def admin_update_test_group(group_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    db.update_test_group(group_id, data)
    return {"ok": True}


@router.delete("/test-groups/{group_id}")
def admin_delete_test_group(group_id: int, admin=Depends(require_admin)):
    db.delete_test_group(group_id)
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


# ---------- E'tirozlar (Attestatsiya) ----------

@router.get("/objections")
def admin_list_objections(status: str = None, admin=Depends(require_admin)):
    return {"objections": db.get_objections(status=status)}


@router.put("/objections/{objection_id}")
def admin_update_objection(objection_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    status = data.get("status", "reviewed")
    db.update_objection_status(objection_id, status)
    return {"ok": True}
