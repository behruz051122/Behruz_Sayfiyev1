# certificate_pdf.py
# O'quvchi biror kursni 100% tugatganda beriladigan PDF sertifikatni
# generatsiya qiladi. reportlab — sof Python kutubxona (tashqi binar
# (masalan wkhtmltopdf) talab qilmaydi), shuning uchun Railway kabi
# konteyner muhitida qo'shimcha sozlashsiz ishlaydi.

import io

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

# CHEMBIOX/loyihaning asosiy rang sxemasi (webapp/style.css bilan bir xil).
TEAL_DARK = HexColor("#0f5c56")
TEAL = HexColor("#0f766e")
TEAL_LIGHT = HexColor("#14b8a6")
GOLD = HexColor("#b8892b")
INK = HexColor("#0f172a")
INK_DIM = HexColor("#64748b")
CREAM = HexColor("#fbfaf7")


def generate_certificate_pdf(
    student_name: str,
    course_title: str,
    brand_name: str,
    certificate_number: str,
    issued_date: str,
) -> bytes:
    """Bitta sahifali (A4, landshaft) sertifikat PDF baytlarini qaytaradi."""
    buffer = io.BytesIO()
    width, height = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=landscape(A4))

    # ---- Fon ----
    c.setFillColor(CREAM)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # ---- Tashqi bezakli ramka ----
    margin = 14 * mm
    c.setStrokeColor(TEAL)
    c.setLineWidth(2.2)
    c.rect(margin, margin, width - 2 * margin, height - 2 * margin, fill=0, stroke=1)
    inner_margin = margin + 4 * mm
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.8)
    c.rect(inner_margin, inner_margin, width - 2 * inner_margin, height - 2 * inner_margin, fill=0, stroke=1)

    center_x = width / 2

    # ---- Brend nomi (yuqorida) ----
    c.setFillColor(TEAL_DARK)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(center_x, height - 34 * mm, brand_name.upper())
    c.setFillColor(INK_DIM)
    c.setFont("Helvetica", 9)
    c.drawCentredString(center_x, height - 40 * mm, "ONLINE TA'LIM PLATFORMASI")

    # ---- Sarlavha ----
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 34)
    c.drawCentredString(center_x, height - 58 * mm, "SERTIFIKAT")
    c.setFillColor(INK_DIM)
    c.setFont("Helvetica-Oblique", 10.5)
    c.drawCentredString(center_x, height - 65 * mm, "muvaffaqiyatli kurs yakunlanishi uchun beriladi")

    # ---- O'quvchi ismi ----
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(center_x, height - 85 * mm, student_name)

    # Ism ostidagi ingichka chiziq
    line_half = 55 * mm
    c.setStrokeColor(TEAL_LIGHT)
    c.setLineWidth(1)
    c.line(center_x - line_half, height - 89 * mm, center_x + line_half, height - 89 * mm)

    # ---- Tavsif matni ----
    c.setFillColor(INK_DIM)
    c.setFont("Helvetica", 11.5)
    c.drawCentredString(center_x, height - 100 * mm, "quyidagi kursni to'liq (100%) muvaffaqiyatli yakunlagani uchun ushbu sertifikat bilan taqdirlanadi:")

    # ---- Kurs nomi ----
    c.setFillColor(TEAL_DARK)
    c.setFont("Helvetica-Bold", 17)
    c.drawCentredString(center_x, height - 112 * mm, course_title)

    # ---- Pastki qism: sana / imzo / sertifikat raqami ----
    bottom_y = margin + 16 * mm
    col_left_x = margin + 30 * mm
    col_right_x = width - margin - 30 * mm

    c.setStrokeColor(INK_DIM)
    c.setLineWidth(0.6)
    c.line(col_left_x - 22 * mm, bottom_y + 8 * mm, col_left_x + 22 * mm, bottom_y + 8 * mm)
    c.setFillColor(INK)
    c.setFont("Helvetica", 9)
    c.drawCentredString(col_left_x, bottom_y + 3 * mm, issued_date)
    c.setFillColor(INK_DIM)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(col_left_x, bottom_y - 2.5 * mm, "BERILGAN SANA")

    c.setStrokeColor(INK_DIM)
    c.line(col_right_x - 22 * mm, bottom_y + 8 * mm, col_right_x + 22 * mm, bottom_y + 8 * mm)
    c.setFillColor(INK)
    c.setFont("Helvetica-Oblique", 11)
    c.drawCentredString(col_right_x, bottom_y + 3 * mm, brand_name)
    c.setFillColor(INK_DIM)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(col_right_x, bottom_y - 2.5 * mm, "O'QITUVCHI")

    # ---- O'rtadagi bezak muhr (oddiy doira + yulduzcha) ----
    seal_r = 11 * mm
    c.setFillColor(GOLD)
    c.circle(center_x, bottom_y + 3 * mm, seal_r, fill=1, stroke=0)
    c.setFillColor(CREAM)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(center_x, bottom_y + 3 * mm - 5.5, "★")

    # ---- Sertifikat raqami (eng pastda, kichik) ----
    c.setFillColor(INK_DIM)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(center_x, margin + 5 * mm, f"Sertifikat raqami: {certificate_number}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()
