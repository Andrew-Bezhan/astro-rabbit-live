"""
Система RLHF (Reinforcement Learning from Human Feedback) для улучшения качества генерации
"""

import asyncio
from typing import Dict, Any, List, Tuple, Optional
from utils.logger import setup_logger

logger = setup_logger()


class RLHFFeedbackSystem:
    """Система обратной связи для итеративного улучшения текста"""
    
    def __init__(self, validator_agent):
        """
        Инициализация RLHF системы
        
        Args:
            validator_agent: Агент-валидатор для оценки качества
        """
        self.validator = validator_agent
        self.max_iterations = 5
        self.target_scores = {
            'zodiac': 8.5,
            'forecast': 9.0,
            'compatibility': 8.0
        }
    
    async def iterative_improvement(self, 
                                  initial_text: str, 
                                  analysis_type: str,
                                  original_prompt: str,
                                  generation_function,
                                  generation_params: Dict[str, Any]) -> Tuple[str, float, List[Dict]]:
        """
        Итеративное улучшение текста с обратной связью
        
        Args:
            initial_text (str): Первоначальный сгенерированный текст
            analysis_type (str): Тип анализа
            original_prompt (str): Оригинальный промпт
            generation_function: Функция для повторной генерации
            generation_params (Dict): Параметры для генерации
            
        Returns:
            Tuple[str, float, List[Dict]]: (лучший текст, финальная оценка, история итераций)
        """
        target_score = self.target_scores.get(analysis_type, 8.5)
        current_text = initial_text
        best_text = initial_text
        best_score = 0.0
        iteration_history = []
        
        logger.info(f"🎯 Запуск RLHF системы для {analysis_type}, цель: {target_score}/10")
        
        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"🔄 RLHF Итерация #{iteration}")
            
            # Получаем оценку от валидатора
            if hasattr(self.validator, 'claude_agent') and self.validator.use_claude:
                validation_result = await self.validator.claude_agent.claude_validator.validate_and_score(
                    current_text, original_prompt, analysis_type
                )
            else:
                # Резервная оценка
                validation_result = await self._fallback_scoring(current_text, analysis_type)
            
            current_score = validation_result.get('score', 0.0)
            issues = validation_result.get('issues', [])
            suggestions = validation_result.get('suggestions', [])
            
            # Сохраняем историю
            iteration_data = {
                'iteration': iteration,
                'score': current_score,
                'issues': issues,
                'suggestions': suggestions,
                'text_length': len(current_text)
            }
            iteration_history.append(iteration_data)
            
            logger.info(f"📊 Итерация {iteration}: оценка {current_score}/10")
            
            # Обновляем лучший результат
            if current_score > best_score:
                best_score = current_score
                best_text = current_text
                logger.info(f"🏆 Новый лучший результат: {best_score}/10")
            
            # Проверяем достижение цели
            if current_score >= target_score:
                logger.info(f"✅ Цель достигнута! Оценка {current_score}/10 >= {target_score}/10")
                return current_text, current_score, iteration_history
            
            # Если не последняя итерация, улучшаем текст
            if iteration < self.max_iterations:
                logger.info(f"🔧 Улучшаем текст на основе обратной связи")
                
                # Создаем улучшенный промпт на основе обратной связи
                enhanced_prompt = self._create_feedback_prompt(
                    original_prompt, 
                    current_text, 
                    issues, 
                    suggestions, 
                    target_score,
                    iteration
                )
                
                # Регенерируем текст с учетом обратной связи
                try:
                    improved_text = await self._regenerate_with_feedback(
                        generation_function,
                        generation_params,
                        enhanced_prompt,
                        current_score,
                        target_score
                    )
                    current_text = improved_text
                    logger.info(f"🚀 Текст регенерирован с учетом обратной связи")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка регенерации: {e}")
                    # Используем валидатор для исправления
                    if hasattr(self.validator, 'claude_agent') and self.validator.use_claude:
                        current_text = await self.validator.claude_agent.claude_validator.fix_text_with_claude(
                            current_text, issues, target_score
                        )
                    else:
                        current_text = await self._fallback_fix(current_text, issues)
                
                # Пауза между итерациями
                await asyncio.sleep(0.5)
        
        logger.warning(f"⚠️ Достигнуто максимум итераций ({self.max_iterations})")
        logger.info(f"🏆 Лучший результат: {best_score}/10")
        
        return best_text, best_score, iteration_history
    
    def _create_feedback_prompt(self, 
                              original_prompt: str, 
                              current_text: str, 
                              issues: List[str], 
                              suggestions: List[str],
                              target_score: float,
                              iteration: int) -> str:
        """Создание улучшенного промпта на основе обратной связи"""
        
        feedback_prompt = f"""
{original_prompt}

КРИТИЧЕСКАЯ ОБРАТНАЯ СВЯЗЬ ОТ ВАЛИДАТОРА (ИТЕРАЦИЯ {iteration}):

НАЙДЕННЫЕ ПРОБЛЕМЫ:
{chr(10).join([f"❌ {issue}" for issue in issues])}

ПРЕДЛОЖЕНИЯ ПО УЛУЧШЕНИЮ:
{chr(10).join([f"💡 {suggestion}" for suggestion in suggestions])}

ЦЕЛЬ: Достичь оценки {target_score}/10

ПРЕДЫДУЩИЙ ТЕКСТ (для анализа ошибок):
{current_text[:500]}...

ТРЕБОВАНИЯ ДЛЯ УЛУЧШЕНИЯ:
1. Исправь ВСЕ указанные проблемы
2. Реализуй ВСЕ предложения по улучшению
3. Увеличь эмоциональность и детализацию
4. Добавь больше конкретных примеров
5. Улучши структуру и читаемость
6. Используй более яркие астрологические образы

ГЕНЕРИРУЙ НОВЫЙ, УЛУЧШЕННЫЙ ТЕКСТ С УЧЕТОМ ВСЕЙ ОБРАТНОЙ СВЯЗИ!
"""
        return feedback_prompt
    
    async def _regenerate_with_feedback(self, 
                                      generation_function, 
                                      generation_params: Dict[str, Any],
                                      enhanced_prompt: str,
                                      current_score: float,
                                      target_score: float) -> str:
        """Регенерация текста с учетом обратной связи"""
        
        # Обновляем параметры генерации
        updated_params = generation_params.copy()
        
        # Добавляем мотивационные инструкции в зависимости от оценки
        if current_score < 3.0:
            motivation = "КРИТИЧЕСКИ ВАЖНО: Предыдущий текст получил очень низкую оценку. Создай ПОЛНОСТЬЮ НОВЫЙ, высококачественный текст!"
        elif current_score < 6.0:
            motivation = "ВАЖНО: Улучши качество текста, добавь больше деталей и эмоциональности!"
        else:
            motivation = "ПОЧТИ ГОТОВО: Доведи текст до совершенства, исправив последние недочеты!"
        
        enhanced_prompt_with_motivation = f"{enhanced_prompt}\n\n{motivation}"
        
        # Если есть возможность обновить промпт в параметрах
        if 'prompt' in updated_params:
            updated_params['prompt'] = enhanced_prompt_with_motivation
        
        # Вызываем функцию генерации с обновленными параметрами
        improved_text = await generation_function(**updated_params)
        
        return improved_text
    
    async def _fallback_scoring(self, text: str, analysis_type: str) -> Dict[str, Any]:
        """Резервная система оценки при недоступности Claude"""
        
        # Простая оценка на основе локальных правил
        score = 5.0  # Базовая оценка
        issues = []
        suggestions = []
        
        # Проверяем длину
        if len(text) < 500:
            score -= 2.0
            issues.append("Текст слишком короткий")
            suggestions.append("Увеличь объем текста до минимум 1000 слов")
        
        # Проверяем эмодзи
        emoji_count = len([c for c in text if ord(c) > 127])
        if emoji_count < 10:
            score -= 1.0
            issues.append("Недостаточно эмодзи")
            suggestions.append("Добавь больше эмодзи для структурирования")
        
        # Проверяем структуру
        if '🌟' not in text:
            score -= 1.5
            issues.append("Отсутствуют заголовки")
            suggestions.append("Добавь заголовки с эмодзи 🌟")
        
        return {
            'score': max(1.0, score),
            'is_valid': score >= 7.0,
            'issues': issues,
            'suggestions': suggestions,
            'confidence': 0.7
        }
    
    async def _fallback_fix(self, text: str, issues: List[str]) -> str:
        """Резервное исправление текста"""
        improved_text = text
        
        # Простые исправления
        if "короткий" in str(issues):
            improved_text += "\n\n🌟 Дополнительный анализ\n\nДанная компания обладает уникальными астрологическими характеристиками, которые определяют её потенциал и возможности развития."
        
        if "эмодзи" in str(issues):
            improved_text = "🌟 " + improved_text.replace("\n", "\n💎 ", 1)
        
        return improved_text


class EnhancedValidationAgent:
    """Улучшенный агент валидации с RLHF"""
    
    def __init__(self, base_validator):
        """
        Инициализация улучшенного агента
        
        Args:
            base_validator: Базовый валидатор
        """
        self.base_validator = base_validator
        self.rlhf_system = RLHFFeedbackSystem(base_validator)
        logger.info("✅ RLHF валидационная система инициализирована")
    
    async def validate_and_improve_with_rlhf(self, 
                                           text: str, 
                                           analysis_type: str,
                                           original_prompt: str,
                                           generation_function=None,
                                           generation_params: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Основной метод валидации с RLHF
        
        Args:
            text (str): Исходный текст
            analysis_type (str): Тип анализа
            original_prompt (str): Оригинальный промпт
            generation_function: Функция для регенерации
            generation_params (Dict): Параметры генерации
            
        Returns:
            Tuple[str, Dict]: (улучшенный текст, метрики качества)
        """
        try:
            if generation_function and generation_params:
                # Полный RLHF цикл с регенерацией
                improved_text, final_score, history = await self.rlhf_system.iterative_improvement(
                    text, analysis_type, original_prompt, generation_function, generation_params
                )
                
                metrics = {
                    'final_score': final_score,
                    'iterations_used': len(history),
                    'improvement_history': history,
                    'method': 'RLHF_full'
                }
            else:
                # Только валидация и исправление без регенерации
                improved_text = await self.base_validator.validate_and_fix(text, analysis_type, original_prompt)
                
                # Получаем финальную оценку
                if hasattr(self.base_validator, 'claude_agent') and self.base_validator.use_claude:
                    final_validation = await self.base_validator.claude_agent.claude_validator.validate_and_score(
                        improved_text, original_prompt, analysis_type
                    )
                    final_score = final_validation.get('score', 5.0)
                else:
                    final_score = 6.0  # Базовая оценка для резервного режима
                
                metrics = {
                    'final_score': final_score,
                    'iterations_used': 1,
                    'improvement_history': [],
                    'method': 'validation_only'
                }
            
            logger.info(f"🎯 RLHF завершен: {final_score}/10 за {metrics['iterations_used']} итераций")
            return improved_text, metrics
            
        except Exception as e:
            logger.error(f"❌ Ошибка RLHF системы: {e}")
            # Возвращаем базовую очистку
            cleaned_text = self.base_validator._basic_cleanup(text) if hasattr(self.base_validator, '_basic_cleanup') else text
            return cleaned_text, {'final_score': 5.0, 'method': 'fallback', 'error': str(e)}
