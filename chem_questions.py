# chem_questions.py
# ==========================================================================
#  KIMYO O'YINI — SAVOL GENERATORI
# ==========================================================================
# ASOSIY G'OYA: o'qituvchi SAVOL YOZMAYDI.
#
# U faqat MODDA kiritadi (formula, nomi, tarixiy nomi, rangi, cho'kmasi,
# reaksiyasi, qo'llanilishi). Shu bitta bazadan quyidagilar AVTOMATIK
# yasaladi:
#
#   1) O'rganish     — kartochkalar (formula + nom + qo'shimcha ma'lumot)
#   2) Test          — variantli savollar (chalg'ituvchilar shu bazadan)
#   3) Moslashtirish — formula <-> nom juftliklari, 6 tadan taxta
#   4) Yozish        — formulani klaviaturadan kiritish
#   5) Battle        — yuqoridagilarning aralashmasi
#
# Natijada 276 ta modda kiritilsa, o'n minglab savol variantlari o'z-o'zidan
# paydo bo'ladi va har safar boshqacha tartibda keladi.
#
# MUHIM: bu modul BAZAGA MUROJAAT QILMAYDI — unga tayyor modda ro'yxati
# (dict'lar) beriladi. Shu sababli uni testlash oson va u har qanday
# kontekstda (level o'yini, battle, chempionat) qayta ishlatiladi.

import random
import re
import unicodedata

# Savol turlari — mijoz (frontend) shu kalitlarga qarab UI tanlaydi.
Q_FORMULA_BY_NAME = "formula_by_name"     # "sulfat kislota" -> H2SO4
Q_NAME_BY_FORMULA = "name_by_formula"     # H2SO4 -> "sulfat kislota"
Q_COLOR_PURE = "color_pure"               # moddaning sof holdagi rangi
Q_COLOR_SOLUTION = "color_solution"       # eritmadagi rangi
Q_PRECIPITATE = "precipitate"             # cho'kma rangi
Q_HISTORIC = "historic_name"              # tarixiy (xalq) nomi

# Har bir savol turining sarlavhasi va savol matni.
_Q_META = {
    Q_FORMULA_BY_NAME: ("MODDA NOMI", "Bu moddaning formulasi qanday?"),
    Q_NAME_BY_FORMULA: ("FORMULA", "Bu qaysi modda?"),
    Q_COLOR_PURE: ("SOF HOLDAGI RANGI", "Bu moddaning sof holdagi rangi qanday?"),
    Q_COLOR_SOLUTION: ("ERITMADAGI RANGI", "Bu moddaning eritmadagi rangi qanday?"),
    Q_PRECIPITATE: ("CHO'KMA", "Bu moddaning cho'kmasi qanday rangda?"),
    Q_HISTORIC: ("TARIXIY NOMI", "Bu modda xalq orasida qanday nomlanadi?"),
}


# --------------------------------------------------------------------------
#  Formulani solishtirish (Yozish bosqichi uchun)
# --------------------------------------------------------------------------

# Yuqori/pastki indeks belgilarini oddiy raqamga aylantirish jadvali.
# O'quvchi telefonda "H₂SO₄" ni ham, "H2SO4" ni ham yozishi mumkin —
# ikkalasi ham to'g'ri hisoblanishi kerak.
_SUBSCRIPT_MAP = str.maketrans({
    "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
    "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
    "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
    "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
})


def normalize_formula(text: str) -> str:
    """Formulani solishtirishga tayyorlaydi.

    Nima qiladi:
      - yuqori/pastki indekslarni oddiy raqamga aylantiradi (H₂O -> H2O)
      - bo'sh joy, nuqta va tirelarni olib tashlaydi
      - lotin/kirill ko'rinishidagi bir xil harflarni birlashtiradi

    Nima QILMAYDI: katta-kichik harfni o'zgartirmaydi. Kimyoda bu MUHIM —
    "CO" (uglerod oksidi) va "Co" (kobalt) butunlay boshqa moddalar.
    """
    if not text:
        return ""
    s = unicodedata.normalize("NFKC", str(text))
    s = s.translate(_SUBSCRIPT_MAP)
    # Kirill klaviaturasida tasodifan yozilishi mumkin bo'lgan harflar.
    s = s.translate(str.maketrans({
        "А": "A", "В": "B", "С": "C", "Е": "E", "Н": "H", "К": "K",
        "М": "M", "О": "O", "Р": "P", "Т": "T", "Х": "X",
        "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x",
    }))
    s = re.sub(r"[\s·•\-–—_]", "", s)
    return s


def check_write_answer(user_answer: str, correct_formula: str) -> bool:
    """Yozish bosqichida javobni tekshiradi."""
    return bool(normalize_formula(user_answer)) and \
        normalize_formula(user_answer) == normalize_formula(correct_formula)


# --------------------------------------------------------------------------
#  Yordamchilar
# --------------------------------------------------------------------------

def _val(sub: dict, field: str):
    """Maydon qiymatini oladi; bo'sh yoki "yo'q" bo'lsa None qaytaradi.

    Baza bosqichma-bosqich to'ldiriladi: avval formula+nom, keyin ranglar.
    To'ldirilmagan maydondan savol yasamaslik kerak — aks holda o'quvchiga
    "javobi yo'q" savol chiqadi.
    """
    v = (sub.get(field) or "").strip()
    if not v or v.lower() in ("yo'q", "yoq", "-", "—", "none"):
        return None
    return v


def _pick_distractors(correct, pool_values, count=3):
    """Chalg'ituvchi variantlar: shu bazadagi BOSHQA haqiqiy qiymatlar.

    Nega tasodifiy matn emas: haqiqiy moddalarning formulalari chalg'ituvchi
    sifatida ancha foydali — o'quvchi "shunga o'xshash, lekin boshqa" ni
    ajratishni o'rganadi. Aynan shu ta'lim qiymatini beradi.
    """
    others = [v for v in set(pool_values) if v and v != correct]
    random.shuffle(others)
    return others[:count]


def _make_mcq(prompt_label, prompt_value, question_text, correct, distractors,
              q_type, substance_id):
    """Variantli savolni yig'adi va variantlarni aralashtiradi."""
    options = [correct] + list(distractors)
    random.shuffle(options)
    return {
        "type": q_type,
        "substance_id": substance_id,
        "prompt_label": prompt_label,
        "prompt_value": prompt_value,
        "question_text": question_text,
        "options": options,
        "correct_index": options.index(correct),
        "correct_answer": correct,
    }


# --------------------------------------------------------------------------
#  1-bosqich — O'RGANISH (kartochkalar)
# --------------------------------------------------------------------------

def build_learn_cards(substances):
    """Har modda uchun bitta kartochka.

    Kartochkada formula va nom asosiy o'rinda; rang/cho'kma/tarixiy nom
    esa "qo'shimcha" ro'yxatida — o'quvchi bosib ko'rishi mumkin.
    """
    cards = []
    for s in substances:
        extras = []
        for field, label in (
            ("historic_name", "Tarixiy nomi"),
            ("color_pure", "Sof holda"),
            ("color_solution", "Eritmada"),
            ("color_precipitate", "Cho'kma"),
            ("usage_text", "Qo'llanilishi"),
        ):
            v = _val(s, field)
            if v:
                extras.append({"label": label, "value": v})
        cards.append({
            "substance_id": s["id"],
            "formula": s["formula"],
            "name": s["name"],
            "extras": extras,
        })
    return cards


# --------------------------------------------------------------------------
#  2-bosqich — TEST (variantli savollar)
# --------------------------------------------------------------------------

def build_test_questions(substances, pool=None, per_substance=1, shuffle=True):
    """Har modda uchun variantli savol(lar).

    `pool` — chalg'ituvchi variantlarni olish uchun kengroq ro'yxat (odatda
    butun kategoriya). Berilmasa, shu levelning o'zidan olinadi.
    """
    pool = pool or substances
    formulas = [p["formula"] for p in pool]
    names = [p["name"] for p in pool]

    questions = []
    for s in substances:
        variants = _substance_question_variants(s, pool, formulas, names)
        if not variants:
            continue
        random.shuffle(variants)
        questions.extend(variants[:max(1, per_substance)])

    if shuffle:
        random.shuffle(questions)
    return questions


def _substance_question_variants(s, pool, formulas, names):
    """Bitta moddadan yasash MUMKIN bo'lgan barcha savollar.

    Qaysi savol yasalishi bazaning to'ldirilganiga bog'liq: rang kiritilmagan
    bo'lsa rang savoli yo'q. Shuning uchun bazani to'ldirgan sari savollar
    xilma-xilligi o'z-o'zidan ortadi.
    """
    out = []

    # a) Nom -> formula (eng asosiy tur)
    d = _pick_distractors(s["formula"], formulas)
    if len(d) >= 2:
        out.append(_make_mcq(_Q_META[Q_FORMULA_BY_NAME][0], s["name"],
                             _Q_META[Q_FORMULA_BY_NAME][1],
                             s["formula"], d, Q_FORMULA_BY_NAME, s["id"]))

    # b) Formula -> nom (teskari yo'nalish — eslab qolishni mustahkamlaydi)
    d = _pick_distractors(s["name"], names)
    if len(d) >= 2:
        out.append(_make_mcq(_Q_META[Q_NAME_BY_FORMULA][0], s["formula"],
                             _Q_META[Q_NAME_BY_FORMULA][1],
                             s["name"], d, Q_NAME_BY_FORMULA, s["id"]))

    # c) Rang va cho'kma savollari — faqat baza to'ldirilgan bo'lsa
    for field, q_type in (
        ("color_pure", Q_COLOR_PURE),
        ("color_solution", Q_COLOR_SOLUTION),
        ("color_precipitate", Q_PRECIPITATE),
    ):
        correct = _val(s, field)
        if not correct:
            continue
        pool_vals = [_val(p, field) for p in pool]
        d = _pick_distractors(correct, [v for v in pool_vals if v])
        if len(d) >= 2:
            out.append(_make_mcq(_Q_META[q_type][0], s["formula"],
                                 _Q_META[q_type][1], correct, d, q_type, s["id"]))

    # d) Tarixiy nom
    hist = _val(s, "historic_name")
    if hist:
        pool_vals = [_val(p, "historic_name") for p in pool]
        d = _pick_distractors(hist, [v for v in pool_vals if v])
        if len(d) >= 2:
            out.append(_make_mcq(_Q_META[Q_HISTORIC][0], s["formula"],
                                 _Q_META[Q_HISTORIC][1], hist, d, Q_HISTORIC, s["id"]))

    return out


# --------------------------------------------------------------------------
#  3-bosqich — MOSLASHTIRISH (juftlash taxtalari)
# --------------------------------------------------------------------------

def build_match_boards(substances, per_board=6):
    """Moddalarni 6 tadan taxtalarga bo'ladi.

    Nega 6 ta: 12 juftlikni bitta ekranda ko'rsatish telefonda o'qib
    bo'lmas darajada siqilib ketadi. 6 juftlik — barmoq bilan bosishga
    qulay va bir qarashda qamrab olinadigan hajm.
    """
    items = list(substances)
    random.shuffle(items)
    boards = []
    for i in range(0, len(items), per_board):
        chunk = items[i:i + per_board]
        if len(chunk) < 2:
            # Bitta modda qolsa — oldingi taxtaga qo'shib yuboramiz.
            if boards:
                chunk = boards.pop()["_raw"] + chunk
            else:
                continue
        left = [{"substance_id": s["id"], "text": s["formula"]} for s in chunk]
        right = [{"substance_id": s["id"], "text": s["name"]} for s in chunk]
        random.shuffle(left)
        random.shuffle(right)
        boards.append({"left": left, "right": right, "_raw": chunk})

    for b in boards:
        b.pop("_raw", None)
    return boards


# --------------------------------------------------------------------------
#  4-bosqich — YOZISH (formulani kiritish)
# --------------------------------------------------------------------------

def build_write_questions(substances, shuffle=True):
    """Nom beriladi — o'quvchi formulani o'zi yozadi.

    `hint` — birinchi belgi va uzunlik: o'quvchi butunlay qotib qolmasin.
    To'g'ri javob mijozga YUBORILMAYDI, tekshiruv serverda bo'ladi.
    """
    out = []
    for s in substances:
        formula = s["formula"] or ""
        out.append({
            "type": "write_formula",
            "substance_id": s["id"],
            "prompt_label": "MODDA NOMI",
            "prompt_value": s["name"],
            "question_text": "Bu moddaning formulasini yozing",
            "hint": {
                "first_char": formula[:1],
                "length": len(normalize_formula(formula)),
            },
        })
    if shuffle:
        random.shuffle(out)
    return out


# --------------------------------------------------------------------------
#  5 — BATTLE savollari (aralash)
# --------------------------------------------------------------------------

def build_battle_questions(pool, count=10, q_types=None):
    """Battle uchun tez javob beriladigan variantli savollar.

    Battle'da faqat variantli savollar bo'ladi — chunki g'olib TEZLIK bilan
    aniqlanadi, klaviaturada yozish esa tezlikni o'lchashni adolatsiz qiladi
    (telefon klaviaturasi har xil).
    """
    if not pool:
        return []
    formulas = [p["formula"] for p in pool]
    names = [p["name"] for p in pool]

    candidates = []
    for s in random.sample(pool, min(len(pool), max(count * 3, 30))):
        for q in _substance_question_variants(s, pool, formulas, names):
            if q_types and q["type"] not in q_types:
                continue
            candidates.append(q)

    random.shuffle(candidates)

    # Bitta modda bo'yicha ikkita savol tushib qolmasligi uchun filtr.
    seen, out = set(), []
    for q in candidates:
        if q["substance_id"] in seen:
            continue
        seen.add(q["substance_id"])
        out.append(q)
        if len(out) >= count:
            break
    return out


def strip_answers(questions):
    """Mijozga yuborishdan oldin to'g'ri javobni olib tashlaydi.

    XAVFSIZLIK: `correct_index` brauzerga yuborilsa, o'quvchi uni
    developer tools orqali ko'rib qo'yishi mumkin. Shuning uchun javob
    faqat serverda qoladi va tekshiruv ham serverda bo'ladi.
    """
    safe = []
    for q in questions:
        item = {k: v for k, v in q.items()
                if k not in ("correct_index", "correct_answer")}
        safe.append(item)
    return safe
