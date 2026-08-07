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
        msg = str(e)
        # "user not found" — bu XATO EMAS: odam shunchaki guruhda yo'q.
        if "not found" in msg.lower() or "PARTICIPANT_ID_INVALID" in msg:
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
        db.save_membership(telegram_id, g["id"], is_member, status)
        # Guruh sozlamasidagi xatoni saqlaymiz — admin panelda ko'rinadi
        # ("bot admin emas" kabi muammoni o'qituvchi darhol bilib oladi).
        if error and error != g.get("last_error"):
            db.update_access_group(g["id"], last_error=error[:200])
        elif not error and g.get("last_error"):
            db.update_access_group(g["id"], last_error=None)

    return db.get_member_group_ids(telegram_id)


async def verify_group_setup(bot, chat_id: str):
    """Admin panel uchun: bot shu guruhda ADMINmi va guruh nomi nima?

    Sozlashdagi eng ko'p uchraydigan xatoni ("bot guruhga qo'shilmagan"
    yoki "admin qilinmagan") o'qituvchi darhol ko'rishi uchun.
    """
    result = {"ok": False, "title": None, "member_count": None,
              "bot_is_admin": False, "error": None}
    try:
        chat = await bot.get_chat(chat_id)
        result["title"] = getattr(chat, "title", None)
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
    except Exception as e:
        msg = str(e)
        if "chat not found" in msg.lower():
            result["error"] = ("Guruh topilmadi. chat_id to'g'ri ekanini va bot "
                               "guruhga qo'shilganini tekshiring.")
        else:
            result["error"] = msg[:300]
    return result


# Kirish holatini hisoblash DB qatlamida (database.access_state_for) —
# u yerda ham kerak bo'lgani uchun. Bu yerda faqat qulay nom beramiz.
access_state = db.access_state_for
