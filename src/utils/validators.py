import re
from datetime import datetime
from typing import Union, Optional


def validate_float(value: str, field_name: str = "Поле", min_value: Optional[float] = None,
                   max_value: Optional[float] = None) -> Optional[float]:
    """
    Валидация числового значения с плавающей точкой

    Args:
        value: Строковое значение для валидации
        field_name: Название поля для сообщений об ошибках
        min_value: Минимальное допустимое значение
        max_value: Максимальное допустимое значение

    Returns:
        float: Валидное числовое значение или None при ошибке
    """
    if not value or not value.strip():
        return None

    # Заменяем запятую на точку для русской локали
    value = value.strip().replace(',', '.')

    try:
        float_value = float(value)

        if min_value is not None and float_value < min_value:
            raise ValueError(f"{field_name} должно быть больше или равно {min_value}")

        if max_value is not None and float_value > max_value:
            raise ValueError(f"{field_name} должно быть меньше или равно {max_value}")

        return float_value

    except ValueError as e:
        if "could not convert" in str(e):
            raise ValueError(f"{field_name} должно быть числом")
        else:
            raise e


def validate_int(value: str, field_name: str = "Поле", min_value: Optional[int] = None,
                 max_value: Optional[int] = None) -> Optional[int]:
    """
    Валидация целочисленного значения

    Args:
        value: Строковое значение для валидации
        field_name: Название поля для сообщений об ошибках
        min_value: Минимальное допустимое значение
        max_value: Максимальное допустимое значение

    Returns:
        int: Валидное целочисленное значение или None при ошибке
    """
    if not value or not value.strip():
        return None

    try:
        int_value = int(value.strip())

        if min_value is not None and int_value < min_value:
            raise ValueError(f"{field_name} должно быть больше или равно {min_value}")

        if max_value is not None and int_value > max_value:
            raise ValueError(f"{field_name} должно быть меньше или равно {max_value}")

        return int_value

    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError(f"{field_name} должно быть целым числом")
        else:
            raise e


def validate_text(value: str, field_name: str = "Поле", min_length: int = 1,
                  max_length: Optional[int] = None, allow_special_chars: bool = True) -> Optional[str]:
    """
    Валидация текстового значения

    Args:
        value: Строковое значение для валидации
        field_name: Название поля для сообщений об ошибках
        min_length: Минимальная длина строки
        max_length: Максимальная длина строки
        allow_special_chars: Разрешать ли специальные символы

    Returns:
        str: Валидное текстовое значение или None при ошибке
    """
    if not value:
        value = ""

    # Убираем лишние пробелы
    cleaned_value = value.strip()

    if len(cleaned_value) < min_length:
        if min_length == 1:
            raise ValueError(f"{field_name} не может быть пустым")
        else:
            raise ValueError(f"{field_name} должно содержать минимум {min_length} символов")

    if max_length is not None and len(cleaned_value) > max_length:
        raise ValueError(f"{field_name} должно содержать максимум {max_length} символов")

    # Проверка на недопустимые символы
    if not allow_special_chars:
        # Разрешаем только буквы, цифры, пробелы и базовые знаки препинания
        if not re.match(r'^[а-яёА-ЯЁa-zA-Z0-9\s\-_.,()]+$', cleaned_value):
            raise ValueError(f"{field_name} содержит недопустимые символы")

    return cleaned_value


def validate_email(email: str) -> bool:
    """
    Валидация email адреса

    Args:
        email: Email адрес для валидации

    Returns:
        bool: True если email валиден
    """
    if not email or not email.strip():
        return False

    email = email.strip().lower()

    # Простая регулярка для email
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    return bool(re.match(email_pattern, email))


def validate_phone(phone: str, country_code: str = "RU") -> Optional[str]:
    """
    Валидация номера телефона

    Args:
        phone: Номер телефона для валидации
        country_code: Код страны (RU, US, etc.)

    Returns:
        str: Отформатированный номер телефона или None при ошибке
    """
    if not phone or not phone.strip():
        return None

    # Убираем все, кроме цифр и +
    cleaned_phone = re.sub(r'[^\d+]', '', phone.strip())

    if country_code == "RU":
        # Российские номера
        if cleaned_phone.startswith('+7'):
            cleaned_phone = cleaned_phone[2:]
        elif cleaned_phone.startswith('8'):
            cleaned_phone = cleaned_phone[1:]
        elif cleaned_phone.startswith('7'):
            cleaned_phone = cleaned_phone[1:]

        if len(cleaned_phone) != 10:
            raise ValueError("Номер телефона должен содержать 10 цифр после кода страны")

        # Форматируем как +7 (XXX) XXX-XX-XX
        formatted = f"+7 ({cleaned_phone[:3]}) {cleaned_phone[3:6]}-{cleaned_phone[6:8]}-{cleaned_phone[8:]}"
        return formatted

    else:
        # Для других стран - базовая валидация
        if len(cleaned_phone) < 7 or len(cleaned_phone) > 15:
            raise ValueError("Номер телефона должен содержать от 7 до 15 цифр")

        return cleaned_phone


def validate_date(date_str: str, date_format: str = "%d.%m.%Y") -> Optional[datetime]:
    """
    Валидация даты

    Args:
        date_str: Строка с датой
        date_format: Формат даты

    Returns:
        datetime: Объект datetime или None при ошибке
    """
    if not date_str or not date_str.strip():
        return None

    try:
        return datetime.strptime(date_str.strip(), date_format)
    except ValueError:
        raise ValueError(f"Дата должна быть в формате {date_format}")


def validate_positive_number(value: Union[str, int, float], field_name: str = "Значение") -> float:
    """
    Валидация положительного числа

    Args:
        value: Значение для валидации
        field_name: Название поля для сообщений об ошибках

    Returns:
        float: Положительное число
    """
    if isinstance(value, str):
        numeric_value = validate_float(value, field_name)
        if numeric_value is None:
            raise ValueError(f"{field_name} не может быть пустым")
    else:
        numeric_value = float(value)

    if numeric_value <= 0:
        raise ValueError(f"{field_name} должно быть больше нуля")

    return numeric_value


def validate_material_length(length_str: str, material_type: str) -> Optional[float]:
    """
    Валидация длины материала в зависимости от типа

    Args:
        length_str: Строка с длиной
        material_type: Тип материала (Пиломатериал, Метиз)

    Returns:
        float: Валидная длина или None
    """
    if material_type == "Метиз":
        # Для метизов длина не обязательна
        if not length_str or not length_str.strip():
            return None
        # Если указана, должна быть 0
        length = validate_float(length_str, "Длина")
        if length is not None and length != 0:
            raise ValueError("Для метизов длина должна быть 0 или пустой")
        return None

    else:  # Пиломатериал
        if not length_str or not length_str.strip():
            raise ValueError("Для пиломатериалов длина обязательна")

        length = validate_float(length_str, "Длина", min_value=0.1, max_value=20.0)
        if length is None:
            raise ValueError("Длина пиломатериала должна быть указана")

        return length


def validate_stage_part(part: str) -> str:
    """
    Валидация части этапа

    Args:
        part: Часть этапа

    Returns:
        str: Валидная часть этапа
    """
    valid_parts = ["start", "meter", "end"]

    if not part or part.strip().lower() not in valid_parts:
        raise ValueError(f"Часть этапа должна быть одной из: {', '.join(valid_parts)}")

    return part.strip().lower()


def format_currency(amount: Union[int, float], currency: str = "руб") -> str:
    """
    Форматирование суммы как валюты

    Args:
        amount: Сумма
        currency: Обозначение валюты

    Returns:
        str: Отформатированная сумма
    """
    try:
        return f"{float(amount):.2f} {currency}"
    except (ValueError, TypeError):
        return f"0.00 {currency}"


def format_date(date_obj: datetime, date_format: str = "%d.%m.%Y") -> str:
    """
    Форматирование даты

    Args:
        date_obj: Объект datetime
        date_format: Формат даты

    Returns:
        str: Отформатированная дата
    """
    if not isinstance(date_obj, datetime):
        return ""

    return date_obj.strftime(date_format)


def safe_division(dividend: Union[int, float], divisor: Union[int, float],
                  default: Union[int, float] = 0) -> float:
    """
    Безопасное деление с обработкой деления на ноль

    Args:
        dividend: Делимое
        divisor: Делитель
        default: Значение по умолчанию при делении на ноль

    Returns:
        float: Результат деления или значение по умолчанию
    """
    try:
        if divisor == 0:
            return float(default)
        return float(dividend) / float(divisor)
    except (ValueError, TypeError):
        return float(default)


def clean_filename(filename: str) -> str:
    """
    Очистка имени файла от недопустимых символов

    Args:
        filename: Исходное имя файла

    Returns:
        str: Очищенное имя файла
    """
    if not filename:
        return "untitled"

    # Заменяем недопустимые символы на подчеркивания
    cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename.strip())

    # Убираем множественные подчеркивания
    cleaned = re.sub(r'_+', '_', cleaned)

    # Убираем подчеркивания в начале и конце
    cleaned = cleaned.strip('_')

    if not cleaned:
        return "untitled"

    return cleaned


def validate_warehouse_quantity(quantity_str: str, material_type: str) -> int:
    """
    Валидация количества на складе

    Args:
        quantity_str: Строка с количеством
        material_type: Тип материала

    Returns:
        int: Валидное количество
    """
    quantity = validate_int(quantity_str, "Количество", min_value=1, max_value=9999)

    if quantity is None:
        raise ValueError("Количество обязательно для указания")

    return quantity


def validate_order_data(order_items: list) -> bool:
    """
    Валидация данных заказа

    Args:
        order_items: Список позиций заказа

    Returns:
        bool: True если данные валидны
    """
    if not order_items:
        raise ValueError("Заказ не может быть пустым")

    for item_type, item_id, quantity_or_length in order_items:
        if item_type not in ['product', 'stage']:
            raise ValueError(f"Неверный тип позиции: {item_type}")

        if not isinstance(item_id, int) or item_id <= 0:
            raise ValueError("ID позиции должен быть положительным числом")

        if item_type == 'product':
            if not isinstance(quantity_or_length, int) or quantity_or_length <= 0:
                raise ValueError("Количество изделия должно быть положительным числом")
        else:  # stage
            if not isinstance(quantity_or_length, (int, float)) or quantity_or_length <= 0:
                raise ValueError("Длина этапа должна быть положительным числом")

    return True


def normalize_material_name(name: str) -> str:
    """
    Нормализация названия материала

    Args:
        name: Исходное название

    Returns:
        str: Нормализованное название
    """
    if not name:
        return ""

    # Убираем лишние пробелы и приводим к единому регистру
    normalized = ' '.join(name.strip().split())

    # Первая буква заглавная
    return normalized.capitalize()


def validate_price_markup(cost_price: float, sale_price: float) -> float:
    """
    Валидация наценки на товар

    Args:
        cost_price: Себестоимость
        sale_price: Цена продажи

    Returns:
        float: Процент наценки
    """
    if cost_price <= 0:
        raise ValueError("Себестоимость должна быть больше нуля")

    if sale_price <= cost_price:
        raise ValueError("Цена продажи должна быть больше себестоимости")

    markup_percent = ((sale_price - cost_price) / cost_price) * 100
    return markup_percent