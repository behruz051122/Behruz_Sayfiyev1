# bio_questions.py
# ==========================================================================
#  BIOLOGIYA O'YINI — SAVOL GENERATORI
# ==========================================================================
# Kimyodagi kabi, o'qituvchi SAVOL YOZMAYDI — u TERMIN, KETMA-KETLIK va
# RASM kiritadi. Lekin biologiyada ma'lumot turli shaklda bo'lgani uchun
# bu yerda 7 xil o'yin bor (kimyoda 4 ta edi):
#
#   1) learn     — kartochka (termin + ta'rif + vazifa + qiziqarli fakt)
#   2) test      — variantli savol
#   3) match     — termin va ta'rifni juftlash
#   4) sequence  — jarayon bosqichlarini TARTIBGA SOLISH        (yangi)
#   5) group     — elementlarni GURUHLARGA ajratish             (yangi)
#   6) whoami    — ipuchalarga qarab topish, ball kamayib boradi (yangi)
#   7) image     — rasmdagi qismlarni belgilash                 (yangi)
#
# Bu modul BAZAGA MUROJAAT QILMAYDI — unga tayyor dict'lar beriladi.

import random

# Savol turlari
Q_DEF_BY_TERM = "definition_by_term"     # "Mitoxondriya" -> ta'rifi
Q_TERM_BY_DEF = "term_by_definition"     # ta'rif -> "Mitoxondriya"
Q_FUNC_BY_TERM = "function_by_term"      # "Ribosoma" -> vazifasi
Q_TERM_BY_FUNC = "term_by_function"      # vazifa -> "Ribosoma"
Q_GROUP_BY_TERM = "group_by_term"        # "Bakteriya" -> "Prokariot"

_Q_META = {
    Q_DEF_BY_TERM:  ("TERMIN", "Bu nima?"),
    Q_TERM_BY_DEF:  ("TA'RIF", "Bu qaysi termin?"),
    Q_FUNC_BY_TERM: ("TERMIN", "Uning asosiy vazifasi nima?"),
    Q_TERM_BY_FUNC: ("VAZIFA", "Bu vazifani kim bajaradi?"),
    Q_GROUP_BY_TERM: ("TERMIN", "U qaysi guruhga kiradi?"),
}


def _val(item: dict, field: str):
    """Bo'sh yoki "yo'q" qiymatni None qiladi — bo'sh maydondan savol
    yasalmasligi uchun (baza bosqichma-bosqich to'ldiriladi)."""
    v = (item.get(field) or "")
    v = v.strip() if isinstance(v, str) else v
    if not v or (isinstance(v, str) and v.lower() in ("yo'q", "yoq", "-", "—", "none")):
        return None
    return v


def _distractors(correct, pool_values, count=3):
    """Chalg'ituvchi variantlar — shu bazadagi BOSHQA haqiqiy qiymatlar.

    Biologiyada bu ayniqsa muhim: "mitoxondriya" ga qarshi "ribosoma" va
    "lizosoma" qo'yilsa, o'quvchi ularni ajratishni o'rganadi. Tasodifiy
    matn bunday ta'lim qiymatini bermaydi.
    """
    others = [v for v in dict.fromkeys(pool_values) if v and v != correct]
    random.shuffle(others)
    return others[:count]


def _mcq(label, prompt, question, correct, distractors, q_type, term_id):
    options = [correct] + list(distractors)
    random.shuffle(options)
    return {
        "type": q_type, "term_id": term_id,
        "prompt_label": label, "prompt_value": prompt,
        "question_text": question,
        "options": options,
        "correct_index": options.index(correct),
        "correct_answer": correct,
    }


# --------------------------------------------------------------------------
#  1. O'RGANISH — kartochkalar
# --------------------------------------------------------------------------

def build_learn_cards(terms):
    """Har termin uchun kartochka.

    Kartochkada termin katta, ta'rif ostida, qolgan ma'lumotlar
    "qo'shimcha" ro'yxatida — o'quvchi bir qarashda asosiyni oladi.
    """
    cards = []
    for t in terms:
        extras = []
        for field, label in (
            ("function_text", "Vazifasi"),
            ("group_name", "Guruhi"),
            ("extra_fact", "Qiziqarli fakt"),
        ):
            v = _val(t, field)
            if v:
                extras.append({"label": label, "value": v})
        cards.append({
            "term_id": t["id"],
            "term": t["term"],
            "definition": _val(t, "definition") or "",
            "image_url": _val(t, "image_url"),
            "extras": extras,
        })
    return cards


# --------------------------------------------------------------------------
#  2. TEST — variantli savollar
# --------------------------------------------------------------------------

def _term_variants(t, pool):
    """Bitta termindan yasash mumkin bo'lgan barcha savollar."""
    out = []
    terms = [x["term"] for x in pool]
    defs = [_val(x, "definition") for x in pool]
    funcs = [_val(x, "function_text") for x in pool]
    groups = [_val(x, "group_name") for x in pool]

    definition = _val(t, "definition")
    if definition:
        d = _distractors(definition, [v for v in defs if v])
        if len(d) >= 2:
            out.append(_mcq(_Q_META[Q_DEF_BY_TERM][0], t["term"],
                            _Q_META[Q_DEF_BY_TERM][1], definition, d,
                            Q_DEF_BY_TERM, t["id"]))
        d = _distractors(t["term"], terms)
        if len(d) >= 2:
            out.append(_mcq(_Q_META[Q_TERM_BY_DEF][0], definition,
                            _Q_META[Q_TERM_BY_DEF][1], t["term"], d,
                            Q_TERM_BY_DEF, t["id"]))

    function = _val(t, "function_text")
    if function:
        d = _distractors(function, [v for v in funcs if v])
        if len(d) >= 2:
            out.append(_mcq(_Q_META[Q_FUNC_BY_TERM][0], t["term"],
                            _Q_META[Q_FUNC_BY_TERM][1], function, d,
                            Q_FUNC_BY_TERM, t["id"]))
        d = _distractors(t["term"], terms)
        if len(d) >= 2:
            out.append(_mcq(_Q_META[Q_TERM_BY_FUNC][0], function,
                            _Q_META[Q_TERM_BY_FUNC][1], t["term"], d,
                            Q_TERM_BY_FUNC, t["id"]))

    group = _val(t, "group_name")
    if group:
        d = _distractors(group, [v for v in groups if v])
        # Guruh savoli faqat kamida 3 xil guruh bo'lsa mazmunli bo'ladi.
        if len(d) >= 2:
            out.append(_mcq(_Q_META[Q_GROUP_BY_TERM][0], t["term"],
                            _Q_META[Q_GROUP_BY_TERM][1], group, d,
                            Q_GROUP_BY_TERM, t["id"]))
    return out


def build_test_questions(terms, pool=None, per_term=1, shuffle=True):
    pool = pool or terms
    questions = []
    for t in terms:
        variants = _term_variants(t, pool)
        if not variants:
            continue
        random.shuffle(variants)
        questions.extend(variants[:max(1, per_term)])
    if shuffle:
        random.shuffle(questions)
    return questions


# --------------------------------------------------------------------------
#  3. JUFTLASH
# --------------------------------------------------------------------------

def build_match_boards(terms, per_board=5):
    """Termin <-> ta'rif juftliklari.

    Nega 5 ta (kimyoda 6 edi): biologiya ta'riflari uzunroq, telefonda
    6 ta juftlik ekranga sig'maydi va o'quvchi aylantirib o'tirishga
    majbur bo'ladi.
    """
    usable = [t for t in terms if _val(t, "definition")]
    random.shuffle(usable)
    boards = []
    for i in range(0, len(usable), per_board):
        chunk = usable[i:i + per_board]
        if len(chunk) < 2:
            if boards:
                # Yolg'iz qolganini oldingi taxtaga qo'shamiz.
                prev = boards[-1]
                for t in chunk:
                    prev["left"].append({"term_id": t["id"], "text": t["term"]})
                    prev["right"].append({"term_id": t["id"], "text": _val(t, "definition")})
                random.shuffle(prev["right"])
            continue
        left = [{"term_id": t["id"], "text": t["term"]} for t in chunk]
        right = [{"term_id": t["id"], "text": _val(t, "definition")} for t in chunk]
        random.shuffle(left)
        random.shuffle(right)
        boards.append({"left": left, "right": right})
    return boards


# --------------------------------------------------------------------------
#  4. KETMA-KETLIK  (yangi)
# --------------------------------------------------------------------------

def build_sequence_tasks(sequences):
    """Jarayon bosqichlarini aralashtirib beradi.

    To'g'ri tartib mijozga YUBORILMAYDI — tekshiruv serverda bo'ladi.
    Aks holda o'quvchi javobni ko'rib qo'yardi.

    Aralashtirish "haqiqatan aralash" bo'lishi kafolatlanadi: tasodifan
    to'g'ri tartib chiqib qolsa, qayta aralashtiriladi.
    """
    tasks = []
    for s in sequences:
        steps = list(s.get("steps") or [])
        if len(steps) < 2:
            continue
        shuffled = steps[:]
        for _ in range(12):
            random.shuffle(shuffled)
            if shuffled != steps:
                break
        tasks.append({
            "sequence_id": s["id"],
            "title": s["title"],
            "description": s.get("description") or "",
            "shuffled_steps": shuffled,
            "step_count": len(steps),
        })
    return tasks


def check_sequence(user_order, correct_steps) -> dict:
    """Foydalanuvchi tartibini tekshiradi.

    Faqat "to'g'ri/xato" emas, NECHTASI JOYIDA ekanini ham qaytaradi —
    o'quvchi qayerda xato qilganini ko'radi va bu o'rganishga yordam beradi.
    """
    user_order = [str(x).strip() for x in (user_order or [])]
    correct = [str(x).strip() for x in (correct_steps or [])]
    in_place = sum(1 for i, s in enumerate(user_order)
                   if i < len(correct) and s == correct[i])
    return {
        "correct": user_order == correct,
        "in_place": in_place,
        "total": len(correct),
        "correct_order": correct,
    }


# --------------------------------------------------------------------------
#  5. GURUHLASH  (yangi)
# --------------------------------------------------------------------------

def build_group_task(terms, max_items=12):
    """Elementlarni savatlarga ajratish topshirig'i.

    Guruhlar terminlarning `group_name` maydonidan olinadi. Kamida
    2 xil guruh bo'lishi shart — aks holda o'yin mazmunsiz.
    """
    grouped = {}
    for t in terms:
        g = _val(t, "group_name")
        if g:
            grouped.setdefault(g, []).append(t)
    if len(grouped) < 2:
        return None

    # Har guruhdan teng miqdorda olamiz — biror guruh ustunlik qilmasin,
    # aks holda o'quvchi "hammasini shu savatga tashlayman" deb topib oladi.
    per_group = max(1, max_items // len(grouped))
    items = []
    for g, lst in grouped.items():
        random.shuffle(lst)
        for t in lst[:per_group]:
            items.append({"term_id": t["id"], "text": t["term"], "group": g})
    random.shuffle(items)

    return {
        "groups": sorted(grouped.keys()),
        "items": [{"term_id": i["term_id"], "text": i["text"]} for i in items],
        "answer_key": {str(i["term_id"]): i["group"] for i in items},
        "total": len(items),
    }


# --------------------------------------------------------------------------
#  6. "KIM MEN?"  (yangi)
# --------------------------------------------------------------------------

WHOAMI_MAX_POINTS = 4     # birinchi ipuchada topsa — 4 ball


def build_whoami_tasks(terms, pool=None, shuffle=True):
    """Ipuchalar ketma-ket ochiladi, ball kamayib boradi.

    Ipuchalar UMUMIYDAN ANIQQA tartibda beriladi (o'qituvchi shunday
    yozadi). Shuning uchun ular ARALASHTIRILMAYDI — aks holda birinchi
    ipucha javobni oshkor qilib qo'yishi mumkin.
    """
    pool = pool or terms
    all_terms = [x["term"] for x in pool]
    tasks = []
    for t in terms:
        clues = [c for c in (t.get("clues") or []) if str(c).strip()]
        if not clues:
            continue
        options = [t["term"]] + _distractors(t["term"], all_terms, count=3)
        if len(options) < 3:
            continue
        random.shuffle(options)
        tasks.append({
            "term_id": t["id"],
            "clues": clues,
            "options": options,
            "max_points": WHOAMI_MAX_POINTS,
        })
    if shuffle:
        random.shuffle(tasks)
    return tasks


def whoami_points(clue_index: int, max_points: int = WHOAMI_MAX_POINTS) -> int:
    """Nechanchi ipuchada topgani bo'yicha ball (1 dan kam bo'lmaydi)."""
    return max(1, max_points - int(clue_index))


# --------------------------------------------------------------------------
#  7. RASM BO'YICHA BELGILASH  (yangi)
# --------------------------------------------------------------------------

def build_image_tasks(tasks):
    """Rasmdagi nuqtalarni belgilash.

    Mijozga nuqtalarning koordinatalari beriladi (ularni ko'rsatish
    kerak), lekin QAYSI NUQTA QAYSI NOM ekani ARALASHTIRILGAN holda —
    o'quvchi mos nomni tanlaydi. To'g'ri javob serverda tekshiriladi.
    """
    out = []
    for t in tasks:
        labels = [l for l in (t.get("labels") or [])
                  if isinstance(l, dict) and l.get("name")]
        if not labels:
            continue
        points = [{"index": i, "x": l.get("x", 50), "y": l.get("y", 50)}
                  for i, l in enumerate(labels)]
        names = [l["name"] for l in labels]
        shuffled_names = names[:]
        random.shuffle(shuffled_names)
        out.append({
            "task_id": t["id"],
            "title": t["title"],
            "image_url": t["image_url"],
            "points": points,
            "names": shuffled_names,
            "total": len(labels),
        })
    return out


def check_image_answer(task_labels, point_index: int, name: str) -> bool:
    """Nuqta va nom mos kelishini tekshiradi."""
    labels = task_labels or []
    if not (0 <= int(point_index) < len(labels)):
        return False
    expected = (labels[int(point_index)].get("name") or "").strip().lower()
    return expected == (name or "").strip().lower()


# --------------------------------------------------------------------------
#  Umumiy
# --------------------------------------------------------------------------

def strip_answers(questions):
    """To'g'ri javobni mijozga yubormaslik uchun tozalaydi."""
    return [{k: v for k, v in q.items()
             if k not in ("correct_index", "correct_answer", "answer_key")}
            for q in questions]
