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
    get_battles_needing_notification, mark_battle_notified
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
