import math
import os
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from .base_tab import BaseTab
from ..services.order_service import OrderService
from ..services.product_service import ProductService
from ..services.stage_service import StageService
from ..services.warehouse_service import WarehouseService
from ..utils.pdf_generator import PDFGenerator
from cutting_optimizer import CuttingOptimizer


class OrdersTab(BaseTab):
    """Вкладка для работы с заказами"""

    def __init__(self, db_path, main_window=None):
        super().__init__(db_path, main_window)
        self.order_service = OrderService(db_path)
        self.product_service = ProductService(db_path)
        self.stage_service = StageService(db_path)
        self.warehouse_service = WarehouseService(db_path)
        self.pdf_generator = PDFGenerator(db_path)

        # Текущий заказ
        self.current_order_items = []  # [(item_type, item_id, quantity_or_length)]
        self.selected_order_item_index = None

        self.init_ui()
        self.load_orders()

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        main_splitter = QSplitter(Qt.Vertical)

        # Верхняя панель - создание заказа
        order_creation_group = QGroupBox("Создание заказа")
        creation_layout = QVBoxLayout()

        # Текущий заказ
        current_order_layout = QHBoxLayout()

        # Левая часть - добавление позиций
        add_items_group = QGroupBox("Добавить в заказ")
        add_items_layout = QFormLayout()

        # Переключатель типа позиции
        self.item_type_combo = QComboBox()
        self.item_type_combo.addItems(["Изделие", "Этап"])
        self.item_type_combo.currentTextChanged.connect(self.on_item_type_changed)
        add_items_layout.addRow(QLabel("Тип позиции:"), self.item_type_combo)

        # Комбобокс для изделий/этапов
        self.item_combo = QComboBox()
        add_items_layout.addRow(QLabel("Позиция:"), self.item_combo)

        # Поля ввода
        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("1")
        self.quantity_label = QLabel("Количество:")
        add_items_layout.addRow(self.quantity_label, self.quantity_input)

        self.length_input = QLineEdit()
        self.length_input.setPlaceholderText("5.0")
        self.length_label = QLabel("Длина (м):")
        add_items_layout.addRow(self.length_label, self.length_input)
        self.length_label.hide()
        self.length_input.hide()

        # Кнопки
        add_buttons_layout = QHBoxLayout()

        self.add_to_order_btn = QPushButton("Добавить в заказ")
        self.add_to_order_btn.clicked.connect(self.add_to_order)
        add_buttons_layout.addWidget(self.add_to_order_btn)

        self.remove_from_order_btn = QPushButton("Удалить из заказа")
        self.remove_from_order_btn.clicked.connect(self.remove_from_order)
        self.remove_from_order_btn.setEnabled(False)
        add_buttons_layout.addWidget(self.remove_from_order_btn)

        add_items_layout.addRow(add_buttons_layout)
        add_items_group.setLayout(add_items_layout)
        current_order_layout.addWidget(add_items_group)

        # Правая часть - содержимое заказа
        order_content_group = QGroupBox("Содержимое заказа")
        content_layout = QVBoxLayout()

        self.order_table = QTableWidget()
        self.order_table.setColumnCount(5)
        self.order_table.setHorizontalHeaderLabels([
            "Тип", "Название", "Количество/Длина", "Стоимость", "Ед.изм."
        ])
        self.order_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.order_table.cellClicked.connect(self.on_order_item_selected)
        content_layout.addWidget(self.order_table)

        self.total_cost_label = QLabel("Общая стоимость: 0.00 руб")
        self.total_cost_label.setStyleSheet("font-weight: bold; font-size: 14pt; color: #1976D2;")
        content_layout.addWidget(self.total_cost_label)

        order_content_group.setLayout(content_layout)
        current_order_layout.addWidget(order_content_group)

        creation_layout.addLayout(current_order_layout)

        # Кнопки заказа
        order_buttons_layout = QHBoxLayout()

        self.clear_order_btn = QPushButton("Очистить заказ")
        self.clear_order_btn.clicked.connect(self.clear_current_order)
        order_buttons_layout.addWidget(self.clear_order_btn)

        self.check_availability_btn = QPushButton("Проверить наличие материалов")
        self.check_availability_btn.clicked.connect(self.check_materials_availability)
        order_buttons_layout.addWidget(self.check_availability_btn)

        self.optimize_cutting_btn = QPushButton("Оптимизировать раскрой")
        self.optimize_cutting_btn.clicked.connect(self.optimize_cutting)
        order_buttons_layout.addWidget(self.optimize_cutting_btn)

        self.create_order_btn = QPushButton("Создать заказ")
        self.create_order_btn.clicked.connect(self.create_order)
        order_buttons_layout.addWidget(self.create_order_btn)

        creation_layout.addLayout(order_buttons_layout)

        # Инструкции к заказу
        instructions_group = QGroupBox("Инструкции к заказу")
        instructions_layout = QVBoxLayout()

        self.instructions_input = QTextEdit()
        self.instructions_input.setPlaceholderText("Дополнительные инструкции к заказу...")
        self.instructions_input.setMaximumHeight(80)
        instructions_layout.addWidget(self.instructions_input)

        instructions_group.setLayout(instructions_layout)
        creation_layout.addWidget(instructions_group)

        order_creation_group.setLayout(creation_layout)
        main_splitter.addWidget(order_creation_group)

        # Нижняя панель - список заказов
        orders_list_group = QGroupBox("Существующие заказы")
        orders_layout = QVBoxLayout()

        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(5)
        self.orders_table.setHorizontalHeaderLabels([
            "ID", "Дата", "Стоимость", "Позиций", "PDF"
        ])
        self.orders_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.orders_table.cellClicked.connect(self.on_order_selected)
        orders_layout.addWidget(self.orders_table)

        # Кнопки управления заказами
        orders_buttons_layout = QHBoxLayout()

        self.view_order_btn = QPushButton("Просмотр заказа")
        self.view_order_btn.clicked.connect(self.view_order)
        self.view_order_btn.setEnabled(False)
        orders_buttons_layout.addWidget(self.view_order_btn)

        self.generate_pdf_btn = QPushButton("Создать PDF")
        self.generate_pdf_btn.clicked.connect(self.generate_order_pdf)
        self.generate_pdf_btn.setEnabled(False)
        orders_buttons_layout.addWidget(self.generate_pdf_btn)

        self.open_pdf_btn = QPushButton("Открыть PDF")
        self.open_pdf_btn.clicked.connect(self.open_order_pdf)
        self.open_pdf_btn.setEnabled(False)
        orders_buttons_layout.addWidget(self.open_pdf_btn)

        self.delete_order_btn = QPushButton("Удалить заказ")
        self.delete_order_btn.clicked.connect(self.delete_order)
        self.delete_order_btn.setEnabled(False)
        orders_buttons_layout.addWidget(self.delete_order_btn)

        self.refresh_orders_btn = QPushButton("Обновить список")
        self.refresh_orders_btn.clicked.connect(self.load_orders)
        orders_buttons_layout.addWidget(self.refresh_orders_btn)

        orders_layout.addLayout(orders_buttons_layout)
        orders_list_group.setLayout(orders_layout)
        main_splitter.addWidget(orders_list_group)

        main_splitter.setSizes([400, 300])

        main_layout = QVBoxLayout()
        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)

        # Загружаем данные
        self.load_products_and_stages()
        self.on_item_type_changed("Изделие")

    def load_products_and_stages(self):
        """Загрузка списков изделий и этапов"""
        try:
            self.products = self.product_service.get_all_products()
            self.stages = self.stage_service.get_all_stages()
        except Exception as e:
            self.handle_exception(e, "загрузке данных для заказов")

    def on_item_type_changed(self, item_type):
        """Обработка смены типа позиции"""
        self.item_combo.clear()

        if item_type == "Изделие":
            for prod_id, prod_name, cost in self.products:
                self.item_combo.addItem(f"{prod_name} ({self.format_currency(cost)})", prod_id)

            self.quantity_label.setText("Количество:")
            self.quantity_label.show()
            self.quantity_input.show()
            self.length_label.hide()
            self.length_input.hide()
        else:  # Этап
            for stage_id, stage_name, cost, description in self.stages:
                self.item_combo.addItem(f"{stage_name} ({self.format_currency(cost)} за м)", stage_id)

            self.quantity_label.hide()
            self.quantity_input.hide()
            self.length_label.show()
            self.length_input.show()

    def on_order_item_selected(self, row, col):
        """Обработка выбора позиции в заказе"""
        if 0 <= row < len(self.current_order_items):
            self.selected_order_item_index = row
            self.remove_from_order_btn.setEnabled(True)

    def on_order_selected(self, row, col):
        """Обработка выбора заказа из списка"""
        order_id = self.get_selected_item_id(self.orders_table, row)
        if order_id is not None:
            self.selected_item_id = order_id
            self.view_order_btn.setEnabled(True)
            self.generate_pdf_btn.setEnabled(True)
            self.delete_order_btn.setEnabled(True)

            # Проверяем наличие PDF
            pdf_filename = self.orders_table.item(row, 4).text()
            self.open_pdf_btn.setEnabled(bool(pdf_filename and pdf_filename != "Нет"))

    def add_to_order(self):
        """Добавление позиции в заказ"""
        item_type_text = self.item_type_combo.currentText()
        item_id = self.item_combo.currentData()

        if not item_id:
            self.show_warning("Ошибка", "Выберите позицию")
            return

        if item_type_text == "Изделие":
            quantity = self.validate_int_input(self.quantity_input.text(), "Количество", min_value=1)
            if quantity is None:
                return

            # Находим изделие в списке
            product_name = None
            product_cost = 0
            for prod_id, prod_name, cost in self.products:
                if prod_id == item_id:
                    product_name = prod_name
                    product_cost = cost
                    break

            if not product_name:
                self.show_error("Ошибка", "Изделие не найдено")
                return

            self.current_order_items.append(('product', item_id, quantity))

        else:  # Этап
            length = self.validate_float_input(self.length_input.text(), "Длина", min_value=0.1)
            if length is None:
                return

            # Находим этап в списке
            stage_name = None
            for stage_id, s_name, cost, description in self.stages:
                if stage_id == item_id:
                    stage_name = s_name
                    break

            if not stage_name:
                self.show_error("Ошибка", "Этап не найден")
                return

            self.current_order_items.append(('stage', item_id, length))

        self.update_order_display()
        self.quantity_input.clear()
        self.length_input.clear()

    def remove_from_order(self):
        """Удаление позиции из заказа"""
        if self.selected_order_item_index is not None:
            del self.current_order_items[self.selected_order_item_index]
            self.selected_order_item_index = None
            self.remove_from_order_btn.setEnabled(False)
            self.update_order_display()

    def update_order_display(self):
        """Обновление отображения заказа"""
        try:
            self.order_table.setRowCount(len(self.current_order_items))
            total_cost = 0

            for row_idx, (item_type, item_id, quantity_or_length) in enumerate(self.current_order_items):
                if item_type == 'product':
                    # Находим изделие
                    product_name = None
                    product_cost = 0
                    for prod_id, prod_name, cost in self.products:
                        if prod_id == item_id:
                            product_name = prod_name
                            product_cost = cost
                            break

                    item_cost = product_cost * quantity_or_length
                    total_cost += item_cost

                    self.populate_table_row(self.order_table, row_idx, [
                        "Изделие",
                        product_name,
                        f"{quantity_or_length}",
                        self.format_currency(item_cost),
                        "шт"
                    ], readonly_columns=[0, 1, 2, 3, 4])

                else:  # stage
                    # Находим этап и рассчитываем его стоимость для данной длины
                    stage_name = None
                    for stage_id, s_name, cost, description in self.stages:
                        if stage_id == item_id:
                            stage_name = s_name
                            break

                    # Рассчитываем стоимость этапа для конкретной длины
                    stage_cost = self.stage_service.compute_stage_cost_for_length(item_id, quantity_or_length)
                    total_cost += stage_cost

                    self.populate_table_row(self.order_table, row_idx, [
                        "Этап",
                        stage_name,
                        f"{quantity_or_length:.1f}",
                        self.format_currency(stage_cost),
                        "м"
                    ], readonly_columns=[0, 1, 2, 3, 4])

            self.total_cost_label.setText(f"Общая стоимость: {self.format_currency(total_cost)}")
            sale_price = total_cost * 2
            self.total_cost_label.setText(
                f"Себестоимость: {self.format_currency(total_cost)} | "
                f"Цена реализации: {self.format_currency(sale_price)}"
            )

        except Exception as e:
            self.handle_exception(e, "обновлении отображения заказа")

    def clear_current_order(self):
        """Очистка текущего заказа"""
        if self.current_order_items and not self.confirm_action("Подтверждение",
                                                                "Очистить текущий заказ?"):
            return

        self.current_order_items.clear()
        self.selected_order_item_index = None
        self.remove_from_order_btn.setEnabled(False)
        self.update_order_display()
        self.instructions_input.clear()

    def check_materials_availability(self):
        """Проверка наличия материалов на складе"""
        if not self.current_order_items:
            self.show_warning("Предупреждение", "Заказ пуст")
            return

        try:
            requirements = self.order_service.calculate_order_requirements(self.current_order_items)
            missing = self.warehouse_service.check_availability(requirements)

            if missing:
                message = "Недостаточно материалов:\n\n" + "\n".join(missing)
                message += "\n\nСоздать заказ всё равно?"
                if not self.confirm_action("Недостаток материалов", message):
                    return False
            else:
                self.show_info("Проверка материалов", "Все необходимые материалы есть на складе!")
                return True

        except Exception as e:
            self.handle_exception(e, "проверке наличия материалов")
            return False

    def optimize_cutting(self):
        """Оптимизация раскроя материалов"""
        if not self.current_order_items:
            self.show_warning("Предупреждение", "Заказ пуст")
            return

        try:
            requirements = self.order_service.calculate_order_requirements(self.current_order_items)

            # Создаем диалог с результатами оптимизации
            dialog = QDialog(self)
            dialog.setWindowTitle("Результаты оптимизации раскроя")
            dialog.setMinimumSize(600, 400)

            layout = QVBoxLayout()

            # Результаты по каждому материалу
            for material_name, requirements_list in requirements.items():
                if any("Пиломатериал" in str(req) for req in requirements_list):
                    # Только для пиломатериалов оптимизируем раскрой
                    lengths_needed = [req[0] for req in requirements_list if isinstance(req[0], (int, float))]

                    if lengths_needed:
                        group = QGroupBox(f"Оптимизация раскроя: {material_name}")
                        group_layout = QVBoxLayout()

                        # Получаем складские остатки этого материала
                        warehouse_items = self.warehouse_service.get_all_warehouse_items()
                        available_lengths = []
                        for w_id, w_name, w_length, w_quantity, w_type, w_unit in warehouse_items:
                            if w_name == material_name and w_length > 0:
                                available_lengths.extend([w_length] * w_quantity)

                        if available_lengths:
                            optimizer = CuttingOptimizer()
                            result = optimizer.optimize(available_lengths, lengths_needed)

                            result_text = f"Требуется отрезков: {len(lengths_needed)}\n"
                            result_text += f"Используется досок: {len(result['used_boards'])}\n"
                            result_text += f"Остается досок: {len(result['remaining_boards'])}\n"
                            result_text += f"Отходы: {result['total_waste']:.2f} м\n\n"

                            result_text += "Инструкции по раскрою:\n"
                            for i, (board_length, cuts) in enumerate(result['cutting_plan']):
                                if cuts:
                                    result_text += f"Доска {i + 1} ({board_length:.2f}м): "
                                    result_text += " + ".join(f"{cut:.2f}м" for cut in cuts)
                                    waste = board_length - sum(cuts)
                                    if waste > 0:
                                        result_text += f" + отход {waste:.2f}м"
                                    result_text += "\n"

                            result_label = QLabel(result_text)
                            result_label.setFont(result_label.font())
                            result_label.setStyleSheet("font-family: monospace;")
                            group_layout.addWidget(result_label)
                        else:
                            group_layout.addWidget(QLabel("Нет подходящих досок на складе"))

                        group.setLayout(group_layout)
                        layout.addWidget(group)

            if layout.count() == 0:
                layout.addWidget(QLabel("Нет пиломатериалов для оптимизации"))

            # Кнопка закрытия
            close_btn = QPushButton("Закрыть")
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)

            dialog.setLayout(layout)
            dialog.exec_()

        except Exception as e:
            self.handle_exception(e, "оптимизации раскроя")

    def create_order(self):
        """Создание заказа"""
        if not self.current_order_items:
            self.show_warning("Ошибка", "Заказ пуст")
            return

        try:
            # Рассчитываем общую стоимость
            total_cost = self.order_service.calculate_order_total_cost(self.current_order_items)
            instructions = self.instructions_input.toPlainText().strip()

            # Создаем заказ
            order_id = self.order_service.create_order(total_cost, instructions)

            # Добавляем позиции в заказ
            for item_type, item_id, quantity_or_length in self.current_order_items:
                if item_type == 'product':
                    # Находим название и стоимость изделия
                    product_name = None
                    product_cost = 0
                    for prod_id, prod_name, cost in self.products:
                        if prod_id == item_id:
                            product_name = prod_name
                            product_cost = cost
                            break

                    item_total_cost = product_cost * quantity_or_length
                    self.order_service.add_product_to_order(
                        order_id, item_id, quantity_or_length, product_name, item_total_cost)

                else:  # stage
                    # Находим название этапа и рассчитываем стоимость
                    stage_name = None
                    for stage_id, s_name, cost, description in self.stages:
                        if stage_id == item_id:
                            stage_name = s_name
                            break

                    stage_cost = self.stage_service.compute_stage_cost_for_length(item_id, quantity_or_length)
                    self.order_service.add_stage_to_order(
                        order_id, item_id, quantity_or_length, stage_name, stage_cost)

            # Обновляем склад
            self.update_warehouse_after_order()

            # Очищаем текущий заказ
            self.clear_current_order()

            # Обновляем список заказов
            self.load_orders()

            self.show_info("Успех", f"Заказ №{order_id} создан на сумму {self.format_currency(total_cost)}")
            self.set_status_message(f"Создан заказ №{order_id}", 3000)

        except Exception as e:
            self.handle_exception(e, "создании заказа")

    def update_warehouse_after_order(self):
        """Обновление склада после создания заказа"""
        try:
            # Получаем требования к материалам
            requirements = self.order_service.calculate_order_requirements(self.current_order_items)

            # Получаем текущие остатки склада
            warehouse_items = self.warehouse_service.get_all_warehouse_items()

            # Создаем словарь остатков
            stock = {}
            for w_id, w_name, w_length, w_quantity, w_type, w_unit in warehouse_items:
                if w_name not in stock:
                    stock[w_name] = []
                stock[w_name].append([w_length, w_quantity])

            # Списываем материалы согласно требованиям
            updated_stock = []
            for material_name, req_list in requirements.items():
                if material_name in stock:
                    remaining = stock[material_name][:]

                    for req_value, description in req_list:
                        # Для пиломатериалов ищем подходящую доску
                        found = False
                        for i, (length, qty) in enumerate(remaining):
                            if length >= req_value and qty > 0:
                                remaining[i][1] -= 1
                                if remaining[i][1] <= 0:
                                    remaining[i] = [0, 0]
                                # Если остался кусок, добавляем его
                                if length - req_value > 0.3:  # Минимальный остаток
                                    remaining.append([length - req_value, 1])
                                found = True
                                break

                        if not found:
                            # Для метизов просто уменьшаем количество
                            for i, (length, qty) in enumerate(remaining):
                                if length == 0 and qty >= req_value:
                                    remaining[i][1] -= req_value
                                    break

                    # Добавляем остатки в обновленный склад
                    for length, qty in remaining:
                        if qty > 0:
                            updated_stock.append((material_name, length, qty))

                else:
                    # Материала нет на складе - добавляем как есть (остатки других материалов)
                    continue

            # Добавляем материалы, которые не были в требованиях
            for material_name, stock_list in stock.items():
                if material_name not in requirements:
                    for length, qty in stock_list:
                        if qty > 0:
                            updated_stock.append((material_name, length, qty))

            # Обновляем склад
            self.warehouse_service.update_warehouse_bulk(updated_stock)

            # Обновляем вкладку склада если она есть
            if self.main_window and hasattr(self.main_window, 'warehouse_tab'):
                self.main_window.warehouse_tab.load_data()

        except Exception as e:
            print(f"Ошибка обновления склада: {str(e)}")

    def load_orders(self):
        """Загрузка списка заказов"""
        try:
            orders = self.order_service.get_all_orders()
            self.orders_table.setRowCount(len(orders))

            for row_idx, (order_id, order_date, total_cost, pdf_filename, items_count) in enumerate(orders):
                # Форматируем дату
                try:
                    date_obj = datetime.fromisoformat(order_date.replace('Z', '+00:00'))
                    formatted_date = date_obj.strftime('%d.%m.%Y %H:%M')
                except:
                    formatted_date = order_date

                pdf_status = pdf_filename if pdf_filename else "Нет"

                self.populate_table_row(self.orders_table, row_idx, [
                    order_id,
                    formatted_date,
                    self.format_currency(total_cost),
                    items_count,
                    pdf_status
                ], readonly_columns=[0, 1, 2, 3, 4])

        except Exception as e:
            self.handle_exception(e, "загрузке заказов")

    def view_order(self):
        """Просмотр деталей заказа"""
        if not self.selected_item_id:
            return

        try:
            order = self.order_service.get_order_by_id(self.selected_item_id)
            order_items = self.order_service.get_order_items(self.selected_item_id)

            if not order:
                self.show_error("Ошибка", "Заказ не найден")
                return

            # Создаем диалог просмотра
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Заказ №{self.selected_item_id}")
            dialog.setMinimumSize(500, 400)

            layout = QVBoxLayout()

            # Информация о заказе
            info_text = f"Дата: {order[1]}\n"
            info_text += f"Стоимость: {self.format_currency(order[2])}\n"
            if order[3]:  # instructions
                info_text += f"Инструкции: {order[3]}\n"

            info_label = QLabel(info_text)
            layout.addWidget(info_label)

            # Таблица позиций
            items_table = QTableWidget()
            items_table.setColumnCount(4)
            items_table.setHorizontalHeaderLabels(["Тип", "Название", "Количество/Длина", "Стоимость"])
            items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            items_table.setRowCount(len(order_items))

            for row_idx, (item_id, prod_id, stage_id, quantity, length, name, cost, item_type) in enumerate(
                    order_items):
                type_text = "Изделие" if item_type == 'product' else "Этап"
                quantity_text = str(quantity) if item_type == 'product' else f"{length:.1f} м"

                items_table.setItem(row_idx, 0, QTableWidgetItem(type_text))
                items_table.setItem(row_idx, 1, QTableWidgetItem(name))
                items_table.setItem(row_idx, 2, QTableWidgetItem(quantity_text))
                items_table.setItem(row_idx, 3, QTableWidgetItem(self.format_currency(cost)))

            layout.addWidget(items_table)

            # Кнопка закрытия
            close_btn = QPushButton("Закрыть")
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)

            dialog.setLayout(layout)
            dialog.exec_()

        except Exception as e:
            self.handle_exception(e, "просмотре заказа")

    def generate_order_pdf(self):
        """Генерация PDF для заказа"""
        if not self.selected_item_id:
            return

        try:
            # Получаем данные заказа
            order_summary = self.order_service.export_order_summary(self.selected_item_id)
            if not order_summary:
                self.show_error("Ошибка", "Заказ не найден")
                return

            # Подготавливаем детали заказа для PDF
            order_details = []
            for product in order_summary['products']:
                order_details.append(('product', None, product['name'], product['quantity'],
                                      product['cost'], None))

            for stage in order_summary['stages']:
                order_details.append(('stage', None, stage['name'], 1,
                                      stage['cost'], stage['length_meters']))

            # Рассчитываем требования к материалам
            order_items = []
            for product in order_summary['products']:
                order_items.append(('product', product['id'], product['quantity']))
            for stage in order_summary['stages']:
                order_items.append(('stage', stage['id'], stage['length_meters']))

            requirements = self.order_service.calculate_order_requirements(order_items)

            # Генерируем PDF
            pdf_path = self.pdf_generator.generate_order_pdf(
                self.selected_item_id,
                order_summary['total_cost'],
                order_details,
                requirements,
                order_summary['instructions']
            )

            self.show_info("Успех", f"PDF создан: {pdf_path}")
            self.load_orders()  # Обновляем таблицу с информацией о PDF

        except Exception as e:
            self.handle_exception(e, "генерации PDF")

    def open_order_pdf(self):
        """Открытие PDF заказа"""
        selected_row = self.orders_table.currentRow()
        if selected_row == -1:
            return

        try:
            pdf_filename = self.orders_table.item(selected_row, 4).text()
            if not pdf_filename or pdf_filename == "Нет":
                self.show_warning("Предупреждение", "PDF файл не создан")
                return

            # Формируем путь к PDF
            if hasattr(sys, 'frozen'):
                pdf_dir = os.path.join(os.path.dirname(sys.executable), 'orders')
            else:
                pdf_dir = os.path.join(os.path.dirname(self.db_path), 'orders')

            pdf_path = os.path.join(pdf_dir, pdf_filename)

            if not os.path.exists(pdf_path):
                self.show_error("Ошибка", f"PDF файл не найден: {pdf_path}")
                return

            # Открываем PDF
            import subprocess
            import platform

            if platform.system() == 'Darwin':  # macOS
                subprocess.call(('open', pdf_path))
            elif platform.system() == 'Windows':  # Windows
                os.startfile(pdf_path)
            else:  # Linux
                subprocess.call(('xdg-open', pdf_path))

        except Exception as e:
            self.handle_exception(e, "открытии PDF")

    def delete_order(self):
        """Удаление заказа"""
        if not self.selected_item_id:
            return

        selected_row = self.orders_table.currentRow()
        order_date = self.orders_table.item(selected_row, 1).text()

        if not self.confirm_action("Подтверждение удаления",
                                   f"Удалить заказ №{self.selected_item_id} от {order_date}?"):
            return

        try:
            self.order_service.delete_order(self.selected_item_id)
            self.load_orders()
            self.clear_order_selection()
            self.show_info("Успех", f"Заказ №{self.selected_item_id} удален")

        except Exception as e:
            self.handle_exception(e, "удалении заказа")

    def clear_order_selection(self):
        """Очистка выбора заказа"""
        self.selected_item_id = None
        self.view_order_btn.setEnabled(False)
        self.generate_pdf_btn.setEnabled(False)
        self.open_pdf_btn.setEnabled(False)
        self.delete_order_btn.setEnabled(False)
        self.clear_table_selection(self.orders_table)

    def load_data(self):
        """Переопределение метода загрузки данных из базового класса"""
        self.load_products_and_stages()
        self.load_orders()
        self.on_item_type_changed(self.item_type_combo.currentText())