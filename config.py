# config.py
# Barcha sozlamalar shu yerda

BOT_TOKEN = "8949426843:AAGMfLmX3NObg8v5gn3BFPieI62-35HoVhA"  # @BotFather dan

# Mini App joylashgan HTTPS manzil
WEBAPP_URL = "https://behruzsayfiyev1-production-4a0a.up.railway.app"

# Botning username'i (referal havolalar uchun), @ belgisisiz
BOT_USERNAME = "Behruz_Sayfiyev1bot"

# Sizning majburiy obuna kanalingiz. Bot shu kanalda ADMIN bo'lishi SHART,
# aks holda obunani tekshira olmaydi. @kanal_username shaklida yozing.
CHANNEL_USERNAME = "@sizning_kanalingiz"
CHANNEL_URL = "https://t.me/sizning_kanalingiz"

# Brend nomi (Mini App'da yuqorida ko'rinadi)
BRAND_NAME = "Behruz Sayfiyev"
BRAND_SUB = "TALABA PANELI"

# Admin panelga kirish paroli — buni albatta o'zgartiring!
ADMIN_PASSWORD = "behruz2026admin"

# Mini App ichidagi Admin bo'limini ko'radigan Telegram ID lar ro'yxati.
# O'zingizning Telegram ID'ingizni shu ro'yxatga qo'shing (bir nechta admin bo'lishi mumkin).
# ID'ingizni bilish uchun Telegram'da @userinfobot ga /start yozing, u sizga ID'ingizni beradi.
ADMIN_TELEGRAM_IDS = [
    0000000000,  # <-- shu yerga o'zingizning Telegram ID'ingizni yozing (raqamlar, tirnoqsiz)
]

# Foydalanuvchilar "Yordam" bo'limida shu shaxsga yozadi (o'zingizning yoki admin yordamchingizning username'i, @ belgisisiz)
ADMIN_CONTACT_USERNAME = "Behruz_Sayfiyev1"

# Ma'lumotlar bazasi fayli qayerda saqlanishi.
# Railway'da doimiy xotira (Volume) ulanganda, u DB_PATH muhit o'zgaruvchisini
# /data/database.db qilib beradi — shunda ma'lumotlar har bir yangilanishda
# (redeploy) o'chib ketmaydi. Agar bu o'zgaruvchi sozlanmagan bo'lsa (masalan
# kompyuteringizda botni sinab ko'rayotganda), oddiy "database.db" ishlatiladi.
import os
DB_PATH = os.environ.get("DB_PATH", "database.db")
