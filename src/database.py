# database.py - Работа с базой данных
"""
Модуль для создания и управления схемой SQLite базы данных.
Содержит функции инициализации БД и утилиты для миграции.
"""

import sqlite3
from config import DatabaseConfig


def check_table_structure(cursor, table_name, expected_columns):
    """Проверяет структуру таблицы и добавляет отсутствующие столбцы"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {col[1] for col in cursor.fetchall()}

    for column, col_type in expected_columns.items():
        if column not in existing_columns:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column} {col_type}")


def create_database():
    """Создает базу данных и таблицы по схеме из config"""
    db_path = DatabaseConfig.get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Создание таблиц
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        type TEXT NOT NULL,
        price REAL NOT NULL,
        unit TEXT NOT NULL
    )""" )

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS warehouse (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        material_id INTEGER NOT NULL,
        length REAL NOT NULL,
        quantity INTEGER NOT NULL,
        FOREIGN KEY(material_id) REFERENCES materials(id)
    )""" )

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        cost REAL NOT NULL DEFAULT 0.0
    )"""
    )

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS product_composition (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        material_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        length REAL,
        FOREIGN KEY(product_id) REFERENCES products(id),
        FOREIGN KEY(material_id) REFERENCES materials(id)
    )"""
    )

    # Таблицы этапов
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        cost REAL NOT NULL DEFAULT 0.0,
        description TEXT
    )"""
    )

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stage_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stage_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        part TEXT NOT NULL,
        FOREIGN KEY(stage_id) REFERENCES stages(id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    )"""
    )

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stage_materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stage_id INTEGER NOT NULL,
        material_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        length REAL,
        part TEXT NOT NULL,
        FOREIGN KEY(stage_id) REFERENCES stages(id),
        FOREIGN KEY(material_id) REFERENCES materials(id)
    )"""
    )

    # Таблицы заказов
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_date TEXT NOT NULL,
        total_cost REAL NOT NULL,
        instructions TEXT,
        pdf_filename TEXT
    )"""
    )

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER,
        stage_id INTEGER,
        quantity INTEGER NOT NULL,
        length_meters REAL,
        product_name TEXT NOT NULL,
        cost REAL NOT NULL,
        item_type TEXT NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders(id)
    )"""
    )

    # Миграции структуры
    try:
        check_table_structure(cursor, 'order_items', {'length_meters': 'REAL'})
        cursor.connection.commit()
    except sqlite3.Error:
        cursor.connection.rollback()

    conn.close()