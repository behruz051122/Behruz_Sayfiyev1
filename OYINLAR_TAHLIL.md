# @kelajakmediklari_bot — "O'yinlar" bo'limi tahlili

Manba: mini app ichida har bir ekran qo'lda bosib chiqilgan (2026-08-07).
Maqsad: shu tizimni Behruz Sayfiyev platformasiga (faqat **Kimyo**) moslashtirish.

---

## 1. Ekranlar xaritasi

```
Bosh sahifa
└── O'yinlar                         (fan kartalari)
    └── Kimyo o'yini                 (HUB — markaziy ekran)
        ├── ELO kartasi ──────────► Reyting jadvali (Global/Viloyat/Tuman)
        ├── Kunlik missiya (0/3)
        ├── Levellar bilan o'rganish
        │   ├── Kategoriya tanlash   (Modda nomlari · Ranglar · Cho'kmalar · Reaksiyalar)
        │   ├── Moddalar lug'ati     (qidiruv + modda kartasi)
        │   └── Level yo'lagi        (23 level, har biri 12 modda, 3 yulduz)
        │       └── Level ichi = 4 BOSQICH
        │           1. O'rganish     — 12 kartochka (flashcard)
        │           2. Test          — 12 savol (variantli)
        │           3. Moslashtirish — 2 taxta × 6 juftlik
        │           4. Yozish        — 12 savol (formulani qo'lda yozish)
        ├── Battle o'ynash           (asosiy CTA)
        └── O'yin rejimlari
            ├── Battle 1v1           (aralash savollar · ELO)
            ├── Do'stga taklif       (6 belgili kod / havola)
            ├── Chempionat           (haftalik turnir, setka)
            └── Bot bilan mashq      (kategoriya tanlab, ELO'siz)
```

---

## 2. Har bir ekran — aniq tafsilotlar

### 2.1 O'yinlar (fan tanlash)

- Sarlavha: "O'yinlar" / "Battle, chempionat va lug'at orqali fanni o'rganing"
- Faol fan kartasi: to'q gradient fon, kolba ikonkasi, o'ng yuqorida `ELO 1000 · Bronza`
  - Nomi, qisqa tavsif ("Modda nomlari, formulalar, ranglar, reaksiyalar")
  - Chip'lar: `Battle 1×1` `Chempionat` `Lug'at`
  - Oq tugma: **O'ynash →**
- Tayyor bo'lmagan fan: xira karta + `TEZ KUNDA` nishoni, tugmasi yo'q
- Pastda izoh: "Haftalik g'oliblar reytingda alohida belgilanadi"

### 2.2 Kimyo o'yini — HUB

| Blok | Mazmuni |
|---|---|
| Yuqori o'ng nishon | `+3350 DNK` (to'plangan valyuta) |
| ELO kartasi | Katta raqam (992), `UMUMIY ELO`, `Bronza · #144`, mayda satr: `0 G'  1 M  0%  🔥0` |
| Kunlik missiya | "Kunlik missiya · 3 ta battle" + progress bar `0/3` |
| O'RGANISH | "Levellar bilan o'rganish / Kategoriya tanlang — oson→qiyin bosqichlar" `0/69` |
| Asosiy CTA | Gradient tugma **Battle o'ynash** |
| O'YIN REJIMLARI | 2×2 grid: Battle 1v1 · Do'stga taklif · Chempionat · Bot bilan mashq |
| Statistika | "KATEGORIYA BO'YICHA G'ALABALAR": Aralash, Modda nomlari, Moddalar rangi, Cho'kmalar, Reaksiyalar — har biri `%` + `n o'yin` |

### 2.3 Levellar bilan o'rganish

- Izoh: "Kategoriya tanlang — har birida oson bosqichdan qiyiniga qarab levellar bor. **Level yakunlansa keyingisi ochiladi.**"
- Kategoriyalar: **Modda nomlari** (faol, "1 sinf bo'limi · 0 yulduz"), Moddalar rangi / Cho'kmalar / Reaksiyalar (`TEZ ORADA`)
- MA'LUMOTNOMA: **Moddalar lug'ati** — "Formula, rang, cho'kma, reaksiyalar"

### 2.4 Level yo'lagi

- Yuqorida yig'ma karta: "Kimyo moddalari — **276 modda · 23 level · 0/69 yulduz**"
- Vertikal yo'lak: ochilgan level — gradient doira ichida raqam; qulflangan — kulrang qulf ikonkasi
- Har level tagida nomi + modda soni: `Kislotalar 1 — kislorodsiz kislotalar (12)`
- Level nomlari (namuna): Kislotalar 1–4 → tuzli minerallar (1,2-qism) → sulfid rudalari →
  temir, marganes va mis minerallari → ohak va karbonat minerallari (1,2) → silikat minerallari va korund …

### 2.5 Level ichi (4 bosqich)

Sarlavha kartasi: level nomi, "12 ta moddani 4 bosqichda o'rganasiz",
"Har bosqichda barcha 12 ta modda qatnashadi", modda chip'lari: `HF` `HCl` `HBr` `HJ` `+8`

| # | Bosqich | Tavsif | Holat nishoni |
|---|---|---|---|
| 1 | **O'rganish** | 12 ta kartochka · Moddalarni ko'rib yodlang | BAJARILDI |
| 2 | **Test** | 12 ta savol · Variantlardan to'g'risini tanlang | HOZIR |
| 3 | **Moslashtirish** | 2 ta taxta · 12 juftlik · Formula va nomni juftlang | 🔒 |
| 4 | **Yozish** | 12 ta savol · Formulani o'zingiz yozing | 🔒 |

Pastda gradient tugma: **N-bosqichni boshlash**

**1-bosqich (O'rganish):** progress bar, `1 / 12`, oq kartada katta gradient **formula** (HF),
ostida to'q sariq **nom** (ftorid kislota), kichik nishon. Tugma: **O'rgandim ✓** (+ orqaga o'q).

**2-bosqich (Test):** `Savol 1 / 12`, savol matni "Bu moddaning formulasi qanday?",
to'q sariq katta **nom**, 4 ta variant tugmasi.
- To'g'ri → yashil, darhol keyingisiga o'tadi
- Xato → tanlangan variant **qizil ✗**, to'g'risi **yashil ✓**, pastda qizil satr `✗ To'g'ri javob: HOCN`

**3-bosqich (Moslashtirish):** "Avval formulani, keyin nomini bosing",
`1/2 TAXTA · 0/12 JUFTLIK TOPILDI`. Ikki ustun: chapda formulalar, o'ngda nomlar (aralash).
To'g'ri juftlik → ikkalasi yashil ✓ va o'chib qoladi.

**4-bosqich (Yozish):** formulani klaviaturadan kiritish.

**Natija ekrani:** konfetti, kubok ikonkasi, "**Ajoyib!**", "Bosqichni muvaffaqiyatli tugatdingiz",
3 ta yulduz (natijaga qarab to'ladi), `+52 ball` ("Shu bosqich uchun to'plandi"),
2 ta ko'rsatkich kartasi: `33% ANIQLIK` va `4/12 TO'G'RI`,
tugmalar: **Davom etish →** va **Yana o'ynash**.

### 2.6 Moddalar lug'ati

- Qidiruv maydoni: "Formula yoki nom bo'yicha qidirish"
- Ro'yxat: chap tomonda kichik chip (formula qisqartmasi), formula (mono shrift), ostida nomi
- Modda kartasi: katta gradient formula → "Tarixiy nomi: qo'rg'oshin yaltirog'i" →
  3 ta chip: `SOF HOLDA` · `ERITMADA` · `CHO'KMA` (rang qiymatlari) →
  `REAKSIYALAR` bloki → `QO'LLANILISHI` bloki

**Modda ma'lumot modeli:** formula, nomi, tarixiy nomi, sof holdagi rangi, eritmadagi rangi,
cho'kma rangi, reaksiyalari, qo'llanilishi, kategoriya, level.

### 2.7 Battle (1v1 / bot)

- Yuqorida ikki o'yinchi paneli: `Siz — 992 ELO · 0 raund` **0 : 1** `Kimyobot — 922 ELO`
- "RAQIB TOPILDI — Kimyobot · 922 ELO", so'ng `1-RAUND · TEST`,
  "Kim tez to'g'ri belgilasa — ball o'shanga", 3-2-1 hisoblagich
- Savol: `SAVOL 2 / 10`, taymer chizig'i + sekundlar, kartada `MODDA NOMI` / **anilin** /
  "Bu moddaning formulasi qanday?", 4 variant `A B C D` harf chiplari bilan
- Javob berilgach: "RAQIB JAVOBI KUTILMOQDA"
- **Bot bilan mashq** — avval kategoriya tanlanadi:
  `Aralash (HAMMASI)` [TAVSIYA], `Modda nomlari`, Ranglar / Cho'kmalar / Reaksiyalar /
  Kislota-asos / Moslashtirish (TEZ ORADA).
  Izoh: "Bitta baza, har xil savol turlari — har modda 15–20 savol beradi"

### 2.8 Do'stga taklif

- Katta gradient kod: `GWM8ME` (6 belgi), "Do'stingiz shu kodni kiritsa o'yin boshlanadi"
- **Telegramda ulashish** tugmasi
- YOKI — "Do'stingiz kodini kiriting" + **Kod bilan qo'shilish**
- "Do'stingiz qo'shilgach kategoriyani siz tanlaysiz"

### 2.9 Chempionat

- Yuqorida: "Yopiq chempionat kodi" + **Kirish**
- `RASMIY CHEMPIONATLAR · SOVRINLI` — bo'sh bo'lsa: "Hozircha rasmiy chempionat yo'q"
- `O'QUVCHILAR CHEMPIONATLARI · FAQAT ELO` — kartalar: nomi, "X yaratgan · Aralash savollar",
  `ELO` yoki `ELO YO'Q` nishoni, `N KISHI`, boshlanish sanasi/vaqti, **Qatnashish — bepul**
- **+ Chempionat yaratish** — "Bepul, sovrinsiz — faqat ELO raqobati"
- Qoida: "Format saralash (teng yarmi o'tadi) — setka — final va 3-o'rin o'yini"

**Yaratish formasi:** nomi ("Masalan: 11-A sinf kubogi"),
boshlanish sharti — `Odam soni to'lganda` / `Belgilangan vaqtda`, kishi soni (8),
"ELO faqat 8 kishidan kam bo'lmasa hisoblanadi", "Kuniga bitta chempionat yaratish mumkin".

### 2.10 Reyting jadvali

- Tab'lar: `Global` · `Viloyat` · `Tuman`
- `HAFTALIK ★ MUKOFOT — HAR HAFTA YAKUNIDA`: ★5 (1-o'rin), ★3 (2), ★2 (3), ★1 (4–10)
- Podium: TOP-3 avatar + ism + sinf/maktab + ELO
- Ro'yxat: `#4` … — avatar, ism, maktab, ELO, o'zgarish (`▲276`), daraja (`BRONZA` / `KUMUSH`)
- Pastda yopishgan qator: `#144 · Siz — 992 · BRONZA`

---

## 3. Tizimning asosiy g'oyasi

1. **Bitta baza — ko'p o'yin.** Moddalar bazasi (formula, nom, rang, cho'kma, reaksiya)
   bir marta kiritiladi; undan flashcard, test, moslashtirish, yozish, battle savollari
   **avtomatik** generatsiya qilinadi. Admin savol yozmaydi — modda kiritadi.
2. **Ikki xil motivatsiya.** Yolg'iz o'rganish (levellar, yulduz, ball) + raqobat
   (ELO, battle, chempionat, reyting).
3. **Ketma-ket ochilish.** Level → keyingi level; bosqich → keyingi bosqich.
4. **Kundalik ilgak.** Kunlik missiya (3 ta battle) + streak + haftalik ★ mukofot.

---

## 4. Bizga moslashtirish — farqlar

| Referens | Bizda |
|---|---|
| DNK ✦ valyutasi | mavjud **coin** tizimi ishlatiladi |
| Global/Viloyat/Tuman reyting | Global + **kurs bo'yicha** (o'quvchilarim) |
| Ochiq platforma, hamma o'ynaydi | Kurs a'zolari uchun; bepul namuna ochiq |
| Och (light) dizayn | Bizning **qorong'i + neon** dizayn tokenlarimiz |
| Kimyo + Biologiya | Hozircha **faqat Kimyo** |
| Kimyobot (sun'iy raqib) | Xuddi shunday — o'quvchi kam bo'lganda kutmasin |
