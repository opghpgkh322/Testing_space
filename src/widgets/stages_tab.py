from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from .base_tab import BaseTab
from ..services.stage_service import StageService
from ..services.product_service import ProductService
from ..services.material_service import MaterialService


class StagesTab(BaseTab):
    """Вкладка для работы с этапами"""

    def __init__(self, db_path, main_window=None):
        super().__init__(db_path, main_window)
        self.stage_service = StageService(db_path)
        self.product_service = ProductService(db_path)
        self.material_service = MaterialService(db_path)
        self.selected_stage_name = None
        self.init_ui()
        self.load_stages()

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        main_splitter = QSplitter(Qt.Horizontal)

        # Левая панель - список этапов
        left_panel = QWidget()
        left_layout = QVBoxLayout()

        stages_group = QGroupBox("Этапы")
        stages_layout = QVBoxLayout()

        # Таблица этапов
        self.stages_table = QTableWidget()
        self.stages_table.setColumnCount(4)
        self.stages_table.setHorizontalHeaderLabels(["ID", "Название", "Себестоимость", "Описание"])
        self.stages_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stages_table.cellClicked.connect(self.on_stage_selected)
        self.stages_table.cellChanged.connect(self.on_stage_cell_edited)
        stages_layout.addWidget(self.stages_table)

        # Форма добавления этапа
        form_layout = QFormLayout()

        self.stage_name_input = QLineEdit()
        self.stage_name_input.setPlaceholderText("Название этапа")
        form_layout.addRow(QLabel("Название этапа:"), self.stage_name_input)

        self.stage_description_input = QTextEdit()
        self.stage_description_input.setPlaceholderText("Описание этапа работ...")
        self.stage_description_input.setMaximumHeight(60)
        form_layout.addRow(QLabel("Описание:"), self.stage_description_input)

        # Кнопки управления этапами
        stage_btn_layout = QHBoxLayout()

        self.add_stage_btn = QPushButton("Добавить этап")
        self.add_stage_btn.clicked.connect(self.add_stage)
        stage_btn_layout.addWidget(self.add_stage_btn)

        self.duplicate_stage_btn = QPushButton("Дублировать этап")
        self.duplicate_stage_btn.clicked.connect(self.duplicate_stage)
        self.duplicate_stage_btn.setEnabled(False)
        stage_btn_layout.addWidget(self.duplicate_stage_btn)

        self.delete_stage_btn = QPushButton("Удалить этап")
        self.delete_stage_btn.clicked.connect(self.delete_stage)
        self.delete_stage_btn.setEnabled(False)
        stage_btn_layout.addWidget(self.delete_stage_btn)

        self.calculate_cost_btn = QPushButton("Рассчитать себестоимость")
        self.calculate_cost_btn.clicked.connect(self.calculate_stage_cost)
        self.calculate_cost_btn.setEnabled(False)
        stage_btn_layout.addWidget(self.calculate_cost_btn)

        form_layout.addRow(stage_btn_layout)
        stages_layout.addLayout(form_layout)
        stages_group.setLayout(stages_layout)
        left_layout.addWidget(stages_group)
        left_panel.setLayout(left_layout)
        main_splitter.addWidget(left_panel)

        # Правая панель - состав этапа
        self.composition_group = QGroupBox("Состав этапа")
        self.composition_group.setEnabled(False)
        composition_layout = QVBoxLayout()

        # Вкладки для изделий и материалов
        composition_tabs = QTabWidget()

        # Вкладка "Изделия в этапе"
        products_tab = QWidget()
        products_layout = QVBoxLayout()

        self.stage_products_table = QTableWidget()
        self.stage_products_table.setColumnCount(5)
        self.stage_products_table.setHorizontalHeaderLabels([
            "ID", "Изделие", "Часть", "Количество", "Стоимость"
        ])
        self.stage_products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stage_products_table.cellChanged.connect(self.on_stage_product_cell_edited)
        self.stage_products_table.cellClicked.connect(self.on_stage_product_selected)
        products_layout.addWidget(self.stage_products_table)

        # Форма добавления изделия в этап
        product_form = QFormLayout()

        self.product_combo = QComboBox()
        product_form.addRow(QLabel("Изделие:"), self.product_combo)

        self.product_part_combo = QComboBox()
        self.product_part_combo.addItems(["start", "meter", "end"])
        self.product_part_combo.setCurrentText("meter")
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
        self.remove_product_from_stage_btn.setEnabled(False)
        product_btn_layout.addWidget(self.remove_product_from_stage_btn)

        product_form.addRow(product_btn_layout)
        products_layout.addLayout(product_form)
        products_tab.setLayout(products_layout)
        composition_tabs.addTab(products_tab, "Изделия")

        # Вкладка "Материалы в этапе"
        materials_tab = QWidget()
        materials_layout = QVBoxLayout()

        self.stage_materials_table = QTableWidget()
        self.stage_materials_table.setColumnCount(7)
        self.stage_materials_table.setHorizontalHeaderLabels([
            "ID", "Материал", "Тип", "Часть", "Количество", "Длина", "Стоимость"
        ])
        self.stage_materials_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stage_materials_table.cellChanged.connect(self.on_stage_material_cell_edited)
        self.stage_materials_table.cellClicked.connect(self.on_stage_material_selected)
        materials_layout.addWidget(self.stage_materials_table)

        # Форма добавления материала в этап
        material_form = QFormLayout()

        self.material_combo = QComboBox()
        material_form.addRow(QLabel("Материал:"), self.material_combo)

        self.material_part_combo = QComboBox()
        self.material_part_combo.addItems(["start", "meter", "end"])
        self.material_part_combo.setCurrentText("meter")
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
        self.remove_material_from_stage_btn.setEnabled(False)
        material_btn_layout.addWidget(self.remove_material_from_stage_btn)

        material_form.addRow(material_btn_layout)
        materials_layout.addLayout(material_form)
        materials_tab.setLayout(materials_layout)
        composition_tabs.addTab(materials_tab, "Материалы")

        composition_layout.addWidget(composition_tabs)

        # Информация о стоимости этапа
        self.cost_info_group = QGroupBox("Стоимость этапа")
        cost_layout = QVBoxLayout()
        self.cost_label = QLabel("Себестоимость этапа: 0.00 руб")
        self.cost_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: #1976D2;")
        cost_layout.addWidget(self.cost_label)

        self.cost_breakdown_label = QLabel("")
        cost_layout.addWidget(self.cost_breakdown_label)
        self.cost_info_group.setLayout(cost_layout)
        composition_layout.addWidget(self.cost_info_group)

        self.composition_group.setLayout(composition_layout)
        main_splitter.addWidget(self.composition_group)
        main_splitter.setSizes([350, 800])

        main_layout = QVBoxLayout()
        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)

    def load_stages(self):
        """Загрузка списка этапов"""
        try:
            stages = self.stage_service.get_all_stages()
            self.stages_table.setRowCount(len(stages))
            self.stages_table.cellChanged.disconnect()  # Отключаем сигнал при загрузке

            for row_idx, (stage_id, stage_name, cost, description) in enumerate(stages):
                # ID (только для чтения)
                id_item = self.make_item_readonly(stage_id)
                self.stages_table.setItem(row_idx, 0, id_item)

                # Название (редактируемое)
                self.stages_table.setItem(row_idx, 1, QTableWidgetItem(stage_name))

                # Себестоимость (только для чтения)
                cost_item = self.make_item_readonly(self.format_currency(cost))
                self.stages_table.setItem(row_idx, 2, cost_item)

                # Описание (редактируемое)
                self.stages_table.setItem(row_idx, 3, QTableWidgetItem(description or ""))

            self.stages_table.cellChanged.connect(self.on_stage_cell_edited)  # Подключаем обратно

        except Exception as e:
            self.handle_exception(e, "загрузке этапов")

    def load_products(self):
        """Загрузка списка изделий для комбобокса"""
        try:
            products = self.product_service.get_products_for_stages()
            self.product_combo.clear()
            for prod_id, prod_name, cost in products:
                self.product_combo.addItem(f"{prod_name} ({self.format_currency(cost)})", prod_id)
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

    def on_stage_selected(self, row, col):
        """Обработка выбора этапа"""
        stage_id = self.get_selected_item_id(self.stages_table, row)
        if stage_id is None:
            return

        try:
            stage = self.stage_service.get_stage_by_id(stage_id)
            if not stage:
                self.show_error("Ошибка", "Этап не найден")
                return

            self.selected_item_id = stage_id
            self.selected_stage_name = stage[1]

            # Активируем группу состава и кнопки
            self.composition_group.setEnabled(True)
            self.composition_group.setTitle(f"Состав этапа: {self.selected_stage_name}")

            self.duplicate_stage_btn.setEnabled(True)
            self.delete_stage_btn.setEnabled(True)
            self.calculate_cost_btn.setEnabled(True)

            # Загружаем данные для комбобоксов и состав этапа
            self.load_products()
            self.load_materials()
            self.load_stage_products()
            self.load_stage_materials()
            self.update_cost_info()

        except Exception as e:
            self.handle_exception(e, "выборе этапа")

    def on_stage_cell_edited(self, row, column):
        """Обработка редактирования ячеек в таблице этапов"""
        try:
            stage_id = self.get_selected_item_id(self.stages_table, row)
            if not stage_id:
                return

            if column == 1:  # Название этапа
                new_name = self.stages_table.item(row, column).text().strip()
                if not new_name:
                    self.show_warning("Ошибка", "Название этапа не может быть пустым")
                    self.load_stages()
                    return

                if self.stage_service.stage_exists(new_name, stage_id):
                    self.show_warning("Ошибка", "Этап с таким названием уже существует")
                    self.load_stages()
                    return

                self.stage_service.update_stage(stage_id, new_name)
                self.selected_stage_name = new_name
                if self.composition_group.isEnabled():
                    self.composition_group.setTitle(f"Состав этапа: {new_name}")

            elif column == 3:  # Описание этапа
                new_description = self.stages_table.item(row, column).text()
                current_name = self.stages_table.item(row, 1).text()
                self.stage_service.update_stage(stage_id, current_name, new_description)

        except Exception as e:
            self.handle_exception(e, "редактировании этапа")
            self.load_stages()

    def on_stage_product_selected(self, row, col):
        """Обработка выбора изделия в этапе"""
        sp_id = self.get_selected_item_id(self.stage_products_table, row)
        if sp_id is not None:
            self.remove_product_from_stage_btn.setEnabled(True)

    def on_stage_material_selected(self, row, col):
        """Обработка выбора материала в этапе"""
        sm_id = self.get_selected_item_id(self.stage_materials_table, row)
        if sm_id is not None:
            self.remove_material_from_stage_btn.setEnabled(True)

    def on_stage_product_cell_edited(self, row, column):
        """Редактирование изделия в этапе"""
        try:
            sp_id = self.get_selected_item_id(self.stage_products_table, row)
            if not sp_id:
                return

            if column == 2:  # Часть
                new_part = self.stage_products_table.item(row, column).text().strip()
                if new_part not in ("start", "meter", "end"):
                    self.show_warning("Ошибка", "Часть должна быть: start, meter или end")
                    self.load_stage_products()
                    return

                current_quantity = int(self.stage_products_table.item(row, 3).text())
                self.stage_service.update_stage_product(sp_id, current_quantity, new_part)

            elif column == 3:  # Количество
                new_quantity = self.validate_int_input(
                    self.stage_products_table.item(row, column).text(), "Количество", min_value=1)
                if new_quantity is None:
                    self.load_stage_products()
                    return

                current_part = self.stage_products_table.item(row, 2).text()
                self.stage_service.update_stage_product(sp_id, new_quantity, current_part)

            self.load_stage_products()
            self.update_cost_info()

        except Exception as e:
            self.handle_exception(e, "редактировании изделия этапа")
            self.load_stage_products()

    def on_stage_material_cell_edited(self, row, column):
        """Редактирование материала в этапе"""
        try:
            sm_id = self.get_selected_item_id(self.stage_materials_table, row)
            if not sm_id:
                return

            current_quantity = int(self.stage_materials_table.item(row, 4).text())
            current_length_text = self.stage_materials_table.item(row, 5).text().strip()
            current_length = float(current_length_text) if current_length_text else None
            current_part = self.stage_materials_table.item(row, 3).text()

            if column == 3:  # Часть
                new_part = self.stage_materials_table.item(row, column).text().strip()
                if new_part not in ("start", "meter", "end"):
                    self.show_warning("Ошибка", "Часть должна быть: start, meter или end")
                    self.load_stage_materials()
                    return
                self.stage_service.update_stage_material(sm_id, current_quantity, current_length, new_part)

            elif column == 4:  # Количество
                new_quantity = self.validate_int_input(
                    self.stage_materials_table.item(row, column).text(), "Количество", min_value=1)
                if new_quantity is None:
                    self.load_stage_materials()
                    return
                self.stage_service.update_stage_material(sm_id, new_quantity, current_length, current_part)

            elif column == 5:  # Длина
                new_length_text = self.stage_materials_table.item(row, column).text().strip()
                new_length = None
                if new_length_text:
                    new_length = self.validate_float_input(new_length_text, "Длина", min_value=0)
                    if new_length is None:
                        self.load_stage_materials()
                        return
                self.stage_service.update_stage_material(sm_id, current_quantity, new_length, current_part)

            self.load_stage_materials()
            self.update_cost_info()

        except Exception as e:
            self.handle_exception(e, "редактировании материала этапа")
            self.load_stage_materials()

    def load_stage_products(self):
        """Загрузка изделий в составе выбранного этапа"""
        if not self.selected_item_id:
            return

        try:
            stage_products = self.stage_service.get_stage_products(self.selected_item_id)
            self.stage_products_table.cellChanged.disconnect()
            self.stage_products_table.setRowCount(len(stage_products))

            for row_idx, (sp_id, prod_name, part, quantity, cost, total_cost) in enumerate(stage_products):
                self.populate_table_row(self.stage_products_table, row_idx, [
                    sp_id,
                    prod_name,
                    part,
                    quantity,
                    self.format_currency(total_cost)
                ], readonly_columns=[0, 1, 4])  # ID, название и стоимость только для чтения

            self.stage_products_table.cellChanged.connect(self.on_stage_product_cell_edited)

        except Exception as e:
            self.handle_exception(e, "загрузке изделий этапа")

    def load_stage_materials(self):
        """Загрузка материалов в составе выбранного этапа"""
        if not self.selected_item_id:
            return

        try:
            stage_materials = self.stage_service.get_stage_materials(self.selected_item_id)
            self.stage_materials_table.cellChanged.disconnect()
            self.stage_materials_table.setRowCount(len(stage_materials))

            for row_idx, (sm_id, mat_name, mat_type, part, quantity, length, price, total_cost) in enumerate(
                    stage_materials):
                length_display = self.format_length(length) if length else ""

                # Для метизов делаем колонку длины нередактируемой
                length_item = QTableWidgetItem(length_display)
                if mat_type == "Метиз":
                    length_item.setFlags(length_item.flags() ^ Qt.ItemIsEditable)

                self.stage_materials_table.setItem(row_idx, 0, self.make_item_readonly(sm_id))
                self.stage_materials_table.setItem(row_idx, 1, self.make_item_readonly(mat_name))
                self.stage_materials_table.setItem(row_idx, 2, self.make_item_readonly(mat_type))
                self.stage_materials_table.setItem(row_idx, 3, QTableWidgetItem(part))
                self.stage_materials_table.setItem(row_idx, 4, QTableWidgetItem(str(quantity)))
                self.stage_materials_table.setItem(row_idx, 5, length_item)
                self.stage_materials_table.setItem(row_idx, 6,
                                                   self.make_item_readonly(self.format_currency(total_cost)))

            self.stage_materials_table.cellChanged.connect(self.on_stage_material_cell_edited)

        except Exception as e:
            self.handle_exception(e, "загрузке материалов этапа")

    def add_stage(self):
        """Добавление нового этапа"""
        name = self.validate_text_input(self.stage_name_input.text(), "Название этапа")
        if name is None:
            return

        description = self.stage_description_input.toPlainText().strip()

        try:
            if self.stage_service.stage_exists(name):
                self.show_warning("Ошибка", "Этап с таким названием уже существует")
                return

            stage_id = self.stage_service.add_stage(name, description)
            self.load_stages()
            self.stage_name_input.clear()
            self.stage_description_input.clear()
            self.show_info("Успех", f"Этап '{name}' добавлен с ID {stage_id}")
            self.set_status_message(f"Добавлен этап: {name}", 3000)

        except Exception as e:
            self.handle_exception(e, "добавлении этапа")

    def duplicate_stage(self):
        """Дублирование этапа"""
        if not self.selected_item_id:
            self.show_warning("Ошибка", "Сначала выберите этап")
            return

        try:
            # Получаем текущее название
            stage = self.stage_service.get_stage_by_id(self.selected_item_id)
            if not stage:
                self.show_error("Ошибка", "Этап не найден")
                return

            original_name = stage[1]
            new_name = f"{original_name} (копия)"

            # Проверяем уникальность и добавляем номер если нужно
            counter = 1
            while self.stage_service.stage_exists(new_name):
                counter += 1
                new_name = f"{original_name} (копия {counter})"

            new_stage_id = self.stage_service.duplicate_stage(self.selected_item_id, new_name)
            self.load_stages()
            self.show_info("Успех", f"Этап продублирован как '{new_name}'")
            self.set_status_message(f"Создана копия: {new_name}", 3000)

        except Exception as e:
            self.handle_exception(e, "дублировании этапа")

    def delete_stage(self):
        """Удаление этапа"""
        selected_row = self.stages_table.currentRow()
        if selected_row == -1:
            self.show_warning("Ошибка", "Выберите этап для удаления")
            return

        try:
            stage_id = self.get_selected_item_id(self.stages_table, selected_row)
            stage_name = self.stages_table.item(selected_row, 1).text()

            if not self.confirm_action("Подтверждение",
                                       f"Вы уверены, что хотите удалить этап '{stage_name}'?\n"
                                       "Это удалит весь его состав."):
                return

            self.stage_service.delete_stage(stage_id)
            self.load_stages()
            self.composition_group.setEnabled(False)
            self.clear_selection()
            self.show_info("Успех", f"Этап '{stage_name}' удален")
            self.set_status_message(f"Удален этап: {stage_name}", 3000)

        except Exception as e:
            self.handle_exception(e, "удалении этапа")

    def add_product_to_stage(self):
        """Добавление изделия в этап"""
        if not self.selected_item_id:
            self.show_warning("Ошибка", "Сначала выберите этап")
            return

        product_id = self.product_combo.currentData()
        if not product_id:
            self.show_warning("Ошибка", "Выберите изделие")
            return

        part = self.product_part_combo.currentText()
        quantity = self.product_quantity_input.value()

        try:
            self.stage_service.add_product_to_stage(self.selected_item_id, product_id, quantity, part)
            self.load_stage_products()
            self.update_cost_info()

            product_name = self.product_combo.currentText().split(' (')[0]
            self.show_info("Успех", f"Изделие '{product_name}' добавлено в этап")

        except Exception as e:
            self.handle_exception(e, "добавлении изделия в этап")

    def remove_product_from_stage(self):
        """Удаление изделия из этапа"""
        selected_row = self.stage_products_table.currentRow()
        if selected_row == -1:
            self.show_warning("Ошибка", "Выберите изделие для удаления")
            return

        try:
            sp_id = self.get_selected_item_id(self.stage_products_table, selected_row)
            product_name = self.stage_products_table.item(selected_row, 1).text()
            part = self.stage_products_table.item(selected_row, 2).text()

            if not self.confirm_action("Подтверждение",
                                       f"Удалить изделие '{product_name}' ({part}) из этапа?"):
                return

            self.stage_service.remove_product_from_stage(sp_id)
            self.load_stage_products()
            self.update_cost_info()
            self.remove_product_from_stage_btn.setEnabled(False)
            self.show_info("Успех", f"Изделие '{product_name}' удалено из этапа")

        except Exception as e:
            self.handle_exception(e, "удалении изделия из этапа")

    def add_material_to_stage(self):
        """Добавление материала в этап"""
        if not self.selected_item_id:
            self.show_warning("Ошибка", "Сначала выберите этап")
            return

        material_id = self.material_combo.currentData()
        if not material_id:
            self.show_warning("Ошибка", "Выберите материал")
            return

        part = self.material_part_combo.currentText()
        quantity = self.material_quantity_input.value()

        length_text = self.material_length_input.text().strip()
        length = None
        if length_text:
            length = self.validate_float_input(length_text, "Длина", min_value=0.01)
            if length is None:
                return

        try:
            self.stage_service.add_material_to_stage(self.selected_item_id, material_id, quantity, length, part)
            self.load_stage_materials()
            self.update_cost_info()
            self.material_length_input.clear()

            material_name = self.material_combo.currentText().split(' (')[0]
            self.show_info("Успех", f"Материал '{material_name}' добавлен в этап")

        except Exception as e:
            self.handle_exception(e, "добавлении материала в этап")

    def remove_material_from_stage(self):
        """Удаление материала из этапа"""
        selected_row = self.stage_materials_table.currentRow()
        if selected_row == -1:
            self.show_warning("Ошибка", "Выберите материал для удаления")
            return

        try:
            sm_id = self.get_selected_item_id(self.stage_materials_table, selected_row)
            material_name = self.stage_materials_table.item(selected_row, 1).text()
            part = self.stage_materials_table.item(selected_row, 3).text()

            if not self.confirm_action("Подтверждение",
                                       f"Удалить материал '{material_name}' ({part}) из этапа?"):
                return

            self.stage_service.remove_material_from_stage(sm_id)
            self.load_stage_materials()
            self.update_cost_info()
            self.remove_material_from_stage_btn.setEnabled(False)
            self.show_info("Успех", f"Материал '{material_name}' удален из этапа")

        except Exception as e:
            self.handle_exception(e, "удалении материала из этапа")

    def calculate_stage_cost(self):
        """Расчет себестоимости этапа"""
        if not self.selected_item_id:
            self.show_warning("Ошибка", "Сначала выберите этап")
            return

        try:
            cost_info = self.stage_service.calculate_stage_cost(self.selected_item_id)
            self.load_stages()  # Обновляем таблицу с новой стоимостью
            self.update_cost_info()

            total_cost = cost_info['total_per_meter']
            self.show_info("Успех", f"Себестоимость рассчитана: {self.format_currency(total_cost)} за метр")

        except Exception as e:
            self.handle_exception(e, "расчете себестоимости этапа")

    def update_cost_info(self):
        """Обновление информации о стоимости этапа"""
        if not self.selected_item_id:
            return

        try:
            cost_info = self.stage_service.calculate_stage_cost(self.selected_item_id)
            breakdown = self.stage_service.get_stage_cost_breakdown(self.selected_item_id)

            # Основная информация о стоимости
            start_cost = cost_info['start_cost']
            meter_cost = cost_info['meter_cost']
            end_cost = cost_info['end_cost']
            total_per_meter = cost_info['total_per_meter']

            main_text = f"Себестоимость этапа (1 м): {self.format_currency(total_per_meter)}<br>"
            main_text += f"• Начальный крепеж: {self.format_currency(start_cost)}<br>"
            main_text += f"• За метр: {self.format_currency(meter_cost)}<br>"
            main_text += f"• Конечный крепеж: {self.format_currency(end_cost)}"

            self.cost_label.setText(main_text)

            # Детализация по компонентам
            breakdown_text = "<b>Детализация:</b><br>"

            for part_name, part_key in [("Начальный крепеж", "start"), ("За метр", "meter"),
                                        ("Конечный крепеж", "end")]:
                part_total = breakdown['totals'][part_key]
                if part_total > 0:
                    breakdown_text += f"<br><b>{part_name} ({self.format_currency(part_total)}):</b><br>"

                    # Изделия
                    for item in breakdown['products'][part_key]:
                        breakdown_text += f"  • {item['name']}: {item['quantity']}шт x {self.format_currency(item['unit_cost'])} = {self.format_currency(item['total_cost'])}<br>"

                    # Материалы
                    for item in breakdown['materials'][part_key]:
                        if item['length']:
                            breakdown_text += f"  • {item['name']}: {item['quantity']}шт x {item['length']}м x {self.format_currency(item['unit_price'])} = {self.format_currency(item['total_cost'])}<br>"
                        else:
                            breakdown_text += f"  • {item['name']}: {item['quantity']}шт x {self.format_currency(item['unit_price'])} = {self.format_currency(item['total_cost'])}<br>"

            self.cost_breakdown_label.setText(breakdown_text)

        except Exception as e:
            self.cost_breakdown_label.setText(f"Ошибка расчета: {str(e)}")

    def clear_selection(self):
        """Очистка выбора"""
        self.selected_item_id = None
        self.selected_stage_name = None
        self.duplicate_stage_btn.setEnabled(False)
        self.delete_stage_btn.setEnabled(False)
        self.calculate_cost_btn.setEnabled(False)
        self.remove_product_from_stage_btn.setEnabled(False)
        self.remove_material_from_stage_btn.setEnabled(False)
        self.clear_table_selection(self.stages_table)

    def load_data(self):
        """Переопределение метода загрузки данных из базового класса"""
        self.load_stages()

    def get_stages_for_orders(self):
        """Получить список этапов для использования в заказах"""
        try:
            return self.stage_service.get_all_stages()
        except Exception as e:
            print(f"Ошибка при получении этапов для заказов: {str(e)}")
            return []