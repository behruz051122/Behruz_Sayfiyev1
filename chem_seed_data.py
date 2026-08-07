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

_MODDA_NOMLARI = [
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


# ==========================================================================
#  CHO'KMALAR
# ==========================================================================
# Bu bo'lim Milliy sertifikat va DTM testlarida eng ko'p so'raladigan
# mavzulardan biri. Cho'kmalar RANGI bo'yicha guruhlangan — chunki
# o'quvchi ularni aynan shu tarzda eslab qoladi ("oq cho'kmalar" ro'yxati,
# "rangli cho'kmalar" ro'yxati), kation oilasi bo'yicha emas.

_CHOKMALAR = [
    {
        "title": "Cho'kmalar 1 — oq cho'kmalar",
        "substances": [
            ("AgCl", "kumush(I) xlorid", None, "oq", None, "oq",
             "NaCl + AgNO3 → AgCl↓ + NaNO3",
             "Cl- ionini aniqlash; yorug'likda qorayadi"),
            ("BaSO4", "bariy sulfat", "og'ir shpat", "oq", None, "oq",
             "BaCl2 + H2SO4 → BaSO4↓ + 2HCl",
             "SO4^2- ionini aniqlash; rentgenda kontrast modda"),
            ("CaCO3", "kalsiy karbonat", "ohaktosh, bo'r, marmar", "oq", None, "oq",
             "Ca(OH)2 + CO2 → CaCO3↓ + H2O",
             "CO2 ni aniqlash (ohakli suvning loyqalanishi); qurilish materiali"),
            ("CaSO4", "kalsiy sulfat", "gips", "oq", None, "oq",
             "CaCl2 + Na2SO4 → CaSO4↓ + 2NaCl",
             "Gips, qurilish va tibbiyotda"),
            ("PbCl2", "qo'rg'oshin(II) xlorid", None, "oq", None, "oq",
             "Pb(NO3)2 + 2NaCl → PbCl2↓ + 2NaNO3",
             "Issiq suvda eriydi — shu bilan AgCl dan farqlanadi"),
            ("PbSO4", "qo'rg'oshin(II) sulfat", None, "oq", None, "oq",
             "Pb(NO3)2 + H2SO4 → PbSO4↓ + 2HNO3",
             "Akkumulyatorda hosil bo'ladi"),
            ("Al(OH)3", "alyuminiy gidroksid", None, "oq", None, "oq jelatinsimon",
             "AlCl3 + 3NaOH → Al(OH)3↓ + 3NaCl",
             "Amfoter — ortiqcha ishqorda eriydi"),
            ("Zn(OH)2", "rux gidroksid", None, "oq", None, "oq",
             "ZnSO4 + 2NaOH → Zn(OH)2↓ + Na2SO4",
             "Amfoter — ortiqcha ishqorda va ammiakda eriydi"),
            ("Mg(OH)2", "magniy gidroksid", None, "oq", None, "oq",
             "MgCl2 + 2NaOH → Mg(OH)2↓ + 2NaCl",
             "Ishqorda erimaydi — Al(OH)3 va Zn(OH)2 dan shu bilan farqlanadi"),
            ("ZnS", "rux sulfid", None, "oq", None, "oq",
             "ZnSO4 + (NH4)2S → ZnS↓ + (NH4)2SO4",
             "Lyuminofor (nur chiqaruvchi qoplama)"),
            ("CuI", "mis(I) yodid", None, "oq", None, "oq",
             "2CuSO4 + 4KI → 2CuI↓ + I2 + 2K2SO4",
             "Yodometriyada; Cu2+ ni aniqlashda"),
            ("Hg2Cl2", "simob(I) xlorid", "kalomel", "oq", None, "oq",
             "Hg2(NO3)2 + 2NaCl → Hg2Cl2↓ + 2NaNO3",
             "Ammiak ta'sirida qorayadi — Hg2^2+ ni aniqlash"),
        ],
    },
    {
        "title": "Cho'kmalar 2 — rangli cho'kmalar",
        "substances": [
            ("AgBr", "kumush(I) bromid", None, "och sariq", None, "och sariq",
             "NaBr + AgNO3 → AgBr↓ + NaNO3",
             "Fotografiya plyonkasida (yorug'likka sezgir)"),
            ("AgI", "kumush(I) yodid", None, "sariq", None, "sariq",
             "KI + AgNO3 → AgI↓ + KNO3",
             "I- ionini aniqlash; sun'iy yomg'ir yog'dirishda"),
            ("PbI2", "qo'rg'oshin(II) yodid", None, "oltinsimon sariq", None, "oltinsimon sariq",
             "Pb(NO3)2 + 2KI → PbI2↓ + 2KNO3",
             "Issiq suvda erib, sovitilganda oltin qirralar hosil qiladi"),
            ("PbS", "qo'rg'oshin(II) sulfid", "qo'rg'oshin yaltirog'i", "qora", None, "qora",
             "Pb(NO3)2 + H2S → PbS↓ + 2HNO3",
             "Pb2+ va S2- ni aniqlash; tabiiy ruda (galenit)"),
            ("CuS", "mis(II) sulfid", None, "qora", None, "qora",
             "CuSO4 + H2S → CuS↓ + H2SO4",
             "Cu2+ ni aniqlash; kislotalarda erimaydi"),
            ("Cu(OH)2", "mis(II) gidroksid", None, "ko'k", None, "ko'k",
             "CuSO4 + 2NaOH → Cu(OH)2↓ + Na2SO4",
             "Qizdirilganda qora CuO ga aylanadi; glyukozani aniqlashda"),
            ("Fe(OH)2", "temir(II) gidroksid", None, "oqish-yashil", None, "oqish-yashil",
             "FeSO4 + 2NaOH → Fe(OH)2↓ + Na2SO4",
             "Havoda oksidlanib jigarrang Fe(OH)3 ga aylanadi"),
            ("Fe(OH)3", "temir(III) gidroksid", None, "qizil-jigarrang", None, "qizil-jigarrang",
             "FeCl3 + 3NaOH → Fe(OH)3↓ + 3NaCl",
             "Fe3+ ni aniqlash; suvni tozalashda koagulyant"),
            ("Cr(OH)3", "xrom(III) gidroksid", None, "kulrang-yashil", None, "kulrang-yashil",
             "CrCl3 + 3NaOH → Cr(OH)3↓ + 3NaCl",
             "Amfoter — ortiqcha ishqorda yashil xromitga aylanib eriydi"),
            ("Ni(OH)2", "nikel(II) gidroksid", None, "och yashil", None, "och yashil",
             "NiSO4 + 2NaOH → Ni(OH)2↓ + Na2SO4",
             "Akkumulyator elektrodlarida"),
            ("Co(OH)2", "kobalt(II) gidroksid", None, "pushti", None, "pushti",
             "CoCl2 + 2NaOH → Co(OH)2↓ + 2NaCl",
             "Havoda asta jigarrangga o'tadi"),
            ("Ag2CrO4", "kumush(I) xromat", None, "g'ishtsimon qizil", None, "g'ishtsimon qizil",
             "2AgNO3 + K2CrO4 → Ag2CrO4↓ + 2KNO3",
             "Mor usulida xloridni titrlashda indikator"),
        ],
    },
]


# ==========================================================================
#  MODDALAR RANGI (eritmalar)
# ==========================================================================
# Bu yerda ERITMA rangi asosiy: laboratoriyada o'quvchi aynan eritmani
# ko'radi. Sof (suvsiz) tuz rangi ko'pincha boshqacha bo'ladi — CoCl2
# buning klassik misoli, shuning uchun ikkalasi ham kiritilgan.

_MODDALAR_RANGI = [
    {
        "title": "Eritmalar rangi — asosiy ionlar",
        "substances": [
            ("CuSO4·5H2O", "mis(II) sulfat gidrati", "mis kuporosi",
             "ko'k kristall", "ko'k", None,
             "CuSO4·5H2O → CuSO4 + 5H2O  (qizdirilganda)",
             "Suvsizlanganda oq bo'ladi — suvni aniqlash usuli"),
            ("FeCl3", "temir(III) xlorid", None,
             "qora-jigarrang kristall", "sariq-jigarrang", None,
             "FeCl3 + 3KSCN → Fe(SCN)3 + 3KCl  (qon-qizil)",
             "Fe3+ ni rodanid bilan aniqlash"),
            ("FeSO4·7H2O", "temir(II) sulfat gidrati", "temir kuporosi",
             "och yashil kristall", "och yashil", None,
             "4FeSO4 + O2 + 2H2O → 4Fe(OH)SO4",
             "Havoda oksidlanib sarg'ayadi"),
            ("KMnO4", "kaliy permanganat", "marganes kaliy",
             "to'q binafsha kristall", "binafsha", None,
             "2KMnO4 + 5Na2SO3 + 3H2SO4 → 2MnSO4 + 5Na2SO4 + K2SO4 + 3H2O",
             "Kuchli oksidlovchi; qaytarilganda rangsizlanadi"),
            ("K2Cr2O7", "kaliy dixromat", "xrompik",
             "to'q sariq kristall", "to'q sariq", None,
             "K2Cr2O7 + 2KOH → 2K2CrO4 + H2O  (sariqqa o'tadi)",
             "Kislotali muhitda kuchli oksidlovchi"),
            ("K2CrO4", "kaliy xromat", None,
             "sariq kristall", "sariq", None,
             "2K2CrO4 + H2SO4 → K2Cr2O7 + K2SO4 + H2O  (to'q sariqqa o'tadi)",
             "Muhitga qarab dixromat ↔ xromat almashinuvi"),
            ("NiSO4", "nikel(II) sulfat", None,
             "yashil kristall", "yashil", None,
             "NiSO4 + 2NaOH → Ni(OH)2↓ + Na2SO4",
             "Nikellash (galvanotexnika)"),
            ("CoCl2", "kobalt(II) xlorid", None,
             "ko'k (suvsiz)", "pushti", None,
             "CoCl2 + 6H2O ⇌ CoCl2·6H2O  (ko'k ⇌ pushti)",
             "Namlikni aniqlovchi indikator qog'oz"),
            ("CrCl3", "xrom(III) xlorid", None,
             "binafsha kristall", "yashil", None,
             "CrCl3 + 3NaOH → Cr(OH)3↓ + 3NaCl",
             "Xrom birikmalari olishda"),
            ("MnSO4", "marganes(II) sulfat", None,
             "och pushti kristall", "och pushti", None,
             "MnSO4 + 2NaOH → Mn(OH)2↓ + Na2SO4",
             "Mikroo'g'it sifatida"),
            ("I2", "yod", None,
             "to'q binafsha kristall", "jigarrang (spirtda)", None,
             "I2 + kraxmal → ko'k rang",
             "Kraxmalni aniqlash; yod eritmasi (antiseptik)"),
            ("Br2", "brom", None,
             "qizil-jigarrang suyuqlik", "sariq-jigarrang", None,
             "Br2 + 2KI → I2 + 2KBr",
             "To'yinmagan bog'ni aniqlash (brom suvi rangsizlanadi)"),
        ],
    },
]


# --------------------------------------------------------------------------
#  Kategoriya kaliti -> namuna levellar
# --------------------------------------------------------------------------
# Admin panelidagi tugma AYNAN TANLANGAN kategoriyaga mos levellarni
# yuklaydi — "Cho'kmalar" bo'limiga kislotalar tushib qolmaydi.

SEED_BY_CATEGORY = {
    "modda_nomlari": _MODDA_NOMLARI,
    "chokmalar": _CHOKMALAR,
    "moddalar_rangi": _MODDALAR_RANGI,
}

# Eski kod bilan moslik uchun (birinchi versiyada bitta ro'yxat edi).
SEED_LEVELS = _MODDA_NOMLARI


def seed_levels_for(category_key: str):
    """Kategoriya kaliti bo'yicha namuna levellar (bo'lmasa — bo'sh)."""
    return SEED_BY_CATEGORY.get((category_key or "").strip().lower(), [])


def seed_summary(category_key: str = "modda_nomlari"):
    """Tugma yonida "nima yuklanadi" ni ko'rsatish uchun."""
    levels = seed_levels_for(category_key)
    return {
        "category_key": category_key,
        "level_count": len(levels),
        "substance_count": sum(len(l["substances"]) for l in levels),
        "titles": [l["title"] for l in levels],
        "available": bool(levels),
    }
