# products_tab.py - Вкладка "Изделия"
"""
Управление изделиями: создание изделий и их состава из материалов.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QTableWidget, QTableWidgetItem,
    QFormLayout, QLineEdit, QPushButton, QLabel, QComboBox, QMessageBox,
    QHBoxLayout
)
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtCore import Qt
from utils import fetch_all, execute
from config import Config


class ProductsTab(QWidget):
    """Вкладка управления изделиями и их составом"""

    def __init__(self, db_path, main_window=None):
        super().__init__()
        self.db_path = db_path
        self.main_window = main_window
        self.selected_product_id = None
        self.init_ui()
        self.load_products()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Группа изделий
        products_group = QGroupBox("Изделия")
        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Название", "Себестоимость"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellClicked.connect(self.on_product_selected)
        layout.addWidget(self.table)

        form = QFormLayout()
        self.name_input = QLineEdit()
        form.addRow("Название изделие:", self.name_input)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Добавить изделие")
        add_btn.clicked.connect(self.add_product)
        btn_layout.addWidget(add_btn)
        del_btn = QPushButton("Удалить изделие")
        del_btn.clicked.connect(self.delete_product)
        btn_layout.addWidget(del_btn)
        calc_btn = QPushButton("Рассчитать себестоимость")
        calc_btn.clicked.connect(self.calculate_product_cost)
        btn_layout.addWidget(calc_btn)
        form.addRow(btn_layout)

        layout.addLayout(form)
        products_group.setLayout(layout)
        main_layout.addWidget(products_group)

        # Вкладка состава
        comp_group = QGroupBox("Состав изделия")
        comp_layout = QVBoxLayout()

        self.comp_table = QTableWidget()
        self.comp_table.setColumnCount(5)
        self.comp_table.setHorizontalHeaderLabels(
            ["ID", "Материал", "Тип", "Количество", "Длина"]
        )
        self.comp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        comp_layout.addWidget(self.comp_table)

        form2 = QFormLayout()
        self.mat_combo = QComboBox()
        form2.addRow("Материал:", self.mat_combo)
        self.qty_input = QLineEdit()
        form2.addRow("Количество:", self.qty_input)
        self.len_input = QLineEdit()
        form2.addRow("Длина:", self.len_input)

        btn2 = QHBoxLayout()
        add2 = QPushButton("Добавить в состав")
        add2.clicked.connect(self.add_to_composition)
        btn2.addWidget(add2)
        rem2 = QPushButton("Удалить из состава")
        rem2.clicked.connect(self.remove_from_composition)
        btn2.addWidget(rem2)
        form2.addRow(btn2)

        comp_layout.addLayout(form2)
        self.cost_label = QLabel("Себестоимость: 0.00 руб")
        comp_layout.addWidget(self.cost_label)
        comp_group.setLayout(comp_layout)
        main_layout.addWidget(comp_group)

        self.setLayout(main_layout)

    def load_products(self):
        """Загружает список изделий"""
        rows = fetch_all("SELECT id, name, cost FROM products ORDER BY name")
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(row['id'])))
            self.table.setItem(i, 1, QTableWidgetItem(row['name']))
            self.table.setItem(i, 2, QTableWidgetItem(f"{row['cost']:.2f}"))

    def on_product_selected(self, row, _col):
        """Обработка выбора изделия"""
        self.selected_product_id = int(self.table.item(row, 0).text())
        self.name_input.setText(self.table.item(row, 1).text())
        self.load_materials()
        self.load_composition()

    def load_materials(self):
        """Загружает список материалов"""
        rows = fetch_all("SELECT id, name FROM materials ORDER BY name")
        self.mat_combo.clear()
        for row in rows:
            self.mat_combo.addItem(row['name'], row['id'])

    def load_composition(self):
        """Загружает состав выбранного изделия"""
        rows = fetch_all(
            "SELECT pc.id, m.name, m.type, pc.quantity, pc.length "
            "FROM product_composition pc "
            "JOIN materials m ON pc.material_id=m.id "
            "WHERE pc.product_id=?", [self.selected_product_id]
        )
        self.comp_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.comp_table.setItem(i, 0, QTableWidgetItem(str(row['id'])))
            self.comp_table.setItem(i, 1, QTableWidgetItem(row['name']))
            self.comp_table.setItem(i, 2, QTableWidgetItem(row['type']))
            self.comp_table.setItem(i, 3, QTableWidgetItem(str(row['quantity'])))
            self.comp_table.setItem(i, 4, QTableWidgetItem(str(row['length'] or "")))

    def add_product(self):
        """Добавление нового изделия"""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название изделия")
            return
        execute("INSERT INTO products(name) VALUES(?)", [name])
        self.load_products()

    def delete_product(self):
        """Удаление изделия"""
        if not self.selected_product_id:
            return
        execute("DELETE FROM product_composition WHERE product_id=?", [self.selected_product_id])
        execute("DELETE FROM products WHERE id=?", [self.selected_product_id])
        self.load_products()

    def calculate_product_cost(self):
        """Рассчитывает себестоимость изделия"""
        rows = fetch_all(
            "SELECT m.price, pc.quantity, pc.length "
            "FROM product_composition pc "
            "JOIN materials m ON pc.material_id=m.id "
            "WHERE pc.product_id=?", [self.selected_product_id]
        )
        total = 0.0
        for r in rows:
            if r['length']:
                total += r['price'] * r['quantity'] * r['length']
            else:
                total += r['price'] * r['quantity']
        execute("UPDATE products SET cost=? WHERE id=?", [total, self.selected_product_id])
        self.cost_label.setText(f"Себестоимость: {total:.2f} руб")
        if self.main_window:
            self.main_window.reload_all_tabs()

    def add_to_composition(self):
        """Добавление материала в состав"""
        mat_id = self.mat_combo.currentData()
        qty_text = self.qty_input.text().strip()
        len_text = self.len_input.text().strip()
        try:
            qty = int(qty_text)
            length = float(len_text) if len_text else None
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Неверный ввод количества или длины")
            return
        execute(
            "INSERT INTO product_composition(product_id,material_id,quantity,length) VALUES(?,?,?,?)",
            [self.selected_product_id, mat_id, qty, length]
        )
        self.load_composition()
        self.calculate_product_cost()

    def remove_from_composition(self):
        """Удаление материала из состава"""
        row = self.comp_table.currentRow()
        if row < 0:
            return
        comp_id = int(self.comp_table.item(row, 0).text())
        execute("DELETE FROM product_composition WHERE id=?", [comp_id])
        self.load_composition()
        self.calculate_product_cost()