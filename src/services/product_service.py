import sqlite3
from contextlib import contextmanager


class ProductService:
    """Сервис для работы с изделиями"""

    def __init__(self, db_path):
        self.db_path = db_path

    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для работы с базой данных"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def get_all_products(self):
        """Получить все изделия"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, cost FROM products ORDER BY name')
            return cursor.fetchall()

    def get_product_by_id(self, product_id):
        """Получить изделие по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, cost FROM products WHERE id = ?', (product_id,))
            return cursor.fetchone()

    def add_product(self, name):
        """Добавить новое изделие"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO products (name, cost) VALUES (?, 0.0)", (name,))
            conn.commit()
            return cursor.lastrowid

    def update_product(self, product_id, name):
        """Обновить название изделия"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE products SET name = ? WHERE id = ?", (name, product_id))
            conn.commit()
            return cursor.rowcount

    def delete_product(self, product_id):
        """Удалить изделие и его состав"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Удаляем состав изделия
            cursor.execute("DELETE FROM product_composition WHERE product_id = ?", (product_id,))
            # Удаляем изделие из этапов
            cursor.execute("DELETE FROM stage_products WHERE product_id = ?", (product_id,))
            # Удаляем само изделие
            cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
            conn.commit()
            return cursor.rowcount

    def product_exists(self, name, exclude_id=None):
        """Проверить существование изделия с данным названием"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if exclude_id:
                cursor.execute("SELECT id FROM products WHERE name = ? AND id != ?", (name, exclude_id))
            else:
                cursor.execute("SELECT id FROM products WHERE name = ?", (name,))
            return cursor.fetchone() is not None

    def get_product_composition(self, product_id):
        """Получить состав изделия"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pc.id, m.name, m.type, pc.quantity, pc.length, m.price,
                       CASE 
                           WHEN m.type = 'Пиломатериал' AND pc.length IS NOT NULL 
                           THEN m.price * pc.quantity * pc.length
                           ELSE m.price * pc.quantity
                       END as total_cost
                FROM product_composition pc
                JOIN materials m ON pc.material_id = m.id
                WHERE pc.product_id = ?
                ORDER BY m.name
            """, (product_id,))
            return cursor.fetchall()

    def add_material_to_product(self, product_id, material_id, quantity, length=None):
        """Добавить материал в состав изделия"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO product_composition (product_id, material_id, quantity, length) 
                VALUES (?, ?, ?, ?)
            """, (product_id, material_id, quantity, length))
            conn.commit()
            return cursor.lastrowid

    def update_product_composition_item(self, composition_id, quantity, length=None):
        """Обновить элемент состава изделия"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE product_composition 
                SET quantity = ?, length = ? 
                WHERE id = ?
            """, (quantity, length, composition_id))
            conn.commit()
            return cursor.rowcount

    def remove_material_from_product(self, composition_id):
        """Удалить материал из состава изделия"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM product_composition WHERE id = ?", (composition_id,))
            conn.commit()
            return cursor.rowcount

    def calculate_product_cost(self, product_id):
        """Рассчитать и обновить себестоимость изделия"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(
                    CASE 
                        WHEN m.type = 'Пиломатериал' AND pc.length IS NOT NULL 
                        THEN m.price * pc.quantity * pc.length
                        ELSE m.price * pc.quantity
                    END
                ) as total_cost
                FROM product_composition pc
                JOIN materials m ON pc.material_id = m.id
                WHERE pc.product_id = ?
            """, (product_id,))

            result = cursor.fetchone()
            total_cost = result[0] if result[0] is not None else 0

            cursor.execute("UPDATE products SET cost = ? WHERE id = ?", (total_cost, product_id))
            conn.commit()
            return total_cost

    def recalculate_all_products_cost(self):
        """Пересчитать себестоимость всех изделий"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM products")
            product_ids = [row[0] for row in cursor.fetchall()]

            for product_id in product_ids:
                self.calculate_product_cost(product_id)

    def get_products_using_material(self, material_id):
        """Получить изделия, использующие определенный материал"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT p.id, p.name, p.cost
                FROM products p
                JOIN product_composition pc ON p.id = pc.product_id
                WHERE pc.material_id = ?
                ORDER BY p.name
            """, (material_id,))
            return cursor.fetchall()

    def get_product_cost_breakdown(self, product_id):
        """Получить детализацию стоимости изделия по материалам"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    m.name,
                    m.type,
                    pc.quantity,
                    pc.length,
                    m.price,
                    CASE 
                        WHEN m.type = 'Пиломатериал' AND pc.length IS NOT NULL 
                        THEN m.price * pc.quantity * pc.length
                        ELSE m.price * pc.quantity
                    END as material_cost,
                    CASE 
                        WHEN m.type = 'Пиломатериал' AND pc.length IS NOT NULL 
                        THEN ROUND((m.price * pc.quantity * pc.length) * 100.0 / 
                             (SELECT SUM(
                                 CASE 
                                     WHEN m2.type = 'Пиломатериал' AND pc2.length IS NOT NULL 
                                     THEN m2.price * pc2.quantity * pc2.length
                                     ELSE m2.price * pc2.quantity
                                 END
                             ) FROM product_composition pc2 
                             JOIN materials m2 ON pc2.material_id = m2.id 
                             WHERE pc2.product_id = ?), 2)
                        ELSE ROUND((m.price * pc.quantity) * 100.0 / 
                             (SELECT SUM(
                                 CASE 
                                     WHEN m2.type = 'Пиломатериал' AND pc2.length IS NOT NULL 
                                     THEN m2.price * pc2.quantity * pc2.length
                                     ELSE m2.price * pc2.quantity
                                 END
                             ) FROM product_composition pc2 
                             JOIN materials m2 ON pc2.material_id = m2.id 
                             WHERE pc2.product_id = ?), 2)
                    END as cost_percentage
                FROM product_composition pc
                JOIN materials m ON pc.material_id = m.id
                WHERE pc.product_id = ?
                ORDER BY material_cost DESC
            """, (product_id, product_id, product_id))
            return cursor.fetchall()

    def duplicate_product(self, product_id, new_name):
        """Создать копию изделия с новым именем"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Создаем новое изделие
            cursor.execute("INSERT INTO products (name, cost) VALUES (?, 0.0)", (new_name,))
            new_product_id = cursor.lastrowid

            # Копируем состав
            cursor.execute("""
                INSERT INTO product_composition (product_id, material_id, quantity, length)
                SELECT ?, material_id, quantity, length
                FROM product_composition
                WHERE product_id = ?
            """, (new_product_id, product_id))

            conn.commit()

            # Рассчитываем стоимость нового изделия
            self.calculate_product_cost(new_product_id)

            return new_product_id

    def get_products_for_stages(self):
        """Получить список изделий для использования в этапах"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, cost FROM products ORDER BY name')
            return cursor.fetchall()

    def get_most_expensive_products(self, limit=10):
        """Получить самые дорогие изделия"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, cost 
                FROM products 
                WHERE cost > 0
                ORDER BY cost DESC 
                LIMIT ?
            """, (limit,))
            return cursor.fetchall()

    def get_products_without_materials(self):
        """Получить изделия без материалов в составе"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.id, p.name, p.cost
                FROM products p
                LEFT JOIN product_composition pc ON p.id = pc.product_id
                WHERE pc.product_id IS NULL
                ORDER BY p.name
            """)
            return cursor.fetchall()