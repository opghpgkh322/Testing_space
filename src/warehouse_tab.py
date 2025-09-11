# warehouse_tab.py - Вкладка "Склад"
"""
Класс для управления складом: добавление и удаление остатков, Git-интеграция.
"""

import os
import subprocess
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QFormLayout, QComboBox,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHBoxLayout, QMessageBox
)
from PyQt5.QtCore import Qt
from utils import fetch_all, execute
from config import Config, DatabaseConfig, GitConfig


class WarehouseTab(QWidget):
    """Вкладка управления складом"""

    def __init__(self, db_path, main_window):
        super().__init__()
        self.db_path = db_path
        self.main_window = main_window
        self.repo_root = GitConfig.find_git_root(db_path)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout()

        # Группа добавления на склад
        add_group = QGroupBox("Добавить на склад")
        form = QFormLayout()
        self.material_combo = QComboBox()
        form.addRow("Материал:", self.material_combo)

        self.length_input = QLineEdit()
        form.addRow("Длина:", self.length_input)

        self.quantity_input = QLineEdit()
        form.addRow("Количество:", self.quantity_input)

        add_btn = QPushButton("Добавить на склад")
        add_btn.clicked.connect(self.add_to_warehouse)
        form.addRow(add_btn)
        add_group.setLayout(form)
        layout.addWidget(add_group)

        # Таблица склада
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Материал", "Длина", "Количество"])
        self.table.horizontalHeader().setSectionResizeMode(Qt.Horizontal)
        layout.addWidget(self.table)

        # Кнопки удаления и Git
        btn_layout = QHBoxLayout()
        del_btn = QPushButton("Удалить выбранное")
        del_btn.clicked.connect(self.delete_item)
        btn_layout.addWidget(del_btn)

        pull_btn = QPushButton("Git pull")
        pull_btn.clicked.connect(self.git_pull)
        push_btn = QPushButton("Git push")
        push_btn.clicked.connect(self.git_push)
        if not self.repo_root:
            pull_btn.setEnabled(False)
            push_btn.setEnabled(False)
        btn_layout.addWidget(pull_btn)
        btn_layout.addWidget(push_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def load_materials(self):
        """Загружает список материалов"""
        rows = fetch_all("SELECT id, name FROM materials ORDER BY name")
        self.material_combo.clear()
        for row in rows:
            self.material_combo.addItem(row['name'], row['id'])

    def load_data(self):
        """Загружает данные склада"""
        rows = fetch_all(
            "SELECT w.id, m.name, w.length, w.quantity "
            "FROM warehouse w JOIN materials m ON w.material_id=m.id "
            "ORDER BY m.name"
        )
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(row['id'])))
            self.table.setItem(i, 1, QTableWidgetItem(row['name']))
            self.table.setItem(i, 2, QTableWidgetItem(str(row['length'])))
            self.table.setItem(i, 3, QTableWidgetItem(str(row['quantity'])))

    def add_to_warehouse(self):
        """Добавляет материал на склад"""
        material_id = self.material_combo.currentData()
        length = self.length_input.text().strip()
        quantity = self.quantity_input.text().strip()
        try:
            length_val = float(length)
            quantity_val = int(quantity)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Длина или количество некорректны")
            return
        try:
            # Проверка существующего остатка
            row = fetch_all(
                "SELECT id FROM warehouse WHERE material_id=? AND length=?",
                [material_id, length_val]
            )
            if row:
                execute(
                    "UPDATE warehouse SET quantity=quantity+? WHERE id=?",
                    [quantity_val, row[0]['id']]
                )
            else:
                execute(
                    "INSERT INTO warehouse(material_id,length,quantity) VALUES(?,?,?)",
                    [material_id, length_val, quantity_val]
                )
            QMessageBox.information(self, "Успех", "Склад обновлен")
            self.length_input.clear()
            self.quantity_input.clear()
            self.load_data()
            self.main_window.reload_all_tabs()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def delete_item(self):
        """Удаляет выбранную запись"""
        row = self.table.currentRow()
        if row < 0:
            return
        item_id = int(self.table.item(row, 0).text())
        execute("DELETE FROM warehouse WHERE id=?", [item_id])
        self.load_data()

    def git_pull(self):
        """Выполняет git pull для data/database.db"""
        try:
            # fetch + checkout
            subprocess.run(['git','fetch'], cwd=self.repo_root, timeout=GitConfig.GIT_TIMEOUT)
            subprocess.run(
                ['git','checkout','origin/master','--',GitConfig.DB_REPO_PATH],
                cwd=self.repo_root, timeout=GitConfig.GIT_TIMEOUT
            )
            # копирование
            src = os.path.join(self.repo_root, GitConfig.DB_REPO_PATH)
            dst = self.db_path
            if os.path.exists(src):
                import shutil; shutil.copy2(src, dst)
            QMessageBox.information(self, "Успех", "Склад синхронизирован")
            self.main_window.reload_all_tabs()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка Git", str(e))

    def git_push(self):
        """Выполняет git push для data/database.db"""
        try:
            dst_repo = os.path.join(self.repo_root, GitConfig.DB_REPO_PATH)
            import shutil; shutil.copy2(self.db_path, dst_repo)
            subprocess.run(['git','add',GitConfig.DB_REPO_PATH], cwd=self.repo_root,
                           timeout=GitConfig.GIT_TIMEOUT)
            subprocess.run(['git','commit','-m','Update database','--',GitConfig.DB_REPO_PATH],
                           cwd=self.repo_root, timeout=GitConfig.GIT_TIMEOUT)
            subprocess.run(['git','push','origin','master','--force'], cwd=self.repo_root,
                           timeout=GitConfig.GIT_TIMEOUT)
            QMessageBox.information(self, "Успех", "Склад отправлен в репозиторий")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка Git", str(e))