import sys
import os
from gui import MainWindow
from PyQt5.QtWidgets import QApplication
from database import create_database

def get_db_path():
    """Возвращает абсолютный путь к базе данных"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, '..', 'data', 'database.db')


if __name__ == "__main__":
    app = QApplication(sys.argv)
    db_path = get_db_path()

    # Проверяем существование папки data
    data_dir = os.path.dirname(db_path)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    create_database(db_path)

    window = MainWindow(db_path)
    window.show()
    sys.exit(app.exec_())