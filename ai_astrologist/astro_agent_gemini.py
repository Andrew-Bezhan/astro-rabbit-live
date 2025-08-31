"""
AI-астролог для анализа компаний и персональных прогнозов
Полная версия с Google Gemini вместо OpenAI
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from .prompts import ASTRO_RABBIT_SYSTEM_PROMPT
from .numerology import NumerologyCalculator
from .gemini_client import GeminiAstroClient
from astrology_api.astro_calculations import AstroCalculations
from utils.config import load_config
from utils.logger import setup_logger

logger = setup_logger()


class AstroAgent:
    """
    AI-астролог с использованием Google Gemini
    """
    
    def __init__(self):
        """Инициализация агента"""
        self.config = load_config()
        
        try:
            self.gemini_client = GeminiAstroClient()
            self.numerology = NumerologyCalculator()
            self.astro_calculations = AstroCalculations()
            logger.info("✅ AstroRabbit инициализирован с Gemini и астрологическими расчетами")
        except Exception as e:
            logger.warning(f"⚠️ AI-астролог недоступен (Gemini API): {type(e).__name__}")
            self.gemini_client = None
            self.numerology = NumerologyCalculator()
            self.astro_calculations = AstroCalculations()
    
    async def analyze_company_zodiac(self, company_info: Dict[str, Any], 
                                   news_data: str = "") -> str:
        """Анализ знака зодиака компании через Gemini"""
        try:
            if not self.gemini_client:
                return "❌ AI сервис недоступен"
            
            zodiac_sign = self._get_zodiac_safe(company_info.get('registration_date'))
            
            chart_data = {
                "company_name": company_info.get('name', ''),
                "zodiac_sign": zodiac_sign,
                "registration_date": str(company_info.get('registration_date', '')),
                "sphere": company_info.get('sphere', ''),
                "news_context": news_data[:2000] if news_data else ''
            }
            
            result = self.gemini_client.generate_astro_analysis(chart_data, "business")
            logger.info(f"✨ Анализ знака зодиака для {company_info.get('name')} завершен через Gemini")
            
            return result or "❌ Не удалось получить анализ"
            
        except Exception as e:
            logger.warning(f"⚠️ Анализ знака зодиака недоступен (Gemini API): {type(e).__name__}")
            return "Извините, произошла ошибка при анализе знака зодиака компании."
    
    async def generate_business_forecast(self, company_data: Dict[str, Any],
                                       astrology_data: str = "",
                                       news_data: str = "") -> str:
        """Генерация бизнес-прогноза через Gemini"""
        try:
            if not self.gemini_client:
                return "❌ AI сервис недоступен"
            
            chart_data = {
                "company_data": company_data,
                "astrology_data": astrology_data,
                "news_data": news_data[:2000]
            }
            
            result = self.gemini_client.generate_astro_analysis(chart_data, "business")
            logger.info(f"📊 Бизнес-прогноз для {company_data.get('name')} сгенерирован через Gemini")
            
            return result or "Прогноз недоступен"
            
        except Exception as e:
            logger.warning(f"⚠️ Бизнес-прогноз недоступен (Gemini API): {type(e).__name__}")
            return "Извините, произошла ошибка при генерации бизнес-прогноза."
    
    async def analyze_compatibility(self, company_data: Dict[str, Any],
                                  object_data: Dict[str, Any],
                                  object_type: str) -> str:
        """Анализ совместимости через Gemini"""
        try:
            if not self.gemini_client:
                return "❌ AI сервис недоступен"
            
            chart_data = {
                "company_data": company_data,
                "object_data": object_data,
                "object_type": object_type
            }
            
            result = self.gemini_client.generate_astro_analysis(chart_data, "compatibility")
            logger.info(f"🤝 Анализ совместимости {object_type} завершен через Gemini")
            
            return result or "Анализ совместимости недоступен"
            
        except Exception as e:
            logger.warning(f"⚠️ Анализ совместимости недоступен (Gemini API): {type(e).__name__}")
            return "Извините, произошла ошибка при анализе совместимости."
    
    async def generate_daily_forecast(self, company_data: Dict[str, Any],
                                    daily_astrology: str = "",
                                    today_news: str = "") -> str:
        """Генерация ежедневного прогноза через Gemini"""
        try:
            if not self.gemini_client:
                return "❌ AI сервис недоступен"
            
            chart_data = {
                "company_data": company_data,
                "daily_astrology": daily_astrology,
                "today_news": today_news[:1500]
            }
            
            result = self.gemini_client.generate_astro_analysis(chart_data, "daily")
            logger.info(f"📅 Ежедневный прогноз для {company_data.get('name')} создан через Gemini")
            
            return result or "Ежедневный прогноз недоступен"
            
        except Exception as e:
            logger.warning(f"⚠️ Ежедневный прогноз недоступен (Gemini API): {type(e).__name__}")
            return "Извините, произошла ошибка при генерации ежедневного прогноза."
    
    async def generate_detailed_analysis(self, company_data: Dict[str, Any],
                                       analysis_type: str,
                                       astrology_data: str = "",
                                       news_data: str = "") -> str:
        """Генерация детального анализа через Gemini"""
        try:
            if not self.gemini_client:
                return "❌ AI сервис недоступен"
            
            chart_data = {
                "company_data": company_data,
                "analysis_type": analysis_type,
                "astrology_data": astrology_data,
                "news_data": news_data[:2000]
            }
            
            result = self.gemini_client.generate_astro_analysis(chart_data, "detailed")
            logger.info(f"🔍 Детальный анализ '{analysis_type}' для {company_data.get('name')} завершен через Gemini")
            
            return result or "Детальный анализ недоступен"
            
        except Exception as e:
            logger.warning(f"⚠️ Детальный анализ недоступен (Gemini API): {type(e).__name__}")
            return "Извините, произошла ошибка при генерации детального анализа."
    
    def _get_zodiac_safe(self, date_value: Any) -> str:
        """Безопасное получение знака зодиака"""
        try:
            from utils.helpers import get_zodiac_sign
            
            if isinstance(date_value, datetime):
                return get_zodiac_sign(date_value)
            elif isinstance(date_value, str):
                # Пытаемся распарсить строку
                try:
                    parsed_date = datetime.strptime(date_value, '%Y-%m-%d')
                    return get_zodiac_sign(parsed_date)
                except:
                    return "Неизвестный знак"
            else:
                return "Неизвестный знак"
        except Exception as e:
            logger.warning(f"⚠️ Ошибка определения знака зодиака: {e}")
            return "Неизвестный знак"
