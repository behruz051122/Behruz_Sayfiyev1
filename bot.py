# bot.py
# Telegram bot: referal tizimi, kanalga majburiy obuna, Mini App

import asyncio
import logging

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, MenuButtonWebApp
)

from config import BOT_TOKEN, WEBAPP_URL, CHANNEL_USERNAME, CHANNEL_URL, BOT_USERNAME
from database import (
    init_db, get_or_create_user, add_sample_courses,
    create_pending_referral, confirm_referral, set_user_subscribed,
    get_confirmed_referral_count, get_enrollments_needing_reminder, mark_reminder_sent,
    get_battles_needing_notification, mark_battle_notified,
    resolve_stale_chem_battles, get_unnotified_chem_battles, mark_chem_battle_notified,
    get_startable_chem_tournaments, start_chem_tournament, get_chem_tournament,
    get_chem_substances_by_category, TOURNAMENT_QUESTION_COUNT,
    get_access_groups, get_users_needing_membership_refresh,
)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


async def is_user_subscribed(telegram_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=telegram_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logging.warning(f"Obuna tekshirishda xatolik: {e}")
        return False


def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Kurslarni ko'rish", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])


async def setup_menu_button():
    """Telegram'ning har bir chat oynasida (xabar yozish maydoni yonida)
    doimiy ko'rinadigan "Menu" tugmasini o'rnatadi — shu orqali foydalanuvchi
    /start bosmasdan, istalgan vaqtda bevosita Mini App'ni ocha oladi.
    Bir marta o'rnatilgach, Telegram tomonda saqlanib qoladi (har safar
    bot ishga tushganda qayta chaqirish xavfsiz — o'zgarish bo'lmasa,
    hech narsa buzilmaydi)."""
    try:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="📚 Kurslar",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        )
        logging.info("Menu tugmasi (persistent Mini App kirish) muvaffaqiyatli o'rnatildi.")
    except Exception as e:
        logging.warning(f"Menu tugmasini o'rnatishda xatolik: {e}")


def subscribe_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=CHANNEL_URL)],
        [InlineKeyboardButton(text="✅ Men obuna bo'ldim", callback_data="check_sub")]
    ])


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    telegram_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username

    # Referal parametrini o'qiymiz: /start ref_123456789
    referrer_id = None
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1 and parts[1].startswith("ref_"):
        try:
            referrer_id = int(parts[1].replace("ref_", ""))
        except ValueError:
            referrer_id = None

    user = get_or_create_user(telegram_id, first_name, username, referred_by=referrer_id)

    # Agar bu foydalanuvchi referal orqali kelgan bo'lsa, pending referal yozamiz
    if referrer_id and referrer_id != telegram_id:
        create_pending_referral(referrer_id, telegram_id)

    subscribed = await is_user_subscribed(telegram_id)
    if subscribed:
        set_user_subscribed(telegram_id, True)
        ref_id = confirm_referral(telegram_id)
        if ref_id:
            try:
                count = get_confirmed_referral_count(ref_id)
                await bot.send_message(
                    ref_id,
                    f"🎉 Sizning taklifingiz orqali yangi foydalanuvchi qo'shildi!\n"
                    f"Hozirgi tasdiqlangan takliflar soni: {count} ta.\n"
                    f"Platformaga o'tib, qaysi darslar ochilganini tekshiring."
                )
            except Exception:
                pass

        await message.answer(
            f"👋 Salom, {user['first_name']}!\n\n"
            f"Sizga {user['points']} ball va {user['coins']} coin taqdim etildi.\n"
            f"Kurslarni ko'rish uchun quyidagi tugmani bosing "
            f"(yoki xabar yozish maydoni yonidagi \"📚 Kurslar\" menyu tugmasidan istalgan vaqtda kirishingiz mumkin):",
            reply_markup=main_menu_keyboard()
        )
    else:
        await message.answer(
            f"👋 Salom, {user['first_name']}!\n\n"
            f"Ba'zi darslar faqat kanalimizga obuna bo'lgan foydalanuvchilarga ochiq.\n"
            f"Davom etish uchun avval kanalga obuna bo'ling:",
            reply_markup=subscribe_keyboard()
        )


@dp.callback_query(F.data == "check_sub")
async def check_sub_handler(callback: CallbackQuery):
    telegram_id = callback.from_user.id
    subscribed = await is_user_subscribed(telegram_id)

    if subscribed:
        set_user_subscribed(telegram_id, True)
        ref_id = confirm_referral(telegram_id)
        if ref_id:
            try:
                count = get_confirmed_referral_count(ref_id)
                await bot.send_message(
                    ref_id,
                    f"🎉 Sizning taklifingiz orqali yangi foydalanuvchi qo'shildi!\n"
                    f"Hozirgi tasdiqlangan takliflar soni: {count} ta."
                )
            except Exception:
                pass

        await callback.message.edit_text("✅ Rahmat! Obuna tasdiqlandi.")
        await callback.message.answer(
            "Kurslarni ko'rish uchun tugmani bosing:",
            reply_markup=main_menu_keyboard()
        )
    else:
        await callback.answer("❌ Siz hali obuna bo'lmadingiz. Avval kanalga qo'shiling.", show_alert=True)


REMINDER_CHECK_INTERVAL_SECONDS = 6 * 60 * 60  # har 6 soatda tekshiradi


async def send_expiry_reminders_loop():
    """
    Pullik kursga obunasi tez orada tugaydigan (yoki yaqinda tugagan)
    foydalanuvchilarga Telegram orqali avtomatik eslatma yuboradi. Har bir
    obunaga faqat BIR MARTA eslatma yuboriladi (bazadagi 'reminder_sent_at'
    ustuni orqali nazorat qilinadi) — spam bo'lmaydi.
    """
    while True:
        try:
            pending = get_enrollments_needing_reminder()
            for e in pending:
                try:
                    await bot.send_message(
                        e["telegram_id"],
                        f"⏳ Diqqat!\n\n\"{e['course_title']}\" kursiga obunangiz muddati "
                        f"tez orada tugaydi (yoki tugagan).\n\n"
                        f"Darslarga uzluksiz kirishni davom ettirish uchun obunangizni "
                        f"yangilash bo'yicha admin bilan bog'laning."
                    )
                    mark_reminder_sent(e["id"])
                    logging.info(f"Obuna eslatmasi yuborildi: telegram_id={e['telegram_id']}, kurs={e['course_title']}")
                except Exception as send_error:
                    logging.warning(f"Eslatma yuborilmadi (telegram_id={e['telegram_id']}): {send_error}")
        except Exception as e:
            logging.error(f"Eslatma tekshiruvi siklida xato: {e}")

        await asyncio.sleep(REMINDER_CHECK_INTERVAL_SECONDS)


HOMEWORK_REMINDER_INTERVAL_SECONDS = 6 * 3600  # kuniga ~4 marta tekshiriladi


async def send_homework_reminders_loop():
    """
    Vazifani belgilangan muddatda topshirmagan o'quvchilarga avtomatik
    Telegram eslatmasi yuboradi.

    SPAMNING OLDINI OLISH: bir xil o'quvchiga bir xil paragraf bo'yicha
    eslatma 48 soatda bir martadan ko'p yuborilmaydi (yuborilgan vaqt
    homework_submissions.reminder_sent_at ustunida saqlanadi).
    """
    import database as db

    while True:
        try:
            pending = db.get_homework_students_needing_reminder(min_hours_between=48)
            for s in pending:
                try:
                    await bot.send_message(
                        s["telegram_id"],
                        f"⚠️ <b>Vazifa eslatmasi</b>\n\n"
                        f"Hurmatli {s.get('first_name') or 'oʻquvchi'}, "
                        f"<b>{s['subject_title']}</b> boʻlimi boʻyicha "
                        f"<b>{s['waiting_paragraph']}-paragraf</b> vazifasi hali topshirilmagan "
                        f"({s['days_idle']} kundan beri harakat yoʻq).\n\n"
                        f"Iltimos, ishlangan masalalar yechimini rasmga tushirib, ilovaga yuklang.",
                        parse_mode="HTML",
                    )
                    db.mark_homework_reminder_sent(
                        s["telegram_id"], s["subject_id"], s["waiting_paragraph"]
                    )
                    logging.info(f"Vazifa eslatmasi yuborildi: telegram_id={s['telegram_id']}, "
                                 f"fan={s['subject_title']}, paragraf={s['waiting_paragraph']}")
                except Exception as send_error:
                    logging.warning(f"Vazifa eslatmasi yuborilmadi "
                                    f"(telegram_id={s['telegram_id']}): {send_error}")
        except Exception as e:
            logging.error(f"Vazifa eslatmalari siklida xato: {e}")

        await asyncio.sleep(HOMEWORK_REMINDER_INTERVAL_SECONDS)


BATTLE_NOTIFY_CHECK_INTERVAL_SECONDS = 15  # o'yin natijasi tezroq yetib borishi kerak


def _battle_result_text(my_score, opp_score, opp_name, subject, elo_before, elo_after, is_winner_none, i_won):
    if is_winner_none:
        headline = "🤝 Durrang!"
    elif i_won:
        headline = "🏆 G'alaba qozondingiz!"
    else:
        headline = "😔 Mag'lubiyat"
    elo_diff = elo_after - elo_before
    sign = "+" if elo_diff > 0 else ""
    opponent_display = opp_name or "Noma'lum"
    return (
        f"⚔️ Jang yakunlandi!\n\n"
        f"{headline}\n"
        f"Fan: {subject}\n"
        f"Raqib: {opponent_display}\n"
        f"Hisob: {my_score} : {opp_score}\n"
        f"ELO: {elo_before} → {elo_after} ({sign}{elo_diff})\n\n"
        f"Yangi jang uchun Mini App'dagi \"O'yinlar\" bo'limiga o'ting."
    )


async def send_battle_result_notifications_loop():
    """
    Battle (1x1 o'yin) ikkala o'yinchi ham javob berib, YAKUNLANGANDA,
    natija Mini App ichida "Mening janglarim" bo'limida ko'rinadi — lekin
    o'yinchi o'sha payt ilovani ochib o'tirmagan bo'lishi mumkin (chunki
    bu ASINXRON o'yin: raqib keyinroq qo'shiladi). Shu sababli natija
    tayyor bo'lishi bilan ikkala o'yinchiga ham Telegram orqali DARHOL
    xabar yuboramiz — xuddi eslatmalar sikli (send_expiry_reminders_loop)
    kabi, lekin ancha tezroq tekshiradigan (15 soniyada bir) alohida sikl.
    """
    while True:
        try:
            battles = get_battles_needing_notification()
            for b in battles:
                try:
                    p1, p2 = b["player1_telegram_id"], b["player2_telegram_id"]
                    u1 = get_or_create_user(p1, "O'quvchi")
                    u2 = get_or_create_user(p2, "O'quvchi")
                    winner = b["winner_telegram_id"]

                    text1 = _battle_result_text(
                        b["player1_score"], b["player2_score"], u2.get("first_name"), b["subject"],
                        b["player1_elo_before"], b["player1_elo_after"],
                        winner is None, winner == p1
                    )
                    text2 = _battle_result_text(
                        b["player2_score"], b["player1_score"], u1.get("first_name"), b["subject"],
                        b["player2_elo_before"], b["player2_elo_after"],
                        winner is None, winner == p2
                    )
                    try:
                        await bot.send_message(p1, text1)
                    except Exception as send_error:
                        logging.warning(f"Battle xabari yuborilmadi (telegram_id={p1}): {send_error}")
                    try:
                        await bot.send_message(p2, text2)
                    except Exception as send_error:
                        logging.warning(f"Battle xabari yuborilmadi (telegram_id={p2}): {send_error}")

                    mark_battle_notified(b["id"])
                except Exception as inner_error:
                    logging.warning(f"Battle xabarini tayyorlashda xato (battle_id={b.get('id')}): {inner_error}")
        except Exception as e:
            logging.error(f"Battle xabarlari siklida xato: {e}")

        await asyncio.sleep(BATTLE_NOTIFY_CHECK_INTERVAL_SECONDS)


async def start_polling_background():
    """
    server.py shu funksiyani chaqiradi — Mini App backendi bilan bot BITTA
    Railway xizmatida (service), bitta Python jarayonida, bitta ma'lumotlar
    bazasi ulanishlari puli bilan ishlaydi. Shu sababli botni alohida
    Railway service qilib joylashtirish SHART EMAS (va tavsiya etilmaydi —
    aks holda ikkita alohida, bir-biridan bexabar ma'lumotlar bazasi hosil
    bo'lib qoladi).

    Tarmoqda vaqtincha uzilish yoki Telegram tomonidan xatolik yuz bersa,
    jarayon butunlay to'xtab qolmasligi uchun avtomatik qayta urinadi.
    """
    while True:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            await setup_menu_button()
            logging.info("Telegram bot polling boshlandi (server bilan bitta jarayonda).")
            await dp.start_polling(bot)
        except Exception as e:
            logging.error(f"Bot polling xatosi, 10 soniyadan keyin qayta urinamiz: {e}")
            await asyncio.sleep(10)


async def main():
    """Faqat bot.py ALOHIDA, mustaqil ishga tushirilganda ishlatiladi
    (masalan lokal kompyuteringizda `python bot.py` orqali sinash uchun).
    Railway'ga joylashtirilgan production muhitda bu funksiya chaqirilmaydi —
    u yerda server.py o'zi start_polling_background()ni ichkarida ishga
    tushiradi."""
    init_db()
    add_sample_courses()
    print("Bot ishga tushdi...")
    await start_polling_background()


if __name__ == "__main__":
    asyncio.run(main())


# ================================================================
# VAZIFA RASMLARINI TELEGRAMDA SAQLASH (server xotirasini tejash)
# ================================================================
#
# O'quvchilarning uy vazifasi suratlari serverda SAQLANMAYDI — bot ularni
# yopiq arxiv kanalga yuboradi va bazada faqat qisqa "file_id" qoladi.
# Bu Railway Volume'ni to'lib ketishdan saqlaydi (2 MB o'rniga ~80 bayt).

from aiogram.types import BufferedInputFile

# Telegram getFile natijasini qayta-qayta so'ramaslik uchun oddiy kesh:
# file_id -> (file_path, olingan_vaqt). file_path uzoq muddat o'zgarmaydi.
_tg_file_path_cache = {}
_TG_FILE_PATH_TTL_SECONDS = 30 * 60


def homework_archive_enabled() -> bool:
    from config import HOMEWORK_ARCHIVE_CHAT_ID
    return bool(HOMEWORK_ARCHIVE_CHAT_ID)


async def upload_homework_photo_to_archive(image_bytes: bytes, filename: str, caption: str = ""):
    """Rasmni arxiv kanalga yuboradi va (file_id, message_id) qaytaradi.

    Kanal sozlanmagan yoki yuborishda xato bo'lsa — None qaytaradi;
    chaqiruvchi kod bu holda rasmni diskka saqlaydi (tizim to'xtamaydi)."""
    from config import HOMEWORK_ARCHIVE_CHAT_ID
    if not HOMEWORK_ARCHIVE_CHAT_ID:
        return None
    try:
        msg = await bot.send_photo(
            chat_id=HOMEWORK_ARCHIVE_CHAT_ID,
            photo=BufferedInputFile(image_bytes, filename=filename or "vazifa.jpg"),
            caption=caption[:1000] if caption else None,
        )
        # Telegram bir nechta o'lchamni qaytaradi — eng kattasini olamiz.
        file_id = msg.photo[-1].file_id if msg.photo else None
        if not file_id:
            return None
        return {"file_id": file_id, "message_id": msg.message_id}
    except Exception as e:
        logging.warning(f"Vazifa rasmini arxivga yuborib bo'lmadi: {e}")
        return None


async def fetch_telegram_file(file_id: str):
    """file_id bo'yicha faylning baytlarini qaytaradi (ko'rsatish uchun)."""
    import time
    try:
        cached = _tg_file_path_cache.get(file_id)
        now = time.time()
        if cached and (now - cached[1]) < _TG_FILE_PATH_TTL_SECONDS:
            file_path = cached[0]
        else:
            tg_file = await bot.get_file(file_id)
            file_path = tg_file.file_path
            _tg_file_path_cache[file_id] = (file_path, now)

        buf = await bot.download_file(file_path)
        return buf.read()
    except Exception as e:
        logging.warning(f"Telegramdan faylni olib bo'lmadi (file_id={file_id[:20]}...): {e}")
        _tg_file_path_cache.pop(file_id, None)
        return None


async def delete_archive_message(message_id: int) -> bool:
    """Arxiv kanaldagi rasm xabarini o'chiradi (eski rasmlarni tozalashda)."""
    from config import HOMEWORK_ARCHIVE_CHAT_ID
    if not HOMEWORK_ARCHIVE_CHAT_ID or not message_id:
        return False
    try:
        await bot.delete_message(chat_id=HOMEWORK_ARCHIVE_CHAT_ID, message_id=int(message_id))
        return True
    except Exception as e:
        logging.info(f"Arxiv xabarini o'chirib bo'lmadi (message_id={message_id}): {e}")
        return False


HOMEWORK_CLEANUP_INTERVAL_SECONDS = 24 * 3600  # kuniga bir marta


async def cleanup_old_homework_photos(retention_days: int = None) -> dict:
    """Baholanganiga belgilangan kundan ko'p vaqt o'tgan vazifa RASMLARINI
    o'chiradi (diskdagi fayl + arxiv kanaldagi xabar).

    MUHIM: o'qituvchi qo'ygan BALL va IZOH hech qachon o'chirilmaydi —
    reyting va o'quvchi tarixi buzilmaydi. Faqat og'ir fayllar tozalanadi,
    shu tufayli server xotirasi doim bo'sh turadi."""
    import os
    import database as db
    from config import HOMEWORK_PHOTO_RETENTION_DAYS, UPLOADS_DIR

    days = retention_days if retention_days is not None else HOMEWORK_PHOTO_RETENTION_DAYS
    expired = db.get_expired_homework_photos(days)
    if not expired:
        return {"deleted": 0, "days": days}

    removed_ids = []
    for photo in expired:
        if photo.get("telegram_message_id"):
            await delete_archive_message(photo["telegram_message_id"])
        url = photo.get("photo_url")
        if url and url.startswith("/uploads/"):
            target = os.path.normpath(os.path.join(UPLOADS_DIR, url[len("/uploads/"):]))
            if target.startswith(os.path.normpath(UPLOADS_DIR)):
                try:
                    os.remove(target)
                except OSError:
                    pass
        removed_ids.append(photo["id"])

    db.delete_homework_photo_rows(removed_ids)
    logging.info(f"Eski vazifa rasmlari tozalandi: {len(removed_ids)} ta "
                 f"({days} kundan oshgan, ball va izohlar saqlanib qoldi)")
    return {"deleted": len(removed_ids), "days": days}


async def cleanup_old_homework_photos_loop():
    """Kuniga bir marta eski vazifa rasmlarini avtomatik tozalaydi."""
    while True:
        try:
            await cleanup_old_homework_photos()
        except Exception as e:
            logging.error(f"Vazifa rasmlarini tozalash siklida xato: {e}")
        await asyncio.sleep(HOMEWORK_CLEANUP_INTERVAL_SECONDS)


# ==========================================================================
#  KIMYO O'YINI — jangni yakunlash va natija haqida xabar
# ==========================================================================

CHEM_BATTLE_CHECK_INTERVAL_SECONDS = 20


def _chem_result_text(my_score, opp_score, opp_name, elo_before, elo_after,
                      is_draw, is_winner, is_bot):
    """Jang natijasi haqida Telegram xabari."""
    if is_draw:
        head = "🤝 <b>Durang!</b>"
    elif is_winner:
        head = "🏆 <b>G'alaba!</b>"
    else:
        head = "😔 <b>Mag'lubiyat</b>"

    delta = ""
    if elo_before is not None and elo_after is not None and elo_after != elo_before:
        diff = elo_after - elo_before
        delta = f"\n📊 ELO: {elo_before} → <b>{elo_after}</b> ({'+' if diff > 0 else ''}{diff})"

    who = f"{opp_name} 🤖" if is_bot else opp_name
    return (f"{head}\n\n"
            f"🧪 Kimyo battle\n"
            f"👤 Raqib: <b>{who}</b>\n"
            f"⚔️ Hisob: <b>{my_score} : {opp_score}</b>{delta}\n\n"
            f"Yana o'ynash uchun ilovadagi <b>O'yinlar</b> bo'limiga kiring.")


async def chem_battle_maintenance_loop():
    """Ikki vazifani bajaradi:

    1) UZOQ KUTGAN janglarni "Kimyobot" bilan yakunlaydi. Kichik guruhda
       ayni damda boshqa o'ynayotgan odam bo'lmasligi mumkin — natijasiz
       osilib qolgan jang o'quvchini ko'ngilsizlantiradi.
    2) Yakunlangan janglar haqida ikkala tomonga Telegram xabari yuboradi
       (o'yinchi o'sha payt ilovani ochib turmagan bo'lishi mumkin).
    """
    while True:
        try:
            resolved = resolve_stale_chem_battles()
            if resolved:
                logging.info(f"[KIMYO] {len(resolved)} ta kutayotgan jang bot bilan yakunlandi")

            # Boshlanish sharti (odam soni yoki vaqt) bajarilgan chempionatlar
            import chem_questions as _cq
            for t in get_startable_chem_tournaments():
                pool = get_chem_substances_by_category(t["category_id"])
                qs = _cq.build_battle_questions(pool, count=TOURNAMENT_QUESTION_COUNT)
                if qs and start_chem_tournament(t["id"], qs):
                    logging.info(f"[KIMYO] Chempionat boshlandi: {t['title']} ({t['player_count']} kishi)")
                    for p in get_chem_tournament(t["id"])["players"]:
                        try:
                            await bot.send_message(
                                p["telegram_id"],
                                f"🏆 <b>{t['title']}</b> chempionati boshlandi!\n\n"
                                f"Saralash bosqichi ochiq — ilovadagi <b>O'yinlar → Chempionat</b> "
                                f"bo'limiga kirib savollarga javob bering.",
                                parse_mode="HTML")
                        except Exception as e:
                            logging.warning(f"[KIMYO] Chempionat xabari yuborilmadi: {e}")
        except Exception as e:
            logging.error(f"[KIMYO] Kutayotgan janglarni yakunlashda xato: {e}")

        try:
            for b in get_unnotified_chem_battles():
                try:
                    p1, p2 = b["p1_telegram_id"], b["p2_telegram_id"]
                    winner = b["winner_telegram_id"]
                    is_draw = winner is None
                    is_bot = bool(b["is_bot"])

                    opp1 = (b["bot_name"] or "Kimyobot") if is_bot else \
                        (get_or_create_user(p2, "Raqib").get("first_name") if p2 else "Raqib")
                    try:
                        await bot.send_message(p1, _chem_result_text(
                            b["p1_score"], b["p2_score"], opp1,
                            b["p1_elo_before"], b["p1_elo_after"],
                            is_draw, winner == p1, is_bot), parse_mode="HTML")
                    except Exception as e:
                        logging.warning(f"[KIMYO] Xabar yuborilmadi ({p1}): {e}")

                    if p2:
                        opp2 = get_or_create_user(p1, "Raqib").get("first_name")
                        try:
                            await bot.send_message(p2, _chem_result_text(
                                b["p2_score"], b["p1_score"], opp2,
                                b["p2_elo_before"], b["p2_elo_after"],
                                is_draw, winner == p2, False), parse_mode="HTML")
                        except Exception as e:
                            logging.warning(f"[KIMYO] Xabar yuborilmadi ({p2}): {e}")

                    mark_chem_battle_notified(b["id"])
                except Exception as e:
                    logging.warning(f"[KIMYO] Xabarni tayyorlashda xato (id={b.get('id')}): {e}")
        except Exception as e:
            logging.error(f"[KIMYO] Xabarlar siklida xato: {e}")

        await asyncio.sleep(CHEM_BATTLE_CHECK_INTERVAL_SECONDS)


# ==========================================================================
#  PULLIK GURUH A'ZOLIGINI FON REJIMIDA YANGILASH
# ==========================================================================

MEMBERSHIP_REFRESH_INTERVAL_SECONDS = 5 * 60   # har 5 daqiqada


async def membership_refresh_loop():
    """Faol o'quvchilarning guruh a'zoligini fon rejimida yangilab turadi.

    NEGA KERAK: a'zolik ilova ochilganda ham tekshiriladi, lekin o'quvchi
    ilovani ochmasdan turib guruhdan chiqib ketishi mumkin. Bu sikl
    tufayli u keyingi safar ilovani ochganida kesh allaqachon yangilangan
    bo'ladi va qulf DARHOL ishlaydi — "bir marta ochilgan, keyin
    bepul ko'raveradi" holati bo'lmaydi.

    Telegram limitiga urmaslik uchun: har aylanishda ko'pi bilan 200 ta
    foydalanuvchi va har biri uchun faqat KESHI ESKIRGAN guruhlar.
    """
    import access_control

    while True:
        try:
            if get_access_groups(only_active=True):
                user_ids = get_users_needing_membership_refresh(limit=200)
                for tid in user_ids:
                    try:
                        await access_control.refresh_user_memberships(bot, tid)
                    except Exception as e:
                        logging.warning(f"[KIRISH] {tid} uchun yangilashda xato: {e}")
                    # Telegram limitiga urmaslik uchun kichik pauza
                    await asyncio.sleep(0.15)
                if user_ids:
                    logging.info(f"[KIRISH] {len(user_ids)} ta o'quvchining a'zoligi yangilandi")
        except Exception as e:
            logging.error(f"[KIRISH] A'zolik siklida xato: {e}")

        await asyncio.sleep(MEMBERSHIP_REFRESH_INTERVAL_SECONDS)
