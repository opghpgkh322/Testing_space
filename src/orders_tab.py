# orders_tab.py - Вкладка "Заказы"
"""
Управление заказами: добавление изделий/этапов, расчет заказа, оптимизация раскроя, сохранение и генерация PDF.
"""

import math
from collections import defaultdict
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QTableWidget, QTableWidgetItem,
    QFormLayout, QComboBox, QSpinBox, QDoubleSpinBox, QPushButton,
    QLabel, QTextEdit, QMessageBox, QHBoxLayout, QDialog
)
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtCore import Qt
from utils import fetch_all, execute
from cutting_optimizer import CuttingOptimizer
from config import Config, DatabaseConfig
from pdf_generator import PDFGenerator


class OrdersTab(QWidget):
    """Вкладка управления заказами"""

    def __init__(self, db_path, main_window=None):
        super().__init__()
        self.db_path = db_path
        self.main_window = main_window
        self.current_order = []  # Список (type, id, qty_or_len)
        self.product_cost_cache = {}
        self.stage_cost_cache = {}
        self.init_ui()
        self.load_order_history()

    def init_ui(self):
        layout = QVBoxLayout()

        order_group = QGroupBox("Создать заказ")
        og_layout = QVBoxLayout()

        # Таблица заказа
        self.order_table = QTableWidget()
        self.order_table.setColumnCount(6)
        self.order_table.setHorizontalHeaderLabels(["Тип","Название","Кол-во","Длина","Себестоимость","Действия"])
        self.order_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        og_layout.addWidget(self.order_table)

        # Форма добавления
        form = QFormLayout()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Изделие","Этап"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        form.addRow("Тип:", self.type_combo)

        self.item_combo = QComboBox()
        form.addRow("Выберите:", self.item_combo)

        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, Config.MAX_QUANTITY)
        form.addRow("Кол-во:", self.qty_spin)

        self.len_spin = QDoubleSpinBox()
        self.len_spin.setRange(Config.MIN_LENGTH, Config.MAX_LENGTH)
        self.len_spin.setDecimals(Config.LENGTH_DECIMALS)
        self.len_spin.setSingleStep(Config.LENGTH_STEP)
        self.len_spin.hide()
        form.addRow("Длина:", self.len_spin)

        add_btn = QPushButton("Добавить в заказ")
        add_btn.clicked.connect(self.add_to_order)
        form.addRow(add_btn)
        og_layout.addLayout(form)

        btns = QHBoxLayout()
        calc_btn = QPushButton("Рассчитать заказ")
        calc_btn.clicked.connect(self.calculate_order)
        btns.addWidget(calc_btn)
        confirm_btn = QPushButton("Подтвердить заказ")
        confirm_btn.clicked.connect(self.confirm_order)
        btns.addWidget(confirm_btn)
        clear_btn = QPushButton("Очистить заказ")
        clear_btn.clicked.connect(self.clear_order)
        btns.addWidget(clear_btn)
        og_layout.addLayout(btns)

        self.instr_text = QTextEdit()
        self.instr_text.setReadOnly(True)
        og_layout.addWidget(QLabel("Окно сообщений:"))
        og_layout.addWidget(self.instr_text)

        self.total_label = QLabel("Общая себестоимость: 0.00 руб")
        og_layout.addWidget(self.total_label)
        order_group.setLayout(og_layout)
        layout.addWidget(order_group)

        # История заказов
        hist_group = QGroupBox("История заказов")
        hg_layout = QVBoxLayout()
        self.hist_table = QTableWidget()
        self.hist_table.setColumnCount(4)
        self.hist_table.setHorizontalHeaderLabels(["ID","Дата","Позиций","Сумма"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.hist_table.cellDoubleClicked.connect(self.show_order_details)
        hg_layout.addWidget(self.hist_table)

        hist_btns = QHBoxLayout()
        open_btn = QPushButton("Открыть PDF")
        open_btn.clicked.connect(self.open_selected_pdf)
        hist_btns.addWidget(open_btn)
        refresh_btn = QPushButton("Обновить историю")
        refresh_btn.clicked.connect(self.load_order_history)
        hist_btns.addWidget(refresh_btn)
        hist_btns.addStretch()
        hg_layout.addLayout(hist_btns)
        hist_group.setLayout(hg_layout)
        layout.addWidget(hist_group)

        self.setLayout(layout)
        self.on_type_changed(self.type_combo.currentText())

    # orders_tab.py - Недостающие методы
    """
    Недостающие методы для OrdersTab класса. Вставить вместо комментария.
    """

    def on_type_changed(self, item_type):
        """Переключение между Изделием и Этапом"""
        self.item_combo.clear()
        if item_type == "Изделие":
            self.len_spin.hide()
            self.qty_spin.show()
            self.load_products()
        else:
            self.len_spin.show()
            self.qty_spin.hide()
            self.load_stages()

    def load_products(self):
        """Загружает изделия в комбобокс"""
        rows = fetch_all("SELECT id, name FROM products ORDER BY name")
        for row in rows:
            self.item_combo.addItem(row['name'], row['id'])

    def load_stages(self):
        """Загружает этапы в комбобокс"""
        rows = fetch_all("SELECT id, name FROM stages ORDER BY name")
        for row in rows:
            self.item_combo.addItem(row['name'], row['id'])

    def add_to_order(self):
        """Добавляет позицию в заказ"""
        item_id = self.item_combo.currentData()
        item_name = self.item_combo.currentText()
        item_type = self.type_combo.currentText()

        if not item_id:
            QMessageBox.warning(self, "Ошибка", f"Выберите {item_type.lower()}")
            return

        row = self.order_table.rowCount()
        self.order_table.setRowCount(row + 1)

        if item_type == "Изделие":
            qty = self.qty_spin.value()
            cost = self._get_product_cost(item_id) * qty
            self.order_table.setItem(row, 0, QTableWidgetItem(item_type))
            self.order_table.setItem(row, 1, QTableWidgetItem(item_name))
            self.order_table.setItem(row, 2, QTableWidgetItem(str(qty)))
            self.order_table.setItem(row, 3, QTableWidgetItem(""))
            self.order_table.setItem(row, 4, QTableWidgetItem(f"{cost:.2f} руб"))
            self.current_order.append(("product", item_id, qty))
        else:  # Этап
            length = self.len_spin.value()
            cost = self._compute_stage_cost(item_id, length)
            self.order_table.setItem(row, 0, QTableWidgetItem(item_type))
            self.order_table.setItem(row, 1, QTableWidgetItem(item_name))
            self.order_table.setItem(row, 2, QTableWidgetItem("1"))
            self.order_table.setItem(row, 3, QTableWidgetItem(f"{length:.2f}"))
            self.order_table.setItem(row, 4, QTableWidgetItem(f"{cost:.2f} руб"))
            self.current_order.append(("stage", item_id, length))

        # Кнопка удаления
        del_btn = QPushButton("Удалить")
        del_btn.clicked.connect(lambda: self._remove_row(row))
        self.order_table.setCellWidget(row, 5, del_btn)

        self.update_total_cost()

    def _remove_row(self, row):
        """Удаляет строку из заказа"""
        if 0 <= row < len(self.current_order):
            self.current_order.pop(row)
        self.order_table.removeRow(row)
        self.update_total_cost()

    def update_total_cost(self):
        """Обновляет общую стоимость"""
        total = 0.0
        for row in range(self.order_table.rowCount()):
            cost_item = self.order_table.item(row, 4)
            if cost_item:
                cost_text = cost_item.text().replace(' руб', '')
                total += float(cost_text or 0)
        self.total_label.setText(f"Общая себестоимость: {total:.2f} руб")

    def clear_order(self):
        """Очищает текущий заказ"""
        self.order_table.setRowCount(0)
        self.current_order = []
        self.instr_text.clear()
        self.total_label.setText("Общая себестоимость: 0.00 руб")

    def calculate_order(self):
        """Рассчитывает заказ с оптимизацией раскроя"""
        if not self.current_order:
            QMessageBox.warning(self, "Ошибка", "Заказ пуст")
            return

        total_cost, requirements = self._expand_order_to_requirements()
        stock_items = self._get_current_stock()

        optimizer = CuttingOptimizer()
        result = optimizer.optimize_cutting(requirements, stock_items)

        # Формирование сообщения
        message = f"💰 Себестоимость: {total_cost:.2f} руб\n"
        message += f"💰 Цена реализации: {total_cost * Config.SALE_PRICE_MULTIPLIER:.2f} руб\n\n"
        message += "📦 Требуемые материалы:\n"

        for material, items in requirements.items():
            total_amount = sum(item[0] for item in items)
            message += f"▫️ {material}: {total_amount:.2f}\n"

        if result['can_produce']:
            message += "\n✅ Материалов достаточно для производства"
        else:
            message += "\n❌ Материалов недостаточно:\n"
            for error in result['missing']:
                message += f" - {error}\n"

        self.instr_text.setText(message)

    def confirm_order(self):
        """Подтверждает заказ и сохраняет в БД"""
        if not self.current_order:
            QMessageBox.warning(self, "Ошибка", "Заказ пуст")
            return

        total_cost, requirements = self._expand_order_to_requirements()
        stock_items = self._get_current_stock()

        optimizer = CuttingOptimizer()
        result = optimizer.optimize_cutting(requirements, stock_items)

        if not result['can_produce']:
            error_msg = "Недостаточно материалов:\n" + "\n".join(result['missing'])
            QMessageBox.critical(self, "Ошибка", error_msg)
            return

        # Сохранение заказа
        order_id = self._save_order_to_db(total_cost)

        # Генерация PDF
        from pdf_generator import PDFGenerator
        order_details = self._prepare_order_details()
        instructions = result.get('cutting_instructions', {})
        pdf_path = PDFGenerator.generate(order_id, total_cost, order_details, requirements, str(instructions))

        # Обновление склада
        self._update_warehouse(result['updated_warehouse'])

        self.clear_order()
        self.load_order_history()
        QMessageBox.information(self, "Успех", f"Заказ подтвержден!\nPDF: {pdf_path}")

    def _expand_order_to_requirements(self):
        """Разворачивает заказ в требования по материалам"""
        requirements = defaultdict(list)
        total_cost = 0.0

        for item_type, item_id, qty_or_len in self.current_order:
            if item_type == "product":
                cost = self._get_product_cost(item_id) * qty_or_len
                total_cost += cost

                # Получаем состав изделия
                rows = fetch_all(
                    "SELECT m.name, m.type, pc.quantity, pc.length "
                    "FROM product_composition pc "
                    "JOIN materials m ON pc.material_id = m.id "
                    "WHERE pc.product_id = ?", [item_id]
                )

                for row in rows:
                    mat_name = row['name']
                    if row['type'] == Config.MATERIAL_TYPES[0] and row['length']:  # Пиломатериал
                        for _ in range(int(row['quantity'] * qty_or_len)):
                            requirements[mat_name].append((row['length'], f"Изделие"))
                    else:  # Метиз
                        requirements[mat_name].append((row['quantity'] * qty_or_len, f"Изделие"))

            else:  # stage
                cost = self._compute_stage_cost(item_id, qty_or_len)
                total_cost += cost

                # Получаем состав этапа
                eff_meters = math.ceil(qty_or_len)

                # Материалы этапа
                rows = fetch_all(
                    "SELECT sm.part, m.name, m.type, sm.quantity, sm.length "
                    "FROM stage_materials sm "
                    "JOIN materials m ON sm.material_id = m.id "
                    "WHERE sm.stage_id = ?", [item_id]
                )

                for row in rows:
                    mult = eff_meters if row['part'] == 'meter' else 1
                    mat_name = row['name']
                    if row['type'] == Config.MATERIAL_TYPES[0] and row['length']:
                        for _ in range(int(row['quantity'] * mult)):
                            requirements[mat_name].append((row['length'], f"Этап {row['part']}"))
                    else:
                        requirements[mat_name].append((row['quantity'] * mult, f"Этап {row['part']}"))

        return total_cost, requirements

    def _get_product_cost(self, product_id):
        """Получает себестоимость изделия"""
        if product_id in self.product_cost_cache:
            return self.product_cost_cache[product_id]

        rows = fetch_all("SELECT cost FROM products WHERE id = ?", [product_id])
        cost = rows[0]['cost'] if rows else 0.0
        self.product_cost_cache[product_id] = cost
        return cost

    def _compute_stage_cost(self, stage_id, length_m):
        """Вычисляет стоимость этапа для заданной длины"""
        eff_meters = math.ceil(max(0.0, float(length_m)))

        start = meter = end = 0.0

        # Изделия в этапе
        rows = fetch_all(
            "SELECT sp.part, p.cost, sp.quantity "
            "FROM stage_products sp "
            "JOIN products p ON sp.product_id = p.id "
            "WHERE sp.stage_id = ?", [stage_id]
        )

        for row in rows:
            mult = eff_meters if row['part'] == 'meter' else 1
            cost_add = row['cost'] * row['quantity'] * mult
            if row['part'] == 'start':
                start += cost_add
            elif row['part'] == 'meter':
                meter += cost_add
            else:
                end += cost_add

        # Материалы в этапе
        rows = fetch_all(
            "SELECT sm.part, m.type, m.price, sm.quantity, sm.length "
            "FROM stage_materials sm "
            "JOIN materials m ON sm.material_id = m.id "
            "WHERE sm.stage_id = ?", [stage_id]
        )

        for row in rows:
            mult = eff_meters if row['part'] == 'meter' else 1
            if row['type'] == Config.MATERIAL_TYPES[0] and row['length']:
                cost_add = row['price'] * row['quantity'] * row['length'] * mult
            else:
                cost_add = row['price'] * row['quantity'] * mult

            if row['part'] == 'start':
                start += cost_add
            elif row['part'] == 'meter':
                meter += cost_add
            else:
                end += cost_add

        return start + meter + end

    def _get_current_stock(self):
        """Получает текущие остатки склада"""
        return fetch_all(
            "SELECT m.name, w.length, w.quantity "
            "FROM warehouse w "
            "JOIN materials m ON w.material_id = m.id"
        )

    def _save_order_to_db(self, total_cost):
        """Сохраняет заказ в базу данных"""
        execute(
            "INSERT INTO orders (order_date, total_cost) VALUES (datetime('now'), ?)",
            [total_cost]
        )

        rows = fetch_all("SELECT last_insert_rowid() as id")
        return rows[0]['id']

    def _prepare_order_details(self):
        """Подготавливает детали заказа для PDF"""
        details = []
        for item_type, item_id, qty_or_len in self.current_order:
            if item_type == "product":
                rows = fetch_all("SELECT name FROM products WHERE id = ?", [item_id])
                name = rows[0]['name'] if rows else f"Изделие #{item_id}"
                cost = self._get_product_cost(item_id) * qty_or_len
                details.append(("product", item_id, name, qty_or_len, cost, None))
            else:
                rows = fetch_all("SELECT name FROM stages WHERE id = ?", [item_id])
                name = rows[0]['name'] if rows else f"Этап #{item_id}"
                cost = self._compute_stage_cost(item_id, qty_or_len)
                details.append(("stage", item_id, name, 1, cost, qty_or_len))
        return details

    def _update_warehouse(self, updated_data):
        """Обновляет остатки склада"""
        execute("DELETE FROM warehouse")
        for material, length, quantity in updated_data:
            if quantity > 0:
                rows = fetch_all("SELECT id FROM materials WHERE name = ?", [material])
                if rows:
                    execute(
                        "INSERT INTO warehouse (material_id, length, quantity) VALUES (?, ?, ?)",
                        [rows[0]['id'], length, quantity]
                    )

    def load_order_history(self):
        """Загружает историю заказов"""
        rows = fetch_all(
            "SELECT o.id, o.order_date, o.total_cost, "
            "COUNT(oi.id) as items_count "
            "FROM orders o "
            "LEFT JOIN order_items oi ON o.id = oi.order_id "
            "GROUP BY o.id "
            "ORDER BY o.order_date DESC"
        )

        self.hist_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.hist_table.setItem(i, 0, QTableWidgetItem(str(row['id'])))
            self.hist_table.setItem(i, 1, QTableWidgetItem(row['order_date']))
            self.hist_table.setItem(i, 2, QTableWidgetItem(str(row['items_count'])))
            self.hist_table.setItem(i, 3, QTableWidgetItem(f"{row['total_cost']:.2f} руб"))

    def show_order_details(self, row, _col):
        """Показывает детали заказа в диалоге"""
        order_id = int(self.hist_table.item(row, 0).text())

        rows = fetch_all(
            "SELECT order_date, total_cost FROM orders WHERE id = ?", [order_id]
        )

        if not rows:
            return

        order_date = rows[0]['order_date']
        total_cost = rows[0]['total_cost']

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Заказ №{order_id}")
        dialog.setMinimumSize(400, 300)

        layout = QVBoxLayout()
        text = f"Заказ от {order_date}\n"
        text += f"Общая стоимость: {total_cost:.2f} руб\n\n"

        items_rows = fetch_all(
            "SELECT product_name, quantity, cost, item_type FROM order_items WHERE order_id = ?",
            [order_id]
        )

        text += "Состав заказа:\n"
        for item in items_rows:
            type_text = "Изделие" if item['item_type'] == 'product' else "Этап"
            text += f"- {item['product_name']} ({type_text}): {item['quantity']} ({item['cost']:.2f} руб)\n"

        text_edit = QTextEdit(text)
        text_edit.setReadOnly(True)
        layout.addWidget(text_edit)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec_()

    def open_selected_pdf(self):
        """Открывает PDF для выбранного заказа"""
        row = self.hist_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите заказ")
            return

        order_id = int(self.hist_table.item(row, 0).text())

        # Поиск PDF файла
        orders_dir = DatabaseConfig.get_orders_dir()
        import os
        for filename in os.listdir(orders_dir):
            if filename.endswith('.pdf') and f'order_{order_id}' in filename:
                filepath = os.path.join(orders_dir, filename)
                # Открытие файла кросс-платформенно
                import platform
                import subprocess
                system = platform.system()
                if system == "Windows":
                    os.startfile(filepath)
                elif system == "Darwin":
                    subprocess.run(["open", filepath])
                else:
                    subprocess.run(["xdg-open", filepath])
                return

        QMessageBox.warning(self, "Ошибка", "PDF файл не найден")
