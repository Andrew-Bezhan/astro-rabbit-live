"""
Система применения редакторских патчей от валидатора
"""

import re
from typing import Dict, Any, List, Optional
from utils.logger import setup_logger

logger = setup_logger()


def apply_validator_patches(current_text: str, report: dict) -> str:
    """
    Применяет патчи от валидатора:
    1) inline_fixes (find/replace)
    2) section_patches (insert/replace/append) по exact title
    
    Args:
        current_text (str): Исходный текст
        report (dict): Отчет валидатора с патчами
        
    Returns:
        str: Текст с примененными патчами
    """
    text = current_text
    patches_applied = 0
    
    logger.info(f"🔧 Применяем патчи валидатора к тексту ({len(text)} символов)")

    # 1) inline fixes — безопасные точечные замены
    inline_fixes = report.get("inline_fixes", [])
    for fx in inline_fixes:
        find = (fx.get("find") or "").strip()
        repl = (fx.get("replace") or "").strip()
        if find and repl and find in text:
            text = text.replace(find, repl)
            patches_applied += 1
            logger.info(f"✅ Применена точечная замена: '{find[:50]}...' → '{repl[:50]}...'")

    # 2) section patches — работа с разделами по заголовкам
    patches = report.get("section_patches", [])
    if patches:
        logger.info(f"🔄 Применяем {len(patches)} патчей разделов")
        
        def find_section(title: str):
            """Ищем заголовок строго как отдельную строку"""
            # ищем заголовок строго как отдельную строку
            pat = re.compile(rf"(?m)^\s*{re.escape(title)}\s*$")
            m = pat.search(text)
            return m.start() if m else -1

        for p in patches:
            title = (p.get("title") or "").strip()
            action = (p.get("action") or "append").strip().lower()
            content = (p.get("content") or "").strip()
            
            if not title or not content:
                logger.warning(f"⚠️ Пропускаем патч с пустыми данными: {title}")
                continue

            idx = find_section(title)
            logger.info(f"🎯 Патч '{title}' (действие: {action}, найден: {idx != -1})")
            
            if action == "insert":
                if idx == -1:
                    # добавляем новый раздел в конец с пустой строкой перед ним
                    text = text.rstrip() + f"\n\n{content}\n"
                    patches_applied += 1
                    logger.info(f"➕ Добавлен новый раздел: {title}")
                else:
                    # уже есть — заменим (чтобы точно прошли)
                    text = re.sub(rf"(?ms)^\s*{re.escape(title)}\s*$.*?(?=^\S|\Z)", content+"\n", text)
                    patches_applied += 1
                    logger.info(f"🔄 Заменен существующий раздел: {title}")
                    
            elif action == "replace":
                if idx == -1:
                    text = text.rstrip() + f"\n\n{content}\n"
                    patches_applied += 1
                    logger.info(f"➕ Добавлен раздел (replace): {title}")
                else:
                    text = re.sub(rf"(?ms)^\s*{re.escape(title)}\s*$.*?(?=^\S|\Z)", content+"\n", text)
                    patches_applied += 1
                    logger.info(f"🔄 Заменен раздел: {title}")
                    
            else:  # append
                if idx == -1:
                    text = text.rstrip() + f"\n\n{content}\n"
                    patches_applied += 1
                    logger.info(f"➕ Добавлен раздел (append): {title}")
                else:
                    # найдём конец текущего раздела (до следующего заголовка)
                    sec_pat = re.compile(rf"(?ms)^\s*{re.escape(title)}\s*$.*?(?=^\S|\Z)")
                    m = sec_pat.search(text)
                    if m:
                        existing = m.group(0).rstrip() + "\n"
                        text = text[:m.start()] + existing + "\n" + content.strip() + "\n" + text[m.end():]
                        patches_applied += 1
                        logger.info(f"📝 Дополнен раздел: {title}")
                    else:
                        text = text.rstrip() + f"\n\n{content}\n"
                        patches_applied += 1
                        logger.info(f"➕ Добавлен раздел (append fallback): {title}")

    logger.info(f"✅ Применено патчей: {patches_applied}, итоговый размер: {len(text)} символов")
    return text


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Вычисляет коэффициент совпадения текстов (Jaccard на словах)
    
    Args:
        text1 (str): Первый текст
        text2 (str): Второй текст
        
    Returns:
        float: Коэффициент от 0.0 до 1.0
    """
    try:
        # Простая метрика на основе слов
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
            
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        similarity = intersection / union if union > 0 else 0.0
        logger.info(f"📊 Схожесть текстов: {similarity:.2f}")
        return similarity
        
    except Exception as e:
        logger.warning(f"⚠️ Ошибка расчета схожести: {e}")
        return 0.5


def determine_editing_mode(iteration: int, current_score: float, prev_score: float, similarity: float) -> str:
    """
    Определяет режим редактирования на основе прогресса
    
    Args:
        iteration (int): Номер итерации
        current_score (float): Текущая оценка
        prev_score (float): Предыдущая оценка
        similarity (float): Схожесть с предыдущей версией
        
    Returns:
        str: "soft" или "hard"
    """
    score_delta = current_score - prev_score if prev_score > 0 else 0.0
    
    # Переключаемся на hard режим если:
    # - Итерация >= 2 И прирост < 0.5
    # - ИЛИ схожесть > 0.95 (текст не меняется)
    # - ИЛИ оценка застряла ниже 7.0 на 3+ итерации
    
    if iteration >= 2 and score_delta < 0.5:
        logger.info(f"🔄 Переключение на HARD режим: малый прирост ({score_delta:.1f})")
        return "hard"
    
    if similarity > 0.95:
        logger.info(f"🔄 Переключение на HARD режим: текст не меняется ({similarity:.2f})")
        return "hard"
        
    if iteration >= 3 and current_score < 7.0:
        logger.info(f"🔄 Переключение на HARD режим: застрял ниже 7.0 ({current_score:.1f})")
        return "hard"
    
    logger.info(f"🔧 Продолжаем SOFT режим (итерация {iteration}, прирост {score_delta:.1f})")
    return "soft"


def check_score_requirements(report: dict, requirements: Optional[dict] = None) -> bool:
    """
    Проверяет соответствие всем требованиям по метрикам
    
    Args:
        report (dict): Отчет валидатора
        requirements (dict): Требования по метрикам
        
    Returns:
        bool: True если все требования выполнены
    """
    if not requirements:
        requirements = {
            "score": 7.0,
            "structure": 7.5,
            "formatting": 8.0,
            "content": 7.0,
            "language": 7.0
        }
    
    passed_metrics = []
    failed_metrics = []
    
    for metric, required_score in requirements.items():
        current_score = float(report.get(metric, 0.0))
        if current_score >= required_score:
            passed_metrics.append(f"{metric}: {current_score:.1f}>={required_score}")
        else:
            failed_metrics.append(f"{metric}: {current_score:.1f}<{required_score}")
    
    # Проверяем блокирующие проблемы
    blocking_issues = report.get("blocking_issues", [])
    critical_issues = [issue for issue in blocking_issues if issue.get("severity") == "CRITICAL"]
    
    all_passed = len(failed_metrics) == 0 and len(critical_issues) == 0
    
    logger.info(f"📊 Метрики: ✅{len(passed_metrics)} ❌{len(failed_metrics)} 🚨{len(critical_issues)}")
    if failed_metrics:
        logger.info(f"❌ Не пройдены: {failed_metrics[:3]}")
    if critical_issues:
        logger.info(f"🚨 Критические проблемы: {[i.get('code', 'unknown') for i in critical_issues[:3]]}")
    
    return all_passed
