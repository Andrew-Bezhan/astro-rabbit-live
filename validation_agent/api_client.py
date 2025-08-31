"""
API клиент для валидации промптов через внешний сервис
"""

import aiohttp
import json
from typing import Dict, Any, Optional, List
from utils.config import load_config
from utils.logger import setup_logger

logger = setup_logger()


class ValidationAPIClient:
    """Клиент для валидации через API"""
    
    def __init__(self):
        """Инициализация API клиента"""
        import os
        self.config = load_config()
        
        # Используем существующую переменную OPENAI_API_KEY
        self.api_key = os.getenv('OPENAI_API_KEY') or getattr(self.config.openai, 'api_key', None)
        self.model = 'gpt-4o-mini'  # Фиксированная модель для валидации
        self.api_url = 'https://api.openai.com/v1/chat/completions'
        
        if self.api_key:
            logger.info("✅ Валидационный API клиент инициализирован")
        else:
            logger.warning("⚠️ API ключ для валидации не найден")
    
    async def validate_text(self, text: str, original_prompt: str) -> Dict[str, Any]:
        """
        Проверка соответствия текста промпту через API
        
        Args:
            text (str): Сгенерированный текст
            original_prompt (str): Оригинальный промпт
            
        Returns:
            Dict[str, Any]: Результат валидации
        """
        if not self.api_key:
            return {
                'is_valid': True,
                'errors': [],
                'suggestions': [],
                'confidence': 0.0
            }
        
        validation_prompt = f"""
Проанализируй, соответствует ли сгенерированный текст ВСЕМ требованиям промпта из prompts.py.

ОРИГИНАЛЬНЫЙ ПРОМПТ:
{original_prompt[:1000]}

СГЕНЕРИРОВАННЫЙ ТЕКСТ:
{text[:2000]}

КРИТИЧЕСКИ ВАЖНЫЕ ТРЕБОВАНИЯ ДЛЯ ПРОВЕРКИ:

1. ФОРМАТИРОВАНИЕ ДЛЯ TELEGRAM:
   - НИКОГДА не используй HTML-теги: <p>, <h1>, <h2>, <h3>, <h4>, <b>, <i>, <ul>, <li>, <hr>, <div>
   - НИКОГДА не используй Markdown: **, __, ##, ###, ---
   - Используй ТОЛЬКО обычный текст с эмодзи
   - Заголовки оформляй: "🌟 Название раздела"
   - Списки оформляй: "• Пункт списка"

2. ОБЯЗАТЕЛЬНЫЕ ЭМОДЗИ:
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

3. СТРУКТУРА АНАЛИЗА:
   - Введение с учетом места регистрации
   - Астрологическая перспектива
   - Анализ текущей ситуации
   - Прогноз и рекомендации
   - Нумерологический анализ
   - Заключение

4. СОДЕРЖАНИЕ:
   - Развернутый, профессиональный и практичный текст
   - НЕ упоминай источники данных
   - Отвечай на русском языке

Ответь в формате JSON:
{{
    "is_valid": true/false,
    "errors": ["список конкретных ошибок"],
    "suggestions": ["предложения по исправлению"],
    "confidence": 0.95
}}
"""
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    'model': self.model,
                    'messages': [
                        {'role': 'system', 'content': 'Ты эксперт по валидации промптов. Отвечай только в формате JSON.'},
                        {'role': 'user', 'content': validation_prompt}
                    ],
                    'max_tokens': 500,
                    'temperature': 0.1
                }
                
                async with session.post(self.api_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['choices'][0]['message']['content']
                        
                        try:
                            validation_result = json.loads(content)
                            logger.info(f"✅ Валидация через API завершена: {validation_result.get('is_valid', False)}")
                            return validation_result
                        except json.JSONDecodeError:
                            logger.warning("⚠️ Ошибка парсинга JSON от API валидации")
                            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка API валидации: {e}")
        
        # Возвращаем дефолтный результат при ошибке
        return {
            'is_valid': True,
            'errors': [],
            'suggestions': [],
            'confidence': 0.0
        }
    
    async def fix_text(self, text: str, errors: List[str]) -> str:
        """
        Исправление текста через API
        
        Args:
            text (str): Исходный текст
            errors (List[str]): Список ошибок
            
        Returns:
            str: Исправленный текст
        """
        if not self.api_key or not errors:
            return text
        
        fix_prompt = f"""
Исправь следующий текст согласно ВСЕМ требованиям из prompts.py:

ОШИБКИ ДЛЯ ИСПРАВЛЕНИЯ:
{chr(10).join(errors)}

ТЕКСТ ДЛЯ ИСПРАВЛЕНИЯ:
{text}

СТРОГИЕ ТРЕБОВАНИЯ К ИСПРАВЛЕНИЮ:

1. ФОРМАТИРОВАНИЕ ДЛЯ TELEGRAM:
   - УБЕРИ все HTML-теги: <p>, <h1>, <h2>, <h3>, <h4>, <b>, <i>, <ul>, <li>, <hr>, <div>
   - УБЕРИ весь Markdown: **, __, ##, ###, ---
   - ИСПОЛЬЗУЙ только обычный текст с эмодзи
   - Заголовки ТОЛЬКО так: "🌟 Название раздела"
   - Списки ТОЛЬКО так: "• Пункт списка"

2. ОБЯЗАТЕЛЬНЫЕ ЭМОДЗИ (используй правильно):
   🌟 - заголовки и важные моменты
   💎 - сильные стороны
   🚀 - возможности развития  
   ⚠️ - риски и предупреждения
   📈 - рост и прогресс
   🔮 - астрологические предсказания
   💼 - бизнес-рекомендации
   🎯 - цели и направления
   💡 - инсайты и идеи
   🔢 - нумерологический анализ
   🌍 - географические факторы
   ✨ - заключения и итоги

3. СТРУКТУРА (обязательно включи):
   - Введение с учетом места регистрации
   - Астрологическая перспектива
   - Анализ текущей ситуации
   - Прогноз и рекомендации
   - Нумерологический анализ
   - Заключение

4. НЕ упоминай источники данных
5. Отвечай на русском языке

Верни ТОЛЬКО исправленный текст без дополнительных комментариев.
"""
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    'model': self.model,
                    'messages': [
                        {'role': 'system', 'content': 'Ты эксперт по исправлению текста. Возвращай только исправленный текст.'},
                        {'role': 'user', 'content': fix_prompt}
                    ],
                    'max_tokens': 2000,
                    'temperature': 0.1
                }
                
                async with session.post(self.api_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        fixed_text = result['choices'][0]['message']['content'].strip()
                        logger.info("✅ Текст исправлен через API")
                        return fixed_text
                        
        except Exception as e:
            logger.warning(f"⚠️ Ошибка исправления через API: {e}")
        
        return text
