# main.py - обновленная версия для работы с рефакторинговой архитектурой
import sys
import os
from PyQt5.QtWidgets import QApplication
from gui import MainWindow
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
        print(f"✅ Создана папка для данных: {data_dir}")

    return db_path


def setup_application_style(app):
    """Настройка стиля приложения"""
    app.setStyle('Fusion')

    # Устанавливаем современную темную тему для Qt приложения
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QTabWidget::pane {
            border: 1px solid #555555;
            background-color: #3c3c3c;
        }
        QTabWidget::tab-bar {
            left: 5px;
        }
        QTabBar::tab {
            background-color: #555555;
            color: #ffffff;
            padding: 8px 12px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background-color: #4CAF50;
            font-weight: bold;
        }
        QTabBar::tab:hover {
            background-color: #666666;
        }
        QGroupBox {
            font-weight: bold;
            border: 2px solid #555555;
            border-radius: 5px;
            margin: 10px 0px;
            padding: 5px 0px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QTableWidget {
            gridline-color: #555555;
            background-color: #404040;
            alternate-background-color: #4a4a4a;
        }
        QHeaderView::section {
            background-color: #555555;
            color: #ffffff;
            padding: 5px;
            font-weight: bold;
            border: none;
        }
        QPushButton {
            background-color: #555555;
            color: #ffffff;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #666666;
        }
        QPushButton:pressed {
            background-color: #444444;
        }
        QPushButton:disabled {
            background-color: #333333;
            color: #888888;
        }
        QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            background-color: #404040;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 5px;
            border-radius: 3px;
        }
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
            border: 2px solid #4CAF50;
        }
        QLabel {
            color: #ffffff;
        }
        QStatusBar {
            background-color: #333333;
            color: #ffffff;
        }
        QMenuBar {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QMenuBar::item:selected {
            background-color: #4CAF50;
        }
        QMenu {
            background-color: #3c3c3c;
            color: #ffffff;
            border: 1px solid #555555;
        }
        QMenu::item:selected {
            background-color: #4CAF50;
        }
    """)


def check_dependencies():
    """Проверка наличия необходимых зависимостей"""
    required_modules = [
        'PyQt5',
        'reportlab',
        'sqlite3'
    ]

    missing_modules = []

    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)

    if missing_modules:
        print("❌ ОШИБКА: Не найдены необходимые модули:")
        for module in missing_modules:
            print(f"  - {module}")
        print("\n📦 Установите зависимости: pip install -r requirements.txt")
        return False

    return True


def print_startup_info():
    """Вывод информации о запуске"""
    print("=" * 60)
    print("🏭 СИСТЕМА УПРАВЛЕНИЯ СКЛАДОМ - SPACE CONCEPT")
    print("   Версия: 2.0 (Рефакторинг)")
    print("   Назначение: Учет материалов для веревочных парков")
    print("=" * 60)
    print("📁 Архитектура приложения:")
    print("   ├── services/     - Бизнес-логика и работа с данными")
    print("   ├── widgets/      - Компоненты пользовательского интерфейса")
    print("   └── utils/        - Вспомогательные утилиты")
    print("=" * 60)
    print("🚀 Запуск приложения...")


def main():
    """Главная функция запуска приложения"""
    try:
        # Выводим информацию о запуске
        print_startup_info()

        # Проверяем зависимости
        if not check_dependencies():
            input("Нажмите Enter для выхода...")
            return 1

        # Создаем приложение Qt
        app = QApplication(sys.argv)
        app.setApplicationName("Space Concept - Складской учет")
        app.setApplicationVersion("2.0")
        app.setOrganizationName("Space Concept")

        # Настраиваем стиль
        setup_application_style(app)

        # Получаем путь к базе данных
        db_path = get_db_path()
        print(f"📂 Путь к базе данных: {db_path}")

        # Создаем/проверяем базу данных
        try:
            create_database(db_path)
            print("✅ База данных готова к работе")
        except Exception as e:
            print(f"❌ Ошибка инициализации базы данных: {str(e)}")
            return 1

        # ВАЖНО: Удалено создание тестовых этапов (из комментария в оригинальном main.py)
        # initialize_stages_data(db_path) - УДАЛЕНО согласно рефакторингу

        # Создаем главное окно с новой архитектурой
        try:
            window = MainWindow(db_path)
            print("✅ Интерфейс инициализирован")

            # Показываем окно
            window.show()
            print("✅ Приложение запущено успешно!")
            print("=" * 60)

            # Запускаем основной цикл приложения
            exit_code = app.exec_()

            print("\n" + "=" * 60)
            print("👋 Завершение работы приложения")
            print("=" * 60)

            return exit_code

        except ImportError as e:
            print(f"❌ Ошибка импорта модулей интерфейса: {str(e)}")
            print("💡 Убедитесь, что все файлы рефакторинга на месте")
            return 1

        except Exception as e:
            print(f"❌ Ошибка создания интерфейса: {str(e)}")
            return 1

    except KeyboardInterrupt:
        print("\n⚠️ Прерывание пользователем")
        return 0

    except Exception as e:
        print(f"❌ Критическая ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    # Запускаем приложение и передаем код возврата
    exit_code = main()
    sys.exit(exit_code)