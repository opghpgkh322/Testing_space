# materials_tab.py - Вкладка "Материалы"
"""
Класс для управления материалами: добавление, редактирование, удаление.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QFormLayout, QLineEdit, QComboBox, QLabel, QPushButton,
    QMessageBox, QHBoxLayout
)
from PyQt5.QtCore import Qt
from utils import fetch_all, execute
from config import Config


class MaterialsTab(QWidget):
    """Вкладка управления материалами"""

    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self.selected_material_id = None
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout()

        # Таблица материалов
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Название", "Тип", "Цена"])
        self.table.horizontalHeader().setSectionResizeMode(Qt.Horizontal)
        self.table.cellClicked.connect(self.on_table_cell_clicked)
        layout.addWidget(self.table)

        # Форма для введения данных
        form_layout = QFormLayout()
        self.name_input = QLineEdit()
        form_layout.addRow(QLabel("Название:"), self.name_input)

        self.type_combo = QComboBox()
        self.type_combo.addItems(Config.MATERIAL_TYPES)
        form_layout.addRow(QLabel("Тип:"), self.type_combo)

        self.price_input = QLineEdit()
        form_layout.addRow(QLabel("Цена:"), self.price_input)

        layout.addLayout(form_layout)

        # Кнопки действий
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

    def load_data(self):
        """Загружает данные материалов из БД"""
        rows = fetch_all("SELECT id, name, type, price FROM materials ORDER BY name")
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(row['id'])))
            self.table.setItem(i, 1, QTableWidgetItem(row['name']))
            self.table.setItem(i, 2, QTableWidgetItem(row['type']))
            self.table.setItem(i, 3, QTableWidgetItem(f"{row['price']:.2f}"))

    def on_table_cell_clicked(self, row, _col):
        """Заполнение формы при выборе строки"""
        item = self.table.item(row, 0)
        if not item:
            return
        self.selected_material_id = int(item.text())
        self.name_input.setText(self.table.item(row, 1).text())
        self.type_combo.setCurrentText(self.table.item(row, 2).text())
        self.price_input.setText(self.table.item(row, 3).text())

    def add_material(self):
        """Добавляет новый материал"""
        name = self.name_input.text().strip()
        mtype = self.type_combo.currentText()
        price_text = self.price_input.text().strip()
        try:
            price = float(price_text)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Цена должна быть числом")
            return

        try:
            execute(
                "INSERT INTO materials (name, type, price, unit) VALUES (?, ?, ?, ?)",
                [name, mtype, price, Config.LUMBER_UNIT if mtype == Config.MATERIAL_TYPES[0] else Config.FASTENER_UNIT]
            )
            QMessageBox.information(self, "Успех", "Материал добавлен")
            self.load_data()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def edit_material(self):
        """Редактирует выбранный материал"""
        if not self.selected_material_id:
            QMessageBox.warning(self, "Ошибка", "Выберите материал")
            return
        name = self.name_input.text().strip()
        mtype = self.type_combo.currentText()
        price_text = self.price_input.text().strip()
        try:
            price = float(price_text)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Цена должна быть числом")
            return

        try:
            execute(
                "UPDATE materials SET name=?, type=?, price=?, unit=? WHERE id=?",
                [name, mtype, price,
                 Config.LUMBER_UNIT if mtype == Config.MATERIAL_TYPES[0] else Config.FASTENER_UNIT,
                 self.selected_material_id]
            )
            QMessageBox.information(self, "Успех", "Материал обновлен")
            self.load_data()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def delete_material(self):
        """Удаляет выбранный материал"""
        if not self.selected_material_id:
            QMessageBox.warning(self, "Ошибка", "Выберите материал")
            return
        try:
            execute("DELETE FROM materials WHERE id=?", [self.selected_material_id])
            QMessageBox.information(self, "Успех", "Материал удален")
            self.load_data()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))