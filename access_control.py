# access_control.py
# ==========================================================================
#  PULLIK GURUH A'ZOLIGINI TEKSHIRISH
# ==========================================================================
# G'OYA: o'quvchini qo'lda kursga biriktirish o'rniga, uning Telegram ID si
# o'qituvchining YOPIQ guruhida bor-yo'qligi avtomatik tekshiriladi.
#
# NEGA ALOHIDA MODUL: bu mantiq uch joyda kerak bo'ladi (kurslar, testlar,
# fon vazifasi). Har birida takrorlamaslik uchun bitta joyga yig'ilgan.
#
# TELEGRAM TALABI: bot guruhda ADMIN bo'lishi shart. Aks holda
# get_chat_member() "not enough rights" xatosini qaytaradi. Admin panelda
# shu holatni tekshiradigan tugma bor.

import logging

import database as db

logger = logging.getLogger(__name__)


def _migrated_chat_id(exc):
    """Guruh SUPERGURUHGA aylangan bo'lsa, Telegram YANGI chat_id ni beradi.

    NEGA MUHIM: oddiy guruh (basic group) supergruhga aylanganda ID
    BUTUNLAY O'ZGARADI. Buni ushlamasak, o'qituvchi hech narsa qilmagan
    holda kirish tizimi to'satdan ishlamay qolardi va hamma o'quvchi
    qulflanib qolardi.
    """
    return getattr(exc, "migrate_to_chat_id", None)


async def check_membership(bot, chat_id: str, telegram_id: int):
    """Bitta guruhda bitta odamni tekshiradi.

    Qaytaradi: (a'zomi, holat_matni, xato_matni)

    Telegram javob bermasa yoki bot admin bo'lmasa — (False, None, xato).
    Bunday holatda kirish BERILMAYDI, chunki "ishonchsiz holatda yopiq"
    tamoyili xavfsizroq: aks holda bitta tarmoq uzilishi butun pullik
    kontentni ochib yuborardi.
    """
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=telegram_id)
        status = getattr(member, "status", None)
        status = getattr(status, "value", status)   # aiogram enum -> matn
        return (status in db.TELEGRAM_MEMBER_STATUSES), status, None
    except Exception as e:
        new_id = _migrated_chat_id(e)
        if new_id:
            # Guruh supergruhga aylangan — yangi ID bilan qayta urinamiz.
            logger.info(f"[KIRISH] Guruh supergruhga aylandi: {chat_id} -> {new_id}")
            return await check_membership(bot, str(new_id), telegram_id)

        msg = str(e)
        low = msg.lower()
        # "user not found" — bu XATO EMAS: odam shunchaki guruhda yo'q.
        if "user not found" in low or "PARTICIPANT_ID_INVALID" in msg:
            return False, "left", None
        logger.warning(f"[KIRISH] A'zolikni tekshirib bo'lmadi (chat={chat_id}, "
                       f"user={telegram_id}): {msg}")
        return False, None, msg


async def refresh_user_memberships(bot, telegram_id: int, force: bool = False):
    """O'quvchining barcha guruhlardagi a'zoligini yangilaydi.

    `force=False` bo'lsa faqat KESHI ESKIRGAN guruhlar tekshiriladi —
    shuning uchun har dars ochilganda Telegram'ga so'rov yog'ilmaydi.
    """
    groups = (db.get_access_groups(only_active=True) if force
              else db.get_stale_membership_groups(telegram_id))
    if not groups:
        return db.get_member_group_ids(telegram_id)

    for g in groups:
        is_member, status, error = await check_membership(bot, g["chat_id"], telegram_id)

        # Guruh supergruhga aylangan bo'lsa — yangi ID ni bazaga yozib
        # qo'yamiz, keyingi safar to'g'ridan-to'g'ri ishlatiladi.
        new_id = await _detect_migration(bot, g["chat_id"])
        if new_id and str(new_id) != str(g["chat_id"]):
            db.update_access_group(g["id"], chat_id=str(new_id))
            logger.info(f"[KIRISH] Guruh ID yangilandi: {g['chat_id']} -> {new_id}")

        db.save_membership(telegram_id, g["id"], is_member, status)
        # Guruh sozlamasidagi xatoni saqlaymiz — admin panelda ko'rinadi
        # ("bot admin emas" kabi muammoni o'qituvchi darhol bilib oladi).
        if error and error != g.get("last_error"):
            db.update_access_group(g["id"], last_error=error[:200])
        elif not error and g.get("last_error"):
            db.update_access_group(g["id"], last_error=None)

    return db.get_member_group_ids(telegram_id)


async def _detect_migration(bot, chat_id: str):
    """Guruh supergruhga aylanganini aniqlaydi (aylanmagan bo'lsa None)."""
    try:
        await bot.get_chat(chat_id)
        return None
    except Exception as e:
        return _migrated_chat_id(e)


# Guruh sozlamasi BUZUQ ekanini ko'rsatuvchi xatolar. Bunday holatda
# o'quvchini qulflab qo'yish NOTO'G'RI — bu o'qituvchining sozlash xatosi,
# o'quvchining aybi emas. Shuning uchun buzuq guruh KIRISHNI CHEKLAMAYDI,
# faqat admin panelda katta ogohlantirish chiqadi.
BROKEN_SETUP_MARKERS = (
    "chat not found",
    "bot is not a member",
    "not enough rights",
    "chat_id is empty",
    "bot was kicked",
    "forbidden",
)


def is_broken_setup(error_text: str) -> bool:
    low = (error_text or "").lower()
    return any(m in low for m in BROKEN_SETUP_MARKERS)


async def verify_group_setup(bot, chat_id: str):
    """Admin panel uchun: bot shu guruhda ADMINmi va guruh nomi nima?

    Sozlashdagi eng ko'p uchraydigan xatoni ("bot guruhga qo'shilmagan"
    yoki "admin qilinmagan") o'qituvchi darhol ko'rishi uchun.
    """
    result = {"ok": False, "title": None, "member_count": None,
              "bot_is_admin": False, "error": None,
              "chat_type": None, "migrated_to": None}
    try:
        try:
            chat = await bot.get_chat(chat_id)
        except Exception as e:
            new_id = _migrated_chat_id(e)
            if not new_id:
                raise
            # Supergruhga aylangan — yangi ID bilan davom etamiz va
            # chaqiruvchiga uni qaytaramiz (bazada yangilanadi).
            result["migrated_to"] = str(new_id)
            chat_id = str(new_id)
            chat = await bot.get_chat(chat_id)

        result["title"] = getattr(chat, "title", None)
        ctype = getattr(chat, "type", None)
        result["chat_type"] = getattr(ctype, "value", ctype)
        try:
            result["member_count"] = await bot.get_chat_member_count(chat_id)
        except Exception:
            pass

        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id=chat_id, user_id=me.id)
        status = getattr(member, "status", None)
        status = getattr(status, "value", status)
        result["bot_is_admin"] = status in ("administrator", "creator")
        result["ok"] = result["bot_is_admin"]
        if not result["bot_is_admin"]:
            result["error"] = ("Bot bu guruhda admin emas. Guruh sozlamalari -> "
                               "Administratorlar -> botni admin qiling.")
        elif result["chat_type"] == "group":
            # Oddiy guruh ishlaydi, lekin supergruhga aylanganda ID o'zgaradi.
            # Biz buni avtomatik ushlaymiz, shuning uchun bu xato emas — izoh.
            result["note"] = ("Bu ODDIY guruh. U supergruhga aylansa ID o'zgaradi — "
                              "tizim buni o'zi sezib yangilaydi, siz hech narsa "
                              "qilishingiz shart emas.")
    except Exception as e:
        msg = str(e)
        if "chat not found" in msg.lower():
            result["error"] = ("Guruh topilmadi. chat_id NOTO'G'RI yoki bot guruhga "
                               "qo'shilmagan. Diqqat: bunday holatda o'quvchilar "
                               "QULFLANMAYDI — kirish eski tartibda ishlayveradi.")
        else:
            result["error"] = msg[:300]
    return result


# Kirish holatini hisoblash DB qatlamida (database.access_state_for) —
# u yerda ham kerak bo'lgani uchun. Bu yerda faqat qulay nom beramiz.
access_state = db.access_state_for
