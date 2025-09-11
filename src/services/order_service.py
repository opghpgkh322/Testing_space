import sqlite3
from contextlib import contextmanager
from datetime import datetime
from collections import defaultdict
import math


class OrderService:
    """Сервис для работы с заказами"""

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

    def create_order(self, total_cost, instructions=None):
        """Создать новый заказ"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO orders (order_date, total_cost, instructions) 
                VALUES (datetime('now'), ?, ?)
            """, (total_cost, instructions))
            conn.commit()
            return cursor.lastrowid

    def add_product_to_order(self, order_id, product_id, quantity, product_name, cost):
        """Добавить изделие в заказ"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO order_items 
                (order_id, product_id, stage_id, quantity, length_meters, product_name, cost, item_type)
                VALUES (?, ?, NULL, ?, NULL, ?, ?, 'product')
            """, (order_id, product_id, quantity, product_name, cost))
            conn.commit()
            return cursor.lastrowid

    def add_stage_to_order(self, order_id, stage_id, length_meters, stage_name, cost):
        """Добавить этап в заказ"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO order_items 
                (order_id, product_id, stage_id, quantity, length_meters, product_name, cost, item_type)
                VALUES (?, NULL, ?, 1, ?, ?, ?, 'stage')
            """, (order_id, stage_id, length_meters, stage_name, cost))
            conn.commit()
            return cursor.lastrowid

    def get_all_orders(self):
        """Получить все заказы с количеством позиций"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.id, o.order_date, o.total_cost, o.pdf_filename,
                       COUNT(oi.id) as items_count
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                GROUP BY o.id, o.order_date, o.total_cost, o.pdf_filename
                ORDER BY o.order_date DESC
            """)
            return cursor.fetchall()

    def get_order_by_id(self, order_id):
        """Получить заказ по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, order_date, total_cost, instructions, pdf_filename
                FROM orders WHERE id = ?
            """, (order_id,))
            return cursor.fetchone()

    def get_order_items(self, order_id):
        """Получить позиции заказа"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, product_id, stage_id, quantity, length_meters, 
                       product_name, cost, item_type
                FROM order_items 
                WHERE order_id = ?
                ORDER BY item_type, product_name
            """, (order_id,))
            return cursor.fetchall()

    def update_order_pdf_filename(self, order_id, pdf_filename):
        """Обновить имя PDF файла заказа"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE orders SET pdf_filename = ? WHERE id = ?",
                           (pdf_filename, order_id))
            conn.commit()
            return cursor.rowcount

    def delete_order(self, order_id):
        """Удалить заказ и все его позиции"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
            cursor.execute("DELETE FROM orders WHERE id = ?", (order_id,))
            conn.commit()
            return cursor.rowcount

    def calculate_order_requirements(self, order_items):
        """
        Рассчитать требования к материалам для заказа
        order_items: список кортежей (item_type, item_id, quantity_or_length)
        """
        requirements = defaultdict(list)

        with self.get_connection() as conn:
            cursor = conn.cursor()

            for item_type, item_id, quantity_or_length in order_items:
                if item_type == 'product':
                    # Получаем состав изделия
                    cursor.execute("""
                        SELECT m.name, m.type, pc.quantity, pc.length
                        FROM product_composition pc
                        JOIN materials m ON pc.material_id = m.id
                        WHERE pc.product_id = ?
                    """, (item_id,))

                    cursor.execute("SELECT name FROM products WHERE id = ?", (item_id,))
                    product_name = cursor.fetchone()[0]

                    for mat_name, mat_type, comp_qty, comp_length in cursor.fetchall():
                        total_quantity = quantity_or_length
                        if mat_type == "Пиломатериал" and comp_length:
                            # Для пиломатериалов добавляем каждый отрезок отдельно
                            for _ in range(int(comp_qty * total_quantity)):
                                requirements[mat_name].append((float(comp_length), f"Изделие '{product_name}'"))
                        else:
                            # Для метизов суммируем количество
                            requirements[mat_name].append((comp_qty * total_quantity, f"Изделие '{product_name}'"))

                elif item_type == 'stage':
                    # Для этапов используем длину в метрах
                    length_m = float(quantity_or_length)
                    effective_meters = math.ceil(length_m)

                    cursor.execute("SELECT name FROM stages WHERE id = ?", (item_id,))
                    stage_name = cursor.fetchone()[0]

                    # Материалы напрямую в этапе
                    cursor.execute("""
                        SELECT sm.part, m.name, m.type, sm.quantity, sm.length
                        FROM stage_materials sm
                        JOIN materials m ON sm.material_id = m.id
                        WHERE sm.stage_id = ?
                    """, (item_id,))

                    for part, mat_name, mat_type, sm_qty, sm_length in cursor.fetchall():
                        multiplier = effective_meters if part == 'meter' else 1
                        if mat_type == "Пиломатериал" and sm_length:
                            for _ in range(int(sm_qty * multiplier)):
                                requirements[mat_name].append((float(sm_length), f"Этап '{stage_name}' ({part})"))
                        else:
                            requirements[mat_name].append((sm_qty * multiplier, f"Этап '{stage_name}' ({part})"))

                    # Материалы через изделия этапа
                    cursor.execute("""
                        SELECT sp.part, sp.quantity, p.id, p.name
                        FROM stage_products sp
                        JOIN products p ON sp.product_id = p.id
                        WHERE sp.stage_id = ?
                    """, (item_id,))

                    for part, sp_qty, prod_id, prod_name in cursor.fetchall():
                        multiplier = effective_meters if part == 'meter' else 1

                        cursor.execute("""
                            SELECT m.name, m.type, pc.quantity, pc.length
                            FROM product_composition pc
                            JOIN materials m ON pc.material_id = m.id
                            WHERE pc.product_id = ?
                        """, (prod_id,))

                        for mat_name, mat_type, pc_qty, pc_length in cursor.fetchall():
                            total_qty = pc_qty * sp_qty * multiplier
                            if mat_type == "Пiломатериал" and pc_length:
                                for _ in range(int(total_qty)):
                                    requirements[mat_name].append((float(pc_length),
                                                                   f"Этап '{stage_name}' ({part}) → {prod_name}"))
                            else:
                                requirements[mat_name].append((total_qty,
                                                               f"Этап '{stage_name}' ({part}) → {prod_name}"))

        return dict(requirements)

    def calculate_order_total_cost(self, order_items):
        """Рассчитать общую стоимость заказа"""
        total_cost = 0.0

        with self.get_connection() as conn:
            cursor = conn.cursor()

            for item_type, item_id, quantity_or_length in order_items:
                if item_type == 'product':
                    cursor.execute("SELECT cost FROM products WHERE id = ?", (item_id,))
                    product_cost = cursor.fetchone()[0]
                    total_cost += product_cost * quantity_or_length

                elif item_type == 'stage':
                    # Рассчитываем стоимость этапа для данной длины
                    stage_cost = self._calculate_stage_cost_for_length(item_id, quantity_or_length)
                    total_cost += stage_cost

        return total_cost

    def _calculate_stage_cost_for_length(self, stage_id, length_m):
        """Рассчитать стоимость этапа для конкретной длины"""
        effective_meters = math.ceil(max(0.0, float(length_m)))

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
                if part == 'start':
                    start_cost += pcost * qty * mult
                elif part == 'meter':
                    meter_cost += pcost * qty * mult
                else:  # end
                    end_cost += pcost * qty * mult

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
                    add_cost = price * qty * float(length) * mult
                else:
                    add_cost = price * qty * mult

                if part == 'start':
                    start_cost += add_cost
                elif part == 'meter':
                    meter_cost += add_cost
                else:  # end
                    end_cost += add_cost

            return start_cost + meter_cost + end_cost

    def get_orders_by_date_range(self, start_date, end_date):
        """Получить заказы за период"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.id, o.order_date, o.total_cost, 
                       COUNT(oi.id) as items_count
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                WHERE DATE(o.order_date) BETWEEN ? AND ?
                GROUP BY o.id, o.order_date, o.total_cost
                ORDER BY o.order_date DESC
            """, (start_date, end_date))
            return cursor.fetchall()

    def get_order_statistics(self):
        """Получить статистику по заказам"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Общая статистика
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_orders,
                    SUM(total_cost) as total_revenue,
                    AVG(total_cost) as avg_order_value,
                    MAX(total_cost) as max_order_value,
                    MIN(total_cost) as min_order_value
                FROM orders
            """)
            general_stats = cursor.fetchone()

            # Статистика по месяцам
            cursor.execute("""
                SELECT 
                    strftime('%Y-%m', order_date) as month,
                    COUNT(*) as orders_count,
                    SUM(total_cost) as monthly_revenue
                FROM orders
                GROUP BY strftime('%Y-%m', order_date)
                ORDER BY month DESC
                LIMIT 12
            """)
            monthly_stats = cursor.fetchall()

            # Самые популярные изделия
            cursor.execute("""
                SELECT 
                    oi.product_name,
                    SUM(oi.quantity) as total_quantity,
                    COUNT(*) as order_count
                FROM order_items oi
                WHERE oi.item_type = 'product'
                GROUP BY oi.product_name
                ORDER BY total_quantity DESC
                LIMIT 10
            """)
            popular_products = cursor.fetchall()

            # Самые популярные этапы
            cursor.execute("""
                SELECT 
                    oi.product_name as stage_name,
                    SUM(oi.length_meters) as total_meters,
                    COUNT(*) as order_count
                FROM order_items oi
                WHERE oi.item_type = 'stage'
                GROUP BY oi.product_name
                ORDER BY total_meters DESC
                LIMIT 10
            """)
            popular_stages = cursor.fetchall()

            return {
                'general': general_stats,
                'monthly': monthly_stats,
                'popular_products': popular_products,
                'popular_stages': popular_stages
            }

    def get_material_consumption_by_orders(self, limit_orders=None):
        """Получить потребление материалов по заказам"""
        material_usage = defaultdict(float)

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Получаем заказы
            if limit_orders:
                cursor.execute("SELECT id FROM orders ORDER BY order_date DESC LIMIT ?", (limit_orders,))
            else:
                cursor.execute("SELECT id FROM orders")

            order_ids = [row[0] for row in cursor.fetchall()]

            for order_id in order_ids:
                # Получаем позиции заказа
                cursor.execute("""
                    SELECT item_type, product_id, stage_id, quantity, length_meters
                    FROM order_items WHERE order_id = ?
                """, (order_id,))

                order_items = []
                for item_type, prod_id, stage_id, qty, length in cursor.fetchall():
                    if item_type == 'product':
                        order_items.append(('product', prod_id, qty))
                    else:
                        order_items.append(('stage', stage_id, length))

                # Рассчитываем требования к материалам
                requirements = self.calculate_order_requirements(order_items)

                # Суммируем потребление
                for material, items in requirements.items():
                    for value, description in items:
                        material_usage[material] += value

        # Сортируем по убыванию потребления
        return sorted(material_usage.items(), key=lambda x: x[1], reverse=True)

    def export_order_summary(self, order_id):
        """Экспортировать сводку заказа для внешних систем"""
        order = self.get_order_by_id(order_id)
        if not order:
            return None

        order_items = self.get_order_items(order_id)

        # Группируем позиции
        products = []
        stages = []

        for item in order_items:
            item_id, prod_id, stage_id, qty, length, name, cost, item_type = item
            if item_type == 'product':
                products.append({
                    'id': prod_id,
                    'name': name,
                    'quantity': qty,
                    'cost': cost
                })
            else:
                stages.append({
                    'id': stage_id,
                    'name': name,
                    'length_meters': length,
                    'cost': cost
                })

        return {
            'order_id': order[0],
            'order_date': order[1],
            'total_cost': order[2],
            'sale_price': order[2] * 2,  # Цена реализации
            'instructions': order[3],
            'pdf_filename': order[4],
            'products': products,
            'stages': stages,
            'items_count': len(order_items)
        }