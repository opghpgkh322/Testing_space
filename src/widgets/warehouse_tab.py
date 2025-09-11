import os
import platform
import subprocess
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
from .base_tab import BaseTab
from ..services.warehouse_service import WarehouseService
from ..services.material_service import MaterialService


class WarehouseTab(BaseTab):
    """Вкладка для работы со складом"""

    def __init__(self, db_path, main_window=None):
        super().__init__(db_path, main_window)
        self.warehouse_service = WarehouseService(db_path)
        self.material_service = MaterialService(db_path)
        self.repo_root = self.find_git_root(db_path)
        self.init_ui()
        self.load_data()

    @staticmethod
    def find_git_root(path):
        """Поиск корневой папки Git репозитория"""
        path = os.path.abspath(path)
        while True:
            if os.path.exists(os.path.join(path, '.git')):
                return path
            parent = os.path.dirname(path)
            if parent == path:
                return None
            path = parent

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        layout = QVBoxLayout()

        # Группа для добавления на склад
        add_group = QGroupBox("Добавить материал на склад")
        add_layout = QFormLayout()

        self.material_combo = QComboBox()
        self.load_materials()
        add_layout.addRow(QLabel("Материал:"), self.material_combo)

        self.length_input = QLineEdit()
        self.length_input.setPlaceholderText("0 для метизов, иначе длина в метрах")
        add_layout.addRow(QLabel("Длина (м):"), self.length_input)

        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("Количество")
        add_layout.addRow(QLabel("Количество:"), self.quantity_input)

        self.add_btn = QPushButton("Добавить на склад")
        self.add_btn.clicked.connect(self.add_to_warehouse)
        add_layout.addRow(self.add_btn)

        add_group.setLayout(add_layout)
        layout.addWidget(add_group)

        # Таблица склада
        warehouse_group = QGroupBox("Складские остатки")
        warehouse_layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Материал", "Тип", "Длина (м)", "Количество", "Ед.изм."
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellClicked.connect(self.on_table_cell_clicked)
        warehouse_layout.addWidget(self.table)

        warehouse_group.setLayout(warehouse_layout)
        layout.addWidget(warehouse_group)

        # Кнопки управления складом
        warehouse_buttons_layout = QHBoxLayout()

        self.edit_btn = QPushButton("Редактировать запись")
        self.edit_btn.clicked.connect(self.edit_warehouse_item)
        self.edit_btn.setEnabled(False)
        warehouse_buttons_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Удалить запись")
        self.delete_btn.clicked.connect(self.delete_warehouse_item)
        self.delete_btn.setEnabled(False)
        warehouse_buttons_layout.addWidget(self.delete_btn)

        self.refresh_btn = QPushButton("Обновить данные")
        self.refresh_btn.clicked.connect(self.load_data)
        warehouse_buttons_layout.addWidget(self.refresh_btn)

        layout.addLayout(warehouse_buttons_layout)

        # Git операции (если репозиторий найден)
        if self.repo_root:
            git_group = QGroupBox("Синхронизация с Git")
            git_layout = QHBoxLayout()

            self.git_pull_btn = QPushButton("Git Pull (получить обновления)")
            self.git_pull_btn.clicked.connect(self.git_pull)
            git_layout.addWidget(self.git_pull_btn)

            self.git_push_btn = QPushButton("Git Push (отправить изменения)")
            self.git_push_btn.clicked.connect(self.git_push)
            git_layout.addWidget(self.git_push_btn)

            git_group.setLayout(git_layout)
            layout.addWidget(git_group)

        # Статистика склада
        stats_group = QGroupBox("Статистика склада")
        stats_layout = QVBoxLayout()
        self.stats_label = QLabel("Загрузка статистики...")
        stats_layout.addWidget(self.stats_label)
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        self.setLayout(layout)

    def load_materials(self):
        """Загрузка списка материалов для комбобокса"""
        try:
            materials = self.warehouse_service.get_materials_for_combo()
            self.material_combo.clear()
            for mat_id, mat_name, mat_type in materials:
                self.material_combo.addItem(f"{mat_name} ({mat_type})", mat_id)
        except Exception as e:
            self.handle_exception(e, "загрузке материалов")

    def load_data(self):
        """Загрузка данных склада"""
        try:
            warehouse_items = self.warehouse_service.get_all_warehouse_items()
            self.table.setRowCount(len(warehouse_items))

            for row_idx, (w_id, name, length, quantity, m_type, unit) in enumerate(warehouse_items):
                self.populate_table_row(self.table, row_idx, [
                    w_id,
                    name,
                    m_type,
                    self.format_length(length),
                    quantity,
                    unit
                ], readonly_columns=[0, 1, 2, 5])  # ID, название, тип и ед.изм. только для чтения

            self.update_warehouse_stats()

        except Exception as e:
            self.handle_exception(e, "загрузке данных склада")

    def update_warehouse_stats(self):
        """Обновление статистики склада"""
        try:
            stock_summary = self.warehouse_service.get_stock_summary()
            low_stock_items = self.warehouse_service.get_low_stock_items(5)
            total_value = self.warehouse_service.get_warehouse_value()

            stats_text = f"<b>Общая статистика склада:</b><br>"
            stats_text += f"• Общая стоимость склада: {total_value:.2f} руб<br>"
            stats_text += f"• Видов материалов: {len(stock_summary)}<br><br>"

            if low_stock_items:
                stats_text += f"<b>⚠️ Материалы с низкими остатками:</b><br>"
                for name, m_type, total_amount, unit in low_stock_items[:5]:
                    stats_text += f"• {name}: {total_amount:.1f} {unit}<br>"
            else:
                stats_text += f"<b>✅ Все материалы в достатке</b><br>"

            self.stats_label.setText(stats_text)

        except Exception as e:
            self.stats_label.setText(f"Ошибка загрузки статистики: {str(e)}")

    def on_table_cell_clicked(self, row, column):
        """Обработка клика по таблице"""
        warehouse_id = self.get_selected_item_id(self.table, row)
        if warehouse_id is None:
            return

        try:
            self.selected_item_id = warehouse_id
            self.edit_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)

            # Заполняем поля для редактирования
            length_text = self.table.item(row, 3).text()
            quantity_text = self.table.item(row, 4).text()

            self.length_input.setText(length_text)
            self.quantity_input.setText(str(quantity_text))

        except Exception as e:
            self.handle_exception(e, "выборе записи склада")

    def add_to_warehouse(self):
        """Добавление материала на склад"""
        material_id = self.material_combo.currentData()
        if not material_id:
            self.show_warning("Ошибка", "Выберите материал")
            return

        length = self.validate_float_input(self.length_input.text(), "Длина", min_value=0)
        if length is None:
            return

        quantity = self.validate_int_input(self.quantity_input.text(), "Количество", min_value=1)
        if quantity is None:
            return

        try:
            self.warehouse_service.add_to_warehouse(material_id, length, quantity)
            self.load_data()
            self.length_input.clear()
            self.quantity_input.clear()

            material_name = self.material_combo.currentText().split(' (')[0]
            self.show_info("Успех", f"Добавлено на склад: {material_name}")
            self.set_status_message("Склад обновлен", 3000)

        except Exception as e:
            self.handle_exception(e, "добавлении на склад")

    def edit_warehouse_item(self):
        """Редактирование записи склада"""
        if not self.selected_item_id:
            self.show_warning("Ошибка", "Выберите запись для редактирования")
            return

        length = self.validate_float_input(self.length_input.text(), "Длина", min_value=0)
        if length is None:
            return

        quantity = self.validate_int_input(self.quantity_input.text(), "Количество", min_value=1)
        if quantity is None:
            return

        try:
            self.warehouse_service.update_warehouse_item(self.selected_item_id, length, quantity)
            self.load_data()
            self.clear_selection()
            self.show_info("Успех", "Запись склада обновлена")
            self.set_status_message("Запись склада обновлена", 3000)

        except Exception as e:
            self.handle_exception(e, "редактировании записи склада")

    def delete_warehouse_item(self):
        """Удаление записи склада"""
        if not self.selected_item_id:
            self.show_warning("Ошибка", "Выберите запись для удаления")
            return

        selected_row = self.table.currentRow()
        material_name = self.table.item(selected_row, 1).text()
        length = self.table.item(selected_row, 3).text()
        quantity = self.table.item(selected_row, 4).text()

        if not self.confirm_action("Подтверждение удаления",
                                   f"Удалить запись:\n{material_name}, {length}м, {quantity} шт?"):
            return

        try:
            self.warehouse_service.delete_warehouse_item(self.selected_item_id)
            self.load_data()
            self.clear_selection()
            self.show_info("Успех", "Запись удалена со склада")
            self.set_status_message("Запись удалена", 3000)

        except Exception as e:
            self.handle_exception(e, "удалении записи склада")

    def clear_selection(self):
        """Очистка выбора"""
        self.selected_item_id = None
        self.edit_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.clear_table_selection(self.table)
        self.length_input.clear()
        self.quantity_input.clear()

    def git_pull(self):
        """Синхронизация с Git (получение обновлений)"""
        if not self.repo_root:
            self.show_error("Ошибка", "Git репозиторий не найден")
            return

        if not self.confirm_action("Подтверждение",
                                   "Принудительный git pull может перезаписать локальные изменения. Продолжить?"):
            return

        try:
            # Получаем обновления
            result = subprocess.run(['git', 'fetch', 'origin'], cwd=self.repo_root,
                                    capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                self.show_error("Ошибка", f"Ошибка при получении обновлений:\n{error_msg}")
                return

            # Обновляем файл базы данных
            db_repo_path = 'data/database.db'
            reset_result = subprocess.run(['git', 'checkout', 'origin/master', '--', db_repo_path],
                                          cwd=self.repo_root, capture_output=True, text=True, timeout=30)

            if reset_result.returncode == 0:
                repo_db_path = os.path.join(self.repo_root, db_repo_path)
                if os.path.exists(repo_db_path):
                    import shutil
                    shutil.copy2(repo_db_path, self.db_path)
                    self.show_info("Успех", "Склад заполнился актуальными остатками")
                    self.load_data()
                    self.refresh_related_tabs()
                else:
                    self.show_error("Ошибка", "Файл базы данных не найден в репозитории")
            else:
                error_msg = reset_result.stderr if reset_result.stderr else reset_result.stdout
                self.show_error("Ошибка", f"Ошибка при обновлении файла:\n{error_msg}")

        except subprocess.TimeoutExpired:
            self.show_error("Ошибка", "Операция Git заняла слишком много времени")
        except Exception as e:
            self.handle_exception(e, "синхронизации с Git")

    def git_push(self):
        """Отправка изменений в Git"""
        if not self.repo_root:
            self.show_error("Ошибка", "Git репозиторий не найден")
            return

        try:
            db_repo_path = 'data/database.db'
            repo_db_path = os.path.join(self.repo_root, db_repo_path)
            repo_db_dir = os.path.dirname(repo_db_path)

            # Создаем папку если нужно
            if not os.path.exists(repo_db_dir):
                os.makedirs(repo_db_dir)

            # Копируем базу данных
            import shutil
            shutil.copy2(self.db_path, repo_db_path)

            # Добавляем файл в Git
            add_result = subprocess.run(['git', 'add', db_repo_path], cwd=self.repo_root,
                                        capture_output=True, text=True, timeout=30)

            if add_result.returncode != 0:
                error_msg = add_result.stderr if add_result.stderr else add_result.stdout
                self.show_error("Ошибка", f"Ошибка при добавлении файла:\n{error_msg}")
                return

            # Проверяем есть ли изменения
            status_result = subprocess.run(['git', 'status', '--porcelain', db_repo_path],
                                           cwd=self.repo_root, capture_output=True, text=True, timeout=30)

            if not status_result.stdout.strip():
                self.show_info("Информация", "Нет изменений в базе данных для коммита")
                return

            # Делаем коммит
            commit_result = subprocess.run(['git', 'commit', '-m', 'Update database from application', db_repo_path],
                                           cwd=self.repo_root, capture_output=True, text=True, timeout=30)

            if commit_result.returncode != 0 and "nothing to commit" not in commit_result.stderr:
                error_msg = commit_result.stderr if commit_result.stderr else commit_result.stdout
                self.show_error("Ошибка", f"Ошибка при коммите:\n{error_msg}")
                return

            # Отправляем изменения
            push_result = subprocess.run(['git', 'push', 'origin', 'master', '--force'],
                                         cwd=self.repo_root, capture_output=True, text=True, timeout=30)

            if push_result.returncode == 0:
                self.show_info("Успех", "Файл склада отправлен в репозиторий")
                self.set_status_message("Данные отправлены в Git", 3000)
            else:
                error_msg = push_result.stderr if push_result.stderr else push_result.stdout
                self.show_error("Ошибка", f"Ошибка при отправке:\n{error_msg}")

        except subprocess.TimeoutExpired:
            self.show_error("Ошибка", "Операция Git заняла слишком много времени")
        except Exception as e:
            self.handle_exception(e, "отправке в Git")

    def get_current_stock_for_requirements(self):
        """Получить текущие остатки для проверки требований (для использования в заказах)"""
        try:
            warehouse_items = self.warehouse_service.get_all_warehouse_items()
            return [(name, length, quantity) for _, name, _, length, quantity, _ in warehouse_items]
        except Exception as e:
            print(f"Ошибка при получении остатков склада: {str(e)}")
            return []

    def update_warehouse_after_order(self, updated_data):
        """Обновить склад после выполнения заказа (для использования в заказах)"""
        try:
            self.warehouse_service.update_warehouse_bulk(updated_data)
            self.load_data()
            self.set_status_message("Склад обновлен после заказа", 3000)
        except Exception as e:
            self.handle_exception(e, "обновлении склада после заказа")