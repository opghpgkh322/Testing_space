# config.py - Конфигурация приложения
"""
Модуль конфигурации для системы управления складом веревочных парков.
Содержит все настройки, константы и пути, используемые в приложении.
"""

import os
import sys
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


class Config:
    """Основные настройки приложения"""
    
    # Информация о приложении
    APP_NAME = "Учет деревообрабатывающего цеха - SpaceConcept"
    APP_VERSION = "2.0"
    
    # Размеры окна
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 900
    WINDOW_MIN_WIDTH = 800
    WINDOW_MIN_HEIGHT = 600
    
    # Настройки оптимизатора раскроя
    MIN_USEFUL_LENGTH = 0.3  # Минимальный полезный остаток (м)
    
    # Множитель для расчета цены реализации
    SALE_PRICE_MULTIPLIER = 2.0
    
    # Настройки PDF
    PDF_PAGE_SIZE = "letter"
    PDF_FONT_SIZE_TITLE = 16
    PDF_FONT_SIZE_HEADING = 14
    PDF_FONT_SIZE_NORMAL = 12
    
    # Типы материалов
    MATERIAL_TYPES = ["Пиломатериал", "Метиз"]
    
    # Части этапов и изделий
    STAGE_PARTS = ["start", "meter", "end"]
    
    # Единицы измерения
    LUMBER_UNIT = "м"
    FASTENER_UNIT = "шт"
    
    # Ограничения ввода
    MAX_QUANTITY = 999
    MAX_LENGTH = 9999.0
    MIN_LENGTH = 0.01
    LENGTH_STEP = 0.10
    LENGTH_DECIMALS = 2


class DatabaseConfig:
    """Настройки базы данных"""
    
    DB_NAME = "database.db"
    DATA_DIR = "data"
    ORDERS_DIR = "orders"
    
    @staticmethod
    def get_db_path():
        """Возвращает абсолютный путь к базе данных"""
        if getattr(sys, 'frozen', False):
            # Запуск из собранного exe
            base_dir = os.path.dirname(sys.executable)
            db_path = os.path.join(base_dir, DatabaseConfig.DATA_DIR, DatabaseConfig.DB_NAME)
        else:
            # Запуск из исходного кода
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, DatabaseConfig.DATA_DIR, DatabaseConfig.DB_NAME)
        
        # Создаем папку data, если она не существует
        data_dir = os.path.dirname(db_path)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        return os.path.abspath(db_path)
    
    @staticmethod
    def get_orders_dir():
        """Возвращает путь к папке с заказами"""
        if getattr(sys, 'frozen', False):
            orders_dir = os.path.join(os.path.dirname(sys.executable), DatabaseConfig.ORDERS_DIR)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            orders_dir = os.path.join(base_dir, DatabaseConfig.ORDERS_DIR)
        
        if not os.path.exists(orders_dir):
            os.makedirs(orders_dir)
        
        return orders_dir


class FontConfig:
    """Настройки шрифтов для PDF"""
    
    ARIAL_FONT_NAME = "Arial"
    ARIAL_FONT_FILE = "arial.ttf"
    FONTS_DIR = "fonts"
    
    _font_registered = False
    
    @classmethod
    def setup_arial_font(cls):
        """Регистрирует шрифт Arial для использования в PDF"""
        if cls._font_registered:
            return True
        
        try:
            if getattr(sys, 'frozen', False):
                font_path = os.path.join(
                    os.path.dirname(sys.executable), 
                    cls.FONTS_DIR, 
                    cls.ARIAL_FONT_FILE
                )
            else:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                font_path = os.path.join(current_dir, cls.FONTS_DIR, cls.ARIAL_FONT_FILE)
            
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont(cls.ARIAL_FONT_NAME, font_path))
                cls._font_registered = True
                print(f"✓ Шрифт {cls.ARIAL_FONT_NAME} успешно зарегистрирован")
                return True
            else:
                print(f"✗ Файл шрифта не найден: {font_path}")
                return False
                
        except Exception as e:
            print(f"✗ Ошибка регистрации шрифта {cls.ARIAL_FONT_NAME}: {e}")
            return False
    
    @classmethod
    def is_font_available(cls):
        """Проверяет, доступен ли шрифт Arial"""
        return cls._font_registered


class GitConfig:
    """Настройки для работы с Git"""
    
    GIT_TIMEOUT = 30  # секунд
    DB_REPO_PATH = "data/database.db"
    
    @staticmethod
    def find_git_root(start_path):
        """Находит корень Git репозитория"""
        path = os.path.abspath(start_path)
        while True:
            if os.path.exists(os.path.join(path, '.git')):
                return path
            parent = os.path.dirname(path)
            if parent == path:
                return None
            path = parent


# Инициализация шрифта при импорте модуля
FontConfig.setup_arial_font()