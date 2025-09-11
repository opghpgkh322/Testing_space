import sqlite3
from contextlib import contextmanager


class MaterialService:
    """Сервис для работы с материалами"""

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

    def get_all_materials(self):
        """Получить все материалы"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, type, price FROM materials ORDER BY name')
            return cursor.fetchall()

    def get_material_by_id(self, material_id):
        """Получить материал по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, type, price, unit FROM materials WHERE id = ?', (material_id,))
            return cursor.fetchone()

    def add_material(self, name, material_type, price, unit):
        """Добавить новый материал"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO materials (name, type, price, unit) VALUES (?, ?, ?, ?)",
                           (name, material_type, price, unit))
            conn.commit()
            return cursor.lastrowid

    def update_material(self, material_id, name, material_type, price, unit):
        """Обновить материал"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE materials SET name = ?, type = ?, price = ?, unit = ? WHERE id = ?",
                           (name, material_type, price, unit, material_id))
            conn.commit()
            return cursor.rowcount

    def delete_material(self, material_id):
        """Удалить материал"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM materials WHERE id = ?", (material_id,))
            conn.commit()
            return cursor.rowcount

    def material_exists(self, name, exclude_id=None):
        """Проверить существование материала с данным названием"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if exclude_id:
                cursor.execute("SELECT id FROM materials WHERE name = ? AND id != ?", (name, exclude_id))
            else:
                cursor.execute("SELECT id FROM materials WHERE name = ?", (name,))
            return cursor.fetchone() is not None

    def get_products_using_material(self, material_id):
        """Получить список изделий, использующих данный материал"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT product_id FROM product_composition WHERE material_id = ?", (material_id,))
            return [row[0] for row in cursor.fetchall()]

    def get_stages_using_material(self, material_id):
        """Получить список этапов, использующих данный материал"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT stage_id FROM stage_materials WHERE material_id = ?", (material_id,))
            return [row[0] for row in cursor.fetchall()]

    def recalculate_products_cost(self, product_ids):
        """Пересчитать себестоимость изделий"""
        if not product_ids:
            return

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for product_id in product_ids:
                cursor.execute("""
                    SELECT SUM(
                        CASE 
                            WHEN m.type = 'Пиломатериал' AND pc.length IS NOT NULL 
                            THEN m.price * pc.quantity * pc.length
                            ELSE m.price * pc.quantity
                        END
                    ) 
                    FROM product_composition pc
                    JOIN materials m ON pc.material_id = m.id
                    WHERE pc.product_id = ?
                """, (product_id,))

                result = cursor.fetchone()
                total_cost = result[0] if result[0] is not None else 0
                cursor.execute("UPDATE products SET cost = ? WHERE id = ?", (total_cost, product_id))
            conn.commit()

    def recalculate_stages_cost(self, stage_ids):
        """Пересчитать себестоимость этапов"""
        if not stage_ids:
            return

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for stage_id in stage_ids:
                # Стоимость изделий в этапе
                cursor.execute("""
                    SELECT SUM(p.cost * sp.quantity) 
                    FROM stage_products sp
                    JOIN products p ON sp.product_id = p.id
                    WHERE sp.stage_id = ? AND sp.part = 'meter'
                """, (stage_id,))
                products_cost = cursor.fetchone()[0] or 0

                # Стоимость материалов в этапе
                cursor.execute("""
                    SELECT sm.quantity, sm.length, m.price, m.type
                    FROM stage_materials sm
                    JOIN materials m ON sm.material_id = m.id
                    WHERE sm.stage_id = ? AND sm.part = 'meter'
                """, (stage_id,))

                materials_cost = 0
                for quantity, length, price, material_type in cursor.fetchall():
                    if material_type == "Пиломатериал" and length:
                        materials_cost += price * quantity * length
                    else:
                        materials_cost += price * quantity

                total_cost = products_cost + materials_cost
                cursor.execute("UPDATE stages SET cost = ? WHERE id = ?", (total_cost, stage_id))
            conn.commit()

    def get_materials_by_type(self, material_type):
        """Получить материалы по типу"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, type, price FROM materials WHERE type = ? ORDER BY name', (material_type,))
            return cursor.fetchall()

    def get_material_usage_summary(self, material_id):
        """Получить сводку использования материала"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Использование в изделиях
            cursor.execute("""
                SELECT p.name, pc.quantity, pc.length
                FROM product_composition pc
                JOIN products p ON pc.product_id = p.id
                WHERE pc.material_id = ?
                ORDER BY p.name
            """, (material_id,))
            products = cursor.fetchall()

            # Использование в этапах
            cursor.execute("""
                SELECT s.name, sm.part, sm.quantity, sm.length
                FROM stage_materials sm
                JOIN stages s ON sm.stage_id = s.id
                WHERE sm.material_id = ?
                ORDER BY s.name, sm.part
            """, (material_id,))
            stages = cursor.fetchall()

            # Остатки на складе
            cursor.execute("""
                SELECT w.length, w.quantity
                FROM warehouse w
                WHERE w.material_id = ?
                ORDER BY w.length DESC
            """, (material_id,))
            warehouse = cursor.fetchall()

            return {
                'products': products,
                'stages': stages,
                'warehouse': warehouse
            }