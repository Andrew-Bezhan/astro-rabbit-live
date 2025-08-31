"""
Состояния для сбора данных от пользователя
"""

from enum import Enum, auto
from typing import Optional, Dict
from datetime import datetime


class BotState(Enum):
    """Состояния бота для сбора данных"""
    
    # Основные состояния
    IDLE = auto()                    # Бот ожидает команды
    
    # Состояния для простого анализа знака зодиака
    ZODIAC_COMPANY_NAME = auto()     # Ввод названия компании
    ZODIAC_REG_DATE = auto()         # Ввод даты регистрации
    ZODIAC_REG_PLACE = auto()        # Ввод места регистрации
    
    # Состояния для полного бизнес-прогноза
    BUSINESS_COMPANY_NAME = auto()   # Ввод названия компании
    BUSINESS_REG_DATE = auto()       # Ввод даты регистрации
    BUSINESS_REG_PLACE = auto()      # Ввод места регистрации
    BUSINESS_SPHERE = auto()         # Выбор сферы деятельности
    BUSINESS_OWNER_NAME = auto()     # Ввод имени собственника
    BUSINESS_OWNER_BIRTH = auto()    # Ввод даты рождения собственника
    BUSINESS_DIRECTOR_NAME = auto()  # Ввод имени директора
    BUSINESS_DIRECTOR_BIRTH = auto() # Ввод даты рождения директора
    
    # Состояния для создания профиля компании
    PROFILE_COMPANY_NAME = auto()    # Ввод названия для профиля
    PROFILE_REG_DATE = auto()        # Ввод даты регистрации для профиля
    PROFILE_REG_PLACE = auto()       # Ввод места регистрации для профиля
    PROFILE_SPHERE = auto()          # Выбор сферы для профиля
    PROFILE_OWNER_NAME = auto()      # Ввод имени собственника для профиля
    PROFILE_OWNER_BIRTH = auto()     # Ввод даты рождения собственника для профиля
    PROFILE_DIRECTOR_NAME = auto()   # Ввод имени директора для профиля
    PROFILE_DIRECTOR_BIRTH = auto()  # Ввод даты рождения директора для профиля
    
    # Состояния для проверки совместимости
    COMPAT_COMPANY_SELECT = auto()   # Выбор компании из профиля
    COMPAT_TYPE_SELECT = auto()      # Выбор типа совместимости
    COMPAT_OBJECT_NAME = auto()      # Ввод имени объекта
    COMPAT_OBJECT_BIRTH = auto()     # Ввод даты рождения объекта
    COMPAT_OBJECT_PLACE = auto()     # Ввод места рождения объекта
    
    # Состояния для настройки ежедневных прогнозов
    DAILY_COMPANY_SELECT = auto()    # Выбор компании для прогнозов
    DAILY_TIME_SET = auto()          # Настройка времени уведомлений
    
    # Состояния для управления профилями компаний
    PROFILE_CREATE = auto()          # Создание нового профиля
    PROFILE_EDIT = auto()            # Редактирование профиля
    PROFILE_DELETE_CONFIRM = auto()  # Подтверждение удаления
    
    # Состояния для детального анализа
    ANALYSIS_COMPANY_SELECT = auto() # Выбор компании для анализа
    ANALYSIS_TYPE_SELECT = auto()    # Выбор типа анализа
    
    # Состояния для выбора компании из профиля
    SELECTING_COMPANY_FOR_FORECAST = auto()  # Выбор компании для прогноза
    SELECTING_COMPANY_FOR_COMPATIBILITY = auto()  # Выбор компании для совместимости


class UserData:
    """Класс для хранения данных пользователя в процессе диалога"""
    
    def __init__(self):
        # Данные компании
        self.company_name: Optional[str] = None
        self.registration_date: Optional[datetime] = None
        self.registration_place: Optional[str] = None
        self.business_sphere: Optional[str] = None
        
        # Данные собственника
        self.owner_name: Optional[str] = None
        self.owner_birth_date: Optional[datetime] = None
        
        # Данные директора
        self.director_name: Optional[str] = None
        self.director_birth_date: Optional[datetime] = None
        
        # Данные для совместимости
        self.compatibility_type: Optional[str] = None
        self.object_name: Optional[str] = None
        self.object_birth_date: Optional[datetime] = None
        self.object_birth_place: Optional[str] = None
        
        # Временные данные для сохранения профиля
        self.temp_company_data: Optional[Dict] = None
        
        # Настройки
        self.daily_forecast_enabled: bool = False
        self.daily_forecast_time: str = "08:00"
        self.selected_company_id: Optional[int] = None
        
        # Временные данные
        self.current_step: Optional[str] = None
        self.temp_data: dict = {}
    
    def reset(self):
        """Сброс всех данных"""
        # Данные компании
        self.company_name = None
        self.registration_date = None
        self.registration_place = None
        self.business_sphere = None
        
        # Данные собственника
        self.owner_name = None
        self.owner_birth_date = None
        
        # Данные директора
        self.director_name = None
        self.director_birth_date = None
        
        # Данные для совместимости
        self.compatibility_type = None
        self.object_name = None
        self.object_birth_date = None
        self.object_birth_place = None
        
        # Настройки
        self.daily_forecast_enabled = False
        self.daily_forecast_time = "08:00"
        self.selected_company_id = None
        
        # Временные данные
        self.current_step = None
        self.temp_data = {}
    
    def to_dict(self) -> dict:
        """
        Преобразование в словарь
        
        Returns:
            dict: Данные пользователя
        """
        return {
            'company_name': self.company_name,
            'registration_date': self.registration_date,
            'registration_place': self.registration_place,
            'business_sphere': self.business_sphere,
            'owner_name': self.owner_name,
            'owner_birth_date': self.owner_birth_date,
            'director_name': self.director_name,
            'director_birth_date': self.director_birth_date,
            'compatibility_type': self.compatibility_type,
            'object_name': self.object_name,
            'object_birth_date': self.object_birth_date,
            'object_birth_place': self.object_birth_place,
            'daily_forecast_enabled': self.daily_forecast_enabled,
            'daily_forecast_time': self.daily_forecast_time,
            'selected_company_id': self.selected_company_id
        }
    
    def from_dict(self, data: dict):
        """
        Загрузка из словаря
        
        Args:
            data (dict): Данные пользователя
        """
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def get_company_data(self) -> dict:
        """
        Получение данных компании
        
        Returns:
            dict: Данные компании
        """
        return {
            'name': self.company_name,
            'registration_date': self.registration_date,
            'registration_place': self.registration_place,
            'business_sphere': self.business_sphere,
            'owner_name': self.owner_name,
            'owner_birth_date': self.owner_birth_date,
            'director_name': self.director_name,
            'director_birth_date': self.director_birth_date
        }
    
    def get_compatibility_data(self) -> dict:
        """
        Получение данных для совместимости
        
        Returns:
            dict: Данные для анализа совместимости
        """
        return {
            'type': self.compatibility_type,
            'name': self.object_name,
            'birth_date': self.object_birth_date,
            'birth_place': self.object_birth_place
        }
    
    def is_company_complete(self) -> bool:
        """
        Проверка полноты данных компании для базового анализа
        
        Returns:
            bool: True если данные полные
        """
        return all([
            self.company_name,
            self.registration_date,
            self.registration_place
        ])
    
    def is_business_complete(self) -> bool:
        """
        Проверка полноты данных для бизнес-прогноза
        
        Returns:
            bool: True если данные полные
        """
        return all([
            self.company_name,
            self.registration_date,
            self.registration_place,
            self.business_sphere,
            self.director_birth_date  # Обязательное поле
        ])
    
    def is_compatibility_complete(self) -> bool:
        """
        Проверка полноты данных для анализа совместимости
        
        Returns:
            bool: True если данные полные
        """
        return all([
            self.compatibility_type,
            self.object_name,
            self.object_birth_date
        ])


class StateManager:
    """Менеджер состояний пользователей"""
    
    def __init__(self):
        self.user_states = {}    # user_id -> BotState
        self.user_data = {}      # user_id -> UserData
    
    def get_state(self, user_id: int) -> BotState:
        """
        Получение текущего состояния пользователя
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            BotState: Текущее состояние
        """
        return self.user_states.get(user_id, BotState.IDLE)
    
    def set_state(self, user_id: int, state: BotState):
        """
        Установка состояния пользователя
        
        Args:
            user_id (int): ID пользователя
            state (BotState): Новое состояние
        """
        self.user_states[user_id] = state
    
    def get_user_data(self, user_id: int) -> UserData:
        """
        Получение данных пользователя
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            UserData: Данные пользователя
        """
        if user_id not in self.user_data:
            self.user_data[user_id] = UserData()
        return self.user_data[user_id]
    
    def reset_user(self, user_id: int):
        """
        Сброс состояния и данных пользователя
        
        Args:
            user_id (int): ID пользователя
        """
        self.user_states[user_id] = BotState.IDLE
        if user_id in self.user_data:
            self.user_data[user_id].reset()
    
    def clear_user_data(self, user_id: int):
        """
        Полная очистка данных пользователя
        
        Args:
            user_id (int): ID пользователя
        """
        if user_id in self.user_states:
            del self.user_states[user_id]
        if user_id in self.user_data:
            del self.user_data[user_id]

