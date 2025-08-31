"""
Google Gemini API клиент для астрологических вычислений
Замена OpenAI согласно требованиям пользователя
"""

import os
from typing import Dict, Any, Optional, Union
from datetime import datetime

try:
    import google.generativeai as genai
    from google.generativeai.types import GenerateContentResponse
    GEMINI_AVAILABLE = True
except ImportError:
    genai = None
    GenerateContentResponse = None
    GEMINI_AVAILABLE = False

from utils.config import load_config
from utils.logger import setup_logger

logger = setup_logger()


class GeminiAstroClient:
    """Клиент для работы с Google Gemini API"""
    
    def __init__(self):
        """Инициализация Gemini клиента"""
        self.config = load_config()
        self.model: Optional[Any] = None
        
        try:
            # Проверяем доступность Gemini
            if not GEMINI_AVAILABLE or not genai:
                raise ImportError("Google GenAI SDK не установлен")
            
            # Настраиваем Gemini API
            genai.configure(api_key=self.config.gemini.api_key)  # type: ignore
            self.model = genai.GenerativeModel(self.config.gemini.model)  # type: ignore
            logger.info("🔮 Gemini астрологический клиент инициализирован")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка инициализации Gemini: {e}")
            self.model = None
    
    def get_birth_chart(self, birth_date: datetime, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Создание натальной карты через Gemini
        
        Args:
            birth_date (datetime): Дата рождения
            latitude (float): Широта места рождения
            longitude (float): Долгота места рождения
            
        Returns:
            Dict[str, Any]: Данные натальной карты
        """
        if not GEMINI_AVAILABLE or not self.config.gemini.api_key or not self.model:
            logger.warning("⚠️ Gemini недоступен, используем базовую карту")
            return self._get_fallback_chart(birth_date, latitude, longitude)
        
        try:
            prompt = f"""
            Создай натальную карту в JSON формате для:
            Дата: {birth_date.strftime('%Y-%m-%d %H:%M')}
            Координаты: {latitude}, {longitude}
            
            Верни JSON с полями:
            - sun_sign: знак солнца
            - moon_sign: знак луны  
            - rising_sign: восходящий знак
            - planets: позиции планет
            - houses: астрологические дома
            - aspects: аспекты между планетами
            
            Ответ должен быть только валидный JSON без дополнительного текста.
            """
            
            # Используем Gemini для генерации натальной карты
            response = self.model.generate_content(prompt)
            
            result_text = response.text
            
            # Пытаемся распарсить JSON
            import json
            try:
                if result_text:
                    # Очищаем от markdown разметки если есть
                    clean_text = result_text.strip()
                    if clean_text.startswith('```json'):
                        clean_text = clean_text.replace('```json', '').replace('```', '').strip()
                    elif clean_text.startswith('```'):
                        clean_text = clean_text.replace('```', '').strip()
                    
                    chart_data = json.loads(clean_text)
                    logger.info("✨ Натальная карта создана через Gemini")
                    return chart_data
                else:
                    return self._get_fallback_chart(birth_date, latitude, longitude)
            except json.JSONDecodeError:
                logger.warning("⚠️ Gemini вернул невалидный JSON, используем базовый вариант")
                return self._get_fallback_chart(birth_date, latitude, longitude)
                
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
        rising_sign = moon_signs[(month_offset + 6) % 12]
        
        return {
            "sun_sign": sun_sign,
            "moon_sign": moon_sign,
            "rising_sign": rising_sign,
            "planets": {
                "mercury": moon_signs[(month_offset + 1) % 12],
                "venus": moon_signs[(month_offset + 2) % 12],
                "mars": moon_signs[(month_offset + 4) % 12],
                "jupiter": moon_signs[(month_offset + 8) % 12]
            },
            "houses": {
                "house_1": rising_sign,
                "house_2": moon_signs[(month_offset + 7) % 12],
                "house_10": moon_signs[(month_offset + 4) % 12]
            },
            "aspects": [
                "Солнце в гармонии с Луной",
                "Меркурий поддерживает коммуникации",
                "Венера благоприятна для партнерств"
            ]
        }
    
    def generate_astro_analysis(self, chart_data: Dict[str, Any], analysis_type: str) -> str:
        """
        Генерация астрологического анализа через Gemini
        
        Args:
            chart_data (Dict): Данные натальной карты
            analysis_type (str): Тип анализа
            
        Returns:
            str: Астрологический анализ
        """
        if not GEMINI_AVAILABLE or not self.config.gemini.api_key or not self.model:
            return "Астрологический анализ недоступен (Gemini API не настроен)"
        
        try:
            # Определяем тип анализа
            analysis_prompts = {
                "personality": "Проанализируй личность по натальной карте",
                "business": "Дай бизнес-прогноз на основе астрологических данных", 
                "compatibility": "Проанализируй совместимость",
                "daily": "Создай ежедневный астрологический прогноз",
                "detailed": "Сделай детальный астрологический анализ"
            }
            
            base_prompt = analysis_prompts.get(analysis_type, "Сделай астрологический анализ")
            
            import json
            prompt = f"""
            {base_prompt} на основе следующих астрологических данных:
            
            {json.dumps(chart_data, ensure_ascii=False, indent=2)}
            
            КРИТИЧЕСКИ ВАЖНО - ФОРМАТИРОВАНИЕ ДЛЯ TELEGRAM:
            - НИКОГДА не используй HTML-теги: <p>, <h1>, <h2>, <h3>, <h4>, <b>, <i>, <ul>, <li>, <hr>, <div>
            - НИКОГДА не используй Markdown: **, __, ##, ###, ---
            - Используй ТОЛЬКО обычный текст с эмодзи
            - Заголовки оформляй: "🌟 Название раздела"
            - Списки оформляй: "• Пункт списка"
            - После каждого раздела добавляй пустую строку
            
            ОБЯЗАТЕЛЬНЫЕ ЭМОДЗИ:
            - 🌟 для заголовков и важных моментов
            - ⭐ для ключевых характеристик
            - 💼 для бизнес-рекомендаций
            - ⚡ для энергичных качеств
            - 🚀 для возможностей развития
            - ⚠️ для рисков и предупреждений
            - 💎 для сильных сторон
            - 🔮 для астрологических предсказаний
            - 📈 для роста и прогресса
            - 🤝 для партнерств и отношений
            - 🎯 для целей и направлений
            - 💡 для инсайтов и идей
            - 🔢 для нумерологических расчетов
            - 🌍 для географических факторов
            - ✨ для заключений и итогов
            
            Предоставь подробный, профессиональный анализ на русском языке.
            Используй астрологические термины и дай практические рекомендации.
            Ответ должен быть структурированным и информативным.
            """
            
            # Используем Gemini для генерации анализа
            logger.info(f"🔮 Отправляем запрос к Gemini для {analysis_type}")
            logger.debug(f"Промпт для Gemini ({len(prompt)} символов): {prompt[:200]}...")
            
            response = self.model.generate_content(prompt)
            logger.debug(f"Получен ответ от Gemini: {response}")
            
            if not response:
                logger.error(f"❌ Gemini вернул None для {analysis_type}")
                raise Exception("Gemini response is None")
            
            if not hasattr(response, 'text'):
                logger.error(f"❌ Gemini response не имеет атрибута 'text': {dir(response)}")
                raise Exception("Gemini response has no text attribute")
            
            result = response.text
            if not result:
                logger.error(f"❌ Gemini response.text пустой")
                # Проверяем другие возможные атрибуты
                if hasattr(response, 'parts') and response.parts:
                    logger.info("🔍 Пробуем извлечь текст из response.parts")
                    result = ''.join([part.text for part in response.parts if hasattr(part, 'text')])
                
                if not result:
                    raise Exception("Gemini returned empty text")
            
            if len(result.strip()) < 100:
                logger.warning(f"⚠️ Gemini вернул короткий результат ({len(result)} символов): {result}")
                # Не возвращаем заглушку, а пробуем повторный запрос
                logger.info("🔄 Пробуем повторный запрос к Gemini")
                response2 = self.model.generate_content(prompt + "\n\nПожалуйста, предоставь развернутый анализ минимум на 1000 слов.")
                if response2 and hasattr(response2, 'text') and response2.text:
                    result = response2.text
            
            logger.info(f"🔮 Gemini анализ '{analysis_type}' завершен ({len(result)} символов)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка Gemini анализа: {type(e).__name__}: {e}")
            
            # Пробуем альтернативный простой запрос
            try:
                logger.info("🔄 Пробуем упрощенный запрос к Gemini")
                
                # Извлекаем данные компании из chart_data
                company_name = "Неизвестная"
                company_date = "Неизвестна"
                company_sphere = "Неизвестна"
                
                if isinstance(chart_data, dict):
                    if 'company_name' in chart_data:
                        company_name = chart_data['company_name']
                    elif 'name' in chart_data:
                        company_name = chart_data['name']
                    
                    if 'registration_date' in chart_data:
                        company_date = str(chart_data['registration_date'])
                    
                    if 'business_sphere' in chart_data:
                        company_sphere = chart_data['business_sphere']
                
                simple_prompt = f"""Создай астрологический анализ для компании.
                
Данные компании:
Название: {company_name}
Дата регистрации: {company_date}
Сфера деятельности: {company_sphere}

Создай развернутый профессиональный астрологический анализ на русском языке.
Используй эмодзи для структурирования: 🌟 для заголовков, 💎 для особенностей, 🚀 для возможностей.
Минимум 800 слов."""

                fallback_response = self.model.generate_content(simple_prompt)
                if fallback_response and hasattr(fallback_response, 'text') and fallback_response.text:
                    logger.info(f"✅ Упрощенный запрос к Gemini успешен ({len(fallback_response.text)} символов)")
                    return fallback_response.text
                    
            except Exception as e2:
                logger.error(f"❌ Упрощенный запрос тоже не удался: {e2}")
            
            # Если все не удалось - выбрасываем исключение, чтобы вызывающий код мог обработать
            raise Exception(f"Gemini недоступен: {e}")
