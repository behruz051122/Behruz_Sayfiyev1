"""
generate_password_hash.py
Yangi admin parol o'rnatmoqchi bo'lsangiz shu skriptni ishga tushiring:

    python generate_password_hash.py

So'ralganda yangi parolni kiriting — skript uni bcrypt bilan xeshlab beradi.
Chiqqan qatorni ".env" faylidagi ADMIN_PASSWORD_HASH= qatoriga qo'ying.

DIQQAT: Parolning o'zini hech qayerga (kodga, .env'ga, chatga) yozib qo'ymang —
faqat shu skript chiqargan xesh saqlanadi. Parolni faqat o'zingiz eslab qoling.
"""

import getpass
from auth import hash_password

if __name__ == "__main__":
    pw1 = getpass.getpass("Yangi admin parolni kiriting: ")
    pw2 = getpass.getpass("Parolni tasdiqlang: ")

    if pw1 != pw2:
        print("\n❌ Parollar mos kelmadi. Qaytadan urinib ko'ring.")
    elif len(pw1) < 8:
        print("\n❌ Parol kamida 8 belgidan iborat bo'lishi kerak.")
    else:
        hashed = hash_password(pw1)
        print("\n✅ Tayyor. Quyidagi qatorni '.env' fayliga qo'ying:\n")
        print(f"ADMIN_PASSWORD_HASH={hashed}")
        print("\n(Eski qatorni albatta o'chirib, shu bilan almashtiring)")
