# main.py - Точка входа приложения
"""
Запускает Qt приложение, инициализирует БД и главное окно.
"""
import sys
from PyQt5.QtWidgets import QApplication
from config import DatabaseConfig, Config
from database import create_database
from main_window import MainWindow


def main():
    # Инициализация базы данных
    create_database()
    
    # Создаем Qt приложение
    app = QApplication(sys.argv)
    
    # Путь к БД
    db_path = DatabaseConfig.get_db_path()
    
    # Создаем и показываем главное окно
    window = MainWindow(db_path)
    window.setWindowTitle(Config.APP_NAME)
    window.resize(Config.WINDOW_WIDTH, Config.WINDOW_HEIGHT)
    window.show()
    
    # Запуск цикла событий
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()