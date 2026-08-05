# docx_import.py
# Word (.docx) fayldan savollarni ommaviy o'qib olish.
#
# KUTILADIGAN SHABLON (har bir savol shu formatda yoziladi):
#
#   1. Savol matni shu yerga yoziladi?
#   (agar kerak bo'lsa, aynan shu yerga — savol bilan variantlar orasiga —
#   rasm/jadval/grafik joylashtiring: Word'da "Ilova -> Rasm" yoki
#   "Ilova -> Jadval" orqali)
#   A) birinchi variant
#   B) ikkinchi variant
#   C) uchinchi variant
#   D) to'rtinchi variant
#   Javob: B
#
# Savol raqami "1." yoki "1)" bilan, variantlar "A)" yoki "A." bilan
# boshlanishi kifoya (katta-kichik harf farqi muhim emas). "To'g'ri javob-B"
# yoki "Javob:B" kabi variantlar ham qo'llab-quvvatlanadi. Agar 4 ta variant
# bitta qatorda (masalan jadval ustunlaridek tab bilan ajratilgan) yozilgan
# bo'lsa, bu ham avtomatik ajratib olinadi. Word jadvallari (haqiqiy
# "Insert -> Table" orqali qo'yilgan) ham o'qiladi va ASL katak-katak
# ko'rinishida (matn shaklida emas) ilovada ko'rsatiladi.
#
# QULAY USUL — YASHIL RANG BILAN JAVOB BELGILASH:
# "Javob: B" qatorini har safar qo'lda yozish o'rniga, to'g'ri variantning
# MATNINI (yoki harfini) Word'da YASHIL rangga bo'yab qo'ysangiz ham bo'ladi
# — dastur buni avtomatik tanib, to'g'ri javob sifatida oladi. Agar bitta
# savolda ham yashil belgilash, ham "Javob:" qatori bo'lsa — YASHIL rang
# ustuvor hisoblanadi (chunki "Javob:" qatori ko'pincha shablondan
# nusxalanib, xato holda bir xil harfda qolib ketishi mumkin).

import io
import json
import re

QUESTION_RE = re.compile(r"^\s*(\d+)[\.\)]\s*(.*)$")
OPTION_RE = re.compile(r"^\s*[A-Da-d][\.\)]")
MULTI_OPTION_RE = re.compile(r"([A-Da-d])[\.\)]\s*")
# ANSWER_RE endi qatorning BOSHIDA emas, ISTALGAN joyida "javob" so'zini
# qidiradi ("To'g'ri javob-B", "Javob: B", "javob - b" barchasi mos keladi) —
# faqat qator harf bilan tugashi kerak.
ANSWER_RE = re.compile(r"javob\s*[:\-]?\s*([A-Da-d])\s*$", re.IGNORECASE)

BLIP_TAG = "{http://schemas.openxmlformats.org/drawingml/2006/main}blip"
REL_EMBED_ATTR = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"

# Word'da rasm qo'yilganda ko'pincha ishlatiladigan format(lar) — <img> tegida
# to'g'ridan-to'g'ri ko'rsatib bo'ladiganlari. EMF/WMF kabi vektor formatlar
# brauzerda ochilmaydi, shu sababli ularni o'tkazib yuboramiz (savol matni va
# variantlar baribir to'g'ri qo'shiladi, faqat rasmsiz).
IMAGE_EXT_BY_CONTENT_TYPE = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def _extract_images(paragraph, document_part):
    """Paragraf ichidagi rasmlarni (bytes, content_type) ro'yxati sifatida qaytaradi."""
    images = []
    for blip in paragraph._p.findall(".//" + BLIP_TAG):
        rId = blip.get(REL_EMBED_ATTR)
        if not rId:
            continue
        try:
            part = document_part.related_parts[rId]
            images.append((part.blob, part.content_type))
        except KeyError:
            continue
    return images


def _is_greenish_rgb(rgb) -> bool:
    """RGBColor qiymati yashil ranga o'xshaydimi tekshiradi. Word'da standart
    "Green" (00B050), "Light Green" (92D050) kabi turli xil yashil ranglar
    ishlatilishi mumkin — aniq bitta qiymatni emas, "yashil kanal qizil va
    ko'k kanallardan sezilarli yuqori" evristikasini qo'llaymiz."""
    if rgb is None:
        return False
    try:
        r, g, b = rgb[0], rgb[1], rgb[2]
    except Exception:
        return False
    return g > 100 and g > r + 30 and g > b + 30


def _run_is_green(run) -> bool:
    """Run (matn bo'lagi) YASHIL rangda yozilganmi yoki YASHIL fon bilan
    bo'yalganmi (highlight) tekshiradi — ikkala usul ham qo'llab-quvvatlanadi."""
    try:
        color = run.font.color
        if color is not None and color.type is not None and color.rgb is not None:
            if _is_greenish_rgb(color.rgb):
                return True
    except Exception:
        pass
    try:
        hl = run.font.highlight_color
        if hl is not None and "GREEN" in str(hl).upper():
            return True
    except Exception:
        pass
    return False


def _split_options_with_color(paragraph):
    """Bitta qatorda bitta YOKI bir nechta variant bo'lishi mumkin (masalan
    "A) 0   B) 25   C) 50   D) 75" — jadval ustunlaridek tab bilan ajratilgan).
    Paragraf RUN'lari (Word'dagi matn formatlash bo'laklari) orqali har bir
    variantning matnini VA shu variant YASHIL rang bilan belgilanganmi-
    yo'qmi aniqlaydi. Natija: {harf: {"text": ..., "green": bool}}"""
    runs_info = []
    pos = 0
    full_text = ""
    for run in paragraph.runs:
        t = run.text
        runs_info.append((pos, pos + len(t), run))
        full_text += t
        pos += len(t)

    matches = list(MULTI_OPTION_RE.finditer(full_text))
    if not matches:
        return {}

    result = {}
    for i, m in enumerate(matches):
        letter = m.group(1).upper()
        content_start = m.end()
        content_end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        content = full_text[content_start:content_end].strip(" \t")

        # Ranglash tekshiruvi harf belgisi ("B)")dan boshlab olinadi — chunki
        # ba'zi o'qituvchilar faqat harfni, ba'zilari butun variant matnini
        # yashil rangga bo'yaydi, ikkalasi ham hisobga olinishi kerak.
        color_start, color_end = m.start(), content_end
        is_green = any(
            _run_is_green(run)
            for r_start, r_end, run in runs_info
            if r_start < color_end and r_end > color_start
        )

        result[letter] = {"text": content, "green": is_green}
    return result


def _table_rows(table):
    """Haqiqiy Word jadvalini (Insert -> Table orqali qo'yilgan) qatorlar
    ro'yxati sifatida qaytaradi — matnga aylantirmasdan, ASL katak-katak
    tuzilishini saqlab qolish uchun (frontend buni haqiqiy <table> sifatida
    chizadi)."""
    rows = []
    for row in table.rows:
        cells = [c.text.strip() for c in row.cells]
        rows.append(cells)
    return rows


def _iter_block_items(document):
    """python-docx standart holda paragraflar (doc.paragraphs) va jadvallar
    (doc.tables) ni ALOHIDA, hujjatdagi HAQIQIY tartibini yo'qotib ro'yxat
    qiladi. Savol qaysi jadvalga tegishli ekanini bilish uchun bizga aniq
    hujjat tartibi kerak — shu funksiya har ikkalasini asl tartibda beradi."""
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    body = document.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


class ParsedQuestion:
    def __init__(self, order_num):
        self.order_num = order_num
        self.question_text = ""
        self.options = {}
        self.correct_letter = None   # "Javob: B" kabi MATN orqali ko'rsatilgan javob
        self.green_letter = None     # variant matni YASHIL rangda belgilangan bo'lsa
        self.image_bytes = None
        self.image_content_type = None
        self.table_data = None       # {"tables": [{"rows": [[...], ...]}, ...]}
        self.has_table = False

    @property
    def effective_correct_letter(self):
        """YASHIL rang bilan belgilash — "Javob:" qatoridan KO'RA ustuvor,
        chunki matn qatori ko'pincha shablondan nusxalanib, xato holda bir
        xil harfda qolib ketishi mumkin (o'qituvchining haqiqiy niyati odatda
        aynan YASHIL rangda ko'rinadi)."""
        return self.green_letter or self.correct_letter

    def is_complete(self) -> bool:
        letter = self.effective_correct_letter
        return (
            bool(self.question_text.strip())
            and len(self.options) == 4
            and letter in self.options
        )

    def missing_summary(self) -> str:
        problems = []
        if not self.question_text.strip():
            problems.append("savol matni yo'q")
        missing_opts = [l for l in "ABCD" if l not in self.options]
        if missing_opts:
            problems.append(f"variant(lar) yo'q: {', '.join(missing_opts)}")
        letter = self.effective_correct_letter
        if not letter:
            problems.append("to'g'ri javob ko'rsatilmagan (variantni YASHIL rangda belgilang yoki \"Javob: B\" kabi qator qo'shing)")
        elif letter not in self.options:
            problems.append(f"to'g'ri javob ({letter}) hech qanday variantga mos kelmadi")
        return "; ".join(problems) if problems else ""

    def table_data_json(self):
        return json.dumps(self.table_data, ensure_ascii=False) if self.table_data else None


def parse_docx(file_bytes: bytes):
    """
    .docx fayl baytlarini o'qib, ParsedQuestion obyektlari ro'yxatini qaytaradi.
    Har bir savol to'liq (is_complete()==True) yoki muammoli bo'lishi mumkin —
    chaqiruvchi (router) muammolilarni admin uchun aniq ko'rsatishi kerak.
    """
    from docx import Document
    from docx.table import Table

    doc = Document(io.BytesIO(file_bytes))
    document_part = doc.part

    questions = []
    current = None
    order_counter = 0
    # Savol matni ICHIDA "1) ...", "2) ..." kabi raqamlangan bandlar (masalan
    # "quyidagi ifodalardan qaysilari to'g'ri?" turidagi savollarda) bo'lishi
    # mumkin — bularni HAQIQIY yangi savol bilan adashtirmaslik uchun, raqam
    # faqat OLDINGI tasdiqlangan savol raqamidan KATTA bo'lsagina, uni yangi
    # savol deb hisoblaymiz ("aniq +1" talab qilinmaydi — real hujjatlarda
    # savol raqamlari orasida uzilish bo'lishi mumkin, masalan 11 dan keyin
    # to'g'ridan-to'g'ri 14 kelishi; lekin savol ICHIDAGI band deyarli
    # doim 1 dan qayta boshlanadi, shuning uchun "kattami" tekshiruvi
    # ikkalasini ham to'g'ri ajratadi).
    last_confirmed_number = None

    for block in _iter_block_items(doc):
        if isinstance(block, Table):
            if current is not None:
                current.has_table = True
                rows = _table_rows(block)
                if rows:
                    if current.table_data is None:
                        current.table_data = {"tables": []}
                    current.table_data["tables"].append({"rows": rows})
            continue

        paragraph = block
        text = paragraph.text.strip()

        q_match = QUESTION_RE.match(text) if text else None
        opt_match = OPTION_RE.match(text) if text else None
        ans_match = ANSWER_RE.search(text) if text else None

        is_new_question = False
        if q_match:
            found_num = int(q_match.group(1))
            if current is None or last_confirmed_number is None or found_num > last_confirmed_number:
                is_new_question = True

        if is_new_question:
            if current is not None:
                questions.append(current)
            order_counter += 1
            current = ParsedQuestion(order_counter)
            current.question_text = q_match.group(2).strip()
            last_confirmed_number = int(q_match.group(1))
        elif current is not None and opt_match:
            found = _split_options_with_color(paragraph)
            for letter, info in found.items():
                current.options[letter] = info["text"]
                if info["green"]:
                    current.green_letter = letter
        elif current is not None and ans_match:
            current.correct_letter = ans_match.group(1).upper()
        elif current is not None and text and not current.options:
            # Variant/javob qatoriga mos kelmagan, bo'sh bo'lmagan qator —
            # ko'p qatorli savol matnining davomi deb hisoblanadi (variantlar
            # boshlangandan keyingi izohli qatorlarga tegilmaydi).
            current.question_text = (current.question_text + " " + text).strip()

        if current is not None and current.image_bytes is None:
            imgs = _extract_images(paragraph, document_part)
            if imgs:
                current.image_bytes, current.image_content_type = imgs[0]

    if current is not None:
        questions.append(current)

    return questions
