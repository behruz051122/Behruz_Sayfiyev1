# Nazorat testi — talabalarni tayinlash (yangi imkoniyat)

## Nima o'zgardi

Ilgari nazorat testi faqat bitta kursga bog'lab qo'yilardi — shu kursga yozilgan
o'quvchi avtomatik kira olardi. Endi bunga qo'shimcha, **har bir nazorat testiga
xohlagan talabalaringizni bevosita, birma-bir tayinlash** imkoniyati qo'shildi —
kursga umuman yozilmagan bo'lsa ham.

Ikkala usul ham parallel ishlaydi:
1. **Tayinlash** (yangi, tavsiya etiladi) — admin panelda "👥 Talabalar" tugmasi
   orqali aniq talabalarni qidirib, shu testga qo'shasiz.
2. **Kursga bog'lash** (eski usul, hali ham ishlaydi) — test bir kursga
   bog'langan bo'lsa, shu kursga yozilgan har bir o'quvchi ham avtomatik kira oladi.

Bittasi yetarli — ikkalasini birga ishlatish ham mumkin.

## Oylik reyting endi qanday hisoblanadi

Reyting avval faqat foiz natijaga qarab tuzilardi. Endi **teng foiz to'plagan
talabalar orasida kim tezroq (kamroq vaqtda) topshirgan bo'lsa, o'sha yuqorida**
turadi. Reyting ro'yxatida va "sizning o'rningiz" blokida endi o'rtacha vaqt ham
(masalan `⏱ 3:45`) ko'rsatiladi.

## Admin panelda qanday ishlatiladi

1. **Admin** bo'limi → **Testlar** → kerakli nazorat testining qatorida
   **"👥 Talabalar"** tugmasini bosing (bu tugma faqat "🎓 NAZORAT" belgili
   testlarda chiqadi).
2. Ochilgan oynada qidiruv maydoniga talabaning ismini, username'ini yoki
   Telegram ID raqamini yozing — natijalar avtomatik chiqadi.
3. Kerakli talaba qatorida **"+ Tayinlash"** tugmasini bosing — u darhol
   "Tayinlangan talabalar" ro'yxatiga qo'shiladi va testni topshira oladi.
4. Kimnidir ro'yxatdan chiqarish uchun uning qatoridagi **"O'chirish"**
   tugmasini bosing.

**Eslatma:** Talaba ro'yxatda chiqishi uchun u avval botni kamida bir marta
ochgan bo'lishi kerak (shunda uning ismi bazaga yoziladi). Agar talaba hali
botga kirmagan bo'lsa, uni Telegram ID raqami orqali ham qidirib topib, tayinlab
qo'yishingiz mumkin — bot ochilishi bilan ruxsat avtomatik ishlay boshlaydi.

## Yangi/o'zgargan fayllar

- `database.py` — `control_test_access` jadvali, tayinlash/o'chirish/qidirish
  funksiyalari, vaqtni hisobga oluvchi reyting
- `routers/admin_control_tests.py` — yangi fayl (admin uchun tayinlash API'si
  va talaba qidirish API'si)
- `routers/tests.py` — kirish tekshiruvi endi tayinlash + kurs ikkalasini ham
  hisobga oladi
- `server.py` — yangi router ulandi
- `webapp/index.html`, `webapp/js/admin.js` — "Talabalar" boshqaruv oynasi
- `webapp/js/tests.js`, `webapp/js/leaderboard.js` — talaba tomonidagi matnlar
  va reytingda vaqt ko'rsatilishi yangilandi

## Joylashtirish (deploy)

Boshqa hech qanday maxsus qadam kerak emas — `database.py` ishga tushganda
yangi jadvalni o'zi avtomatik yaratadi (`CREATE TABLE IF NOT EXISTS`), mavjud
ma'lumotlarga tegmaydi. Odatdagidek:

```
git add .
git commit -m "nazorat testiga talaba tayinlash + vaqt-asosli reyting"
git push
```

Railway avtomatik qayta deploy qiladi.
