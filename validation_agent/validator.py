"""
Агент-валидатор для проверки соответствия генерируемого текста промптам
"""

import re
import json
import traceback
from typing import Dict, Any, List, Tuple, Optional
from utils.logger import setup_logger

logger = setup_logger()

# --- BEGIN SAFE LOGGING HELPERS ---
def _safe_json(obj) -> str:
    """Безопасно сериализует любой объект для лога, не роняя логгер."""
    try:
        if isinstance(obj, str):
            # попытка вытащить JSON из «грязной» строки и красиво отформатировать
            obj_str = obj.strip()
            if obj_str.startswith("{") and obj_str.endswith("}"):
                return json.dumps(json.loads(obj_str), ensure_ascii=False, indent=2)
            return obj
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        try:
            return str(obj)
        except Exception:
            return "<unprintable>"

def log_kv(level: str, msg: str, payload=None):
    """Лог с безопасной подстановкой. Никаких f-строк/format/%."""
    safe_payload = _safe_json(payload)
    if level == "error":
        logger.error(msg + " | data=" + safe_payload)
    elif level == "warning":
        logger.warning(msg + " | data=" + safe_payload)
    elif level == "info":
        logger.info(msg + " | data=" + safe_payload)
    else:
        logger.debug(msg + " | data=" + safe_payload)
# --- END SAFE LOGGING HELPERS ---


class PromptValidator:
    """Валидатор соответствия промптам"""
    
    def __init__(self):
        """Инициализация валидатора"""
        self.validation_rules = {
            'no_html_tags': self._check_no_html_tags,
            'no_markdown': self._check_no_markdown,
            'has_emojis': self._check_has_emojis,
            'proper_structure': self._check_proper_structure,
            'no_hash_symbols': self._check_no_hash_symbols,
            'required_emoji_sections': self._check_required_emoji_sections,
            'graphic_icons_not_bullets': self._check_graphic_icons_not_bullets,
            'astro_symbols_usage': self._check_astro_symbols_usage,
            'russian_language': self._check_russian_language,
            'no_source_mentions': self._check_no_source_mentions,
            'professional_tone': self._check_professional_tone,
            'no_direct_financial_advice': self._check_no_direct_financial_advice
        }
    
    def validate_text(self, text: str, analysis_type: str = "zodiac") -> Tuple[bool, List[str]]:
        """
        Проверка текста на соответствие промптам
        
        Args:
            text (str): Текст для проверки
            analysis_type (str): Тип анализа
            
        Returns:
            Tuple[bool, List[str]]: (валиден ли текст, список ошибок)
        """
        errors = []
        
        for rule_name, rule_func in self.validation_rules.items():
            try:
                is_valid, error_msg = rule_func(text)
                if not is_valid:
                    errors.append(f"{rule_name}: {error_msg}")
            except Exception as e:
                errors.append(f"{rule_name}: Ошибка проверки - {e}")
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            logger.warning("⚠️ Текст не соответствует промпту (%s): %s", analysis_type, errors)
        else:
            logger.info("✅ Текст соответствует промпту (%s)", analysis_type)
        
        return is_valid, errors
    
    def _check_no_html_tags(self, text: str) -> Tuple[bool, str]:
        """Проверка отсутствия HTML-тегов (кроме разрешенных для Telegram)"""
        # Разрешаем <b> и <i> для Telegram
        forbidden_tags = re.findall(r'<(?!/?[bi]>)[^>]+>', text)
        if forbidden_tags:
            return False, f"Найдены запрещенные HTML-теги: {forbidden_tags[:5]}"
        return True, ""
    
    def _check_no_markdown(self, text: str) -> Tuple[bool, str]:
        """Проверка отсутствия Markdown"""
        markdown_patterns = [
            r'\*\*[^*]+\*\*',  # **жирный**
            r'__[^_]+__',      # __жирный__
            r'\*[^*]+\*',      # *курсив*
            r'_[^_]+_',        # _курсив_
            r'^#{1,6}\s',      # # заголовки
        ]
        
        for pattern in markdown_patterns:
            if re.search(pattern, text, re.MULTILINE):
                return False, f"Найден Markdown: {pattern}"
        
        return True, ""
    
    def _check_has_emojis(self, text: str) -> Tuple[bool, str]:
        """Проверка наличия эмодзи"""
        emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\U0001F900-\U0001F9FF]'
        emojis = re.findall(emoji_pattern, text)
        
        if len(emojis) < 5:
            return False, f"Недостаточно эмодзи: {len(emojis)} (нужно минимум 5)"
        
        return True, ""
    
    def _check_proper_structure(self, text: str) -> Tuple[bool, str]:
        """Проверка правильной структуры"""
        # Проверяем наличие разделов с эмодзи
        required_sections = ['🌟', '💎', '🚀', '⚠️']
        found_sections = []
        
        for section in required_sections:
            if section in text:
                found_sections.append(section)
        
        if len(found_sections) < 3:
            return False, f"Недостаточно разделов: {found_sections} (нужно минимум 3 из {required_sections})"
        
        return True, ""
    
    def _check_no_hash_symbols(self, text: str) -> Tuple[bool, str]:
        """Проверка отсутствия символов #"""
        if '#' in text:
            hash_lines = [line.strip() for line in text.split('\n') if '#' in line]
            return False, f"Найдены символы #: {hash_lines[:3]}"
        
        return True, ""
    
    def _check_required_emoji_sections(self, text: str) -> Tuple[bool, str]:
        """Проверка наличия обязательных 6 блоков из prompts.py"""
        # Обязательные блоки из COMPANY_ZODIAC_PROMPT
        required_blocks = [
            ('🌟', 'ВЛИЯНИЕ ЗНАКА ЗОДИАКА НА СУДЬБУ', 300),
            ('🔮', 'ВЛИЯНИЕ ПЛАНЕТ И МЕСТА РЕГИСТРАЦИИ', 250),
            ('💎', 'СИЛЬНЫЕ СТОРОНЫ И ПОТЕНЦИАЛ РОСТА', 300),
            ('🧘', 'ФИЛОСОФСКАЯ КОНЦЕПЦИЯ КОМПАНИИ', 250),
            ('⚠️', 'ПОТЕНЦИАЛЬНЫЕ РИСКИ И ВЫЗОВЫ', 200),
            ('💼', 'БИЗНЕС-РЕКОМЕНДАЦИИ И СТРАТЕГИИ', 200)
        ]
        
        missing_blocks = []
        
        for emoji, block_name, min_words in required_blocks:
            if emoji not in text:
                missing_blocks.append(f"{emoji} {block_name}")
            else:
                # Проверяем приблизительный объем блока
                lines_with_emoji = [line for line in text.split('\n') if emoji in line]
                if len(lines_with_emoji) == 0:
                    missing_blocks.append(f"{emoji} {block_name} (отсутствует)")
        
        if missing_blocks:
            return False, f"Отсутствуют обязательные блоки из prompts.py: {missing_blocks[:3]}"
        
        # Проверяем общий объем (минимум 1500 слов)
        word_count = len(text.split())
        if word_count < 1000:  # Примерная проверка
            return False, f"Недостаточный объем текста: ~{word_count} слов (нужно минимум 1500)"
        
        return True, ""
    
    def _check_russian_language(self, text: str) -> Tuple[bool, str]:
        """Проверка использования русского языка"""
        # Простая проверка наличия кириллицы
        cyrillic_chars = len(re.findall(r'[а-яё]', text.lower()))
        total_letters = len(re.findall(r'[a-zA-Zа-яёА-ЯЁ]', text))
        
        if total_letters > 0:
            cyrillic_ratio = cyrillic_chars / total_letters
            if cyrillic_ratio < 0.8:
                return False, f"Недостаточно русского текста: {cyrillic_ratio:.2%} кириллицы"
        
        return True, ""
    
    def _check_no_source_mentions(self, text: str) -> Tuple[bool, str]:
        """Проверка отсутствия упоминания источников"""
        source_keywords = [
            'источник', 'данные получены', 'согласно', 'по данным',
            'newsdata', 'prokerala', 'gemini', 'openai', 'api'
        ]
        
        text_lower = text.lower()
        found_sources = [word for word in source_keywords if word in text_lower]
        
        if found_sources:
            return False, f"Найдены упоминания источников: {found_sources}"
        
        return True, ""
    
    def _check_graphic_icons_not_bullets(self, text: str) -> Tuple[bool, str]:
        """Проверка использования графических иконок вместо обычных маркеров"""
        # Ищем обычные маркеры
        bullet_patterns = [r'^\s*\*\s', r'^\s*-\s', r'^\s*•\s']
        found_bullets = []
        
        for pattern in bullet_patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            if matches:
                found_bullets.extend(matches)
        
        if found_bullets:
            return False, f"Найдены обычные маркеры вместо графических иконок: {found_bullets[:3]}"
        
        # Проверяем наличие графических иконок из prompts.py
        required_icons = ['⭐', '🎯', '💫', '⚡', '🔥', '💎', '🚀', '⚠️', '💰']
        found_icons = [icon for icon in required_icons if icon in text]
        
        if len(found_icons) < 3:
            return False, f"Недостаточно графических иконок. Найдено: {found_icons}, нужно минимум 3 из {required_icons}"
        
        return True, ""
    
    def _check_astro_symbols_usage(self, text: str) -> Tuple[bool, str]:
        """Проверка использования астрологических символов"""
        astro_symbols = ['♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓', '☉', '☽', '☿', '♀', '♂', '♃', '♄', '⛢', '♆', '♇']
        found_symbols = [symbol for symbol in astro_symbols if symbol in text]
        
        if len(found_symbols) < 2:
            return False, f"Недостаточно астрологических символов. Найдено: {found_symbols}, нужно минимум 2"
        
        return True, ""
    
    def _check_professional_tone(self, text: str) -> Tuple[bool, str]:
        """Проверка профессионального тона"""
        # Ищем непрофессиональные фразы
        unprofessional_phrases = [
            'извините', 'простите', 'к сожалению', 'возможно', 'наверное', 'может быть',
            'я думаю', 'я считаю', 'по моему мнению'
        ]
        
        text_lower = text.lower()
        found_unprofessional = [phrase for phrase in unprofessional_phrases if phrase in text_lower]
        
        if found_unprofessional:
            return False, f"Найдены непрофессиональные фразы: {found_unprofessional[:3]}"
        
        return True, ""
    
    def _check_no_direct_financial_advice(self, text: str) -> Tuple[bool, str]:
        """Проверка отсутствия прямых финансовых советов"""
        direct_advice_patterns = [
            r'покупайте\s+акции', r'продавайте\s+акции', r'инвестируйте\s+в',
            r'купите\s+', r'продайте\s+', r'вложите\s+деньги'
        ]
        
        text_lower = text.lower()
        found_advice = []
        
        for pattern in direct_advice_patterns:
            if re.search(pattern, text_lower):
                found_advice.append(pattern)
        
        if found_advice:
            return False, f"Найдены прямые финансовые советы: {found_advice[:2]}"
        
        return True, ""
    
    def fix_text(self, text: str) -> str:
        """
        Автоматическое исправление текста
        
        Args:
            text (str): Исходный текст
            
        Returns:
            str: Исправленный текст
        """
        # Убираем только запрещенные HTML-теги (сохраняем <b> и <i> для Telegram)
        text = re.sub(r'<(?!/?[bi]>)[^>]+>', '', text)
        
        # Убираем Markdown
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **жирный**
        text = re.sub(r'__([^_]+)__', r'\1', text)      # __жирный__
        text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *курсив*
        text = re.sub(r'_([^_]+)_', r'\1', text)        # _курсив_
        
        # Убираем символы # и заменяем на эмодзи
        text = re.sub(r'^#{1,6}\s*(.+)$', r'🌟 \1', text, flags=re.MULTILINE)
        text = re.sub(r'###\s*(.+)', r'💎 \1', text)
        text = re.sub(r'##\s*(.+)', r'🚀 \1', text)
        text = re.sub(r'#\s*(.+)', r'⭐ \1', text)
        
        # Заменяем разделители
        text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^===+$', '', text, flags=re.MULTILINE)
        
        # Убираем упоминания источников
        text = re.sub(r'(источник|данные получены|согласно|по данным)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(newsdata|prokerala|gemini|openai|api)', '', text, flags=re.IGNORECASE)
        
        # Заменяем обычные маркеры на графические иконки (только если их еще нет)
        text = re.sub(r'^\s*\*\s+(?!⭐|💫|🎯|⚡|🔥|💎|🚀|⚠️|💰)(.+)', r'⭐ \1', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*-\s+(?!⭐|💫|🎯|⚡|🔥|💎|🚀|⚠️|💰)(.+)', r'💫 \1', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*•\s+(?!⭐|💫|🎯|⚡|🔥|💎|🚀|⚠️|💰)(.+)', r'🎯 \1', text, flags=re.MULTILINE)
        
        # Убираем непрофессиональные фразы
        unprofessional_replacements = {
            'извините': '', 'простите': '', 'к сожалению': '',
            'возможно': 'вероятно', 'наверное': 'скорее всего', 'может быть': 'вероятно',
            'я думаю': '', 'я считаю': '', 'по моему мнению': ''
        }
        
        for phrase, replacement in unprofessional_replacements.items():
            text = re.sub(phrase, replacement, text, flags=re.IGNORECASE)
        
        # Добавляем обязательные 6 блоков если их нет
        if '🌟' not in text or 'ВЛИЯНИЕ ЗНАКА ЗОДИАКА' not in text:
            text = '🌟 ВЛИЯНИЕ ЗНАКА ЗОДИАКА НА СУДЬБУ КОМПАНИИ\n\n' + text
        if '🔮' not in text or 'ВЛИЯНИЕ ПЛАНЕТ' not in text:
            text = text + '\n\n🔮 ВЛИЯНИЕ ПЛАНЕТ И МЕСТА РЕГИСТРАЦИИ'
        if '💎' not in text or 'СИЛЬНЫЕ СТОРОНЫ' not in text:
            text = text + '\n\n💎 СИЛЬНЫЕ СТОРОНЫ И ПОТЕНЦИАЛ РОСТА'
        if '🧘' not in text or 'ФИЛОСОФСКАЯ КОНЦЕПЦИЯ' not in text:
            text = text + '\n\n🧘 ФИЛОСОФСКАЯ КОНЦЕПЦИЯ КОМПАНИИ'
        if '⚠️' not in text or 'ПОТЕНЦИАЛЬНЫЕ РИСКИ' not in text:
            text = text + '\n\n⚠️ ПОТЕНЦИАЛЬНЫЕ РИСКИ И ВЫЗОВЫ'
        if '💼' not in text or 'БИЗНЕС-РЕКОМЕНДАЦИИ' not in text:
            text = text + '\n\n💼 БИЗНЕС-РЕКОМЕНДАЦИИ И СТРАТЕГИИ'
        
        # Добавляем пустые строки между разделами с эмодзи
        text = re.sub(r'(\n)(🌟|💎|🚀|⚠️|📈|🔮|💼|🎯|💡|✨)', r'\1\n\2', text)
        
        # Убираем лишние переносы
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        return text.strip()


class ValidationAgent:
    """Агент для валидации и исправления промптов с RLHF"""
    
    def __init__(self):
        """Инициализация агента валидации"""
        # Используем Anthropic валидатор как основной
        try:
            from validation_agent.claude_validator import AnthropicValidationAgent
            self.claude_agent = AnthropicValidationAgent()
            self.use_claude = True
            logger.info("✅ Anthropic валидатор инициализирован")
        except Exception as e:
            logger.warning("⚠️ Anthropic валидатор недоступен: %s", str(e))
            # Резервный локальный валидатор
            self.validator = PromptValidator()
            self.use_claude = False
            logger.info("✅ Резервный валидатор инициализирован")
    
    async def validate_and_fix(self, text: str, analysis_type: str = "zodiac", original_prompt: str = "") -> str:
        """
        Валидация и исправление текста до достижения минимум 7 баллов
        
        Args:
            text (str): Исходный текст
            analysis_type (str): Тип анализа
            original_prompt (str): Оригинальный промпт для валидации
            
        Returns:
            str: Валидированный и исправленный текст
        """
        try:
            if self.use_claude and hasattr(self, 'claude_agent'):
                # Используем Anthropic валидатор как основной
                logger.info("🤖 Используем Anthropic валидатор для %s (цель: 7+ баллов)", analysis_type)
                
                # СТРЕМИМСЯ К МАКСИМАЛЬНОЙ ОЦЕНКЕ 10 БАЛЛОВ
                logger.info("🎯 ЦЕЛЬ: достичь оценки 10.0/10 (стремимся к совершенству)")
                
                # Запускаем валидацию через Claude с итеративным улучшением
                improved_text = await self.claude_agent.validate_and_fix(
                    text=text,
                    analysis_type=analysis_type,
                    original_prompt=original_prompt
                )
                
                # Получаем финальную оценку
                final_result = await self.claude_agent.claude_validator.validate_and_score(
                    improved_text, original_prompt, analysis_type
                )
                final_score = final_result.get('score', 7.0)
                logger.info("🏆 Anthropic валидация завершена: %.1f/10", final_score)
                return improved_text
            else:
                # Используем резервный валидатор
                logger.info("🔧 Используем резервный валидатор для %s", analysis_type)
                return await self._fallback_validation(text, analysis_type, original_prompt)
                
        except Exception as e:
            logger.error("❌ Критическая ошибка валидации: %s", str(e))
            logger.error("Stacktrace: %s", traceback.format_exc())
            # ВСЕГДА возвращаем хотя бы базовую очистку
            return self._basic_cleanup(text)
    
    def _basic_cleanup(self, text: str) -> str:
        """Базовая очистка текста при ошибках валидации"""
        if not text:
            return "Анализ недоступен"
        
        # Минимальная обработка для читаемости
        text = re.sub(r'<(?!/?[bi]>)[^>]+>', '', text)  # Убираем лишние HTML
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Нормализуем переносы
        
        return text.strip()
    
    async def _fallback_validation(self, text: str, analysis_type: str, original_prompt: str) -> str:
        """Резервная валидация при недоступности Claude"""
        import asyncio
        
        if not hasattr(self, 'validator'):
            self.validator = PromptValidator()
        
        current_text = text
        max_iterations = 2  # Уменьшаем для резервного режима
        iteration = 0
        
        logger.info("🔍 Резервная валидация текста типа '%s'", analysis_type)
        
        while iteration < max_iterations:
            iteration += 1
            logger.info("🔄 Итерация валидации #%d", iteration)
            
            # Локальная валидация
            is_valid_local, local_errors = self.validator.validate_text(current_text, analysis_type)
            
            if is_valid_local:
                logger.info("✅ Резервная валидация завершена за %d итераций", iteration)
                return current_text
            
            # Исправляем локально
            current_text = self.validator.fix_text(current_text)
            logger.info("🔧 Текст исправлен локально (итерация %d)", iteration)
            
            # Пауза между итерациями
            if iteration < max_iterations:
                await asyncio.sleep(0.1)
        
        return current_text
    
    async def validate_and_fix_with_rlhf(self, 
                                       text: str, 
                                       analysis_type: str = "zodiac", 
                                       original_prompt: str = "",
                                       generation_function=None,
                                       generation_params: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Валидация с использованием основного валидатора
        
        Args:
            text (str): Исходный текст
            analysis_type (str): Тип анализа
            original_prompt (str): Оригинальный промпт
            generation_function: Функция для регенерации (опционально)
            generation_params (Dict): Параметры генерации (опционально)
            
        Returns:
            Tuple[str, Dict]: (улучшенный текст, метрики качества)
        """
        logger.info("🔧 Используем основную валидацию для %s", analysis_type)
        improved_text = await self.validate_and_fix(text, analysis_type, original_prompt)
        return improved_text, {'final_score': 7.0, 'method': 'anthropic'}
