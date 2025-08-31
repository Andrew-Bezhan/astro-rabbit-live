"""
CRUD операции для работы с базой данных
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json

from .models import User, Company, Analysis, NewsCache, UserSession, SystemLog
from utils.logger import setup_logger

logger = setup_logger()


class UserCRUD:
    """CRUD операции для пользователей"""
    
    @staticmethod
    def create_user(session: Session, telegram_id: int, username: Optional[str] = None, 
                   first_name: Optional[str] = None, last_name: Optional[str] = None) -> User:
        """Создание нового пользователя"""
        try:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            session.add(user)
            session.flush()  # Получаем ID
            logger.info(f"👤 Создан пользователь: {telegram_id}")
            return user
        except Exception as e:
            logger.error(f"❌ Ошибка создания пользователя: {e}")
            raise
    
    @staticmethod
    def get_user_by_telegram_id(session: Session, telegram_id: int) -> Optional[User]:
        """Получение пользователя по Telegram ID"""
        return session.query(User).filter(User.telegram_id == telegram_id).first()
    
    @staticmethod
    def get_or_create_user(session: Session, telegram_id: int, username: Optional[str] = None,
                          first_name: Optional[str] = None, last_name: Optional[str] = None) -> User:
        """Получение существующего или создание нового пользователя"""
        user = UserCRUD.get_user_by_telegram_id(session, telegram_id)
        if not user:
            user = UserCRUD.create_user(session, telegram_id, username, first_name, last_name)
        else:
            # Обновляем данные если изменились
            updated = False
            if username is not None and getattr(user, 'username', None) != username:
                user.username = username  # type: ignore
                updated = True
            if first_name is not None and getattr(user, 'first_name', None) != first_name:
                user.first_name = first_name  # type: ignore
                updated = True
            if last_name is not None and getattr(user, 'last_name', None) != last_name:
                user.last_name = last_name  # type: ignore
                updated = True
            
            if updated:
                user.updated_at = datetime.utcnow()  # type: ignore
                logger.info(f"👤 Обновлен пользователь: {telegram_id}")
        
        return user
    
    @staticmethod
    def update_user_birth_data(session: Session, user_id: int, birth_date: Optional[datetime] = None,
                              birth_place: Optional[str] = None, birth_time: Optional[str] = None,
                              zodiac_sign: Optional[str] = None) -> Optional[User]:
        """Обновление астрологических данных пользователя"""
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                if birth_date:
                    user.birth_date = birth_date  # type: ignore
                if birth_place:
                    user.birth_place = birth_place  # type: ignore
                if birth_time:
                    user.birth_time = birth_time  # type: ignore
                if zodiac_sign:
                    user.zodiac_sign = zodiac_sign  # type: ignore
                
                user.updated_at = datetime.utcnow()  # type: ignore
                logger.info(f"👤 Обновлены астро-данные пользователя: {user_id}")
            return user
        except Exception as e:
            logger.error(f"❌ Ошибка обновления данных пользователя: {e}")
            raise


class CompanyCRUD:
    """CRUD операции для компаний"""
    
    @staticmethod
    def create_company(session: Session, owner_id: int, name: str, registration_date: datetime,
                      registration_place: str, **kwargs) -> Company:
        """Создание новой компании"""
        try:
            company = Company(
                owner_id=owner_id,
                name=name,
                registration_date=registration_date,
                registration_place=registration_place,
                **kwargs
            )
            session.add(company)
            session.flush()  # Получаем ID
            logger.info(f"🏢 Создана компания: {name}")
            return company
        except Exception as e:
            logger.error(f"❌ Ошибка создания компании: {e}")
            raise
    
    @staticmethod
    def get_companies_by_user(session: Session, user_id: int) -> List[Company]:
        """Получение компаний пользователя"""
        return session.query(Company).filter(
            and_(Company.owner_id == user_id, Company.is_active == True)
        ).order_by(desc(Company.created_at)).all()
    
    @staticmethod
    def get_company_by_id(session: Session, company_id: int) -> Optional[Company]:
        """Получение компании по ID"""
        return session.query(Company).filter(Company.id == company_id).first()
    
    @staticmethod
    def update_company_astro_data(session: Session, company_id: int, 
                                 zodiac_sign: Optional[str] = None, zodiac_element: Optional[str] = None,
                                 ruling_planet: Optional[str] = None, natal_chart: Optional[Dict] = None,
                                 name_number: Optional[int] = None, destiny_number: Optional[int] = None) -> Optional[Company]:
        """Обновление астрологических данных компании"""
        try:
            company = session.query(Company).filter(Company.id == company_id).first()
            if company:
                if zodiac_sign:
                    company.zodiac_sign = zodiac_sign  # type: ignore
                if zodiac_element:
                    company.zodiac_element = zodiac_element  # type: ignore
                if ruling_planet:
                    company.ruling_planet = ruling_planet  # type: ignore
                if natal_chart:
                    company.natal_chart = natal_chart  # type: ignore
                if name_number:
                    company.name_number = name_number  # type: ignore
                if destiny_number:
                    company.destiny_number = destiny_number  # type: ignore
                
                company.updated_at = datetime.utcnow()  # type: ignore
                logger.info(f"🏢 Обновлены астро-данные компании: {company_id}")
            return company
        except Exception as e:
            logger.error(f"❌ Ошибка обновления данных компании: {e}")
            raise
    
    @staticmethod
    def delete_company(session: Session, company_id: int, user_id: int) -> bool:
        """Мягкое удаление компании"""
        try:
            company = session.query(Company).filter(
                and_(Company.id == company_id, Company.owner_id == user_id)
            ).first()
            if company:
                company.is_active = False  # type: ignore
                company.updated_at = datetime.utcnow()  # type: ignore
                logger.info(f"🏢 Удалена компания: {company_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка удаления компании: {e}")
            raise


class AnalysisCRUD:
    """CRUD операции для анализов"""
    
    @staticmethod
    def create_analysis(session: Session, user_id: int, analysis_type: str,
                       result_text: str, company_id: Optional[int] = None, **kwargs) -> Analysis:
        """Создание нового анализа"""
        try:
            analysis = Analysis(
                user_id=user_id,
                company_id=company_id,
                analysis_type=analysis_type,
                result_text=result_text,
                **kwargs
            )
            session.add(analysis)
            session.flush()  # Получаем ID
            logger.info(f"📊 Создан анализ: {analysis_type} для пользователя {user_id}")
            return analysis
        except Exception as e:
            logger.error(f"❌ Ошибка создания анализа: {e}")
            raise
    
    @staticmethod
    def get_analyses_by_user(session: Session, user_id: int, limit: int = 10) -> List[Analysis]:
        """Получение анализов пользователя"""
        return session.query(Analysis).filter(Analysis.user_id == user_id)\
                     .order_by(desc(Analysis.created_at)).limit(limit).all()
    
    @staticmethod
    def get_analyses_by_company(session: Session, company_id: int, limit: int = 10) -> List[Analysis]:
        """Получение анализов для компании"""
        return session.query(Analysis).filter(Analysis.company_id == company_id)\
                     .order_by(desc(Analysis.created_at)).limit(limit).all()
    
    @staticmethod
    def get_recent_analyses(session: Session, hours: int = 24) -> List[Analysis]:
        """Получение недавних анализов"""
        since = datetime.utcnow() - timedelta(hours=hours)
        return session.query(Analysis).filter(Analysis.created_at >= since)\
                     .order_by(desc(Analysis.created_at)).all()


class SessionCRUD:
    """CRUD операции для пользовательских сессий"""
    
    @staticmethod
    def create_or_update_session(session: Session, user_id: int, current_state: str,
                               session_data: Optional[Dict] = None, expires_hours: int = 24) -> UserSession:
        """Создание или обновление сессии пользователя"""
        try:
            # Ищем существующую сессию
            user_session = session.query(UserSession).filter(UserSession.user_id == user_id).first()
            
            expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
            
            if user_session:
                # Обновляем существующую
                user_session.current_state = current_state  # type: ignore
                user_session.session_data = session_data  # type: ignore
                user_session.updated_at = datetime.utcnow()  # type: ignore
                user_session.expires_at = expires_at  # type: ignore
            else:
                # Создаем новую
                user_session = UserSession(
                    user_id=user_id,
                    current_state=current_state,
                    session_data=session_data,
                    expires_at=expires_at
                )
                session.add(user_session)
            
            session.flush()
            return user_session
        except Exception as e:
            logger.error(f"❌ Ошибка работы с сессией: {e}")
            raise
    
    @staticmethod
    def get_session(session: Session, user_id: int) -> Optional[UserSession]:
        """Получение активной сессии пользователя"""
        now = datetime.utcnow()
        return session.query(UserSession).filter(
            and_(
                UserSession.user_id == user_id,
                or_(UserSession.expires_at.is_(None), UserSession.expires_at > now)
            )
        ).first()
    
    @staticmethod
    def clear_session(session: Session, user_id: int) -> bool:
        """Очистка сессии пользователя"""
        try:
            user_session = session.query(UserSession).filter(UserSession.user_id == user_id).first()
            if user_session:
                session.delete(user_session)
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Ошибка очистки сессии: {e}")
            raise


class CacheCRUD:
    """CRUD операции для кэша"""
    
    @staticmethod
    def set_cache(session: Session, cache_key: str, data: Dict, ttl_hours: int = 1):
        """Сохранение данных в кэш"""
        try:
            expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
            
            # Удаляем старый кэш с этим ключом
            session.query(NewsCache).filter(NewsCache.cache_key == cache_key).delete()
            
            # Создаем новый
            cache_entry = NewsCache(
                cache_key=cache_key,
                news_data=data,
                expires_at=expires_at
            )
            session.add(cache_entry)
            session.flush()
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения в кэш: {e}")
            raise
    
    @staticmethod
    def get_cache(session: Session, cache_key: str) -> Optional[Dict]:
        """Получение данных из кэша"""
        try:
            now = datetime.utcnow()
            cache_entry = session.query(NewsCache).filter(
                and_(
                    NewsCache.cache_key == cache_key,
                    NewsCache.expires_at > now
                )
            ).first()
            
            if cache_entry:
                return cache_entry.news_data  # type: ignore
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения из кэша: {e}")
            return None
    
    @staticmethod
    def clear_expired_cache(session: Session) -> int:
        """Очистка устаревшего кэша"""
        try:
            now = datetime.utcnow()
            deleted = session.query(NewsCache).filter(NewsCache.expires_at <= now).delete()
            logger.info(f"🧹 Очищено {deleted} записей кэша")
            return deleted
        except Exception as e:
            logger.error(f"❌ Ошибка очистки кэша: {e}")
            return 0

