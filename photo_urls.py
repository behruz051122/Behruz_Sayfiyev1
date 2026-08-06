# photo_urls.py
# Vazifa rasmlari uchun KO'RISH HAVOLASINI tayyorlaydi.
#
# Rasm ikki xil joyda bo'lishi mumkin:
#   - Telegram arxiv kanalida (yangi, asosiy usul — server xotirasi tejaladi)
#   - Serverning /uploads papkasida (eski yozuvlar bilan moslik uchun)
#
# Telegramdagi rasm himoyalangan endpoint orqali beriladi. Brauzerdagi
# <img src="..."> tegi maxsus header yubora olmagani uchun, havolaga
# QISQA MUDDATLI IMZO qo'shiladi (auth.sign_photo_token). Imzo ro'yxat
# tayyorlanayotganda — kirish huquqi ALLAQACHON tekshirilgandan keyin
# beriladi, shuning uchun begona odam havolani yasay olmaydi.

from auth import sign_photo_token
from config import JWT_SECRET_KEY

PHOTO_URL_TTL_SECONDS = 86400  # 24 soat


def decorate_photo_urls(photos):
    """Har bir rasmga `view_url` qo'shadi. Ro'yxatni joyida o'zgartiradi
    va o'zini qaytaradi."""
    for p in photos or []:
        if p.get("in_telegram"):
            expires_at, signature = sign_photo_token(p["id"], JWT_SECRET_KEY, PHOTO_URL_TTL_SECONDS)
            p["view_url"] = f"/api/homework/photo/{p['id']}?e={expires_at}&s={signature}"
        else:
            p["view_url"] = p.get("photo_url")
    return photos
