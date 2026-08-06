# Brend to'plami — Behruz Sayfiyev

Brendning ikkita alohida vazifasi bor. Ularni **aralashtirmang**:

| Vazifa | Fayl | Nima uchun |
|---|---|---|
| **Avatar** (Telegram, Instagram, YouTube) | `avatar_1024.png` | Doira ichida 40 px da ko'rinadi → faqat harflar o'qiladi |
| **Logotip** (mini app, hujjat, video, kitob) | `logo.svg`, `lockup_*.svg` | Yonida ism yozilgan, joy yetarli → nishon ishlaydi |

## 1. Avatar — "BS" monogramma

`avatar_1024.png` · `avatar_512.png`

Gradient doira (`#2dd4bf → #a78bfa`) + to'q rangdagi qalin **BS**.
Telegram avatarni doiraga kesadi, shuning uchun nishon emas, harflar ishlatilgan —
chat ro'yxatida 40 px da ham darhol tanib olinadi (`avatar_final_preview.png` ga qarang).

**BotFather'ga qo'yish:** @BotFather → `/mybots` → bot → Edit Bot → Edit Botpic →
`avatar_1024.png` ni **rasm sifatida** (fayl emas) yuboring.

## 2. Logotip nishoni

| Element | Ma'nosi |
|---|---|
| Olti burchak | Benzol halqasi → **kimyo** |
| DNK qo'sh spirali | Genetika → **biologiya** |
| Firuza → binafsha gradient | Brend ranglari |

| Fayl | Qayerda |
|---|---|
| `logo.svg` | Kontur nishon — istalgan fon ustida |
| `logo_icon.svg` / `logo_icon_512.png` | To'ldirilgan ikonka — favicon |
| `logo_glyph_dark.svg` | Gradient plitka ustiga (mini app splash va topbar) |
| `logo_glyph_white.svg` | To'q fon ustiga, oq rangda |

## 3. Lokap (nishon + yozuv)

`lockup_dark.svg` — to'q fon uchun · `lockup_light.svg` — oq/och fon uchun

Nishon + **BEHRUZ SAYFIYEV** / KIMYO · BIOLOGIYA.
Prezentatsiya sarlavhasi, video intro/outro, kitob muqovasi, banner, vizitka —
ismingiz ko'rinishi kerak bo'lgan **hamma joyda shu ishlatiladi**.

## 4. Kvadrat lokap (`kvadrat/` papkasi)

`kvadrat/kvadrat_2048.png` · `_1080.png` · `_1024.png` · `_512.png`

Nishon tepada, ostida **Behruz Sayfiyev** va **KIMYO · BIOLOGIYA**.
To'q ko'k fon (`#0a0f1c`) + nishon ortida yumshoq nur.

Qayerda ishlatiladi:

- Instagram va YouTube **profil rasmi**
- post muqovasi, karusel birinchi sahifasi
- video thumbnail fonи, intro/outro
- prezentatsiya sarlavha slaydi
- kitob orqa muqovasi, sertifikat blankasi

**Telegram bot avatariga qo'ymang** — 40 px da yozuv o'qilmaydi, u yerda
`avatar_1024.png` ishlatiladi. `kvadrat/compare_sq.png` da 4 xil nishon
varianti taqqoslangan (arxiv sifatida saqlangan).

## Foydalanish qoidalari

1. **Minimal o'lcham:** avatar 40 px, kontur nishon 32 px, lokap 160 px (eni).
2. **Bo'sh maydon:** nishon atrofida kamida balandligining 25 % qismi bo'sh qolsin.
3. **Ranglarni o'zgartirmang.** Bir rangli chop etishda `logo_glyph_dark.svg` (qora)
   yoki `logo_glyph_white.svg` (oq).
4. **Cho'zmang** — faqat proporsional kattalashtiring/kichraytiring.
5. SVG vektor: banner, futbolka, bilbordda ham sifat yo'qolmaydi.

## Ranglar

```
Firuza (asosiy)   #2dd4bf
Binafsha (urg'u)  #a78bfa
To'q fon          #0a0f1c
Och fon           #f6f8fb
Matn (to'q fonda) #eef2ff
Matn (och fonda)  #111827
```

Shrift: **Manrope / Inter** (bo'lmasa — tizim sans-serif), sarlavha 800–900 og'irlikda.

---

`*_preview.png`, `compare_*.png` fayllari — faqat ko'rish uchun namunalar,
ular ishlatiladigan logotip emas.
