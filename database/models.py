"""
Модели базы данных AstroBot
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Dict, Any, Optional

Base = declarative_base()


class User(Base):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    
    # Личные данные для астрологического анализа
    birth_date = Column(DateTime, nullable=True)
    birth_place = Column(String(255), nullable=True)
    birth_time = Column(String(10), nullable=True)  # HH:MM формат
    zodiac_sign = Column(String(50), nullable=True)
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    language = Column(String(10), default='ru')
    
    # Связи
    companies = relationship("Company", back_populates="owner")
    analyses = relationship("Analysis", back_populates="user")
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"


class Company(Base):
    """Модель компании"""
    __tablename__ = 'companies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Основная информация
    name = Column(String(500), nullable=False)
    legal_name = Column(String(500), nullable=True)  # Полное юридическое название
    inn = Column(String(20), nullable=True)
    ogrn = Column(String(20), nullable=True)
    
    # Данные регистрации для астрологического анализа
    registration_date = Column(DateTime, nullable=False)
    registration_place = Column(String(255), nullable=False)
    registration_time = Column(String(10), nullable=True)  # HH:MM формат
    
    # Координаты для астрологических расчетов
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Астрологические данные
    zodiac_sign = Column(String(50), nullable=True)
    zodiac_element = Column(String(20), nullable=True)  # Огонь, Вода, Воздух, Земля
    ruling_planet = Column(String(50), nullable=True)
    
    # Нумерологические данные
    name_number = Column(Integer, nullable=True)
    destiny_number = Column(Integer, nullable=True)
    
    # Бизнес информация
    industry = Column(String(255), nullable=True)
    business_type = Column(String(100), nullable=True)  # ООО, ИП, АО и т.д.
    description = Column(Text, nullable=True)
    website = Column(String(255), nullable=True)
    
    # Данные руководства
    owner_name = Column(String(255), nullable=True)
    owner_birth_date = Column(DateTime, nullable=True)
    director_name = Column(String(255), nullable=True)
    director_birth_date = Column(DateTime, nullable=True)
    
    # Натальная карта (JSON)
    natal_chart = Column(JSON, nullable=True)
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Связи
    owner = relationship("User", back_populates="companies")
    analyses = relationship("Analysis", back_populates="company")
    
    def __repr__(self):
        return f"<Company(name={self.name}, zodiac_sign={self.zodiac_sign})>"


class Analysis(Base):
    """Модель астрологического анализа"""
    __tablename__ = 'analyses'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=True)
    
    # Тип анализа
    analysis_type = Column(String(100), nullable=False)  # zodiac, forecast, compatibility, daily
    
    # Входные данные
    input_data = Column(JSON, nullable=True)  # Сохраняем параметры запроса
    
    # Результаты анализа
    result_text = Column(Text, nullable=False)  # Основной текст результата
    result_data = Column(JSON, nullable=True)  # Структурированные данные
    
    # Астрологические данные
    zodiac_signs = Column(JSON, nullable=True)  # Знаки зодиака участников
    compatibility_score = Column(Integer, nullable=True)  # Оценка совместимости 0-100
    
    # Источники данных
    news_used = Column(Boolean, default=False)
    numerology_used = Column(Boolean, default=False)
    astrology_api_used = Column(Boolean, default=False)
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    processing_time = Column(Float, nullable=True)  # Время обработки в секундах
    
    # Связи
    user = relationship("User", back_populates="analyses")
    company = relationship("Company", back_populates="analyses")
    
    def __repr__(self):
        return f"<Analysis(type={self.analysis_type}, user_id={self.user_id})>"


class NewsCache(Base):
    """Кэш новостей для оптимизации"""
    __tablename__ = 'news_cache'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Ключ кэша
    cache_key = Column(String(255), unique=True, nullable=False, index=True)
    
    # Данные
    news_data = Column(JSON, nullable=False)
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    def __repr__(self):
        return f"<NewsCache(key={self.cache_key})>"


class UserSession(Base):
    """Сессии пользователей для многошагового ввода"""
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Данные сессии
    current_state = Column(String(100), nullable=False)  # Состояние из states.py
    session_data = Column(JSON, nullable=True)  # Временные данные
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # Связи
    user = relationship("User")
    
    def __repr__(self):
        return f"<UserSession(user_id={self.user_id}, state={self.current_state})>"


class SystemLog(Base):
    """Логи системы для мониторинга"""
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Данные лога
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    module = Column(String(100), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    # Дополнительные данные
    extra_data = Column(JSON, nullable=True)
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    user = relationship("User")
    
    def __repr__(self):
        return f"<SystemLog(level={self.level}, module={self.module})>"


