"""
Железобетонный JSON парсер для Claude ответов с авто-починкой
"""

import json
import re
from typing import Any, Dict
from utils.logger import setup_logger

logger = setup_logger()

try:
    import jsonschema  # type: ignore
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    jsonschema = None  # type: ignore
    logger.warning("⚠️ jsonschema не установлена, валидация схемы отключена")

VALIDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": ["number", "string"]},
        "structure": {"type": ["number", "string"]},
        "content": {"type": ["number", "string"]},
        "language": {"type": ["number", "string"]},
        "formatting": {"type": ["number", "string"]},
        "blocking_issues": {"type": "array"},
        "section_patches": {"type": "array"},
        "inline_fixes": {"type": "array"},
        "delta_targets": {"type": "object"},
        "skeleton": {"type": "string"},
        "issues": {"type": "array", "items": {"type": "string"}},
        "suggestions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["score"],
    "additionalProperties": True,
}

_NUMBER_FIELDS = ("score", "structure", "content", "language", "formatting")


def _to_float(val, default=0.0):
    """Безопасное приведение к float"""
    try:
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            # чистим пробелы/кавычки/запятые внутри числа
            cand = val.strip().strip('"').strip("'")
            return float(cand)
    except Exception:
        pass
    return default


def _coerce_numbers(d: Dict[str, Any]) -> Dict[str, Any]:
    """Приведение числовых полей к float"""
    for k in _NUMBER_FIELDS:
        if k in d:
            d[k] = _to_float(d[k], 0.0)
    return d


def _extract_json_block(text: str) -> str:
    """
    Пытается вытащить первый валидный JSON-объект из текста:
    - срез между первой '{' и соответствующей '}' с балансировкой скобок
    - fallback: самая «похоже на JSON»-часть по regex
    """
    text = text.strip()
    start = text.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i+1]
    
    # fallback: убираем маркдаун-кодовые блоки и пробуем найти JSON по regex
    code = re.sub(r"^```(json)?|```$", "", text, flags=re.MULTILINE).strip()
    m = re.search(r"\{[\s\S]*\}", code)
    if m:
        return m.group(0)
    
    return text  # в худшем случае вернем исходник


def parse_validation_response(content: str) -> Dict[str, Any]:
    """
    Железобетонный парсер Claude ответов с авто-починкой
    
    Args:
        content (str): Ответ от Claude
        
    Returns:
        Dict[str, Any]: Распарсенный и нормализованный результат
    """
    # предварительная очистка «ломающихся» символов переноса/юникода
    clean = (content or "").replace("\r", " ").replace("\t", " ")
    candidate = _extract_json_block(clean)

    # первая попытка — как есть
    try:
        data = json.loads(candidate)
        logger.info("✅ JSON распарсен с первой попытки")
    except Exception as first_error:
        logger.warning(f"⚠️ Первая попытка парсинга не удалась: {first_error}")
        
        # мягкая починка: убираем «висячие» кавычки, заменяем запятые в числах
        repaired = candidate.replace("\n", " ")
        repaired = re.sub(r"(\d),(\d)", r"\1.\2", repaired)  # 9,0 -> 9.0
        repaired = repaired.replace(",,", ",")
        
        # часто встречается мусор типа: "score": " 9.0, \"structure\": 8.0 ...
        # попробуем отсечь хвост после первого корректного числа в поле score
        repaired = re.sub(r'"score"\s*:\s*"([^"]+)"', 
                         lambda m: f'"score": "{m.group(1).split(",")[0].strip()}"', 
                         repaired)
        
        try:
            data = json.loads(repaired)
            logger.info("✅ JSON восстановлен после починки")
        except Exception as e:
            logger.error(f"❌ Критическая ошибка парсинга JSON: {e}")
            logger.error(f"RAW ответ: {content[:800]}")
            # Возвращаем дефолтную структуру
            data = {
                "score": 5.0,
                "structure": 5.0,
                "content": 5.0,
                "language": 5.0,
                "issues": ["Ошибка парсинга ответа валидатора"],
                "suggestions": ["Проверьте корректность промпта"]
            }

    # Приводим числа к float
    data = _coerce_numbers(data)

    # Валидация схемы (если доступна)
    if HAS_JSONSCHEMA and jsonschema:
        try:
            jsonschema.validate(instance=data, schema=VALIDATION_SCHEMA)  # type: ignore
            logger.info("✅ JSON соответствует схеме")
        except Exception as e:
            # не валидно по схеме — но оставим как есть, лишь залогируем
            logger.warning(f"⚠️ JSON валидатора не соответствует схеме: {e}")

    # нормализуем пустые массивы
    data.setdefault("issues", [])
    data.setdefault("suggestions", [])

    return data
