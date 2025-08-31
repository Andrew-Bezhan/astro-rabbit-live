"""
Gemini-based астрологический клиент вместо ProKerala
Замена GPT на Google Gemini
"""

from typing import Dict, Any, Optional
from datetime import datetime
from utils.config import load_config
from utils.logger import setup_logger

logger = setup_logger()


class GPTAstroClient:
    """Клиент для астрологических расчетов на базе Gemini (бывший GPT)"""
    
    def __init__(self):
        """Инициализация Gemini клиента"""
        self.config = load_config()
        try:
            from ai_astrologist.gemini_client import GeminiAstroClient
            self.gemini_client = GeminiAstroClient()
            logger.info("🔮 Gemini астрологический клиент инициализирован")
        except Exception as e:
            logger.warning(f"⚠️ Gemini клиент недоступен: {type(e).__name__}")
            self.gemini_client = None
    
    async def get_birth_chart(self, birth_date: datetime, latitude: float, longitude: float) -> Dict[str, Any]:
        """Получение натальной карты через Gemini"""
        if not self.gemini_client:
            logger.warning("⚠️ Gemini клиент недоступен для натальной карты")
            return self._get_fallback_chart(birth_date, latitude, longitude)
        
        try:
            # Используем Gemini для создания натальной карты
            chart_data = self.gemini_client.get_birth_chart(birth_date, latitude, longitude)
            logger.info("✨ Натальная карта создана через Gemini")
            return chart_data
                
        except Exception as e:
            logger.warning(f"⚠️ Ошибка Gemini астрологии: {type(e).__name__}")
            return self._get_fallback_chart(birth_date, latitude, longitude)
    
    def _get_fallback_chart(self, birth_date: datetime, latitude: float, longitude: float) -> Dict[str, Any]:
        """Базовая натальная карта без внешних API"""
        from utils.helpers import get_zodiac_sign
        
        sun_sign = get_zodiac_sign(birth_date)
        
        # Упрощенные расчеты для других знаков
        month_offset = birth_date.month
        moon_signs = ["Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева", 
                     "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы"]
        moon_sign = moon_signs[(month_offset + 3) % 12]
        ascendant = moon_signs[(month_offset + 6) % 12]
        
        return {
            "sun_sign": sun_sign,
            "moon_sign": moon_sign,
            "ascendant": ascendant,
            "planets": {
                "mercury": moon_signs[(month_offset + 1) % 12],
                "venus": moon_signs[(month_offset + 2) % 12],
                "mars": moon_signs[(month_offset + 4) % 12],
                "jupiter": moon_signs[(month_offset + 8) % 12]
            },
            "aspects": [
                "Солнце в гармонии с Луной",
                "Меркурий поддерживает коммуникации",
                "Венера благоприятна для партнерств"
            ],
            "interpretation": f"Компания под знаком {sun_sign} обладает характерными для этого знака качествами в бизнесе."
        }
    
    def _get_coordinates_by_city(self, city: str) -> tuple[float, float]:
        """Получение координат города (упрощенная версия)"""
        # Базовые координаты крупных городов
        city_coords = {
            "москва": (55.7558, 37.6176),
            "санкт-петербург": (59.9311, 30.3609),
            "новосибирск": (55.0084, 82.9357),
            "екатеринбург": (56.8431, 60.6454),
            "казань": (55.8304, 49.0661),
            "нижний новгород": (56.2965, 43.9361),
            "челябинск": (55.1644, 61.4368),
            "самара": (53.2001, 50.15),
            "омск": (54.9885, 73.3242),
            "ростов-на-дону": (47.2357, 39.7015)
        }
        
        city_lower = city.lower().strip()
        return city_coords.get(city_lower, (55.7558, 37.6176))  # По умолчанию Москва


