"""
Модуль для настройки логирования
"""

import os
import sys
from loguru import logger


def setup_logger():
    """
    Настройка логгера для проекта
    
    Returns:
        logger: Настроенный логгер
    """
    # Удаляем стандартный обработчик
    logger.remove()
    
    # Получаем уровень логирования из переменных окружения
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    
    # Формат логов
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # Добавляем обработчик для консоли
    logger.add(
        sys.stdout,
        format=log_format,
        level=log_level,
        colorize=True
    )
    
    # Добавляем обработчик для файла
    logger.add(
        "logs/astrobot.log",
        format=log_format,
        level=log_level,
        rotation="100 MB",
        retention="30 days",
        compression="zip"
    )
    
    # Создаем директорию для логов если её нет
    os.makedirs("logs", exist_ok=True)
    
    return logger




