"""
Анализатор новостей для астрологических прогнозов
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import schedule
import threading
import time

from .newsdata_client import NewsDataClient
from embedding.embedding_manager import EmbeddingManager
from utils.logger import setup_logger

logger = setup_logger()


class NewsAnalyzer:
    """Анализатор и планировщик новостей"""
    
    def __init__(self):
        """Инициализация анализатора"""
        self.news_client = NewsDataClient()
        self.embedding_manager = EmbeddingManager()
        self.is_running = False
        self.scheduler_thread = None
        
        logger.info("📊 NewsAnalyzer инициализирован")
    
    async def analyze_news_for_company(self, company_sphere: str, 
                                     days_back: int = 7) -> Dict[str, Any]:
        """
        Анализ новостей для конкретной компании
        
        Args:
            company_sphere (str): Сфера деятельности компании
            days_back (int): Количество дней назад для анализа
            
        Returns:
            Dict[str, Any]: Анализ новостей
        """
        try:
            # Получаем новости по сфере деятельности
            sphere_news = await self.news_client.get_news_by_sphere(
                company_sphere, limit=15
            )
            
            # Получаем общие экономические новости
            all_news = await self.news_client.get_all_business_news(
                limit_per_category=5
            )
            
            # Безопасная обработка новостей
            sphere_news = sphere_news or []
            all_news = all_news or {}
            
            # Объединяем все новости для анализа настроений
            all_news_list = sum(all_news.values(), []) if all_news else []
            combined_news = sphere_news + all_news_list
            
            # Анализируем влияние на компанию
            analysis = {
                'sphere_specific': self._analyze_sphere_impact(sphere_news, company_sphere),
                'general_economic': self._analyze_general_impact(all_news),
                'market_sentiment': self._calculate_market_sentiment(combined_news),
                'key_trends': self._extract_key_trends(sphere_news),
                'risks_and_opportunities': self._identify_risks_opportunities(
                    sphere_news, company_sphere
                ),
                'summary': self._create_news_summary(sphere_news, all_news)
            }
            
            logger.info(f"📈 Анализ новостей для сферы '{company_sphere}' завершен")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа новостей для компании: {e}")
            return self._get_empty_analysis()
    
    async def get_daily_news_digest(self) -> str:
        """
        Получение ежедневной сводки новостей
        
        Returns:
            str: Текстовая сводка новостей
        """
        try:
            # Получаем свежие новости
            summary = await self.news_client.get_fresh_news_summary(hours_back=24)
            
            # Получаем детальные новости для анализа
            all_news = await self.news_client.get_all_business_news(
                limit_per_category=3
            )
            
            # Формируем расширенную сводку
            digest_parts = [
                "🌅 **ЕЖЕДНЕВНАЯ СВОДКА НОВОСТЕЙ**",
                f"📅 {datetime.now().strftime('%d.%m.%Y')}",
                "",
                summary
            ]
            
            # Добавляем ключевые тренды
            trends = self._extract_daily_trends(all_news)
            if trends:
                digest_parts.extend(["", "📊 **КЛЮЧЕВЫЕ ТРЕНДЫ:**"] + trends)
            
            digest = '\n'.join(digest_parts)
            logger.info("📰 Ежедневная сводка новостей сформирована")
            
            return digest
            
        except Exception as e:
            logger.error(f"❌ Ошибка формирования ежедневной сводки: {e}")
            return "Ошибка при получении ежедневной сводки новостей."
    
    async def start_daily_parsing(self):
        """Запуск ежедневного парсинга новостей"""
        try:
            if self.is_running:
                logger.warning("⚠️ Парсер новостей уже запущен")
                return
            
            # Настраиваем расписание
            schedule.clear()  # Очищаем предыдущие задачи
            
            # Парсинг в 07:00 утра
            schedule.every().day.at("07:00").do(self._scheduled_news_parsing)
            
            # Запускаем планировщик в отдельном потоке
            self.is_running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.scheduler_thread.start()
            
            logger.info("⏰ Ежедневный парсер новостей запущен (07:00)")
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска ежедневного парсера: {e}")
    
    def stop_daily_parsing(self):
        """Остановка ежедневного парсинга"""
        try:
            self.is_running = False
            schedule.clear()
            
            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=5)
            
            logger.info("⏹️ Ежедневный парсер новостей остановлен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки парсера: {e}")
    
    def _run_scheduler(self):
        """Запуск планировщика в отдельном потоке"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Проверяем каждую минуту
            except Exception as e:
                logger.error(f"❌ Ошибка в планировщике: {e}")
                time.sleep(300)  # Ждем 5 минут при ошибке
    
    def _scheduled_news_parsing(self):
        """Запланированный парсинг новостей"""
        try:
            logger.info("🕐 Начат запланированный парсинг новостей...")
            
            # Создаем новый event loop для потока
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Выполняем парсинг
                loop.run_until_complete(self._parse_and_save_news())
            finally:
                loop.close()
            
            logger.info("✅ Запланированный парсинг новостей завершен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка запланированного парсинга: {e}")
    
    async def _parse_and_save_news(self):
        """Парсинг и сохранение новостей в векторную БД"""
        try:
            # Получаем все типы новостей
            all_news = await self.news_client.get_all_business_news(
                limit_per_category=10
            )
            
            saved_count = 0
            
            # Сохраняем каждую новость в векторную БД
            for category, articles in all_news.items():
                for article in articles:
                    try:
                        await self.embedding_manager.save_news_article(
                            title=article['title'],
                            content=article.get('description', ''),
                            category=category,
                            source=article['source'],
                            url=article['url']
                        )
                        saved_count += 1
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка сохранения новости: {e}")
                        continue
            
            logger.info(f"💾 Сохранено {saved_count} новостей в векторную БД")
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга и сохранения новостей: {e}")
    
    def _analyze_sphere_impact(self, news: List[Dict], sphere: str) -> Dict[str, Any]:
        """Анализ влияния новостей на конкретную сферу"""
        if not news:
            return {"impact_level": "low", "relevant_news": []}
        
        # Простой анализ на основе ключевых слов
        positive_keywords = ["рост", "увеличение", "развитие", "инвестиции", "прибыль"]
        negative_keywords = ["падение", "снижение", "кризис", "убытки", "проблемы"]
        
        relevant_news = []
        impact_score = 0
        
        for article in news[:5]:  # Берем топ-5 новостей
            text = (article.get('title', '') + ' ' + 
                   article.get('description', '')).lower()
            
            positive_count = sum(1 for word in positive_keywords if word in text)
            negative_count = sum(1 for word in negative_keywords if word in text)
            
            article_impact = positive_count - negative_count
            impact_score += article_impact
            
            relevant_news.append({
                "title": article.get('title', ''),
                "impact": "positive" if article_impact > 0 else 
                         "negative" if article_impact < 0 else "neutral",
                "url": article.get('url', '')
            })
        
        impact_level = ("high" if abs(impact_score) >= 3 else 
                       "medium" if abs(impact_score) >= 1 else "low")
        
        return {
            "impact_level": impact_level,
            "impact_score": impact_score,
            "relevant_news": relevant_news
        }
    
    def _analyze_general_impact(self, all_news: Dict[str, List]) -> Dict[str, str]:
        """Анализ общего экономического воздействия"""
        analysis = {}
        
        for category, articles in all_news.items():
            if articles:
                # Берем заголовки первых 3 новостей
                headlines = [article.get('title', '') for article in articles[:3]]
                summary = "; ".join(headlines)[:200] + "..."
                analysis[category] = summary
            else:
                analysis[category] = "Новости не найдены"
        
        return analysis
    
    def _calculate_market_sentiment(self, all_articles: List[Dict]) -> str:
        """Расчет рыночных настроений"""
        if not all_articles:
            return "neutral"
        
        positive_words = ["рост", "прибыль", "успех", "развитие", "инвестиции"]
        negative_words = ["падение", "кризис", "убытки", "проблемы", "снижение"]
        
        total_sentiment = 0
        
        for article in all_articles:
            text = (article.get('title', '') + ' ' + 
                   article.get('description', '')).lower()
            
            positive_score = sum(1 for word in positive_words if word in text)
            negative_score = sum(1 for word in negative_words if word in text)
            
            total_sentiment += positive_score - negative_score
        
        if total_sentiment > 2:
            return "positive"
        elif total_sentiment < -2:
            return "negative"
        else:
            return "neutral"
    
    def _extract_key_trends(self, news: List[Dict]) -> List[str]:
        """Извлечение ключевых трендов"""
        if not news:
            return []
        
        # Простое извлечение трендов на основе частых слов в заголовках
        trends = []
        
        for article in news[:3]:
            title = article.get('title', '')
            if len(title) > 20:  # Достаточно информативный заголовок
                trends.append(title)
        
        return trends
    
    def _identify_risks_opportunities(self, news: List[Dict], sphere: str) -> Dict[str, List[str]]:
        """Идентификация рисков и возможностей"""
        risks = []
        opportunities = []
        
        for article in news[:5]:
            text = (article.get('title', '') + ' ' + 
                   article.get('description', '')).lower()
            title = article.get('title', '')
            
            # Простая логика определения рисков и возможностей
            risk_indicators = ["кризис", "падение", "проблемы", "санкции", "дефицит"]
            opportunity_indicators = ["рост", "инвестиции", "развитие", "новый", "расширение"]
            
            if any(indicator in text for indicator in risk_indicators):
                risks.append(title)
            elif any(indicator in text for indicator in opportunity_indicators):
                opportunities.append(title)
        
        return {
            "risks": risks[:3],  # Топ-3 риска
            "opportunities": opportunities[:3]  # Топ-3 возможности
        }
    
    def _create_news_summary(self, sphere_news: List[Dict], 
                           all_news: Dict[str, List]) -> str:
        """Создание краткой сводки новостей"""
        summary_parts = []
        
        # Добавляем новости по сфере
        if sphere_news:
            summary_parts.append("Релевантные новости по сфере деятельности:")
            for article in sphere_news[:2]:
                summary_parts.append(f"• {article.get('title', '')}")
        
        # Добавляем общие экономические новости
        if all_news:
            summary_parts.append("\nОбщие экономические новости:")
            for category, articles in all_news.items():
                if articles:
                    category_name = {
                        'politics': 'Политика',
                        'business': 'Экономика',
                        'stock_market': 'Фондовый рынок'
                    }.get(category, category)
                    
                    top_article = articles[0]
                    summary_parts.append(f"• {category_name}: {top_article.get('title', '')}")
        
        return '\n'.join(summary_parts) if summary_parts else "Актуальные новости не найдены."
    
    def _extract_daily_trends(self, all_news: Dict[str, List]) -> List[str]:
        """Извлечение ежедневных трендов"""
        trends = []
        
        for category, articles in all_news.items():
            if articles:
                top_article = articles[0]
                title = top_article.get('title', '')
                if title:
                    trends.append(f"• {title}")
        
        return trends
    
    def _get_empty_analysis(self) -> Dict[str, Any]:
        """Получение пустого анализа при ошибке"""
        return {
            'sphere_specific': {"impact_level": "low", "relevant_news": []},
            'general_economic': {},
            'market_sentiment': "neutral",
            'key_trends': [],
            'risks_and_opportunities': {"risks": [], "opportunities": []},
            'summary': "Анализ новостей временно недоступен."
        }


