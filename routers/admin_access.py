# routers/admin_access.py
# ==========================================================================
#  ADMIN — PULLIK GURUHLAR VA AVTOMATIK KIRISH
# ==========================================================================
# O'qituvchi bu yerda:
#   1) pullik guruhini qo'shadi (chat_id + taklif havolasi)
#   2) botning guruhda admin ekanini bir bosishda tekshiradi
#   3) qaysi kurs / test bosqichi qaysi guruhga tegishli ekanini belgilaydi
#
# Shundan keyin o'quvchilarni QO'LDA qo'shish shart emas: guruhda bo'lgan
# har kim avtomatik kirish oladi, chiqib ketgani esa ~10 daqiqada yopiladi.

from fastapi import APIRouter, Depends, HTTPException, Body

from routers.deps import require_admin
import database as db
import access_control

router = APIRouter(prefix="/api/admin/access", tags=["admin-access"])


# --------------------------------------------------------------------------
#  Guruhlar
# --------------------------------------------------------------------------

@router.get("/groups")
def admin_list_groups(admin=Depends(require_admin)):
    groups = db.get_access_groups()
    links = db.get_all_content_links()
    for g in groups:
        g["member_count"] = db.get_group_member_count(g["id"])
        g["course_count"] = sum(1 for (t, _), ids in links.items()
                                if t == "course" and g["id"] in ids)
        g["stage_count"] = sum(1 for (t, _), ids in links.items()
                               if t == "test_stage" and g["id"] in ids)
    return {"groups": groups, "ttl_minutes": db.MEMBERSHIP_TTL_MINUTES}


@router.post("/groups")
def admin_create_group(data: dict = Body(...), admin=Depends(require_admin)):
    title = (data.get("title") or "").strip()
    chat_id = (data.get("chat_id") or "").strip()
    if not title or not chat_id:
        raise HTTPException(status_code=400, detail="Guruh nomi va chat_id majburiy")

    # Eng ko'p uchraydigan xato: yopiq guruh ID sini "-100" prefiksisiz kiritish.
    if chat_id.lstrip("-").isdigit() and chat_id.startswith("-") and not chat_id.startswith("-100"):
        raise HTTPException(
            status_code=400,
            detail="Yopiq guruh/kanal ID si '-100' bilan boshlanadi. "
                   "Masalan: -1001234567890")

    gid = db.create_access_group(title, chat_id, data.get("invite_link"))
    return {"success": True, "id": gid}


@router.put("/groups/{group_id}")
def admin_update_group(group_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    if not db.get_access_group(group_id):
        raise HTTPException(status_code=404, detail="Guruh topilmadi")
    db.update_access_group(group_id, **data)
    return {"success": True}


@router.delete("/groups/{group_id}")
def admin_delete_group(group_id: int, admin=Depends(require_admin)):
    db.delete_access_group(group_id)
    return {"success": True}


@router.post("/groups/{group_id}/verify")
async def admin_verify_group(group_id: int, admin=Depends(require_admin)):
    """Bot guruhda ADMINmi? — sozlashdagi eng ko'p uchraydigan xatoni topadi.

    Bot admin bo'lmasa Telegram a'zolikni tekshirishga ruxsat bermaydi va
    hech kim kirish ololmaydi. Shuning uchun bu tugma juda muhim.
    """
    g = db.get_access_group(group_id)
    if not g:
        raise HTTPException(status_code=404, detail="Guruh topilmadi")

    import bot as bot_module
    result = await access_control.verify_group_setup(bot_module.bot, g["chat_id"])
    db.update_access_group(group_id, last_error=result.get("error"))
    return result


@router.post("/groups/{group_id}/sync")
async def admin_sync_group(group_id: int, admin=Depends(require_admin)):
    """Bazadagi barcha foydalanuvchilarning shu guruhdagi a'zoligini
    darhol qayta tekshiradi.

    Odatda buni fon vazifasi o'zi bajaradi. Bu tugma "hozir tekshirilsin"
    deganda ishlatiladi — masalan guruhga ko'p odam qo'shgandan keyin.
    """
    g = db.get_access_group(group_id)
    if not g:
        raise HTTPException(status_code=404, detail="Guruh topilmadi")

    import bot as bot_module
    users = db.get_users_needing_membership_refresh(limit=500)
    checked = members = 0
    for tid in users:
        is_member, status, _ = await access_control.check_membership(
            bot_module.bot, g["chat_id"], tid)
        db.save_membership(tid, group_id, is_member, status)
        checked += 1
        if is_member:
            members += 1
    return {"success": True, "checked": checked, "members": members,
            "total_members_cached": db.get_group_member_count(group_id)}


# --------------------------------------------------------------------------
#  Kontentni guruhga bog'lash
# --------------------------------------------------------------------------

@router.get("/links")
def admin_list_links(admin=Depends(require_admin)):
    """Kurslar va test bosqichlari + ularning guruh bog'lanishlari.

    Bitta so'rovda hammasi qaytadi — admin panelda bitta jadvalda
    ko'rsatiladi va o'qituvchi nima ochiq, nima yopiqligini bir qarashda
    ko'radi.
    """
    links = db.get_all_content_links()

    courses = []
    for c in db.get_all_courses():
        courses.append({
            "id": c["id"], "title": c["title"],
            "is_free": bool(c["is_free"]),
            "group_ids": links.get(("course", c["id"]), []),
        })

    stages = []
    for card in db.get_test_subject_cards(only_active=False):
        for st in db.get_test_stages(card["id"], only_active=False):
            stages.append({
                "id": st["id"],
                "title": f"{card['title']} — {st['title']}",
                "group_ids": links.get(("test_stage", st["id"]), []),
            })

    return {"courses": courses, "stages": stages,
            "groups": db.get_access_groups(only_active=True)}


@router.put("/links/{content_type}/{content_id}")
def admin_set_links(content_type: str, content_id: int, data: dict = Body(...),
                    admin=Depends(require_admin)):
    if content_type not in ("course", "test_stage"):
        raise HTTPException(status_code=400, detail="Noma'lum kontent turi")
    db.set_content_groups(content_type, content_id, data.get("group_ids") or [])
    return {"success": True}
