# pdf_generator.py - Генерация PDF отчетов
"""
Модуль для формирования PDF заказа с использованием reportlab.
"""

import os
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from config import DatabaseConfig, FontConfig, Config


class PDFGenerator:
    """Класс для создания PDF отчетов по заказам"""

    @staticmethod
    def generate(order_id, total_cost, order_details, requirements, instructions_text):
        """Генерирует PDF файл для заказа"""
        # Настройка папки
        orders_dir = DatabaseConfig.get_orders_dir()
        filename = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_order_{order_id}.pdf"
        filepath = os.path.join(orders_dir, filename)

        # Настройка документа
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()

        # При наличии Arial используем его
        if FontConfig.setup_arial_font():
            title_style = ParagraphStyle(
                'Title', parent=styles['Title'], fontName=FontConfig.ARIAL_FONT_NAME,
                fontSize=Config.PDF_FONT_SIZE_TITLE
            )
            heading_style = ParagraphStyle(
                'Heading', parent=styles['Heading2'], fontName=FontConfig.ARIAL_FONT_NAME,
                fontSize=Config.PDF_FONT_SIZE_HEADING
            )
            normal_style = ParagraphStyle(
                'Normal', parent=styles['Normal'], fontName=FontConfig.ARIAL_FONT_NAME,
                fontSize=Config.PDF_FONT_SIZE_NORMAL
            )
        else:
            title_style = styles['Title']
            heading_style = styles['Heading2']
            normal_style = styles['Normal']

        # Сборка содержимого
        story = []
        story.append(Paragraph(f"Заказ №{order_id} от {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", title_style))
        story.append(Spacer(1, 12))

        # Стоимости
        story.append(Paragraph(f"Себестоимость: {total_cost:.2f} руб", heading_style))
        story.append(Paragraph(f"Цена реализации: {total_cost * Config.SALE_PRICE_MULTIPLIER:.2f} руб", heading_style))
        story.append(Spacer(1, 12))

        # Состав заказа
        story.append(Paragraph("Состав заказа:", heading_style))
        for item in order_details:
            type_, id_, name, qty, cost, length = item
            line = f"- {name} ({'Изделие' if type_=='product' else 'Этап'}): {qty}"
            if type_=='stage' and length:
                line += f", длина {length:.2f} м"
            line += f" - {cost:.2f} руб"
            story.append(Paragraph(line, normal_style))

        story.append(Spacer(1, 12))
        story.append(Paragraph("Сводка материалов:", heading_style))
        # Агрегированный список
        lumber = {}
        fasteners = {}
        material_types = {name:type_ for name,type_ in fetch_material_types()}  # helper
        for name, reqs in requirements.items():
            total = sum(r[0] for r in reqs)
            if material_types.get(name)=='Пиломатериал':
                lumber[name] = total
            else:
                fasteners[name] = total
        if lumber:
            story.append(Paragraph("Пиломатериалы:", normal_style))
            for m, v in lumber.items():
                story.append(Paragraph(f"• {m}: {v:.2f} м", normal_style))
        if fasteners:
            story.append(Paragraph("Метизы:", normal_style))
            for m, v in fasteners.items():
                story.append(Paragraph(f"• {m}: {v:.0f} шт", normal_style))

        story.append(Spacer(1, 12))
        story.append(Paragraph("Инструкции распила:", heading_style))
        story.append(Paragraph(instructions_text.replace('\n','<br/>'), normal_style))

        # Сохраняем PDF
        doc.build(story)
        return filepath


def fetch_material_types():
    """Вспомогательная функция для получения типов материалов из БД"""
    from utils import fetch_all
    rows = fetch_all("SELECT name,type FROM materials")
    return [(r['name'], r['type']) for r in rows]