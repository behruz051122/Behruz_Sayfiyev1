# chem_seed_data.py
# ==========================================================================
#  KIMYO O'YINI — NAMUNA BAZA
# ==========================================================================
# Admin panelidagi "Namuna moddalarni yuklash" tugmasi shu ma'lumotni
# bazaga qo'shadi. Maqsad — o'qituvchi bo'sh ekrandan boshlamasin:
# ikkita to'liq level bilan tizimni darhol sinab ko'ra olsin, keyin
# ustiga o'z levellarini qo'shsin.
#
# MA'LUMOT ANIQLIGI HAQIDA:
#   - Ranglar SOF MODDA uchun (xona haroratida) va SUVDAGI ERITMA uchun
#     alohida ko'rsatilgan — bu ikkisi ko'pincha farq qiladi.
#   - Ishonch hosil qilib bo'lmaydigan qiymat qo'yilmagan (None) — savol
#     generatori bo'sh maydondan savol yasamaydi, shuning uchun noto'g'ri
#     savol chiqmaydi.
#   - Ba'zi kislotalar SOF HOLDA MAVJUD EMAS (H2CO3, H2SO3, HClO) — ular
#     faqat eritmada bo'ladi va bu izohda aytilgan.
#
# Maydonlar tartibi:
#   (formula, nomi, tarixiy nomi, sof holdagi rangi, eritmadagi rangi,
#    cho'kma rangi, reaksiyalari, qo'llanilishi)

SEED_LEVELS = [
    {
        "title": "Kislotalar 1 — kislorodsiz kislotalar",
        "substances": [
            ("HF", "ftorid kislota", "plavik kislota",
             "rangsiz gaz", "rangsiz", None,
             "SiO2 + 4HF → SiF4↑ + 2H2O",
             "Shishani o'yish (gravirovka), ftoridlar olish"),

            ("HCl", "xlorid kislota", "tuz kislotasi",
             "rangsiz gaz", "rangsiz", None,
             "Zn + 2HCl → ZnCl2 + H2↑",
             "Metallarni tozalash, oshqozon shirasida bor"),

            ("HBr", "bromid kislota", None,
             "rangsiz gaz", "rangsiz", None,
             "HBr + NaOH → NaBr + H2O",
             "Bromidlar va dori vositalarini olish"),

            ("HI", "yodid kislota", None,
             "rangsiz gaz", "rangsiz", None,
             "2HI → H2 + I2  (qizdirilganda)",
             "Yodidlar olish; havoda asta-sarg'ayadi (I2 ajraladi)"),

            ("H2S", "sulfid kislota", "vodorod sulfid",
             "rangsiz gaz", "rangsiz", None,
             "H2S + Pb(NO3)2 → PbS↓ + 2HNO3",
             "Sifat tahlilida kationlarni aniqlash; zaharli, chirigan tuxum hidli"),

            ("H2Se", "selenid kislota", None,
             "rangsiz gaz", "rangsiz", None,
             None,
             "Selenidlar olish; H2S dan kuchliroq kislota"),

            ("H2Te", "tellurid kislota", None,
             "rangsiz gaz", "rangsiz", None,
             None,
             "Telluridlar olish; qatorda eng kuchli kislota"),

            ("HCN", "sianid kislota", "sinil kislotasi",
             "rangsiz suyuqlik", "rangsiz", None,
             "HCN + NaOH → NaCN + H2O",
             "Juda zaharli; sianidlar olishda (sanoatda qattiq nazorat ostida)"),

            ("HSCN", "rodanid kislota", "tiosianat kislota",
             "rangsiz", "rangsiz", None,
             "Fe3+ + 3SCN- → Fe(SCN)3  (qon-qizil rang)",
             "Fe3+ ionini aniqlashda sifat reaktivi"),

            ("HN3", "azid kislota", "azotli vodorod kislotasi",
             "rangsiz suyuqlik", "rangsiz", None,
             "HN3 + NaOH → NaN3 + H2O",
             "Azidlar olish; portlovchi, o'ta ehtiyot talab qiladi"),
        ],
    },
    {
        "title": "Kislotalar 2 — kislorodli kislotalar",
        "substances": [
            ("H2SO4", "sulfat kislota", "kuporos moyi",
             "rangsiz moysimon suyuqlik", "rangsiz", None,
             "H2SO4 + BaCl2 → BaSO4↓ + 2HCl",
             "Akkumulyator, mineral o'g'it, sanoatda eng ko'p ishlatiladigan kislota"),

            ("H2SO3", "sulfit kislota", None,
             "sof holda mavjud emas", "rangsiz", None,
             "SO2 + H2O ⇌ H2SO3",
             "Faqat eritmada bo'ladi; oqartiruvchi va konservant sifatida"),

            ("HNO3", "nitrat kislota", "aqua fortis (kuchli suv)",
             "rangsiz suyuqlik", "rangsiz", None,
             "Cu + 4HNO3(kons.) → Cu(NO3)2 + 2NO2↑ + 2H2O",
             "O'g'it, portlovchi moddalar; saqlanganda NO2 dan sarg'ayadi"),

            ("HNO2", "nitrit kislota", None,
             "sof holda mavjud emas", "och ko'k", None,
             "NaNO2 + HCl → HNO2 + NaCl",
             "Faqat eritmada, sovuqda barqaror; diazolash reaksiyalarida"),

            ("H3PO4", "ortofosfat kislota", "fosfor kislotasi",
             "rangsiz kristall", "rangsiz", None,
             "H3PO4 + 3NaOH → Na3PO4 + 3H2O",
             "Fosforli o'g'itlar, ichimliklarda kislotalik regulyatori"),

            ("HPO3", "metafosfat kislota", None,
             "rangsiz shishasimon massa", "rangsiz", None,
             "HPO3 + H2O → H3PO4",
             "Suvni yutuvchi modda (quritgich)"),

            ("H4P2O7", "pirofosfat kislota", "difosfat kislota",
             "rangsiz kristall", "rangsiz", None,
             "2H3PO4 → H4P2O7 + H2O  (qizdirilganda)",
             "Pirofosfatlar olish"),

            ("H2CO3", "karbonat kislota", "ko'mir kislotasi",
             "sof holda mavjud emas", "rangsiz", None,
             "CO2 + H2O ⇌ H2CO3",
             "Gazlangan ichimliklar; faqat eritmada bo'ladi"),

            ("H2SiO3", "metasilikat kislota", "kremniy kislotasi",
             "oq amorf modda", None, "oq jelatinsimon",
             "Na2SiO3 + 2HCl → H2SiO3↓ + 2NaCl",
             "Silikagel olish (quritgich va adsorbent)"),

            ("HClO", "gipoxlorit kislota", None,
             "sof holda mavjud emas", "och sarg'ish-yashil", None,
             "Cl2 + H2O ⇌ HCl + HClO",
             "Oqartirish va suvni zararsizlantirish"),

            ("HClO3", "xlorat kislota", None,
             "sof holda mavjud emas", "rangsiz", None,
             "Ba(ClO3)2 + H2SO4 → BaSO4↓ + 2HClO3",
             "Xloratlar (Bertole tuzi) olish"),

            ("HClO4", "perxlorat kislota", None,
             "rangsiz suyuqlik", "rangsiz", None,
             "HClO4 + KOH → KClO4 + H2O",
             "Eng kuchli mineral kislotalardan biri; analitik kimyoda"),
        ],
    },
]


def seed_summary():
    """Tugma yonida ko'rsatish uchun qisqa ma'lumot."""
    return {
        "level_count": len(SEED_LEVELS),
        "substance_count": sum(len(l["substances"]) for l in SEED_LEVELS),
        "titles": [l["title"] for l in SEED_LEVELS],
    }
