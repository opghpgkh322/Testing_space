# stages_tab.py - Вкладка "Этапы"
"""
Управление этапами работ: CRUD, состав (изделия и материалы), расчет себестоимости по частям.
"""

import math
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QGroupBox, QTableWidget,
    QTableWidgetItem, QFormLayout, QLineEdit, QTextEdit, QPushButton,
    QComboBox, QSpinBox, QDoubleSpinBox, QLabel, QMessageBox,
    QHBoxLayout, QTabWidget, QHeaderView
)
from PyQt5.QtCore import Qt
from utils import fetch_all, execute
from config import Config


class StagesTab(QWidget):
    """Вкладка управления этапами и их составом"""

    def __init__(self, db_path, main_window=None):
        super().__init__()
        self.db_path = db_path
        self.main_window = main_window
        self.selected_stage_id = None
        self.init_ui()
        self.load_stages()

    def init_ui(self):
        layout = QVBoxLayout()
        splitter = QSplitter(Qt.Horizontal)

        # Список этапов
        left = QWidget()
        left_layout = QVBoxLayout()
        self.stages_table = QTableWidget()
        self.stages_table.setColumnCount(4)
        self.stages_table.setHorizontalHeaderLabels(["ID","Название","Себестоимость","Описание"])
        self.stages_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stages_table.cellClicked.connect(self.on_stage_selected)
        left_layout.addWidget(self.stages_table)

        form = QFormLayout()
        self.name_input = QLineEdit()
        form.addRow("Название:", self.name_input)
        self.desc_input = QTextEdit()
        form.addRow("Описание:", self.desc_input)

        btns = QHBoxLayout()
        add = QPushButton("Добавить этап")
        add.clicked.connect(self.add_stage)
        btns.addWidget(add)
        rem = QPushButton("Удалить этап")
        rem.clicked.connect(self.delete_stage)
        btns.addWidget(rem)
        cost = QPushButton("Рассчитать себестоимость")
        cost.clicked.connect(self.calculate_stage_cost)
        btns.addWidget(cost)
        form.addRow(btns)

        left_layout.addLayout(form)
        left.setLayout(left_layout)
        splitter.addWidget(left)

        # Состав этапа
        right_group = QGroupBox("Состав этапа")
        right_group.setEnabled(False)
        comp_layout = QVBoxLayout()
        tabs = QTabWidget()

        # Вкладка изделий
        prod_tab = QWidget()
        pl = QVBoxLayout()
        self.prod_table = QTableWidget()
        self.prod_table.setColumnCount(5)
        self.prod_table.setHorizontalHeaderLabels(["ID","Изделие","Часть","Кол-во","Стоимость"])
        self.prod_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        pl.addWidget(self.prod_table)
        pfl = QFormLayout()
        self.prod_combo = QComboBox()
        pfl.addRow("Изделие:", self.prod_combo)
        self.part_combo = QComboBox()
        self.part_combo.addItems(Config.STAGE_PARTS)
        pfl.addRow("Часть:", self.part_combo)
        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, Config.MAX_QUANTITY)
        pfl.addRow("Кол-во:", self.qty_spin)
        pb = QHBoxLayout()
        padd = QPushButton("Добавить")
        padd.clicked.connect(self.add_prod_to_stage)
        pb.addWidget(padd)
        prem = QPushButton("Удалить")
        prem.clicked.connect(self.remove_prod_from_stage)
        pb.addWidget(prem)
        pfl.addRow(pb)
        pl.addLayout(pfl)
        prod_tab.setLayout(pl)
        tabs.addTab(prod_tab, "Изделия")

        # Вкладка материалов
        mat_tab = QWidget()
        ml = QVBoxLayout()
        self.mat_table = QTableWidget()
        self.mat_table.setColumnCount(7)
        self.mat_table.setHorizontalHeaderLabels(["ID","Материал","Тип","Часть","Кол-во","Длина","Стоимость"])
        self.mat_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        ml.addWidget(self.mat_table)
        mfl = QFormLayout()
        self.mat_combo = QComboBox()
        mfl.addRow("Материал:", self.mat_combo)
        self.mpart_combo = QComboBox()
        self.mpart_combo.addItems(Config.STAGE_PARTS)
        mfl.addRow("Часть:", self.mpart_combo)
        self.mqty_spin = QSpinBox()
        self.mqty_spin.setRange(1, Config.MAX_QUANTITY)
        mfl.addRow("Кол-во:", self.mqty_spin)
        self.length_input = QLineEdit()
        mfl.addRow("Длина:", self.length_input)
        mb = QHBoxLayout()
        madd = QPushButton("Добавить")
        madd.clicked.connect(self.add_mat_to_stage)
        mb.addWidget(madd)
        mrem = QPushButton("Удалить")
        mrem.clicked.connect(self.remove_mat_from_stage)
        mb.addWidget(mrem)
        mfl.addRow(mb)
        ml.addLayout(mfl)
        mat_tab.setLayout(ml)
        tabs.addTab(mat_tab, "Материалы")

        comp_layout.addWidget(tabs)
        self.cost_label = QLabel("Себестоимость этапа: 0.00 руб")
        comp_layout.addWidget(self.cost_label)
        right_group.setLayout(comp_layout)
        splitter.addWidget(right_group)

        layout.addWidget(splitter)
        self.setLayout(layout)

    # stages_tab.py - Недостающие методы
    """
    Недостающие методы для StagesTab класса. Вставить вместо комментария.
    """

    def load_stages(self):
        """Загружает список этапов"""
        rows = fetch_all("SELECT id, name, cost, description FROM stages ORDER BY name")
        self.stages_table.setRowCount(len(rows))

        for i, row in enumerate(rows):
            self.stages_table.setItem(i, 0, QTableWidgetItem(str(row['id'])))
            self.stages_table.setItem(i, 1, QTableWidgetItem(row['name']))
            self.stages_table.setItem(i, 2, QTableWidgetItem(f"{row['cost']:.2f} руб"))
            self.stages_table.setItem(i, 3, QTableWidgetItem(row['description'] or ""))

    def on_stage_selected(self, row, _col):
        """Обработка выбора этапа"""
        try:
            if row < 0 or row >= self.stages_table.rowCount():
                return

            self.selected_stage_id = int(self.stages_table.item(row, 0).text())
            stage_name = self.stages_table.item(row, 1).text()

            # Заполняем форму
            self.name_input.setText(stage_name)
            desc_item = self.stages_table.item(row, 3)
            self.desc_input.setPlainText(desc_item.text() if desc_item else "")

            # Активируем правую панель
            right_group = self.findChild(QGroupBox, "composition_group")
            if right_group:
                right_group.setEnabled(True)
                right_group.setTitle(f"Состав этапа: {stage_name}")

            self.load_products()
            self.load_materials()
            self.load_stage_products()
            self.load_stage_materials()
            self.calculate_stage_cost()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка выбора", str(e))

    def load_products(self):
        """Загружает список изделий для комбобокса"""
        rows = fetch_all("SELECT id, name FROM products ORDER BY name")
        self.prod_combo.clear()
        for row in rows:
            self.prod_combo.addItem(row['name'], row['id'])

    def load_materials(self):
        """Загружает список материалов для комбобокса"""
        rows = fetch_all("SELECT id, name, type FROM materials ORDER BY name")
        self.mat_combo.clear()
        for row in rows:
            self.mat_combo.addItem(f"{row['name']} ({row['type']})", row['id'])

    def load_stage_products(self):
        """Загружает изделия в составе этапа"""
        if not self.selected_stage_id:
            return

        rows = fetch_all(
            "SELECT sp.id, p.name, sp.part, sp.quantity, (p.cost * sp.quantity) as total_cost "
            "FROM stage_products sp "
            "JOIN products p ON sp.product_id = p.id "
            "WHERE sp.stage_id = ?", [self.selected_stage_id]
        )

        self.prod_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.prod_table.setItem(i, 0, QTableWidgetItem(str(row['id'])))
            self.prod_table.setItem(i, 1, QTableWidgetItem(row['name']))
            self.prod_table.setItem(i, 2, QTableWidgetItem(row['part']))
            self.prod_table.setItem(i, 3, QTableWidgetItem(str(row['quantity'])))
            self.prod_table.setItem(i, 4, QTableWidgetItem(f"{row['total_cost']:.2f} руб"))

    def load_stage_materials(self):
        """Загружает материалы в составе этапа"""
        if not self.selected_stage_id:
            return

        rows = fetch_all(
            "SELECT sm.id, m.name, m.type, sm.part, sm.quantity, sm.length, "
            "CASE "
            "  WHEN m.type = 'Пиломатериал' AND sm.length IS NOT NULL "
            "  THEN (m.price * sm.quantity * sm.length) "
            "  ELSE (m.price * sm.quantity) "
            "END as total_cost "
            "FROM stage_materials sm "
            "JOIN materials m ON sm.material_id = m.id "
            "WHERE sm.stage_id = ?", [self.selected_stage_id]
        )

        self.mat_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.mat_table.setItem(i, 0, QTableWidgetItem(str(row['id'])))
            self.mat_table.setItem(i, 1, QTableWidgetItem(row['name']))
            self.mat_table.setItem(i, 2, QTableWidgetItem(row['type']))
            self.mat_table.setItem(i, 3, QTableWidgetItem(row['part']))
            self.mat_table.setItem(i, 4, QTableWidgetItem(str(row['quantity'])))
            self.mat_table.setItem(i, 5, QTableWidgetItem(str(row['length'] or "")))
            self.mat_table.setItem(i, 6, QTableWidgetItem(f"{row['total_cost']:.2f} руб"))

    def add_stage(self):
        """Добавляет новый этап"""
        name = self.name_input.text().strip()
        description = self.desc_input.toPlainText().strip()

        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название этапа")
            return

        try:
            execute("INSERT INTO stages (name, description) VALUES (?, ?)", [name, description])
            self.load_stages()
            self.name_input.clear()
            self.desc_input.clear()
            QMessageBox.information(self, "Успех", "Этап добавлен!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def delete_stage(self):
        """Удаляет выбранный этап"""
        if not self.selected_stage_id:
            QMessageBox.warning(self, "Ошибка", "Выберите этап для удаления")
            return

        # Получаем название этапа для подтверждения
        rows = fetch_all("SELECT name FROM stages WHERE id = ?", [self.selected_stage_id])
        if not rows:
            return

        stage_name = rows[0]['name']
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Вы уверены, что хотите удалить этап '{stage_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                execute("DELETE FROM stage_products WHERE stage_id = ?", [self.selected_stage_id])
                execute("DELETE FROM stage_materials WHERE stage_id = ?", [self.selected_stage_id])
                execute("DELETE FROM stages WHERE id = ?", [self.selected_stage_id])

                self.load_stages()
                self.selected_stage_id = None
                QMessageBox.information(self, "Успех", "Этап удален")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def calculate_stage_cost(self):
        """Рассчитывает себестоимость этапа"""
        if not self.selected_stage_id:
            return

        try:
            start_cost = meter_cost = end_cost = 0.0

            # Стоимость изделий по частям
            rows = fetch_all(
                "SELECT sp.part, p.cost, sp.quantity "
                "FROM stage_products sp "
                "JOIN products p ON sp.product_id = p.id "
                "WHERE sp.stage_id = ?", [self.selected_stage_id]
            )

            for row in rows:
                cost_add = row['cost'] * row['quantity']
                if row['part'] == 'start':
                    start_cost += cost_add
                elif row['part'] == 'meter':
                    meter_cost += cost_add
                else:
                    end_cost += cost_add

            # Стоимость материалов по частям
            rows = fetch_all(
                "SELECT sm.part, m.type, m.price, sm.quantity, sm.length "
                "FROM stage_materials sm "
                "JOIN materials m ON sm.material_id = m.id "
                "WHERE sm.stage_id = ?", [self.selected_stage_id]
            )

            for row in rows:
                if row['type'] == Config.MATERIAL_TYPES[0] and row['length']:  # Пиломатериал
                    cost_add = row['price'] * row['quantity'] * row['length']
                else:
                    cost_add = row['price'] * row['quantity']

                if row['part'] == 'start':
                    start_cost += cost_add
                elif row['part'] == 'meter':
                    meter_cost += cost_add
                else:
                    end_cost += cost_add

            # Обновляем отображение
            one_meter_total = start_cost + meter_cost + end_cost
            self.cost_label.setText(
                f"Себестоимость этапа (1 м): {one_meter_total:.2f} руб | "
                f"Метр: {meter_cost:.2f} руб | Крепления: {(start_cost + end_cost):.2f} руб"
            )

            # Сохраняем стоимость "метровой" части для совместимости
            execute("UPDATE stages SET cost = ? WHERE id = ?", [meter_cost, self.selected_stage_id])

            self.load_stages()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка расчета", str(e))

    def add_prod_to_stage(self):
        """Добавляет изделие в состав этапа"""
        if not self.selected_stage_id:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите этап")
            return

        product_id = self.prod_combo.currentData()
        part = self.part_combo.currentText()
        quantity = self.qty_spin.value()

        if not product_id:
            QMessageBox.warning(self, "Ошибка", "Выберите изделие")
            return

        try:
            execute(
                "INSERT INTO stage_products (stage_id, product_id, quantity, part) VALUES (?, ?, ?, ?)",
                [self.selected_stage_id, product_id, quantity, part]
            )
            self.load_stage_products()
            self.calculate_stage_cost()
            QMessageBox.information(self, "Успех", "Изделие добавлено в этап")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def remove_prod_from_stage(self):
        """Удаляет изделие из состава этапа"""
        row = self.prod_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите изделие для удаления")
            return

        sp_id = int(self.prod_table.item(row, 0).text())
        product_name = self.prod_table.item(row, 1).text()

        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить изделие '{product_name}' из этапа?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            execute("DELETE FROM stage_products WHERE id = ?", [sp_id])
            self.load_stage_products()
            self.calculate_stage_cost()
            QMessageBox.information(self, "Успех", "Изделие удалено из этапа")

    def add_mat_to_stage(self):
        """Добавляет материал в состав этапа"""
        if not self.selected_stage_id:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите этап")
            return

        material_id = self.mat_combo.currentData()
        part = self.mpart_combo.currentText()
        quantity = self.mqty_spin.value()
        length_text = self.length_input.text().strip()

        if not material_id:
            QMessageBox.warning(self, "Ошибка", "Выберите материал")
            return

        try:
            length_val = float(length_text) if length_text else None
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Длина должна быть числом")
            return

        try:
            execute(
                "INSERT INTO stage_materials (stage_id, material_id, quantity, length, part) VALUES (?, ?, ?, ?, ?)",
                [self.selected_stage_id, material_id, quantity, length_val, part]
            )
            self.load_stage_materials()
            self.calculate_stage_cost()
            QMessageBox.information(self, "Успех", "Материал добавлен в этап")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def remove_mat_from_stage(self):
        """Удаляет материал из состава этапа"""
        row = self.mat_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите материал для удаления")
            return

        sm_id = int(self.mat_table.item(row, 0).text())
        material_name = self.mat_table.item(row, 1).text()

        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить материал '{material_name}' из этапа?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            execute("DELETE FROM stage_materials WHERE id = ?", [sm_id])
            self.load_stage_materials()
            self.calculate_stage_cost()
            QMessageBox.information(self, "Успех", "Материал удален из этапа")
