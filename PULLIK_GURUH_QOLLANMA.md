# Pullik guruh orqali avtomatik kirish

## Muammo va yechim

**Ilgari:** har bir o'quvchini qo'lda kursga biriktirish kerak edi.
O'quvchi ko'p bo'lganda bu real emas.

**Endi:** yopiq (pullik) guruhingizda bo'lgan har kim **avtomatik** kirish oladi.
Mini app o'quvchining **Telegram ID** sini guruh a'zolari bilan solishtiradi.

- Guruhda bor → pullik darslar va testlar ochiq
- Guruhda yo'q → «Pullik guruhga qo'shiling» yozuvi va **qo'shilish tugmasi**
- Guruhdan chiqib ketsa → **10 daqiqada** avtomatik yopiladi
- Ommaviy (bepul) darslar → **hammaga ochiq**, o'zgarmaydi
- Qo'lda biriktirish → **saqlangan**, istisno holatlar uchun ishlaydi

---

## Sozlash (5 daqiqa, bir marta)

### 1-qadam. Botni guruhga qo'shing va ADMIN qiling

> ⚠️ **Eng muhim qadam.** Bot admin bo'lmasa Telegram a'zolikni tekshirishga
> ruxsat bermaydi va hech kim kirish ololmaydi.

Guruh → Sozlamalar → Administratorlar → **@Behruz_Sayfiyev1bot** ni qo'shing.
Qo'shimcha huquq berish shart emas — oddiy admin yetarli.

### 2-qadam. Guruh ID sini toping

1. Guruhdagi istalgan xabarni **@userinfobot** ga forward qiling
2. U `-100` bilan boshlanadigan raqamni ko'rsatadi, masalan `-1001234567890`

> Yopiq guruh ID si **doim `-100` bilan boshlanadi**. Agar `-100` siz
> kiritsangiz, tizim xato deb qaytaradi.

### 3-qadam. Taklif havolasini oling

Guruh → Sozlamalar → Taklif havolalari → havolani nusxalang
(`https://t.me/+AbCdEf...`).

Bu havola o'quvchining «qo'shilish» tugmasiga qo'yiladi. Havola bo'lmasa
tugma o'rniga «Admin bilan bog'lanish» chiqadi.

### 4-qadam. Admin panelga kiriting

**Admin panel → 🔐 Pullik guruhlar → + Guruh**

| Maydon | Namuna |
|---|---|
| Guruh nomi | Kimyo pullik guruh |
| chat_id | -1001234567890 |
| Taklif havolasi | https://t.me/+AbCdEf... |

Saqlaganingizda tizim **darhol tekshiradi** va bot admin emasligini
o'sha zahoti aytadi.

### 5-qadam. Qaysi kontent qaysi guruhga tegishli

Pastda **«Qaysi kontent qaysi guruhga tegishli»** jadvali chiqadi.
Kurs yoki test bosqichi yonidagi guruh belgisini bosing — tamom.

- Belgilangan kurs **faqat** shu guruh a'zolariga ochiladi
- Hech qaysi guruh belgilanmagan kurs — **eski tartibda** ishlaydi
- Bepul kurslarga guruh belgilash **shart emas** (ular baribir ochiq)

---

## Kundalik ish

O'quvchi to'lov qiladi → siz uni guruhga qo'shasiz → **tamom**.
Mini appda hech narsa qilish shart emas.

### Tugmalar

| Tugma | Nima qiladi |
|---|---|
| 🔍 **Tekshirish** | Bot guruhda adminmi, guruh nomi va a'zolar soni |
| 🔄 **Yangilash** | Barcha o'quvchilar a'zoligini hoziroq qayta tekshiradi |
| ✏️ | Nomi, chat_id yoki havolani o'zgartirish |
| 🗑 | Guruhni va uning bog'lanishlarini o'chirish |

🔄 tugmasi odatda kerak emas — tizim har 5 daqiqada o'zi tekshiradi.
Guruhga ko'p odam qo'shganingizdan keyin bosishingiz mumkin.

---

## O'quvchi nimani ko'radi

Guruhda **bo'lmasa** — pullik darsni ochganda:

> 🔐 **Bu dars pullik bo'lim uchun**
> Darsni ko'rish uchun **Kimyo pullik guruh** guruhiga qo'shilishingiz kerak.
> Guruhga qo'shilganingizdan so'ng barcha darslar **avtomatik ochiladi**.
>
> `➕ Kimyo pullik guruhiga qo'shilish`
> `✅ Men qo'shildim — tekshirish`

«Men qo'shildim» tugmasi a'zolikni **darhol** qayta tekshiradi — o'quvchi
10 daqiqa kutib o'tirmaydi.

Testlarda ham xuddi shunday: pullik bosqich yonida qo'shilish havolasi chiqadi.

---

## Xavfsizlik

- Qulf **serverda** tekshiriladi. Mijozdagi qulfni chetlab o'tib
  to'g'ridan-to'g'ri so'rov yuborilsa ham server rad etadi.
- **«Ishonchsiz holatda yopiq»** tamoyili: Telegram javob bermasa yoki
  bot admin bo'lmasa — kirish **berilmaydi**. Aks holda bitta tarmoq
  uzilishi butun pullik kontentni ochib yuborardi.
- A'zolik natijasi 10 daqiqa saqlanadi — shuning uchun har dars ochilganda
  Telegram'ga so'rov yog'ilmaydi va ilova sekinlashmaydi.

---

## Ko'p beriladigan savollar

**Bir nechta guruhim bor — bo'ladimi?**
Ha. Istagancha guruh qo'shing va har kursni o'z guruhiga bog'lang.
Bitta kursni bir nechta guruhga ham bog'lash mumkin — **birortasida**
bo'lsa yetarli.

**Guruhdan chiqib ketgan o'quvchi nima bo'ladi?**
~10 daqiqada pullik darslar yopiladi. Bepul darslar ochiq qoladi.

**To'lagan, lekin guruhga qo'shilmagan o'quvchi bo'lsa?**
Eski usul saqlangan — uni admin panelidan qo'lda biriktirasiz.
Ikkala yo'l parallel ishlaydi.

**Kanalda ham ishlaydimi?**
Ha, yopiq kanal ham bo'ladi — bot u yerda ham admin bo'lishi kerak.

**Bot admin emasligini qanday bilaman?**
🔍 tugmasi aytadi, va guruh ro'yxatida qizil ogohlantirish chiqadi.
