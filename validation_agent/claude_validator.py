"""
Агент-валидатор на базе Claude-3.5-Sonnet от Anthropic
"""

import os
import aiohttp
import json
import traceback
from typing import Dict, Any, List, Tuple
from utils.logger import setup_logger

logger = setup_logger()


class ClaudeValidatorAgent:
    """Продвинутый валидатор на Claude-3.5-Sonnet"""
    
    def __init__(self):
        """Инициализация Claude валидатора"""
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.model = "claude-3-5-sonnet-20241022"
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.max_tokens = 2000
        
        if self.api_key:
            logger.info("✅ Claude валидатор инициализирован")
        else:
            logger.warning("⚠️ ANTHROPIC_API_KEY не найден в .env")
    
    async def validate_and_score(self, text: str, original_prompt: str, analysis_type: str = "zodiac") -> Dict[str, Any]:
        """
        Валидация и оценка текста через Claude
        """
        if not self.api_key:
            return {
                'score': 5.0,
                'is_valid': False,
                'issues': ['API ключ не настроен'],
                'suggestions': [],
                'fixed_text': text
            }
        
        validation_prompt = f"""
Ты - эксперт по валидации текстов для Telegram ботов. Проанализируй сгенерированный текст на ПОЛНОЕ соответствие ВСЕМ правилам из prompts.py и дай количественную оценку.

ОРИГИНАЛЬНЫЙ ПРОМПТ:
{original_prompt}

СГЕНЕРИРОВАННЫЙ ТЕКСТ:
{text}

КРИТЕРИИ ОЦЕНКИ (каждый от 1 до 10):

1. ФОРМАТИРОВАНИЕ ДЛЯ TELEGRAM (вес: 30%):
   - СТРОГО проверь: НИКОГДА не используй HTML-теги
   - СТРОГО проверь: НИКОГДА не используй Markdown
   - Используй ТОЛЬКО обычный текст с эмодзи
   - Заголовки оформляй: "🌟 Название раздела"
   - Списки: ОБЯЗАТЕЛЬНО используй разнообразные графические иконки

2. СТРУКТУРА АНАЛИЗА ЗОДИАКА (вес: 25%):
   - ОБЯЗАТЕЛЬНО проверь наличие ВСЕХ 6 БЛОКОВ:
     🌟 БЛОК 1 - ВЛИЯНИЕ ЗНАКА ЗОДИАКА НА СУДЬБУ КОМПАНИИ (300+ слов)
     🔮 БЛОК 2 - ВЛИЯНИЕ ПЛАНЕТ И МЕСТА РЕГИСТРАЦИИ (250+ слов)  
     💎 БЛОК 3 - СИЛЬНЫЕ СТОРОНЫ И ПОТЕНЦИАЛ РОСТА (300+ слов)
     🧘 БЛОК 4 - ФИЛОСОФСКАЯ КОНЦЕПЦИЯ КОМПАНИИ (250+ слов)
     ⚠️ БЛОК 5 - ПОТЕНЦИАЛЬНЫЕ РИСКИ И ВЫЗОВЫ (200+ слов)
     💼 БЛОК 6 - БИЗНЕС-РЕКОМЕНДАЦИИ И СТРАТЕГИИ (200+ слов)
   - Минимум 1500 слов общего объема

3. СОДЕРЖАНИЕ И ПРОФЕССИОНАЛИЗМ (вес: 30%):
   - Поэтичное описание космической природы знака
   - ОБЯЗАТЕЛЬНО процитируй конкретные новости из контекста
   - Примеры 2-3 известных компаний с тем же знаком
   - НЕ упоминай источники данных (API, сервисы)

4. ЯЗЫК И СТИЛЬ (вес: 15%):
   - Профессиональный, уверенный тон
   - Использование только русского языка
   - От эзотерики к бизнес-логике

ВЕРНИ ТОЛЬКО ЧИСЛО ОЦЕНКИ ОТ 1 ДО 10. Например: 7.5
"""
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'x-api-key': self.api_key,
                    'content-type': 'application/json',
                    'anthropic-version': '2023-06-01'
                }
                
                payload = {
                    'model': self.model,
                    'max_tokens': 100,
                    'messages': [
                        {
                            'role': 'user',
                            'content': validation_prompt
                        }
                    ]
                }
                
                async with session.post(self.api_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result['content'][0]['text'].strip()
                        
                        try:
                            # Извлекаем число оценки
                            score_text = content.replace(',', '.').strip()
                            score = float(score_text)
                            
                            logger.info("✅ Claude валидация завершена: оценка %.1f/10", score)
                            
                            return {
                                'score': score,
                                'is_valid': score >= 7.0,
                                'confidence': 0.9,
                                'issues': [],
                                'suggestions': []
                            }
                            
                        except Exception as e:
                            logger.warning("⚠️ Ошибка парсинга оценки Claude: %s", str(e))
                            logger.warning("Ответ Claude: %s", content[:200])
                    else:
                        logger.warning("⚠️ Claude API ошибка: %s", response.status)
                        
        except Exception as e:
            logger.warning("⚠️ Ошибка Claude валидации: %s", str(e))
        
        # Возвращаем дефолтный результат при ошибке
        return {
            'score': 5.0,
            'is_valid': False,
            'issues': ['Ошибка API валидации'],
            'suggestions': [],
            'confidence': 0.0
        }
    
    async def fix_text_with_claude(self, text: str, target_score: float = 10.0) -> str:
        """Исправление текста через Claude"""
        if not self.api_key:
            return text
        
        fix_prompt = f"""
Исправь следующий текст для достижения оценки {target_score}/10 согласно ВСЕМ правилам из prompts.py.

ТЕКСТ ДЛЯ ИСПРАВЛЕНИЯ:
{text}

СТРОГИЕ ТРЕБОВАНИЯ ИЗ PROMPTS.PY:

1. ФОРМАТИРОВАНИЕ ДЛЯ TELEGRAM:
   - СТРОГО: НИКОГДА не используй HTML-теги
   - СТРОГО: НИКОГДА не используй Markdown
   - Используй ТОЛЬКО обычный текст с эмодзи
   - Заголовки оформляй: "🌟 Название раздела"
   - Списки: ОБЯЗАТЕЛЬНО используй графические иконки: ⭐ 🎯 💫 ⚡ 🔥 💎 🚀 ⚠️ 💰

2. ОБЯЗАТЕЛЬНЫЕ 6 БЛОКОВ АНАЛИЗА ЗОДИАКА:
   🌟 БЛОК 1 - ВЛИЯНИЕ ЗНАКА ЗОДИАКА НА СУДЬБУ КОМПАНИИ (300+ слов)
   🔮 БЛОК 2 - ВЛИЯНИЕ ПЛАНЕТ И МЕСТА РЕГИСТРАЦИИ (250+ слов)
   💎 БЛОК 3 - СИЛЬНЫЕ СТОРОНЫ И ПОТЕНЦИАЛ РОСТА (300+ слов)
   🧘 БЛОК 4 - ФИЛОСОФСКАЯ КОНЦЕПЦИЯ КОМПАНИИ (250+ слов)
   ⚠️ БЛОК 5 - ПОТЕНЦИАЛЬНЫЕ РИСКИ И ВЫЗОВЫ (200+ слов)
   💼 БЛОК 6 - БИЗНЕС-РЕКОМЕНДАЦИИ И СТРАТЕГИИ (200+ слов)

3. КАЧЕСТВО:
   - Минимум 1500 слов развернутого анализа
   - ОБЯЗАТЕЛЬНО укажи конкретные новости и их влияние
   - Примеры 2-3 известных компаний с тем же знаком

КРИТИЧЕСКИ ВАЖНО:
- НЕ СОКРАЩАЙ текст - только улучшай и дополняй
- Соблюдай ВСЕ правила из prompts.py

Верни ТОЛЬКО исправленный текст без комментариев.
"""
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'x-api-key': self.api_key,
                    'content-type': 'application/json',
                    'anthropic-version': '2023-06-01'
                }
                
                payload = {
                    'model': self.model,
                    'max_tokens': self.max_tokens,
                    'messages': [
                        {
                            'role': 'user',
                            'content': fix_prompt
                        }
                    ]
                }
                
                async with session.post(self.api_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        fixed_text = result['content'][0]['text'].strip()
                        logger.info("✅ Текст исправлен через Claude")
                        return fixed_text
                    else:
                        logger.warning("⚠️ Claude исправление недоступно: %s", response.status)
                        
        except Exception as e:
            logger.warning("⚠️ Ошибка исправления через Claude: %s", str(e))
        
        return text
    
    async def iterative_refinement(self, text: str, original_prompt: str, 
                                 analysis_type: str = "zodiac", 
                                 target_score: float = 10.0,
                                 max_iterations: int = 7,
                                 update_callback=None) -> Tuple[str, float]:
        """
        Итеративное улучшение текста до достижения целевой оценки
        """
        current_text = text
        iteration = 0
        
        logger.info("🎯 НАЧИНАЕМ ИТЕРАТИВНОЕ УЛУЧШЕНИЕ ДО ОЦЕНКИ %.1f/10", target_score)
        logger.info("📊 ОСНОВНОЙ АГЕНТ БУДЕТ СТРЕМИТЬСЯ К МАКСИМАЛЬНОЙ ОЦЕНКЕ")
        
        while iteration < max_iterations:
            iteration += 1
            logger.info("=" * 60)
            logger.info("🔄 ИТЕРАЦИЯ УЛУЧШЕНИЯ #%d из %d", iteration, max_iterations)
            logger.info("🎯 ЦЕЛЬ: достичь оценки %.1f/10", target_score)
            
            # Получаем оценку от Claude
            validation_result = await self.validate_and_score(current_text, original_prompt, analysis_type)
            current_score = validation_result.get('score', 5.0)
            
            # ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ ОЦЕНКИ
            logger.info("📊 ТЕКУЩАЯ ОЦЕНКА: %.1f/10", current_score)
            
            # Отправляем обновление пользователю если есть callback
            if update_callback:
                try:
                    await update_callback(f"🔍 **ВАЛИДАЦИЯ ИТЕРАЦИЯ #{iteration}**\n\n"
                                        f"📊 Текущая оценка: **{current_score:.1f}/10**\n"
                                        f"🎯 Цель: **{target_score:.1f}/10**\n"
                                        f"⏳ Улучшаем текст...")
                except:
                    pass  # Игнорируем ошибки обновления UI
            
            # ПРОВЕРЯЕМ ДОСТИЖЕНИЕ ЦЕЛИ
            if current_score >= target_score:
                logger.info("🎉 ЦЕЛЬ ДОСТИГНУТА! Оценка %.1f/10 за %d итераций", current_score, iteration)
                logger.info("🏆 ОСНОВНОЙ АГЕНТ УСПЕШНО ДОСТИГ МАКСИМАЛЬНОГО КАЧЕСТВА!")
                return current_text, current_score
            elif current_score >= 7.0:
                logger.info("✅ Минимальный порог пройден: %.1f/10, но продолжаем к цели %.1f", current_score, target_score)
            else:
                logger.warning("⚠️ Оценка %.1f/10 ниже минимума 7.0 - ОСНОВНОЙ АГЕНТ ДОЛЖЕН УЛУЧШИТЬ ТЕКСТ", current_score)
            
            # УЛУЧШАЕМ ТЕКСТ
            logger.info("🔧 ОСНОВНОЙ АГЕНТ ПРИМЕНЯЕТ УЛУЧШЕНИЯ...")
            improved_text = await self.fix_text_with_claude(current_text, target_score)
            
            if improved_text and len(improved_text.strip()) > 100:
                if len(improved_text) < len(current_text) * 0.7:
                    logger.warning("⚠️ Текст сократился с %d до %d символов - отклоняем", len(current_text), len(improved_text))
                    break
                
                current_text = improved_text
                logger.info("✅ ОСНОВНОЙ АГЕНТ УЛУЧШИЛ ТЕКСТ (%d символов)", len(current_text))
                logger.info("🔄 ПЕРЕХОДИМ К СЛЕДУЮЩЕЙ ИТЕРАЦИИ ДЛЯ ДОСТИЖЕНИЯ ЦЕЛИ %.1f/10", target_score)
            else:
                logger.warning("⚠️ ОСНОВНОЙ АГЕНТ НЕ СМОГ УЛУЧШИТЬ ТЕКСТ - завершаем итерации")
                break
        
        logger.warning("⚠️ ДОСТИГНУТО МАКСИМУМ ИТЕРАЦИЙ (%d)", max_iterations)
        logger.info("🔍 ФИНАЛЬНАЯ ПРОВЕРКА КАЧЕСТВА...")
        final_result = await self.validate_and_score(current_text, original_prompt, analysis_type)
        final_score = final_result.get('score', 5.0)
        
        logger.info("=" * 60)
        logger.info("🏁 ИТОГОВЫЙ РЕЗУЛЬТАТ:")
        logger.info("📊 ФИНАЛЬНАЯ ОЦЕНКА: %.1f/10", final_score)
        if final_score >= target_score:
            logger.info("🎉 ОСНОВНОЙ АГЕНТ ДОСТИГ ЦЕЛИ %.1f/10!", target_score)
        elif final_score >= 7.0:
            logger.info("✅ Минимальный порог пройден, но цель %.1f не достигнута", target_score)
        else:
            logger.warning("❌ Оценка %.1f ниже минимума 7.0", final_score)
        logger.info("=" * 60)
        
        return current_text, final_score


class AnthropicValidationAgent:
    """Главный класс валидации на Claude"""
    
    def __init__(self):
        """Инициализация агента"""
        self.claude_validator = ClaudeValidatorAgent()
        logger.info("✅ Anthropic валидатор инициализирован")
    
    async def validate_and_fix(self, text: str, analysis_type: str = "zodiac", original_prompt: str = "") -> str:
        """
        Основной метод валидации и исправления
        """
        try:
            # СТРЕМИМСЯ К МАКСИМАЛЬНОЙ ОЦЕНКЕ 10 БАЛЛОВ
            target_score = 10.0
            
            # Запускаем итеративное улучшение с максимальным количеством попыток
            improved_text, final_score = await self.claude_validator.iterative_refinement(
                text=text,
                original_prompt=original_prompt,
                analysis_type=analysis_type,
                target_score=target_score,
                max_iterations=7
            )
            
            logger.info("🎯 Финальная оценка: %.1f/10 для %s", final_score, analysis_type)
            return improved_text
            
        except Exception as e:
            logger.error("❌ Ошибка Claude валидации: %s", str(e))
            return text  # Возвращаем оригинал при ошибке


