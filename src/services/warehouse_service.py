import sqlite3
from contextlib import contextmanager
from collections import defaultdict


class WarehouseService:
    """Сервис для работы со складом"""

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

    def get_all_warehouse_items(self):
        """Получить все записи склада"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT w.id, m.name, w.length, w.quantity, m.type, m.unit
                FROM warehouse w
                JOIN materials m ON w.material_id = m.id
                ORDER BY m.name, w.length DESC
            """)
            return cursor.fetchall()

    def get_warehouse_by_material(self, material_id):
        """Получить складские остатки конкретного материала"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT w.id, w.length, w.quantity
                FROM warehouse w
                WHERE w.material_id = ?
                ORDER BY w.length DESC
            """, (material_id,))
            return cursor.fetchall()

    def add_to_warehouse(self, material_id, length, quantity):
        """Добавить материал на склад"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Проверяем, есть ли уже такая запись
            cursor.execute("""
                SELECT id, quantity FROM warehouse 
                WHERE material_id = ? AND length = ?
            """, (material_id, length))
            existing = cursor.fetchone()

            if existing:
                # Увеличиваем количество существующей записи
                new_quantity = existing[1] + quantity
                cursor.execute("""
                    UPDATE warehouse SET quantity = ? WHERE id = ?
                """, (new_quantity, existing[0]))
                return existing[0]
            else:
                # Создаем новую запись
                cursor.execute("""
                    INSERT INTO warehouse (material_id, length, quantity) 
                    VALUES (?, ?, ?)
                """, (material_id, length, quantity))
                conn.commit()
                return cursor.lastrowid

    def update_warehouse_item(self, warehouse_id, length, quantity):
        """Обновить запись склада"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE warehouse SET length = ?, quantity = ? WHERE id = ?
            """, (length, quantity, warehouse_id))
            conn.commit()
            return cursor.rowcount

    def delete_warehouse_item(self, warehouse_id):
        """Удалить запись склада"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM warehouse WHERE id = ?", (warehouse_id,))
            conn.commit()
            return cursor.rowcount

    def get_stock_summary(self):
        """Получить сводку по остаткам на складе"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    m.name,
                    m.type,
                    m.unit,
                    SUM(CASE 
                        WHEN m.type = 'Пиломатериал' THEN w.length * w.quantity
                        ELSE w.quantity
                    END) as total_amount,
                    COUNT(w.id) as positions_count
                FROM warehouse w
                JOIN materials m ON w.material_id = m.id
                GROUP BY m.id, m.name, m.type, m.unit
                ORDER BY m.name
            """)
            return cursor.fetchall()

    def check_availability(self, requirements):
        """
        Проверить наличие материалов на складе
        requirements: dict {material_name: [(length/quantity, description), ...]}
        """
        missing = []

        with self.get_connection() as conn:
            cursor = conn.cursor()

            for material_name, items in requirements.items():
                # Получаем тип материала
                cursor.execute("SELECT type FROM materials WHERE name = ?", (material_name,))
                material_type_result = cursor.fetchone()

                if not material_type_result:
                    missing.append(f"{material_name}: материал не найден в базе")
                    continue

                material_type = material_type_result[0]

                # Получаем остатки на складе
                cursor.execute("""
                    SELECT w.length, w.quantity
                    FROM warehouse w
                    JOIN materials m ON w.material_id = m.id
                    WHERE m.name = ?
                    ORDER BY w.length DESC
                """, (material_name,))
                stock = cursor.fetchall()

                if material_type == "Пиломатериал":
                    # Для пиломатериалов проверяем раскрой
                    required_lengths = [item[0] for item in items]
                    if not self._check_lumber_availability(stock, required_lengths):
                        total_required = sum(required_lengths)
                        total_available = sum(length * qty for length, qty in stock)
                        missing.append(
                            f"{material_name}: требуется {total_required:.2f}м, доступно {total_available:.2f}м")
                else:
                    # Для метизов просто суммируем количество
                    total_required = sum(item[0] for item in items)
                    total_available = sum(qty for _, qty in stock)
                    if total_available < total_required:
                        missing.append(f"{material_name}: требуется {total_required}шт, доступно {total_available}шт")

        return missing

    def _check_lumber_availability(self, stock, required_lengths):
        """Проверить возможность раскроя пиломатериалов"""
        # Создаем список доступных досок
        available_boards = []
        for length, quantity in stock:
            available_boards.extend([length] * quantity)

        # Сортируем требования по убыванию
        required_sorted = sorted(required_lengths, reverse=True)

        # Пытаемся "раскроить" каждую требуемую длину
        for req_length in required_sorted:
            found = False
            for i, board_length in enumerate(available_boards):
                if board_length >= req_length:
                    # "Отрезаем" от доски
                    available_boards[i] -= req_length
                    if available_boards[i] < 0.3:  # Минимальный остаток
                        available_boards.pop(i)
                    found = True
                    break

            if not found:
                return False

        return True

    def update_warehouse_bulk(self, updated_data):
        """Массовое обновление склада после заказа"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Очищаем текущие остатки
            cursor.execute("DELETE FROM warehouse")

            # Добавляем новые остатки
            for material_name, length, quantity in updated_data:
                if quantity > 0:
                    cursor.execute("""
                        INSERT INTO warehouse (material_id, length, quantity)
                        SELECT m.id, ?, ?
                        FROM materials m
                        WHERE m.name = ?
                    """, (length, quantity, material_name))

            conn.commit()

    def get_materials_for_combo(self):
        """Получить список материалов для комбобокса"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, type FROM materials ORDER BY name")
            return cursor.fetchall()

    def get_low_stock_items(self, threshold=5):
        """Получить материалы с низкими остатками"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    m.name,
                    m.type,
                    SUM(CASE 
                        WHEN m.type = 'Пиломатериал' THEN w.length * w.quantity
                        ELSE w.quantity
                    END) as total_amount,
                    m.unit
                FROM warehouse w
                JOIN materials m ON w.material_id = m.id
                GROUP BY m.id, m.name, m.type, m.unit
                HAVING total_amount <= ?
                ORDER BY total_amount ASC
            """, (threshold,))
            return cursor.fetchall()

    def get_warehouse_value(self):
        """Рассчитать общую стоимость материалов на складе"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(
                    CASE 
                        WHEN m.type = 'Пиломатериал' 
                        THEN w.length * w.quantity * m.price
                        ELSE w.quantity * m.price
                    END
                ) as total_value
                FROM warehouse w
                JOIN materials m ON w.material_id = m.id
            """)
            result = cursor.fetchone()
            return result[0] if result[0] is not None else 0