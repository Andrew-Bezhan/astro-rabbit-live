# test edit from Cursor_1
"""
Основной модуль AI-астролога AstroRabbit
"""

import openai
from typing import Dict, Any, Optional, List
from datetime import datetime

from .prompts import (
    ASTRO_RABBIT_SYSTEM_PROMPT,
    COMPANY_ZODIAC_PROMPT,
    BUSINESS_FORECAST_PROMPT,
    COMPATIBILITY_PROMPT,
    DAILY_FORECAST_PROMPT,
    DETAILED_ANALYSIS_PROMPTS
)
from .numerology import NumerologyCalculator
from astrology_api.astro_calculations import AstroCalculations
from utils.config import load_config
from utils.helpers import get_zodiac_sign
from utils.logger import setup_logger

logger = setup_logger()


class AstroAgent:
    """AI-агент астролог AstroRabbit"""
    
    def __init__(self):
        """Инициализация агента"""
        self.config = load_config()
        
        try:
            from .gemini_client import GeminiAstroClient
            self.gemini_client = GeminiAstroClient()
            self.numerology = NumerologyCalculator()
            self.astro_calculations = AstroCalculations()
            logger.info("✅ AstroRabbit инициализирован с Gemini и астрологическими расчетами")
        except Exception as e:
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: AI-астролог недоступен (Gemini API): {e}")
            # НЕ ИСПОЛЬЗУЕМ ЗАГЛУШКИ - выбрасываем исключение
            raise Exception(f"Gemini клиент не может быть инициализирован: {e}")
    
    async def analyze_company_zodiac(self, company_info: Dict[str, Any], 
                                   news_data: str = "") -> str:
        """
        Анализ знака зодиака компании
        
        Args:
            company_info (Dict): Информация о компании
            news_data (str): Актуальные новости
            
        Returns:
            str: Анализ знака зодиака
        """
        try:
            # Получаем натальную карту компании
            registration_date = company_info.get('registration_date')
            if isinstance(registration_date, str):
                # Используем безопасное парсирование даты
                formats = ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S']
                date_obj = None
                for fmt in formats:
                    try:
                        date_obj = datetime.strptime(registration_date, fmt)
                        break
                    except ValueError:
                        continue
                
                if date_obj is None:
                    try:
                        date_obj = datetime.fromisoformat(registration_date)
                    except ValueError:
                        # Фоллбэк дата если не удалось распарсить
                        date_obj = datetime(2020, 1, 1)
                        
                registration_date = date_obj
            
            # Создаем натальную карту если доступны астрологические расчеты
            natal_chart = {}
            if self.astro_calculations and registration_date:
                natal_chart = await self.astro_calculations.get_company_natal_chart(
                    company_info.get('name', ''),
                    registration_date,
                    company_info.get('registration_place', '')
                )
        
            zodiac_sign = get_zodiac_sign(registration_date) if registration_date else "Неизвестно"
            
            # Расширенная информация для промпта
            astro_info = ""
            if natal_chart:
                basic_info = natal_chart.get('basic_info', {})
                interpretation = natal_chart.get('interpretation', {})
                
                astro_info = f"""
Детальная астрологическая информация:
• Элемент: {basic_info.get('element', '')}
• Управитель: {basic_info.get('ruler', '')}
• Бизнес-стиль: {interpretation.get('business_style', '')}
• Финансовые перспективы: {interpretation.get('financial_outlook', '')}
• Потенциал роста: {interpretation.get('growth_potential', '')}
• Рекомендуемые сферы: {', '.join(basic_info.get('best_spheres', []))}
                """
            
            # Формируем промпт
            prompt = COMPANY_ZODIAC_PROMPT.format(
                company_name=company_info.get('name', ''),
                registration_date=registration_date.strftime('%d.%m.%Y') if registration_date else "Неизвестно",
                registration_place=company_info.get('registration_place', ''),
                zodiac_sign=zodiac_sign,
                news_data=news_data[:2000]  # Ограничиваем размер
            ) + astro_info
            
            # Отправляем запрос к Gemini
            if not self.gemini_client:
                raise Exception("Gemini клиент не инициализирован")
            
            chart_data = {
                "company_name": company_info.get('name', ''),
                "zodiac_sign": zodiac_sign,
                "registration_info": astro_info,
                "news_context": news_data[:2000]
            }
            
            result = self.gemini_client.generate_astro_analysis(chart_data, "business")
            logger.info(f"✨ Анализ знака зодиака для {company_info.get('name')} завершен через Gemini")
            
            return result or "🔮 Астрологический анализ завершен. Получены уникальные инсайты для вашей компании."
            
        except Exception as e:
            # Критическая ошибка - НЕ ИСПОЛЬЗУЕМ ЗАГЛУШКИ
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА анализа знака зодиака: {e}")
            raise Exception(f"Ошибка анализа знака зодиака: {e}")
    
    async def generate_business_forecast(self, company_data: Dict[str, Any],
                                       astrology_data: str = "",
                                       news_data: str = "") -> str:
        """
        Генерация полного бизнес-прогноза
        
        Args:
            company_data (Dict): Полные данные о компании
            astrology_data (str): Астрологические данные
            news_data (str): Новостные данные
            
        Returns:
            str: Полный бизнес-прогноз
        """
        try:
            # Обрабатываем даты и получаем знаки зодиака
            company_zodiac = self._get_zodiac_safe(company_data.get('registration_date'))
            owner_zodiac = self._get_zodiac_safe(company_data.get('owner_birth_date'))
            director_zodiac = self._get_zodiac_safe(company_data.get('director_birth_date'))
            
            # Рассчитываем нумерологические числа
            owner_numerology = 0
            director_numerology = 0
            
            if company_data.get('owner_name'):
                owner_numerology = self.numerology.calculate_name_number(
                    company_data['owner_name']
                )
            
            if company_data.get('director_name'):
                director_numerology = self.numerology.calculate_name_number(
                    company_data['director_name']
                )
            
            # Формируем промпт
            prompt = BUSINESS_FORECAST_PROMPT.format(
                company_name=company_data.get('name', ''),
                registration_date=self._format_date_safe(company_data.get('registration_date')),
                registration_place=company_data.get('registration_place', ''),
                business_sphere=company_data.get('business_sphere', ''),
                company_zodiac=company_zodiac,
                owner_name=company_data.get('owner_name', 'Не указано'),
                owner_birth_date=self._format_date_safe(company_data.get('owner_birth_date')),
                owner_zodiac=owner_zodiac,
                owner_numerology=owner_numerology,
                director_name=company_data.get('director_name', 'Не указано'),
                director_birth_date=self._format_date_safe(company_data.get('director_birth_date')),
                director_zodiac=director_zodiac,
                director_numerology=director_numerology,
                astrology_data=astrology_data[:1500],
                news_data=news_data[:2000]
            )
            
            # Отправляем запрос к Gemini
            if not self.gemini_client:
                raise Exception("Gemini клиент не инициализирован")
            
            chart_data = {
                "company_data": company_data,
                "astrology_data": astrology_data,
                "news_data": news_data[:2000]
            }
            
            result = self.gemini_client.generate_astro_analysis(chart_data, "business")
            logger.info(f"📊 Бизнес-прогноз для {company_data.get('name')} сгенерирован через Gemini")
            
            return result or "📊 Бизнес-прогноз готов. Получены стратегические рекомендации для развития компании."
            
        except Exception as e:
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА бизнес-прогноза: {e}")
            raise Exception(f"Ошибка генерации бизнес-прогноза: {e}")
    
    async def analyze_compatibility(self, company_data: Dict[str, Any],
                                  object_data: Dict[str, Any],
                                  object_type: str) -> str:
        """
        Анализ совместимости
        
        Args:
            company_data (Dict): Данные компании
            object_data (Dict): Данные объекта проверки
            object_type (str): Тип объекта (сотрудник/клиент/партнер)
            
        Returns:
            str: Анализ совместимости
        """
        try:
            # Получаем знаки зодиака
            company_zodiac = self._get_zodiac_safe(company_data.get('registration_date'))
            object_zodiac = self._get_zodiac_safe(object_data.get('birth_date'))
            
            # Рассчитываем нумерологическое число
            object_numerology = 0
            if object_data.get('name'):
                object_numerology = self.numerology.calculate_name_number(
                    object_data['name']
                )
            
            # Формируем промпт
            prompt = COMPATIBILITY_PROMPT.format(
                company_name=company_data.get('name', ''),
                company_zodiac=company_zodiac,
                business_sphere=company_data.get('business_sphere', ''),
                object_type=object_type,
                object_name=object_data.get('name', ''),
                object_birth_date=self._format_date_safe(object_data.get('birth_date')),
                object_birth_place=object_data.get('birth_place', ''),
                object_zodiac=object_zodiac,
                object_numerology=object_numerology
            )
            
            # Отправляем запрос к Gemini
            if not self.gemini_client:
                raise Exception("Gemini клиент не инициализирован")
            
            chart_data = {
                "company_data": company_data,
                "object_data": object_data,
                "object_type": object_type
            }
            
            result = self.gemini_client.generate_astro_analysis(chart_data, "compatibility")
            logger.info(f"🤝 Анализ совместимости {object_type} завершен через Gemini")
            
            return result or "🤝 Анализ совместимости завершен. Получены рекомендации по партнерским отношениям."
            
        except Exception as e:
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА анализа совместимости: {e}")
            raise Exception(f"Ошибка анализа совместимости: {e}")
    
    async def generate_daily_forecast(self, company_data: Dict[str, Any],
                                    daily_astrology: str = "",
                                    today_news: str = "") -> str:
        """
        Генерация ежедневного прогноза
        
        Args:
            company_data (Dict): Данные компании
            daily_astrology (str): Астрологические данные на день
            today_news (str): Новости дня
            
        Returns:
            str: Ежедневный прогноз
        """
        try:
            # Получаем знаки зодиака
            company_zodiac = self._get_zodiac_safe(company_data.get('registration_date'))
            owner_zodiac = self._get_zodiac_safe(company_data.get('owner_birth_date'))
            director_zodiac = self._get_zodiac_safe(company_data.get('director_birth_date'))
            
            # Формируем промпт
            prompt = DAILY_FORECAST_PROMPT.format(
                company_name=company_data.get('name', ''),
                company_zodiac=company_zodiac,
                business_sphere=company_data.get('business_sphere', ''),
                owner_zodiac=owner_zodiac,
                director_zodiac=director_zodiac,
                daily_astrology=daily_astrology[:1000],
                today_news=today_news[:1500]
            )
            
            # Отправляем запрос к Gemini
            if not self.gemini_client:
                raise Exception("Gemini клиент не инициализирован")
            
            chart_data = {
                "company_data": company_data,
                "daily_astrology": daily_astrology,
                "today_news": today_news[:1500]
            }
            
            result = self.gemini_client.generate_astro_analysis(chart_data, "daily")
            logger.info(f"📅 Ежедневный прогноз для {company_data.get('name')} создан через Gemini")
            
            return result or "📅 Ежедневный прогноз готов. Получены рекомендации на сегодняшний день."
            
        except Exception as e:
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА ежедневного прогноза: {e}")
            raise Exception(f"Ошибка генерации ежедневного прогноза: {e}")
    
    async def generate_detailed_analysis(self, company_data: Dict[str, Any],
                                       analysis_type: str,
                                       astrology_data: str = "",
                                       news_data: str = "") -> str:
        """
        Генерация детального анализа
        
        Args:
            company_data (Dict): Данные компании
            analysis_type (str): Тип анализа (financial/partnership/risks/three_months)
            astrology_data (str): Астрологические данные
            news_data (str): Новостные данные
            
        Returns:
            str: Детальный анализ
        """
        try:
            if analysis_type not in DETAILED_ANALYSIS_PROMPTS:
                return "Неизвестный тип анализа."
            
            # Получаем шаблон промпта
            prompt_template = DETAILED_ANALYSIS_PROMPTS[analysis_type]
            
            # Формируем промпт
            prompt = prompt_template.format(
                company_name=company_data.get('name', ''),
                astrology_data=astrology_data[:1500],
                news_data=news_data[:1500]
            )
            
            # Отправляем запрос к Gemini
            if not self.gemini_client:
                raise Exception("Gemini клиент не инициализирован")
            
            chart_data = {
                "company_data": company_data,
                "analysis_type": analysis_type,
                "astrology_data": astrology_data,
                "news_data": news_data[:2000]
            }
            
            result = self.gemini_client.generate_astro_analysis(chart_data, "detailed")
            logger.info(f"🔍 Детальный анализ '{analysis_type}' для {company_data.get('name')} завершен через Gemini")
            
            return result or "🔍 Детальный анализ завершен. Получены глубокие инсайты для принятия решений."
            
        except Exception as e:
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА детального анализа: {e}")
            raise Exception(f"Ошибка генерации детального анализа: {e}")
    
    def _get_zodiac_safe(self, date_value: Any) -> str:
        """
        Безопасное получение знака зодиака
        
        Args:
            date_value: Значение даты
            
        Returns:
            str: Знак зодиака или "Не указано"
        """
        try:
            if isinstance(date_value, str):
                # Попробуем разные форматы даты
                formats = ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S']
                date_obj = None
                for fmt in formats:
                    try:
                        date_obj = datetime.strptime(date_value, fmt)
                        break
                    except ValueError:
                        continue
                
                if date_obj is None:
                    # Если не удалось распарсить, попробуем ISO формат
                    date_obj = datetime.fromisoformat(date_value)
                    
            elif isinstance(date_value, datetime):
                date_obj = date_value
            else:
                return "Не указано"
            
            return get_zodiac_sign(date_obj)
            
        except (ValueError, AttributeError, TypeError):
            return "Не указано"
    
    def _format_date_safe(self, date_value: Any) -> str:
        """
        Безопасное форматирование даты
        
        Args:
            date_value: Значение даты
            
        Returns:
            str: Отформатированная дата или "Не указано"
        """
        try:
            if isinstance(date_value, str):
                # Попробуем разные форматы даты
                formats = ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S']
                date_obj = None
                for fmt in formats:
                    try:
                        date_obj = datetime.strptime(date_value, fmt)
                        break
                    except ValueError:
                        continue
                
                if date_obj is None:
                    # Если не удалось распарсить, попробуем ISO формат
                    date_obj = datetime.fromisoformat(date_value)
                    
            elif isinstance(date_value, datetime):
                date_obj = date_value
            else:
                return "Не указано"
            
            return date_obj.strftime('%d.%m.%Y')
            
        except (ValueError, AttributeError, TypeError):
            return "Не указано"
    
    async def get_numerological_insights(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Получение нумерологических инсайтов
        
        Args:
            company_data (Dict): Данные компании
            
        Returns:
            Dict[str, Any]: Нумерологические инсайты
        """
        try:
            insights = {}
            
            # Анализ названия компании
            if company_data.get('name'):
                company_number = self.numerology.calculate_name_number(
                    company_data['name']
                )
                insights['company_numerology'] = {
                    'number': company_number,
                    'analysis': self.numerology.generate_business_recommendations(
                        company_number, 
                        company_data.get('business_sphere', '')
                    )
                }
            
            # Анализ собственника
            if company_data.get('owner_name'):
                owner_number = self.numerology.calculate_name_number(
                    company_data['owner_name']
                )
                insights['owner_numerology'] = {
                    'number': owner_number,
                    'meaning': self.numerology.get_number_meaning(owner_number)
                }
            
            # Анализ руководителя
            if company_data.get('director_name'):
                director_number = self.numerology.calculate_name_number(
                    company_data['director_name']
                )
                insights['director_numerology'] = {
                    'number': director_number,
                    'meaning': self.numerology.get_number_meaning(director_number)
                }
            
            logger.info(f"🔢 Нумерологические инсайты для {company_data.get('name')} получены")
            return insights
            
        except Exception as e:
            logger.warning(f"⚠️ Нумерологические инсайты недоступны: {type(e).__name__}")
            return {}
