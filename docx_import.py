# docx_import.py
# Word (.docx) fayldan savollarni ommaviy o'qib olish.
#
# KUTILADIGAN SHABLON (har bir savol shu formatda yoziladi):
#
#   1. Savol matni shu yerga yoziladi?
#   (agar kerak bo'lsa, aynan shu yerga — savol bilan variantlar orasiga —
#   rasm/jadval/grafik joylashtiring: Word'da "Ilova -> Rasm" orqali)
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
# "Insert -> Table" orqali qo'yilgan) ham o'qiladi va savol matniga qo'shimcha
# ma'lumot sifatida biriktiriladi.

import io
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


def _split_options_from_line(text: str):
    """Bitta qatorda bitta YOKI bir nechta variant bo'lishi mumkin (masalan
    "A) 0   B) 25   C) 50   D) 75" — jadval ustunlaridek tab bilan ajratilgan).
    Qatordagi barcha "HARF) matn" bo'laklarini topib, {harf: matn} qaytaradi."""
    matches = list(MULTI_OPTION_RE.finditer(text))
    if not matches:
        return {}
    result = {}
    for i, m in enumerate(matches):
        letter = m.group(1).upper()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip(" \t")
        result[letter] = content
    return result


def _table_to_text(table) -> str:
    """Haqiqiy Word jadvalini (Insert -> Table orqali qo'yilgan) o'qiladigan
    matn ko'rinishiga o'giradi — savol matniga qo'shimcha sifatida
    biriktiriladi (masalan davriy jadval ma'lumotlari, izotoplar foizi)."""
    lines = []
    for row in table.rows:
        cells = [c.text.strip().replace("\n", " ") for c in row.cells]
        lines.append(" | ".join(cells))
    return "\n".join(lines)


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
        self.correct_letter = None
        self.image_bytes = None
        self.image_content_type = None
        self.has_table = False

    def is_complete(self) -> bool:
        return (
            bool(self.question_text.strip())
            and len(self.options) == 4
            and self.correct_letter in self.options
        )

    def missing_summary(self) -> str:
        problems = []
        if not self.question_text.strip():
            problems.append("savol matni yo'q")
        missing_opts = [l for l in "ABCD" if l not in self.options]
        if missing_opts:
            problems.append(f"variant(lar) yo'q: {', '.join(missing_opts)}")
        if not self.correct_letter:
            problems.append("to'g'ri javob ko'rsatilmagan (\"Javob: B\" kabi qator kerak)")
        elif self.correct_letter not in self.options:
            problems.append(f"to'g'ri javob ({self.correct_letter}) hech qanday variantga mos kelmadi")
        return "; ".join(problems) if problems else ""


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
                table_text = _table_to_text(block)
                if table_text:
                    current.question_text = (current.question_text + "\n" + table_text).strip()
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
            found = _split_options_from_line(text)
            for letter, content in found.items():
                current.options[letter] = content
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
