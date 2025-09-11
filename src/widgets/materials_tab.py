from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from .base_tab import BaseTab
from ..services.material_service import MaterialService


class MaterialsTab(BaseTab):
    """Вкладка для работы с материалами"""

    def __init__(self, db_path, main_window=None):
        super().__init__(db_path, main_window)
        self.material_service = MaterialService(db_path)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        layout = QVBoxLayout()

        # Таблица материалов
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Название", "Тип", "Цена"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellClicked.connect(self.on_table_cell_clicked)
        layout.addWidget(self.table)

        # Форма добавления/редактирования
        form_group = QGroupBox("Добавить/редактировать материал")
        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Брус 100x100")
        form_layout.addRow(QLabel("Название:"), self.name_input)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Пиломатериал", "Метиз"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        form_layout.addRow(QLabel("Тип:"), self.type_combo)

        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("5.00")
        form_layout.addRow(QLabel("Цена:"), self.price_input)

        self.unit_label = QLabel("м")
        form_layout.addRow(QLabel("Ед. изм:"), self.unit_label)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Кнопки управления
        buttons_layout = QHBoxLayout()

        self.add_btn = QPushButton("Добавить материал")
        self.add_btn.clicked.connect(self.add_material)
        buttons_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Сохранить изменения")
        self.edit_btn.clicked.connect(self.edit_material)
        self.edit_btn.setEnabled(False)
        buttons_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Удалить материал")
        self.delete_btn.clicked.connect(self.delete_material)
        self.delete_btn.setEnabled(False)
        buttons_layout.addWidget(self.delete_btn)

        self.clear_btn = QPushButton("Очистить форму")
        self.clear_btn.clicked.connect(self.clear_form)
        buttons_layout.addWidget(self.clear_btn)

        layout.addLayout(buttons_layout)

        # Информационная панель
        info_group = QGroupBox("Информация")
        info_layout = QVBoxLayout()
        self.info_label = QLabel("Выберите материал для просмотра информации")
        info_layout.addWidget(self.info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        self.setLayout(layout)

    def on_type_changed(self, material_type):
        """Обработка изменения типа материала"""
        if material_type == "Пиломатериал":
            self.unit_label.setText("м")
        else:
            self.unit_label.setText("шт")

    def on_table_cell_clicked(self, row, column):
        """Обработка клика по ячейке таблицы"""
        material_id = self.get_selected_item_id(self.table, row)
        if material_id is None:
            return

        try:
            # Получаем данные материала
            material = self.material_service.get_material_by_id(material_id)
            if not material:
                self.show_error("Ошибка", "Материал не найден")
                return

            material_id, name, m_type, price, unit = material

            # Заполняем форму
            self.selected_item_id = material_id
            self.name_input.setText(name)
            self.type_combo.setCurrentText(m_type)
            self.price_input.setText(str(price))
            self.on_type_changed(m_type)

            # Активируем кнопки редактирования
            self.edit_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)

            # Обновляем информационную панель
            self.update_info_panel(material_id)

        except Exception as e:
            self.handle_exception(e, "выборе материала")

    def update_info_panel(self, material_id):
        """Обновление информационной панели"""
        try:
            usage_summary = self.material_service.get_material_usage_summary(material_id)

            info_text = f"<b>Использование материала:</b><br>"

            # Использование в изделиях
            if usage_summary['products']:
                info_text += "<br><b>В изделиях:</b><br>"
                for product_name, quantity, length in usage_summary['products']:
                    if length:
                        info_text += f"• {product_name}: {quantity} x {length}м<br>"
                    else:
                        info_text += f"• {product_name}: {quantity} шт<br>"

            # Использование в этапах
            if usage_summary['stages']:
                info_text += "<br><b>В этапах:</b><br>"
                for stage_name, part, quantity, length in usage_summary['stages']:
                    if length:
                        info_text += f"• {stage_name} ({part}): {quantity} x {length}м<br>"
                    else:
                        info_text += f"• {stage_name} ({part}): {quantity} шт<br>"

            # Остатки на складе
            if usage_summary['warehouse']:
                info_text += "<br><b>На складе:</b><br>"
                total_stock = 0
                for length, quantity in usage_summary['warehouse']:
                    if length > 0:
                        info_text += f"• {length}м: {quantity} шт<br>"
                        total_stock += length * quantity
                    else:
                        info_text += f"• {quantity} шт<br>"
                        total_stock += quantity

                unit = "м" if self.type_combo.currentText() == "Пиломатериал" else "шт"
                info_text += f"<br><b>Всего на складе: {total_stock:.2f} {unit}</b>"

            if not any([usage_summary['products'], usage_summary['stages'], usage_summary['warehouse']]):
                info_text += "<br>Материал не используется"

            self.info_label.setText(info_text)

        except Exception as e:
            self.info_label.setText(f"Ошибка загрузки информации: {str(e)}")

    def load_data(self):
        """Загрузка списка материалов"""
        try:
            materials = self.material_service.get_all_materials()
            self.table.setRowCount(len(materials))

            for row_idx, (material_id, name, m_type, price) in enumerate(materials):
                # Заполняем строку таблицы
                self.populate_table_row(self.table, row_idx, [
                    material_id,
                    name,
                    m_type,
                    self.format_currency(price)
                ], readonly_columns=[0, 1, 2, 3])  # Все колонки только для чтения

        except Exception as e:
            self.handle_exception(e, "загрузке материалов")

    def add_material(self):
        """Добавление нового материала"""
        name = self.validate_text_input(self.name_input.text(), "Название")
        if name is None:
            return

        m_type = self.type_combo.currentText()
        unit = self.unit_label.text()

        price = self.validate_float_input(self.price_input.text(), "Цена", min_value=0.01)
        if price is None:
            return

        try:
            if self.material_service.material_exists(name):
                self.show_warning("Ошибка", "Материал с таким названием уже существует")
                return

            material_id = self.material_service.add_material(name, m_type, price, unit)
            self.load_data()
            self.clear_form()
            self.show_info("Успех", f"Материал '{name}' добавлен с ID {material_id}")
            self.set_status_message(f"Добавлен материал: {name}", 3000)

        except Exception as e:
            self.handle_exception(e, "добавлении материала")

    def edit_material(self):
        """Редактирование выбранного материала"""
        if not self.selected_item_id:
            self.show_warning("Ошибка", "Выберите материал для редактирования")
            return

        name = self.validate_text_input(self.name_input.text(), "Название")
        if name is None:
            return

        m_type = self.type_combo.currentText()
        unit = self.unit_label.text()

        price = self.validate_float_input(self.price_input.text(), "Цена", min_value=0.01)
        if price is None:
            return

        try:
            if self.material_service.material_exists(name, self.selected_item_id):
                self.show_warning("Ошибка", "Материал с таким названием уже существует")
                return

            # Получаем изделия и этапы, использующие этот материал
            affected_products = self.material_service.get_products_using_material(self.selected_item_id)
            affected_stages = self.material_service.get_stages_using_material(self.selected_item_id)

            # Обновляем материал
            self.material_service.update_material(self.selected_item_id, name, m_type, price, unit)

            # Пересчитываем себестоимость затронутых изделий и этапов
            if affected_products:
                self.material_service.recalculate_products_cost(affected_products)
            if affected_stages:
                self.material_service.recalculate_stages_cost(affected_stages)

            self.load_data()
            self.clear_form()
            self.show_info("Успех", f"Материал '{name}' обновлен")
            self.set_status_message(f"Обновлен материал: {name}", 3000)

            # Обновляем связанные вкладки
            self.refresh_related_tabs(['products', 'stages', 'warehouse'])

        except Exception as e:
            self.handle_exception(e, "обновлении материала")

    def delete_material(self):
        """Удаление выбранного материала"""
        if not self.selected_item_id:
            self.show_warning("Ошибка", "Выберите материал для удаления")
            return

        try:
            # Получаем информацию о материале
            material = self.material_service.get_material_by_id(self.selected_item_id)
            if not material:
                self.show_error("Ошибка", "Материал не найден")
                return

            material_name = material[1]

            # Проверяем использование материала
            affected_products = self.material_service.get_products_using_material(self.selected_item_id)
            affected_stages = self.material_service.get_stages_using_material(self.selected_item_id)

            warning_message = f"Вы уверены, что хотите удалить материал '{material_name}'?"
            if affected_products or affected_stages:
                warning_message += f"\n\nЭто повлияет на:"
                if affected_products:
                    warning_message += f"\n• {len(affected_products)} изделий"
                if affected_stages:
                    warning_message += f"\n• {len(affected_stages)} этапов"
                warning_message += f"\n\nСебестоимость будет пересчитана."

            if not self.confirm_action("Подтверждение удаления", warning_message):
                return

            # Удаляем материал
            self.material_service.delete_material(self.selected_item_id)

            # Пересчитываем себестоимость затронутых изделий и этапов
            if affected_products:
                self.material_service.recalculate_products_cost(affected_products)
            if affected_stages:
                self.material_service.recalculate_stages_cost(affected_stages)

            self.load_data()
            self.clear_form()
            self.show_info("Успех", f"Материал '{material_name}' удален")
            self.set_status_message(f"Удален материал: {material_name}", 3000)

            # Обновляем связанные вкладки
            self.refresh_related_tabs(['products', 'stages', 'warehouse'])

        except Exception as e:
            self.handle_exception(e, "удалении материала")

    def clear_form(self):
        """Очистка формы"""
        self.name_input.clear()
        self.price_input.clear()
        self.type_combo.setCurrentIndex(0)
        self.on_type_changed(self.type_combo.currentText())
        self.selected_item_id = None
        self.edit_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.clear_table_selection(self.table)
        self.info_label.setText("Выберите материал для просмотра информации")

    def get_materials_for_combo(self):
        """Получить список материалов для комбобокса (для использования другими вкладками)"""
        try:
            return self.material_service.get_all_materials()
        except Exception as e:
            print(f"Ошибка при получении материалов для комбобокса: {str(e)}")
            return []

    def get_materials_by_type(self, material_type):
        """Получить материалы по типу (для использования другими вкладками)"""
        try:
            return self.material_service.get_materials_by_type(material_type)
        except Exception as e:
            print(f"Ошибка при получении материалов по типу {material_type}: {str(e)}")
            return []