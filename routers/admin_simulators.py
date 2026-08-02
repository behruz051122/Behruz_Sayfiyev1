# routers/admin_simulators.py
from fastapi import APIRouter, Depends, Body

from routers.deps import require_admin
import database as db

router = APIRouter(prefix="/api/admin", tags=["admin-simulators"])


@router.get("/simulators")
def admin_list_simulators(admin=Depends(require_admin)):
    sims = db.get_all_simulators(only_active=False)
    for s in sims:
        s["subjects"] = db.get_simulator_subjects(s["id"])
    return {"simulators": sims}


@router.post("/simulators")
def admin_create_simulator(data: dict = Body(...), admin=Depends(require_admin)):
    return {"id": db.create_simulator(data)}


@router.put("/simulators/{simulator_id}")
def admin_update_simulator(simulator_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    db.update_simulator(simulator_id, data)
    return {"ok": True}


@router.delete("/simulators/{simulator_id}")
def admin_delete_simulator(simulator_id: int, admin=Depends(require_admin)):
    db.delete_simulator(simulator_id)
    return {"ok": True}


@router.get("/simulators/{simulator_id}/subjects")
def admin_list_simulator_subjects(simulator_id: int, admin=Depends(require_admin)):
    return {
        "subjects": db.get_simulator_subjects(simulator_id),
        "subject_pools": db.get_subject_pools(),
    }


@router.post("/simulator-subjects")
def admin_add_simulator_subject(data: dict = Body(...), admin=Depends(require_admin)):
    return {"id": db.add_simulator_subject(data)}


@router.delete("/simulator-subjects/{entry_id}")
def admin_delete_simulator_subject(entry_id: int, admin=Depends(require_admin)):
    db.delete_simulator_subject(entry_id)
    return {"ok": True}
