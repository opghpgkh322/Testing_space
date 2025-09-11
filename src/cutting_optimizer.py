class CuttingOptimizer:
    """Оптимизатор раскроя пиломатериалов"""

    def __init__(self):
        self.waste_threshold = 0.3  # Минимальный остаток, который считается полезным (в метрах)

    def optimize(self, available_lengths, required_lengths):
        """
        Оптимизация раскроя досок

        Args:
            available_lengths: Список доступных длин досок [6.0, 6.0, 4.5, ...]
            required_lengths: Список необходимых отрезков [2.5, 1.8, 0.75, ...]

        Returns:
            dict: Результат оптимизации с планом раскроя
        """
        # Сортируем необходимые длины по убыванию для более эффективного размещения
        required_sorted = sorted(required_lengths, reverse=True)
        available_sorted = sorted(available_lengths, reverse=True)

        used_boards = []
        cutting_plan = []
        remaining_boards = available_sorted.copy()
        uncut_requirements = required_sorted.copy()

        # Основной алгоритм оптимизации
        for required_length in required_sorted:
            best_board_idx = None
            best_waste = float('inf')

            # Ищем наиболее подходящую доску (с минимальными отходами)
            for i, available_length in enumerate(remaining_boards):
                if available_length >= required_length:
                    waste = available_length - required_length
                    if waste < best_waste:
                        best_waste = waste
                        best_board_idx = i

            if best_board_idx is not None:
                # Используем найденную доску
                board_length = remaining_boards[best_board_idx]
                used_boards.append(board_length)

                # Планируем раскрой этой доски
                cuts_on_board = [required_length]
                remaining_length = board_length - required_length
                uncut_requirements.remove(required_length)

                # Пытаемся разместить на этой же доске другие отрезки
                for other_req in uncut_requirements[:]:
                    if remaining_length >= other_req:
                        cuts_on_board.append(other_req)
                        remaining_length -= other_req
                        uncut_requirements.remove(other_req)

                cutting_plan.append((board_length, cuts_on_board))
                remaining_boards.pop(best_board_idx)

        # Рассчитываем статистику
        total_waste = sum(
            board_length - sum(cuts)
            for board_length, cuts in cutting_plan
        )

        efficiency = (
            (sum(required_lengths) / sum(board_length for board_length, _ in cutting_plan)) * 100
            if cutting_plan else 0
        )

        return {
            'cutting_plan': cutting_plan,
            'used_boards': used_boards,
            'remaining_boards': remaining_boards,
            'total_waste': total_waste,
            'efficiency_percent': efficiency,
            'uncut_requirements': uncut_requirements,
            'success': len(uncut_requirements) == 0
        }

    def optimize_multiple_materials(self, materials_requirements):
        """
        Оптимизация раскроя для нескольких типов материалов

        Args:
            materials_requirements: dict вида {
                'Брус 100x100': {
                    'available': [6.0, 6.0, 4.5],
                    'required': [2.5, 1.8, 0.75]
                }
            }

        Returns:
            dict: Результаты оптимизации для каждого материала
        """
        results = {}

        for material_name, data in materials_requirements.items():
            available = data.get('available', [])
            required = data.get('required', [])

            if available and required:
                results[material_name] = self.optimize(available, required)
            else:
                results[material_name] = {
                    'cutting_plan': [],
                    'used_boards': [],
                    'remaining_boards': available,
                    'total_waste': 0,
                    'efficiency_percent': 0,
                    'uncut_requirements': required,
                    'success': len(required) == 0
                }

        return results

    def get_cutting_instructions(self, optimization_result):
        """
        Получить текстовые инструкции по раскрою

        Args:
            optimization_result: Результат работы optimize()

        Returns:
            str: Текст с инструкциями
        """
        instructions = []

        if not optimization_result['success']:
            instructions.append("⚠️ ВНИМАНИЕ: Не все отрезки удалось разместить!")
            instructions.append(f"Недостающие отрезки: {optimization_result['uncut_requirements']}")
            instructions.append("")

        instructions.append("📏 ПЛАН РАСКРОЯ:")
        instructions.append("=" * 50)

        for i, (board_length, cuts) in enumerate(optimization_result['cutting_plan'], 1):
            waste = board_length - sum(cuts)

            instructions.append(f"Доска №{i} ({board_length:.2f}м):")
            for j, cut in enumerate(cuts, 1):
                instructions.append(f"  ✂️ Отрезок {j}: {cut:.2f}м")

            if waste > self.waste_threshold:
                instructions.append(f"  📦 Остаток: {waste:.2f}м (сохранить)")
            elif waste > 0:
                instructions.append(f"  🗑️ Отходы: {waste:.2f}м")

            instructions.append("")

        # Статистика
        instructions.append("📊 СТАТИСТИКА:")
        instructions.append("=" * 30)
        instructions.append(f"Использовано досок: {len(optimization_result['used_boards'])}")
        instructions.append(f"Осталось досок: {len(optimization_result['remaining_boards'])}")
        instructions.append(f"Общие отходы: {optimization_result['total_waste']:.2f}м")
        instructions.append(f"Эффективность: {optimization_result['efficiency_percent']:.1f}%")

        return "\n".join(instructions)

    def suggest_optimal_board_lengths(self, required_lengths, standard_lengths=None):
        """
        Предложение оптимальных длин досок для закупки

        Args:
            required_lengths: Список необходимых отрезков
            standard_lengths: Стандартные длины досок в продаже

        Returns:
            dict: Рекомендации по закупке
        """
        if standard_lengths is None:
            standard_lengths = [3.0, 4.0, 4.5, 6.0]

        recommendations = {}

        for std_length in standard_lengths:
            # Тестируем оптимизацию с досками только этой длины
            test_available = [std_length] * len(required_lengths)  # Достаточное количество
            result = self.optimize(test_available, required_lengths)

            recommendations[std_length] = {
                'boards_needed': len(result['used_boards']),
                'efficiency': result['efficiency_percent'],
                'total_waste': result['total_waste'],
                'cost_factor': len(result['used_boards']) * std_length
            }

        # Находим наиболее эффективный вариант
        best_option = max(
            recommendations.items(),
            key=lambda x: x[1]['efficiency'] - (x[1]['total_waste'] * 0.1)  # Штраф за отходы
        )

        return {
            'recommendations': recommendations,
            'best_option': best_option[0],
            'best_efficiency': best_option[1]['efficiency']
        }

    def calculate_material_requirements(self, cutting_plan_result, material_price_per_meter):
        """
        Расчет стоимости материалов на основе плана раскроя

        Args:
            cutting_plan_result: Результат optimize()
            material_price_per_meter: Цена за метр материала

        Returns:
            dict: Информация о стоимости
        """
        total_material_used = sum(
            board_length for board_length, _ in cutting_plan_result['cutting_plan']
        )

        total_useful_length = sum(
            sum(cuts) for _, cuts in cutting_plan_result['cutting_plan']
        )

        material_cost = total_material_used * material_price_per_meter
        effective_cost = total_useful_length * material_price_per_meter
        waste_cost = cutting_plan_result['total_waste'] * material_price_per_meter

        return {
            'total_material_meters': total_material_used,
            'useful_meters': total_useful_length,
            'waste_meters': cutting_plan_result['total_waste'],
            'total_cost': material_cost,
            'effective_cost': effective_cost,
            'waste_cost': waste_cost,
            'cost_per_useful_meter': material_cost / total_useful_length if total_useful_length > 0 else 0
        }