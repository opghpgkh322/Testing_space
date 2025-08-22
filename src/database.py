# database.py
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
    """Создает базу данных и таблицы"""
    # Создаем папку если не существует
    data_dir = os.path.dirname(db_path)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Таблица материалов
    cursor.execute('''CREATE TABLE IF NOT EXISTS materials (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        type TEXT NOT NULL CHECK(type IN ('Пиломатериал', 'Метиз')),
                        price REAL NOT NULL,
                        unit TEXT NOT NULL)''')

    # Таблица склада
    cursor.execute('''CREATE TABLE IF NOT EXISTS warehouse (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        material_id INTEGER NOT NULL,
                        length REAL NOT NULL,
                        quantity INTEGER NOT NULL DEFAULT 1,
                        FOREIGN KEY (material_id) REFERENCES materials(id))''')

    # Таблица изделий
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        cost REAL NOT NULL DEFAULT 0.0)''')

    # Таблица состава изделий
    cursor.execute('''CREATE TABLE IF NOT EXISTS product_composition (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_id INTEGER NOT NULL,
                        material_id INTEGER NOT NULL,
                        quantity INTEGER NOT NULL,
                        length REAL,
                        FOREIGN KEY (product_id) REFERENCES products(id),
                        FOREIGN KEY (material_id) REFERENCES materials(id))''')

    # Таблица заказов
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        total_cost REAL NOT NULL DEFAULT 0.0,
                        instructions TEXT,
                        pdf_filename TEXT)''')

    # Таблица позиций заказа
    cursor.execute('''CREATE TABLE IF NOT EXISTS order_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id INTEGER NOT NULL,
                        product_id INTEGER NOT NULL,
                        quantity INTEGER NOT NULL,
                        product_name TEXT NOT NULL DEFAULT '',
                        cost REAL NOT NULL DEFAULT 0.0,
                        FOREIGN KEY (order_id) REFERENCES orders(id),
                        FOREIGN KEY (product_id) REFERENCES products(id))''')

    conn.commit()

    # Проверяем и добавляем отсутствующие столбцы
    try:
        # Для orders
        check_table_structure(cursor, "orders", {
            "pdf_filename": "TEXT"
        })

        # Для order_items
        check_table_structure(cursor, "order_items", {
            "product_name": "TEXT NOT NULL DEFAULT ''",
            "cost": "REAL NOT NULL DEFAULT 0.0"
        })

        conn.commit()
    except sqlite3.Error as e:
        print(f"Ошибка при обновлении таблиц: {e}")
        conn.rollback()
    finally:
        conn.close()