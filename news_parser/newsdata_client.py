"""
Клиент для работы с NewsData.io API
"""

import requests
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json

from utils.config import load_config
from utils.logger import setup_logger

logger = setup_logger()


class NewsDataClient:
    """Клиент для работс NewsData.io API"""
    
    def __init__(self):
        """Инициализация клиента"""
        self.config = load_config()
        self.api_key = self.config.newsdata.api_key
        self.base_url = self.config.newsdata.base_url
        self.language = self.config.newsdata.language
        self.country = self.config.newsdata.country
        
        # Проверяем наличие API ключа
        if not self.api_key:
            logger.error("❌ Отсутствует API ключ NewsData.io")
            raise ValueError("NewsData.io API key is required")
        
        logger.info("📰 NewsData.io клиент инициализирован")
    
    async def get_politics_news(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получение новостей по политике
        
        Args:
            limit (int): Количество новостей
            
        Returns:
            List[Dict]: Список новостей
        """
        try:
            params = {
                'apikey': self.api_key,
                'category': 'politics',
                'language': self.language,
                'country': self.country,
                'size': min(limit, 50)  # Максимум 50 на запрос
            }
            
            response = await self._make_request(params)
            
            if response and response.get('status') == 'success':
                articles = response.get('results', [])
                logger.info(f"📰 Получено {len(articles)} новостей по политике")
                return self._format_articles(articles, 'politics')
            else:
                logger.warning(f"⚠️ Не удалось получить новости по политике: {response}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения новостей по политике: {e}")
            return []
    
    async def get_business_news(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получение новостей по экономике
        
        Args:
            limit (int): Количество новостей
            
        Returns:
            List[Dict]: Список новостей
        """
        try:
            params = {
                'apikey': self.api_key,
                'category': 'business',
                'language': self.language,
                'country': self.country,
                'size': min(limit, 50)
            }
            
            response = await self._make_request(params)
            
            if response and response.get('status') == 'success':
                articles = response.get('results', [])
                logger.info(f"💼 Получено {len(articles)} новостей по экономике")
                return self._format_articles(articles, 'business')
            else:
                logger.warning(f"⚠️ Не удалось получить новости по экономике: {response}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения новостей по экономике: {e}")
            return []
    
    async def get_stock_market_news(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получение новостей по фондовому рынку
        
        Args:
            limit (int): Количество новостей
            
        Returns:
            List[Dict]: Список новостей
        """
        try:
            # Ключевые слова для поиска новостей по фондовому рынку
            stock_keywords = "акции OR биржа OR инвестиции OR фондовый OR ценные OR IPO"
            
            params = {
                'apikey': self.api_key,
                'q': stock_keywords,
                'category': 'business',
                'language': self.language,
                'country': self.country,
                'size': min(limit, 50)
            }
            
            response = await self._make_request(params)
            
            if response and response.get('status') == 'success':
                articles = response.get('results', [])
                logger.info(f"📈 Получено {len(articles)} новостей по фондовому рынку")
                return self._format_articles(articles, 'stock_market')
            else:
                logger.warning(f"⚠️ Не удалось получить новости по фондовому рынку: {response}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения новостей по фондовому рынку: {e}")
            return []
    
    async def get_news_by_sphere(self, business_sphere: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получение новостей по конкретной сфере деятельности
        
        Args:
            business_sphere (str): Сфера деятельности
            limit (int): Количество новостей
            
        Returns:
            List[Dict]: Список новостей
        """
        try:
            # Маппинг сфер деятельности на ключевые слова
            sphere_keywords = {
                "Энергетика": "энергетика OR электричество OR газ OR нефть OR энергия",
                "Финансы и инвестиции": "банки OR финансы OR инвестиции OR кредиты OR страхование",
                "Технологии и телекоммуникации": "технологии OR IT OR интернет OR связь OR цифровизация",
                "Строительство и промышленность": "строительство OR промышленность OR производство OR заводы",
                "Торговля и сфера услуг": "торговля OR ритейл OR услуги OR потребители OR магазины",
                "Государственный сектор": "государство OR госсектор OR бюджет OR чиновники",
                "Медицина": "медицина OR здравоохранение OR больницы OR фармацевтика",
                "Образование": "образование OR школы OR университеты OR обучение"
            }
            
            keywords = sphere_keywords.get(business_sphere, business_sphere)
            
            params = {
                'apikey': self.api_key,
                'q': keywords,
                'language': self.language,
                'country': self.country,
                'size': min(limit, 50)
            }
            
            response = await self._make_request(params)
            
            if response and response.get('status') == 'success':
                articles = response.get('results', [])
                logger.info(f"🎯 Получено {len(articles)} новостей по сфере '{business_sphere}'")
                return self._format_articles(articles, f'sphere_{business_sphere}')
            else:
                logger.warning(f"⚠️ Не удалось получить новости по сфере '{business_sphere}': {response}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения новостей по сфере '{business_sphere}': {e}")
            return []
    
    async def get_all_business_news(self, limit_per_category: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """
        Получение всех типов бизнес-новостей
        
        Args:
            limit_per_category (int): Лимит новостей на категорию
            
        Returns:
            Dict: Словарь с новостями по категориям
        """
        try:
            # Получаем новости параллельно
            tasks = [
                self.get_politics_news(limit_per_category),
                self.get_business_news(limit_per_category),
                self.get_stock_market_news(limit_per_category)
            ]
            
            politics_news, business_news, stock_news = await asyncio.gather(*tasks)
            
            result = {
                'politics': politics_news,
                'business': business_news,
                'stock_market': stock_news
            }
            
            total_count = sum(len(news) for news in result.values())
            logger.info(f"📰 Получено всего {total_count} новостей по всем категориям")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения всех новостей: {e}")
            return {'politics': [], 'business': [], 'stock_market': []}
    
    async def _make_request(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Выполнение HTTP запроса к API
        
        Args:
            params (Dict): Параметры запроса
            
        Returns:
            Optional[Dict]: Ответ API или None
        """
        try:
            # Выполняем запрос в отдельном потоке для избежания блокировки
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.get(self.base_url, params=params, timeout=30)
            )
            
            response.raise_for_status()
            
            # Проверяем Content-Type
            content_type = response.headers.get('Content-Type', '')
            if 'application/json' not in content_type:
                logger.warning(f"⚠️ Неожиданный Content-Type: {content_type}")
                return None
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ HTTP ошибка при запросе к NewsData.io: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"❌ Ошибка декодирования JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка при запросе: {e}")
            return None
    
    def _format_articles(self, articles: List[Dict], category: str) -> List[Dict[str, Any]]:
        """
        Форматирование статей в единый формат
        
        Args:
            articles (List[Dict]): Исходные статьи
            category (str): Категория новостей
            
        Returns:
            List[Dict]: Отформатированные статьи
        """
        formatted_articles = []
        
        for article in articles:
            try:
                formatted_article = {
                    'title': article.get('title', 'Без заголовка'),
                    'description': article.get('description', ''),
                    'content': article.get('content', ''),
                    'url': article.get('link', ''),
                    'source': article.get('source_id', 'Неизвестно'),
                    'published_date': self._parse_date(article.get('pubDate')),
                    'category': category,
                    'keywords': article.get('keywords', []),
                    'country': article.get('country', []),
                    'language': article.get('language', self.language)
                }
                
                # Объединяем заголовок и описание для полного текста
                full_text = f"{formatted_article['title']}. {formatted_article['description']}"
                if formatted_article['content']:
                    full_text += f" {formatted_article['content']}"
                
                formatted_article['full_text'] = full_text
                formatted_articles.append(formatted_article)
                
            except Exception as e:
                logger.warning(f"⚠️ Ошибка форматирования статьи: {e}")
                continue
        
        return formatted_articles
    
    def _parse_date(self, date_string: Optional[str]) -> Optional[datetime]:
        """
        Парсинг даты из строки
        
        Args:
            date_string (Optional[str]): Строка с датой
            
        Returns:
            Optional[datetime]: Объект datetime или None
        """
        if not date_string:
            return None
        
        try:
            # NewsData.io возвращает даты в формате ISO
            return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            try:
                # Альтернативный формат
                return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                logger.warning(f"⚠️ Не удалось распарсить дату: {date_string}")
                return None
    
    async def get_fresh_news_summary(self, hours_back: int = 24) -> str:
        """
        Получение краткой сводки свежих новостей
        
        Args:
            hours_back (int): Количество часов назад
            
        Returns:
            str: Краткая сводка новостей
        """
        try:
            # Получаем все новости
            all_news = await self.get_all_business_news(limit_per_category=3)
            
            summary_parts = []
            
            for category, articles in all_news.items():
                if articles:
                    category_name = {
                        'politics': 'Политика',
                        'business': 'Экономика', 
                        'stock_market': 'Фондовый рынок'
                    }.get(category, category)
                    
                    summary_parts.append(f"**{category_name}:**")
                    
                    for article in articles[:2]:  # Берем только первые 2 новости
                        summary_parts.append(f"• {article['title']}")
            
            if summary_parts:
                summary = '\n'.join(summary_parts)
                logger.info("📋 Сводка новостей сформирована")
                return summary
            else:
                return "Актуальные новости не найдены."
                
        except Exception as e:
            logger.error(f"❌ Ошибка формирования сводки новостей: {e}")
            return "Ошибка при получении сводки новостей."




