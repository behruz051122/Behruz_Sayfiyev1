# bot.py
# Telegram bot: referal tizimi, kanalga majburiy obuna, Mini App

import asyncio
import logging

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)

from config import BOT_TOKEN, WEBAPP_URL, CHANNEL_USERNAME, CHANNEL_URL, BOT_USERNAME
from database import (
    init_db, get_or_create_user, add_sample_courses,
    create_pending_referral, confirm_referral, set_user_subscribed,
    get_confirmed_referral_count
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
        [InlineKeyboardButton(text="🚀 Platformaga o'tish", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])


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
            f"Platformaga o'tish uchun quyidagi tugmani bosing:",
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
            "Platformaga o'tish uchun tugmani bosing:",
            reply_markup=main_menu_keyboard()
        )
    else:
        await callback.answer("❌ Siz hali obuna bo'lmadingiz. Avval kanalga qo'shiling.", show_alert=True)


async def main():
    init_db()
    add_sample_courses()
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
