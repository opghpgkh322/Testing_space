# main_window.py - Главное окно приложения
"""
Основной класс QMainWindow, управляющий вкладками приложения.
"""

from PyQt5.QtWidgets import QMainWindow, QPushButton, QTabWidget
from PyQt5.QtCore import Qt
from config import Config
from materials_tab import MaterialsTab
from warehouse_tab import WarehouseTab
from products_tab import ProductsTab
from stages_tab import StagesTab
from orders_tab import OrdersTab


class MainWindow(QMainWindow):
    """Главное окно приложения, содержащее вкладки и кнопки обновления"""

    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self.init_ui()

    def init_ui(self):
        # Настройка окна
        self.setWindowTitle(Config.APP_NAME)
        self.setMinimumSize(Config.WINDOW_MIN_WIDTH, Config.WINDOW_MIN_HEIGHT)

        # Кнопка обновления
        self.refresh_btn = QPushButton("Обновить все данные", self)
        self.refresh_btn.clicked.connect(self.reload_all_tabs)
        self.refresh_btn.setFixedSize(150, 30)

        # Вкладки
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # Добавление вкладок
        self.materials_tab = MaterialsTab(self.db_path)
        self.tabs.addTab(self.materials_tab, "Материалы")

        self.warehouse_tab = WarehouseTab(self.db_path, self)
        self.tabs.addTab(self.warehouse_tab, "Склад")

        self.products_tab = ProductsTab(self.db_path, self)
        self.tabs.addTab(self.products_tab, "Изделия")

        self.stages_tab = StagesTab(self.db_path, self)
        self.tabs.addTab(self.stages_tab, "Этапы")

        self.orders_tab = OrdersTab(self.db_path, self)
        self.tabs.addTab(self.orders_tab, "Заказы")

        # Размещение кнопки
        self.refresh_btn.move(self.width() - 160, 0)
        self.statusBar().showMessage("Готово")

    def resizeEvent(self, event):
        """Обновление расположения кнопки при изменении размера"""
        super().resizeEvent(event)
        self.refresh_btn.move(self.width() - 160, 0)

    def reload_all_tabs(self):
        """Перезагрузка данных во всех вкладках"""
        self.materials_tab.load_data()
        self.warehouse_tab.load_data()
        self.products_tab.load_products()
        self.stages_tab.load_stages()
        self.orders_tab.load_order_history()
        self.statusBar().showMessage("Данные обновлены", 3000)

    def on_tab_changed(self, index):
        """Обработка смены вкладок для подгрузки данных"""
        tab_name = self.tabs.tabText(index)
        if tab_name == "Склад":
            self.warehouse_tab.load_materials()
        elif tab_name == "Изделия":
            self.products_tab.load_materials()
        elif tab_name == "Этапы":
            self.stages_tab.load_products()
            self.stages_tab.load_materials()
        elif tab_name == "Заказы":
            self.orders_tab.load_order_history()