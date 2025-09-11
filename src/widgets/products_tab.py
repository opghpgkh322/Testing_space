from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from .base_tab import BaseTab
from ..services.product_service import ProductService
from ..services.material_service import MaterialService


class ProductsTab(BaseTab):
    """Вкладка для работы с изделиями"""

    def __init__(self, db_path, main_window=None):
        super().__init__(db_path, main_window)
        self.product_service = ProductService(db_path)
        self.material_service = MaterialService(db_path)
        self.selected_composition_id = None
        self.init_ui()
        self.load_products()

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        main_layout = QVBoxLayout()

        # Группа изделий
        products_group = QGroupBox("Изделия")
        products_layout = QVBoxLayout()

        # Таблица изделий
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(3)
        self.products_table.setHorizontalHeaderLabels(["ID", "Название", "Себестоимость"])
        self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.products_table.cellClicked.connect(self.on_product_selected)
        products_layout.addWidget(self.products_table)

        # Форма добавления изделия
        product_form_layout = QFormLayout()

        self.product_name_input = QLineEdit()
        self.product_name_input.setPlaceholderText("Островок")
        product_form_layout.addRow(QLabel("Название изделия:"), self.product_name_input)

        # Кнопки управления изделиями
        product_btn_layout = QHBoxLayout()

        self.add_product_btn = QPushButton("Добавить изделие")
        self.add_product_btn.clicked.connect(self.add_product)
        product_btn_layout.addWidget(self.add_product_btn)

        self.duplicate_product_btn = QPushButton("Дублировать изделие")
        self.duplicate_product_btn.clicked.connect(self.duplicate_product)
        self.duplicate_product_btn.setEnabled(False)
        product_btn_layout.addWidget(self.duplicate_product_btn)

        self.delete_product_btn = QPushButton("Удалить изделие")
        self.delete_product_btn.clicked.connect(self.delete_product)
        self.delete_product_btn.setEnabled(False)
        product_btn_layout.addWidget(self.delete_product_btn)

        self.calculate_cost_btn = QPushButton("Рассчитать себестоимость")
        self.calculate_cost_btn.clicked.connect(self.calculate_product_cost)
        self.calculate_cost_btn.setEnabled(False)
        product_btn_layout.addWidget(self.calculate_cost_btn)

        product_form_layout.addRow(product_btn_layout)
        products_layout.addLayout(product_form_layout)
        products_group.setLayout(products_layout)
        main_layout.addWidget(products_group)

        # Группа состава изделия
        self.composition_group = QGroupBox("Состав изделия")
        self.composition_group.setEnabled(False)
        composition_layout = QVBoxLayout()

        # Таблица состава
        self.composition_table = QTableWidget()
        self.composition_table.setColumnCount(6)
        self.composition_table.setHorizontalHeaderLabels([
            "ID", "Материал", "Тип", "Количество", "Длина (м)", "Стоимость"
        ])
        self.composition_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.composition_table.cellClicked.connect(self.on_composition_selected)
        self.composition_table.cellDoubleClicked.connect(self.edit_composition_item)
        composition_layout.addWidget(self.composition_table)

        # Форма добавления материала в состав
        add_material_layout = QFormLayout()

        self.material_combo = QComboBox()
        self.load_materials()
        add_material_layout.addRow(QLabel("Материал:"), self.material_combo)

        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("1")
        add_material_layout.addRow(QLabel("Количество:"), self.quantity_input)

        self.length_input = QLineEdit()
        self.length_input.setPlaceholderText("0.75 (для пиломатериалов)")
        add_material_layout.addRow(QLabel("Длина (м):"), self.length_input)

        # Кнопки управления составом
        composition_btn_layout = QHBoxLayout()

        self.add_to_composition_btn = QPushButton("Добавить в состав")
        self.add_to_composition_btn.clicked.connect(self.add_to_composition)
        composition_btn_layout.addWidget(self.add_to_composition_btn)

        self.remove_from_composition_btn = QPushButton("Удалить из состава")
        self.remove_from_composition_btn.clicked.connect(self.remove_from_composition)
        self.remove_from_composition_btn.setEnabled(False)
        composition_btn_layout.addWidget(self.remove_from_composition_btn)

        self.clear_composition_btn = QPushButton("Очистить состав")
        self.clear_composition_btn.clicked.connect(self.clear_composition)
        composition_btn_layout.addWidget(self.clear_composition_btn)

        add_material_layout.addRow(composition_btn_layout)
        composition_layout.addLayout(add_material_layout)

        # Информация о себестоимости
        self.cost_info_group = QGroupBox("Детализация себестоимости")
        cost_info_layout = QVBoxLayout()
        self.cost_label = QLabel("Себестоимость: 0.00 руб")
        self.cost_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: #2E7D32;")
        cost_info_layout.addWidget(self.cost_label)

        self.cost_breakdown_label = QLabel("")
        cost_info_layout.addWidget(self.cost_breakdown_label)
        self.cost_info_group.setLayout(cost_info_layout)

        composition_layout.addWidget(self.cost_info_group)
        self.composition_group.setLayout(composition_layout)
        main_layout.addWidget(self.composition_group)

        self.setLayout(main_layout)

    def load_products(self):
        """Загрузка списка изделий"""
        try:
            products = self.product_service.get_all_products()
            self.products_table.setRowCount(len(products))

            for row_idx, (prod_id, prod_name, cost) in enumerate(products):
                self.populate_table_row(self.products_table, row_idx, [
                    prod_id,
                    prod_name,
                    self.format_currency(cost)
                ], readonly_columns=[0, 2])  # ID и стоимость только для чтения

        except Exception as e:
            self.handle_exception(e, "загрузке изделий")

    def load_materials(self):
        """Загрузка списка материалов для комбобокса"""
        try:
            materials = self.material_service.get_all_materials()
            self.material_combo.clear()
            for mat_id, mat_name, mat_type, price in materials:
                self.material_combo.addItem(f"{mat_name} ({mat_type})", mat_id)
        except Exception as e:
            self.handle_exception(e, "загрузке материалов")

    def on_product_selected(self, row, col):
        """Обработка выбора изделия"""
        product_id = self.get_selected_item_id(self.products_table, row)
        if product_id is None:
            return

        try:
            # Получаем данные изделия
            product = self.product_service.get_product_by_id(product_id)
            if not product:
                self.show_error("Ошибка", "Изделие не найдено")
                return

            self.selected_item_id = product_id
            product_name = product[1]

            # Активируем группу состава и кнопки
            self.composition_group.setEnabled(True)
            self.composition_group.setTitle(f"Состав изделия: {product_name}")

            self.duplicate_product_btn.setEnabled(True)
            self.delete_product_btn.setEnabled(True)
            self.calculate_cost_btn.setEnabled(True)

            # Загружаем состав и рассчитываем стоимость
            self.load_composition()
            self.update_cost_info()

        except Exception as e:
            self.handle_exception(e, "выборе изделия")

    def on_composition_selected(self, row, col):
        """Обработка выбора элемента состава"""
        composition_id = self.get_selected_item_id(self.composition_table, row)
        if composition_id is not None:
            self.selected_composition_id = composition_id
            self.remove_from_composition_btn.setEnabled(True)

    def edit_composition_item(self, row, col):
        """Редактирование элемента состава по двойному клику"""
        if col not in [3, 4]:  # Только количество и длина редактируются
            return

        composition_id = self.get_selected_item_id(self.composition_table, row)
        if not composition_id:
            return

        try:
            current_quantity = int(self.composition_table.item(row, 3).text())
            current_length_text = self.composition_table.item(row, 4).text()
            current_length = float(current_length_text) if current_length_text else None

            dialog = QDialog(self)
            dialog.setWindowTitle("Редактирование состава")
            dialog.setFixedSize(300, 150)
            layout = QVBoxLayout()

            if col == 3:  # Количество
                layout.addWidget(QLabel("Новое количество:"))
                spin_box = QSpinBox()
                spin_box.setMinimum(1)
                spin_box.setMaximum(999)
                spin_box.setValue(current_quantity)
                layout.addWidget(spin_box)

                def update_quantity():
                    try:
                        self.product_service.update_product_composition_item(
                            composition_id, spin_box.value(), current_length)
                        self.load_composition()
                        self.update_cost_info()
                        dialog.accept()
                    except Exception as e:
                        self.handle_exception(e, "обновлении количества")

                btn_layout = QHBoxLayout()
                ok_btn = QPushButton("OK")
                ok_btn.clicked.connect(update_quantity)
                cancel_btn = QPushButton("Отмена")
                cancel_btn.clicked.connect(dialog.reject)
                btn_layout.addWidget(ok_btn)
                btn_layout.addWidget(cancel_btn)
                layout.addLayout(btn_layout)

            elif col == 4:  # Длина
                layout.addWidget(QLabel("Новая длина (м):"))
                length_input = QLineEdit()
                length_input.setText(str(current_length) if current_length else "")
                length_input.setPlaceholderText("Оставьте пустым для метизов")
                layout.addWidget(length_input)

                def update_length():
                    try:
                        length_text = length_input.text().strip()
                        new_length = float(length_text) if length_text else None

                        self.product_service.update_product_composition_item(
                            composition_id, current_quantity, new_length)
                        self.load_composition()
                        self.update_cost_info()
                        dialog.accept()
                    except ValueError:
                        self.show_warning("Ошибка", "Длина должна быть числом")
                    except Exception as e:
                        self.handle_exception(e, "обновлении длины")

                btn_layout = QHBoxLayout()
                ok_btn = QPushButton("OK")
                ok_btn.clicked.connect(update_length)
                cancel_btn = QPushButton("Отмена")
                cancel_btn.clicked.connect(dialog.reject)
                btn_layout.addWidget(ok_btn)
                btn_layout.addWidget(cancel_btn)
                layout.addLayout(btn_layout)

            dialog.setLayout(layout)
            dialog.exec_()

        except Exception as e:
            self.handle_exception(e, "редактировании состава")

    def load_composition(self):
        """Загрузка состава изделия"""
        if not self.selected_item_id:
            return

        try:
            composition = self.product_service.get_product_composition(self.selected_item_id)
            self.composition_table.setRowCount(len(composition))

            for row_idx, (comp_id, mat_name, mat_type, quantity, length, price, total_cost) in enumerate(composition):
                length_display = self.format_length(length) if length else ""

                self.populate_table_row(self.composition_table, row_idx, [
                    comp_id,
                    mat_name,
                    mat_type,
                    quantity,
                    length_display,
                    self.format_currency(total_cost)
                ], readonly_columns=[0, 1, 2, 5])  # ID, материал, тип и стоимость только для чтения

        except Exception as e:
            self.handle_exception(e, "загрузке состава изделия")

    def add_product(self):
        """Добавление нового изделия"""
        name = self.validate_text_input(self.product_name_input.text(), "Название изделия")
        if name is None:
            return

        try:
            if self.product_service.product_exists(name):
                self.show_warning("Ошибка", "Изделие с таким названием уже существует")
                return

            product_id = self.product_service.add_product(name)
            self.load_products()
            self.product_name_input.clear()
            self.show_info("Успех", f"Изделие '{name}' добавлено с ID {product_id}")
            self.set_status_message(f"Добавлено изделие: {name}", 3000)

        except Exception as e:
            self.handle_exception(e, "добавлении изделия")

    def duplicate_product(self):
        """Дублирование изделия"""
        if not self.selected_item_id:
            self.show_warning("Ошибка", "Сначала выберите изделие")
            return

        try:
            # Получаем текущее название
            product = self.product_service.get_product_by_id(self.selected_item_id)
            if not product:
                self.show_error("Ошибка", "Изделие не найдено")
                return

            original_name = product[1]
            new_name = f"{original_name} (копия)"

            # Проверяем уникальность и добавляем номер если нужно
            counter = 1
            while self.product_service.product_exists(new_name):
                counter += 1
                new_name = f"{original_name} (копия {counter})"

            new_product_id = self.product_service.duplicate_product(self.selected_item_id, new_name)
            self.load_products()
            self.show_info("Успех", f"Изделие продублировано как '{new_name}'")
            self.set_status_message(f"Создана копия: {new_name}", 3000)

        except Exception as e:
            self.handle_exception(e, "дублировании изделия")

    def delete_product(self):
        """Удаление изделия"""
        selected_row = self.products_table.currentRow()
        if selected_row == -1:
            self.show_warning("Ошибка", "Выберите изделие для удаления")
            return

        try:
            product_id = self.get_selected_item_id(self.products_table, selected_row)
            product_name = self.products_table.item(selected_row, 1).text()

            if not self.confirm_action("Подтверждение",
                                       f"Вы уверены, что хотите удалить изделие '{product_name}'?\n"
                                       "Это также удалит его из всех этапов."):
                return

            self.product_service.delete_product(product_id)
            self.load_products()
            self.composition_group.setEnabled(False)
            self.clear_selection()
            self.show_info("Успех", f"Изделие '{product_name}' удалено")
            self.set_status_message(f"Удалено изделие: {product_name}", 3000)

            # Обновляем связанные вкладки
            self.refresh_related_tabs(['stages'])

        except Exception as e:
            self.handle_exception(e, "удалении изделия")

    def add_to_composition(self):
        """Добавление материала в состав изделия"""
        if not self.selected_item_id:
            self.show_warning("Ошибка", "Сначала выберите изделие")
            return

        material_id = self.material_combo.currentData()
        if not material_id:
            self.show_warning("Ошибка", "Выберите материал")
            return

        quantity = self.validate_int_input(self.quantity_input.text(), "Количество", min_value=1)
        if quantity is None:
            return

        length_text = self.length_input.text().strip()
        length = None
        if length_text:
            length = self.validate_float_input(length_text, "Длина", min_value=0.01)
            if length is None:
                return

        try:
            self.product_service.add_material_to_product(self.selected_item_id, material_id, quantity, length)
            self.load_composition()
            self.update_cost_info()
            self.quantity_input.clear()
            self.length_input.clear()

            material_name = self.material_combo.currentText().split(' (')[0]
            self.show_info("Успех", f"Материал '{material_name}' добавлен в состав")

        except Exception as e:
            self.handle_exception(e, "добавлении материала в состав")

    def remove_from_composition(self):
        """Удаление материала из состава изделия"""
        if not self.selected_composition_id:
            self.show_warning("Ошибка", "Выберите материал для удаления")
            return

        selected_row = self.composition_table.currentRow()
        material_name = self.composition_table.item(selected_row, 1).text()

        if not self.confirm_action("Подтверждение",
                                   f"Удалить материал '{material_name}' из состава?"):
            return

        try:
            self.product_service.remove_material_from_product(self.selected_composition_id)
            self.load_composition()
            self.update_cost_info()
            self.selected_composition_id = None
            self.remove_from_composition_btn.setEnabled(False)
            self.show_info("Успех", f"Материал '{material_name}' удален из состава")

        except Exception as e:
            self.handle_exception(e, "удалении материала из состава")

    def clear_composition(self):
        """Очистка всего состава изделия"""
        if not self.selected_item_id:
            return

        if not self.confirm_action("Подтверждение",
                                   "Удалить все материалы из состава изделия?"):
            return

        try:
            # Получаем все элементы состава и удаляем их
            composition = self.product_service.get_product_composition(self.selected_item_id)
            for comp_id, _, _, _, _, _, _ in composition:
                self.product_service.remove_material_from_product(comp_id)

            self.load_composition()
            self.update_cost_info()
            self.show_info("Успех", "Состав изделия очищен")

        except Exception as e:
            self.handle_exception(e, "очистке состава")

    def calculate_product_cost(self):
        """Расчет себестоимости изделия"""
        if not self.selected_item_id:
            self.show_warning("Ошибка", "Сначала выберите изделие")
            return

        try:
            cost = self.product_service.calculate_product_cost(self.selected_item_id)
            self.load_products()  # Обновляем таблицу с новой стоимостью
            self.update_cost_info()
            self.show_info("Успех", f"Себестоимость рассчитана: {self.format_currency(cost)}")

        except Exception as e:
            self.handle_exception(e, "расчете себестоимости")

    def update_cost_info(self):
        """Обновление информации о себестоимости"""
        if not self.selected_item_id:
            return

        try:
            # Получаем общую стоимость
            product = self.product_service.get_product_by_id(self.selected_item_id)
            if not product:
                return

            total_cost = product[2]
            self.cost_label.setText(f"Себестоимость: {self.format_currency(total_cost)}")

            # Получаем детализацию
            breakdown = self.product_service.get_product_cost_breakdown(self.selected_item_id)
            if not breakdown:
                self.cost_breakdown_label.setText("Состав пуст")
                return

            breakdown_text = "<b>Детализация по материалам:</b><br>"
            for name, m_type, quantity, length, price, mat_cost, percentage in breakdown:
                if length:
                    breakdown_text += f"• {name}: {quantity} x {length}м x {price:.2f}руб = {mat_cost:.2f}руб ({percentage}%)<br>"
                else:
                    breakdown_text += f"• {name}: {quantity}шт x {price:.2f}руб = {mat_cost:.2f}руб ({percentage}%)<br>"

            self.cost_breakdown_label.setText(breakdown_text)

        except Exception as e:
            self.cost_breakdown_label.setText(f"Ошибка расчета: {str(e)}")

    def clear_selection(self):
        """Очистка выбора"""
        self.selected_item_id = None
        self.selected_composition_id = None
        self.duplicate_product_btn.setEnabled(False)
        self.delete_product_btn.setEnabled(False)
        self.calculate_cost_btn.setEnabled(False)
        self.remove_from_composition_btn.setEnabled(False)
        self.clear_table_selection(self.products_table)
        self.clear_table_selection(self.composition_table)

    def load_data(self):
        """Переопределение метода загрузки данных из базового класса"""
        self.load_products()
        self.load_materials()

    def get_products_for_stages(self):
        """Получить список изделий для использования в этапах"""
        try:
            return self.product_service.get_products_for_stages()
        except Exception as e:
            print(f"Ошибка при получении изделий для этапов: {str(e)}")
            return []