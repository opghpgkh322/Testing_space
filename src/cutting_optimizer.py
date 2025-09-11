# cutting_optimizer.py - Оптимизация раскроя материалов
"""
Класс для оптимизации раскроя пиломатериалов и работы с метизами.
"""

import sqlite3
from collections import defaultdict
from config import Config, DatabaseConfig


class CuttingOptimizer:
    """Оптимизирует раскрой материалов для заданных требований"""

    MIN_USEFUL_LENGTH = Config.MIN_USEFUL_LENGTH

    @staticmethod
    def optimize_cutting(requirements, stock_items):
        """Основной метод оптимизации раскроя"""
        # Копия склада
        warehouse = defaultdict(list)
        for name, length, qty in stock_items:
            if qty <= 0:
                continue
            warehouse[name].append({'length': length, 'quantity': qty, 'original': length})

        material_types = CuttingOptimizer._get_material_types()
        can_produce = True
        missing = []
        instructions = defaultdict(list)
        updated = []

        # Проверяем наличие
        for mat, reqs in requirements.items():
            total_req = sum(r[0] for r in reqs)
            total_avail = sum(item['quantity'] * item['length'] if material_types.get(mat)==Config.MATERIAL_TYPES[0] else item['quantity'] for item in warehouse.get(mat, []))
            if total_avail < total_req:
                missing.append(f"{mat}: требуется {total_req}, доступно {total_avail}")
                can_produce = False

        # Обработка по типам
        for mat, reqs in requirements.items():
            if material_types.get(mat)==Config.MATERIAL_TYPES[1]:
                # Метиз
                result = CuttingOptimizer._process_fastener(mat, reqs, warehouse.get(mat, []))
            else:
                result = CuttingOptimizer._process_lumber(mat, reqs, warehouse.get(mat, []))
            instructions[mat] = result['instructions']
            updated.extend(result['updated'])
            if not result['success']:
                missing.extend(result.get('missing', []))
                can_produce = False

        # Добавляем неучтенные
        for name, items in warehouse.items():
            if name not in requirements:
                for item in items:
                    updated.append([name, item['length'], item['quantity']])

        # Округление и сортировка
        updated = [[m, round(l,2), q] for m,l,q in updated]
        updated.sort(key=lambda x:(x[0], -x[1]))

        return {'can_produce': can_produce, 'missing': missing, 'updated': updated, 'instructions': dict(instructions)}

    @staticmethod
    def _get_material_types():
        conn = sqlite3.connect(DatabaseConfig.get_db_path())
        cursor = conn.cursor()
        cursor.execute("SELECT name,type FROM materials")
        types = dict(cursor.fetchall())
        conn.close()
        return types

    @staticmethod
    def _process_lumber(material, requirements, stock):
        """Оптимизация раскроя пиломатериалов"""
        requirements = [r for r in requirements if r[0]>0]
        if not requirements:
            return {'success': True, 'instructions': [], 'updated': [], 'missing': []}
        # Список досок
        boards = []
        for item in stock:
            for _ in range(item['quantity']):
                boards.append({'orig': item['original'], 'cur': item['length'], 'cuts': []})
        boards.sort(key=lambda x: x['cur'], reverse=True)

        missing = defaultdict(float)
        # Раскрой
        for length, desc in sorted(requirements, key=lambda x:x[0], reverse=True):
            placed = False
            best_i, best_rem = -1, float('inf')
            for i, b in enumerate(boards):
                if b['cur'] >= length and (b['cur']-length) < best_rem:
                    best_rem = b['cur']-length
                    best_i = i
            if best_i>=0:
                b = boards[best_i]
                b['cur'] = round(b['cur'] - length, 2)
                b['cuts'].append((length, desc))
                placed = True
            if not placed:
                missing[desc] += length

        # Инструкции и остатки
        instructions, updated = [], []
        for b in boards:
            if b['cuts']:
                instr = f"Доска {b['orig']}м:\n"
                for i,(l,d) in enumerate(b['cuts'],1): instr+=f" {i}. Отпилить {l}м для {d}\n"
                rem = b['cur']
                instr+=f" Остаток: {rem:.2f}м{' (не используется)' if rem<Config.MIN_USEFUL_LENGTH else ''}\n"
                instructions.append(instr)
            if b['cur']>=Config.MIN_USEFUL_LENGTH:
                found=False
                for u in updated:
                    if u[0]==material and abs(u[1]-b['cur'])<0.01:
                        u[2]+=1; found=True; break
                if not found: updated.append([material,b['cur'],1])

        miss_list = [f"{desc}: не хватает {round(v,2)}м" for desc,v in missing.items()]
        return {'success': len(miss_list)==0, 'instructions': instructions, 'updated': updated, 'missing': miss_list}

    @staticmethod
    def _process_fastener(material, requirements, stock):
        """Обработка метизов"""
        total_req = sum(r[0] for r in requirements)
        total_avail = sum(item['quantity'] for item in stock)
        if total_avail < total_req:
            return {'success': False, 'updated': [], 'instructions': [], 'missing': [f"{material}: требуется {total_req}, доступно {total_avail}"]}
        instr = [f"{r[0]} шт для {r[1]}" for r in requirements]
        updated = []
        if total_avail-total_req>0: updated.append([material,0.0,total_avail-total_req])
        return {'success': True, 'instructions': instr, 'updated': updated, 'missing': []}
