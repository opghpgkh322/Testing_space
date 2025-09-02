# src/gui.py
import sys
import os
import subprocess
import sqlite3
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
                             QHBoxLayout, QFormLayout, QGroupBox, QSpinBox, QTextEdit, QDialog)
from PyQt5.QtCore import Qt

try:
    if getattr(sys, 'frozen', False):
        # Если приложение запущено как собранный exe
        font_path = os.path.join(os.path.dirname(sys.executable), 'fonts', 'arial.ttf')
    else:
        # Если приложение запущено из исходного кода
        font_path = os.path.join(os.path.dirname(__file__), 'fonts', 'arial.ttf')

    pdfmetrics.registerFont(TTFont('Arial', font_path))
except:
    print("Шрифт Arial не найден, используется стандартный")

class MaterialsTab(QWidget):
    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout()

        # Таблица материалов
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Название", "Тип", "Цена", "Ед. изм."])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        # Форма добавления/редактирования материала
        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Брус 100x100")
        form_layout.addRow(QLabel("Название:"), self.name_input)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Пиломатериал", "Метиз"])
        form_layout.addRow(QLabel("Тип:"), self.type_combo)

        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("5.00")
        form_layout.addRow(QLabel("Цена:"), self.price_input)

        self.unit_input = QLineEdit()
        self.unit_input.setPlaceholderText("м или шт")
        form_layout.addRow(QLabel("Ед. изм:"), self.unit_input)

        layout.addLayout(form_layout)

        # Кнопки
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

        # Подключаем обработчик выбора строки в таблице
        self.table.cellClicked.connect(self.on_table_cell_clicked)

    def on_table_cell_clicked(self, row, column):
        """Заполняет форму данными выбранного материала"""
        if row >= 0:
            material_id = self.table.item(row, 0).text()
            name = self.table.item(row, 1).text()
            m_type = self.table.item(row, 2).text()
            price = self.table.item(row, 3).text()
            unit = self.table.item(row, 4).text()

            # Сохраняем ID выбранного материала
            self.selected_material_id = material_id

            # Заполняем форму
            self.name_input.setText(name)
            self.type_combo.setCurrentText(m_type)
            self.price_input.setText(price)
            self.unit_input.setText(unit)

    def edit_material(self):
        """Редактирует выбранный материал"""
        if not hasattr(self, 'selected_material_id'):
            QMessageBox.warning(self, "Ошибка", "Выберите материал для редактирования")
            return

        name = self.name_input.text().strip()
        m_type = self.type_combo.currentText()
        price = self.price_input.text().strip()
        unit = self.unit_input.text().strip()

        if not name or not price or not unit:
            QMessageBox.warning(self, "Ошибка", "Все поля обязательны для заполнения")
            return

        try:
            price_val = float(price)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Цена должна быть числом")
            return

        # Проверяем, не используется ли это название другим материалом
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM materials WHERE name = ? AND id != ?",
            (name, self.selected_material_id)
        )
        existing = cursor.fetchone()

        if existing:
            QMessageBox.warning(self, "Ошибка", "Материал с таким названием уже существует")
            conn.close()
            return

        # Обновляем материал в базе данных
        try:
            cursor.execute(
                "UPDATE materials SET name = ?, type = ?, price = ?, unit = ? WHERE id = ?",
                (name, m_type, price_val, unit, self.selected_material_id)
            )
            conn.commit()

            # Пересчитываем себестоимость всех изделий, использующих этот материал
            self.recalculate_products_with_material(self.selected_material_id)

            conn.close()

            self.load_data()  # Перезагружаем таблицу
            self.clear_form()  # Очищаем форму

            QMessageBox.information(self, "Успех", "Материал обновлен!")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка базы данных", f"Ошибка при обновлении материала: {str(e)}")
        finally:
            conn.close()

    def recalculate_products_with_material(self, material_id):
        """Пересчитывает себестоимость изделий, использующих указанный материал"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            # Находим все изделия, которые используют этот материал
            cursor.execute('''
                SELECT DISTINCT product_id 
                FROM product_composition 
                WHERE material_id = ?
            ''', (material_id,))
            product_ids = [row[0] for row in cursor.fetchall()]

            # Для каждого изделия пересчитываем себестоимость
            for product_id in product_ids:
                cursor.execute('''
                    SELECT m.price, pc.quantity, pc.length
                    FROM product_composition pc
                    JOIN materials m ON pc.material_id = m.id
                    WHERE pc.product_id = ?
                ''', (product_id,))
                composition = cursor.fetchall()

                total_cost = 0
                for row in composition:
                    price, quantity, length = row
                    if length:  # Для пиломатериалов
                        total_cost += price * quantity * length
                    else:  # Для метизов
                        total_cost += price * quantity

                # Обновляем себестоимость изделия
                cursor.execute("UPDATE products SET cost = ? WHERE id = ?",
                               (total_cost, product_id))

            conn.commit()
        except Exception as e:
            print(f"Ошибка при пересчете себестоимости: {str(e)}")
            conn.rollback()
        finally:
            conn.close()

    def clear_form(self):
        """Очищает форму ввода"""
        self.name_input.clear()
        self.price_input.clear()
        self.unit_input.clear()
        if hasattr(self, 'selected_material_id'):
            delattr(self, 'selected_material_id')

    def load_data(self):
        """Загружает данные материалов"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, type, price, unit FROM materials ORDER BY name')
        materials = cursor.fetchall()
        conn.close()

        self.table.setRowCount(len(materials))
        for row_idx, row_data in enumerate(materials):
            for col_idx, col_data in enumerate(row_data):
                if col_idx == 3:  # Для price
                    item = QTableWidgetItem(f"{float(col_data):.2f}")
                else:
                    item = QTableWidgetItem(str(col_data))
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.table.setItem(row_idx, col_idx, item)

    def add_material(self):
        name = self.name_input.text().strip()
        m_type = self.type_combo.currentText()
        price = self.price_input.text().strip()
        unit = self.unit_input.text().strip()

        if not name or not price or not unit:
            QMessageBox.warning(self, "Ошибка", "Все поля обязательны для заполнения")
            return

        try:
            price_val = float(price)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Цена должна быть числом")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO materials (name, type, price, unit) VALUES (?, ?, ?, ?)",
                (name, m_type, price_val, unit)
            )
            conn.commit()
            conn.close()

            # Обновляем все выпадающие списки в главном окне
            if hasattr(self, 'main_window_ref'):
                self.main_window_ref.update_all_comboboxes()

            self.load_data()  # Перезагружаем таблицу
            self.name_input.clear()
            self.price_input.clear()
            self.unit_input.clear()
            QMessageBox.information(self, "Успех", "Материал добавлен!")
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Ошибка", "Материал с таким названием уже существует")

    def delete_material(self):
        selected_row = self.table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите материал для удаления")
            return

        material_id = int(self.table.item(selected_row, 0).text())

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Вы уверены, что хотите удалить этот материал?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM materials WHERE id = ?", (material_id,))
            conn.commit()
            conn.close()
            self.load_data()
            QMessageBox.information(self, "Успех", "Материал удален")


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

        # Группа для добавления на склад
        add_group = QGroupBox("Добавить на склад")
        add_layout = QFormLayout()

        # Выбор материала
        self.material_combo = QComboBox()
        self.load_materials()
        add_layout.addRow(QLabel("Материал:"), self.material_combo)

        # Длина
        self.length_input = QLineEdit()
        self.length_input.setPlaceholderText("0 для метизов, иначе длина в метрах")
        add_layout.addRow(QLabel("Длина:"), self.length_input)

        # Количество
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

        # Кнопки управления
        btn_layout = QHBoxLayout()

        self.delete_btn = QPushButton("Удалить выбранное")
        self.delete_btn.clicked.connect(self.delete_item)
        btn_layout.addWidget(self.delete_btn)

        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

        # Кнопки Git
        git_btn_layout = QHBoxLayout()

        self.git_pull_btn = QPushButton("Git pull database.db")
        self.git_pull_btn.clicked.connect(self.git_pull)
        git_btn_layout.addWidget(self.git_pull_btn)

        self.git_push_btn = QPushButton("Git push database.db")
        self.git_push_btn.clicked.connect(self.git_push)
        git_btn_layout.addWidget(self.git_push_btn)

        main_layout.addLayout(git_btn_layout)

        # Если репозиторий не найден, отключаем кнопки
        if self.repo_root is None:
            self.git_pull_btn.setEnabled(False)
            self.git_push_btn.setEnabled(False)
            self.git_pull_btn.setToolTip("Git репозиторий не найден")
            self.git_push_btn.setToolTip("Git репозиторий не найден")

        self.setLayout(main_layout)

    def git_pull(self):
        if self.repo_root is None:
            QMessageBox.critical(self, "Ошибка", "Git репозиторий не найден")
            return

        # Предупреждение о возможной потере локальных изменений
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Принудительный git pull может перезаписать локальные изменения. Продолжить?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.No:
            return

        try:
            # Выполняем git fetch
            result = subprocess.run(['git', 'fetch', 'origin'],
                                    cwd=self.repo_root,
                                    capture_output=True,
                                    text=True,
                                    timeout=30)

            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                QMessageBox.critical(self, "Ошибка", f"Ошибка при получении изменений:\n{error_msg}")
                return

            # Всегда используем фиксированный путь к базе данных в репозитории
            db_repo_path = 'data/database.db'

            # Принудительно сбрасываем файл database.db к версии из удаленного репозитория
            reset_result = subprocess.run(['git', 'checkout', 'origin/master', '--', db_repo_path],
                                          cwd=self.repo_root,
                                          capture_output=True,
                                          text=True,
                                          timeout=30)

            if reset_result.returncode == 0:
                # Копируем обновленный файл из репозитория в папку приложения
                repo_db_path = os.path.join(self.repo_root, db_repo_path)
                if os.path.exists(repo_db_path):
                    import shutil
                    shutil.copy2(repo_db_path, self.db_path)
                    QMessageBox.information(self, "Успех", "Склад заполнился актуальными остатками")
                    # Перезагружаем все вкладки
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
            # Всегда используем фиксированный путь к базе данных в репозитории
            db_repo_path = 'data/database.db'

            # Копируем текущую базу данных в репозиторий
            repo_db_path = os.path.join(self.repo_root, db_repo_path)
            repo_db_dir = os.path.dirname(repo_db_path)

            if not os.path.exists(repo_db_dir):
                os.makedirs(repo_db_dir)

            import shutil
            shutil.copy2(self.db_path, repo_db_path)

            # Добавляем только database.db
            add_result = subprocess.run(['git', 'add', db_repo_path],
                                        cwd=self.repo_root,
                                        capture_output=True,
                                        text=True,
                                        timeout=30)

            if add_result.returncode != 0:
                error_msg = add_result.stderr if add_result.stderr else add_result.stdout
                QMessageBox.critical(self, "Ошибка", f"Ошибка при добавлении файла:\n{error_msg}")
                return

            # Проверяем, есть ли изменения для коммита
            status_result = subprocess.run(['git', 'status', '--porcelain', db_repo_path],
                                           cwd=self.repo_root,
                                           capture_output=True,
                                           text=True,
                                           timeout=30)

            if not status_result.stdout.strip():
                QMessageBox.information(self, "Информация", "Нет изменений в базе данных для коммита")
                return

            # Коммитим только database.db
            commit_result = subprocess.run(['git', 'commit', '-m', 'Update database from application', db_repo_path],
                                           cwd=self.repo_root,
                                           capture_output=True,
                                           text=True,
                                           timeout=30)

            if commit_result.returncode != 0 and "nothing to commit" not in commit_result.stderr:
                error_msg = commit_result.stderr if commit_result.stderr else commit_result.stdout
                QMessageBox.critical(self, "Ошибка", f"Ошибка при коммите:\n{error_msg}")
                return

            # Пушим
            push_result = subprocess.run(['git', 'push', 'origin', 'master', '--force'],
                                         cwd=self.repo_root,
                                         capture_output=True,
                                         text=True,
                                         timeout=30)

            if push_result.returncode == 0:
                QMessageBox.information(self, "Успех", "Файл склада отправлен в репозиторий")
            else:
                error_msg = push_result.stderr if push_result.stderr else push_result.stdout
                QMessageBox.critical(self, "Ошибка", f"Ошибка при отправке:\n{error_msg}")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {str(e)}")

    def load_materials(self):
        """Загружает материалы в выпадающий список"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM materials")
        materials = cursor.fetchall()
        conn.close()

        self.material_combo.clear()
        for mat_id, mat_name in materials:
            self.material_combo.addItem(mat_name, mat_id)

    def load_data(self):
        """Загружает данные склада"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT w.id, m.name, w.length, w.quantity 
            FROM warehouse w
            JOIN materials m ON w.material_id = m.id
            ORDER BY m.name
        ''')
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
            # Проверяем, есть ли уже такая запись
            cursor.execute(
                "SELECT id FROM warehouse WHERE material_id = ? AND length = ?",
                (material_id, length_val)
            )
            existing = cursor.fetchone()

            if existing:
                # Обновляем количество
                cursor.execute(
                    "UPDATE warehouse SET quantity = quantity + ? WHERE id = ?",
                    (quantity_val, existing[0])
                )
            else:
                # Добавляем новую запись
                cursor.execute(
                    "INSERT INTO warehouse (material_id, length, quantity) VALUES (?, ?, ?)",
                    (material_id, length_val, quantity_val)
                )

            conn.commit()
            self.load_data()  # Перезагружаем таблицу
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

        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            "Вы уверены, что хотите удалить эту запись?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM warehouse WHERE id = ?", (item_id,))
            conn.commit()
            conn.close()
            self.load_data()
            QMessageBox.information(self, "Успех", "Запись удалена")


class ProductsTab(QWidget):
    def __init__(self, db_path, main_window=None):  # Добавляем параметр main_window
        super().__init__()
        self.db_path = db_path
        self.main_window = main_window  # Сохраняем ссылку на главное окно
        self.selected_product_id = None
        self.selected_product_name = None
        self.init_ui()
        self.load_products()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Группа для изделий
        products_group = QGroupBox("Изделия")
        products_layout = QVBoxLayout()

        # Таблица изделий
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(2)
        self.products_table.setHorizontalHeaderLabels(["ID", "Название"])
        self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.products_table.cellClicked.connect(self.on_product_selected)
        products_layout.addWidget(self.products_table)

        # Форма добавления изделия
        form_layout = QFormLayout()

        self.product_name_input = QLineEdit()
        self.product_name_input.setPlaceholderText("Островок")
        form_layout.addRow(QLabel("Название изделия:"), self.product_name_input)

        # Кнопки
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

        # Группа для состава изделия
        self.composition_group = QGroupBox("Состав изделия")
        self.composition_group.setEnabled(False)  # Изначально отключено
        composition_layout = QVBoxLayout()

        # Таблица состава
        self.composition_table = QTableWidget()
        self.composition_table.setColumnCount(5)
        self.composition_table.setHorizontalHeaderLabels(["ID", "Материал", "Тип", "Количество", "Длина (м)"])
        self.composition_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        composition_layout.addWidget(self.composition_table)

        # Форма добавления материала в состав
        add_form_layout = QFormLayout()

        self.material_combo = QComboBox()
        add_form_layout.addRow(QLabel("Материал:"), self.material_combo)

        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("1")
        add_form_layout.addRow(QLabel("Количество:"), self.quantity_input)

        self.length_input = QLineEdit()
        self.length_input.setPlaceholderText("0.75 (для пиломатериалов)")
        add_form_layout.addRow(QLabel("Длина (м):"), self.length_input)

        # Кнопки
        comp_btn_layout = QHBoxLayout()

        self.add_to_composition_btn = QPushButton("Добавить в состав")
        self.add_to_composition_btn.clicked.connect(self.add_to_composition)
        comp_btn_layout.addWidget(self.add_to_composition_btn)

        self.remove_from_composition_btn = QPushButton("Удалить из состава")
        self.remove_from_composition_btn.clicked.connect(self.remove_from_composition)
        comp_btn_layout.addWidget(self.remove_from_composition_btn)

        add_form_layout.addRow(comp_btn_layout)
        composition_layout.addLayout(add_form_layout)

        # Поле себестоимости
        self.cost_label = QLabel("Себестоимость: 0.00 руб")
        composition_layout.addWidget(self.cost_label)

        self.composition_group.setLayout(composition_layout)
        main_layout.addWidget(self.composition_group)

        self.setLayout(main_layout)

    def recalculate_all_products_cost(self):
        """Пересчитывает себестоимость всех изделий"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            # Получаем все изделия
            cursor.execute("SELECT id FROM products")
            product_ids = [row[0] for row in cursor.fetchall()]

            for product_id in product_ids:
                # Рассчитываем себестоимость для каждого изделия
                cursor.execute('''
                    SELECT m.price, pc.quantity, pc.length
                    FROM product_composition pc
                    JOIN materials m ON pc.material_id = m.id
                    WHERE pc.product_id = ?
                ''', (product_id,))
                composition = cursor.fetchall()

                total_cost = 0
                for row in composition:
                    price, quantity, length = row
                    if length:  # Для пиломатериалов
                        total_cost += price * quantity * length
                    else:  # Для метизов
                        total_cost += price * quantity

                # Обновляем себестоимость изделия
                cursor.execute("UPDATE products SET cost = ? WHERE id = ?",
                               (total_cost, product_id))

            conn.commit()
        except Exception as e:
            print(f"Ошибка при пересчете себестоимости: {str(e)}")
            conn.rollback()
        finally:
            conn.close()

    def load_products(self):
        """Загружает список изделий"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, cost FROM products ORDER BY name")
        products = cursor.fetchall()
        conn.close()

        # Обновляем таблицу - добавляем столбец для себестоимости
        self.products_table.setColumnCount(3)
        self.products_table.setHorizontalHeaderLabels(["ID", "Название", "Себестоимость"])

        self.products_table.setRowCount(len(products))
        for row_idx, (prod_id, prod_name, cost) in enumerate(products):
            self.products_table.setItem(row_idx, 0, QTableWidgetItem(str(prod_id)))
            self.products_table.setItem(row_idx, 1, QTableWidgetItem(prod_name))
            self.products_table.setItem(row_idx, 2, QTableWidgetItem(f"{cost:.2f} руб"))

    def on_product_selected(self, row, col):
        """Обработка выбора изделия"""
        try:
            # Проверяем, что выбрана валидная строка
            if row < 0 or row >= self.products_table.rowCount():
                return

            # Получаем ID и название изделия
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

            # Рассчитываем себестоимость с обработкой ошибок
            try:
                self.calculate_product_cost()
            except Exception as e:
                QMessageBox.warning(self, "Ошибка расчета", f"Не удалось рассчитать себестоимость: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка выбора", f"Произошла ошибка: {str(e)}")

    def load_materials(self):
        """Загружает материалы в выпадающий список"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, type FROM materials ORDER BY name")
        materials = cursor.fetchall()
        conn.close()

        self.material_combo.clear()
        for mat_id, mat_name, mat_type in materials:
            self.material_combo.addItem(f"{mat_name} ({mat_type})", mat_id)

    def load_composition(self):
        """Загружает состав выбранного изделия"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT pc.id, m.name, m.type, pc.quantity, pc.length 
            FROM product_composition pc
            JOIN materials m ON pc.material_id = m.id
            WHERE pc.product_id = ?
        ''', (self.selected_product_id,))
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
        """Добавление нового изделия"""
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
        """Удаление выбранного изделия"""
        selected_row = self.products_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите изделие для удаления")
            return

        product_id = int(self.products_table.item(selected_row, 0).text())
        product_name = self.products_table.item(selected_row, 1).text()

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Вы уверены, что хотите удалить изделие '{product_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                # Удаляем состав изделия
                cursor.execute("DELETE FROM product_composition WHERE product_id = ?", (product_id,))
                # Удаляем само изделие
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
        """Добавление материала в состав изделия"""
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
                (self.selected_product_id, material_id, quantity_val, length_val)
            )
            conn.commit()
            self.load_composition()
            self.calculate_product_cost()
            QMessageBox.information(self, "Успех", "Материал добавлен в состав")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка базы данных", str(e))
        finally:
            conn.close()

    def remove_from_composition(self):
        """Удаление материала из состава изделия"""
        selected_row = self.composition_table.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите материал для удаления")
            return

        comp_id = int(self.composition_table.item(selected_row, 0).text())
        material_name = self.composition_table.item(selected_row, 1).text()

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить материал '{material_name}' из состава?",
            QMessageBox.Yes | QMessageBox.No
        )

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
        """Расчет себестоимости изделия"""
        if not hasattr(self, 'selected_product_id') or self.selected_product_id is None:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите изделие")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 1. Получаем состав изделия
            cursor.execute('''
                SELECT m.price, pc.quantity, pc.length
                FROM product_composition pc
                JOIN materials m ON pc.material_id = m.id
                WHERE pc.product_id = ?
            ''', (self.selected_product_id,))
            composition = cursor.fetchall()

            # 2. Рассчитываем себестоимость
            total_cost = 0
            for row in composition:
                price, quantity, length = row
                if length:  # Для пиломатериалов
                    total_cost += price * quantity * length
                else:  # Для метизов
                    total_cost += price * quantity

            # 3. Обновляем значение в интерфейсе
            self.cost_label.setText(f"Себестоимость: {total_cost:.2f} руб")

            # 4. Обновляем значение в базе данных
            cursor.execute("UPDATE products SET cost = ? WHERE id = ?",
                           (total_cost, self.selected_product_id))
            conn.commit()

            # 5. Обновляем кэш стоимости в заказах, если он существует
            if self.main_window and hasattr(self.main_window, 'orders_tab'):
                if hasattr(self.main_window.orders_tab, 'product_cost_cache'):
                    if self.selected_product_id in self.main_window.orders_tab.product_cost_cache:
                        del self.main_window.orders_tab.product_cost_cache[self.selected_product_id]

        except Exception as e:
            QMessageBox.critical(self, "Ошибка расчета", f"Произошла ошибка: {str(e)}")
        finally:
            conn.close()


class OrdersTab(QWidget):
    def __init__(self, db_path, main_window):
        super().__init__()
        self.db_path = db_path
        self.main_window = main_window
        self.init_ui()
        self.load_products()
        self.current_order = []  # Хранит текущий заказ: (product_id, quantity)
        self.product_cost_cache = {}  # Кэш стоимости изделий

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Группа для создания заказа
        order_group = QGroupBox("Создать заказ")
        order_layout = QVBoxLayout()

        # Таблица текущего заказа
        self.order_table = QTableWidget()
        self.order_table.setColumnCount(3)
        self.order_table.setHorizontalHeaderLabels(["Изделие", "Количество", "Себестоимость"])
        self.order_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        order_layout.addWidget(self.order_table)

        # Форма добавления позиции
        form_layout = QFormLayout()

        # Выбор изделия
        self.product_combo = QComboBox()
        form_layout.addRow(QLabel("Изделие:"), self.product_combo)

        # Количество
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setMinimum(1)
        self.quantity_spin.setMaximum(999)
        self.quantity_spin.setValue(1)
        form_layout.addRow(QLabel("Количество:"), self.quantity_spin)

        # Кнопка добавления в заказ
        self.add_to_order_btn = QPushButton("Добавить в заказ")
        self.add_to_order_btn.clicked.connect(self.add_to_order)
        form_layout.addRow(self.add_to_order_btn)

        order_layout.addLayout(form_layout)

        # Кнопки управления заказом
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

        # Поле для инструкций по распилу
        self.instructions_text = QTextEdit()
        self.instructions_text.setReadOnly(True)
        self.instructions_text.setMinimumHeight(150)
        order_layout.addWidget(QLabel("Окно сообщений:"))
        order_layout.addWidget(self.instructions_text)

        # Поле для итоговой стоимости
        self.total_cost_label = QLabel("Общая себестоимость: 0.00 руб")
        self.total_cost_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        order_layout.addWidget(self.total_cost_label)

        order_group.setLayout(order_layout)
        main_layout.addWidget(order_group)

        # Группа истории заказов
        history_group = QGroupBox("История заказов")
        history_layout = QVBoxLayout()

        # Таблица истории заказов
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["ID", "Дата", "Изделий", "Сумма"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.cellDoubleClicked.connect(self.show_order_details)
        history_layout.addWidget(self.history_table)

        history_group.setLayout(history_layout)
        main_layout.addWidget(history_group)

        self.setLayout(main_layout)

    def open_pdf(self, pdf_path):
        """Открывает PDF-файл с помощью стандартного приложения системы"""
        import subprocess
        import os
        import platform

        if not os.path.exists(pdf_path):
            QMessageBox.warning(self, "Ошибка", f"PDF-файл не найден: {pdf_path}")
            return

        try:
            if platform.system() == 'Windows':
                os.startfile(pdf_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.call(('open', pdf_path))
            else:  # Linux
                subprocess.call(('xdg-open', pdf_path))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть PDF: {str(e)}")

    def load_products(self):
        """Загружает изделия в выпадающий список"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM products")
        products = cursor.fetchall()
        conn.close()

        self.product_combo.clear()
        for prod_id, prod_name in products:
            self.product_combo.addItem(prod_name, prod_id)

    def add_to_order(self):
        """Добавляет позицию в текущий заказ"""
        product_id = self.product_combo.currentData()
        product_name = self.product_combo.currentText()
        quantity = self.quantity_spin.value()

        # Получаем себестоимость изделия (из кэша или базы данных)
        if product_id in self.product_cost_cache:
            cost_per_unit = self.product_cost_cache[product_id]
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT cost FROM products WHERE id = ?", (product_id,))
            cost_per_unit = cursor.fetchone()[0]
            conn.close()
            self.product_cost_cache[product_id] = cost_per_unit  # Сохраняем в кэш

        # Проверяем, есть ли уже этот продукт в заказе
        existing_row = -1
        for row in range(self.order_table.rowCount()):
            if int(self.order_table.item(row, 0).data(Qt.UserRole)) == product_id:
                existing_row = row
                break

        if existing_row >= 0:
            # Обновляем количество
            current_quantity = int(self.order_table.item(existing_row, 1).text())
            new_quantity = current_quantity + quantity
            self.order_table.item(existing_row, 1).setText(str(new_quantity))

            # Пересчитываем стоимость на основе стоимости за единицу
            new_cost = cost_per_unit * new_quantity
            self.order_table.item(existing_row, 2).setText(f"{new_cost:.2f} руб")
        else:
            # Добавляем новую строку
            row_count = self.order_table.rowCount()
            self.order_table.setRowCount(row_count + 1)

            # Сохраняем product_id в UserRole
            item = QTableWidgetItem(product_name)
            item.setData(Qt.UserRole, product_id)
            self.order_table.setItem(row_count, 0, item)

            self.order_table.setItem(row_count, 1, QTableWidgetItem(str(quantity)))
            self.order_table.setItem(row_count, 2, QTableWidgetItem(f"{cost_per_unit * quantity:.2f} руб"))

        # Обновляем текущий заказ
        self.current_order = []
        for row in range(self.order_table.rowCount()):
            product_id = int(self.order_table.item(row, 0).data(Qt.UserRole))
            quantity = int(self.order_table.item(row, 1).text())
            self.current_order.append((product_id, quantity))

        # Обновляем итоговую стоимость
        self.update_total_cost()

    def update_total_cost(self):
        """Пересчитывает общую стоимость заказа"""
        total = 0
        for row in range(self.order_table.rowCount()):
            cost_text = self.order_table.item(row, 2).text().replace(' руб', '')
            total += float(cost_text)

        self.total_cost_label.setText(f"Общая себестоимость: {total:.2f} руб")

    def clear_order(self):
        """Очищает текущий заказ"""
        self.order_table.setRowCount(0)
        self.current_order = []
        self.instructions_text.clear()
        self.total_cost_label.setText("Общая себестоимость: 0.00 руб")

    def calculate_order(self):
        """Рассчитывает заказ без подтверждения"""
        if not self.current_order:
            QMessageBox.warning(self, "Ошибка", "Заказ пуст")
            return

        # Рассчитываем общую стоимость
        total_cost = 0
        materials_summary = defaultdict(float)

        for product_id, quantity in self.current_order:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT cost FROM products WHERE id = ?", (product_id,))
            cost = cursor.fetchone()[0]
            total_cost += cost * quantity

            # Получаем состав продукта
            cursor.execute('''
                SELECT m.name, pc.quantity, pc.length, m.type
                FROM product_composition pc
                JOIN materials m ON pc.material_id = m.id
                WHERE pc.product_id = ?
            ''', (product_id,))

            for name, comp_quantity, length, mtype in cursor.fetchall():
                if mtype == "Пиломатериал" and length:
                    materials_summary[name] += comp_quantity * quantity * length
                else:
                    materials_summary[name] += comp_quantity * quantity

            conn.close()

        # Рассчитываем требования к материалам для проверки доступности
        requirements = self._calculate_material_requirements()
        stock_items = self._get_current_stock()

        # Проверяем доступность материалов
        optimizer = CuttingOptimizer()
        result = optimizer.optimize_cutting(
            requirements,
            stock_items,
            self.db_path
        )

        # Формируем сообщение с материалами
        materials_message = "📦 Требуемые материалы:\n\n"
        for material, amount in materials_summary.items():
            # Определяем единицы измерения
            material_types = CuttingOptimizer._get_material_types(self.db_path)
            unit = "м" if material_types.get(material) == "Пиломатериал" else "шт"
            materials_message += f"▫️ {material}: {amount:.2f} {unit}\n"

            # Формируем сообщение о доступности материалов
            if result['can_produce']:
                availability_message = "\n✅ Материалов достаточно для производства"
            else:
                availability_message = "\n❌ Материалов недостаточно:\n"
                # Группируем ошибки по материалам для лучшей читаемости
                material_errors = defaultdict(list)
                for error in result['missing']:
                    # Извлекаем название материала из сообщения об ошибке
                    if ":" in error:
                        material = error.split(":")[0]
                        material_errors[material].append(error)

                # Формируем сообщение с группировкой по материалам
                for material, errors in material_errors.items():
                    availability_message += f"\n   {material}:\n"
                    for error in errors:
                        # Убираем название материала из каждого сообщения, так как оно уже указано
                        error_msg = error.split(":", 1)[1] if ":" in error else error
                        availability_message += f"      -{error_msg.strip()}\n"

        instructions = "📊 Расчет заказа:\n\n"
        instructions += f"💰 Себестоимость: {total_cost:.2f} руб\n"
        instructions += f"💰 Цена реализации: {total_cost * 2:.2f} руб\n\n"
        instructions += materials_message
        instructions += availability_message

        self.instructions_text.setText(instructions)
        self.total_cost_label.setText(f"Общая себестоимость: {total_cost:.2f} руб")

    def confirm_order(self):
        try:
            print("[DEBUG] Начало подтверждения заказа")
            if not self.current_order:
                QMessageBox.warning(self, "Ошибка", "Заказ пуст")
                return

            print("[DEBUG] Расчет общей стоимости")
            total_cost = 0
            order_details = []
            for product_id, quantity in self.current_order:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name, cost FROM products WHERE id = ?", (product_id,))
                name, cost = cursor.fetchone()
                conn.close()
                total_cost += cost * quantity
                order_details.append((product_id, name, quantity, cost * quantity))

            print("[DEBUG] Расчет требований к материалам")
            requirements = self._calculate_material_requirements()
            print(f"Требования: {requirements}")

            print("[DEBUG] Получение текущих остатков")
            stock_items = self._get_current_stock()
            print(f"Остатки: {stock_items}")

            optimizer = CuttingOptimizer()
            result = optimizer.optimize_cutting(
                requirements,
                stock_items,
                self.db_path
            )

            print(f"[DEBUG] Результат оптимизации: can_produce={result['can_produce']}")
            print(f"[DEBUG] Инструкции: {result.get('cutting_instructions', {})}")
            print(f"[DEBUG] Обновленные остатки: {result['updated_warehouse']}")

            if not result['can_produce']:
                error_msg = "Недостаточно материалов:\n" + "\n".join(result['missing'])
                QMessageBox.critical(self, "Ошибка", error_msg)
                return

            print("[DEBUG] Обновление склада")
            self._update_warehouse(result['updated_warehouse'])

            # Обновляем отображение склада в GUI
            if hasattr(self.main_window, 'warehouse_tab'):
                self.main_window.warehouse_tab.load_data()

            print("[DEBUG] Формирование инструкций")
            instructions_text = self._generate_instructions_text(total_cost, result, requirements)

            print("[DEBUG] Сохранение заказа в БД")
            # Сохраняем заказ и получаем его ID
            order_id = self._save_order_to_db(total_cost, order_details, instructions_text)

            # Генерация PDF
            if getattr(sys, 'frozen', False):
                pdf_dir = os.path.join(os.path.dirname(sys.executable), 'orders')
            else:
                pdf_dir = os.path.join(os.path.dirname(self.db_path), 'orders')
            if not os.path.exists(pdf_dir):
                os.makedirs(pdf_dir)

            pdf_filename = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_order.pdf"
            pdf_path = os.path.join(pdf_dir, pdf_filename)

            # Сохраняем информацию о PDF в базе данных
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE orders SET pdf_filename = ? WHERE id = ?",
                           (pdf_filename, order_id))
            conn.commit()
            conn.close()

            # Регистрация шрифта с поддержкой кириллицы
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            try:
                font_path = os.path.join(os.path.dirname(__file__), 'fonts', 'arial.ttf')
                pdfmetrics.registerFont(TTFont('Arial', font_path))
            except:
                print("Шрифт Arial не найден, используется стандартный")

            doc = SimpleDocTemplate(pdf_path, pagesize=letter)
            styles = getSampleStyleSheet()

            # Установка шрифта для всех стилей
            for style in styles.byName.values():
                try:
                    style.fontName = 'Arial'
                except:
                    pass
                style.leading = 14

            story = []

            # Заголовок
            story.append(Paragraph(f"Заказ от {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Title']))
            story.append(Spacer(1, 12))

            # Таблица с себестоимостью и ценой реализации
            sale_price = total_cost * 2
            from reportlab.lib import colors
            from reportlab.platypus import Table, TableStyle

            # Создаем таблицу для стоимости и цены реализации
            cost_data = [
                [Paragraph(f"<b>Себестоимость:</b> {round(total_cost, 2):.2f} руб", styles['Heading2']),
                 Paragraph(f"<b>Цена реализации:</b> {round(sale_price, 2):.2f} руб", styles['Heading2'])]
            ]

            cost_table = Table(cost_data, colWidths=[250, 250])
            cost_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ]))

            story.append(cost_table)
            story.append(Spacer(1, 12))

            # Количество изделий
            story.append(Paragraph("Количество изделий:", styles['Heading2']))
            for _, name, quantity, _ in order_details:
                story.append(Paragraph(f"- {name}: {quantity} шт", styles['Normal']))
            story.append(Spacer(1, 12))

            # Затрачиваемые материалы
            story.append(Paragraph("Затрачиваемые материалы:", styles['Heading2']))
            materials_used = defaultdict(float)
            material_types = CuttingOptimizer._get_material_types(self.db_path)
            for material, req_list in requirements.items():
                total = sum(req[0] for req in req_list)
                unit = 'м' if material_types.get(material) == 'Пиломатериал' else 'шт'
                materials_used[material] += total
                story.append(Paragraph(f"- {material}: {round(total, 2):.2f} {unit}", styles['Normal']))
            story.append(Spacer(1, 12))

            # Инструкция по распилу
            if instructions_text:
                # Используем моноширинный шрифт для инструкций
                try:
                    pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
                    instruction_style = styles['Normal']
                    instruction_style.fontName = 'Arial'
                except:
                    instruction_style = styles['Normal']

                instructions_pdf = instructions_text.replace('\n', '<br/>')
                story.append(Paragraph("Инструкция по распилу:", styles['Heading2']))
                story.append(Paragraph(instructions_pdf, instruction_style))

            doc.build(story)
            print(f"[DEBUG] PDF сгенерирован: {pdf_path}")
            QMessageBox.information(self, "PDF", f"PDF заказа сохранён: {pdf_path}")

            print("[DEBUG] Очистка заказа")
            self.clear_order()
            self.load_order_history()

            # Показываем сообщение о подтверждении заказа
            self.instructions_text.setText("Заказ подтвержден, PDF-отчёт сформирован.\nСклад был обновлен.")

            QMessageBox.information(self, "Успех", "Заказ успешно подтвержден!")
            print("[DEBUG] Подтверждение заказа завершено")
        except Exception as e:
            print(f"[ERROR] Ошибка при подтверждении заказа: {str(e)}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Произошла критическая ошибка: {str(e)}")

    def _generate_instructions_text(self, total_cost, result, requirements):
        """Генерирует полный текст инструкций для заказа"""
        instructions = ""

        # Получаем типы материалов из БД
        material_types = CuttingOptimizer._get_material_types(self.db_path)

        if result.get('cutting_instructions'):
            for material, material_instructions in result['cutting_instructions'].items():
                # Пропускаем метизы в инструкциях по распилу
                if material_types.get(material) == "Метиз":
                    continue

                instructions += f"Материал: {material}\n"

                for i, instr in enumerate(material_instructions, 1):
                    # Убираем двоеточие после "Взять отрезок"
                    instr = instr.replace("Взять отрезок", "Взять отрезок").replace("м:", "м")

                    # Заменяем точки на скобки в нумерации распилов
                    lines = instr.split('\n')
                    formatted_lines = []

                    for line in lines:
                        if line.strip().startswith(tuple(str(x) for x in range(1, 10))):
                            # Это строка с распилом вида "1. Отпилить..."
                            parts = line.split('.', 1)
                            if len(parts) > 1:
                                formatted_lines.append(f"   {parts[0]}){parts[1]}")
                            else:
                                formatted_lines.append(line)
                        else:
                            formatted_lines.append(line)

                    # Объединяем обратно
                    formatted_instr = '\n'.join(formatted_lines)
                    instructions += f"{i}. {formatted_instr}\n\n"

        if not instructions.strip():
            instructions = "Инструкции по распилу не требуются."

        return instructions.strip()

    def _calculate_material_requirements(self):
        """Рассчитывает требования к материалам для текущего заказа"""
        requirements = defaultdict(list)

        for product_id, quantity in self.current_order:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Получаем название изделия
            cursor.execute("SELECT name FROM products WHERE id = ?", (product_id,))
            product_name = cursor.fetchone()[0]

            # Получаем состав изделия
            cursor.execute('''
                SELECT m.name, m.type, pc.quantity, pc.length
                FROM product_composition pc
                JOIN materials m ON pc.material_id = m.id
                WHERE pc.product_id = ?
            ''', (product_id,))

            for material, mtype, comp_quantity, length in cursor.fetchall():
                # Для пиломатериалов добавляем каждый отрезок отдельно с указанием изделия
                if mtype == "Пиломатериал" and length:
                    for _ in range(int(comp_quantity * quantity)):
                        requirements[material].append((length, product_name))
                # Для метизов добавляем общее количество с указанием изделия
                else:
                    # Важно: для метизов храним (количество, изделие)
                    requirements[material].append((comp_quantity * quantity, product_name))

            conn.close()

        return requirements

    def _get_current_stock(self):
        """Возвращает текущие остатки на складе"""
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

    def _update_warehouse(self, updated_data):
        """Обновляет склад на основе результатов оптимизации"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Полностью очищаем склад
            cursor.execute("DELETE FROM warehouse")

            # Добавляем обновленные данные
            for material, length, quantity in updated_data:
                # Получаем ID материала
                cursor.execute("SELECT id FROM materials WHERE name = ?", (material,))
                result = cursor.fetchone()

                if result and quantity > 0:
                    mat_id = result[0]
                    cursor.execute(
                        "INSERT INTO warehouse (material_id, length, quantity) VALUES (?, ?, ?)",
                        (mat_id, length, quantity)
                    )

            conn.commit()

            # Логируем изменения
            print(f"[DEBUG] Склад обновлен: {len(updated_data)} записей")
            for item in updated_data:
                print(f"  - {item[0]}: {item[1]}м x {item[2]}шт")

        except sqlite3.Error as e:
            print(f"Ошибка при обновлении склада: {e}")
            conn.rollback()
        finally:
            conn.close()

        # Обновляем отображение склада
        if hasattr(self.main_window, 'warehouse_tab'):
            self.main_window.warehouse_tab.load_data()

    def _save_order_to_db(self, total_cost, order_details, instructions_text):
        """Сохраняет заказ в базу данных вместе с инструкциями и возвращает ID заказа"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        order_id = None

        try:
            # Добавляем запись о заказе с инструкциями
            cursor.execute('''
                INSERT INTO orders (order_date, total_cost, instructions)
                VALUES (datetime('now'), ?, ?)
            ''', (total_cost, instructions_text))
            order_id = cursor.lastrowid

            # Добавляем позиции заказа
            for product_id, name, quantity, cost in order_details:
                cursor.execute('''
                    INSERT INTO order_items (order_id, product_id, quantity, product_name, cost)
                    VALUES (?, ?, ?, ?, ?)
                ''', (order_id, product_id, quantity, name, cost))

            conn.commit()
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка базы данных", f"Ошибка при сохранении заказа: {str(e)}")
            conn.rollback()
        finally:
            conn.close()

        return order_id

    def load_order_history(self):
        """Загружает историю заказов"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT o.id, o.order_date, o.total_cost, 
                       SUM(oi.quantity) as total_items, o.pdf_filename
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                GROUP BY o.id
                ORDER BY o.order_date DESC
            ''')
            orders = cursor.fetchall()

            self.history_table.setRowCount(len(orders))
            self.history_table.setColumnCount(5)  # Увеличиваем количество столбцов
            self.history_table.setHorizontalHeaderLabels(["ID", "Дата", "Изделий", "Сумма", "PDF"])

            # Устанавливаем ширину столбцов
            self.history_table.setColumnWidth(0, 50)  # ID
            self.history_table.setColumnWidth(1, 150)  # Дата
            self.history_table.setColumnWidth(2, 80)  # Изделий
            self.history_table.setColumnWidth(3, 100)  # Сумма
            self.history_table.setColumnWidth(4, 80)  # PDF

            for row_idx, (order_id, date, total_cost, items_count, pdf_filename) in enumerate(orders):
                self.history_table.setItem(row_idx, 0, QTableWidgetItem(str(order_id)))
                self.history_table.setItem(row_idx, 1, QTableWidgetItem(date))
                self.history_table.setItem(row_idx, 2, QTableWidgetItem(str(items_count)))
                self.history_table.setItem(row_idx, 3, QTableWidgetItem(f"{total_cost:.2f} руб"))

                # Добавляем кнопку для открытия PDF
                if pdf_filename:
                    pdf_btn = QPushButton("Открыть")
                    # Правильно определяем путь к папке с PDF-файлами
                    if getattr(sys, 'frozen', False):
                        pdf_dir = os.path.join(os.path.dirname(sys.executable), 'orders')
                    else:
                        pdf_dir = os.path.join(os.path.dirname(self.db_path), 'orders')
                    pdf_path = os.path.join(pdf_dir, pdf_filename)
                    pdf_btn.clicked.connect(lambda checked, path=pdf_path: self.open_pdf(path))
                    self.history_table.setCellWidget(row_idx, 4, pdf_btn)
                else:
                    self.history_table.setItem(row_idx, 4, QTableWidgetItem("Нет PDF"))
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка базы данных", f"Ошибка загрузки истории: {str(e)}")
        finally:
            conn.close()

    def show_order_details(self, row, column):
        """Показывает детали выбранного заказа с инструкциями"""
        order_id = self.history_table.item(row, 0).text()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT product_name, quantity, cost 
            FROM order_items 
            WHERE order_id = ?
        ''', (order_id,))
        items = cursor.fetchall()

        cursor.execute('''
            SELECT order_date, total_cost, instructions, pdf_filename 
            FROM orders 
            WHERE id = ?
        ''', (order_id,))
        order_date, total_cost, instructions, pdf_filename = cursor.fetchone()
        conn.close()

        # Создаем диалоговое окно с вкладками
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Детали заказа №{order_id}")
        dialog.setMinimumSize(600, 500)

        layout = QVBoxLayout()
        tab_widget = QTabWidget()

        # Вкладка с изделиями
        items_tab = QWidget()
        items_layout = QVBoxLayout()

        items_text = f"Заказ от {order_date}:\n\n"
        items_text += f"Общая стоимость: {total_cost:.2f} руб\n\n"
        items_text += "Состав заказа:\n"
        for name, quantity, cost in items:
            items_text += f"- {name}: {quantity} шт ({cost:.2f} руб)\n"

        items_label = QTextEdit(items_text)
        items_label.setReadOnly(True)
        items_layout.addWidget(items_label)
        items_tab.setLayout(items_layout)
        tab_widget.addTab(items_tab, "Изделия")

        # Вкладка с инструкциями
        if instructions:
            instructions_tab = QWidget()
            instructions_layout = QVBoxLayout()

            instructions_label = QTextEdit(instructions)
            instructions_label.setReadOnly(True)
            instructions_layout.addWidget(instructions_label)
            instructions_tab.setLayout(instructions_layout)
            tab_widget.addTab(instructions_tab, "Инструкции")

        layout.addWidget(tab_widget)

        if pdf_filename:
            # Правильно определяем путь к папке с PDF-файлами
            if getattr(sys, 'frozen', False):
                pdf_dir = os.path.join(os.path.dirname(sys.executable), 'orders')
            else:
                pdf_dir = os.path.join(os.path.dirname(self.db_path), 'orders')
            pdf_path = os.path.join(pdf_dir, pdf_filename)

            pdf_btn = QPushButton("Открыть PDF-отчет")
            pdf_btn.clicked.connect(lambda: self.open_pdf(pdf_path))
            layout.addWidget(pdf_btn)

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec_()


class MainWindow(QMainWindow):
    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self.setWindowTitle("Учет деревообрабатывающего цеха")
        self.setGeometry(100, 100, 1000, 800)

        # Создаем кнопку обновления для главного окна
        self.refresh_btn = QPushButton("Обновить все данные")
        self.refresh_btn.clicked.connect(self.reload_all_tabs)

        # Размещаем кнопку в правом верхнем углу
        self.refresh_btn.setFixedSize(150, 30)
        self.refresh_btn.move(self.width() - 160, 0)

        # Создаем вкладки
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Подключаем сигнал переключения вкладок
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # Вкладка материалов
        self.materials_tab = MaterialsTab(db_path)
        self.materials_tab.main_window_ref = self  # Добавляем ссылку на главное окно
        self.tabs.addTab(self.materials_tab, "Материалы")

        # Вкладка склада
        self.warehouse_tab = WarehouseTab(db_path, self)
        self.tabs.addTab(self.warehouse_tab, "Склад")

        # Вкладка изделий
        self.products_tab = ProductsTab(db_path, self)  # Передаем ссылку на главное окно
        self.tabs.addTab(self.products_tab, "Изделия")

        # Вкладка заказов
        self.orders_tab = OrdersTab(db_path, self)
        self.tabs.addTab(self.orders_tab, "Заказы")

        # Добавляем кнопку обновления поверх вкладок
        self.refresh_btn.setParent(self)
        self.refresh_btn.raise_()  # Поднимаем кнопку поверх других элементов

        # Статус бар
        self.statusBar().showMessage("Готово")

    def on_tab_changed(self, index):
        """Обновляет данные при переключении вкладок"""
        tab_name = self.tabs.tabText(index)

        if tab_name == "Склад":
            self.warehouse_tab.load_materials()
        elif tab_name == "Изделия":
            self.products_tab.load_materials()
        elif tab_name == "Заказы":
            self.orders_tab.load_products()

    def update_all_comboboxes(self):
        """Обновляет все выпадающие списки во вкладках"""
        self.warehouse_tab.load_materials()
        self.products_tab.load_materials()
        self.orders_tab.load_products()

    def resizeEvent(self, event):
        """Обработчик изменения размера окна - перемещаем кнопку в правый верхний угол"""
        super().resizeEvent(event)
        self.refresh_btn.move(self.width() - 160, 0)

    def reload_all_tabs(self):
        """Перезагружает данные во всех вкладках"""
        # Пересчитываем себестоимость всех изделий
        self.products_tab.recalculate_all_products_cost()

        # Затем загружаем данные
        self.materials_tab.load_data()
        self.warehouse_tab.load_data()
        self.products_tab.load_products()
        self.orders_tab.load_order_history()
        self.orders_tab.load_products()
        self.statusBar().showMessage("Данные обновлены", 3000)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db')
    window = MainWindow(db_path)
    window.show()
    sys.exit(app.exec_())