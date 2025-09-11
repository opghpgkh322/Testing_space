import sqlite3
import os
from contextlib import contextmanager


def create_database(db_path):
    """Создание базы данных со всеми необходимыми таблицами"""

    # Создаем директорию для базы данных если не существует
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Таблица материалов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL CHECK (type IN ('Пиломатериал', 'Метиз')),
                price REAL NOT NULL CHECK (price >= 0),
                unit TEXT NOT NULL DEFAULT 'м',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица складских остатков
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warehouse (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id INTEGER NOT NULL,
                length REAL NOT NULL DEFAULT 0 CHECK (length >= 0),
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (material_id) REFERENCES materials (id) ON DELETE CASCADE
            )
        ''')

        # Таблица изделий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                cost REAL NOT NULL DEFAULT 0 CHECK (cost >= 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица составов изделий (связь изделие-материал)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_composition (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                material_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                length REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
                FOREIGN KEY (material_id) REFERENCES materials (id) ON DELETE CASCADE
            )
        ''')

        # Таблица этапов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                cost REAL NOT NULL DEFAULT 0 CHECK (cost >= 0),
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица изделий в этапах
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stage_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stage_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                part TEXT NOT NULL DEFAULT 'meter' CHECK (part IN ('start', 'meter', 'end')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (stage_id) REFERENCES stages (id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
            )
        ''')

        # Таблица материалов в этапах (прямое использование)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stage_materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stage_id INTEGER NOT NULL,
                material_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                length REAL,
                part TEXT NOT NULL DEFAULT 'meter' CHECK (part IN ('start', 'meter', 'end')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (stage_id) REFERENCES stages (id) ON DELETE CASCADE,
                FOREIGN KEY (material_id) REFERENCES materials (id) ON DELETE CASCADE
            )
        ''')

        # Таблица заказов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                total_cost REAL NOT NULL CHECK (total_cost >= 0),
                instructions TEXT,
                pdf_filename TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица позиций заказов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER,
                stage_id INTEGER,
                quantity INTEGER,
                length_meters REAL,
                product_name TEXT NOT NULL,
                cost REAL NOT NULL CHECK (cost >= 0),
                item_type TEXT NOT NULL CHECK (item_type IN ('product', 'stage')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE SET NULL,
                FOREIGN KEY (stage_id) REFERENCES stages (id) ON DELETE SET NULL,
                CHECK (
                    (item_type = 'product' AND product_id IS NOT NULL AND stage_id IS NULL AND quantity IS NOT NULL AND length_meters IS NULL) OR
                    (item_type = 'stage' AND stage_id IS NOT NULL AND product_id IS NULL AND length_meters IS NOT NULL AND quantity IS NULL)
                )
            )
        ''')

        # Создание индексов для улучшения производительности
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_materials_name ON materials (name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_materials_type ON materials (type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_warehouse_material ON warehouse (material_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_name ON products (name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_product_composition_product ON product_composition (product_id)')
        cursor.execute(
            'CREATE INDEX IF NOT EXISTS idx_product_composition_material ON product_composition (material_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stages_name ON stages (name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stage_products_stage ON stage_products (stage_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stage_products_product ON stage_products (product_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stage_materials_stage ON stage_materials (stage_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stage_materials_material ON stage_materials (material_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_date ON orders (order_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items (order_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_items_type ON order_items (item_type)')

        # Триггеры для автоматического обновления updated_at
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS update_materials_timestamp 
            AFTER UPDATE ON materials
            FOR EACH ROW
            BEGIN
                UPDATE materials SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        ''')

        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS update_warehouse_timestamp 
            AFTER UPDATE ON warehouse
            FOR EACH ROW
            BEGIN
                UPDATE warehouse SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        ''')

        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS update_products_timestamp 
            AFTER UPDATE ON products
            FOR EACH ROW
            BEGIN
                UPDATE products SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        ''')

        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS update_stages_timestamp 
            AFTER UPDATE ON stages
            FOR EACH ROW
            BEGIN
                UPDATE stages SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        ''')

        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS update_orders_timestamp 
            AFTER UPDATE ON orders
            FOR EACH ROW
            BEGIN
                UPDATE orders SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        ''')

        conn.commit()
        print("✅ База данных создана успешно")

    except Exception as e:
        conn.rollback()
        raise Exception(f"Ошибка создания базы данных: {str(e)}")
    finally:
        conn.close()


@contextmanager
def get_db_connection(db_path):
    """Контекстный менеджер для безопасной работы с базой данных"""
    conn = sqlite3.connect(db_path)
    try:
        # Включаем поддержку внешних ключей
        conn.execute("PRAGMA foreign_keys = ON")
        # Устанавливаем режим WAL для лучшей производительности при конкурентном доступе
        conn.execute("PRAGMA journal_mode = WAL")
        yield conn
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def check_database_integrity(db_path):
    """Проверка целостности базы данных"""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            # Проверка целостности
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()[0]

            if integrity_result != "ok":
                raise Exception(f"Нарушение целостности базы данных: {integrity_result}")

            # Проверка внешних ключей
            cursor.execute("PRAGMA foreign_key_check")
            fk_violations = cursor.fetchall()

            if fk_violations:
                raise Exception(f"Нарушения внешних ключей: {fk_violations}")

            # Получение информации о таблицах
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            required_tables = [
                'materials', 'warehouse', 'products', 'product_composition',
                'stages', 'stage_products', 'stage_materials', 'orders', 'order_items'
            ]

            missing_tables = set(required_tables) - set(tables)
            if missing_tables:
                raise Exception(f"Отсутствуют таблицы: {missing_tables}")

            return {
                'integrity': integrity_result,
                'tables': tables,
                'foreign_keys': 'ok',
                'status': 'healthy'
            }

    except Exception as e:
        return {
            'integrity': 'error',
            'error': str(e),
            'status': 'corrupted'
        }


def get_database_statistics(db_path):
    """Получение статистики по базе данных"""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            stats = {}

            # Статистика по таблицам
            tables = [
                ('materials', 'Материалы'),
                ('warehouse', 'Складские позиции'),
                ('products', 'Изделия'),
                ('product_composition', 'Составы изделий'),
                ('stages', 'Этапы'),
                ('stage_products', 'Изделия в этапах'),
                ('stage_materials', 'Материалы в этапах'),
                ('orders', 'Заказы'),
                ('order_items', 'Позиции заказов')
            ]

            for table_name, table_desc in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                stats[table_desc] = cursor.fetchone()[0]

            # Размер базы данных
            db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
            stats['Размер БД (МБ)'] = round(db_size / (1024 * 1024), 2)

            # Последняя активность
            cursor.execute("""
                SELECT MAX(datetime) FROM (
                    SELECT MAX(created_at) as datetime FROM materials
                    UNION ALL
                    SELECT MAX(created_at) as datetime FROM orders
                    UNION ALL
                    SELECT MAX(created_at) as datetime FROM warehouse
                )
            """)
            last_activity = cursor.fetchone()[0]
            stats['Последняя активность'] = last_activity

            return stats

    except Exception as e:
        return {'error': str(e)}


def vacuum_database(db_path):
    """Оптимизация базы данных (освобождение места, дефрагментация)"""
    try:
        conn = sqlite3.connect(db_path)

        # VACUUM нельзя выполнить в транзакции
        conn.execute("VACUUM")

        # Анализ для оптимизации запросов
        conn.execute("ANALYZE")

        conn.close()
        print("✅ Оптимизация базы данных завершена")
        return True

    except Exception as e:
        print(f"❌ Ошибка оптимизации базы данных: {str(e)}")
        return False


def backup_database(db_path, backup_path=None):
    """Создание резервной копии базы данных"""
    try:
        import shutil
        from datetime import datetime

        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            db_dir = os.path.dirname(db_path)
            backup_path = os.path.join(db_dir, f"database_backup_{timestamp}.db")

        shutil.copy2(db_path, backup_path)
        print(f"✅ Резервная копия создана: {backup_path}")
        return backup_path

    except Exception as e:
        print(f"❌ Ошибка создания резервной копии: {str(e)}")
        return None


def restore_database(backup_path, db_path):
    """Восстановление базы данных из резервной копии"""
    try:
        import shutil

        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Файл резервной копии не найден: {backup_path}")

        # Проверяем целостность резервной копии
        check_result = check_database_integrity(backup_path)
        if check_result['status'] != 'healthy':
            raise Exception(f"Резервная копия повреждена: {check_result.get('error', 'Unknown error')}")

        # Создаем резервную копию текущей БД
        current_backup = backup_database(db_path)

        # Восстанавливаем из резервной копии
        shutil.copy2(backup_path, db_path)

        print(f"✅ База данных восстановлена из: {backup_path}")
        print(f"✅ Текущая БД сохранена как: {current_backup}")
        return True

    except Exception as e:
        print(f"❌ Ошибка восстановления базы данных: {str(e)}")
        return False


def migrate_database(db_path, target_version=None):
    """Миграция базы данных (для будущих версий)"""
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()

            # Проверяем текущую версию схемы
            cursor.execute("PRAGMA user_version")
            current_version = cursor.fetchone()[0]

            print(f"Текущая версия схемы: {current_version}")

            # Здесь можно добавить логику миграций для будущих версий
            # if current_version < 1:
            #     # Миграция к версии 1
            #     pass

            print("✅ Миграция базы данных завершена")
            return True

    except Exception as e:
        print(f"❌ Ошибка миграции базы данных: {str(e)}")
        return False