# database.py - ОКОНЧАТЕЛЬНО ИСПРАВЛЕННАЯ ВЕРСИЯ
import sqlite3
import os


def check_table_structure(cursor, table_name, expected_columns):
    """Проверяет структуру таблицы и добавляет отсутствующие столбцы"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = {col[1] for col in cursor.fetchall()}

    for column, col_type in expected_columns.items():
        if column not in existing_columns:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column} {col_type}")


def create_database(db_path):
    """Создает базу данных и таблицы с поддержкой этапов"""
    data_dir = os.path.dirname(db_path)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Существующие таблицы
    cursor.execute("""CREATE TABLE IF NOT EXISTS materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        type TEXT NOT NULL CHECK(type IN ("Пиломатериал", "Метиз")),
        price REAL NOT NULL,
        unit TEXT NOT NULL)""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS warehouse (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        material_id INTEGER NOT NULL,
        length REAL NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY (material_id) REFERENCES materials(id))""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        cost REAL NOT NULL DEFAULT 0.0)""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS product_composition (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        material_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        length REAL,
        FOREIGN KEY (product_id) REFERENCES products(id),
        FOREIGN KEY (material_id) REFERENCES materials(id))""")

    # НОВЫЕ ТАБЛИЦЫ ДЛЯ ЭТАПОВ
    cursor.execute("""CREATE TABLE IF NOT EXISTS stages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        cost REAL NOT NULL DEFAULT 0.0,
        description TEXT)""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS stage_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stage_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        FOREIGN KEY (stage_id) REFERENCES stages(id),
        FOREIGN KEY (product_id) REFERENCES products(id))""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS stage_materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stage_id INTEGER NOT NULL,
        material_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        length REAL,
        FOREIGN KEY (stage_id) REFERENCES stages(id),
        FOREIGN KEY (material_id) REFERENCES materials(id))""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        total_cost REAL NOT NULL DEFAULT 0.0,
        instructions TEXT,
        pdf_filename TEXT)""")

    # ИСПРАВЛЕНИЕ 1: Пересоздаем таблицу order_items с правильной схемой
    # Сначала проверяем, есть ли таблица
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='order_items'")
    table_exists = cursor.fetchone()

    if table_exists:
        # Сохраняем существующие данные
        cursor.execute("SELECT * FROM order_items")
        existing_data = cursor.fetchall()

        # Получаем структуру старой таблицы
        cursor.execute("PRAGMA table_info(order_items)")
        old_columns = [col[1] for col in cursor.fetchall()]

        # Удаляем старую таблицу
        cursor.execute("DROP TABLE order_items")

    # Создаем новую таблицу с правильной схемой
    cursor.execute("""CREATE TABLE order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER,
        stage_id INTEGER,
        quantity INTEGER NOT NULL,
        product_name TEXT NOT NULL DEFAULT '',
        cost REAL NOT NULL DEFAULT 0.0,
        item_type TEXT NOT NULL DEFAULT 'product' CHECK(item_type IN ('product', 'stage')),
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (product_id) REFERENCES products(id),
        FOREIGN KEY (stage_id) REFERENCES stages(id))""")

    # Восстанавливаем данные если были
    if table_exists and existing_data:
        for row in existing_data:
            # Адаптируем старые данные к новой структуре
            if len(row) >= 7:  # Если есть все основные поля
                cursor.execute("""INSERT INTO order_items 
                                (id, order_id, product_id, quantity, product_name, cost, item_type)
                                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                             (row[0], row[1], row[2], row[4], row[5], row[6], 'product'))

    conn.commit()

    # Проверяем и добавляем отсутствующие столбцы для других таблиц
    try:
        check_table_structure(cursor, "orders", {
            "pdf_filename": "TEXT"
        })
        conn.commit()
    except sqlite3.Error as e:
        print(f"Ошибка при обновлении таблиц: {e}")
        conn.rollback()
    finally:
        conn.close()
