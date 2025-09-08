# main.py - исправленная версия без тестовых этапов
import sys
import os
from gui import MainWindow
from PyQt5.QtWidgets import QApplication
from database import create_database


def get_db_path():
    """Возвращает абсолютный путь к базе данных"""
    if getattr(sys, 'frozen', False):
        # Если приложение запущено как собранный exe
        base_dir = os.path.dirname(sys.executable)
        db_path = os.path.join(base_dir, 'data', 'database.db')
    else:
        # Если приложение запущено из исходного кода
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, '..', 'data', 'database.db')

    # Преобразуем путь к абсолютному и нормализуем
    db_path = os.path.abspath(db_path)
    data_dir = os.path.dirname(db_path)

    # Создаем папку data, если она не существует
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    return db_path


if __name__ == "__main__":
    app = QApplication(sys.argv)
    db_path = get_db_path()

    # Проверяем существование папки data
    data_dir = os.path.dirname(db_path)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    create_database(db_path)

    # ИСПРАВЛЕНИЕ 1: Убрано создание тестовых этапов
    # initialize_stages_data(db_path) - УДАЛЕНО

    window = MainWindow(db_path)
    window.show()
    sys.exit(app.exec_())
