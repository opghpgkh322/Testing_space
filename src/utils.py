# utils.py - Вспомогательные функции
"""
Модуль с общими утилитами для работы GUI и БД.
"""

import sqlite3
from config import DatabaseConfig


def get_connection():
    """Открывает подключение к базе данных"""
    db_path = DatabaseConfig.get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_all(query, params=None):
    """Возвращает все строки по SQL запросу"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params or [])
        return cursor.fetchall()


def execute(query, params=None):
    """Выполняет SQL запрос без возврата результата"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params or [])
        conn.commit()