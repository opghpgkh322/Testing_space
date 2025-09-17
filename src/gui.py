# gui.py - ВЕРСИЯ С АВТОЗАПОЛНЕНИЕМ ПОЛЕЙ

import sys
import os
import math
import subprocess
import sqlite3
import platform
from functools import partial
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime
from cutting_optimizer import CuttingOptimizer
from collections import defaultdict
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QTableWidget,
                             QTableWidgetItem, QPushButton, QVBoxLayout, QWidget,
                             QHeaderView, QMessageBox, QLabel, QLineEdit, QComboBox,
                             QHBoxLayout, QFormLayout, QGroupBox, QSpinBox, QDoubleSpinBox, QTextEdit,
                             QDialog, QSplitter)
from PyQt5.QtCore import Qt

# ИСПРАВЛЕНИЕ 1: Улучшенная регистрация шрифта Arial
ARIAL_FONT_REGISTERED = False


def setup_arial_font():
    global ARIAL_FONT_REGISTERED
    try:
        if getattr(sys, 'frozen', False):
            font_path = os.path.join(os.path.dirname(sys.executable), 'fonts', 'arial.ttf')
        else:
            font_path = os.path.join(os.path.dirname(__file__), 'fonts', 'arial.ttf')
        print(f"Попытка загрузить шрифт: {font_path}")
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('Arial', font_path))
            ARIAL_FONT_REGISTERED = True
            print("✓ Шрифт Arial успешно зарегистрирован")
        else:
            print(f"✗ Файл шрифта не найден: {font_path}")
            ARIAL_FONT_REGISTERED = False
    except Exception as e:
        print(f"✗ Ошибка регистрации шрифта Arial: {e}")
        ARIAL_FONT_REGISTERED = False


# Вызываем функцию регистрации
setup_arial_font()


class RoutesPlanningDialog(QDialog):
    """Диалог для планирования трасс веревочного парка"""

    def __init__(self, stages, parent=None):
        super().__init__(parent)
        self.stages = stages
        self.routes = []
        self.setWindowTitle("Планирование трасс веревочного парка")
        self.setModal(True)
        self.resize(800, 600)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Упрощенная инструкция
        info_label = QLabel("""**Планирование трасс веревочного парка:**
• **Статические этапы** - требуют страховочный трос

• **Динамические/Зип этапы** - НЕ требуют трос и разрывают трассу

• Укажите для каждого статического этапа: номер трассы и позицию в ней

• Динамические этапы автоматически исключаются из расчета троса
""")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Таблица планирования (убрали лишний столбец)
        self.planning_table = QTableWidget()
        self.planning_table.setColumnCount(5)  # БЫЛО 6, СТАЛО 5
        self.planning_table.setHorizontalHeaderLabels([
            "Этап", "Длина (м)", "Категория", "№ трассы", "№ в трассе"
        ])
        self.planning_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.planning_table.setRowCount(len(self.stages))

        for row, stage in enumerate(self.stages):
            # Название этапа
            name_item = QTableWidgetItem(stage['name'])
            name_item.setFlags(name_item.flags() ^ Qt.ItemIsEditable)
            self.planning_table.setItem(row, 0, name_item)

            # Длина
            length_item = QTableWidgetItem(f"{stage['length']:.2f}")
            length_item.setFlags(length_item.flags() ^ Qt.ItemIsEditable)
            self.planning_table.setItem(row, 1, length_item)

            # Категория с цветовой индикацией
            category_item = QTableWidgetItem(stage['category'])
            category_item.setFlags(category_item.flags() ^ Qt.ItemIsEditable)
            if stage['category'] == 'Статика':
                category_item.setBackground(Qt.green)
                category_item.setToolTip("Требует страховочный трос")
            else:
                category_item.setBackground(Qt.red)
                category_item.setToolTip("НЕ требует трос, разрывает трассу")
            self.planning_table.setItem(row, 2, category_item)

            # № трассы
            route_spin = QSpinBox()
            route_spin.setMinimum(1)
            route_spin.setMaximum(10)
            route_spin.setValue(1)
            route_spin.setToolTip("Номер трассы для страховочного троса")
            route_spin.valueChanged.connect(self.validate_positions)
            self.planning_table.setCellWidget(row, 3, route_spin)

            # № в трассе
            position_spin = QSpinBox()
            position_spin.setMinimum(1)
            position_spin.setMaximum(20)
            position_spin.setValue(row + 1)
            position_spin.setToolTip("Позиция этапа внутри трассы троса")
            position_spin.valueChanged.connect(self.validate_positions)
            self.planning_table.setCellWidget(row, 4, position_spin)

        layout.addWidget(self.planning_table)

        # ДОБАВЛЕНО: Лейбл для отображения ошибок валидации
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("color: red; font-weight: bold;")
        self.validation_label.setWordWrap(True)
        layout.addWidget(self.validation_label)

        # Кнопки
        btn_layout = QHBoxLayout()
        auto_btn = QPushButton("Автоматическое планирование")
        auto_btn.clicked.connect(self.auto_planning)
        auto_btn.setToolTip("Автоматически расставить этапы по трассам без конфликтов")
        btn_layout.addWidget(auto_btn)

        preview_btn = QPushButton("Предварительный просмотр")
        preview_btn.clicked.connect(self.show_preview)
        preview_btn.setToolTip("Показать, как будут рассчитаны трассы троса")
        btn_layout.addWidget(preview_btn)

        btn_layout.addStretch()

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept_with_validation)
        btn_layout.addWidget(self.ok_btn)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

        # Выполняем начальную валидацию
        self.validate_positions()

    def validate_positions(self):
        """Проверяет, чтобы ни две строки не имели один и тот же (трасса, позиция)."""
        seen = {}
        conflicts = []

        for row in range(self.planning_table.rowCount()):
            route = self.planning_table.cellWidget(row, 3).value()
            pos = self.planning_table.cellWidget(row, 4).value()
            key = (route, pos)
            name = self.stages[row]['name']
            seen.setdefault(key, []).append(name)

        for key, names in seen.items():
            if len(names) > 1:
                r, p = key
                conflicts.append(f"Трасса {r}, позиция {p}: {', '.join(names)}")

        if conflicts:
            self.validation_label.setText("⚠️ Конфликты позиций:\n" + "\n".join(conflicts))
            self.ok_btn.setEnabled(False)
        else:
            self.validation_label.setText("✅ Конфликтов позиций нет")
            self.ok_btn.setEnabled(True)

    def accept_with_validation(self):
        """ДОБАВЛЕНО: Принятие диалога только при отсутствии конфликтов"""
        self.validate_positions()
        if self.ok_btn.isEnabled():
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка валидации",
                                "Есть конфликты позиций! Несколько этапов не могут находиться "
                                "на одной позиции в одной трассе.")

    def auto_planning(self):
        """Автоматическое планирование без конфликтов"""
        # Получаем только статические этапы
        static_stages = []
        for row in range(len(self.stages)):
            if self.stages[row]['category'] == 'Статика':
                static_stages.append(row)

        if not static_stages:
            QMessageBox.information(self, "Информация", "Нет статических этапов для планирования")
            return

        # Размещаем статические этапы в одну трассу по порядку
        for i, row in enumerate(static_stages):
            route_widget = self.planning_table.cellWidget(row, 3)
            position_widget = self.planning_table.cellWidget(row, 4)

            route_widget.setValue(1)  # Все в первую трассу
            position_widget.setValue(i + 1)  # По порядку без конфликтов

        # Запускаем валидацию
        self.validate_positions()

    def show_preview(self):
        """Исправленный предварительный просмотр расчета трасс"""
        # Проверяем позиции
        self.validate_positions()
        if not self.ok_btn.isEnabled():
            QMessageBox.warning(self, "Ошибка", "Устраните конфликты позиций перед просмотром")
            return

        # Получаем трассы
        routes = self.get_routes()

        # Общая статистика
        total_stages = len(self.stages)
        static_count = sum(1 for s in self.stages if s['category'] == "Статика")
        dynamic_count = total_stages - static_count

        preview = f"🔍 Предварительный расчет трасс:\n"
        preview += f"Всего этапов: {total_stages} (Статика: {static_count}, Динамика/Зип: {dynamic_count})\n"
        preview += f"Трасс страховочного троса: {len(routes)}\n\n"

        total_rope = 0.0
        total_clamps = 0

        for idx, route in enumerate(routes, 1):
            preview += f"=== Трасса {idx} ===\n"
            preview += f"Статических этапов: {len(route)}\n"

            # Восстанавливаем полную трассу с динамическими этапами
            full_route = []
            for row in range(len(self.stages)):
                route_widget = self.planning_table.cellWidget(row, 3)
                position_widget = self.planning_table.cellWidget(row, 4)
                stage = self.stages[row]

                if route_widget and position_widget:
                    if route_widget.value() == idx:
                        full_route.append((position_widget.value(), stage))

            # Сортируем по позиции и разбиваем на сегменты
            full_route.sort(key=lambda x: x[0])
            segments = []
            current_segment = None

            for pos, stage in full_route:
                stage_type = 'static' if stage['category'] == 'Статика' else 'dynamic'

                if current_segment is None or current_segment['type'] != stage_type:
                    current_segment = {'type': stage_type, 'stages': [stage]}
                    segments.append(current_segment)
                else:
                    current_segment['stages'].append(stage)

            # Расчет для этой трассы - только статические сегменты
            route_rope = 0.0
            route_clamps = 0

            for segment in segments:
                if segment['type'] == 'static':
                    N = len(segment['stages'])
                    L = sum(s['length'] for s in segment['stages'])
                    rope = 5 + 5 * N + L
                    clamps = 6 + 6 * N
                    route_rope += rope
                    route_clamps += clamps
                    preview += f" Статический сегмент: {N} этапов, {L:.2f}м → "
                    preview += f"Трос: {rope:.2f}м, Зажимы: {clamps}шт\n"
                elif segment['type'] == 'dynamic':
                    preview += f" Динамический сегмент: игнорируется (разрывает трассу)\n"

            total_rope += route_rope
            total_clamps += route_clamps
            preview += f"Итого по трассе {idx}: {route_rope:.2f}м троса, {route_clamps} зажимов\n\n"

        preview += f"📊 ОБЩИЙ ИТОГ: {total_rope:.2f}м троса М12, {total_clamps} зажимов М12"

        QMessageBox.information(self, "Предварительный расчет", preview)

    def get_routes(self):
        """Возвращает список трасс с этапами (включая динамические для правильного разбиения)"""
        routes_dict = {}

        # Собираем ВСЕ этапы с их позициями в трассах
        for row in range(len(self.stages)):
            stage = self.stages[row]
            route_widget = self.planning_table.cellWidget(row, 3)
            position_widget = self.planning_table.cellWidget(row, 4)

            route_num = route_widget.value()
            position = position_widget.value()

            if route_num not in routes_dict:
                routes_dict[route_num] = {}
            routes_dict[route_num][position] = stage

        # Преобразуем в список трасс, отсортированных по позициям
        routes = []
        for route_num in sorted(routes_dict.keys()):
            route_stages = []
            for position in sorted(routes_dict[route_num].keys()):
                route_stages.append(routes_dict[route_num][position])
            if route_stages:  # Добавляем только непустые трассы
                routes.append(route_stages)

        return routes


# КЛАСС ЭТАПОВ С АВТОЗАПОЛНЕНИЕМ
class StagesTab(QWidget):
    def __init__(self, db_path, main_window=None):
        super().__init__()
        self.db_path = db_path
        self.main_window = main_window
        self.selected_stage_id = None
        self.selected_stage_name = None
        self.init_ui()
        self.load_stages()

    def init_ui(self):
        main_splitter = QSplitter(Qt.Horizontal)

        # Левая панель
        left_panel = QWidget()
        left_layout = QVBoxLayout()

        # Поисковое поле
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по этапам…")
        self.search_input.textChanged.connect(self.filter_table)
        left_layout.addWidget(self.search_input)

        stages_group = QGroupBox("Этапы")
        stages_layout = QVBoxLayout()

        # Таблица этапов
        self.stages_table = QTableWidget()
        self.stages_table.setColumnCount(5)
        self.stages_table.setHorizontalHeaderLabels(["ID", "Название", "Категория", "Себестоимость", "Описание"])
        self.stages_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stages_table.cellClicked.connect(self.on_stage_selected)
        self.stages_table.cellChanged.connect(self.on_stage_cell_edited)
        stages_layout.addWidget(self.stages_table)

        # Форма добавления этапа
        form_layout = QFormLayout()

        self.stage_name_input = QLineEdit()
        self.stage_name_input.setPlaceholderText("Название этапа")
        form_layout.addRow(QLabel("Название этапа:"), self.stage_name_input)

        # Выбор категории этапа
        self.stage_category_combo = QComboBox()
        self.stage_category_combo.addItems(["Статика", "Динамика", "Зип"])
        form_layout.addRow(QLabel("Категория:"), self.stage_category_combo)

        self.stage_description_input = QTextEdit()
        self.stage_description_input.setPlaceholderText("Описание этапа работ...")
        self.stage_description_input.setMaximumHeight(60)
        form_layout.addRow(QLabel("Описание:"), self.stage_description_input)

        btn_layout = QHBoxLayout()
        self.add_stage_btn = QPushButton("Добавить этап")
        self.add_stage_btn.clicked.connect(self.add_stage)
        btn_layout.addWidget(self.add_stage_btn)

        self.delete_stage_btn = QPushButton("Удалить этап")
        self.delete_stage_btn.clicked.connect(self.delete_stage)
        btn_layout.addWidget(self.delete_stage_btn)

        self.calculate_cost_btn = QPushButton("Рассчитать себестоимость")
        self.calculate_cost_btn.clicked.connect(self.calculate_stage_cost)
        btn_layout.addWidget(self.calculate_cost_btn)

        form_layout.addRow(btn_layout)
        stages_layout.addLayout(form_layout)
        stages_group.setLayout(stages_layout)
        left_layout.addWidget(stages_group)
        left_panel.setLayout(left_layout)
        main_splitter.addWidget(left_panel)

        # Правая панель - состав этапа
        self.composition_group = QGroupBox("Состав этапа")
        self.composition_group.setEnabled(False)
        composition_layout = QVBoxLayout()

        composition_tabs = QTabWidget()

        # Вкладка "Изделия в этапе"
        products_tab = QWidget()
        products_layout = QVBoxLayout()

        self.stage_products_table = QTableWidget()
        self.stage_products_table.setColumnCount(5)
        self.stage_products_table.setHorizontalHeaderLabels(
            ["ID", "Изделие", "Часть", "Количество", "Стоимость"]
        )
        self.stage_products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stage_products_table.cellChanged.connect(self.on_stage_product_cell_edited)
        products_layout.addWidget(self.stage_products_table)

        product_form = QFormLayout()

        self.product_combo = QComboBox()
        product_form.addRow(QLabel("Изделие:"), self.product_combo)

        self.product_part_combo = QComboBox()
        self.product_part_combo.addItems(["start", "meter", "end"])
        product_form.addRow(QLabel("Часть:"), self.product_part_combo)

        self.product_quantity_input = QSpinBox()
        self.product_quantity_input.setMinimum(1)
        self.product_quantity_input.setMaximum(999)
        self.product_quantity_input.setValue(1)
        product_form.addRow(QLabel("Количество:"), self.product_quantity_input)

        product_btn_layout = QHBoxLayout()
        self.add_product_to_stage_btn = QPushButton("Добавить изделие")
        self.add_product_to_stage_btn.clicked.connect(self.add_product_to_stage)
        product_btn_layout.addWidget(self.add_product_to_stage_btn)

        self.remove_product_from_stage_btn = QPushButton("Удалить изделие")
        self.remove_product_from_stage_btn.clicked.connect(self.remove_product_from_stage)
        product_btn_layout.addWidget(self.remove_product_from_stage_btn)

        product_form.addRow(product_btn_layout)
        products_layout.addLayout(product_form)
        products_tab.setLayout(products_layout)
        composition_tabs.addTab(products_tab, "Изделия")

        # Вкладка "Материалы в этапе" С АВТОЗАПОЛНЕНИЕМ
        materials_tab = QWidget()
        materials_layout = QVBoxLayout()

        self.stage_materials_table = QTableWidget()
        self.stage_materials_table.setColumnCount(7)
        self.stage_materials_table.setHorizontalHeaderLabels(
            ["ID", "Материал", "Тип", "Часть", "Количество", "Длина", "Стоимость"]
        )
        self.stage_materials_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stage_materials_table.cellChanged.connect(self.on_stage_material_cell_edited)
        materials_layout.addWidget(self.stage_materials_table)

        material_form = QFormLayout()

        self.material_combo = QComboBox()
        # АВТОЗАПОЛНЕНИЕ: подключаем обработчик изменения материала
        self.material_combo.currentTextChanged.connect(self.on_material_changed)
        material_form.addRow(QLabel("Материал:"), self.material_combo)

        self.material_part_combo = QComboBox()
        self.material_part_combo.addItems(["start", "meter", "end"])
        material_form.addRow(QLabel("Часть:"), self.material_part_combo)

        self.material_quantity_input = QSpinBox()
        self.material_quantity_input.setMinimum(1)
        self.material_quantity_input.setMaximum(999)
        self.material_quantity_input.setValue(1)
        material_form.addRow(QLabel("Количество:"), self.material_quantity_input)

        self.material_length_input = QLineEdit()
        self.material_length_input.setPlaceholderText("0.75 (для пиломатериалов)")
        material_form.addRow(QLabel("Длина (м):"), self.material_length_input)

        material_btn_layout = QHBoxLayout()
        self.add_material_to_stage_btn = QPushButton("Добавить материал")
        self.add_material_to_stage_btn.clicked.connect(self.add_material_to_stage)
        material_btn_layout.addWidget(self.add_material_to_stage_btn)

        self.remove_material_from_stage_btn = QPushButton("Удалить материал")
        self.remove_material_from_stage_btn.clicked.connect(self.remove_material_from_stage)
        material_btn_layout.addWidget(self.remove_material_from_stage_btn)

        material_form.addRow(material_btn_layout)
        materials_layout.addLayout(material_form)
        materials_tab.setLayout(materials_layout)
        composition_tabs.addTab(materials_tab, "Материалы")

        composition_layout.addWidget(composition_tabs)

        self.cost_label = QLabel("Себестоимость этапа: 0.00 руб")
        self.cost_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        composition_layout.addWidget(self.cost_label)

        self.composition_group.setLayout(composition_layout)
        main_splitter.addWidget(self.composition_group)

        main_splitter.setSizes([300, 700])

        main_layout = QVBoxLayout()
        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)

    # НОВАЯ ФУНКЦИЯ АВТОЗАПОЛНЕНИЯ ДЛЯ МАТЕРИАЛОВ
    def on_material_changed(self, material_text):
        """АВТОЗАПОЛНЕНИЕ: Заполняет длину в зависимости от типа материала"""
        if not material_text:
            return

        try:
            # Извлекаем ID материала из ComboBox
            material_id = self.material_combo.currentData()
            if not material_id:
                return

            # Получаем тип материала из БД
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT type FROM materials WHERE id = ?", (material_id,))
            result = cursor.fetchone()
            conn.close()

            if result:
                material_type = result[0]
                if material_type == "Метиз":
                    # Для метизов автоматически ставим длину 0
                    self.material_length_input.setText("0")
                    self.material_length_input.setEnabled(False)
                    self.material_length_input.setToolTip("Длина для метизов всегда 0")
                else:
                    # Для пиломатериалов включаем поле и очищаем
                    self.material_length_input.setEnabled(True)
                    if self.material_length_input.text() == "0":
                        self.material_length_input.clear()
                    self.material_length_input.setToolTip("Введите длину в метрах")

        except Exception as e:
            print(f"Ошибка при автозаполнении материала: {e}")

    def on_stage_product_cell_edited(self, row, column):
        """Редактирование части/количества изделия в этапе"""
        try:
            sp_id = int(self.stage_products_table.item(row, 0).text())

            if column == 2:  # Часть
                new_part = self.stage_products_table.item(row, column).text().strip()
                if new_part not in ("start", "meter", "end"):
                    QMessageBox.warning(self, "Ошибка", "Часть должна быть: start, meter или end")
                    self.load_stage_products()
                    return

                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("UPDATE stage_products SET part = ? WHERE id = ?", (new_part, sp_id))
                conn.commit()
                conn.close()

                self.load_stage_products()
                self.calculate_stage_cost()

            elif column == 3:  # Количество
                new_quantity = int(self.stage_products_table.item(row, column).text())
                if new_quantity < 1:
                    QMessageBox.warning(self, "Ошибка", "Количество должно быть больше 0")
                    self.load_stage_products()
                    return

                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("UPDATE stage_products SET quantity = ? WHERE id = ?", (new_quantity, sp_id))
                conn.commit()
                conn.close()

                self.load_stage_products()
                self.calculate_stage_cost()

        except (ValueError, TypeError):
            QMessageBox.warning(self, "Ошибка", "Некорректное значение")
            self.load_stage_products()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при обновлении: {str(e)}")
            self.load_stage_products()

    def on_category_changed(self, row, new_category):
        """Обновляет категорию этапа в БД"""
        try:
            stage_id = int(self.stages_table.item(row, 0).text())
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE stages SET category = ? WHERE id = ?", (new_category, stage_id))
            conn.commit()
            conn.close()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить категорию: {str(e)}")
            self.load_stages()

    def on_stage_material_cell_edited(self, row, column):
        """Редактирование части/количества/длины материалов этапа"""
        try:
            sm_id = int(self.stage_materials_table.item(row, 0).text())

            if column == 3:  # Часть
                new_part = self.stage_materials_table.item(row, column).text().strip()
                if new_part not in ("start", "meter", "end"):
                    QMessageBox.warning(self, "Ошибка", "Часть должна быть: start, meter или end")
                    self.load_stage_materials()
                    return

                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("UPDATE stage_materials SET part = ? WHERE id = ?", (new_part, sm_id))
                conn.commit()
                conn.close()

                self.load_stage_materials()
                self.calculate_stage_cost()

            elif column == 4:  # Количество
                new_quantity = int(self.stage_materials_table.item(row, column).text())
                if new_quantity < 1:
                    QMessageBox.warning(self, "Ошибка", "Количество должно быть больше 0")
                    self.load_stage_materials()
                    return

                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("UPDATE stage_materials SET quantity = ? WHERE id = ?", (new_quantity, sm_id))
                conn.commit()
                conn.close()

                self.load_stage_materials()
                self.calculate_stage_cost()

            elif column == 5:  # Длина
                new_length_text = self.stage_materials_table.item(row, column).text().strip()
                new_length = float(new_length_text) if new_length_text else None

                if new_length is not None and new_length < 0:
                    QMessageBox.warning(self, "Ошибка", "Длина не может быть отрицательной")
                    self.load_stage_materials()
                    return

                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("UPDATE stage_materials SET length = ? WHERE id = ?", (new_length, sm_id))
                conn.commit()
                conn.close()

                self.load_stage_materials()
                self.calculate_stage_cost()

        except (ValueError, TypeError):
            QMessageBox.warning(self, "Ошибка", "Некорректное значение")
            self.load_stage_materials()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при обновлении: {str(e)}")
            self.load_stage_materials()

    def on_stage_cell_edited(self, row, column):
        """Обработка редактирования ячеек с учетом новой колонки категории"""
        try:
            stage_id = int(self.stages_table.item(row, 0).text())

            if column == 1:  # Название этапа
                new_name = self.stages_table.item(row, column).text().strip()
                if not new_name:
                    QMessageBox.warning(self, "Ошибка", "Название этапа не может быть пустым")
                    self.load_stages()
                    return

                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("UPDATE stages SET name = ? WHERE id = ?", (new_name, stage_id))
                conn.commit()
                conn.close()

            elif column == 4:  # Описание этапа
                new_description = self.stages_table.item(row, column).text()
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("UPDATE stages SET description = ? WHERE id = ?", (new_description, stage_id))
                conn.commit()
                conn.close()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при обновлении: {str(e)}")
            self.load_stages()

    def load_stages(self):
        """Загружает список этапов с категориями"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, category, cost, description FROM stages ORDER BY name")
        stages = cursor.fetchall()
        conn.close()

        self.stages_table.setRowCount(len(stages))
        self.stages_table.cellChanged.disconnect()

        for row_idx, (stage_id, stage_name, category, cost, description) in enumerate(stages):
            # ID (только для чтения)
            id_item = QTableWidgetItem(str(stage_id))
            id_item.setFlags(id_item.flags() ^ Qt.ItemIsEditable)
            self.stages_table.setItem(row_idx, 0, id_item)

            # Название (редактируемое)
            self.stages_table.setItem(row_idx, 1, QTableWidgetItem(stage_name))

            # Категория (редактируемое)
            category_combo = QComboBox()
            category_combo.addItems(["Статика", "Динамика", "Зип"])
            category_combo.setCurrentText(category or "Статика")
            category_combo.currentTextChanged.connect(
                lambda new_cat, r=row_idx: self.on_category_changed(r, new_cat)
            )
            self.stages_table.setCellWidget(row_idx, 2, category_combo)

            # Себестоимость (только для чтения)
            cost_item = QTableWidgetItem(f"{cost:.2f} руб")
            cost_item.setFlags(cost_item.flags() ^ Qt.ItemIsEditable)
            self.stages_table.setItem(row_idx, 3, cost_item)

            # Описание (редактируемое)
            self.stages_table.setItem(row_idx, 4, QTableWidgetItem(description or ""))

        self.stages_table.cellChanged.connect(self.on_stage_cell_edited)

    def load_stage_products(self):
        """Загружает изделия в составе выбранного этапа с поддержкой части"""
        if not self.selected_stage_id:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sp.id, p.name, sp.part, sp.quantity, (p.cost * sp.quantity) as total_cost
            FROM stage_products sp
            JOIN products p ON sp.product_id = p.id
            WHERE sp.stage_id = ?
        """, (self.selected_stage_id,))
        stage_products = cursor.fetchall()
        conn.close()

        self.stage_products_table.cellChanged.disconnect()
        self.stage_products_table.setRowCount(len(stage_products))

        for row_idx, (sp_id, prod_name, part, quantity, total_cost) in enumerate(stage_products):
            id_item = QTableWidgetItem(str(sp_id))
            id_item.setFlags(id_item.flags() ^ Qt.ItemIsEditable)
            self.stage_products_table.setItem(row_idx, 0, id_item)

            name_item = QTableWidgetItem(prod_name)
            name_item.setFlags(name_item.flags() ^ Qt.ItemIsEditable)
            self.stage_products_table.setItem(row_idx, 1, name_item)

            self.stage_products_table.setItem(row_idx, 2, QTableWidgetItem(part))
            self.stage_products_table.setItem(row_idx, 3, QTableWidgetItem(str(quantity)))

            cost_item = QTableWidgetItem(f"{total_cost:.2f} руб")
            cost_item.setFlags(cost_item.flags() ^ Qt.ItemIsEditable)
            self.stage_products_table.setItem(row_idx, 4, cost_item)

        self.stage_products_table.cellChanged.connect(self.on_stage_product_cell_edited)

    def load_stage_materials(self):
        """Загружает материалы в составе выбранного этапа с поддержкой редактирования и части"""
        if not self.selected_stage_id:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sm.id, m.name, m.type, sm.part, sm.quantity, sm.length, m.price,
                   CASE 
                       WHEN m.type = 'Пиломатериал' AND sm.length IS NOT NULL 
                       THEN (m.price * sm.quantity * sm.length)
                       ELSE (m.price * sm.quantity)
                   END as total_cost
            FROM stage_materials sm
            JOIN materials m ON sm.material_id = m.id
            WHERE sm.stage_id = ?
        """, (self.selected_stage_id,))
        stage_materials = cursor.fetchall()
        conn.close()

        self.stage_materials_table.cellChanged.disconnect()
        self.stage_materials_table.setRowCount(len(stage_materials))

        for row_idx, (sm_id, mat_name, mat_type, part, quantity, length, price, total_cost) in enumerate(
                stage_materials):
            id_item = QTableWidgetItem(str(sm_id))
            id_item.setFlags(id_item.flags() ^ Qt.ItemIsEditable)
            self.stage_materials_table.setItem(row_idx, 0, id_item)

            name_item = QTableWidgetItem(mat_name)
            name_item.setFlags(name_item.flags() ^ Qt.ItemIsEditable)
            self.stage_materials_table.setItem(row_idx, 1, name_item)

            type_item = QTableWidgetItem(mat_type)
            type_item.setFlags(type_item.flags() ^ Qt.ItemIsEditable)
            self.stage_materials_table.setItem(row_idx, 2, type_item)

            self.stage_materials_table.setItem(row_idx, 3, QTableWidgetItem(part))
            self.stage_materials_table.setItem(row_idx, 4, QTableWidgetItem(str(quantity)))

            length_item = QTableWidgetItem(str(length) if length else "")
            if mat_type == "Метиз":
                length_item.setFlags(length_item.flags() ^ Qt.ItemIsEditable)
            self.stage_materials_table.setItem(row_idx, 5, length_item)

            cost_item = QTableWidgetItem(f"{total_cost:.2f} руб")
            cost_item.setFlags(cost_item.flags() ^ Qt.ItemIsEditable)
            self.stage_materials_table.setItem(row_idx, 6, cost_item)

        self.stage_materials_table.cellChanged.connect(self.on_stage_material_cell_edited)

    def calculate_stage_cost(self):
        """Расчет себестоимости этапа с разложением по частям"""
        if not self.selected_stage_id:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Стоимость изделий по частям
            cursor.execute("""
                SELECT sp.part, p.cost, sp.quantity
                FROM stage_products sp
                JOIN products p ON sp.product_id = p.id
                WHERE sp.stage_id = ?
            """, (self.selected_stage_id,))

            start_cost = meter_cost = end_cost = 0.0
            for part, pcost, qty in cursor.fetchall():
                if part == 'start':
                    start_cost += pcost * qty
                elif part == 'meter':
                    meter_cost += pcost * qty
                else:
                    end_cost += pcost * qty

            # Стоимость материалов по частям (за 1 метр для 'meter')
            cursor.execute("""
                SELECT sm.part, m.type, m.price, sm.quantity, sm.length
                FROM stage_materials sm
                JOIN materials m ON sm.material_id = m.id
                WHERE sm.stage_id = ?
            """, (self.selected_stage_id,))

            for part, mtype, price, qty, length in cursor.fetchall():
                if mtype == "Пиломатериал" and length:
                    add = price * qty * length
                else:
                    add = price * qty

                if part == 'start':
                    start_cost += add
                elif part == 'meter':
                    meter_cost += add
                else:
                    end_cost += add

            # Обновляем отображение: 1 метр = start + meter + end
            one_meter_total = start_cost + meter_cost + end_cost
            self.cost_label.setText(
                f"Себестоимость этапа (1 м): {one_meter_total:.2f} руб | "
                f"Метр: {meter_cost:.2f} руб | Крепления: {(start_cost + end_cost):.2f} руб"
            )

            # В stages.cost сохраняем стоимость "метровой" части для совместимости
            cursor.execute("UPDATE stages SET cost = ? WHERE id = ?", (meter_cost, self.selected_stage_id))
            conn.commit()
            self.load_stages()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка расчета", f"Произошла ошибка: {str(e)}")
        finally:
            conn.close()

    # Остальные методы без изменений
    def on_stage_selected(self, row, col):
        try:
            if row < 0 or row >= self.stages_table.rowCount():
                return

            id_item = self.stages_table.item(row, 0)
            name_item = self.stages_table.item(row, 1)

            if not id_item or not name_item:
                return

            self.selected_stage_id = int(id_item.text())
            self.selected_stage_name = name_item.text()

            self.composition_group.setEnabled(True)
            self.composition_group.setTitle(f"Состав этапа: {self.selected_stage_name}")

            self.load_products()
            self.load_materials()
            self.load_stage_products()
            self.load_stage_materials()
            self.calculate_stage_cost()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка выбора", f"Произошла ошибка: {str(e)}")

    def load_products(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM products ORDER BY name")
        products = cursor.fetchall()
        conn.close()

        self.product_combo.clear()
        for prod_id, prod_name in products:
            self.product_combo.addItem(prod_name, prod_id)

    def load_materials(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, type FROM materials ORDER BY name")
        materials = cursor.fetchall()
        conn.close()

        self.material_combo.clear()
        for mat_id, mat_name, mat_type in materials:
            self.material_combo.addItem(f"{mat_name} ({mat_type})", mat_id)

    def add_stage(self):
        """Добавляет этап с категорией"""
        name = self.stage_name_input.text().strip()
        category = self.stage_category_combo.currentText()
        description = self.stage_description_input.toPlainText().strip()

        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название этапа")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO stages (name, category, description) VALUES (?, ?, ?)",
                (name, category, description)
            )
            conn.commit()
            self.load_stages()
            self.stage_name_input.clear()
            self.stage_description_input.clear()
            QMessageBox.information(self, "Успех", "Этап добавлен!")
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Ошибка", "Этап с таким названием уже существует")
        finally:
            conn.close()

    def delete_stage(self):
        selected_row = self.stages_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите этап для удаления")
            return

        stage_id = int(self.stages_table.item(selected_row, 0).text())
        stage_name = self.stages_table.item(selected_row, 1).text()

        reply = QMessageBox.question(self, "Подтверждение",
                                     f"Вы уверены, что хотите удалить этап '{stage_name}'?",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM stage_products WHERE stage_id = ?", (stage_id,))
                cursor.execute("DELETE FROM stage_materials WHERE stage_id = ?", (stage_id,))
                cursor.execute("DELETE FROM stages WHERE id = ?", (stage_id,))
                conn.commit()
                self.load_stages()
                self.composition_group.setEnabled(False)
                QMessageBox.information(self, "Успех", "Этап удален")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка базы данных", str(e))
            finally:
                conn.close()

    def add_product_to_stage(self):
        if not self.selected_stage_id:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите этап")
            return

        product_id = self.product_combo.currentData()
        part = self.product_part_combo.currentText()
        quantity = self.product_quantity_input.value()

        if not product_id:
            QMessageBox.warning(self, "Ошибка", "Выберите изделие")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO stage_products (stage_id, product_id, quantity, part) VALUES (?, ?, ?, ?)",
                (self.selected_stage_id, product_id, quantity, part)
            )
            conn.commit()
            self.load_stage_products()
            self.calculate_stage_cost()
            QMessageBox.information(self, "Успех", "Изделие добавлено в этап")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка базы данных", str(e))
        finally:
            conn.close()

    def remove_product_from_stage(self):
        selected_row = self.stage_products_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите изделие для удаления")
            return

        sp_id = int(self.stage_products_table.item(selected_row, 0).text())
        product_name = self.stage_products_table.item(selected_row, 1).text()

        reply = QMessageBox.question(self, "Подтверждение",
                                     f"Удалить изделие '{product_name}' из этапа?",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM stage_products WHERE id = ?", (sp_id,))
            conn.commit()
            conn.close()
            self.load_stage_products()
            self.calculate_stage_cost()
            QMessageBox.information(self, "Успех", "Изделие удалено из этапа")

    def add_material_to_stage(self):
        if not self.selected_stage_id:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите этап")
            return

        material_id = self.material_combo.currentData()
        part = self.material_part_combo.currentText()
        quantity = self.material_quantity_input.value()
        length = self.material_length_input.text().strip()

        if not material_id:
            QMessageBox.warning(self, "Ошибка", "Выберите материал")
            return

        try:
            length_val = float(length) if length else None
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Длина должна быть числом")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO stage_materials (stage_id, material_id, quantity, length, part) VALUES (?, ?, ?, ?, ?)",
                (self.selected_stage_id, material_id, quantity, length_val, part)
            )
            conn.commit()
            self.load_stage_materials()
            self.calculate_stage_cost()
            QMessageBox.information(self, "Успех", "Материал добавлен в этап")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка базы данных", str(e))
        finally:
            conn.close()

    def remove_material_from_stage(self):
        selected_row = self.stage_materials_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите материал для удаления")
            return

        sm_id = int(self.stage_materials_table.item(selected_row, 0).text())
        material_name = self.stage_materials_table.item(selected_row, 1).text()

        reply = QMessageBox.question(self, "Подтверждение",
                                     f"Удалить материал '{material_name}' из этапа?",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM stage_materials WHERE id = ?", (sm_id,))
            conn.commit()
            conn.close()
            self.load_stage_materials()
            self.calculate_stage_cost()
            QMessageBox.information(self, "Успех", "Материал удален из этапа")

    def recalculate_all_stages_cost(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM stages")
            stage_ids = [row[0] for row in cursor.fetchall()]

            for stage_id in stage_ids:
                cursor.execute("""
                    SELECT SUM(p.cost * sp.quantity) as products_cost
                    FROM stage_products sp
                    JOIN products p ON sp.product_id = p.id
                    WHERE sp.stage_id = ?
                """, (stage_id,))
                products_cost = cursor.fetchone()[0] or 0

                cursor.execute("""
                    SELECT sm.quantity, sm.length, m.price, m.type
                    FROM stage_materials sm
                    JOIN materials m ON sm.material_id = m.id
                    WHERE sm.stage_id = ?
                """, (stage_id,))

                materials_cost = 0
                for quantity, length, price, material_type in cursor.fetchall():
                    if material_type == "Пиломатериал" and length:
                        materials_cost += price * quantity * length
                    else:
                        materials_cost += price * quantity

                total_cost = products_cost + materials_cost
                cursor.execute("UPDATE stages SET cost = ? WHERE id = ?", (total_cost, stage_id))

            conn.commit()
        except Exception as e:
            print(f"Ошибка при пересчете себестоимости этапов: {str(e)}")
            conn.rollback()
        finally:
            conn.close()

    def filter_table(self, text: str):
        """Скрывает строки, где не найден текст ни в одной ячейке."""
        text = text.lower()
        for r in range(self.stages_table.rowCount()):  # НЕ self.table, А self.stages_table
            row_text = " ".join(
                self.stages_table.item(r, c).text().lower()  # НЕ self.table, А self.stages_table
                for c in range(self.stages_table.columnCount())  # НЕ self.table, А self.stages_table
                if self.stages_table.item(r, c)  # НЕ self.table, А self.stages_table
            )
            self.stages_table.setRowHidden(r, text not in row_text)  # НЕ self.table, А self.stages_table


# КЛАСС МАТЕРИАЛОВ С АВТОЗАПОЛНЕНИЕМ
class MaterialsTab(QWidget):
    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по материалам…")
        self.search_input.textChanged.connect(self.filter_table)
        layout.addWidget(self.search_input)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Название", "Тип", "Цена"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Брус 100x100")
        form_layout.addRow(QLabel("Название:"), self.name_input)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Пиломатериал", "Метиз"])
        # АВТОЗАПОЛНЕНИЕ: подключаем обработчик изменения типа
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        form_layout.addRow(QLabel("Тип:"), self.type_combo)

        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("5.00")
        form_layout.addRow(QLabel("Цена:"), self.price_input)

        self.unit_label = QLabel("м")
        form_layout.addRow(QLabel("Ед. изм:"), self.unit_label)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()

        self.add_btn = QPushButton("Добавить")
        self.add_btn.clicked.connect(self.add_material)
        btn_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Редактировать")
        self.edit_btn.clicked.connect(self.edit_material)
        btn_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.clicked.connect(self.delete_material)
        btn_layout.addWidget(self.delete_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

        self.table.cellClicked.connect(self.on_table_cell_clicked)

    def on_type_changed(self, material_type):
        """АВТОЗАПОЛНЕНИЕ: Изменяет единицу измерения в зависимости от типа"""
        if material_type == "Пиломатериал":
            self.unit_label.setText("м")
        else:
            self.unit_label.setText("шт")

    def on_table_cell_clicked(self, row, column):
        try:
            if row >= 0 and self.table.item(row, 0) is not None:
                material_id = self.table.item(row, 0).text()
                name = self.table.item(row, 1).text()
                m_type = self.table.item(row, 2).text()
                price = self.table.item(row, 3).text()

                self.selected_material_id = material_id
                self.name_input.setText(name)
                self.type_combo.setCurrentText(m_type)
                self.price_input.setText(price)

                # АВТОЗАПОЛНЕНИЕ: обновляем единицу измерения
                if m_type == "Пиломатериал":
                    self.unit_label.setText("м")
                else:
                    self.unit_label.setText("шт")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при выборе материала: {str(e)}")

    def edit_material(self):
        if not hasattr(self, 'selected_material_id'):
            QMessageBox.warning(self, "Ошибка", "Выберите материал для редактирования")
            return

        name = self.name_input.text().strip()
        m_type = self.type_combo.currentText()
        price = self.price_input.text().strip()
        unit = self.unit_label.text()

        if not name or not price:
            QMessageBox.warning(self, "Ошибка", "Название и цена обязательны для заполнения")
            return

        try:
            price_val = float(price)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Цена должна быть числом")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM materials WHERE name = ? AND id != ?", (name, self.selected_material_id))
        existing = cursor.fetchone()
        if existing:
            QMessageBox.warning(self, "Ошибка", "Материал с таким названием уже существует")
            conn.close()
            return

        try:
            cursor.execute("UPDATE materials SET name = ?, type = ?, price = ?, unit = ? WHERE id = ?",
                           (name, m_type, price_val, unit, self.selected_material_id))
            conn.commit()
            self.recalculate_products_with_material(self.selected_material_id)
            conn.close()
            self.load_data()
            self.clear_form()
            QMessageBox.information(self, "Успех", "Материал обновлен!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка базы данных", f"Ошибка при обновлении материала: {str(e)}")
        finally:
            conn.close()

    def recalculate_products_with_material(self, material_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT DISTINCT product_id FROM product_composition WHERE material_id = ?", (material_id,))
            product_ids = [row[0] for row in cursor.fetchall()]

            for product_id in product_ids:
                cursor.execute("""SELECT m.price, pc.quantity, pc.length
                               FROM product_composition pc
                               JOIN materials m ON pc.material_id = m.id
                               WHERE pc.product_id = ?""", (product_id,))
                composition = cursor.fetchall()

                total_cost = 0
                for row in composition:
                    price, quantity, length = row
                    if length:
                        total_cost += price * quantity * length
                    else:
                        total_cost += price * quantity

                cursor.execute("UPDATE products SET cost = ? WHERE id = ?", (total_cost, product_id))

            conn.commit()
        except Exception as e:
            print(f"Ошибка при пересчете себестоимости: {str(e)}")
            conn.rollback()
        finally:
            conn.close()

    def clear_form(self):
        self.name_input.clear()
        self.price_input.clear()
        if hasattr(self, 'selected_material_id'):
            delattr(self, 'selected_material_id')

    def load_data(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, type, price FROM materials')
        materials = cursor.fetchall()
        conn.close()

        self.table.setRowCount(len(materials))
        for row_idx, row_data in enumerate(materials):
            for col_idx, col_data in enumerate(row_data):
                if col_idx == 3:
                    item = QTableWidgetItem(f"{float(col_data):.2f}")
                else:
                    item = QTableWidgetItem(str(col_data))
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.table.setItem(row_idx, col_idx, item)

    def add_material(self):
        name = self.name_input.text().strip()
        m_type = self.type_combo.currentText()
        price = self.price_input.text().strip()
        unit = self.unit_label.text()

        if not name or not price:
            QMessageBox.warning(self, "Ошибка", "Название и цена обязательны для заполнения")
            return

        try:
            price_val = float(price)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Цена должна быть числом")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO materials (name, type, price, unit) VALUES (?, ?, ?, ?)",
                           (name, m_type, price_val, unit))
            conn.commit()
            conn.close()
            self.load_data()
            self.name_input.clear()
            self.price_input.clear()
            QMessageBox.information(self, "Успех", "Материал добавлен!")
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Ошибка", "Материал с таким названием уже существует")

    def delete_material(self):
        selected_row = self.table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите материал для удаления")
            return

        material_id = int(self.table.item(selected_row, 0).text())
        reply = QMessageBox.question(self, "Подтверждение",
                                     f"Вы уверены, что хотите удалить этот материал?",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM materials WHERE id = ?", (material_id,))
            conn.commit()
            conn.close()
            self.load_data()
            QMessageBox.information(self, "Успех", "Материал удален")

    def filter_table(self, text: str):
        """Скрывает строки, где не найден текст ни в одной ячейке."""
        text = text.lower()
        for r in range(self.table.rowCount()):
            row_text = " ".join(
                self.table.item(r, c).text().lower()
                for c in range(self.table.columnCount())
                if self.table.item(r, c)
            )
            self.table.setRowHidden(r, text not in row_text)


# КЛАСС ИЗДЕЛИЙ С АВТОЗАПОЛНЕНИЕМ
class ProductsTab(QWidget):
    def __init__(self, db_path, main_window=None):
        super().__init__()
        self.db_path = db_path
        self.main_window = main_window
        self.selected_product_id = None
        self.selected_product_name = None
        self.init_ui()
        self.load_products()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Поисковое поле
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по изделиям…")
        self.search_input.textChanged.connect(self.filter_table)
        main_layout.addWidget(self.search_input)

        products_group = QGroupBox("Изделия")
        products_layout = QVBoxLayout()
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(3)
        self.products_table.setHorizontalHeaderLabels(["ID", "Название", "Себестоимость"])
        self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.products_table.cellClicked.connect(self.on_product_selected)
        products_layout.addWidget(self.products_table)

        form_layout = QFormLayout()
        self.product_name_input = QLineEdit()
        self.product_name_input.setPlaceholderText("Островок")
        form_layout.addRow(QLabel("Название изделия:"), self.product_name_input)

        btn_layout = QHBoxLayout()
        self.add_product_btn = QPushButton("Добавить изделие")
        self.add_product_btn.clicked.connect(self.add_product)
        btn_layout.addWidget(self.add_product_btn)

        self.delete_product_btn = QPushButton("Удалить изделие")
        self.delete_product_btn.clicked.connect(self.delete_product)
        btn_layout.addWidget(self.delete_product_btn)

        self.calculate_cost_btn = QPushButton("Рассчитать себестоимость")
        self.calculate_cost_btn.clicked.connect(self.calculate_product_cost)
        btn_layout.addWidget(self.calculate_cost_btn)

        form_layout.addRow(btn_layout)
        products_layout.addLayout(form_layout)
        products_group.setLayout(products_layout)
        main_layout.addWidget(products_group)

        self.composition_group = QGroupBox("Состав изделия")
        self.composition_group.setEnabled(False)
        composition_layout = QVBoxLayout()
        self.composition_table = QTableWidget()
        self.composition_table.setColumnCount(5)
        self.composition_table.setHorizontalHeaderLabels(["ID", "Материал", "Тип", "Количество", "Длина (м)"])
        self.composition_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        composition_layout.addWidget(self.composition_table)

        add_form_layout = QFormLayout()
        self.material_combo = QComboBox()
        self.material_combo.currentTextChanged.connect(self.on_material_changed_in_products)
        add_form_layout.addRow(QLabel("Материал:"), self.material_combo)

        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("1")
        add_form_layout.addRow(QLabel("Количество:"), self.quantity_input)

        self.length_input = QLineEdit()
        self.length_input.setPlaceholderText("0.75 (для пиломатериалов)")
        add_form_layout.addRow(QLabel("Длина (м):"), self.length_input)

        comp_btn_layout = QHBoxLayout()
        self.add_to_composition_btn = QPushButton("Добавить в состав")
        self.add_to_composition_btn.clicked.connect(self.add_to_composition)
        comp_btn_layout.addWidget(self.add_to_composition_btn)

        self.remove_from_composition_btn = QPushButton("Удалить из состава")
        self.remove_from_composition_btn.clicked.connect(self.remove_from_composition)
        comp_btn_layout.addWidget(self.remove_from_composition_btn)

        add_form_layout.addRow(comp_btn_layout)
        composition_layout.addLayout(add_form_layout)
        self.cost_label = QLabel("Себестоимость: 0.00 руб")
        composition_layout.addWidget(self.cost_label)
        self.composition_group.setLayout(composition_layout)
        main_layout.addWidget(self.composition_group)

        self.setLayout(main_layout)

    # НОВАЯ ФУНКЦИЯ АВТОЗАПОЛНЕНИЯ ДЛЯ ИЗДЕЛИЙ
    def on_material_changed_in_products(self, material_text):
        """АВТОЗАПОЛНЕНИЕ: Заполняет длину в зависимости от типа материала в изделиях"""
        if not material_text:
            return

        try:
            # Извлекаем ID материала из ComboBox
            material_id = self.material_combo.currentData()
            if not material_id:
                return

            # Получаем тип материала из БД
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT type FROM materials WHERE id = ?", (material_id,))
            result = cursor.fetchone()
            conn.close()

            if result:
                material_type = result[0]
                if material_type == "Метиз":
                    # Для метизов автоматически ставим длину 0
                    self.length_input.setText("0")
                    self.length_input.setEnabled(False)
                    self.length_input.setToolTip("Длина для метизов всегда 0")
                else:
                    # Для пиломатериалов включаем поле и очищаем
                    self.length_input.setEnabled(True)
                    if self.length_input.text() == "0":
                        self.length_input.clear()
                    self.length_input.setToolTip("Введите длину в метрах")

        except Exception as e:
            print(f"Ошибка при автозаполнении материала в изделиях: {e}")

    def recalculate_all_products_cost(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM products")
            product_ids = [row[0] for row in cursor.fetchall()]

            for product_id in product_ids:
                cursor.execute("""SELECT m.price, pc.quantity, pc.length
                               FROM product_composition pc
                               JOIN materials m ON pc.material_id = m.id
                               WHERE pc.product_id = ?""", (product_id,))
                composition = cursor.fetchall()

                total_cost = 0
                for row in composition:
                    price, quantity, length = row
                    if length:
                        total_cost += price * quantity * length
                    else:
                        total_cost += price * quantity

                cursor.execute("UPDATE products SET cost = ? WHERE id = ?", (total_cost, product_id))

            conn.commit()
        except Exception as e:
            print(f"Ошибка при пересчете себестоимости: {str(e)}")
            conn.rollback()
        finally:
            conn.close()

    def load_products(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, cost FROM products ORDER BY name")
        products = cursor.fetchall()
        conn.close()

        self.products_table.setRowCount(len(products))
        for row_idx, (prod_id, prod_name, cost) in enumerate(products):
            self.products_table.setItem(row_idx, 0, QTableWidgetItem(str(prod_id)))
            self.products_table.setItem(row_idx, 1, QTableWidgetItem(prod_name))
            self.products_table.setItem(row_idx, 2, QTableWidgetItem(f"{cost:.2f} руб"))

    def on_product_selected(self, row, col):
        try:
            if row < 0 or row >= self.products_table.rowCount():
                return

            id_item = self.products_table.item(row, 0)
            name_item = self.products_table.item(row, 1)

            if not id_item or not name_item:
                return

            self.selected_product_id = int(id_item.text())
            self.selected_product_name = name_item.text()

            self.composition_group.setEnabled(True)
            self.composition_group.setTitle(f"Состав изделия: {self.selected_product_name}")

            self.load_materials()
            self.load_composition()

            try:
                self.calculate_product_cost()
            except Exception as e:
                QMessageBox.warning(self, "Ошибка расчета", f"Не удалось рассчитать себестоимость: {str(e)}")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка выбора", f"Произошла ошибка: {str(e)}")

    def load_materials(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, type FROM materials ORDER BY name")
        materials = cursor.fetchall()
        conn.close()

        self.material_combo.clear()
        for mat_id, mat_name, mat_type in materials:
            self.material_combo.addItem(f"{mat_name} ({mat_type})", mat_id)

    def load_composition(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""SELECT pc.id, m.name, m.type, pc.quantity, pc.length   
                        FROM product_composition pc
                        JOIN materials m ON pc.material_id = m.id
                        WHERE pc.product_id = ?""", (self.selected_product_id,))
        composition = cursor.fetchall()
        conn.close()

        self.composition_table.setRowCount(len(composition))
        for row_idx, (comp_id, mat_name, mat_type, quantity, length) in enumerate(composition):
            self.composition_table.setItem(row_idx, 0, QTableWidgetItem(str(comp_id)))
            self.composition_table.setItem(row_idx, 1, QTableWidgetItem(mat_name))
            self.composition_table.setItem(row_idx, 2, QTableWidgetItem(mat_type))
            self.composition_table.setItem(row_idx, 3, QTableWidgetItem(str(quantity)))
            self.composition_table.setItem(row_idx, 4, QTableWidgetItem(str(length) if length else ""))

    def add_product(self):
        name = self.product_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название изделия")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO products (name) VALUES (?)", (name,))
            conn.commit()
            self.load_products()
            self.product_name_input.clear()
            QMessageBox.information(self, "Успех", "Изделие добавлено!")
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Ошибка", "Изделие с таким названием уже существует")
        finally:
            conn.close()

    def delete_product(self):
        selected_row = self.products_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите изделие для удаления")
            return

        product_id = int(self.products_table.item(selected_row, 0).text())
        product_name = self.products_table.item(selected_row, 1).text()

        reply = QMessageBox.question(self, "Подтверждение",
                                     f"Вы уверены, что хотите удалить изделие '{product_name}'?",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM product_composition WHERE product_id = ?", (product_id,))
                cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
                conn.commit()
                self.load_products()
                self.composition_group.setEnabled(False)
                self.composition_table.setRowCount(0)
                QMessageBox.information(self, "Успех", "Изделие удалено")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка базы данных", str(e))
            finally:
                conn.close()

    def add_to_composition(self):
        if not hasattr(self, 'selected_product_id'):
            QMessageBox.warning(self, "Ошибка", "Сначала выберите изделие")
            return

        material_id = self.material_combo.currentData()
        quantity = self.quantity_input.text().strip()
        length = self.length_input.text().strip()

        if not material_id or not quantity:
            QMessageBox.warning(self, "Ошибка", "Выберите материал и укажите количество")
            return

        try:
            quantity_val = int(quantity)
            length_val = float(length) if length else None
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Количество должно быть целым числом, длина - числом")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO product_composition (product_id, material_id, quantity, length) VALUES (?, ?, ?, ?)",
                (self.selected_product_id, material_id, quantity_val, length_val))
            conn.commit()
            self.load_composition()
            self.calculate_product_cost()
            QMessageBox.information(self, "Успех", "Материал добавлен в состав")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка базы данных", str(e))
        finally:
            conn.close()

    def remove_from_composition(self):
        selected_row = self.composition_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите материал для удаления")
            return

        comp_id = int(self.composition_table.item(selected_row, 0).text())
        material_name = self.composition_table.item(selected_row, 1).text()

        reply = QMessageBox.question(self, "Подтверждение",
                                     f"Удалить материал '{material_name}' из состава?",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM product_composition WHERE id = ?", (comp_id,))
            conn.commit()
            conn.close()
            self.load_composition()
            self.calculate_product_cost()
            QMessageBox.information(self, "Успех", "Материал удален из состава")

    def calculate_product_cost(self):
        if not hasattr(self, 'selected_product_id') or self.selected_product_id is None:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите изделие")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""SELECT m.price, pc.quantity, pc.length
                           FROM product_composition pc
                           JOIN materials m ON pc.material_id = m.id
                           WHERE pc.product_id = ?""", (self.selected_product_id,))
            composition = cursor.fetchall()

            total_cost = 0
            for row in composition:
                price, quantity, length = row
                if length:
                    total_cost += price * quantity * length
                else:
                    total_cost += price * quantity

            self.cost_label.setText(f"Себестоимость: {total_cost:.2f} руб")

            cursor.execute("UPDATE products SET cost = ? WHERE id = ?", (total_cost, self.selected_product_id))
            conn.commit()

            if self.main_window and hasattr(self.main_window, 'orders_tab'):
                if hasattr(self.main_window.orders_tab, 'product_cost_cache'):
                    if self.selected_product_id in self.main_window.orders_tab.product_cost_cache:
                        del self.main_window.orders_tab.product_cost_cache[self.selected_product_id]

        except Exception as e:
            QMessageBox.critical(self, "Ошибка расчета", f"Произошла ошибка: {str(e)}")
        finally:
            conn.close()

    def filter_table(self, text: str):
        """Скрывает строки, где не найден текст ни в одной ячейке."""
        text = text.lower()
        for r in range(self.products_table.rowCount()):  # НЕ self.table, А self.products_table
            row_text = " ".join(
                self.products_table.item(r, c).text().lower()  # НЕ self.table, А self.products_table
                for c in range(self.products_table.columnCount())  # НЕ self.table, А self.products_table
                if self.products_table.item(r, c)  # НЕ self.table, А self.products_table
            )
            self.products_table.setRowHidden(r, text not in row_text)  # НЕ self.table, А self.products_table


class WarehouseTab(QWidget):
    def __init__(self, db_path, main_window):
        super().__init__()
        self.db_path = db_path
        self.main_window = main_window
        self.repo_root = self.find_git_root(db_path)
        self.init_ui()
        self.load_data()

    @staticmethod
    def find_git_root(path):
        path = os.path.abspath(path)
        while True:
            if os.path.exists(os.path.join(path, '.git')):
                return path
            parent = os.path.dirname(path)
            if parent == path:
                return None
            path = parent

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Поисковое поле
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по складу…")
        self.search_input.textChanged.connect(self.filter_table)
        main_layout.addWidget(self.search_input)

        # Группа добавления
        add_group = QGroupBox("Добавить на склад")
        add_layout = QFormLayout()

        self.material_combo = QComboBox()
        # Подключаем автозаполнение
        self.material_combo.currentTextChanged.connect(self.on_warehouse_material_changed)
        self.load_materials()
        add_layout.addRow(QLabel("Материал:"), self.material_combo)

        # Поле длины
        self.length_input = QLineEdit()
        self.length_input.setPlaceholderText("0 для метизов, иначе длина в метрах")
        add_layout.addRow(QLabel("Длина:"), self.length_input)

        # Поле количества
        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("Количество")
        add_layout.addRow(QLabel("Количество:"), self.quantity_input)

        # Кнопка добавления
        self.add_btn = QPushButton("Добавить на склад")
        self.add_btn.clicked.connect(self.add_to_warehouse)
        add_layout.addRow(self.add_btn)

        add_group.setLayout(add_layout)
        main_layout.addWidget(add_group)

        # Таблица склада
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Материал", "Длина", "Количество"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        main_layout.addWidget(self.table)

        # Кнопка удаления
        btn_layout = QHBoxLayout()
        self.delete_btn = QPushButton("Удалить выбранное")
        self.delete_btn.clicked.connect(self.delete_item)
        btn_layout.addWidget(self.delete_btn)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)

    def git_pull(self):
        if self.repo_root is None:
            QMessageBox.critical(self, "Ошибка", "Git репозиторий не найден")
            return

        reply = QMessageBox.question(self, "Подтверждение",
                                     "Принудительный git pull может перезаписать локальные изменения. Продолжить?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.No:
            return

        try:
            result = subprocess.run(['git', 'fetch', 'origin'], cwd=self.repo_root,
                                    capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                QMessageBox.critical(self, "Ошибка", f"Ошибка при получении изменений:\n{error_msg}")
                return

            db_repo_path = 'data/database.db'
            reset_result = subprocess.run(['git', 'checkout', 'origin/master', '--', db_repo_path],
                                          cwd=self.repo_root, capture_output=True, text=True, timeout=30)

            if reset_result.returncode == 0:
                repo_db_path = os.path.join(self.repo_root, db_repo_path)
                if os.path.exists(repo_db_path):
                    import shutil
                    shutil.copy2(repo_db_path, self.db_path)
                    QMessageBox.information(self, "Успех", "Склад заполнился актуальными остатками")
                    self.main_window.reload_all_tabs()
                else:
                    QMessageBox.critical(self, "Ошибка", "Файл базы данных не найден в репозитории")
            else:
                error_msg = reset_result.stderr if reset_result.stderr else reset_result.stdout
                QMessageBox.critical(self, "Ошибка", f"Ошибка при обновлении файла:\n{error_msg}")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {str(e)}")

    def git_push(self):
        if self.repo_root is None:
            QMessageBox.critical(self, "Ошибка", "Git репозиторий не найден")
            return

        try:
            db_repo_path = 'data/database.db'
            repo_db_path = os.path.join(self.repo_root, db_repo_path)
            repo_db_dir = os.path.dirname(repo_db_path)

            if not os.path.exists(repo_db_dir):
                os.makedirs(repo_db_dir)

            import shutil
            shutil.copy2(self.db_path, repo_db_path)

            add_result = subprocess.run(['git', 'add', db_repo_path], cwd=self.repo_root,
                                        capture_output=True, text=True, timeout=30)

            if add_result.returncode != 0:
                error_msg = add_result.stderr if add_result.stderr else add_result.stdout
                QMessageBox.critical(self, "Ошибка", f"Ошибка при добавлении файла:\n{error_msg}")
                return

            status_result = subprocess.run(['git', 'status', '--porcelain', db_repo_path],
                                           cwd=self.repo_root, capture_output=True, text=True, timeout=30)

            if not status_result.stdout.strip():
                QMessageBox.information(self, "Информация", "Нет изменений в базе данных для коммита")
                return

            commit_result = subprocess.run(['git', 'commit', '-m', 'Update database from application', db_repo_path],
                                           cwd=self.repo_root, capture_output=True, text=True, timeout=30)

            if commit_result.returncode != 0 and "nothing to commit" not in commit_result.stderr:
                error_msg = commit_result.stderr if commit_result.stderr else commit_result.stdout
                QMessageBox.critical(self, "Ошибка", f"Ошибка при коммите:\n{error_msg}")
                return

            push_result = subprocess.run(['git', 'push', 'origin', 'master', '--force'],
                                         cwd=self.repo_root, capture_output=True, text=True, timeout=30)

            if push_result.returncode == 0:
                QMessageBox.information(self, "Успех", "Файл склада отправлен в репозиторий")
            else:
                error_msg = push_result.stderr if push_result.stderr else push_result.stdout
                QMessageBox.critical(self, "Ошибка", f"Ошибка при отправке:\n{error_msg}")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {str(e)}")

    def load_materials(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM materials")
        materials = cursor.fetchall()
        conn.close()

        self.material_combo.clear()
        for mat_id, mat_name in materials:
            self.material_combo.addItem(mat_name, mat_id)

    def load_data(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""SELECT w.id, m.name, w.length, w.quantity 
        FROM warehouse w
        JOIN materials m ON w.material_id = m.id
        ORDER BY m.name""")
        warehouse = cursor.fetchall()
        conn.close()

        self.table.setRowCount(len(warehouse))
        for row_idx, row_data in enumerate(warehouse):
            for col_idx, col_data in enumerate(row_data):
                item = QTableWidgetItem(str(col_data))
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.table.setItem(row_idx, col_idx, item)

    def add_to_warehouse(self):
        material_id = self.material_combo.currentData()
        length = self.length_input.text().strip()
        quantity = self.quantity_input.text().strip()

        if not material_id or not length or not quantity:
            QMessageBox.warning(self, "Ошибка", "Все поля обязательны для заполнения")
            return

        try:
            length_val = float(length)
            quantity_val = int(quantity)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Длина и количество должны быть числами")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT id FROM warehouse WHERE material_id = ? AND length = ?",
                           (material_id, length_val))
            existing = cursor.fetchone()

            if existing:
                cursor.execute("UPDATE warehouse SET quantity = quantity + ? WHERE id = ?",
                               (quantity_val, existing[0]))
            else:
                cursor.execute("INSERT INTO warehouse (material_id, length, quantity) VALUES (?, ?, ?)",
                               (material_id, length_val, quantity_val))

            conn.commit()
            self.load_data()
            self.length_input.clear()
            self.quantity_input.clear()
            QMessageBox.information(self, "Успех", "Склад обновлен!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка базы данных", str(e))
        finally:
            conn.close()

    def delete_item(self):
        selected_row = self.table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите запись для удаления")
            return

        item_id = int(self.table.item(selected_row, 0).text())

        reply = QMessageBox.question(self, "Подтверждение удаления",
                                     "Вы уверены, что хотите удалить эту запись?",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM warehouse WHERE id = ?", (item_id,))
            conn.commit()
            conn.close()
            self.load_data()
            QMessageBox.information(self, "Успех", "Запись удалена")

    def on_warehouse_material_changed(self, material_text):
        """
        Автозаполнение: при выборе метиза длина = 0 и блокируется,
        для пиломатериала поле активируется.
        """
        if not material_text:
            return
        try:
            material_id = self.material_combo.currentData()
            if not material_id:
                return
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT type FROM materials WHERE id = ?", (material_id,))
            result = cursor.fetchone()
            conn.close()
            if not result:
                return
            mat_type = result[0]
            if mat_type == "Метиз":
                self.length_input.setText("0")
                self.length_input.setEnabled(False)
                self.length_input.setToolTip("Длина для метизов всегда 0")
            else:
                self.length_input.setEnabled(True)
                if self.length_input.text() == "0":
                    self.length_input.clear()
                self.length_input.setToolTip("Введите длину в метрах")
        except Exception as e:
            print(f"Ошибка автозаполнения на складе: {e}")

    def filter_table(self, text: str):
        """Скрывает строки, где не найден текст ни в одной ячейке."""
        text = text.lower()
        for r in range(self.table.rowCount()):
            row_text = " ".join(
                self.table.item(r, c).text().lower()
                for c in range(self.table.columnCount())
                if self.table.item(r, c)
            )
            self.table.setRowHidden(r, text not in row_text)


class OrdersTab(QWidget):
    def __init__(self, db_path, main_window):
        super().__init__()
        self.db_path = db_path
        self.main_window = main_window
        self.init_ui()

        # ИСПРАВЛЕНИЕ 3: Загружаем изделия по умолчанию (так как "Изделие" выбрано по умолчанию)
        self.load_products()

        self.current_order = []
        self.product_cost_cache = {}
        self.stage_cost_cache = {}

    def init_ui(self):
        main_layout = QVBoxLayout()

        order_group = QGroupBox("Создать заказ")
        order_layout = QVBoxLayout()

        self.order_table = QTableWidget()
        self.order_table.setColumnCount(6)
        self.order_table.setHorizontalHeaderLabels(
            ["Тип", "Название", "Количество", "Длина (м)", "Себестоимость", "Действия"])
        self.order_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.order_table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        order_layout.addWidget(self.order_table)

        form_layout = QFormLayout()

        self.item_type_combo = QComboBox()
        self.item_type_combo.addItems(["Изделие", "Этап"])
        self.item_type_combo.currentTextChanged.connect(self.on_item_type_changed)
        form_layout.addRow(QLabel("Тип:"), self.item_type_combo)

        self.item_combo = QComboBox()
        form_layout.addRow(QLabel("Выберите:"), self.item_combo)

        self.quantity_spin = QSpinBox()
        self.quantity_spin.setMinimum(1)
        self.quantity_spin.setMaximum(999)
        self.quantity_spin.setValue(1)
        form_layout.addRow(QLabel("Количество:"), self.quantity_spin)

        self.length_spin = QDoubleSpinBox()
        self.length_spin.setDecimals(2)
        self.length_spin.setMinimum(0.01)
        self.length_spin.setMaximum(9999.0)
        self.length_spin.setSingleStep(0.10)
        form_layout.addRow(QLabel("Длина (м):"), self.length_spin)
        self.length_spin.hide()  # по умолчанию скрыто (для Изделия)

        self.add_to_order_btn = QPushButton("Добавить в заказ")
        self.add_to_order_btn.clicked.connect(self.add_to_order)
        form_layout.addRow(self.add_to_order_btn)

        order_layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        self.calculate_btn = QPushButton("Рассчитать заказ")
        self.calculate_btn.clicked.connect(self.calculate_order)
        btn_layout.addWidget(self.calculate_btn)

        self.confirm_btn = QPushButton("Подтвердить заказ")
        self.confirm_btn.clicked.connect(self.confirm_order)
        btn_layout.addWidget(self.confirm_btn)

        self.clear_btn = QPushButton("Очистить заказ")
        self.clear_btn.clicked.connect(self.clear_order)
        btn_layout.addWidget(self.clear_btn)

        order_layout.addLayout(btn_layout)

        self.instructions_text = QTextEdit()
        self.instructions_text.setReadOnly(True)
        self.instructions_text.setMinimumHeight(150)
        order_layout.addWidget(QLabel("Окно сообщений:"))
        order_layout.addWidget(self.instructions_text)

        self.total_cost_label = QLabel("Общая себестоимость: 0.00 руб")
        self.total_cost_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        order_layout.addWidget(self.total_cost_label)

        order_group.setLayout(order_layout)
        main_layout.addWidget(order_group)

        history_group = QGroupBox("История заказов")
        history_layout = QVBoxLayout()
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["ID", "Дата", "Позиций", "Сумма"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.cellDoubleClicked.connect(self.show_order_details)
        history_layout.addWidget(self.history_table)

        history_buttons_layout = QHBoxLayout()
        self.open_pdf_btn = QPushButton("Открыть PDF")
        self.open_pdf_btn.clicked.connect(self.open_selected_pdf)
        history_buttons_layout.addWidget(self.open_pdf_btn)

        self.refresh_history_btn = QPushButton("Обновить историю")
        self.refresh_history_btn.clicked.connect(self.load_order_history)
        history_buttons_layout.addWidget(self.refresh_history_btn)
        history_buttons_layout.addStretch()
        history_layout.addLayout(history_buttons_layout)

        history_group.setLayout(history_layout)
        main_layout.addWidget(history_group)

        # ДОБАВЛЯЕМ КНОПКУ РАСЧЕТА СТРАХОВОЧНОГО ТРОСА
        self.calculate_rope_btn = QPushButton("Рассчитать и добавить страховочный трос к заказу")
        self.calculate_rope_btn.clicked.connect(self.calculate_safety_rope)
        btn_layout.addWidget(self.calculate_rope_btn)

        self.setLayout(main_layout)

    def calculate_rope_materials(self, routes):
        """
        Исправленный расчет материалов страховочного троса.
        Теперь правильно работает с полными трассами, включая динамические этапы.
        """
        total_rope = 0.0
        total_clamps = 0

        for route in routes:
            if not route:  # Пустая трасса
                continue

            # Разбиваем трассу на сегменты (как в show_preview)
            segments = []
            current_segment = None

            for stage in route:
                stage_type = 'static' if stage['category'] == 'Статика' else 'dynamic'

                if current_segment is None or current_segment['type'] != stage_type:
                    # Начинаем новый сегмент
                    current_segment = {'type': stage_type, 'stages': [stage]}
                    segments.append(current_segment)
                else:
                    # Продолжаем текущий сегмент
                    current_segment['stages'].append(stage)

            # Рассчитываем трос только для статических сегментов
            for segment in segments:
                if segment['type'] == 'static':
                    N = len(segment['stages'])
                    L = sum(stage['length'] for stage in segment['stages'])
                    rope = 5 + 5 * N + L
                    clamps = 6 + 6 * N
                    total_rope += rope
                    total_clamps += clamps

        return total_rope, total_clamps

    def calculate_safety_rope(self):
        """Рассчитывает и добавляет страховочный трос в заказ"""
        # Получаем все этапы из заказа
        stages_in_order = []
        for row in range(self.order_table.rowCount()):
            if self.order_table.item(row, 0) and self.order_table.item(row, 0).text() == "Этап":
                stage_id = self.order_table.item(row, 1).data(Qt.UserRole) if self.order_table.item(row, 1) else None
                stage_name = self.order_table.item(row, 1).text() if self.order_table.item(row,
                                                                                           1) else "Неизвестный этап"
                length_text = self.order_table.item(row, 3).text() if self.order_table.item(row, 3) else "0"

                try:
                    length = float(length_text)
                except (ValueError, AttributeError):
                    length = 0.0

                if stage_id:
                    # Получаем категорию этапа
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT category FROM stages WHERE id = ?", (stage_id,))
                    result = cursor.fetchone()
                    category = result[0] if result else "Статика"
                    conn.close()

                    stages_in_order.append({
                        'id': stage_id,
                        'name': stage_name,
                        'length': length,
                        'category': category
                    })

        if not stages_in_order:
            QMessageBox.warning(self, "Ошибка", "В заказе нет этапов для расчета страховочного троса")
            return

        # Проверяем, есть ли статические этапы
        static_stages = [s for s in stages_in_order if s['category'] == 'Статика']
        if not static_stages:
            QMessageBox.information(self, "Информация",
                                    f"В заказе только динамические/зип этапы ({len(stages_in_order)} шт.).\n"
                                    "Страховочный трос не требуется.")
            return

        dynamic_count = len(stages_in_order) - len(static_stages)
        info_msg = f"В заказе:\n• Статических этапов: {len(static_stages)}\n• Динамических/Зип: {dynamic_count}"

        # Открываем диалог планирования трасс
        dialog = RoutesPlanningDialog(stages_in_order, self)

        # Показываем информацию перед планированием
        QMessageBox.information(self, "Планирование трасс",
                                f"{info_msg}\n\nСейчас откроется окно планирования трасс.\n"
                                "Динамические этапы разрывают страховочный трос!")

        if dialog.exec_() == QDialog.Accepted:
            routes = dialog.get_routes()
            if routes:
                total_rope, total_clamps = self.calculate_rope_materials(routes)
                self.add_rope_to_order(total_rope, total_clamps)

                # Показываем детальный отчет
                routes_info = f"Создано трасс троса: {len(routes)}\n"
                for i, route in enumerate(routes, 1):
                    routes_info += f"Трасса {i}: {len(route)} этапов\n"

                QMessageBox.information(self, "Расчет завершен",
                                        f"{routes_info}\nДобавлено:\n"
                                        f"• Трос М12: {total_rope:.2f} м\n"
                                        f"• Зажимы М12: {total_clamps} шт")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось создать трассы для страховочного троса")

    def add_rope_to_order(self, rope_length, clamps_count):
        """Исправленный метод добавления материалов страховочного троса в заказ"""
        try:
            # Получаем ID материалов из БД
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, price FROM materials WHERE name = 'Трос М12'")
            rope_result = cursor.fetchone()
            cursor.execute("SELECT id, price FROM materials WHERE name = 'Зажим М12'")
            clamp_result = cursor.fetchone()
            conn.close()

            if not rope_result or not clamp_result:
                QMessageBox.warning(self, "Ошибка",
                                    "Материалы 'Трос М12' или 'Зажим М12' не найдены в базе данных.\n"
                                    "Добавьте эти материалы в раздел 'Материалы'")
                return

            rope_id, rope_price = rope_result
            clamp_id, clamp_price = clamp_result

            # Добавляем позиции в заказ
            for material_name, material_id, amount, price in [
                ("Трос М12", rope_id, rope_length, rope_price),
                ("Зажим М12", clamp_id, clamps_count, clamp_price),
            ]:
                row = self.order_table.rowCount()
                self.order_table.insertRow(row)

                # Тип позиции
                self.order_table.setItem(row, 0, QTableWidgetItem("Материал"))

                # Название с ID в данных
                item = QTableWidgetItem(material_name)
                item.setData(Qt.UserRole, material_id)
                self.order_table.setItem(row, 1, item)

                # Количество (округляем зажимы до целого числа)
                quantity_text = f"{amount:.2f}" if material_name.startswith("Трос") else str(int(amount))
                self.order_table.setItem(row, 2, QTableWidgetItem(quantity_text))

                # Длина (пустая для материалов)
                self.order_table.setItem(row, 3, QTableWidgetItem(""))

                # Стоимость
                total_cost = amount * price
                self.order_table.setItem(row, 4, QTableWidgetItem(f"{total_cost:.2f} руб"))

                # Кнопка удаления
                delete_btn = QPushButton("Удалить")
                delete_btn.clicked.connect(partial(self.remove_from_order, row))
                self.order_table.setCellWidget(row, 5, delete_btn)

            # Обновляем кнопки удаления для всех строк
            for r in range(self.order_table.rowCount()):
                widget = self.order_table.cellWidget(r, 5)
                if isinstance(widget, QPushButton):
                    widget.clicked.disconnect()
                    widget.clicked.connect(partial(self.remove_from_order, r))

            self.update_total_cost()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при добавлении троса: {str(e)}")

    def on_item_type_changed(self, item_type):
        """Переключение между Изделием и Этапом с показом поля длины для этапа"""
        self.item_combo.clear()
        if item_type == "Изделие":
            self.length_spin.hide()
            self.quantity_spin.show()
            self.load_products()
        else:
            self.length_spin.show()
            self.quantity_spin.hide()
            self.load_stages()

    def load_products(self):
        """Загружает ТОЛЬКО изделия в выпадающий список"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM products ORDER BY name")
        products = cursor.fetchall()
        conn.close()

        # Очищаем и заполняем список изделиями
        self.item_combo.clear()
        for prod_id, prod_name in products:
            self.item_combo.addItem(prod_name, prod_id)

    def load_stages(self):
        """Загружает ТОЛЬКО этапы в выпадающий список"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM stages ORDER BY name")
        stages = cursor.fetchall()
        conn.close()

        # Очищаем и заполняем список этапами
        self.item_combo.clear()
        for stage_id, stage_name in stages:
            self.item_combo.addItem(stage_name, stage_id)

    def add_to_order(self):
        """Добавление позиции в заказ: для Этапа учитываем длину, для Изделия — количество"""
        item_id = self.item_combo.currentData()
        item_name = self.item_combo.currentText()
        item_type = self.item_type_combo.currentText()

        if not item_id:
            QMessageBox.warning(self, "Ошибка", f"Выберите {item_type.lower()}")
            return

        if item_type == "Изделие":
            quantity = self.quantity_spin.value()
            cost_per_unit = self._get_product_cost(item_id)

            row_count = self.order_table.rowCount()
            self.order_table.setRowCount(row_count + 1)

            self.order_table.setItem(row_count, 0, QTableWidgetItem(item_type))

            name_item = QTableWidgetItem(item_name)
            name_item.setData(Qt.UserRole, item_id)
            name_item.setData(Qt.UserRole + 1, item_type)
            self.order_table.setItem(row_count, 1, name_item)

            self.order_table.setItem(row_count, 2, QTableWidgetItem(str(quantity)))
            self.order_table.setItem(row_count, 3, QTableWidgetItem(""))  # длина пустая для изделия
            self.order_table.setItem(row_count, 4, QTableWidgetItem(f"{cost_per_unit * quantity:.2f} руб"))

            delete_btn = QPushButton("Удалить")
            delete_btn.clicked.connect(lambda: self.remove_from_order(row_count))
            self.order_table.setCellWidget(row_count, 5, delete_btn)

        else:  # Этап
            # ИСПРАВЛЕНО: НЕ округляем длину, сохраняем точное значение
            length_m = self.length_spin.value()  # Убрано round()

            if length_m <= 0:
                QMessageBox.warning(self, "Ошибка", "Длина этапа должна быть больше 0")
                return

            cost_total = self._compute_stage_cost(stage_id=item_id, length_m=length_m)

            row_count = self.order_table.rowCount()
            self.order_table.setRowCount(row_count + 1)

            self.order_table.setItem(row_count, 0, QTableWidgetItem(item_type))

            name_item = QTableWidgetItem(item_name)
            name_item.setData(Qt.UserRole, item_id)
            name_item.setData(Qt.UserRole + 1, item_type)
            name_item.setData(Qt.UserRole + 2, length_m)  # сохраним точную длину
            self.order_table.setItem(row_count, 1, name_item)

            self.order_table.setItem(row_count, 2, QTableWidgetItem("1"))  # количество строкой = 1 для этапа

            # ИСПРАВЛЕНО: показываем точную длину с 2 знаками после запятой
            self.order_table.setItem(row_count, 3, QTableWidgetItem(f"{length_m:.2f}"))
            self.order_table.setItem(row_count, 4, QTableWidgetItem(f"{cost_total:.2f} руб"))

            delete_btn = QPushButton("Удалить")
            delete_btn.clicked.connect(lambda: self.remove_from_order(row_count))
            self.order_table.setCellWidget(row_count, 5, delete_btn)

        self._update_current_order()
        self.update_total_cost()

    def _get_product_cost(self, product_id):
        if product_id in self.product_cost_cache:
            return self.product_cost_cache[product_id]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT cost FROM products WHERE id = ?", (product_id,))
        cost = cursor.fetchone()[0]
        conn.close()

        self.product_cost_cache[product_id] = cost
        return cost

    def _get_stage_cost(self, stage_id):
        if stage_id in self.stage_cost_cache:
            return self.stage_cost_cache[stage_id]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT cost FROM stages WHERE id = ?", (stage_id,))
        cost = cursor.fetchone()[0]
        conn.close()

        self.stage_cost_cache[stage_id] = cost
        return cost

    def _update_current_order(self):
        self.current_order = []
        for row in range(self.order_table.rowCount()):
            item_type = self.order_table.item(row, 0).text()
            item_id = int(self.order_table.item(row, 1).data(Qt.UserRole))
            quantity = int(self.order_table.item(row, 2).text())
            self.current_order.append((item_type, item_id, quantity))

    def remove_from_order(self, row):
        """Безопасно удаляет строку и обновляет индексы кнопок."""
        if 0 <= row < self.order_table.rowCount():
            self.order_table.removeRow(row)
            # Перепривязываем все лямбды удаления с новыми индексами
            for r in range(self.order_table.rowCount()):
                widget = self.order_table.cellWidget(r, 5)
                if isinstance(widget, QPushButton):
                    widget.clicked.disconnect()
                    widget.clicked.connect(partial(self.remove_from_order, r))
            self.update_total_cost()

    def on_cell_double_clicked(self, row, column):
        # Редактирование количества для изделия и длины (м) для этапа
        item_type = self.order_table.item(row, 0).text()
        item_id = int(self.order_table.item(row, 1).data(Qt.UserRole))

        if item_type == "Изделие" and column == 2:
            dialog = QDialog(self)
            dialog.setWindowTitle("Изменение количества")
            dialog.setFixedSize(300, 150)
            layout = QVBoxLayout()
            item_name = self.order_table.item(row, 1).text()
            layout.addWidget(QLabel(f"Позиция: {item_name}"))
            spin_box = QSpinBox()
            spin_box.setMinimum(1)
            spin_box.setMaximum(999)
            spin_box.setValue(int(self.order_table.item(row, 2).text()))
            layout.addWidget(QLabel("Новое количество:"))
            layout.addWidget(spin_box)
            btn_layout = QHBoxLayout()
            ok_btn = QPushButton("OK");
            cancel_btn = QPushButton("Отмена")
            ok_btn.clicked.connect(dialog.accept);
            cancel_btn.clicked.connect(dialog.reject)
            btn_layout.addWidget(ok_btn);
            btn_layout.addWidget(cancel_btn)
            layout.addLayout(btn_layout)
            dialog.setLayout(layout)
            if dialog.exec_() == QDialog.Accepted:
                new_quantity = spin_box.value()
                self.order_table.item(row, 2).setText(str(new_quantity))
                cost_per_unit = self._get_product_cost(item_id)
                new_cost = cost_per_unit * new_quantity
                self.order_table.item(row, 4).setText(f"{new_cost:.2f} руб")
                self._update_current_order()
                self.update_total_cost()

        if item_type == "Этап" and column == 3:
            dialog = QDialog(self)
            dialog.setWindowTitle("Изменение длины (м)")
            dialog.setFixedSize(320, 160)
            layout = QVBoxLayout()
            item_name = self.order_table.item(row, 1).text()
            layout.addWidget(QLabel(f"Этап: {item_name}"))

            spin = QDoubleSpinBox()
            spin.setDecimals(2)  # ИСПРАВЛЕНО: 2 знака после запятой
            spin.setMinimum(0.01)
            spin.setMaximum(9999.0)
            spin.setSingleStep(0.01)  # ИСПРАВЛЕНО: шаг 0.01 вместо 0.10

            current_len_text = self.order_table.item(row, 3).text() or "0"
            try:
                current_len = float(current_len_text)
            except ValueError:
                current_len = 1.00
            spin.setValue(current_len if current_len > 0 else 1.00)

            layout.addWidget(QLabel("Новая длина (м):"))
            layout.addWidget(spin)
            btn_layout = QHBoxLayout()
            ok_btn = QPushButton("OK")
            cancel_btn = QPushButton("Отмена")
            ok_btn.clicked.connect(dialog.accept)
            cancel_btn.clicked.connect(dialog.reject)
            btn_layout.addWidget(ok_btn)
            btn_layout.addWidget(cancel_btn)
            layout.addLayout(btn_layout)
            dialog.setLayout(layout)

            if dialog.exec_() == QDialog.Accepted:
                # ИСПРАВЛЕНО: НЕ округляем новую длину
                new_len = spin.value()  # Убрано round()
                self.order_table.item(row, 3).setText(f"{new_len:.2f}")

                # пересчёт стоимости строки с точной длиной
                new_cost = self._compute_stage_cost(item_id, new_len)
                self.order_table.item(row, 4).setText(f"{new_cost:.2f} руб")

                # обновим сохранённую длину в UserRole+2 у названия
                name_item = self.order_table.item(row, 1)
                name_item.setData(Qt.UserRole + 2, new_len)  # Сохраняем точную длину

                self._update_current_order()
                self.update_total_cost()

    def update_total_cost(self):
        total = 0.0
        for row in range(self.order_table.rowCount()):
            cost_text = self.order_table.item(row, 4).text().replace(' руб', '')
            total += float(cost_text or 0)
        self.total_cost_label.setText(f"Общая себестоимость: {total:.2f} руб")

    def clear_order(self):
        self.order_table.setRowCount(0)
        self.current_order = []
        self.instructions_text.clear()
        self.total_cost_label.setText("Общая себестоимость: 0.00 руб")

    def calculate_order(self):
        if not self.current_order:
            QMessageBox.warning(self, "Ошибка", "Заказ пуст")
            return

        total_cost, requirements = self._expand_order_to_requirements()
        stock_items = self._get_current_stock()

        optimizer = CuttingOptimizer()
        result = optimizer.optimize_cutting(requirements, stock_items, self.db_path)

        materials_message = "📦 Требуемые материалы:\n\n"
        # Суммарные количества по материалам (м или шт) уже можно получить, если нужно, отдельно
        for material, items in requirements.items():
            # подсчитать сумму значений по материалу
            amount = 0.0
            # определяем тип по наличию длин (float) против шт (int)
            is_length = any(
                isinstance(val, float) and val > 0 and not float(val).is_integer() or isinstance(val, float) for val, _
                in items)
            for val, _ in items:
                amount += float(val)
            unit = "м" if is_length else "шт"
            materials_message += f"▫️ {material}: {amount:.2f} {unit}\n"

        if result['can_produce']:
            availability_message = "\n✅ Материалов достаточно для производства"
        else:
            availability_message = "\n❌ Материалов недостаточно:\n"
            for error in result['missing']:
                availability_message += f" - {error}\n"

        instructions = "📊 Расчет заказа:\n\n"
        instructions += f"💰 Себестоимость: {total_cost:.2f} руб\n"
        instructions += f"💰 Цена реализации: {total_cost * 2:.2f} руб\n\n"
        instructions += materials_message
        instructions += availability_message

        self.instructions_text.setText(instructions)
        self.total_cost_label.setText(f"Общая себестоимость: {total_cost:.2f} руб")

    def _expand_order_to_requirements(self, order_items):
        """
        Исправленный метод преобразования заказа в требования по материалам
        """
        requirements = defaultdict(list)
        total_cost = 0.0

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        for item_type, item_id, quantity, length_m in order_items:
            if item_type == "Изделие":
                # Обрабатываем изделие
                c.execute("SELECT cost FROM products WHERE id = ?", (item_id,))
                cost_row = c.fetchone()
                if cost_row:
                    total_cost += cost_row[0] * quantity

                # Материалы изделия
                c.execute("""SELECT m.name, m.type, pc.quantity, pc.length
                            FROM product_composition pc 
                            JOIN materials m ON pc.material_id = m.id
                            WHERE pc.product_id = ?""", (item_id,))

                product_name = self._get_product_name(item_id)

                for mname, mtype, q, length in c.fetchall():
                    if mtype == "Пиломатериал" and length:
                        # Для пиломатериалов: каждый кусок отдельно
                        total_pieces = q * quantity
                        for _ in range(int(total_pieces)):
                            requirements[mname].append((float(length), product_name))
                    else:
                        # Для метизов: общее количество
                        total_quantity = math.ceil(q * quantity)
                        requirements[mname].append((total_quantity, product_name))

            else:  # item_type == "Этап"
                # Обрабатываем этап
                stage_cost = self._compute_stage_cost(item_id, length_m)
                total_cost += stage_cost

                # Материалы напрямую из этапа
                c.execute("""SELECT sm.part, sm.quantity, sm.length, m.name, m.type
                            FROM stage_materials sm 
                            JOIN materials m ON sm.material_id = m.id
                            WHERE sm.stage_id = ?""", (item_id,))

                for part, sm_qty, sm_length, mname, mtype in c.fetchall():
                    multiplier = 1 if part in ('start', 'end') else length_m

                    if mtype == "Пиломатериал" and sm_length:
                        total_pieces = sm_qty * multiplier
                        for _ in range(math.ceil(total_pieces)):
                            requirements[mname].append((float(sm_length), f"Этап({part})→Материал"))
                    else:
                        total_quantity = math.ceil(sm_qty * multiplier)
                        requirements[mname].append((total_quantity, f"Этап({part})→Материал"))

                # Материалы через изделия этапа
                c.execute("""SELECT sp.part, sp.quantity, p.id, p.name
                            FROM stage_products sp 
                            JOIN products p ON sp.product_id = p.id
                            WHERE sp.stage_id = ?""", (item_id,))

                for part, sp_qty, prod_id, prod_name in c.fetchall():
                    multiplier = 1 if part in ('start', 'end') else length_m

                    c2 = conn.cursor()
                    c2.execute("""SELECT m.name, m.type, pc.quantity, pc.length
                                FROM product_composition pc 
                                JOIN materials m ON pc.material_id = m.id
                                WHERE pc.product_id = ?""", (prod_id,))

                    for mname, mtype, q, length in c2.fetchall():
                        if mtype == "Пиломатериал" and length:
                            total_pieces = q * sp_qty * multiplier
                            for _ in range(math.ceil(total_pieces)):
                                requirements[mname].append((float(length), f"Этап({part})→{prod_name}"))
                        else:
                            total_quantity = math.ceil(q * sp_qty * multiplier)
                            requirements[mname].append((total_quantity, f"Этап({part})→{prod_name}"))

        conn.close()
        return total_cost, requirements

    def _get_product_name(self, product_id: int) -> str:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM products WHERE id = ?", (product_id,))
        row = c.fetchone()
        conn.close()
        return row if row else f"Изделие #{product_id}"

    def _compute_stage_cost(self, stage_id: int, length_m: float) -> float:
        """
        Рассчитывает стоимость этапа заданной длины.

        Формула: (start_cost + end_cost) + meter_cost * length_m
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Получаем стоимость изделий по частям
            cursor.execute("""
                SELECT sp.part, p.cost, sp.quantity
                FROM stage_products sp  
                JOIN products p ON sp.product_id = p.id
                WHERE sp.stage_id = ?
            """, (stage_id,))

            start_cost = meter_cost = end_cost = 0.0
            for part, pcost, qty in cursor.fetchall():
                cost_contribution = pcost * qty
                if part == 'start':
                    start_cost += cost_contribution
                elif part == 'meter':
                    meter_cost += cost_contribution
                else:  # end
                    end_cost += cost_contribution

            # Получаем стоимость материалов по частям
            cursor.execute("""
                SELECT sm.part, m.type, m.price, sm.quantity, sm.length
                FROM stage_materials sm
                JOIN materials m ON sm.material_id = m.id  
                WHERE sm.stage_id = ?
            """, (stage_id,))

            for part, mtype, price, qty, length in cursor.fetchall():
                if mtype == "Пиломатериал" and length:
                    cost_contribution = price * qty * length
                else:
                    cost_contribution = price * qty

                if part == 'start':
                    start_cost += cost_contribution
                elif part == 'meter':
                    meter_cost += cost_contribution
                else:  # end
                    end_cost += cost_contribution

            conn.close()

            # Общая стоимость = фиксированные части + метровая часть * длина
            total_cost = start_cost + end_cost + (meter_cost * length_m)
            return total_cost

        except Exception as e:
            print(f"Ошибка расчета стоимости этапа {stage_id}: {e}")
            return 0.0

    def _get_row_length_for_stage(self, stage_id: int) -> float:
        # ищем строку в таблице заказа с этим stage_id и читаем колонку "Длина (м)"
        for row in range(self.order_table.rowCount()):
            if self.order_table.item(row, 0).text() == "Этап":
                name_item = self.order_table.item(row, 1)
                if int(name_item.data(Qt.UserRole)) == stage_id:
                    # сначала смотрим сохранённое значение
                    saved = name_item.data(Qt.UserRole + 2)
                    if saved is not None:
                        return float(saved)
                    # иначе читаем из ячейки
                    txt = self.order_table.item(row, 3).text() or "0"
                    try:
                        return float(txt)
                    except Exception:
                        return 0.0
        return 0.0

    def _get_stage_materials(self, stage_id, quantity):
        materials_summary = defaultdict(float)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Материалы из изделий в этапе
        cursor.execute("""
        SELECT m.name, m.type, pc.quantity, pc.length, sp.quantity as stage_qty
        FROM stage_products sp
        JOIN product_composition pc ON sp.product_id = pc.product_id
        JOIN materials m ON pc.material_id = m.id
        WHERE sp.stage_id = ?
        """, (stage_id,))

        for name, mtype, comp_quantity, length, stage_qty in cursor.fetchall():
            total_qty = comp_quantity * stage_qty * quantity
            if mtype == "Пиломатериал" and length:
                materials_summary[name] += total_qty * length
            else:
                materials_summary[name] += total_qty

        # Материалы напрямую в этапе
        cursor.execute("""
        SELECT m.name, m.type, sm.quantity, sm.length
        FROM stage_materials sm
        JOIN materials m ON sm.material_id = m.id
        WHERE sm.stage_id = ?
        """, (stage_id,))

        for name, mtype, sm_quantity, length in cursor.fetchall():
            total_qty = sm_quantity * quantity
            if mtype == "Пиломатериал" and length:
                materials_summary[name] += total_qty * length
            else:
                materials_summary[name] += total_qty

        conn.close()
        return materials_summary

    def _calculate_material_requirements(self):
        requirements = defaultdict(list)

        for item_type, item_id, quantity in self.current_order:
            if item_type == "Изделие":
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute("SELECT name FROM products WHERE id = ?", (item_id,))
                product_name = cursor.fetchone()[0]

                cursor.execute("""SELECT m.name, m.type, pc.quantity, pc.length
                FROM product_composition pc
                JOIN materials m ON pc.material_id = m.id
                WHERE pc.product_id = ?""", (item_id,))

                for material, mtype, comp_quantity, length in cursor.fetchall():
                    if mtype == "Пиломатериал" and length:
                        for _ in range(int(comp_quantity * quantity)):
                            requirements[material].append((length, product_name))
                    else:
                        requirements[material].append((comp_quantity * quantity, product_name))
                conn.close()

            else:  # Этап
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute("SELECT name FROM stages WHERE id = ?", (item_id,))
                stage_name = cursor.fetchone()[0]

                # Материалы из изделий в этапе
                cursor.execute("""
                SELECT m.name, m.type, pc.quantity, pc.length, sp.quantity as stage_qty, p.name as product_name
                FROM stage_products sp
                JOIN products p ON sp.product_id = p.id
                JOIN product_composition pc ON sp.product_id = pc.product_id
                JOIN materials m ON pc.material_id = m.id
                WHERE sp.stage_id = ?
                """, (item_id,))

                for material, mtype, comp_qty, length, stage_qty, product_name in cursor.fetchall():
                    total_qty = comp_qty * stage_qty * quantity
                    item_description = f"{stage_name}({product_name})"

                    if mtype == "Пиломатериал" and length:
                        for _ in range(int(total_qty)):
                            requirements[material].append((length, item_description))
                    else:
                        requirements[material].append((total_qty, item_description))

                # Материалы напрямую в этапе
                cursor.execute("""
                SELECT m.name, m.type, sm.quantity, sm.length
                FROM stage_materials sm
                JOIN materials m ON sm.material_id = m.id
                WHERE sm.stage_id = ?
                """, (item_id,))

                for material, mtype, sm_quantity, length in cursor.fetchall():
                    total_qty = sm_quantity * quantity
                    if mtype == "Пиломатериал" and length:
                        for _ in range(int(total_qty)):
                            requirements[material].append((length, stage_name))
                    else:
                        requirements[material].append((total_qty, stage_name))

                conn.close()

        return requirements

    def _get_current_stock(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                'SELECT m.name, w.length, w.quantity FROM warehouse w JOIN materials m ON w.material_id = m.id')
            return cursor.fetchall()
        finally:
            if conn:
                conn.close()

    def confirm_order(self):
        """Подтверждение заказа с учётом длины этапов и сохранением length_meters"""
        try:
            if not self.current_order:
                QMessageBox.warning(self, "Ошибка", "Заказ пуст")
                return

            total_cost = 0.0
            order_details = []

            for item_type, item_id, quantity in self.current_order:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                if item_type == "Изделие":
                    cursor.execute("SELECT name, cost FROM products WHERE id = ?", (item_id,))
                    name, cost = cursor.fetchone()
                    total_cost += cost * quantity
                    order_details.append(('product', item_id, name, quantity, cost * quantity, None))
                else:
                    cursor.execute("SELECT name FROM stages WHERE id = ?", (item_id,))
                    row_stage = cursor.fetchone()
                    name = row_stage if row_stage else f"Этап #{item_id}"
                    length_m = self._get_row_length_for_stage(item_id)
                    cost = self._compute_stage_cost(item_id, length_m)
                    total_cost += cost
                    order_details.append(('stage', item_id, name, 1, cost, length_m))

                conn.close()

            # Единая сборка требований для раскроя
            _, requirements = self._expand_order_to_requirements()

            stock_items = self._get_current_stock()
            optimizer = CuttingOptimizer()
            result = optimizer.optimize_cutting(requirements, stock_items, self.db_path)

            if not result['can_produce']:
                error_msg = "Недостаточно материалов:\n" + "\n".join(result['missing'])
                QMessageBox.critical(self, "Ошибка", error_msg)
                return

            self._update_warehouse(result['updated_warehouse'])
            if hasattr(self.main_window, 'warehouse_tab'):
                self.main_window.warehouse_tab.load_data()

            instructions_text = self._generate_instructions_text(total_cost, result, requirements)
            order_id = self._save_order_to_db(total_cost, order_details, instructions_text)
            self._generate_pdf(order_id, total_cost, order_details, requirements, instructions_text)

            self.clear_order()
            self.load_order_history()
            self.instructions_text.setText("Заказ подтвержден, PDF-отчёт сформирован.\nСклад был обновлен.")
            QMessageBox.information(self, "Успех", "Заказ успешно подтвержден!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Произошла критическая ошибка: {str(e)}")

    def _update_warehouse(self, updated_data):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM warehouse")
            for material, length, quantity in updated_data:
                cursor.execute("SELECT id FROM materials WHERE name = ?", (material,))
                result = cursor.fetchone()

                if result and quantity > 0:
                    mat_id = result[0]
                    cursor.execute("INSERT INTO warehouse (material_id, length, quantity) VALUES (?, ?, ?)",
                                   (mat_id, length, quantity))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении склада: {e}")
            conn.rollback()
        finally:
            conn.close()

    def _save_order_to_db(self, total_cost, order_details, instructions_text):
        """Сохранение заказа, включая длину этапов в order_items.length_meters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        order_id = None

        try:
            cursor.execute(
                "INSERT INTO orders (order_date, total_cost, instructions) VALUES (datetime('now'), ?, ?)",
                (total_cost, instructions_text)
            )
            order_id = cursor.lastrowid

            # order_details: (item_type, item_id, name, quantity, cost, length_meters_or_None)
            for item_type, item_id, name, quantity, cost, length_m in order_details:
                if item_type == 'product':
                    name = str(name)
                    cursor.execute(
                        """INSERT INTO order_items
                        (order_id, product_id, stage_id, quantity, length_meters, product_name, cost, item_type)
                        VALUES (?, ?, NULL, ?, NULL, ?, ?, ?)""",
                        (order_id, item_id, quantity, name, cost, 'product')
                    )
                else:
                    name = str(name)
                    cursor.execute(
                        """INSERT INTO order_items
                        (order_id, product_id, stage_id, quantity, length_meters, product_name, cost, item_type)
                        VALUES (?, NULL, ?, ?, ?, ?, ?, ?)""",
                        (order_id, item_id, 1, length_m, name, cost, 'stage')
                    )
            conn.commit()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка базы данных", f"Ошибка при сохранении заказа: {str(e)}")
            conn.rollback()
        finally:
            conn.close()
        return order_id

    def _generate_pdf(self, order_id, total_cost, order_details, requirements, instructions_text):
        try:
            if getattr(sys, 'frozen', False):
                pdf_dir = os.path.join(os.path.dirname(sys.executable), 'orders')
            else:
                pdf_dir = os.path.join(os.path.dirname(self.db_path), 'orders')

            if not os.path.exists(pdf_dir):
                os.makedirs(pdf_dir)

            pdf_filename = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_order.pdf"
            pdf_path = os.path.join(pdf_dir, pdf_filename)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE orders SET pdf_filename = ? WHERE id = ?", (pdf_filename, order_id))
            conn.commit()
            conn.close()

            doc = SimpleDocTemplate(pdf_path, pagesize=letter)
            styles = getSampleStyleSheet()
            if ARIAL_FONT_REGISTERED:
                from reportlab.lib.styles import ParagraphStyle
                title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontName='Arial', fontSize=16,
                                             spaceAfter=12)
                heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontName='Arial',
                                               fontSize=14, spaceAfter=6)
                normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontName='Arial', fontSize=12)
            else:
                title_style = styles['Title']
                heading_style = styles['Heading2']
                normal_style = styles['Normal']

            story = []
            story.append(Paragraph(f"Заказ от {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", title_style))
            story.append(Spacer(1, 12))

            sale_price = total_cost * 2
            story.append(Paragraph(f"Себестоимость: {total_cost:.2f} руб", heading_style))
            story.append(Paragraph(f"Цена реализации: {sale_price:.2f} руб", heading_style))
            story.append(Spacer(1, 12))

            # Состав заказа (печатаем длину для этапов)
            story.append(Paragraph("Состав заказа:", heading_style))
            for item_type, _, name, quantity, cost, length_m in order_details:
                type_text = "Изделие" if item_type == 'product' else "Этап"
                line = f"- {name} ({type_text}): {quantity} шт"
                if item_type == 'stage' and length_m:
                    line += f", длина {length_m:.2f} м"
                story.append(Paragraph(line, normal_style))

            # Сводка материалов (агрегировано)
            story.append(Spacer(1, 12))
            story.append(Paragraph("Сводка материалов:", heading_style))
            material_types = CuttingOptimizer._get_material_types(self.db_path)

            totals_lumber = {}  # м
            totals_fasteners = {}  # шт
            for material, items in requirements.items():
                is_lumber = material_types.get(material) == "Пиломатериал"
                total = 0.0
                for val, _ in items:
                    total += float(val)
                if is_lumber:
                    totals_lumber[material] = totals_lumber.get(material, 0.0) + total
                else:
                    totals_fasteners[material] = totals_fasteners.get(material, 0.0) + total

            if totals_lumber:
                story.append(Paragraph("Пиломатериалы:", normal_style))
                for mat, amount in sorted(totals_lumber.items()):
                    story.append(Paragraph(f"• {mat}: {amount:.2f} м", normal_style))

            if totals_fasteners:
                story.append(Paragraph("Метизы:", normal_style))
                for mat, amount in sorted(totals_fasteners.items()):
                    story.append(Paragraph(f"• {mat}: {amount:.0f} шт", normal_style))

            # Инструкции распила (уже отфильтрованы от тросов)
            if instructions_text:
                story.append(Spacer(1, 12))
                story.append(Paragraph("Инструкции:", heading_style))
                story.append(Paragraph(instructions_text.replace('\n', '<br/>'), normal_style))

            doc.build(story)
            QMessageBox.information(self, "PDF", f"PDF заказа сохранён: {pdf_path}")
        except Exception as e:
            print(f"Ошибка при генерации PDF: {str(e)}")

    def _generate_instructions_text(self, total_cost, result, requirements):
        instructions = ""
        material_types = CuttingOptimizer._get_material_types(self.db_path)
        skip_cut_instructions = {"Трос М8", "Трос М10", "Трос М12"}  # не выводим распил для этих материалов

        if result.get('cutting_instructions'):
            for material, material_instructions in result['cutting_instructions'].items():
                # Скрыть раздел распила для тросов
                if material in skip_cut_instructions:
                    continue
                # Метизы также не имеют распила
                if material_types.get(material) == "Метиз":
                    continue

                instructions += f"Материал: {material}\n"
                for i, instr in enumerate(material_instructions, 1):
                    instructions += f"{i}. {instr}\n\n"

        if not instructions.strip():
            instructions = "Инструкции по распилу не требуются."
        return instructions.strip()

    def load_order_history(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("""SELECT o.id, o.order_date, o.total_cost, 
            SUM(oi.quantity) as total_items
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            GROUP BY o.id
            ORDER BY o.order_date DESC""")
            orders = cursor.fetchall()

            self.history_table.setRowCount(len(orders))
            for row_idx, (order_id, date, total_cost, items_count) in enumerate(orders):
                self.history_table.setItem(row_idx, 0, QTableWidgetItem(str(order_id)))
                self.history_table.setItem(row_idx, 1, QTableWidgetItem(date))
                self.history_table.setItem(row_idx, 2, QTableWidgetItem(str(items_count)))
                self.history_table.setItem(row_idx, 3, QTableWidgetItem(f"{total_cost:.2f} руб"))

        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка базы данных", f"Ошибка загрузки истории: {str(e)}")
        finally:
            conn.close()

    def show_order_details(self, row, column):
        order_id = self.history_table.item(row, 0).text()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT product_name, quantity, cost, item_type FROM order_items WHERE order_id = ?",
                       (order_id,))
        items = cursor.fetchall()

        cursor.execute("SELECT order_date, total_cost, instructions FROM orders WHERE id = ?", (order_id,))
        order_date, total_cost, instructions = cursor.fetchone()
        conn.close()

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Детали заказа №{order_id}")
        dialog.setMinimumSize(600, 400)

        layout = QVBoxLayout()

        items_text = f"Заказ от {order_date}:\n\n"
        items_text += f"Общая стоимость: {total_cost:.2f} руб\n\n"
        items_text += "Состав заказа:\n"
        for name, quantity, cost, item_type in items:
            type_text = "Изделие" if item_type == 'product' else "Этап"
            items_text += f"- {name} ({type_text}): {quantity} шт ({cost:.2f} руб)\n"

        items_label = QTextEdit(items_text)
        items_label.setReadOnly(True)
        layout.addWidget(items_label)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec_()

    # ИСПРАВЛЕНИЕ: Новые методы для работы с PDF
    def open_pdf_file(self, order_id):
        """Открывает PDF файл для указанного заказа"""
        try:
            # Получаем имя PDF файла из БД
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT pdf_filename FROM orders WHERE id = ?", (order_id,))
            result = cursor.fetchone()
            conn.close()

            if not result or not result[0]:
                QMessageBox.warning(self, "PDF не найден", "PDF файл для этого заказа не создан")
                return

            pdf_filename = result[0]

            # Определяем путь к PDF файлу
            if getattr(sys, 'frozen', False):
                pdf_dir = os.path.join(os.path.dirname(sys.executable), 'orders')
            else:
                pdf_dir = os.path.join(os.path.dirname(self.db_path), 'orders')

            pdf_path = os.path.join(pdf_dir, pdf_filename)

            if not os.path.exists(pdf_path):
                QMessageBox.warning(self, "Файл не найден",
                                    f"PDF файл не найден:\n{pdf_path}")
                return

            # Открываем PDF файл кроссплатформенно
            system = platform.system()
            if system == "Windows":
                os.startfile(pdf_path)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", pdf_path])
            else:  # Linux
                subprocess.run(["xdg-open", pdf_path])

            print(f"Открыт PDF файл: {pdf_path}")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть PDF:\n{str(e)}")

    def open_selected_pdf(self):
        """Открывает PDF для выбранного заказа в истории"""
        selected_row = self.history_table.currentRow()

        if selected_row == -1:
            QMessageBox.warning(self, "Выберите заказ",
                                "Пожалуйста, выберите заказ из списка истории")
            return

        # Получаем ID заказа из первой колонки
        order_id = int(self.history_table.item(selected_row, 0).text())

        # Вызываем метод открытия PDF
        self.open_pdf_file(order_id)


# ИСПРАВЛЕННЫЙ ГЛАВНЫЙ КЛАСС
class MainWindow(QMainWindow):
    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self.setWindowTitle("Учет деревообрабатывающего цеха - ИСПРАВЛЕНО")
        self.setGeometry(100, 100, 1200, 900)

        self.refresh_btn = QPushButton("Обновить все данные")
        self.refresh_btn.clicked.connect(self.reload_all_tabs)
        self.refresh_btn.setFixedSize(150, 30)
        self.refresh_btn.move(self.width() - 160, 0)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # Существующие вкладки
        self.materials_tab = MaterialsTab(db_path)
        self.materials_tab.main_window_ref = self
        self.tabs.addTab(self.materials_tab, "Материалы")

        self.warehouse_tab = WarehouseTab(db_path, self)
        self.tabs.addTab(self.warehouse_tab, "Склад")

        self.products_tab = ProductsTab(db_path, self)
        self.tabs.addTab(self.products_tab, "Изделия")

        # ИСПРАВЛЕННАЯ ВКЛАДКА ЭТАПОВ
        self.stages_tab = StagesTab(db_path, self)
        self.tabs.addTab(self.stages_tab, "Этапы")

        # ИСПРАВЛЕННАЯ ВКЛАДКА ЗАКАЗОВ
        self.orders_tab = OrdersTab(db_path, self)
        self.tabs.addTab(self.orders_tab, "Заказы")

        self.refresh_btn.setParent(self)
        self.refresh_btn.raise_()

        self.statusBar().showMessage("Готово - все ошибки исправлены!")

    def on_tab_changed(self, index):
        tab_name = self.tabs.tabText(index)

        if tab_name == "Склад":
            self.warehouse_tab.load_materials()
        elif tab_name == "Изделия":
            self.products_tab.load_materials()
        elif tab_name == "Этапы":
            self.stages_tab.load_products()
            self.stages_tab.load_materials()
        elif tab_name == "Заказы":
            # ИСПРАВЛЕНИЕ 3: Загружаем правильный тип по умолчанию
            current_type = self.orders_tab.item_type_combo.currentText()
            if current_type == "Изделие":
                self.orders_tab.load_products()
            else:
                self.orders_tab.load_stages()
            self.orders_tab.load_order_history()

    def update_all_comboboxes(self):
        self.warehouse_tab.load_materials()
        self.products_tab.load_materials()
        self.stages_tab.load_products()
        self.stages_tab.load_materials()

        # ИСПРАВЛЕНИЕ 3: Обновляем правильный список в заказах
        current_type = self.orders_tab.item_type_combo.currentText()
        if current_type == "Изделие":
            self.orders_tab.load_products()
        else:
            self.orders_tab.load_stages()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refresh_btn.move(self.width() - 160, 0)

    def reload_all_tabs(self):
        """Перезагружает данные во всех вкладках"""
        self.products_tab.recalculate_all_products_cost()
        self.stages_tab.recalculate_all_stages_cost()

        self.materials_tab.load_data()
        self.warehouse_tab.load_data()
        self.products_tab.load_products()
        self.stages_tab.load_stages()
        self.orders_tab.load_order_history()

        # ИСПРАВЛЕНИЕ 3: Правильное обновление списков в заказах
        current_type = self.orders_tab.item_type_combo.currentText()
        if current_type == "Изделие":
            self.orders_tab.load_products()
        else:
            self.orders_tab.load_stages()

        self.statusBar().showMessage("Данные обновлены", 3000)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db')
    window = MainWindow(db_path)
    window.show()
    sys.exit(app.exec_())