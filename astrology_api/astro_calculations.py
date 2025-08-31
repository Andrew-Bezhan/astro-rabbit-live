"""
Модуль астрологических расчетов и интерпретации
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import math

from .gpt_astro_client import GPTAstroClient
from utils.logger import setup_logger

logger = setup_logger()


class AstroCalculations:
    """Класс для астрологических расчетов и интерпретации"""
    
    def __init__(self):
        """Инициализация калькулятора"""
        try:
            self.gpt_client = GPTAstroClient()
        except Exception as e:
            logger.warning(f"⚠️ GPT астрологический клиент недоступен: {e}")
            self.gpt_client = None
        
        # Характеристики знаков зодиака
        self.zodiac_characteristics = {
            'Овен ♈': {
                'element': 'Огонь',
                'quality': 'Кардинальный',
                'ruler': 'Марс',
                'business_traits': 'Лидерство, инициативность, конкурентоспособность',
                'strengths': 'Быстрые решения, новаторство, энергичность',
                'challenges': 'Импульсивность, нетерпеливость, конфликтность',
                'best_spheres': ['Технологии', 'Спорт', 'Военная индустрия', 'Стартапы'],
                'colors': ['Красный', 'Оранжевый'],
                'lucky_numbers': [1, 8, 17]
            },
            'Телец ♉': {
                'element': 'Земля',
                'quality': 'Фиксированный',
                'ruler': 'Венера',
                'business_traits': 'Стабильность, практичность, материальная ориентация',
                'strengths': 'Надежность, упорство, финансовая грамотность',
                'challenges': 'Консерватизм, медлительность, упрямство',
                'best_spheres': ['Финансы', 'Недвижимость', 'Сельское хозяйство', 'Роскошь'],
                'colors': ['Зеленый', 'Розовый'],
                'lucky_numbers': [2, 6, 20]
            },
            'Близнецы ♊': {
                'element': 'Воздух',
                'quality': 'Мутабельный',
                'ruler': 'Меркурий',
                'business_traits': 'Коммуникабельность, адаптивность, многозадачность',
                'strengths': 'Гибкость, обучаемость, сетевое мышление',
                'challenges': 'Поверхностность, непостоянство, разбросанность',
                'best_spheres': ['Медиа', 'Образование', 'IT', 'Торговля'],
                'colors': ['Желтый', 'Голубой'],
                'lucky_numbers': [3, 12, 21]
            },
            'Рак ♋': {
                'element': 'Вода',
                'quality': 'Кардинальный',
                'ruler': 'Луна',
                'business_traits': 'Интуитивность, забота о клиентах, семейные ценности',
                'strengths': 'Эмпатия, защита интересов, лояльность',
                'challenges': 'Эмоциональность, обидчивость, консерватизм',
                'best_spheres': ['Общепит', 'Недвижимость', 'Семейный бизнес', 'Забота'],
                'colors': ['Белый', 'Серебряный'],
                'lucky_numbers': [4, 13, 22]
            },
            'Лев ♌': {
                'element': 'Огонь',
                'quality': 'Фиксированный',
                'ruler': 'Солнце',
                'business_traits': 'Харизма, творчество, представительность',
                'strengths': 'Лидерство, вдохновение, щедрость',
                'challenges': 'Гордыня, расточительность, эгоцентризм',
                'best_spheres': ['Развлечения', 'Мода', 'Премиум-сегмент', 'Искусство'],
                'colors': ['Золотой', 'Оранжевый'],
                'lucky_numbers': [5, 14, 23]
            },
            'Дева ♍': {
                'element': 'Земля',
                'quality': 'Мутабельный',
                'ruler': 'Меркурий',
                'business_traits': 'Аналитичность, перфекционизм, систематичность',
                'strengths': 'Точность, эффективность, качество',
                'challenges': 'Критичность, медлительность, тревожность',
                'best_spheres': ['Медицина', 'Аналитика', 'Качество', 'Консалтинг'],
                'colors': ['Серый', 'Темно-синий'],
                'lucky_numbers': [6, 15, 24]
            },
            'Весы ♎': {
                'element': 'Воздух',
                'quality': 'Кардинальный',
                'ruler': 'Венера',
                'business_traits': 'Дипломатичность, эстетика, партнерство',
                'strengths': 'Справедливость, гармония, сотрудничество',
                'challenges': 'Нерешительность, зависимость от других, поверхностность',
                'best_spheres': ['Юриспруденция', 'Дизайн', 'Дипломатия', 'Красота'],
                'colors': ['Голубой', 'Розовый'],
                'lucky_numbers': [7, 16, 25]
            },
            'Скорпион ♏': {
                'element': 'Вода',
                'quality': 'Фиксированный',
                'ruler': 'Плутон',
                'business_traits': 'Интенсивность, проницательность, трансформация',
                'strengths': 'Глубина анализа, решительность, регенерация',
                'challenges': 'Секретность, мстительность, разрушительность',
                'best_spheres': ['Финансы', 'Безопасность', 'Медицина', 'Исследования'],
                'colors': ['Темно-красный', 'Черный'],
                'lucky_numbers': [8, 17, 26]
            },
            'Стрелец ♐': {
                'element': 'Огонь',
                'quality': 'Мутабельный',
                'ruler': 'Юпитер',
                'business_traits': 'Оптимизм, широкий взгляд, международность',
                'strengths': 'Вдохновение, расширение, философия',
                'challenges': 'Переоценка возможностей, безответственность, догматизм',
                'best_spheres': ['Образование', 'Туризм', 'Международная торговля', 'Спорт'],
                'colors': ['Фиолетовый', 'Бирюзовый'],
                'lucky_numbers': [9, 18, 27]
            },
            'Козерог ♑': {
                'element': 'Земля',
                'quality': 'Кардинальный',
                'ruler': 'Сатурн',
                'business_traits': 'Амбициозность, дисциплина, стратегичность',
                'strengths': 'Планирование, авторитет, долгосрочность',
                'challenges': 'Пессимизм, жесткость, ограниченность',
                'best_spheres': ['Управление', 'Строительство', 'Банкинг', 'Государство'],
                'colors': ['Черный', 'Темно-зеленый'],
                'lucky_numbers': [10, 19, 28]
            },
            'Водолей ♒': {
                'element': 'Воздух',
                'quality': 'Фиксированный',
                'ruler': 'Уран',
                'business_traits': 'Инновационность, гуманизм, независимость',
                'strengths': 'Оригинальность, прогрессивность, командность',
                'challenges': 'Непредсказуемость, отстраненность, радикализм',
                'best_spheres': ['Технологии', 'Экология', 'Социальные проекты', 'Наука'],
                'colors': ['Электрик', 'Неон'],
                'lucky_numbers': [11, 20, 29]
            },
            'Рыбы ♓': {
                'element': 'Вода',
                'quality': 'Мутабельный',
                'ruler': 'Нептун',
                'business_traits': 'Интуиция, сострадание, креативность',
                'strengths': 'Адаптивность, вдохновение, милосердие',
                'challenges': 'Неопределенность, иллюзии, избегание ответственности',
                'best_spheres': ['Искусство', 'Медицина', 'Благотворительность', 'Мистика'],
                'colors': ['Морская волна', 'Фиолетовый'],
                'lucky_numbers': [12, 21, 30]
            }
        }
        
        logger.info("⭐ AstroCalculations инициализирован")
    
    def _get_coordinates_by_city(self, city_name: str) -> Dict[str, float]:
        """Получение координат города (упрощенная версия)"""
        # Основные российские города
        cities = {
            'москва': {'latitude': 55.7558, 'longitude': 37.6176},
            'санкт-петербург': {'latitude': 59.9311, 'longitude': 30.3609},
            'спб': {'latitude': 59.9311, 'longitude': 30.3609},
            'екатеринбург': {'latitude': 56.8431, 'longitude': 60.6454},
            'новосибирск': {'latitude': 55.0084, 'longitude': 82.9357},
            'нижний новгород': {'latitude': 56.2965, 'longitude': 43.9361},
            'казань': {'latitude': 55.8304, 'longitude': 49.0661},
            'челябинск': {'latitude': 55.1644, 'longitude': 61.4368},
            'омск': {'latitude': 54.9885, 'longitude': 73.3242},
            'самара': {'latitude': 53.2001, 'longitude': 50.1500},
            'ростов-на-дону': {'latitude': 47.2357, 'longitude': 39.7015}
        }
        
        city_lower = city_name.lower().strip()
        return cities.get(city_lower, {'latitude': 55.7558, 'longitude': 37.6176})  # Москва по умолчанию
    
    async def get_company_natal_chart(self, company_name: str, registration_date: datetime, 
                                    registration_place: str) -> Dict[str, Any]:
        """
        Получение натальной карты компании
        
        Args:
            company_name (str): Название компании
            registration_date (datetime): Дата регистрации
            registration_place (str): Место регистрации
            
        Returns:
            Dict[str, Any]: Натальная карта компании
        """
        try:
            # Получаем координаты места регистрации
            coordinates = None
            if self.gpt_client:
                # GPT API не предоставляет геокодинг, используем фиксированные координаты
                coordinates = self._get_coordinates_by_city(registration_place)
            
            if not coordinates:
                coordinates = {'latitude': 55.7558, 'longitude': 37.6176}  # Москва по умолчанию
            
            natal_chart = {
                'company_name': company_name,
                'registration_date': registration_date.isoformat() if hasattr(registration_date, 'isoformat') else str(registration_date),
                'registration_place': registration_place,
                'coordinates': coordinates,
                'basic_info': self._get_basic_chart_info(registration_date),
                'planetary_positions': {},
                'houses': {},
                'aspects': {}
            }
            
            # Получаем данные от GPT если доступен (НЕ КРИТИЧНО)
            if self.gpt_client:
                try:
                    chart_data = await self.gpt_client.get_birth_chart(
                        registration_date,
                        coordinates['latitude'],
                        coordinates['longitude']
                    )
                    
                    if chart_data:
                        natal_chart.update(chart_data)
                        logger.info(f"🔮 GPT данные добавлены в натальную карту")
                    else:
                        logger.warning(f"⚠️ GPT астрология временно недоступна, используем базовые расчеты")
                except Exception as e:
                    logger.warning(f"⚠️ GPT астрология ошибка (не критично): {type(e).__name__}")
                    # Продолжаем без GPT данных
            
            # Добавляем интерпретацию
            natal_chart['interpretation'] = self._interpret_company_chart(natal_chart)
            
            logger.info(f"🏢 Натальная карта для {company_name} создана успешно")
            return natal_chart
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка создания натальной карты: {e}")
            # Возвращаем базовую карту вместо пустого словаря
            return {
                'company_name': company_name,
                'registration_date': registration_date.isoformat() if hasattr(registration_date, 'isoformat') else str(registration_date),
                'registration_place': registration_place,
                'coordinates': {'latitude': 55.7558, 'longitude': 37.6176},
                'basic_info': self._get_basic_chart_info(registration_date),
                'interpretation': 'Базовый анализ: система временно использует упрощенные расчеты.',
                'error': str(e)
            }
    
    def _get_basic_chart_info(self, birth_date) -> Dict[str, Any]:
        """Получение базовой информации карты"""
        from utils.helpers import get_zodiac_sign, validate_date
        
        # Преобразуем дату если нужно
        if isinstance(birth_date, str):
            date_obj = validate_date(birth_date)
            if not date_obj:
                # Фоллбэк дата
                from datetime import datetime
                date_obj = datetime(2020, 1, 1)
        else:
            date_obj = birth_date
            
        sun_sign = get_zodiac_sign(date_obj)
        characteristics = self.zodiac_characteristics.get(sun_sign, {})
        
        return {
            'sun_sign': sun_sign,
            'element': characteristics.get('element', 'Неизвестно'),
            'quality': characteristics.get('quality', 'Неизвестно'),
            'ruler': characteristics.get('ruler', 'Неизвестно'),
            'business_traits': characteristics.get('business_traits', ''),
            'strengths': characteristics.get('strengths', ''),
            'challenges': characteristics.get('challenges', ''),
            'best_spheres': characteristics.get('best_spheres', []),
            'colors': characteristics.get('colors', []),
            'lucky_numbers': characteristics.get('lucky_numbers', [])
        }
    
    def _interpret_company_chart(self, chart: Dict[str, Any]) -> Dict[str, Any]:
        """Интерпретация натальной карты компании"""
        basic_info = chart.get('basic_info', {})
        sun_sign = basic_info.get('sun_sign', '')
        
        interpretation = {
            'general_character': f"Компания под знаком {sun_sign} обладает характеристиками: {basic_info.get('business_traits', '')}",
            'strengths': f"Сильные стороны: {basic_info.get('strengths', '')}",
            'challenges': f"Потенциальные вызовы: {basic_info.get('challenges', '')}",
            'recommended_spheres': basic_info.get('best_spheres', []),
            'business_style': self._get_business_style(sun_sign),
            'financial_outlook': self._get_financial_outlook(sun_sign),
            'management_style': self._get_management_style(sun_sign),
            'growth_potential': self._get_growth_potential(sun_sign)
        }
        
        return interpretation
    
    def _get_business_style(self, sun_sign: str) -> str:
        """Определение стиля ведения бизнеса"""
        styles = {
            'Овен ♈': 'Агрессивный, быстрый, инновационный подход',
            'Телец ♉': 'Консервативный, устойчивый, ориентированный на качество',
            'Близнецы ♊': 'Гибкий, коммуникационный, многопрофильный',
            'Рак ♋': 'Семейный, защитный, клиентоориентированный',
            'Лев ♌': 'Представительский, творческий, статусный',
            'Дева ♍': 'Аналитический, систематический, качественный',
            'Весы ♎': 'Партнерский, эстетический, сбалансированный',
            'Скорпион ♏': 'Интенсивный, трансформационный, глубокий',
            'Стрелец ♐': 'Экспансивный, международный, философский',
            'Козерог ♑': 'Структурированный, амбициозный, долгосрочный',
            'Водолей ♒': 'Инновационный, прогрессивный, нестандартный',
            'Рыбы ♓': 'Интуитивный, адаптивный, креативный'
        }
        return styles.get(sun_sign, 'Требует индивидуального анализа')
    
    def _get_financial_outlook(self, sun_sign: str) -> str:
        """Финансовые перспективы по знаку"""
        outlooks = {
            'Овен ♈': 'Быстрая прибыль, рискованные инвестиции, импульсивные решения',
            'Телец ♉': 'Стабильный доход, долгосрочные инвестиции, накопления',
            'Близнецы ♊': 'Множественные источники дохода, торговая прибыль',
            'Рак ♋': 'Семейный капитал, недвижимость, защищенные активы',
            'Лев ♌': 'Престижные инвестиции, развлекательный бизнес, роскошь',
            'Дева ♍': 'Детализированный учет, экономия, качественные активы',
            'Весы ♎': 'Партнерские инвестиции, эстетические ценности, баланс',
            'Скорпион ♏': 'Глубокие инвестиции, трансформация активов, секретность',
            'Стрелец ♐': 'Международные инвестиции, образовательные проекты, рост',
            'Козерог ♑': 'Долгосрочное планирование, структурированные активы, карьерный рост',
            'Водолей ♒': 'Инновационные инвестиции, технологии, нестандартные решения',
            'Рыбы ♓': 'Интуитивные инвестиции, творческие проекты, благотворительность'
        }
        return outlooks.get(sun_sign, 'Требует детального анализа')
    
    def _get_management_style(self, sun_sign: str) -> str:
        """Стиль управления по знаку"""
        styles = {
            'Овен ♈': 'Директивный, быстрый, инициативный лидер',
            'Телец ♉': 'Стабильный, практичный, упорный руководитель',
            'Близнецы ♊': 'Коммуникативный, гибкий, многозадачный менеджер',
            'Рак ♋': 'Заботливый, защищающий, семейный лидер',
            'Лев ♌': 'Харизматичный, вдохновляющий, творческий руководитель',
            'Дева ♍': 'Аналитичный, систематичный, перфекционистский менеджер',
            'Весы ♎': 'Дипломатичный, справедливый, балансирующий лидер',
            'Скорпион ♏': 'Интенсивный, проницательный, трансформирующий руководитель',
            'Стрелец ♐': 'Вдохновляющий, расширяющий, философский лидер',
            'Козерог ♑': 'Структурированный, амбициозный, дисциплинированный руководитель',
            'Водолей ♒': 'Инновационный, независимый, прогрессивный лидер',
            'Рыбы ♓': 'Интуитивный, адаптивный, сочувствующий руководитель'
        }
        return styles.get(sun_sign, 'Индивидуальный стиль руководства')
    
    def _get_growth_potential(self, sun_sign: str) -> str:
        """Потенциал роста по знаку"""
        potentials = {
            'Овен ♈': 'Быстрый рост через инновации и конкуренцию',
            'Телец ♉': 'Устойчивый рост через качество и надежность',
            'Близнецы ♊': 'Рост через коммуникации и адаптацию',
            'Рак ♋': 'Органический рост через заботу о клиентах',
            'Лев ♌': 'Рост через креативность и представительность',
            'Дева ♍': 'Рост через совершенствование и эффективность',
            'Весы ♎': 'Рост через партнерства и гармонию',
            'Скорпион ♏': 'Трансформационный рост через глубокие изменения',
            'Стрелец ♐': 'Экспансивный рост через расширение и образование',
            'Козерог ♑': 'Стратегический рост через планирование и структуру',
            'Водолей ♒': 'Революционный рост через инновации',
            'Рыбы ♓': 'Интуитивный рост через творчество и адаптацию'
        }
        return potentials.get(sun_sign, 'Уникальный путь развития')
    
    async def get_current_transits(self, company_chart: Dict[str, Any]) -> Dict[str, Any]:
        """
        Получение текущих транзитов для компании
        
        Args:
            company_chart (Dict): Натальная карта компании
            
        Returns:
            Dict[str, Any]: Анализ транзитов
        """
        try:
            if not self.gpt_client:
                return self._get_basic_transits()
            
            registration_date = datetime.fromisoformat(
                company_chart.get('registration_date', datetime.now().isoformat())
            )
            coordinates = company_chart.get('coordinates', {'latitude': 55.7558, 'longitude': 37.6176})
            
            # GPT-based транзиты (упрощенная версия)
            transit_data = self._get_basic_transits()
            
            if transit_data:
                # Добавляем интерпретацию транзитов
                transit_data['business_interpretation'] = self._interpret_business_transits(transit_data)
            
            return transit_data
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения транзитов: {e}")
            return self._get_basic_transits()
    
    def _get_basic_transits(self) -> Dict[str, Any]:
        """Базовые транзиты без API"""
        return {
            'current_date': datetime.now().isoformat(),
            'general_influence': 'Период благоприятен для планирования и анализа',
            'business_opportunities': 'Время для укрепления позиций и развития партнерств',
            'potential_challenges': 'Возможны задержки в коммуникациях',
            'recommendations': 'Сосредоточьтесь на внутренних процессах и качестве'
        }
    
    def _interpret_business_transits(self, transit_data: Dict[str, Any]) -> Dict[str, Any]:
        """Интерпретация транзитов для бизнеса"""
        return {
            'financial_impact': 'Анализ влияния на финансы',
            'operational_impact': 'Влияние на операционную деятельность',
            'strategic_opportunities': 'Стратегические возможности',
            'risk_factors': 'Факторы риска',
            'timing_recommendations': 'Рекомендации по времени'
        }
    
    async def analyze_compatibility(self, company_sign: str, person_sign: str, 
                                  relationship_type: str) -> Dict[str, Any]:
        """
        Анализ совместимости между компанией и человеком
        
        Args:
            company_sign (str): Знак зодиака компании
            person_sign (str): Знак зодиака человека
            relationship_type (str): Тип отношений (employee/client/partner)
            
        Returns:
            Dict[str, Any]: Анализ совместимости
        """
        try:
            compatibility = {
                'company_sign': company_sign,
                'person_sign': person_sign,
                'relationship_type': relationship_type,
                'compatibility_score': self._calculate_compatibility_score(company_sign, person_sign),
                'strengths': self._get_compatibility_strengths(company_sign, person_sign, relationship_type),
                'challenges': self._get_compatibility_challenges(company_sign, person_sign, relationship_type),
                'recommendations': self._get_compatibility_recommendations(company_sign, person_sign, relationship_type)
            }
            
            # Получаем данные от API если доступен
            if self.gpt_client:
                # GPT-based совместимость (упрощенная версия) 
                api_compatibility = self._calculate_basic_compatibility(company_sign, person_sign)
                if api_compatibility:
                    compatibility['detailed_analysis'] = api_compatibility
            
            logger.info(f"💕 Анализ совместимости {company_sign} и {person_sign} завершен")
            return compatibility
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа совместимости: {e}")
            return {}
    
    def _calculate_basic_compatibility(self, sign1: str, sign2: str) -> Dict[str, Any]:
        """Упрощенный расчет совместимости знаков"""
        # Совместимость по стихиям
        elements = {
            'Овен ♈': 'Огонь', 'Лев ♌': 'Огонь', 'Стрелец ♐': 'Огонь',
            'Телец ♉': 'Земля', 'Дева ♍': 'Земля', 'Козерог ♑': 'Земля',
            'Близнецы ♊': 'Воздух', 'Весы ♎': 'Воздух', 'Водолей ♒': 'Воздух',
            'Рак ♋': 'Вода', 'Скорпион ♏': 'Вода', 'Рыбы ♓': 'Вода'
        }
        
        element1 = elements.get(sign1, 'Неизвестно')
        element2 = elements.get(sign2, 'Неизвестно')
        
        # Матрица совместимости стихий
        compatibility_matrix = {
            ('Огонь', 'Огонь'): 85,
            ('Огонь', 'Воздух'): 80,
            ('Огонь', 'Земля'): 60,
            ('Огонь', 'Вода'): 45,
            ('Земля', 'Земля'): 85,
            ('Земля', 'Вода'): 75,
            ('Воздух', 'Воздух'): 85,
            ('Воздух', 'Огонь'): 80,
            ('Вода', 'Вода'): 85,
            ('Вода', 'Земля'): 75
        }
        
        score = compatibility_matrix.get((element1, element2), 
                compatibility_matrix.get((element2, element1), 50))
        
        return {
            'compatibility_score': score,
            'element_interaction': f"{element1} и {element2}",
            'summary': f"Совместимость {score}% - {'отличная' if score > 80 else 'хорошая' if score > 65 else 'средняя' if score > 50 else 'сложная'}"
        }
    
    def _calculate_compatibility_score(self, sign1: str, sign2: str) -> int:
        """Расчет оценки совместимости (упрощенный)"""
        # Элементы знаков
        elements = {
            'Овен ♈': 'Огонь', 'Лев ♌': 'Огонь', 'Стрелец ♐': 'Огонь',
            'Телец ♉': 'Земля', 'Дева ♍': 'Земля', 'Козерог ♑': 'Земля',
            'Близнецы ♊': 'Воздух', 'Весы ♎': 'Воздух', 'Водолей ♒': 'Воздух',
            'Рак ♋': 'Вода', 'Скорпион ♏': 'Вода', 'Рыбы ♓': 'Вода'
        }
        
        element1 = elements.get(sign1, 'Неизвестно')
        element2 = elements.get(sign2, 'Неизвестно')
        
        # Совместимость элементов
        if element1 == element2:
            return 85  # Очень хорошая совместимость
        elif (element1 in ['Огонь', 'Воздух'] and element2 in ['Огонь', 'Воздух']) or \
             (element1 in ['Земля', 'Вода'] and element2 in ['Земля', 'Вода']):
            return 75  # Хорошая совместимость
        else:
            return 60  # Средняя совместимость
    
    def _get_compatibility_strengths(self, company_sign: str, person_sign: str, 
                                   relationship_type: str) -> List[str]:
        """Сильные стороны совместимости"""
        return [
            f"Взаимное понимание между {company_sign} и {person_sign}",
            f"Эффективное сотрудничество в роли {relationship_type}",
            "Дополняющие друг друга качества",
            "Потенциал для долгосрочных отношений"
        ]
    
    def _get_compatibility_challenges(self, company_sign: str, person_sign: str, 
                                    relationship_type: str) -> List[str]:
        """Потенциальные вызовы совместимости"""
        return [
            "Возможные различия в подходах к работе",
            "Необходимость адаптации стилей общения",
            "Потенциальные конфликты интересов"
        ]
    
    def _get_compatibility_recommendations(self, company_sign: str, person_sign: str, 
                                         relationship_type: str) -> List[str]:
        """Рекомендации по совместимости"""
        return [
            "Установите четкие границы и ожидания",
            "Используйте сильные стороны каждой стороны",
            "Регулярно обсуждайте цели и приоритеты",
            "Будьте терпеливы к различиям в стилях работы"
        ]
