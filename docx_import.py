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
# boshlanishi kifoya (katta-kichik harf farqi muhim emas). Savollar orasida
# bo'sh qator qoldirish shart emas, lekin o'qish uchun tavsiya etiladi.

import io
import re

QUESTION_RE = re.compile(r"^\s*\d+[\.\)]\s*(.*)$")
OPTION_RE = re.compile(r"^\s*([A-Da-d])[\.\)]\s*(.*)$")
ANSWER_RE = re.compile(r"^\s*javob\s*[:\-]?\s*([A-Da-d])\s*$", re.IGNORECASE)

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


class ParsedQuestion:
    def __init__(self, order_num):
        self.order_num = order_num
        self.question_text = ""
        self.options = {}
        self.correct_letter = None
        self.image_bytes = None
        self.image_content_type = None

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

    doc = Document(io.BytesIO(file_bytes))
    document_part = doc.part

    questions = []
    current = None
    order_counter = 0

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()

        q_match = QUESTION_RE.match(text) if text else None
        opt_match = OPTION_RE.match(text) if text else None
        ans_match = ANSWER_RE.match(text) if text else None

        if q_match:
            if current is not None:
                questions.append(current)
            order_counter += 1
            current = ParsedQuestion(order_counter)
            current.question_text = q_match.group(1).strip()
        elif current is not None and opt_match:
            letter = opt_match.group(1).upper()
            current.options[letter] = opt_match.group(2).strip()
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
