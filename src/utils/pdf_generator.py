import os
import sys
from datetime import datetime
from collections import defaultdict
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm
import sqlite3


class PDFGenerator:
    """Класс для генерации PDF отчетов заказов"""

    def __init__(self, db_path):
        self.db_path = db_path
        self.arial_registered = self._register_arial_font()
        self.styles = self._setup_styles()

    def _register_arial_font(self):
        """Регистрация шрифта Arial для корректного отображения русского текста"""
        try:
            # Пытаемся найти шрифт Arial
            font_paths = []

            if getattr(sys, 'frozen', False):
                # Для скомпилированного приложения
                font_paths.append(os.path.join(os.path.dirname(sys.executable), 'fonts', 'arial.ttf'))
            else:
                # Для разработки
                font_paths.append(os.path.join(os.path.dirname(__file__), '..', 'fonts', 'arial.ttf'))

            # Системные пути к шрифтам
            if sys.platform == 'win32':
                font_paths.append('C:/Windows/Fonts/arial.ttf')
            elif sys.platform == 'darwin':
                font_paths.append('/System/Library/Fonts/Arial.ttf')
            else:
                font_paths.extend([
                    '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
                ])

            for font_path in font_paths:
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont('Arial', font_path))
                    return True

            return False

        except Exception as e:
            print(f"Ошибка регистрации шрифта: {str(e)}")
            return False

    def _setup_styles(self):
        """Настройка стилей для PDF документа"""
        base_styles = getSampleStyleSheet()

        if self.arial_registered:
            # Создаем кастомные стили с Arial
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=base_styles['Title'],
                fontName='Arial',
                fontSize=18,
                spaceAfter=20,
                alignment=1  # Центрирование
            )

            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=base_styles['Heading2'],
                fontName='Arial',
                fontSize=14,
                spaceAfter=12,
                spaceBefore=12
            )

            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=base_styles['Normal'],
                fontName='Arial',
                fontSize=11,
                spaceAfter=6
            )

            small_style = ParagraphStyle(
                'CustomSmall',
                parent=base_styles['Normal'],
                fontName='Arial',
                fontSize=9,
                spaceAfter=4
            )

        else:
            # Используем стандартные стили
            title_style = base_styles['Title']
            heading_style = base_styles['Heading2']
            normal_style = base_styles['Normal']
            small_style = ParagraphStyle(
                'Small',
                parent=base_styles['Normal'],
                fontSize=9
            )

        return {
            'title': title_style,
            'heading': heading_style,
            'normal': normal_style,
            'small': small_style
        }

    def generate_order_pdf(self, order_id, total_cost, order_details, requirements, instructions_text):
        """
        Генерирует PDF отчет для заказа

        Args:
            order_id: ID заказа
            total_cost: Общая себестоимость
            order_details: Список позиций заказа
            requirements: Требования к материалам
            instructions_text: Инструкции к заказу

        Returns:
            str: Путь к созданному PDF файлу
        """
        try:
            # Определяем путь для сохранения PDF
            pdf_path = self._get_pdf_path()
            pdf_filename = self._generate_filename(order_id)
            full_path = os.path.join(pdf_path, pdf_filename)

            # Обновляем информацию о PDF в базе данных
            self._update_order_pdf_filename(order_id, pdf_filename)

            # Создаем документ
            doc = SimpleDocTemplate(
                full_path,
                pagesize=A4,
                rightMargin=2 * cm,
                leftMargin=2 * cm,
                topMargin=2 * cm,
                bottomMargin=2 * cm
            )

            # Строим содержимое PDF
            story = self._build_pdf_content(
                order_id, total_cost, order_details, requirements, instructions_text
            )

            # Генерируем PDF
            doc.build(story)

            return full_path

        except Exception as e:
            raise Exception(f"Ошибка при генерации PDF: {str(e)}")

    def _get_pdf_path(self):
        """Получить путь для сохранения PDF файлов"""
        if getattr(sys, 'frozen', False):
            pdf_dir = os.path.join(os.path.dirname(sys.executable), 'orders')
        else:
            pdf_dir = os.path.join(os.path.dirname(self.db_path), 'orders')

        if not os.path.exists(pdf_dir):
            os.makedirs(pdf_dir)

        return pdf_dir

    def _generate_filename(self, order_id):
        """Генерация имени файла PDF"""
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        return f"order_{order_id}_{timestamp}.pdf"

    def _update_order_pdf_filename(self, order_id, filename):
        """Обновление информации о PDF файле в базе данных"""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE orders SET pdf_filename = ? WHERE id = ?",
                (filename, order_id)
            )
            conn.commit()
        finally:
            conn.close()

    def _build_pdf_content(self, order_id, total_cost, order_details, requirements, instructions_text):
        """Построение содержимого PDF документа"""
        story = []

        # Заголовок документа
        title_text = f"ЗАКАЗ №{order_id}"
        story.append(Paragraph(title_text, self.styles['title']))
        story.append(Spacer(1, 12))

        # Дата создания
        date_text = f"Дата создания: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        story.append(Paragraph(date_text, self.styles['normal']))
        story.append(Spacer(1, 20))

        # Информация о стоимости
        cost_heading = Paragraph("СТОИМОСТЬ ЗАКАЗА", self.styles['heading'])
        story.append(cost_heading)

        sale_price = total_cost * 2
        cost_text = f"Себестоимость: {total_cost:.2f} руб<br/>"
        cost_text += f"Цена реализации: {sale_price:.2f} руб<br/>"
        cost_text += f"Наценка: {sale_price - total_cost:.2f} руб (100%)"

        story.append(Paragraph(cost_text, self.styles['normal']))
        story.append(Spacer(1, 20))

        # Состав заказа
        if order_details:
            story.append(Paragraph("СОСТАВ ЗАКАЗА", self.styles['heading']))

            # Группируем по типам
            products = []
            stages = []

            for item_type, _, name, quantity, cost, length_m in order_details:
                if item_type == 'product':
                    products.append((name, quantity, cost))
                else:
                    stages.append((name, length_m, cost))

            if products:
                story.append(Paragraph("Изделия:", self.styles['normal']))
                for name, quantity, cost in products:
                    item_text = f"• {name}: {quantity} шт — {cost:.2f} руб"
                    story.append(Paragraph(item_text, self.styles['small']))
                story.append(Spacer(1, 10))

            if stages:
                story.append(Paragraph("Этапы:", self.styles['normal']))
                for name, length_m, cost in stages:
                    item_text = f"• {name}: {length_m:.1f} м — {cost:.2f} руб"
                    story.append(Paragraph(item_text, self.styles['small']))
                story.append(Spacer(1, 20))

        # Требования к материалам
        if requirements:
            story.append(Paragraph("СПИСОК МАТЕРИАЛОВ", self.styles['heading']))

            # Создаем сводную таблицу материалов
            materials_summary = self._aggregate_materials(requirements)

            if materials_summary:
                # Заголовки таблицы
                table_data = [['Материал', 'Общее количество', 'Единица измерения']]

                for material_name, total_amount in materials_summary.items():
                    # Определяем единицу измерения (упрощенно)
                    unit = "м" if any(
                        "Пиломатериал" in str(req) for req in requirements.get(material_name, [])) else "шт"
                    table_data.append([
                        material_name,
                        f"{total_amount:.2f}" if unit == "м" else f"{int(total_amount)}",
                        unit
                    ])

                # Создаем таблицу
                table = Table(table_data, colWidths=[8 * cm, 4 * cm, 3 * cm])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Arial' if self.arial_registered else 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('FONTNAME', (0, 1), (-1, -1), 'Arial' if self.arial_registered else 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))

                story.append(table)
                story.append(Spacer(1, 20))

        # Детальная разбивка материалов по позициям
        if requirements:
            story.append(Paragraph("ДЕТАЛИЗАЦИЯ МАТЕРИАЛОВ", self.styles['heading']))

            for material_name, req_list in requirements.items():
                material_heading = f"{material_name}:"
                story.append(Paragraph(material_heading, self.styles['normal']))

                for req_value, description in req_list:
                    if isinstance(req_value, (int, float)):
                        detail_text = f"  • {description}: {req_value:.2f}"
                        # Пытаемся определить единицу измерения из описания
                        if "Пиломатериал" in description:
                            detail_text += " м"
                        else:
                            detail_text += " шт"
                        story.append(Paragraph(detail_text, self.styles['small']))

                story.append(Spacer(1, 8))

            story.append(Spacer(1, 12))

        # Инструкции к заказу
        if instructions_text and instructions_text.strip():
            story.append(Paragraph("ИНСТРУКЦИИ", self.styles['heading']))
            # Заменяем переносы строк на HTML переносы
            formatted_instructions = instructions_text.replace('\n', '<br/>')
            story.append(Paragraph(formatted_instructions, self.styles['normal']))
            story.append(Spacer(1, 20))

        # Подвал документа
        footer_text = f"Документ создан автоматически системой управления складом<br/>"
        footer_text += f"Дата генерации: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        story.append(Spacer(1, 30))
        story.append(Paragraph(footer_text, self.styles['small']))

        return story

    def _aggregate_materials(self, requirements):
        """Агрегирование материалов с подсчетом общего количества"""
        materials_summary = defaultdict(float)

        for material_name, req_list in requirements.items():
            total = 0
            for req_value, description in req_list:
                if isinstance(req_value, (int, float)):
                    total += req_value
            materials_summary[material_name] = total

        return dict(materials_summary)

    def generate_inventory_report(self, warehouse_items, materials_info):
        """
        Генерация отчета по складским остаткам

        Args:
            warehouse_items: Список складских позиций
            materials_info: Информация о материалах

        Returns:
            str: Путь к созданному PDF файлу
        """
        try:
            pdf_path = self._get_pdf_path()
            filename = f"inventory_report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
            full_path = os.path.join(pdf_path, filename)

            doc = SimpleDocTemplate(full_path, pagesize=A4)
            story = []

            # Заголовок
            story.append(Paragraph("ОТЧЕТ ПО СКЛАДСКИМ ОСТАТКАМ", self.styles['title']))
            story.append(Spacer(1, 20))

            # Дата создания
            date_text = f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            story.append(Paragraph(date_text, self.styles['normal']))
            story.append(Spacer(1, 20))

            if warehouse_items:
                # Создаем таблицу остатков
                table_data = [['Материал', 'Тип', 'Длина (м)', 'Количество', 'Стоимость']]
                total_value = 0

                for w_id, name, length, quantity, m_type, unit, price in warehouse_items:
                    length_text = f"{length:.2f}" if length > 0 else "—"

                    if m_type == "Пиломатериал" and length > 0:
                        item_value = price * quantity * length
                    else:
                        item_value = price * quantity

                    total_value += item_value

                    table_data.append([
                        name,
                        m_type,
                        length_text,
                        str(quantity),
                        f"{item_value:.2f} руб"
                    ])

                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Arial' if self.arial_registered else 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('FONTNAME', (0, 1), (-1, -1), 'Arial' if self.arial_registered else 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))

                story.append(table)
                story.append(Spacer(1, 20))

                # Итоговая стоимость
                total_text = f"Общая стоимость склада: {total_value:.2f} руб"
                story.append(Paragraph(total_text, self.styles['heading']))

            else:
                story.append(Paragraph("Склад пуст", self.styles['normal']))

            doc.build(story)
            return full_path

        except Exception as e:
            raise Exception(f"Ошибка при генерации отчета по складу: {str(e)}")

    def generate_cost_analysis_report(self, products_data, stages_data):
        """
        Генерация отчета по анализу себестоимости

        Args:
            products_data: Данные по изделиям
            stages_data: Данные по этапам

        Returns:
            str: Путь к созданному PDF файлу
        """
        try:
            pdf_path = self._get_pdf_path()
            filename = f"cost_analysis_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
            full_path = os.path.join(pdf_path, filename)

            doc = SimpleDocTemplate(full_path, pagesize=A4)
            story = []

            # Заголовок
            story.append(Paragraph("АНАЛИЗ СЕБЕСТОИМОСТИ", self.styles['title']))
            story.append(Spacer(1, 20))

            # Дата создания
            date_text = f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            story.append(Paragraph(date_text, self.styles['normal']))
            story.append(Spacer(1, 20))

            # Анализ изделий
            if products_data:
                story.append(Paragraph("ИЗДЕЛИЯ", self.styles['heading']))

                table_data = [['Название', 'Себестоимость', 'Цена реализации', 'Прибыль']]
                for prod_id, name, cost in products_data:
                    sale_price = cost * 2
                    profit = sale_price - cost

                    table_data.append([
                        name,
                        f"{cost:.2f} руб",
                        f"{sale_price:.2f} руб",
                        f"{profit:.2f} руб"
                    ])

                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Arial' if self.arial_registered else 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('FONTNAME', (0, 1), (-1, -1), 'Arial' if self.arial_registered else 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))

                story.append(table)
                story.append(Spacer(1, 20))

            # Анализ этапов
            if stages_data:
                story.append(Paragraph("ЭТАПЫ", self.styles['heading']))

                table_data = [['Название', 'Себестоимость за м', 'Цена за м', 'Прибыль за м']]
                for stage_id, name, cost, description in stages_data:
                    sale_price = cost * 2
                    profit = sale_price - cost

                    table_data.append([
                        name,
                        f"{cost:.2f} руб",
                        f"{sale_price:.2f} руб",
                        f"{profit:.2f} руб"
                    ])

                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Arial' if self.arial_registered else 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('FONTNAME', (0, 1), (-1, -1), 'Arial' if self.arial_registered else 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))

                story.append(table)

            doc.build(story)
            return full_path

        except Exception as e:
            raise Exception(f"Ошибка при генерации отчета по себестоимости: {str(e)}")