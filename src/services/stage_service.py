import sqlite3
from contextlib import contextmanager
import math


class StageService:
    """Сервис для работы с этапами"""

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

    def get_all_stages(self):
        """Получить все этапы"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, cost, description FROM stages ORDER BY name')
            return cursor.fetchall()

    def get_stage_by_id(self, stage_id):
        """Получить этап по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, cost, description FROM stages WHERE id = ?', (stage_id,))
            return cursor.fetchone()

    def add_stage(self, name, description=None):
        """Добавить новый этап"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO stages (name, cost, description) VALUES (?, 0.0, ?)",
                           (name, description))
            conn.commit()
            return cursor.lastrowid

    def update_stage(self, stage_id, name, description=None):
        """Обновить этап"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE stages SET name = ?, description = ? WHERE id = ?",
                           (name, description, stage_id))
            conn.commit()
            return cursor.rowcount

    def delete_stage(self, stage_id):
        """Удалить этап и его состав"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Удаляем изделия из этапа
            cursor.execute("DELETE FROM stage_products WHERE stage_id = ?", (stage_id,))
            # Удаляем материалы из этапа
            cursor.execute("DELETE FROM stage_materials WHERE stage_id = ?", (stage_id,))
            # Удаляем сам этап
            cursor.execute("DELETE FROM stages WHERE id = ?", (stage_id,))
            conn.commit()
            return cursor.rowcount

    def stage_exists(self, name, exclude_id=None):
        """Проверить существование этапа с данным названием"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if exclude_id:
                cursor.execute("SELECT id FROM stages WHERE name = ? AND id != ?", (name, exclude_id))
            else:
                cursor.execute("SELECT id FROM stages WHERE name = ?", (name,))
            return cursor.fetchone() is not None

    def get_stage_products(self, stage_id):
        """Получить изделия в составе этапа"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sp.id, p.name, sp.part, sp.quantity, p.cost,
                       (p.cost * sp.quantity) as total_cost
                FROM stage_products sp
                JOIN products p ON sp.product_id = p.id
                WHERE sp.stage_id = ?
                ORDER BY sp.part, p.name
            """, (stage_id,))
            return cursor.fetchall()

    def get_stage_materials(self, stage_id):
        """Получить материалы в составе этапа"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sm.id, m.name, m.type, sm.part, sm.quantity, sm.length, m.price,
                       CASE
                           WHEN m.type = 'Пиломатериал' AND sm.length IS NOT NULL
                           THEN (m.price * sm.quantity * sm.length)
                           ELSE (m.price * sm.quantity)
                       END as total_cost
                FROM stage_materials sm
                JOIN materials m ON sm.material_id = m.id
                WHERE sm.stage_id = ?
                ORDER BY sm.part, m.name
            """, (stage_id,))
            return cursor.fetchall()

    def add_product_to_stage(self, stage_id, product_id, quantity, part='meter'):
        """Добавить изделие в этап"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO stage_products (stage_id, product_id, quantity, part) 
                VALUES (?, ?, ?, ?)
            """, (stage_id, product_id, quantity, part))
            conn.commit()
            return cursor.lastrowid

    def add_material_to_stage(self, stage_id, material_id, quantity, length=None, part='meter'):
        """Добавить материал в этап"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO stage_materials (stage_id, material_id, quantity, length, part) 
                VALUES (?, ?, ?, ?, ?)
            """, (stage_id, material_id, quantity, length, part))
            conn.commit()
            return cursor.lastrowid

    def update_stage_product(self, stage_product_id, quantity, part='meter'):
        """Обновить изделие в этапе"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE stage_products SET quantity = ?, part = ? WHERE id = ?
            """, (quantity, part, stage_product_id))
            conn.commit()
            return cursor.rowcount

    def update_stage_material(self, stage_material_id, quantity, length=None, part='meter'):
        """Обновить материал в этапе"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE stage_materials SET quantity = ?, length = ?, part = ? WHERE id = ?
            """, (quantity, length, part, stage_material_id))
            conn.commit()
            return cursor.rowcount

    def remove_product_from_stage(self, stage_product_id):
        """Удалить изделие из этапа"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM stage_products WHERE id = ?", (stage_product_id,))
            conn.commit()
            return cursor.rowcount

    def remove_material_from_stage(self, stage_material_id):
        """Удалить материал из этапа"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM stage_materials WHERE id = ?", (stage_material_id,))
            conn.commit()
            return cursor.rowcount

    def calculate_stage_cost(self, stage_id):
        """Рассчитать себестоимость этапа с разделением по частям"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            start_cost = meter_cost = end_cost = 0.0

            # Стоимость изделий по частям
            cursor.execute("""
                SELECT sp.part, p.cost, sp.quantity
                FROM stage_products sp
                JOIN products p ON sp.product_id = p.id
                WHERE sp.stage_id = ?
            """, (stage_id,))

            for part, pcost, qty in cursor.fetchall():
                cost_add = pcost * qty
                if part == 'start':
                    start_cost += cost_add
                elif part == 'meter':
                    meter_cost += cost_add
                else:  # end
                    end_cost += cost_add

            # Стоимость материалов по частям
            cursor.execute("""
                SELECT sm.part, m.type, m.price, sm.quantity, sm.length
                FROM stage_materials sm
                JOIN materials m ON sm.material_id = m.id
                WHERE sm.stage_id = ?
            """, (stage_id,))

            for part, mtype, price, qty, length in cursor.fetchall():
                if mtype == "Пиломатериал" and length:
                    cost_add = price * qty * length
                else:
                    cost_add = price * qty

                if part == 'start':
                    start_cost += cost_add
                elif part == 'meter':
                    meter_cost += cost_add
                else:  # end
                    end_cost += cost_add

            # Обновляем стоимость этапа (сохраняем только метровую часть для совместимости)
            cursor.execute("UPDATE stages SET cost = ? WHERE id = ?", (meter_cost, stage_id))
            conn.commit()

            return {
                'start_cost': start_cost,
                'meter_cost': meter_cost,
                'end_cost': end_cost,
                'total_per_meter': start_cost + meter_cost + end_cost
            }

    def compute_stage_cost_for_length(self, stage_id, length_meters):
        """Вычислить стоимость этапа для конкретной длины"""
        effective_meters = math.ceil(max(0.0, float(length_meters)))

        with self.get_connection() as conn:
            cursor = conn.cursor()

            start_cost = meter_cost = end_cost = 0.0

            # Стоимость изделий
            cursor.execute("""
                SELECT sp.part, p.cost, sp.quantity
                FROM stage_products sp
                JOIN products p ON sp.product_id = p.id
                WHERE sp.stage_id = ?
            """, (stage_id,))

            for part, pcost, qty in cursor.fetchall():
                mult = effective_meters if part == 'meter' else 1
                cost_add = pcost * qty * mult
                if part == 'start':
                    start_cost += cost_add
                elif part == 'meter':
                    meter_cost += cost_add
                else:  # end
                    end_cost += cost_add

            # Стоимость материалов
            cursor.execute("""
                SELECT sm.part, m.type, m.price, sm.quantity, sm.length
                FROM stage_materials sm
                JOIN materials m ON sm.material_id = m.id
                WHERE sm.stage_id = ?
            """, (stage_id,))

            for part, mtype, price, qty, length in cursor.fetchall():
                mult = effective_meters if part == 'meter' else 1
                if mtype == 'Пиломатериал' and length:
                    cost_add = price * qty * float(length) * mult
                else:
                    cost_add = price * qty * mult

                if part == 'start':
                    start_cost += cost_add
                elif part == 'meter':
                    meter_cost += cost_add
                else:  # end
                    end_cost += cost_add

            return start_cost + meter_cost + end_cost

    def recalculate_all_stages_cost(self):
        """Пересчитать себестоимость всех этапов"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM stages")
            stage_ids = [row[0] for row in cursor.fetchall()]

            for stage_id in stage_ids:
                self.calculate_stage_cost(stage_id)

    def get_stage_cost_breakdown(self, stage_id):
        """Получить детализацию стоимости этапа"""
        breakdown = {
            'products': {'start': [], 'meter': [], 'end': []},
            'materials': {'start': [], 'meter': [], 'end': []},
            'totals': {'start': 0, 'meter': 0, 'end': 0}
        }

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Изделия
            cursor.execute("""
                SELECT sp.part, p.name, sp.quantity, p.cost, (p.cost * sp.quantity) as total
                FROM stage_products sp
                JOIN products p ON sp.product_id = p.id
                WHERE sp.stage_id = ?
                ORDER BY sp.part, p.name
            """, (stage_id,))

            for part, name, qty, cost, total in cursor.fetchall():
                breakdown['products'][part].append({
                    'name': name,
                    'quantity': qty,
                    'unit_cost': cost,
                    'total_cost': total
                })
                breakdown['totals'][part] += total

            # Материалы
            cursor.execute("""
                SELECT sm.part, m.name, m.type, sm.quantity, sm.length, m.price,
                       CASE
                           WHEN m.type = 'Пиломатериал' AND sm.length IS NOT NULL
                           THEN (m.price * sm.quantity * sm.length)
                           ELSE (m.price * sm.quantity)
                       END as total
                FROM stage_materials sm
                JOIN materials m ON sm.material_id = m.id
                WHERE sm.stage_id = ?
                ORDER BY sm.part, m.name
            """, (stage_id,))

            for part, name, mtype, qty, length, price, total in cursor.fetchall():
                breakdown['materials'][part].append({
                    'name': name,
                    'type': mtype,
                    'quantity': qty,
                    'length': length,
                    'unit_price': price,
                    'total_cost': total
                })
                breakdown['totals'][part] += total

        return breakdown

    def duplicate_stage(self, stage_id, new_name):
        """Создать копию этапа"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Получаем описание оригинального этапа
            cursor.execute("SELECT description FROM stages WHERE id = ?", (stage_id,))
            original_description = cursor.fetchone()[0]

            # Создаем новый этап
            cursor.execute("INSERT INTO stages (name, cost, description) VALUES (?, 0.0, ?)",
                           (new_name, original_description))
            new_stage_id = cursor.lastrowid

            # Копируем изделия
            cursor.execute("""
                INSERT INTO stage_products (stage_id, product_id, quantity, part)
                SELECT ?, product_id, quantity, part
                FROM stage_products
                WHERE stage_id = ?
            """, (new_stage_id, stage_id))

            # Копируем материалы
            cursor.execute("""
                INSERT INTO stage_materials (stage_id, material_id, quantity, length, part)
                SELECT ?, material_id, quantity, length, part
                FROM stage_materials
                WHERE stage_id = ?
            """, (new_stage_id, stage_id))

            conn.commit()

            # Рассчитываем стоимость нового этапа
            self.calculate_stage_cost(new_stage_id)

            return new_stage_id

    def get_stages_using_product(self, product_id):
        """Получить этапы, использующие определенное изделие"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT s.id, s.name, s.cost
                FROM stages s
                JOIN stage_products sp ON s.id = sp.stage_id
                WHERE sp.product_id = ?
                ORDER BY s.name
            """, (product_id,))
            return cursor.fetchall()

    def get_stages_using_material(self, material_id):
        """Получить этапы, использующие определенный материал"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT s.id, s.name, s.cost
                FROM stages s
                JOIN stage_materials sm ON s.id = sm.stage_id
                WHERE sm.material_id = ?
                ORDER BY s.name
            """, (material_id,))
            return cursor.fetchall()