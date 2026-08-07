# routers/admin_bio.py
# ==========================================================================
#  BIOLOGIYA O'YINI — admin boshqaruvi
# ==========================================================================
# O'qituvchi uch xil ma'lumot kiritadi, savollar avtomatik yasaladi:
#
#   1) TERMIN      — nomi, ta'rifi, vazifasi, guruhi, ipuchalari
#   2) KETMA-KETLIK — jarayon nomi + bosqichlari (to'g'ri tartibda)
#   3) RASM        — surat + undagi nuqtalar (nomi va joyi)
#
# Levelda qaysi ma'lumot bo'lsa, o'quvchida SHU o'yinlar paydo bo'ladi.

from fastapi import APIRouter, Depends, HTTPException, Body

from routers.deps import require_admin
import database as db
from bio_seed_data import seed_levels_for as bio_seed_for, seed_summary as bio_seed_summary

router = APIRouter(prefix="/api/admin/bio", tags=["admin-bio"])


def _clean(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s or s in ("-", "—", "–") or s.lower() in ("yo'q", "yoq", "none"):
        return None
    return s


# --------------------------------------------------------------------------
#  Mavzular
# --------------------------------------------------------------------------

@router.get("/topics")
def admin_list_topics(admin=Depends(require_admin)):
    topics = db.get_bio_topics()
    for t in topics:
        levels = db.get_bio_levels(t["id"], only_active=False)
        t["level_count"] = len(levels)
        t["term_count"] = sum(l["term_count"] for l in levels)
        t["sequence_count"] = sum(l["sequence_count"] for l in levels)
        t["image_count"] = sum(l["image_count"] for l in levels)
    return {"topics": topics}


@router.put("/topics/{topic_id}")
def admin_update_topic(topic_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    if not db.get_bio_topic(topic_id):
        raise HTTPException(status_code=404, detail="Mavzu topilmadi")
    db.update_bio_topic(topic_id, **data)
    return {"success": True}


@router.post("/topics")
def admin_create_topic(data: dict = Body(...), admin=Depends(require_admin)):
    key = (data.get("key") or "").strip()
    title = (data.get("title") or "").strip()
    if not key or not title:
        raise HTTPException(status_code=400, detail="Kalit va nom majburiy")
    if any(t["key"] == key for t in db.get_bio_topics()):
        raise HTTPException(status_code=400, detail="Bu kalit allaqachon mavjud")
    tid = db.create_bio_topic(key, title, (data.get("subtitle") or "").strip(),
                              (data.get("icon") or "🧬").strip(),
                              data.get("is_ready", 0), data.get("sort_order", 0))
    return {"success": True, "id": tid}


@router.delete("/topics/{topic_id}")
def admin_delete_topic(topic_id: int, admin=Depends(require_admin)):
    db.delete_bio_topic(topic_id)
    return {"success": True}


# --------------------------------------------------------------------------
#  Levellar
# --------------------------------------------------------------------------

@router.get("/topics/{topic_id}/levels")
def admin_list_levels(topic_id: int, admin=Depends(require_admin)):
    levels = db.get_bio_levels(topic_id, only_active=False)
    for l in levels:
        # O'qituvchi levelda qaysi o'yinlar ochilishini darhol ko'rsin.
        l["stages"] = [db.BIO_STAGE_TITLES[k] for k in db.bio_available_stages(l)]
    return {"levels": levels}


@router.post("/topics/{topic_id}/levels")
def admin_create_level(topic_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    title = (data.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Level nomi majburiy")
    if not db.get_bio_topic(topic_id):
        raise HTTPException(status_code=404, detail="Mavzu topilmadi")
    existing = db.get_bio_levels(topic_id, only_active=False)
    order = data.get("sort_order")
    if order in (None, ""):
        order = (max([l["sort_order"] for l in existing]) + 1) if existing else 1
    return {"success": True, "id": db.create_bio_level(topic_id, title, order)}


@router.put("/levels/{level_id}")
def admin_update_level(level_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    if not db.get_bio_level(level_id):
        raise HTTPException(status_code=404, detail="Level topilmadi")
    db.update_bio_level(level_id, **data)
    return {"success": True}


@router.delete("/levels/{level_id}")
def admin_delete_level(level_id: int, admin=Depends(require_admin)):
    db.delete_bio_level(level_id)
    return {"success": True}


# --------------------------------------------------------------------------
#  Terminlar
# --------------------------------------------------------------------------

@router.get("/levels/{level_id}/terms")
def admin_list_terms(level_id: int, admin=Depends(require_admin)):
    return {"terms": db.get_bio_terms(level_id)}


@router.post("/levels/{level_id}/terms")
def admin_create_term(level_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    term = (data.get("term") or "").strip()
    if not term:
        raise HTTPException(status_code=400, detail="Termin nomi majburiy")
    if not db.get_bio_level(level_id):
        raise HTTPException(status_code=404, detail="Level topilmadi")
    existing = db.get_bio_terms(level_id)
    order = data.get("sort_order")
    if order in (None, ""):
        order = (max([t["sort_order"] for t in existing]) + 1) if existing else 1
    tid = db.create_bio_term(
        level_id, term,
        definition=_clean(data.get("definition")),
        function_text=_clean(data.get("function_text")),
        group_name=_clean(data.get("group_name")),
        clues=data.get("clues"),
        extra_fact=_clean(data.get("extra_fact")),
        image_url=_clean(data.get("image_url")),
        sort_order=order)
    return {"success": True, "id": tid}


@router.put("/terms/{term_id}")
def admin_update_term(term_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    if not db.get_bio_term(term_id):
        raise HTTPException(status_code=404, detail="Termin topilmadi")
    clean = {}
    for k, v in data.items():
        clean[k] = v if k == "clues" else _clean(v)
    db.update_bio_term(term_id, **clean)
    return {"success": True}


@router.delete("/terms/{term_id}")
def admin_delete_term(term_id: int, admin=Depends(require_admin)):
    db.delete_bio_term(term_id)
    return {"success": True}


@router.post("/levels/{level_id}/terms/bulk")
def admin_bulk_terms(level_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    """Terminlarni satrma-satr ommaviy yuklash.

        termin | ta'rifi | vazifasi | guruhi | qiziqarli fakt

    Ipuchalar ("Kim men?" uchun) bu yerda kiritilmaydi — ular ko'p qatorli
    bo'lgani uchun alohida formadan qo'shiladi.
    """
    if not db.get_bio_level(level_id):
        raise HTTPException(status_code=404, detail="Level topilmadi")
    text = data.get("text") or ""
    if not text.strip():
        raise HTTPException(status_code=400, detail="Matn bo'sh")

    if data.get("replace"):
        for t in db.get_bio_terms(level_id):
            db.delete_bio_term(t["id"])

    existing = db.get_bio_terms(level_id)
    order = (max([t["sort_order"] for t in existing]) + 1) if existing else 1

    added, skipped = 0, []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in (line.split("|") if "|" in line else line.split("\t"))]
        if not parts or not parts[0]:
            skipped.append({"line": line_no, "text": raw[:80], "reason": "termin nomi yo'q"})
            continue
        db.create_bio_term(
            level_id, parts[0],
            definition=_clean(parts[1] if len(parts) > 1 else None),
            function_text=_clean(parts[2] if len(parts) > 2 else None),
            group_name=_clean(parts[3] if len(parts) > 3 else None),
            extra_fact=_clean(parts[4] if len(parts) > 4 else None),
            sort_order=order)
        order += 1
        added += 1

    return {"success": True, "added": added, "skipped": skipped,
            "total_now": len(db.get_bio_terms(level_id))}


# --------------------------------------------------------------------------
#  Ketma-ketliklar
# --------------------------------------------------------------------------

@router.get("/levels/{level_id}/sequences")
def admin_list_sequences(level_id: int, admin=Depends(require_admin)):
    return {"sequences": db.get_bio_sequences(level_id)}


@router.post("/levels/{level_id}/sequences")
def admin_create_sequence(level_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    title = (data.get("title") or "").strip()
    steps = data.get("steps")
    if not title:
        raise HTTPException(status_code=400, detail="Jarayon nomi majburiy")
    if not db.get_bio_level(level_id):
        raise HTTPException(status_code=404, detail="Level topilmadi")

    parsed = [s.strip() for s in str(steps or "").splitlines() if s.strip()] \
        if isinstance(steps, str) else [str(s).strip() for s in (steps or []) if str(s).strip()]
    if len(parsed) < 2:
        raise HTTPException(status_code=400,
                            detail="Kamida 2 ta bosqich kiriting (har biri alohida qatorda)")

    existing = db.get_bio_sequences(level_id)
    order = (max([s["sort_order"] for s in existing]) + 1) if existing else 1
    sid = db.create_bio_sequence(level_id, title, parsed,
                                 description=_clean(data.get("description")),
                                 sort_order=order)
    return {"success": True, "id": sid, "step_count": len(parsed)}


@router.put("/sequences/{sequence_id}")
def admin_update_sequence(sequence_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    db.update_bio_sequence(sequence_id, **data)
    return {"success": True}


@router.delete("/sequences/{sequence_id}")
def admin_delete_sequence(sequence_id: int, admin=Depends(require_admin)):
    db.delete_bio_sequence(sequence_id)
    return {"success": True}


# --------------------------------------------------------------------------
#  Rasm topshiriqlari
# --------------------------------------------------------------------------

@router.get("/levels/{level_id}/images")
def admin_list_images(level_id: int, admin=Depends(require_admin)):
    return {"tasks": db.get_bio_image_tasks(level_id)}


@router.post("/levels/{level_id}/images")
def admin_create_image(level_id: int, data: dict = Body(...), admin=Depends(require_admin)):
    """Rasm topshirig'i.

    `labels` — [{"name": "Yadro", "x": 42, "y": 55}, ...]
    x, y — rasmning FOIZ koordinatalari (0-100). Foiz ishlatilishining
    sababi: rasm telefonda ham, kompyuterda ham turli o'lchamda
    ko'rsatiladi, foiz esa har ikkalasida ham joyida qoladi.
    """
    title = (data.get("title") or "").strip()
    image_url = (data.get("image_url") or "").strip()
    labels = data.get("labels") or []
    if not title or not image_url:
        raise HTTPException(status_code=400, detail="Sarlavha va rasm majburiy")
    if not db.get_bio_level(level_id):
        raise HTTPException(status_code=404, detail="Level topilmadi")

    clean_labels = []
    for l in labels:
        name = (l.get("name") or "").strip() if isinstance(l, dict) else ""
        if not name:
            continue
        clean_labels.append({
            "name": name,
            "x": max(0, min(100, db.safe_int(l.get("x"), 50))),
            "y": max(0, min(100, db.safe_int(l.get("y"), 50))),
        })
    if not clean_labels:
        raise HTTPException(status_code=400, detail="Kamida bitta nuqta belgilang")

    existing = db.get_bio_image_tasks(level_id)
    order = (max([t["sort_order"] for t in existing]) + 1) if existing else 1
    tid = db.create_bio_image_task(level_id, title, image_url, clean_labels, order)
    return {"success": True, "id": tid, "label_count": len(clean_labels)}


@router.delete("/images/{task_id}")
def admin_delete_image(task_id: int, admin=Depends(require_admin)):
    db.delete_bio_image_task(task_id)
    return {"success": True}


# --------------------------------------------------------------------------
#  Namuna baza
# --------------------------------------------------------------------------

@router.get("/seed/info")
def admin_bio_seed_info(topic_key: str = "hujayra", admin=Depends(require_admin)):
    return bio_seed_summary(topic_key)


@router.post("/topics/{topic_id}/seed")
def admin_bio_seed(topic_id: int, admin=Depends(require_admin)):
    """Mavzuga tayyor namuna levellarni qo'shadi (takrorlanmaydi)."""
    topic = db.get_bio_topic(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Mavzu topilmadi")

    levels = bio_seed_for(topic["key"])
    if not levels:
        raise HTTPException(
            status_code=400,
            detail="Bu mavzu uchun namuna hali tayyorlanmagan — "
                   "terminlarni ommaviy yuklash orqali kiriting.")

    existing = {l["title"].strip().lower()
                for l in db.get_bio_levels(topic_id, only_active=False)}
    order = len(existing) + 1
    added_levels = added_terms = added_sequences = 0
    skipped = []

    for spec in levels:
        if spec["title"].strip().lower() in existing:
            skipped.append(spec["title"])
            continue
        level_id = db.create_bio_level(topic_id, spec["title"], order)
        order += 1
        added_levels += 1

        for i, row in enumerate(spec.get("terms", []), start=1):
            term, definition, function_text, group_name, clues, extra = row
            db.create_bio_term(level_id, term, definition=definition,
                               function_text=function_text, group_name=group_name,
                               clues=clues, extra_fact=extra, sort_order=i)
            added_terms += 1

        for i, seq in enumerate(spec.get("sequences", []), start=1):
            db.create_bio_sequence(level_id, seq["title"], seq["steps"],
                                   description=seq.get("description"), sort_order=i)
            added_sequences += 1

    return {"success": True, "added_levels": added_levels,
            "added_terms": added_terms, "added_sequences": added_sequences,
            "skipped_levels": skipped}
