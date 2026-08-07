# Kimyo o'yini — o'qituvchi uchun qo'llanma

## Eng muhimi: siz savol yozmaysiz

Siz faqat **modda** kiritasiz. Barcha savollar — kartochka, variantli test,
moslashtirish, formulani yozish va battle savollari — shu bazadan **avtomatik**
yasaladi va har safar boshqacha tartibda keladi.

Ya'ni 276 ta modda kiritsangiz, o'n minglab savol varianti o'z-o'zidan paydo bo'ladi.

---

## 1. Bazani to'ldirish (3 qadam)

**Admin panel → 🧪 Kimyo o'yini — moddalar bazasi**

### 1-qadam. Kategoriyani tanlang

Tayyor 4 ta kategoriya bor:

| Kategoriya | Holati |
|---|---|
| Modda nomlari | ochiq |
| Moddalar rangi | yopiq |
| Cho'kmalar | yopiq |
| Reaksiyalar | yopiq |

Yonidagi 👁 / 🚫 tugmasi kategoriyani o'quvchilarga **ochadi yoki yopadi**.
Baza to'lmaguncha yopiq turgani ma'qul — o'quvchi bo'sh bo'limga kirmaydi.

### 2-qadam. Level qo'shing

**+ Level** tugmasi. Har levelda odatda **12 ta modda** bo'ladi.

Nomni mazmunli qo'ying — o'quvchi shuni ko'radi:

```
Kislotalar 1 — kislorodsiz kislotalar
Kislotalar 2 — xlor, brom va yod qatori
Tuzli minerallar (1-qism)
```

### Eng tezi: **"Namuna moddalarni yuklash"** tugmasi

Kategoriyani tanlaganingizda pastda chiqadi. Bir bosishda tayyor baza yuklanadi:

| Kategoriya | Nima yuklanadi |
|---|---|
| **Modda nomlari** | Kislorodsiz kislotalar (10) + kislorodli kislotalar (12) |
| **Cho'kmalar** | Oq cho'kmalar (12) + rangli cho'kmalar (12) |
| **Moddalar rangi** | Eritmalar rangi — asosiy ionlar (12) |
| Reaksiyalar | namuna yo'q — o'zingiz kiritasiz |

Jami **58 ta modda**, har birida tarixiy nomi, ranglari, xarakterli reaksiyasi
va qo'llanilishi bilan. Tugmani qayta bossangiz takrorlanmaydi.

> Cho'kmalar bo'limi Milliy sertifikat va DTM uchun ayniqsa qimmatli —
> "oq cho'kmalar" va "rangli cho'kmalar" alohida guruhlangan, chunki
> o'quvchi ularni aynan shu tarzda eslab qoladi.

### 3-qadam. Moddalarni yuklang

**⬆ Ommaviy yuklash** — eng tez yo'l. Har qatorda bitta modda:

```
formula | nomi | tarixiy nomi | sof rang | eritma rangi | cho'kma rangi
```

Namuna:

```
HF | ftorid kislota
HCl | xlorid kislota | tuz kislotasi
H2SO4 | sulfat kislota | kuporos moyi | rangsiz | rangsiz | -
PbS | qo'rg'oshin sulfid | qo'rg'oshin yaltirog'i | qora | - | qora
```

- Faqat **dastlabki ikkitasi majburiy**. Qolganini keyin to'ldirsangiz ham bo'ladi.
- Bo'sh maydonga `-` qo'ying.
- Ajratgich `|` **yoki tabulyatsiya** — shuning uchun **Excel jadvalidan
  to'g'ridan-to'g'ri nusxa ko'chirib** qo'ysangiz ham ishlaydi.
- Yuklangach nechta qo'shilgani va qaysi qator nega o'tkazib yuborilgani ko'rsatiladi.

> **Baza qanchalik to'liq bo'lsa, savollar shunchalik xilma-xil.** Rang kiritilmagan
> bo'lsa, rang savoli umuman yasalmaydi — "javobi yo'q" savol chiqmaydi.

---

## 2. O'quvchi nimani ko'radi

```
O'yinlar → Kimyo → HUB
    ├── ELO kartasi ────────► Reyting jadvali
    ├── Kunlik missiya (3 ta battle)
    ├── Levellar bilan o'rganish → kategoriya → level yo'lagi → level
    ├── Moddalar lug'ati (qidiruv)
    └── O'yin rejimlari
        ├── Battle 1v1     (ELO o'zgaradi)
        ├── Do'stga taklif (6 belgili kod)
        ├── Bot bilan mashq (ELO o'zgarmaydi)
        ├── Chempionat
        └── Mening janglarim
```

### Level ichidagi 4 bosqich

Har bosqichda shu levelning **barcha moddalari** qatnashadi:

| # | Bosqich | Nima bo'ladi |
|---|---|---|
| 1 | **O'rganish** | Kartochka: formula + nom + rang/cho'kma/tarixiy nom |
| 2 | **Test** | Variantli savol; xato bo'lsa to'g'ri javob yashil bo'lib ko'rsatiladi |
| 3 | **Moslashtirish** | 6 tadan taxta — formula va nomni juftlash |
| 4 | **Yozish** | Formulani klaviaturadan kiritish |

Bosqichlar **ketma-ket** ochiladi. To'rttasi ham bajarilsa — **keyingi level** ochiladi.

**Yulduz:** har levelda 0–3 ta. Uchta sinov bosqichining (Test, Moslashtirish,
Yozish) o'rtachasi. O'rganish hisobga olinmaydi — u sinov emas.
Past natija eski yulduzni **tushirmaydi**, faqat ko'tarish mumkin.

**Coin:** faqat birinchi urinishda beriladi (5–25) — qayta o'ynab cheksiz
coin yig'ib bo'lmaydi.

---

## 3. Battle va ELO

- **Battle 1v1** — kutayotgan raqib bo'lsa darhol jonli jang; bo'lmasa o'quvchi
  javob berib qo'yadi, raqib keyinroq qo'shiladi. **10 daqiqada hech kim
  qo'shilmasa — Kimyobot raqib bo'ladi.** Jang hech qachon osilib qolmaydi.
- Natija tayyor bo'lishi bilan ikkala tomonga **Telegram xabari** boradi.
- **Bot bilan mashq** — darhol, lekin ELO o'zgarmaydi (sun'iy ko'tarishning oldi).
- Tenglikda **tezroq javob bergan** yutadi.

**Darajalar:**

| ELO | Daraja |
|---|---|
| 1700+ | 💎 Olmos |
| 1500–1699 | 🔷 Platina |
| 1300–1499 | 🥇 Oltin |
| 1100–1299 | 🥈 Kumush |
| 1100 dan past | 🥉 Bronza |

---

## 4. Chempionat

Format: **saralash → setka → final**

1. Barcha qatnashchilar **aynan bir xil** 10 ta savolga javob beradi.
2. Ball (tenglikda — vaqt) bo'yicha yuqoridagi 2, 4, 8, 16... kishi o'tadi.
3. Setkada juftliklar ham bir xil savollarga javob beradi — shuning uchun
   **bir vaqtda onlayn bo'lish shart emas**.
4. Ikkala tomon javob berishi bilan g'olib avtomatik keyingi bosqichga o'tadi.

### Sovrinli chempionat (faqat siz e'lon qilasiz)

**Admin panel → 🏆 Chempionatlar → + E'lon qilish**

- Nomi va **sovrin matnini** yozasiz (o'quvchilarga ko'rinadi)
- Qachon boshlanishini tanlaysiz: *odam yig'ilganda* yoki *belgilangan vaqtda*
- Sizning chempionatingiz o'quvchilar ro'yxatida **eng tepada**, "SOVRINLI"
  bo'limida turadi
- Sizga **kuniga bitta** chegarasi yo'q — xohlagancha e'lon qilasiz

O'quvchilarniki esa **sovrinsiz** — faqat ELO raqobati.

### Umumiy qoidalar

- O'quvchilar o'zlari chempionat yaratishi mumkin — **kuniga bitta**.
- Belgilangan odam soni yig'ilishi bilan **avtomatik boshlanadi** va barchaga
  Telegram xabari boradi.
- **ELO faqat 8 va undan ko'p qatnashchi bo'lsa** hisoblanadi — kichik "uy
  chempionati" bilan reytingni ko'tarib bo'lmaydi.
- G'oliblarga bonus: 1-o'rin +40, 2-o'rin +25, 3-o'rin +15 ELO.

---

## 5. Xavfsizlik (nima uchun aldab bo'lmaydi)

- Level va bosqich **qulfi serverda** tekshiriladi — mijozdagi qulf ikonkasini
  chetlab o'tib bo'lmaydi.
- Bosqich bali **serverda qayta hisoblanadi**: mijoz javoblarni yuboradi, server
  ularni bazadan tekshiradi. Mijozdagi ballga ishonilmaydi.
- Battle va chempionatda **to'g'ri javob umuman yuborilmaydi** va **vaqtni ham
  server o'lchaydi** (bitta savolga maksimum 20 soniya).

---

## 6. Nimadan boshlash kerak

1. "Modda nomlari" kategoriyasiga **1-2 ta level** qo'shing (12 tadan modda).
2. O'zingiz kirib to'rt bosqichni o'ynab ko'ring.
3. Yoqsa — qolgan levellarni to'ldiring, kategoriyani ochiq qoldiring.
4. Ranglar/cho'kmalar ustunlarini keyinroq to'ldirsangiz, savollar
   xilma-xilligi o'z-o'zidan ortadi.
