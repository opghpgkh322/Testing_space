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
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    check_table_structure(cursor, "orders", {
        "pdf_filename": "TEXT"
    })
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
                            total_cost REAL NOT NULL,
                            instructions TEXT)''')

    # Таблица позиций заказа (ОБНОВЛЕНО)
    cursor.execute('''CREATE TABLE IF NOT EXISTS order_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        order_id INTEGER NOT NULL,
                        product_id INTEGER NOT NULL,
                        quantity INTEGER NOT NULL,
                        product_name TEXT NOT NULL,
                        cost REAL NOT NULL,
                        FOREIGN KEY (order_id) REFERENCES orders(id),
                        FOREIGN KEY (product_id) REFERENCES products(id))''')

    conn.commit()

    # Проверяем и добавляем столбцы, если они отсутствуют
    try:
        # Для orders
        check_table_structure(cursor, "orders", {
            "total_cost": "REAL NOT NULL DEFAULT 0.0"
        })
        cursor.execute("PRAGMA table_info(orders)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'total_cost' not in columns:
            cursor.execute("ALTER TABLE orders ADD COLUMN total_cost REAL NOT NULL DEFAULT 0.0")

        cursor.execute("PRAGMA table_info(orders)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'instructions' not in columns:
            cursor.execute("ALTER TABLE orders ADD COLUMN instructions TEXT")
        conn.commit()
    except sqlite3.Error as e:
        print(f"Ошибка при обновлении таблицы orders: {e}")

        # Для order_items
        check_table_structure(cursor, "order_items", {
            "product_name": "TEXT NOT NULL DEFAULT ''",
            "cost": "REAL NOT NULL DEFAULT 0.0"
        })
        cursor.execute("PRAGMA table_info(order_items)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'product_name' not in columns:
            cursor.execute("ALTER TABLE order_items ADD COLUMN product_name TEXT NOT NULL DEFAULT ''")
        if 'cost' not in columns:
            cursor.execute("ALTER TABLE order_items ADD COLUMN cost REAL NOT NULL DEFAULT 0.0")

        conn.commit()
    except sqlite3.Error as e:
        print(f"Ошибка при обновлении таблиц: {e}")

    conn.close()