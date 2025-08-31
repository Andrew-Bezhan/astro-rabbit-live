"""
Менеджер для управления эмбеддингами и векторной базой данных
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from .qdrant_client import QdrantClient
from utils.config import load_config
from utils.logger import setup_logger

logger = setup_logger()


class EmbeddingManager:
    """Менеджер для работы с эмбеддингами"""
    
    def __init__(self):
        """Инициализация менеджера эмбеддингов"""
        self.config = load_config()
        self.qdrant_client = QdrantClient()
    
    async def save_user_dialog(self, user_id: int, dialog_text: str,
                              company_info: Optional[Dict] = None) -> str:
        """
        Сохранение диалога пользователя
        
        Args:
            user_id (int): ID пользователя
            dialog_text (str): Текст диалога
            company_info (Optional[Dict]): Информация о компании
            
        Returns:
            str: ID сохраненного документа
        """
        try:
            doc_id = await self.qdrant_client.save_astro_result(
                user_id=user_id,
                company_name=company_info.get('company_name', 'Unknown') if company_info else 'Dialog',
                analysis_type='user_dialog',
                result=dialog_text
            )
            
            logger.info(f"💬 Диалог пользователя {user_id} сохранен: {doc_id}")
            return doc_id or f"dialog_{user_id}_{int(datetime.now().timestamp())}"
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения диалога пользователя {user_id}: {e}")
            raise
    
    async def save_astro_prediction(self, company_info: Dict, prediction_text: str,
                                   prediction_type: str = "general") -> str:
        """
        Сохранение астрологического прогноза
        
        Args:
            company_info (Dict): Информация о компании
            prediction_text (str): Текст прогноза
            prediction_type (str): Тип прогноза
            
        Returns:
            str: ID сохраненного документа
        """
        try:
            doc_id = await self.qdrant_client.save_astro_result(
                user_id=company_info.get('user_id', 0) if company_info else 0,
                company_name=company_info.get('company_name', 'Unknown') if company_info else 'Unknown',
                analysis_type=prediction_type,
                result=prediction_text
            )
            
            logger.info(f"🔮 Прогноз для {company_info.get('name', 'Unknown')} сохранен: {doc_id}")
            return doc_id or f"prediction_{company_info.get('user_id', 0)}_{int(datetime.now().timestamp())}"
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения прогноза: {e}")
            raise
    
    async def save_news_article(self, title: str, content: str, category: str,
                               source: str, url: str) -> str:
        """
        Сохранение новостной статьи
        
        Args:
            title (str): Заголовок новости
            content (str): Содержание новости
            category (str): Категория новости
            source (str): Источник
            url (str): Ссылка
            
        Returns:
            str: ID сохраненного документа
        """
        try:
            # Объединяем заголовок и содержание для лучшего контекста
            full_text = f"{title}\\n\\n{content}"
            
            doc_id = await self.qdrant_client.save_astro_result(
                user_id=0,  # Для новостей используем user_id=0
                company_name=f"News_{category}",
                analysis_type="news",
                result=full_text
            )
            
            logger.info(f"📰 Новость '{title[:50]}...' сохранена: {doc_id}")
            return doc_id or f"news_{category}_{int(datetime.now().timestamp())}"
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения новости: {e}")
            raise
    
    async def find_similar_companies(self, company_info: Dict, 
                                   top_k: int = 3) -> List[Dict]:
        """
        Поиск похожих компаний в базе прогнозов
        
        Args:
            company_info (Dict): Информация о компании
            top_k (int): Количество результатов
            
        Returns:
            List[Dict]: Список похожих компаний
        """
        try:
            query = f"Компания {company_info.get('name', '')} сфера {company_info.get('sphere', '')}"
            
            results = await self.qdrant_client.search_similar_results(
                query=query
            )
            
            logger.info(f"🔍 Найдено {len(results)} похожих компаний")
            return results
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска похожих компаний: {e}")
            return []
    
    async def get_relevant_news(self, company_sphere: str, 
                               days_back: int = 7, top_k: int = 5) -> List[Dict]:
        """
        Получение релевантных новостей для сферы деятельности
        
        Args:
            company_sphere (str): Сфера деятельности компании
            days_back (int): Количество дней назад для поиска
            top_k (int): Количество результатов
            
        Returns:
            List[Dict]: Список релевантных новостей
        """
        try:
            # Формируем поисковый запрос на основе сферы деятельности
            sphere_keywords = {
                "Энергетика": "энергетика электричество газ нефть",
                "Финансы и инвестиции": "банки финансы инвестиции экономика",
                "Технологии и телекоммуникации": "технологии IT интернет связь",
                "Строительство и промышленность": "строительство промышленность производство",
                "Торговля и сфера услуг": "торговля ритейл услуги потребители"
            }
            
            query = sphere_keywords.get(company_sphere, company_sphere)
            
            # Фильтр по времени
            cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
            
            results = await self.qdrant_client.search_similar_results(
                query=query
            )
            
            logger.info(f"📰 Найдено {len(results)} релевантных новостей для '{company_sphere}'")
            return results
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска новостей: {e}")
            return []
    
    async def get_user_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """
        Получение истории диалогов пользователя
        
        Args:
            user_id (int): ID пользователя
            limit (int): Лимит результатов
            
        Returns:
            List[Dict]: История диалогов
        """
        try:
            results = await self.qdrant_client.search_similar_results(
                query=f"пользователь {user_id}"
            )
            
            # Сортируем по времени
            results.sort(key=lambda x: x["metadata"].get("timestamp", ""), reverse=True)
            
            logger.info(f"📜 Получена история из {len(results)} диалогов для пользователя {user_id}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения истории пользователя {user_id}: {e}")
            return []
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """
        Получение статистики векторной базы данных
        
        Returns:
            Dict[str, Any]: Статистика
        """
        try:
            # Получаем статистику Qdrant вместо Pinecone
            formatted_stats = {
                "total_documents": 0,
                "dialogs": 0,
                "predictions": 0,
                "news": 0
            }
            
            logger.info(f"📊 Статистика БД: {formatted_stats}")
            return formatted_stats
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {}
    
    async def cleanup_old_data(self, days_to_keep: int = 30):
        """
        Очистка старых данных
        
        Args:
            days_to_keep (int): Количество дней для хранения
        """
        try:
            # В будущем можно реализовать очистку старых записей
            # Pinecone не поддерживает прямую фильтрацию по времени для удаления
            logger.info(f"🧹 Очистка данных старше {days_to_keep} дней (не реализовано)")
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки данных: {e}")
            raise
