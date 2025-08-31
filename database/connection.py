"""
Подключение к базе данных
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator
import os

from .models import Base
from utils.config import load_config
from utils.logger import setup_logger

logger = setup_logger()


class DatabaseManager:
    """Менеджер базы данных"""
    
    def __init__(self):
        """Инициализация менеджера БД"""
        self.config = load_config()
        self.engine = None
        self.SessionLocal = None
        
        self._init_database()
    
    def _init_database(self):
        """Инициализация подключения к БД"""
        try:
            database_url = self.config.database.url
            
            # Настройки для SQLite
            if database_url.startswith('sqlite'):
                self.engine = create_engine(
                    database_url,
                    connect_args={
                        "check_same_thread": False,
                        "timeout": 20
                    },
                    poolclass=StaticPool,
                    echo=self.config.database.echo
                )
            # Настройки для PostgreSQL
            elif database_url.startswith('postgresql'):
                self.engine = create_engine(
                    database_url,
                    pool_pre_ping=True,
                    pool_recycle=3600,
                    echo=self.config.database.echo
                )
            else:
                raise ValueError(f"Неподдерживаемый тип БД: {database_url}")
            
            # Создаем фабрику сессий
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info(f"🗃️ База данных инициализирована: {database_url}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации БД: {e}")
            raise
    
    def create_tables(self):
        """Создание всех таблиц"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("✅ Таблицы базы данных созданы")
        except Exception as e:
            logger.error(f"❌ Ошибка создания таблиц: {e}")
            raise
    
    def drop_tables(self):
        """Удаление всех таблиц (для разработки)"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("⚠️ Все таблицы удалены")
        except Exception as e:
            logger.error(f"❌ Ошибка удаления таблиц: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Контекстный менеджер для работы с сессией БД
        
        Yields:
            Session: Сессия SQLAlchemy
        """
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized")
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Ошибка в сессии БД: {e}")
            raise
        finally:
            session.close()
    
    def get_session_factory(self):
        """Получение фабрики сессий"""
        return self.SessionLocal
    
    def health_check(self) -> bool:
        """Проверка состояния БД"""
        try:
            from sqlalchemy import text
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            logger.info("✅ База данных доступна")
            return True
        except Exception as e:
            logger.error(f"❌ База данных недоступна: {e}")
            return False


# Глобальный экземпляр менеджера БД
db_manager = DatabaseManager()


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Получить сессию базы данных"""
    with db_manager.get_session() as session:
        yield session


def get_db_session() -> Generator[Session, None, None]:
    """
    Функция для получения сессии БД (для Dependency Injection)
    
    Yields:
        Session: Сессия SQLAlchemy
    """
    with db_manager.get_session() as session:
        yield session


def init_database():
    """Инициализация базы данных при запуске приложения"""
    try:
        logger.info("🚀 Инициализация базы данных...")
        
        # Проверяем доступность
        if not db_manager.health_check():
            raise Exception("База данных недоступна")
        
        # Создаем таблицы
        db_manager.create_tables()
        
        logger.info("✅ База данных готова к работе")
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации базы данных: {e}")
        raise
