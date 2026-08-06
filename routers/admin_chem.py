# routers/admin_chem.py
# ==========================================================================
#  KIMYO O'YINI — admin boshqaruvi
# ==========================================================================
# O'qituvchi bu yerda faqat MODDA kiritadi — savollar avtomatik yasaladi.
#
# Eng muhim qism: OMMAVIY YUKLASH (`/levels/{id}/bulk`). 276 ta moddani
# bitta-bitta formadan kiritish real emas, shuning uchun matnni bir yo'la
# joylashtirib yuborish mumkin:
#
#     HF | ftorid kislota
#     HCl | xlorid kislota | tuz kislotasi
#     PbS | qo'rg'oshin sulfid | qo'rg'oshin yaltirog'i | qora | — | qora
#
# Ustunlar tartibi:
#     formula | nomi | tarixiy nomi | sof rang | eritma rangi | cho'kma rangi
# Faqat birinchi ikkitasi majburiy; qolganlarini keyin to'ldirsa ham bo'ladi.

from fastapi import APIRouter, Depends, HTTPException, Body

from routers.deps import require_admin
import database as db

router = APIRouter(prefix="/api/admin/chem", tags=["admin-chem"])


# --------------------------------------------------------------------------
#  Kategoriyalar
# --------------------------------------------------------------------------

@router.get("/categories")
def admin_list_categories(admin=Depends(require_admin)):
    cats = db.get_chem_categories()
    for c in cats:
        levels = db.get_chem_levels(c["id"], only_active=False)
        c["level_count"] = len(levels)
        c["substance_count"] = sum(l["substance_count"] for l in levels)
    return {"categories": cats}


@router.post("/categories")
def admin_create_category(data: dict = Body(...), admin=Depends(require_admin)):
    key = (data.get("key") or "").strip()
    title = (data.get("title") or "").strip()
    if not key or not title:
        raise HTTPException(status_code=400, detail="Kalit va nom majburiy")
    if any(c["key"] == key for c in db.get_chem_categories()):
        raise HTTPException(status_code=400, detail="Bu kalit allaqachon mavjud")
    cid = db.create_chem_category(
        key, title,
        subtitle=(data.get("subtitle") or "").strip(),
        icon=(data.get("icon") or "🧪").strip(),
        is_ready=data.get("is_ready", 0),
        sort_order=data.get("sort_order", 0),
    )
    return {"success": True, "id": cid}


@router.put("/categories/{category_id}")
def admin_update_category(category_id: int, data: dict = Body(...),
                          admin=Depends(require_admin)):
    if not db.get_chem_category(category_id):
        raise HTTPException(status_code=404, detail="Kategoriya topilmadi")
    db.update_chem_category(category_id, **data)
    return {"success": True}


@router.delete("/categories/{category_id}")
def admin_delete_category(category_id: int, admin=Depends(require_admin)):
    db.delete_chem_category(category_id)
    return {"success": True}


# --------------------------------------------------------------------------
#  Levellar
# --------------------------------------------------------------------------

@router.get("/categories/{category_id}/levels")
def admin_list_levels(category_id: int, admin=Depends(require_admin)):
    return {"levels": db.get_chem_levels(category_id, only_active=False)}


@router.post("/categories/{category_id}/levels")
def admin_create_level(category_id: int, data: dict = Body(...),
                       admin=Depends(require_admin)):
    title = (data.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Level nomi majburiy")
    if not db.get_chem_category(category_id):
        raise HTTPException(status_code=404, detail="Kategoriya topilmadi")

    # Tartib raqami berilmasa — oxiriga qo'shamiz.
    order = data.get("sort_order")
    if order in (None, ""):
        existing = db.get_chem_levels(category_id, only_active=False)
        order = (max([l["sort_order"] for l in existing]) + 1) if existing else 1

    lid = db.create_chem_level(category_id, title, sort_order=order)
    return {"success": True, "id": lid}


@router.put("/levels/{level_id}")
def admin_update_level(level_id: int, data: dict = Body(...),
                       admin=Depends(require_admin)):
    if not db.get_chem_level(level_id):
        raise HTTPException(status_code=404, detail="Level topilmadi")
    db.update_chem_level(level_id, **data)
    return {"success": True}


@router.delete("/levels/{level_id}")
def admin_delete_level(level_id: int, admin=Depends(require_admin)):
    db.delete_chem_level(level_id)
    return {"success": True}


# --------------------------------------------------------------------------
#  Moddalar
# --------------------------------------------------------------------------

@router.get("/levels/{level_id}/substances")
def admin_list_substances(level_id: int, admin=Depends(require_admin)):
    return {"substances": db.get_chem_substances(level_id)}


@router.post("/levels/{level_id}/substances")
def admin_create_substance(level_id: int, data: dict = Body(...),
                           admin=Depends(require_admin)):
    formula = (data.get("formula") or "").strip()
    name = (data.get("name") or "").strip()
    if not formula or not name:
        raise HTTPException(status_code=400, detail="Formula va nom majburiy")
    if not db.get_chem_level(level_id):
        raise HTTPException(status_code=404, detail="Level topilmadi")

    order = data.get("sort_order")
    if order in (None, ""):
        existing = db.get_chem_substances(level_id)
        order = (max([s["sort_order"] for s in existing]) + 1) if existing else 1

    sid = db.create_chem_substance(
        level_id, formula, name,
        historic_name=_clean(data.get("historic_name")),
        color_pure=_clean(data.get("color_pure")),
        color_solution=_clean(data.get("color_solution")),
        color_precipitate=_clean(data.get("color_precipitate")),
        reactions=_clean(data.get("reactions")),
        usage_text=_clean(data.get("usage_text")),
        sort_order=order,
    )
    return {"success": True, "id": sid}


@router.put("/substances/{substance_id}")
def admin_update_substance(substance_id: int, data: dict = Body(...),
                           admin=Depends(require_admin)):
    if not db.get_chem_substance(substance_id):
        raise HTTPException(status_code=404, detail="Modda topilmadi")
    clean = {k: _clean(v) for k, v in data.items()}
    db.update_chem_substance(substance_id, **clean)
    return {"success": True}


@router.delete("/substances/{substance_id}")
def admin_delete_substance(substance_id: int, admin=Depends(require_admin)):
    db.delete_chem_substance(substance_id)
    return {"success": True}


def _clean(v):
    """Bo'sh yoki "yo'q" ma'nosidagi qiymatlarni NULL ga aylantiradi.

    Shunda savol generatori "javobi yo'q" savol yasamaydi — bu muhim,
    chunki baza bosqichma-bosqich to'ldiriladi.
    """
    if v is None:
        return None
    s = str(v).strip()
    if not s or s in ("-", "—", "–") or s.lower() in ("yo'q", "yoq", "none"):
        return None
    return s


# --------------------------------------------------------------------------
#  Ommaviy yuklash
# --------------------------------------------------------------------------

@router.post("/levels/{level_id}/bulk")
def admin_bulk_substances(level_id: int, data: dict = Body(...),
                          admin=Depends(require_admin)):
    """Matnni satrma-satr o'qib, moddalarni bir yo'la qo'shadi.

    Ajratgich sifatida `|` ham, tabulyatsiya ham qabul qilinadi — shunda
    Excel/Word jadvalidan nusxa ko'chirib qo'yish ham ishlaydi.

    `replace=true` bo'lsa levelning eski moddalari o'chiriladi (qayta
    yuklash uchun). Aks holda ustiga qo'shiladi.
    """
    if not db.get_chem_level(level_id):
        raise HTTPException(status_code=404, detail="Level topilmadi")

    text = data.get("text") or ""
    if not text.strip():
        raise HTTPException(status_code=400, detail="Matn bo'sh")

    if data.get("replace"):
        for s in db.get_chem_substances(level_id):
            db.delete_chem_substance(s["id"])

    existing = db.get_chem_substances(level_id)
    order = (max([s["sort_order"] for s in existing]) + 1) if existing else 1

    added, skipped = 0, []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        parts = [p.strip() for p in (line.split("|") if "|" in line else line.split("\t"))]
        parts = [p for p in parts]
        if len(parts) < 2 or not parts[0] or not parts[1]:
            skipped.append({"line": line_no, "text": raw[:80],
                            "reason": "formula yoki nom yo'q"})
            continue

        db.create_chem_substance(
            level_id, parts[0], parts[1],
            historic_name=_clean(parts[2] if len(parts) > 2 else None),
            color_pure=_clean(parts[3] if len(parts) > 3 else None),
            color_solution=_clean(parts[4] if len(parts) > 4 else None),
            color_precipitate=_clean(parts[5] if len(parts) > 5 else None),
            reactions=_clean(parts[6] if len(parts) > 6 else None),
            usage_text=_clean(parts[7] if len(parts) > 7 else None),
            sort_order=order,
        )
        order += 1
        added += 1

    return {"success": True, "added": added, "skipped": skipped,
            "total_now": len(db.get_chem_substances(level_id))}
