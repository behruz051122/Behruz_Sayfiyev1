# Biologiya o'yini — o'qituvchi uchun qo'llanma

## Nima uchun kimyodan boshqacha

Kimyoda ma'lumot bir xil shaklda: har modda uchun formula, nom, rang.
Shuning uchun u yerda 4 ta bosqich hamma levelga to'g'ri keladi.

Biologiyada esa ma'lumot **turli shaklda** bo'ladi:

| Ma'lumot turi | Misol | Qanday o'yin bo'ladi |
|---|---|---|
| Termin va vazifa | Mitoxondriya → ATP sintezi | O'rganish, Test, Juftlash |
| **Jarayon bosqichlari** | Mitoz: profaza → metafaza → ... | **Ketma-ketlik** |
| **Tasnif guruhlari** | Prokariot / Eukariot | **Guruhlash** |
| **Ipuchalar** | "Menda qo'sh membrana bor..." | **Kim men?** |
| **Rasmdagi qismlar** | Hujayra tuzilishi diagrammasi | **Rasm bo'yicha** |

Shuning uchun bu yerda **bosqichlar ro'yxati qat'iy emas**:

> Levelda qanday ma'lumot bo'lsa — o'quvchida **shu o'yinlar** paydo bo'ladi.
> Ketma-ketlik kiritmasangiz, "Ketma-ketlik" o'yini umuman ko'rinmaydi.

Admin panelda har levelning yonida **qaysi o'yinlar ochilgani** yozib turadi —
nima yetishmayotganini darhol ko'rasiz.

---

## Boshlash (1 daqiqa)

**Admin panel → 🧬 Biologiya o'yini — baza**

1. Mavzuni bosing (masalan **Hujayra va organoidlar**)
2. Pastda chiqadigan **"Namuna terminlarni yuklash"** tugmasini bosing
3. 👁 tugmasi bilan mavzuni o'quvchilarga oching

Tayyor namuna: **4 mavzu, 8 level, 80 termin, 8 ketma-ketlik**

| Mavzu | Levellar |
|---|---|
| Hujayra va organoidlar | Hujayra organoidlari · Prokariot va eukariot |
| Odam organ tizimlari | Hazm tizimi · Qon aylanish va nafas |
| Genetika va bo'linish | Hujayra bo'linishi · DNK va oqsil sintezi |
| Botanika va zoologiya | O'simlik organlari · Umurtqalilar sinflari |

---

## O'zingiz kiritish

### Termin

**Level tanlang → Terminlar tabi → + Qo'shish**

| Maydon | Nima uchun kerak |
|---|---|
| Termin * | Asosiy nom |
| Ta'rifi | Test va Juftlash o'yinlari uchun |
| Vazifasi | Qo'shimcha savol turi ("Uning vazifasi nima?") |
| **Guruhi** | **Guruhlash** o'yinidagi savat nomi |
| **Ipuchalar** | **Kim men?** o'yini — har biri alohida qatorda |
| Qiziqarli fakt | Kartochkada ko'rinadi |

> **Ipuchalarni umumiydan aniqqa yozing.** Birinchisi javobni oshkor qilmasin,
> oxirgisi deyarli aniq ko'rsatsin:
> ```
> Menda ikki qavatli membrana bor
> Ichki membranam kristalar hosil qiladi
> Men ATP ishlab chiqaraman
> ```

**Ommaviy yuklash** (eng tez): `termin | ta'rifi | vazifasi | guruhi | fakt`

### Ketma-ketlik

**Ketma-ketliklar tabi → + Qo'shish**

Bosqichlarni **to'g'ri tartibda**, har birini alohida qatorda yozing.
O'quvchiga aralashtirilgan holda ko'rsatiladi.

```
Interfaza
Profaza
Metafaza
Anafaza
Telofaza
```

Xato qilsa, o'quvchiga **nechtasi joyida** ekani va **to'g'ri tartib**
ko'rsatiladi — bu mashq, jazolash emas.

### Rasm bo'yicha

**Rasmlar tabi → + Qo'shish**

1. Sarlavha yozing
2. Rasmni yuklang
3. **Rasm ustida nuqta qo'ymoqchi bo'lgan joyni bosing** va nomini yozing

Koordinatalar foizda saqlanadi — rasm telefonda ham, kompyuterda ham
har xil o'lchamda ko'rsatilsa, nuqtalar joyida qoladi.

---

## O'quvchi nimani ko'radi

```
O'yinlar → Biologiya → HUB
    ├── Mavzular (progress bilan)
    ├── Level yo'lagi → level → o'yinlar
    └── Biologiya lug'ati
```

### 7 xil o'yin

| O'yin | Nima bo'ladi |
|---|---|
| 📇 **O'rganish** | Kartochka: termin + ta'rif + vazifa + fakt |
| ✅ **Test** | 5 xil savol turi (nom↔ta'rif, nom↔vazifa, guruh) |
| 🔗 **Juftlash** | Termin va ta'rifni moslashtirish |
| 🔢 **Ketma-ketlik** | Bosqichlarni ▲▼ tugmalari bilan tartibga solish |
| 🗂 **Guruhlash** | Har elementni o'z savatiga tashlash |
| 🕵️ **Kim men?** | Ipuchalar ochiladi, **erta topsa ko'proq ball** (4→1) |
| 🖼 **Rasm bo'yicha** | Rasmdagi nuqtani bosib, nomini tanlash |

Bosqichlar ketma-ket ochiladi. Hammasi bajarilsa — **keyingi level** ochiladi.

**Yulduz:** har levelda 0–3 ta, sinov bosqichlarining o'rtachasi.
Past natija eski yulduzni tushirmaydi.

**Coin:** faqat birinchi urinishda. Yangi o'yin turlari (ketma-ketlik,
guruhlash, "Kim men?", rasm) **+5 coin ko'proq** beradi — o'quvchi ularni
sinab ko'rishga undaladi.

---

## Vizual farq

Biologiya **zumrad–siyan** rangda (kimyo firuza–binafsha edi).
O'quvchi qaysi fanda ekanini rangdan darhol bilib turadi.

---

## Xavfsizlik

- Ketma-ketlikning **to'g'ri tartibi**, guruhlash **javob kaliti**,
  "Kim men?" **javobi** va rasm nuqtalarining **nomlari** mijozga
  umuman yuborilmaydi — har javob alohida server endpointida tekshiriladi.
- Lug'atda ham **ipuchalar yashiriladi** — aks holda o'quvchi
  "Kim men?" o'yinini lug'atdan ko'chirib olardi.
- Level va bosqich qulfi **serverda** tekshiriladi.

---

## Nima qilsam yaxshiroq bo'ladi

1. **Ipucha yozing.** "Kim men?" — eng qiziqarli o'yin, lekin ipuchasiz
   ishlamaydi. Har levelda 5–6 ta terminga ipucha yozsangiz yetarli.
2. **Guruh nomini bering.** Kamida 2 xil guruh bo'lsa "Guruhlash" ochiladi.
3. **Jarayon qo'shing.** Biologiyada ketma-ketlik savoli juda ko'p —
   mitoz, meyoz, oqsil sintezi, qon aylanish, hazm, refleks yoyi.
4. **Rasm yuklang.** Hujayra, yurak, ko'z, neyron — bitta rasm butun
   levelni jonlantiradi.
