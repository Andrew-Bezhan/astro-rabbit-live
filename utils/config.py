"""
Модуль конфигурации проекта
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class BotConfig:
    """Конфигурация Telegram бота"""
    token: str
    webhook_url: Optional[str] = None
    webhook_port: int = 8443


@dataclass
class DatabaseConfig:
    """Конфигурация базы данных"""
    url: str
    echo: bool = False


@dataclass
class QdrantConfig:
    """Конфигурация Qdrant"""
    api_key: str
    url: str
    collection_name: str = "astrobot-results"


@dataclass
class OpenAIConfig:
    """Конфигурация OpenAI (Deprecated - используется Gemini)"""
    api_key: str
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2000

@dataclass
class GeminiConfig:
    """Конфигурация Google Gemini"""
    api_key: str
    model: str = "gemini-2.5-flash"
    temperature: float = 0.7
    max_tokens: int = 2000
    thinking_budget: int = 0  # Отключаем thinking для скорости


@dataclass
class NewsDataConfig:
    """Конфигурация NewsData.io"""
    api_key: str
    base_url: str = "https://newsdata.io/api/1/news"
    language: str = "ru"
    country: str = "ru"


@dataclass
class AstrologyConfig:
    """Конфигурация астрологического API"""
    client_id: str
    client_secret: str
    base_url: str = "https://api.prokerala.com"


@dataclass
class AppConfig:
    """Основная конфигурация приложения"""
    bot: BotConfig
    database: DatabaseConfig
    qdrant: QdrantConfig
    openai: OpenAIConfig  # Deprecated
    gemini: GeminiConfig
    newsdata: NewsDataConfig
    astrology: AstrologyConfig


def load_config() -> AppConfig:
    """
    Загружает конфигурацию из переменных окружения
    
    Returns:
        AppConfig: Объект конфигурации
    """
    # Загружаем .env файл
    from dotenv import load_dotenv
    load_dotenv()
    return AppConfig(
        bot=BotConfig(
            token=os.getenv('TELEGRAM_BOT_TOKEN', ''),
            webhook_url=os.getenv('WEBHOOK_URL'),
            webhook_port=int(os.getenv('WEBHOOK_PORT', 8443))
        ),
        database=DatabaseConfig(
            url=os.getenv('DATABASE_URL', 'sqlite:///astrobot.db'),
            echo=os.getenv('DATABASE_ECHO', 'False').lower() == 'true'
        ),
        qdrant=QdrantConfig(
            api_key=os.getenv('QDRANT_API_KEY', ''),
            url=os.getenv('QDRANT_URL', ''),
            collection_name=os.getenv('QDRANT_COLLECTION_NAME', 'astrobot-results')
        ),
        openai=OpenAIConfig(
            api_key=os.getenv('OPENAI_API_KEY', ''),
            model=os.getenv('OPENAI_MODEL', 'gpt-4'),
            temperature=float(os.getenv('OPENAI_TEMPERATURE', 0.7)),
            max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', 2000))
        ),
        gemini=GeminiConfig(
            api_key=os.getenv('GEMINI_API_KEY', ''),
            model=os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'),
            temperature=float(os.getenv('GEMINI_TEMPERATURE', 0.7)),
            max_tokens=int(os.getenv('GEMINI_MAX_TOKENS', 2000)),
            thinking_budget=int(os.getenv('GEMINI_THINKING_BUDGET', 0))
        ),
        newsdata=NewsDataConfig(
            api_key=os.getenv('NEWSDATA_API_KEY', '')
        ),
        astrology=AstrologyConfig(
            client_id=os.getenv('PROKERALA_CLIENT_ID', ''),
            client_secret=os.getenv('PROKERALA_CLIENT_SECRET', '')
        )
    )
