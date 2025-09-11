from PyQt5.QtWidgets import QWidget, QMessageBox, QTableWidgetItem
from PyQt5.QtCore import Qt


class BaseTab(QWidget):
    """Базовый класс для всех вкладок приложения"""

    def __init__(self, db_path, main_window=None):
        super().__init__()
        self.db_path = db_path
        self.main_window = main_window
        self.selected_item_id = None

    def show_error(self, title, message):
        """Показать сообщение об ошибке"""
        QMessageBox.critical(self, title, message)

    def show_warning(self, title, message):
        """Показать предупреждение"""
        QMessageBox.warning(self, title, message)

    def show_info(self, title, message):
        """Показать информационное сообщение"""
        QMessageBox.information(self, title, message)

    def confirm_action(self, title, message):
        """Показать диалог подтверждения действия"""
        return QMessageBox.question(self, title, message,
                                    QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes

    def get_selected_item_id(self, table, row, id_column=0):
        """Универсальный метод получения ID выбранного элемента из таблицы"""
        try:
            if row < 0 or row >= table.rowCount():
                return None

            item = table.item(row, id_column)
            if item is None:
                return None

            return int(item.text())
        except (ValueError, AttributeError):
            return None

    def clear_table_selection(self, table):
        """Очистить выделение в таблице"""
        table.clearSelection()
        table.setCurrentItem(None)

    def make_item_readonly(self, text):
        """Создать элемент таблицы только для чтения"""
        item = QTableWidgetItem(str(text))
        item.setFlags(item.flags() ^ Qt.ItemIsEditable)
        return item

    def validate_float_input(self, text, field_name="Поле", min_value=None, max_value=None):
        """Валидация числового поля с плавающей точкой"""
        text = text.strip()
        if not text:
            self.show_warning("Ошибка валидации", f"{field_name} не может быть пустым")
            return None

        try:
            value = float(text)
            if min_value is not None and value < min_value:
                self.show_warning("Ошибка валидации",
                                  f"{field_name} должно быть больше или равно {min_value}")
                return None
            if max_value is not None and value > max_value:
                self.show_warning("Ошибка валидации",
                                  f"{field_name} должно быть меньше или равно {max_value}")
                return None
            return value
        except ValueError:
            self.show_warning("Ошибка валидации", f"{field_name} должно быть числом")
            return None

    def validate_int_input(self, text, field_name="Поле", min_value=1, max_value=None):
        """Валидация целочисленного поля"""
        text = text.strip()
        if not text:
            self.show_warning("Ошибка валидации", f"{field_name} не может быть пустым")
            return None

        try:
            value = int(text)
            if min_value is not None and value < min_value:
                self.show_warning("Ошибка валидации",
                                  f"{field_name} должно быть больше или равно {min_value}")
                return None
            if max_value is not None and value > max_value:
                self.show_warning("Ошибка валидации",
                                  f"{field_name} должно быть меньше или равно {max_value}")
                return None
            return value
        except ValueError:
            self.show_warning("Ошибка валидации", f"{field_name} должно быть целым числом")
            return None

    def validate_text_input(self, text, field_name="Поле", min_length=1, max_length=None):
        """Валидация текстового поля"""
        text = text.strip()
        if len(text) < min_length:
            if min_length == 1:
                self.show_warning("Ошибка валидации", f"{field_name} не может быть пустым")
            else:
                self.show_warning("Ошибка валидации",
                                  f"{field_name} должно содержать минимум {min_length} символов")
            return None

        if max_length is not None and len(text) > max_length:
            self.show_warning("Ошибка валидации",
                              f"{field_name} должно содержать максимум {max_length} символов")
            return None

        return text

    def populate_table_row(self, table, row_index, data, readonly_columns=None):
        """Заполнить строку таблицы данными"""
        if readonly_columns is None:
            readonly_columns = []

        for col_index, value in enumerate(data):
            if col_index < table.columnCount():
                if col_index in readonly_columns:
                    item = self.make_item_readonly(value)
                else:
                    item = QTableWidgetItem(str(value))
                table.setItem(row_index, col_index, item)

    def get_table_row_data(self, table, row_index):
        """Получить данные строки таблицы"""
        data = []
        for col in range(table.columnCount()):
            item = table.item(row_index, col)
            if item:
                data.append(item.text())
            else:
                data.append("")
        return data

    def clear_form_inputs(self, form_widgets):
        """Очистить поля формы"""
        for widget in form_widgets:
            if hasattr(widget, 'clear'):
                widget.clear()
            elif hasattr(widget, 'setCurrentIndex'):
                widget.setCurrentIndex(0)
            elif hasattr(widget, 'setValue'):
                widget.setValue(0)

    def set_table_column_widths(self, table, widths):
        """Установить ширину колонок таблицы"""
        for col, width in enumerate(widths):
            if col < table.columnCount():
                if width == -1:
                    table.horizontalHeader().setSectionResizeMode(col, table.horizontalHeader().Stretch)
                else:
                    table.setColumnWidth(col, width)

    def format_currency(self, value):
        """Форматировать значение как валюту"""
        return f"{float(value):.2f} руб"

    def format_length(self, value):
        """Форматировать значение длины"""
        if value is None or value == "":
            return ""
        return f"{float(value):.2f}"

    def safe_float_conversion(self, value, default=0.0):
        """Безопасное преобразование в float"""
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (ValueError, TypeError):
            return default

    def safe_int_conversion(self, value, default=0):
        """Безопасное преобразование в int"""
        try:
            if value is None or value == "":
                return default
            return int(value)
        except (ValueError, TypeError):
            return default

    def refresh_related_tabs(self, tab_names=None):
        """Обновить связанные вкладки"""
        if self.main_window is None:
            return

        if tab_names is None:
            # Обновляем все вкладки
            if hasattr(self.main_window, 'reload_all_tabs'):
                self.main_window.reload_all_tabs()
        else:
            # Обновляем только указанные вкладки
            for tab_name in tab_names:
                tab_widget = getattr(self.main_window, f"{tab_name}_tab", None)
                if tab_widget and hasattr(tab_widget, 'load_data'):
                    try:
                        tab_widget.load_data()
                    except Exception as e:
                        print(f"Ошибка при обновлении вкладки {tab_name}: {str(e)}")

    def handle_exception(self, exception, operation_name="операции"):
        """Обработка исключений с логированием"""
        error_message = f"Ошибка при выполнении {operation_name}: {str(exception)}"
        print(error_message)  # Логирование в консоль
        self.show_error("Ошибка", error_message)

    def set_status_message(self, message, timeout=0):
        """Установить сообщение в статусной строке"""
        if self.main_window and hasattr(self.main_window, 'statusBar'):
            if timeout > 0:
                self.main_window.statusBar().showMessage(message, timeout)
            else:
                self.main_window.statusBar().showMessage(message)

    def load_data(self):
        """Абстрактный метод загрузки данных - должен быть переопределен в наследниках"""
        pass

    def clear_form(self):
        """Абстрактный метод очистки формы - может быть переопределен в наследниках"""
        pass

    def validate_form(self):
        """Абстрактный метод валидации формы - может быть переопределен в наследниках"""
        return True