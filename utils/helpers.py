"""
Вспомогательные функции для проекта
"""

import re
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class CompanyInfo:
    """Структура данных о компании"""
    name: str
    registration_date: datetime
    registration_place: str
    business_sphere: Optional[str] = None
    owner_name: Optional[str] = None
    owner_birth_date: Optional[datetime] = None
    director_name: Optional[str] = None
    director_birth_date: Optional[datetime] = None


def validate_date(date_string: str) -> Optional[datetime]:
    """
    Валидация и преобразование строки даты
    
    Args:
        date_string (str): Строка с датой
        
    Returns:
        Optional[datetime]: Объект datetime или None
    """
    date_formats = [
        "%d.%m.%Y",
        "%d/%m/%Y", 
        "%Y-%m-%d",
        "%d-%m-%Y"
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_string.strip(), fmt)
        except ValueError:
            continue
    
    return None


def clean_company_name(name: str) -> str:
    """
    Очистка названия компании от лишних символов
    
    Args:
        name (str): Исходное название
        
    Returns:
        str: Очищенное название
    """
    # Удаляем лишние пробелы и приводим к единому формату
    cleaned = re.sub(r'\s+', ' ', name.strip())
    
    # Приводим ООО, ИП и другие формы к стандартному виду
    cleaned = re.sub(r'^(ооо|оао|зао|пао)\s+', 'ООО ', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^(ип)\s+', 'ИП ', cleaned, flags=re.IGNORECASE)
    
    return cleaned


def get_zodiac_sign(birth_date: datetime) -> str:
    """
    Определение знака зодиака по дате рождения
    
    Args:
        birth_date (datetime): Дата рождения
        
    Returns:
        str: Название знака зодиака
    """
    month = birth_date.month
    day = birth_date.day
    
    zodiac_signs = {
        (3, 21, 4, 19): "Овен ♈",
        (4, 20, 5, 20): "Телец ♉", 
        (5, 21, 6, 20): "Близнецы ♊",
        (6, 21, 7, 22): "Рак ♋",
        (7, 23, 8, 22): "Лев ♌",
        (8, 23, 9, 22): "Дева ♍",
        (9, 23, 10, 22): "Весы ♎",
        (10, 23, 11, 21): "Скорпион ♏",
        (11, 22, 12, 21): "Стрелец ♐",
        (12, 22, 12, 31): "Козерог ♑",
        (1, 1, 1, 19): "Козерог ♑",
        (1, 20, 2, 18): "Водолей ♒",
        (2, 19, 3, 20): "Рыбы ♓"
    }
    
    for (start_month, start_day, end_month, end_day), sign in zodiac_signs.items():
        if ((month == start_month and day >= start_day) or 
            (month == end_month and day <= end_day)):
            return sign
    
    return "Неизвестно"


def calculate_numerology_number(name: str) -> int:
    """
    Расчет нумерологического числа по имени
    
    Args:
        name (str): Имя для расчета
        
    Returns:
        int: Нумерологическое число (1-9)
    """
    # Соответствие букв и чисел для русского алфавита
    letter_values = {
        'а': 1, 'б': 2, 'в': 6, 'г': 3, 'д': 4, 'е': 5, 'ё': 5, 'ж': 2, 'з': 7,
        'и': 1, 'й': 1, 'к': 2, 'л': 2, 'м': 4, 'н': 5, 'о': 7, 'п': 8, 'р': 2,
        'с': 3, 'т': 4, 'у': 6, 'ф': 8, 'х': 5, 'ц': 3, 'ч': 7, 'ш': 2, 'щ': 9,
        'ъ': 1, 'ы': 1, 'ь': 1, 'э': 6, 'ю': 7, 'я': 2
    }
    
    # Приводим к нижнему регистру и убираем пробелы
    clean_name = re.sub(r'[^а-яё]', '', name.lower())
    
    # Суммируем значения букв
    total = sum(letter_values.get(char, 0) for char in clean_name)
    
    # Приводим к однозначному числу
    while total > 9:
        total = sum(int(digit) for digit in str(total))
    
    return total


def format_business_sphere(sphere: str) -> str:
    """
    Форматирование сферы деятельности
    
    Args:
        sphere (str): Сфера деятельности
        
    Returns:
        str: Отформатированная сфера
    """
    sphere_mapping = {
        "строительство": "Строительство и промышленность",
        "промышленность": "Строительство и промышленность", 
        "финансы": "Финансы и инвестиции",
        "инвестиции": "Финансы и инвестиции",
        "торговля": "Торговля и сфера услуг",
        "услуги": "Торговля и сфера услуг",
        "технологии": "Технологии и телекоммуникации",
        "телекоммуникации": "Технологии и телекоммуникации",
        "государственный": "Государственный сектор и социальная сфера",
        "социальная": "Государственный сектор и социальная сфера",
        "энергетика": "Энергетика (Energy)"
    }
    
    sphere_lower = sphere.lower()
    for key, value in sphere_mapping.items():
        if key in sphere_lower:
            return value
    
    return sphere


def is_valid_russian_name(name: str) -> bool:
    """
    Проверка, является ли строка валидным русским именем
    
    Args:
        name (str): Проверяемое имя
        
    Returns:
        bool: True если имя валидно
    """
    # Проверяем, что имя содержит только русские буквы, пробелы и дефисы
    pattern = r'^[А-Яа-яЁё\s\-]+$'
    return bool(re.match(pattern, name.strip())) and len(name.strip()) >= 2




