import sqlite3
import os
from datetime import datetime
from database import create_database, get_db_connection


def initialize_database(db_path):
    """Инициализация базы данных с базовыми данными"""

    print("🔧 Инициализация базы данных...")

    # Сначала создаем структуру базы данных
    create_database(db_path)

    # Затем добавляем начальные данные
    add_initial_materials(db_path)
    add_sample_warehouse_items(db_path)
    add_sample_products(db_path)
    add_sample_stages(db_path)

    print("✅ Инициализация базы данных завершена")


def add_initial_materials(db_path):
    """Добавление базового набора материалов"""

    materials = [
        # Пиломатериалы
        ("Брус 100x100", "Пиломатериал", 85.00, "м"),
        ("Брус 150x150", "Пиломатериал", 120.00, "м"),
        ("Доска 25x150", "Пиломатериал", 45.00, "м"),
        ("Доска 40x150", "Пиломатериал", 65.00, "м"),
        ("Доска 50x200", "Пиломатериал", 85.00, "м"),
        ("Рейка 20x40", "Пиломатериал", 15.00, "м"),
        ("Рейка 25x50", "Пиломатериал", 18.00, "м"),
        ("Брусок 40x40", "Пиломатериал", 25.00, "м"),
        ("Брусок 50x50", "Пиломатериал", 35.00, "м"),

        # Метизы
        ("Шуруп 4x60", "Метиз", 2.50, "шт"),
        ("Шуруп 5x80", "Метиз", 3.20, "шт"),
        ("Шуруп 6x100", "Метиз", 4.50, "шт"),
        ("Болт М8x100", "Метиз", 25.00, "шт"),
        ("Болт М10x120", "Метиз", 35.00, "шт"),
        ("Болт М12x150", "Метиз", 45.00, "шт"),
        ("Гайка М8", "Метиз", 3.00, "шт"),
        ("Гайка М10", "Метиз", 4.50, "шт"),
        ("Гайка М12", "Метиз", 6.00, "шт"),
        ("Шайба М8", "Метиз", 1.50, "шт"),
        ("Шайба М10", "Метиз", 2.00, "шт"),
        ("Шайба М12", "Метиз", 2.50, "шт"),
        ("Карабин", "Метиз", 450.00, "шт"),
        ("Зажим троса", "Метиз", 180.00, "шт"),
        ("Талреп", "Метиз", 850.00, "шт"),
        ("Трос 8мм", "Пиломатериал", 65.00, "м"),  # Трос считаем как пиломатериал для расчета длины
    ]

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            for name, material_type, price, unit in materials:
                try:
                    cursor.execute(
                        "INSERT OR IGNORE INTO materials (name, type, price, unit) VALUES (?, ?, ?, ?)",
                        (name, material_type, price, unit)
                    )
                except sqlite3.IntegrityError:
                    # Материал уже существует
                    pass

            conn.commit()
            print(f"✅ Добавлено материалов: {len(materials)}")

    except Exception as e:
        print(f"❌ Ошибка добавления материалов: {str(e)}")


def add_sample_warehouse_items(db_path):
    """Добавление примерных остатков на склад"""

    # Остатки: (material_name, length, quantity)
    warehouse_items = [
        # Пиломатериалы - остатки досок разной длины
        ("Брус 100x100", 6.0, 15),
        ("Брус 100x100", 4.5, 8),
        ("Брус 100x100", 3.0, 12),
        ("Брус 150x150", 6.0, 6),
        ("Брус 150x150", 4.0, 4),
        ("Доска 25x150", 6.0, 25),
        ("Доска 25x150", 4.0, 18),
        ("Доска 25x150", 3.0, 12),
        ("Доска 40x150", 6.0, 20),
        ("Доска 40x150", 4.5, 10),
        ("Доска 50x200", 6.0, 8),
        ("Рейка 20x40", 3.0, 30),
        ("Рейка 25x50", 3.0, 25),
        ("Брусок 40x40", 4.0, 20),
        ("Брусок 50x50", 4.0, 15),
        ("Трос 8мм", 50.0, 2),  # Трос в бухтах

        # Метизы - количество штук
        ("Шуруп 4x60", 0, 500),
        ("Шуруп 5x80", 0, 300),
        ("Шуруп 6x100", 0, 200),
        ("Болт М8x100", 0, 100),
        ("Болт М10x120", 0, 80),
        ("Болт М12x150", 0, 50),
        ("Гайка М8", 0, 120),
        ("Гайка М10", 0, 100),
        ("Гайка М12", 0, 60),
        ("Шайба М8", 0, 150),
        ("Шайба М10", 0, 120),
        ("Шайба М12", 0, 80),
        ("Карабин", 0, 25),
        ("Зажим троса", 0, 40),
        ("Талреп", 0, 15),
    ]

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            for material_name, length, quantity in warehouse_items:
                # Получаем ID материала
                cursor.execute("SELECT id FROM materials WHERE name = ?", (material_name,))
                result = cursor.fetchone()

                if result:
                    material_id = result[0]
                    cursor.execute(
                        "INSERT INTO warehouse (material_id, length, quantity) VALUES (?, ?, ?)",
                        (material_id, length, quantity)
                    )

            conn.commit()
            print(f"✅ Добавлено складских позиций: {len(warehouse_items)}")

    except Exception as e:
        print(f"❌ Ошибка добавления остатков на склад: {str(e)}")


def add_sample_products(db_path):
    """Добавление примерных изделий с составами"""

    products_data = [
        # (product_name, composition)
        ("Островок базовый", [
            ("Брус 100x100", 4, 2.5),  # 4 шт по 2.5м
            ("Доска 40x150", 8, 1.5),  # 8 шт по 1.5м
            ("Шуруп 5x80", 32, None),  # 32 штуки
            ("Болт М10x120", 8, None),  # 8 штук
            ("Гайка М10", 8, None),  # 8 штук
            ("Шайба М10", 16, None),  # 16 штук
        ]),

        ("Переход простой", [
            ("Брус 100x100", 2, 1.2),  # 2 шт по 1.2м
            ("Доска 25x150", 4, 0.8),  # 4 шт по 0.8м
            ("Шуруп 4x60", 16, None),  # 16 штук
            ("Болт М8x100", 4, None),  # 4 штуки
            ("Гайка М8", 4, None),  # 4 штуки
            ("Шайба М8", 8, None),  # 8 штук
        ]),

        ("Платформа угловая", [
            ("Брус 150x150", 2, 2.0),  # 2 шт по 2.0м
            ("Доска 50x200", 6, 1.2),  # 6 шт по 1.2м
            ("Брусок 50x50", 4, 0.6),  # 4 шт по 0.6м
            ("Шуруп 6x100", 24, None),  # 24 штуки
            ("Болт М12x150", 6, None),  # 6 штук
            ("Гайка М12", 6, None),  # 6 штук
            ("Шайба М12", 12, None),  # 12 штук
        ]),
    ]

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            for product_name, composition in products_data:
                # Добавляем изделие
                cursor.execute(
                    "INSERT OR IGNORE INTO products (name, cost) VALUES (?, ?)",
                    (product_name, 0)
                )

                # Получаем ID изделия
                cursor.execute("SELECT id FROM products WHERE name = ?", (product_name,))
                product_id = cursor.fetchone()[0]

                # Добавляем состав
                for material_name, quantity, length in composition:
                    cursor.execute("SELECT id FROM materials WHERE name = ?", (material_name,))
                    material_result = cursor.fetchone()

                    if material_result:
                        material_id = material_result[0]
                        cursor.execute(
                            "INSERT INTO product_composition (product_id, material_id, quantity, length) VALUES (?, ?, ?, ?)",
                            (product_id, material_id, quantity, length)
                        )

            conn.commit()
            print(f"✅ Добавлено изделий: {len(products_data)}")

    except Exception as e:
        print(f"❌ Ошибка добавления изделий: {str(e)}")


def add_sample_stages(db_path):
    """Добавление примерных этапов работ"""

    stages_data = [
        # (stage_name, description, products_list, materials_list)
        ("Установка опор",
         "Установка основных несущих опор конструкции",
         [],  # Изделия не используются
         [  # Материалы напрямую
             ("Брус 150x150", "start", 2, 2.5),  # Начальный крепеж: 2 шт по 2.5м
             ("Брус 100x100", "meter", 1, 1.0),  # На каждый метр: 1 шт по 1м
             ("Болт М12x150", "start", 4, None),  # Начальный крепеж: 4 шт
             ("Болт М10x120", "meter", 2, None),  # На каждый метр: 2 шт
             ("Гайка М12", "start", 4, None),  # Начальный крепеж: 4 шт
             ("Гайка М10", "meter", 2, None),  # На каждый метр: 2 шт
             ("Шайба М12", "start", 8, None),  # Начальный крепеж: 8 шт
             ("Шайба М10", "meter", 4, None),  # На каждый метр: 4 шт
         ]),

        ("Натяжение троса",
         "Установка и натяжение несущих тросов между опорами",
         [],
         [
             ("Карабин", "start", 2, None),  # Начальный крепеж: 2 шт
             ("Карабин", "end", 2, None),  # Конечный крепеж: 2 шт
             ("Талреп", "start", 1, None),  # Начальный крепеж: 1 шт
             ("Трос 8мм", "meter", 1, 1.0),  # На каждый метр: 1м троса
             ("Зажим троса", "meter", 2, None),  # На каждый метр: 2 зажима
         ]),

        ("Настил переходов",
         "Укладка досок настила на переходных участках",
         [
             ("Переход простой", "meter", 1, "meter"),  # На каждый метр: 1 переход
         ],
         [
             ("Доска 40x150", "meter", 3, 1.0),  # На каждый метр: 3 доски по 1м
             ("Шуруп 5x80", "meter", 12, None),  # На каждый метр: 12 шурупов
         ]),
    ]

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            for stage_name, description, products_list, materials_list in stages_data:
                # Добавляем этап
                cursor.execute(
                    "INSERT OR IGNORE INTO stages (name, description, cost) VALUES (?, ?, ?)",
                    (stage_name, description, 0)
                )

                # Получаем ID этапа
                cursor.execute("SELECT id FROM stages WHERE name = ?", (stage_name,))
                stage_id = cursor.fetchone()[0]

                # Добавляем изделия в этап
                for product_name, part, quantity, unit in products_list:
                    cursor.execute("SELECT id FROM products WHERE name = ?", (product_name,))
                    product_result = cursor.fetchone()

                    if product_result:
                        product_id = product_result[0]
                        cursor.execute(
                            "INSERT INTO stage_products (stage_id, product_id, quantity, part) VALUES (?, ?, ?, ?)",
                            (stage_id, product_id, quantity, part)
                        )

                # Добавляем материалы в этап
                for material_name, part, quantity, length in materials_list:
                    cursor.execute("SELECT id FROM materials WHERE name = ?", (material_name,))
                    material_result = cursor.fetchone()

                    if material_result:
                        material_id = material_result[0]
                        cursor.execute(
                            "INSERT INTO stage_materials (stage_id, material_id, quantity, length, part) VALUES (?, ?, ?, ?, ?)",
                            (stage_id, material_id, quantity, length, part)
                        )

            conn.commit()
            print(f"✅ Добавлено этапов: {len(stages_data)}")

    except Exception as e:
        print(f"❌ Ошибка добавления этапов: {str(e)}")


def recalculate_all_costs(db_path):
    """Пересчет всех себестоимостей после инициализации"""

    try:
        print("🔄 Пересчет себестоимости...")

        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            # Пересчет себестоимости изделий
            cursor.execute("SELECT id FROM products")
            product_ids = [row[0] for row in cursor.fetchall()]

            for product_id in product_ids:
                # Получаем состав изделия и рассчитываем стоимость
                cursor.execute('''
                    SELECT m.price, pc.quantity, pc.length, m.type
                    FROM product_composition pc
                    JOIN materials m ON pc.material_id = m.id
                    WHERE pc.product_id = ?
                ''', (product_id,))

                total_cost = 0
                for price, quantity, length, material_type in cursor.fetchall():
                    if material_type == "Пиломатериал" and length:
                        item_cost = price * quantity * length
                    else:
                        item_cost = price * quantity
                    total_cost += item_cost

                cursor.execute(
                    "UPDATE products SET cost = ? WHERE id = ?",
                    (total_cost, product_id)
                )

            # Пересчет себестоимости этапов (упрощенно - за метр)
            cursor.execute("SELECT id FROM stages")
            stage_ids = [row[0] for row in cursor.fetchall()]

            for stage_id in stage_ids:
                # Считаем стоимость материалов на метр
                cursor.execute('''
                    SELECT m.price, sm.quantity, sm.length, sm.part, m.type
                    FROM stage_materials sm
                    JOIN materials m ON sm.material_id = m.id
                    WHERE sm.stage_id = ?
                ''', (stage_id,))

                meter_cost = 0
                for price, quantity, length, part, material_type in cursor.fetchall():
                    if part == "meter":
                        if material_type == "Пиломатериал" and length:
                            meter_cost += price * quantity * length
                        else:
                            meter_cost += price * quantity

                # Добавляем стоимость изделий на метр
                cursor.execute('''
                    SELECT p.cost, sp.quantity
                    FROM stage_products sp
                    JOIN products p ON sp.product_id = p.id
                    WHERE sp.stage_id = ? AND sp.part = 'meter'
                ''', (stage_id,))

                for product_cost, quantity in cursor.fetchall():
                    meter_cost += product_cost * quantity

                cursor.execute(
                    "UPDATE stages SET cost = ? WHERE id = ?",
                    (meter_cost, stage_id)
                )

            conn.commit()
            print("✅ Себестоимость пересчитана")

    except Exception as e:
        print(f"❌ Ошибка пересчета себестоимости: {str(e)}")


def clear_all_data(db_path):
    """Очистка всех данных из базы (для переинициализации)"""

    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            # Порядок важен из-за внешних ключей
            tables_to_clear = [
                'order_items',
                'orders',
                'stage_materials',
                'stage_products',
                'product_composition',
                'warehouse',
                'stages',
                'products',
                'materials'
            ]

            for table in tables_to_clear:
                cursor.execute(f"DELETE FROM {table}")

            # Сбрасываем счетчики автоинкремента
            for table in tables_to_clear:
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")

            conn.commit()
            print("✅ Все данные очищены")

    except Exception as e:
        print(f"❌ Ошибка очистки данных: {str(e)}")


def reset_database(db_path):
    """Полный сброс базы данных с переинициализацией"""

    print("🔄 Сброс базы данных...")

    # Удаляем файл базы данных
    if os.path.exists(db_path):
        os.remove(db_path)
        print("✅ Старая база данных удалена")

    # Создаем заново
    initialize_database(db_path)
    recalculate_all_costs(db_path)

    print("✅ База данных полностью переинициализирована")


if __name__ == "__main__":
    # При запуске файла напрямую - инициализируем базу в папке data
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, "..", "data", "database.db")
    db_path = os.path.abspath(db_path)

    print(f"Инициализация базы данных: {db_path}")

    # Спрашиваем пользователя
    if os.path.exists(db_path):
        response = input("База данных уже существует. Переинициализировать? (y/N): ")
        if response.lower() == 'y':
            reset_database(db_path)
        else:
            print("Инициализация отменена")
    else:
        initialize_database(db_path)
        recalculate_all_costs(db_path)

    print("Готово!")