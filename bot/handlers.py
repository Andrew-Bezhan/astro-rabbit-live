"""
Обработчики команд и сообщений Telegram бота
"""

import asyncio
from typing import Dict, Any
from datetime import datetime
from telegram import Update, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackContext

from .keyboards import BotKeyboards
from .states import BotState, StateManager
from ai_astrologist.astro_agent import AstroAgent
from ai_astrologist.numerology import NumerologyCalculator
from news_parser.news_analyzer import NewsAnalyzer
from embedding.embedding_manager import EmbeddingManager
from utils.helpers import validate_date, clean_company_name, is_valid_russian_name
from utils.logger import setup_logger

logger = setup_logger()


class BotHandlers:
    """Класс обработчиков команд бота"""
    
    def __init__(self):
        """Инициализация обработчиков"""
        self.state_manager = StateManager()
        self.keyboards = BotKeyboards()
        
        # Инициализация ОБЯЗАТЕЛЬНЫХ сервисов согласно ТЗ
        try:
            # Всегда инициализируем основные сервисы
            self.astro_agent = AstroAgent()
            self.numerology = NumerologyCalculator()
            self.news_analyzer = NewsAnalyzer()
            
            # Инициализируем валидатор
            try:
                from validation_agent.validator import ValidationAgent
                self.validator = ValidationAgent()
            except Exception as e:
                logger.warning(f"⚠️ Валидатор недоступен: {e}")
                self.validator = None
            
            # Embedding manager опционально
            try:
                self.embedding_manager = EmbeddingManager()
            except Exception as e:
                logger.warning(f"⚠️ Embedding manager недоступен: {e}")
                self.embedding_manager = None
                
            # Qdrant ОБЯЗАТЕЛЬНЫЙ согласно ТЗ
            try:
                from embedding.qdrant_client import QdrantClient
                self.qdrant_client = QdrantClient()
                logger.info("✅ Qdrant инициализирован")
            except Exception as e:
                logger.warning(f"⚠️ Qdrant недоступен: {e}")
                self.qdrant_client = None
                
            logger.info("✅ Все обязательные сервисы Астробота инициализированы")
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка инициализации: {e}")
            # Инициализируем минимальные заглушки
            self.astro_agent = AstroAgent() if not hasattr(self, 'astro_agent') else self.astro_agent
            self.numerology = NumerologyCalculator()
            self.news_analyzer = NewsAnalyzer() if not hasattr(self, 'news_analyzer') else self.news_analyzer
            self.embedding_manager = None
            self.qdrant_client = None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        if not update.effective_user or not update.message:
            return
            
        user = update.effective_user
        
        welcome_text = f"""
🔮 Добро пожаловать в Астробот, {user.first_name or 'Пользователь'}!

Я — AstroRabbit, ваш персональный эксперт по корпоративной астрологии и нумерологии. 

✨ Что я умею:
• 🔮 Определять знак зодиака компании
• 📈 Составлять бизнес-прогнозы
• 🤝 Анализировать совместимость
• 📅 Давать ежедневные прогнозы
• 🏢 Сохранять профили компаний

🌟 Особенности:
- Прогнозы для компаний, а не для людей
- AI-интерпретация астрологических данных
- Учет экономических трендов
- Практические бизнес-рекомендации

Выберите действие в меню ниже! 👇
        """
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=self.keyboards.get_main_menu(),
            parse_mode=None
        )
        
        # Создаем пользователя в БД если его нет
        try:
            from database.connection import get_session
            from database.crud import UserCRUD
            
            with get_session() as session:
                existing_user = UserCRUD.get_user_by_telegram_id(session, user.id)
                if not existing_user:
                    # Создаем нового пользователя
                    UserCRUD.create_user(
                        session=session,
                        telegram_id=user.id,
                        username=user.username,
                        first_name=user.first_name,
                        last_name=user.last_name
                    )
                    logger.info(f"👤 Создан новый пользователь в БД: {user.id}")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка создания пользователя в БД: {e}")
        
        # Сбрасываем состояние пользователя
        self.state_manager.reset_user(user.id)
        
        logger.info(f"👋 Пользователь {user.id} ({user.first_name or 'Анонимный'}) запустил бота")
    
    async def _check_company_required_and_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE, analysis_type: str):
        """Проверка наличия компаний перед запуском анализа"""
        if not update.effective_user or not update.message:
            return
            
        user_id = update.effective_user.id
        
        # Проверяем наличие сохраненных компаний
        try:
            from database.crud import CompanyCRUD
            from database.connection import get_session
            
            with get_session() as session:
                user_companies = CompanyCRUD.get_companies_by_user(session, user_id)
                
                if not user_companies:
                    # Нет компаний - направляем к созданию
                    await update.message.reply_text(
                        """🏢 ВЫБЕРИТЕ КОМПАНИЮ ИЗ ВАШЕГО СПИСКА
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 У вас пока нет сохраненных компаний.

💡 Для получения прогноза необходимо:
1️⃣ Добавить компанию в "Мои компании"
2️⃣ Заполнить основные данные
3️⃣ Выбрать компанию для анализа

🚀 Нажмите кнопку ниже для добавления компании:""",
                        parse_mode=None,
                        reply_markup=self.keyboards.get_companies_required_menu()
                    )
                    return
                else:
                    # Есть компании - запускаем соответствующий анализ
                    if analysis_type == "zodiac":
                        await self._start_zodiac_analysis(update, context)
                    elif analysis_type == "forecast":
                        await self._start_business_forecast(update, context)
                    elif analysis_type == "compatibility":
                        await self._start_compatibility_check(update, context)
                        
        except Exception as e:
            logger.warning(f"⚠️ Ошибка проверки компаний: {e}")
            # При ошибке направляем к созданию компании
            await update.message.reply_text(
                """🏢 ВЫБЕРИТЕ КОМПАНИЮ ИЗ ВАШЕГО СПИСКА

📋 Возникла ошибка при загрузке списка компаний.

💡 Нажмите кнопку ниже для работы с компаниями:""",
                parse_mode=None,
                reply_markup=self.keyboards.get_companies_required_menu()
            )
    
    # Команды для бокового меню
    async def zodiac_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /zodiac - анализ знака зодиака"""
        await self._check_company_required_and_start(update, context, "zodiac")
    
    async def forecast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /forecast - бизнес-прогноз"""
        await self._check_company_required_and_start(update, context, "forecast")
    
    async def compatibility_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /compatibility - проверка совместимости"""
        await self._check_company_required_and_start(update, context, "compatibility")
    
    async def companies_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /companies - мои компании"""
        await self._show_companies_menu(update, context)
    
    async def cabinet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /cabinet - личный кабинет"""
        await self._show_personal_cabinet(update, context)
    
    async def tariffs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /tariffs - тарифы"""
        await self._show_tariffs_menu(update, context)
    
    async def daily_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /daily - ежедневные прогнозы"""
        await self._show_daily_forecast_menu(update, context)
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /settings - настройки"""
        await self._show_settings_menu(update, context)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        if not update.message:
            return
            
        help_text = """
📚 СПРАВКА ПО АСТРОБОТУ

🔮 Узнать знак зодиака Компании
Определение знака зодиака по дате регистрации и базовый анализ характеристик компании.

📈 Бизнес-прогноз для Компании  
Полный астрологический анализ с учетом:
- Данных компании (название, дата, место регистрации)
- Информации о собственнике и руководителе
- Текущих экономических трендов
- Нумерологического анализа

🤝 Проверить совместимость
Анализ совместимости компании с:
- Сотрудниками
- Клиентами  
- Партнерами

📅 Ежедневные прогнозы
Автоматические утренние прогнозы (в 8:00) на основе:
- Профиля сохраненной компании
- Актуальных астрологических влияний
- Свежих экономических новостей

🏢 Мои компании
Управление сохраненными профилями компаний.

⚙️ Дополнительные возможности:
- Детальные анализы (финансы, партнерство, риски)
- Быстрые прогнозы на 3 месяца
- Нумерологический анализ имен
- Сохранение истории прогнозов

❓ Нужна помощь? Используйте /support
        """
        
        await update.message.reply_text(
            help_text,
            parse_mode=None
        )
    
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Основной обработчик текстовых сообщений"""
        if not update.effective_user or not update.message or not update.message.text:
            return
            
        user_id = update.effective_user.id
        message_text = update.message.text
        current_state = self.state_manager.get_state(user_id)
        
        logger.info(f"💬 Пользователь {user_id}: '{message_text}' (состояние: {current_state.name})")
        
        # Проверяем, не является ли сообщение командой
        if message_text.startswith('/'):
            # Если это команда, перенаправляем к соответствующему обработчику
            if message_text == '/companies':
                await self.companies_command(update, context)
                return
            elif message_text == '/start':
                await self.start_command(update, context)
                return
            elif message_text == '/help':
                await self.help_command(update, context)
                return
            elif message_text == '/zodiac':
                await self.zodiac_command(update, context)
                return
            elif message_text == '/forecast':
                await self.forecast_command(update, context)
                return
            elif message_text == '/compatibility':
                await self.compatibility_command(update, context)
                return
            elif message_text == '/cabinet':
                await self.cabinet_command(update, context)
                return
            elif message_text == '/tariffs':
                await self.tariffs_command(update, context)
                return
            elif message_text == '/daily':
                await self.daily_command(update, context)
                return
            elif message_text == '/settings':
                await self.settings_command(update, context)
                return
            else:
                # Неизвестная команда
                await update.message.reply_text(
                    "🤔 Неизвестная команда. Возвращаюсь в главное меню.",
                    reply_markup=self.keyboards.get_main_menu()
                )
                self.state_manager.reset_user(user_id)
                return
        
        # Обработка основных команд меню
        if current_state == BotState.IDLE:
            await self._handle_main_menu(update, context, message_text)
        
        # Обработка состояний сбора данных
        elif current_state == BotState.ZODIAC_COMPANY_NAME:
            await self._handle_zodiac_company_name(update, context, message_text)
        elif current_state == BotState.ZODIAC_REG_DATE:
            await self._handle_zodiac_reg_date(update, context, message_text)
        elif current_state == BotState.ZODIAC_REG_PLACE:
            result = self._handle_zodiac_reg_place(update, context, message_text)
            if result is not None:
                await result
        
        elif current_state == BotState.BUSINESS_COMPANY_NAME:
            await self._handle_business_company_name(update, context, message_text)
        elif current_state == BotState.BUSINESS_REG_DATE:
            await self._handle_business_reg_date(update, context, message_text)
        elif current_state == BotState.BUSINESS_REG_PLACE:
            await self._handle_business_reg_place(update, context, message_text)
        elif current_state == BotState.BUSINESS_OWNER_NAME:
            await self._handle_business_owner_name(update, context, message_text)
        elif current_state == BotState.BUSINESS_OWNER_BIRTH:
            await self._handle_business_owner_birth(update, context, message_text)
        elif current_state == BotState.BUSINESS_DIRECTOR_NAME:
            await self._handle_business_director_name(update, context, message_text)
        elif current_state == BotState.BUSINESS_DIRECTOR_BIRTH:
            await self._handle_business_director_birth(update, context, message_text)
        
        # Обработка состояний создания профиля компании
        elif current_state == BotState.PROFILE_COMPANY_NAME:
            await self._handle_profile_company_name(update, context, message_text)
        elif current_state == BotState.PROFILE_REG_DATE:
            await self._handle_profile_reg_date(update, context, message_text)
        elif current_state == BotState.PROFILE_REG_PLACE:
            await self._handle_profile_reg_place(update, context, message_text)
        elif current_state == BotState.PROFILE_OWNER_NAME:
            await self._handle_profile_owner_name(update, context, message_text)
        elif current_state == BotState.PROFILE_OWNER_BIRTH:
            await self._handle_profile_owner_birth(update, context, message_text)
        elif current_state == BotState.PROFILE_DIRECTOR_NAME:
            await self._handle_profile_director_name(update, context, message_text)
        elif current_state == BotState.PROFILE_DIRECTOR_BIRTH:
            await self._handle_profile_director_birth(update, context, message_text)
        
        elif current_state == BotState.COMPAT_OBJECT_NAME:
            # await self._handle_compat_object_name(update, context, message_text)
            await self._handle_main_menu(update, context, "🔮 Узнать знак зодиака Компании")
        elif current_state == BotState.COMPAT_OBJECT_BIRTH:
            # await self._handle_compat_object_birth(update, context, message_text)
            await self._handle_main_menu(update, context, "🔮 Узнать знак зодиака Компании")
        elif current_state == BotState.COMPAT_OBJECT_PLACE:
            # await self._handle_compat_object_place(update, context, message_text)
            await self._handle_main_menu(update, context, "🔮 Узнать знак зодиака Компании")
        
        else:
            if update.message:
                await update.message.reply_text(
                    "🤔 Не понимаю. Используйте меню или /help для справки.",
                    reply_markup=self.keyboards.get_main_menu()
                )
            self.state_manager.reset_user(user_id)
    
    async def _handle_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка команд главного меню"""
        if not update.effective_user:
            return
        user_id = update.effective_user.id
        
        if text == "🔮 Узнать знак зодиака Компании":
            await self._check_company_required_and_start(update, context, "zodiac")
        
        elif text == "📈 Бизнес-прогноз для Компании":
            await self._check_company_required_and_start(update, context, "forecast")
        
        elif text == "🤝 Проверить совместимость":
            await self._check_company_required_and_start(update, context, "compatibility")
        
        elif text == "📅 Ежедневные прогнозы":
            await self._show_daily_forecast_menu(update, context)
        
        elif text == "🏢 Мои компании":
            await self._show_companies_menu(update, context)
        
        elif text == "ℹ️ Справка":
            await self.help_command(update, context)
        
        elif text == "⚙️ Настройки":
            await self._show_settings_menu(update, context)
        
        elif text == "👤 Личный кабинет":
            await self._show_personal_cabinet(update, context)
        
        elif text == "💳 Тарифы":
            await self._show_tariffs_menu(update, context)
        
        elif text == "🔙 Главное меню":
            await self.start_command(update, context)
        
        else:
            if update.message:
                await update.message.reply_text(
                    "🤔 Пожалуйста, используйте кнопки меню для навигации.",
                    reply_markup=self.keyboards.get_main_menu()
                )
    
    async def _start_zodiac_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запуск анализа знака зодиака"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        
        # Сначала проверяем, есть ли сохраненные компании
        try:
            from database.crud import CompanyCRUD
            from database.connection import get_session
            
            with get_session() as session:
                user_companies = CompanyCRUD.get_companies_by_user(session, user_id)
                
                if user_companies:
                    # Показываем список компаний для выбора
                    companies_text = "🔮 ВЫБЕРИТЕ КОМПАНИЮ ДЛЯ АНАЛИЗА ЗНАКА ЗОДИАКА\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    
                    for i, comp in enumerate(user_companies, 1):
                        reg_date_str = 'Не указана'
                        if hasattr(comp, 'registration_date') and comp.registration_date is not None:
                            try:
                                reg_date_str = comp.registration_date.strftime('%d.%m.%Y')
                            except:
                                reg_date_str = 'Не указана'
                        
                        companies_text += f"""📊 {i}. {comp.name}
📅 Дата регистрации: {reg_date_str}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"""
                    
                    companies_text += "\n💡 Выберите компанию из списка выше или создайте новый профиль."
                    
                    await update.message.reply_text(
                        companies_text,
                        parse_mode=None,
                        reply_markup=self.keyboards.get_companies_management_menu(user_companies)
                    )
                    
                    # Устанавливаем состояние выбора компании
                    self.state_manager.set_state(user_id, BotState.SELECTING_COMPANY_FOR_FORECAST)
                    return
                    
        except Exception as e:
            logger.warning(f"⚠️ Ошибка загрузки компаний: {e}")
        
        # Если компаний нет или произошла ошибка, предлагаем создать новый профиль
        zodiac_text = """🔮 АНАЛИЗ ЗНАКА ЗОДИАКА КОМПАНИИ

Для определения знака зодиака мне нужны базовые данные о компании.

📝 Введите полное название компании:"""
        
        await update.message.reply_text(
            zodiac_text,
            parse_mode=None,
            reply_markup=ReplyKeyboardRemove()
        )
        
        self.state_manager.set_state(user_id, BotState.ZODIAC_COMPANY_NAME)
        self.state_manager.get_user_data(user_id).reset()
    
    async def _handle_zodiac_company_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка названия компании для анализа знака зодиака"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        user_data = self.state_manager.get_user_data(user_id)
        
        # Очищаем и сохраняем название
        cleaned_name = clean_company_name(text.strip())
        if user_data:
            user_data.company_name = cleaned_name
        
        await update.message.reply_text(
            f"✅ Название: {cleaned_name}\
\
"
            "📅 Теперь введите дату регистрации компании в формате ДД.ММ.ГГГГ\
"
            "Например: 15.12.2015",
            parse_mode=None
        )
        
        self.state_manager.set_state(user_id, BotState.ZODIAC_REG_DATE)
    
    async def _handle_zodiac_reg_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка даты регистрации для анализа знака зодиака"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        user_data = self.state_manager.get_user_data(user_id)
        
        # Валидируем дату
        reg_date = validate_date(text.strip())
        if not reg_date:
            await update.message.reply_text(
                "❌ Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ\
"
                "Например: 15.12.2015",
                parse_mode=None
            )
            return
        
        if user_data:
            user_data.registration_date = reg_date
        
        await update.message.reply_text(
            f"✅ Дата регистрации: {reg_date.strftime('%d.%m.%Y')}\
\
"
            "🏙️ Введите город регистрации компании:",
            parse_mode=None
        )
        
        self.state_manager.set_state(user_id, BotState.ZODIAC_REG_PLACE)
    
    async def _handle_zodiac_reg_place(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка места регистрации и завершение анализа знака зодиака"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        user_data = self.state_manager.get_user_data(user_id)
        
        if user_data:
            user_data.registration_place = text.strip()
        
        if not user_data or not user_data.company_name or not user_data.registration_date:
            await update.message.reply_text(
                "❌ Ошибка: недостаточно данных для анализа. Попробуйте снова.",
                reply_markup=self.keyboards.get_main_menu()
            )
            self.state_manager.reset_user(user_id)
            return
            
        logger.info(f"🔮 Начинаем полный анализ для компании: {user_data.company_name}")
        
        # Краткое уведомление о начале анализа
        await update.message.reply_text(
            "🔮 Анализирую астрологические данные компании...",
            parse_mode=None
        )
        
        # ПОЛНЫЙ АНАЛИЗ СОГЛАСНО ТЗ
        try:
            company_info = user_data.get_company_data()
            
            # Получаем астрологические данные БЕЗ отчетов о процессе
            
            # Получаем астрологические данные через API
            astro_data = ""
            zodiac_sign = ""
            if self.astro_agent and hasattr(self.astro_agent, 'astro_calculations'):
                try:
                    # Создаем натальную карту компании
                    # Учитываем город при расчетах
                    city = user_data.registration_place or "Москва"
                    logger.info(f"🌍 Используем город {city} для астрологических расчетов")
                    
                    natal_chart = await self.astro_agent.astro_calculations.get_company_natal_chart(
                        user_data.company_name,
                        user_data.registration_date,
                        city
                    )
                    
                    if natal_chart and natal_chart.get('basic_info'):
                        zodiac_sign = natal_chart['basic_info'].get('sun_sign', '')
                        characteristics = natal_chart.get('interpretation', {})
                        astro_data = f"""
♈ Знак зодиака: {zodiac_sign}
🔥 Элемент: {natal_chart['basic_info'].get('element', '')}
🪐 Управитель: {natal_chart['basic_info'].get('ruler', '')}
💼 Бизнес-стиль: {characteristics.get('business_style', '')}
💰 Финансовые перспективы: {characteristics.get('financial_outlook', '')}
📈 Потенциал роста: {characteristics.get('growth_potential', '')}
                        """
                except Exception as e:
                    logger.error(f"❌ ProKerala API ОБЯЗАТЕЛЕН согласно ТЗ: {e}")
                    await update.message.reply_text(
                        f"❌ Ошибка: ProKerala API недоступен, но согласно ТЗ обязателен. Попробуйте позже.",
                        reply_markup=self.keyboards.get_main_menu(),
                        parse_mode=None
                    )
                    self.state_manager.reset_user(user_id)
                    return
            else:
                logger.error("❌ AstroAgent недоступен - ОБЯЗАТЕЛЕН согласно ТЗ")
                await update.message.reply_text(
                    "❌ Ошибка: Астрологические сервисы недоступны. Попробуйте позже.",
                    reply_markup=self.keyboards.get_main_menu(),
                    parse_mode=None
                )
                self.state_manager.reset_user(user_id)
                return
            
            # Получаем новостные данные БЕЗ отчетов о процессе
            
            news_data = ""
            if self.news_analyzer:
                try:
                    # Получаем новости по трем блокам согласно ТЗ
                    
                    # Политические новости
                    political_news = await self.news_analyzer.news_client.get_politics_news(limit=3)
                    politics_summary = "🏛️ ПОЛИТИКА:\n"
                    if political_news:
                        for i, article in enumerate(political_news[:3], 1):
                            title = article.get('title', '')[:80]
                            politics_summary += f"{i}. {title}...\n"
                    
                    # Экономические новости
                    business_news = await self.news_analyzer.news_client.get_business_news(limit=3)
                    economy_summary = "\n💼 ЭКОНОМИКА:\n"
                    if business_news:
                        # Обрабатываем как список или как dict с results
                        news_list = business_news if isinstance(business_news, list) else business_news.get('results', [])
                        for i, article in enumerate(news_list[:3], 1):
                            title = article.get('title', '')[:80]
                            economy_summary += f"{i}. {title}...\n"
                    
                    # Новости фондовой биржи
                    stock_news = await self.news_analyzer.news_client.get_stock_market_news(limit=3)
                    logger.info(f"📈 Получено {len(stock_news) if stock_news else 0} новостей по фондовому рынку")
                    stock_summary = "\n📈 ФОНДОВАЯ БИРЖА:\n"
                    if stock_news:
                        # Обрабатываем как список или как dict с results
                        news_list = stock_news if isinstance(stock_news, list) else stock_news.get('results', [])
                        for i, article in enumerate(news_list[:3], 1):
                            title = article.get('title', '')[:80]
                            if any(word in title.lower() for word in ['акци', 'биржа', 'инвест', 'рынок']):
                                stock_summary += f"{i}. {title}...\n"
                    
                    news_data = politics_summary + economy_summary + stock_summary
                    
                except Exception as e:
                    logger.error(f"❌ Новостные API ОБЯЗАТЕЛЬНЫ согласно ТЗ: {e}")
                    await update.message.reply_text(
                        f"❌ Ошибка: Новостные источники недоступны, но согласно ТЗ обязательны. Попробуйте позже.",
                        reply_markup=self.keyboards.get_main_menu(),
                        parse_mode=None
                    )
                    self.state_manager.reset_user(user_id)
                    return
            else:
                logger.error("❌ NewsAnalyzer недоступен - ОБЯЗАТЕЛЕН согласно ТЗ")
                await update.message.reply_text(
                    "❌ Ошибка: Новостные сервисы недоступны. Попробуйте позже.",
                    reply_markup=self.keyboards.get_main_menu(),
                    parse_mode=None
                )
                self.state_manager.reset_user(user_id)
                return
            
            # Обрабатываем данные через LLM БЕЗ отчетов о процессе
            
            # Формируем полный запрос к LLM согласно ТЗ
            if self.astro_agent:
                try:
                    # Правильно формируем данные для агента
                    company_data = {
                        'name': user_data.company_name,
                        'registration_date': user_data.registration_date,
                        'registration_place': user_data.registration_place
                    }
                    
                    # Интегрируем новости в контекст
                    full_analysis = await self.astro_agent.analyze_company_zodiac(
                        company_data, 
                        news_data=news_data
                    )
                    
                    # Добавляем нумерологический анализ
                    if self.numerology and user_data.company_name:
                        name_number = self.numerology.calculate_name_number(user_data.company_name)
                        numerology_interpretation = self.numerology.get_number_interpretation(name_number)
                        full_analysis += f"""

🔢 НУМЕРОЛОГИЧЕСКИЙ АНАЛИЗ:
🎯 Число имени: {name_number}
{numerology_interpretation}"""
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка LLM анализа: {e}")
                    # Создаем детальный анализ даже без LLM
                    full_analysis = f"""🔮 АСТРОЛОГИЧЕСКИЙ АНАЛИЗ КОМПАНИИ

{astro_data}

📊 ХАРАКТЕРИСТИКИ ЗНАКА {zodiac_sign}:
🌟 Компания под знаком {zodiac_sign} обладает уникальными деловыми качествами
💎 Этот знак благоприятствует определенным направлениям бизнеса
✨ Рекомендуется учитывать астрологические циклы при принятии решений

🌟 РЕКОМЕНДАЦИИ:
💼 Используйте сильные стороны знака для развития бизнеса
📅 Планируйте важные решения с учетом астрологических периодов
🚀 Развивайте те направления, которые поддерживает ваш знак зодиака"""
            else:
                # Создаем базовый, но информативный анализ
                full_analysis = f"""🔮 АСТРОЛОГИЧЕСКИЙ АНАЛИЗ КОМПАНИИ

{astro_data}

📊 ХАРАКТЕРИСТИКИ ЗНАКА {zodiac_sign}:
🌟 Компания под знаком {zodiac_sign} обладает особыми деловыми качествами
💎 Этот знак определяет основные бизнес-тенденции и подходы
✨ Астрологические циклы влияют на развитие компании

🌟 БАЗОВЫЕ РЕКОМЕНДАЦИИ:
💼 Развивайте направления, поддерживаемые вашим знаком
📅 Учитывайте астрологические периоды в планировании
🚀 Используйте сильные стороны знака для роста бизнеса"""
            
            # Формируем финальный результат БЕЗ технических сообщений
            
            # Формируем итоговый результат БЕЗ указания источников
            final_result = full_analysis
            
            # Разбиваем длинное сообщение на части
            await self._send_long_message(update, final_result, self.keyboards.get_main_menu())
            
            # Сохраняем полный анализ в базу данных
            try:
                from database.connection import db_manager
                from database.crud import UserCRUD, AnalysisCRUD
                
                with db_manager.get_session() as session:
                    user_db = UserCRUD.get_user_by_telegram_id(session, user_id)
                    if user_db and user_data.company_name and user_data.registration_date:
                        # Приводим Column к int для линтера
                        db_user_id = int(user_db.id)  # type: ignore
                        AnalysisCRUD.create_analysis(
                            session=session,
                            user_id=db_user_id,  # type: ignore
                            analysis_type="zodiac_full_tz",
                            result_text=final_result,
                            input_data={
                                'company_name': user_data.company_name,
                                'registration_date': user_data.registration_date.isoformat(),
                                'registration_place': user_data.registration_place or ""
                            },
                            zodiac_signs=[zodiac_sign] if zodiac_sign else [],
                            news_used=bool(news_data),
                            numerology_used=bool(self.numerology),
                            astrology_api_used=True
                        )
                        logger.info(f"💾 Полный анализ по ТЗ сохранен для пользователя {user_id}")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка сохранения анализа: {e}")
            
            # Сохраняем диалог в векторную БД
            if self.embedding_manager:
                try:
                    await self.embedding_manager.save_user_dialog(
                        user_id, 
                        f"Полный анализ знака зодиака для {user_data.company_name}",
                        company_info
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка сохранения в векторную БД: {e}")
            
            # Предлагаем сохранить профиль компании для будущего использования
            result = self._offer_save_company_profile(update, user_data, final_result)
            if result is not None:
                await result
            
            # Автоматически сохраняем компанию в профиль пользователя
            await self._auto_save_company_profile(update, user_data)
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа знака зодиака: {e}")
            await update.message.reply_text(
                "😔 Произошла ошибка при анализе. Попробуйте позже.",
                reply_markup=self.keyboards.get_main_menu(),
                parse_mode='HTML'
            )
        
        # Возвращаемся в главное меню
        self.state_manager.reset_user(user_id)
    
    async def _send_long_message(self, update: Update, text: str, reply_markup=None):
        """Отправка длинного сообщения с разбивкой на части"""
        MAX_MESSAGE_LENGTH = 4000  # Оставляем запас от лимита Telegram в 4096
        
        if len(text) <= MAX_MESSAGE_LENGTH:
            # Короткое сообщение - отправляем как есть
            if update.message:
                await update.message.reply_text(
                    text,
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
            return
        
        # Разбиваем длинное сообщение
        parts = []
        current_part = ""
        
        # Разбиваем по абзацам
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            # Если параграф слишком длинный сам по себе
            if len(paragraph) > MAX_MESSAGE_LENGTH:
                # Если есть накопленный текст, добавляем его как часть
                if current_part:
                    parts.append(current_part.strip())
                    current_part = ""
                
                # Разбиваем длинный параграф по предложениям
                sentences = paragraph.split('. ')
                temp_part = ""
                
                for sentence in sentences:
                    if len(temp_part + sentence + '. ') > MAX_MESSAGE_LENGTH:
                        if temp_part:
                            parts.append(temp_part.strip())
                        temp_part = sentence + '. '
                    else:
                        temp_part += sentence + '. '
                
                if temp_part:
                    current_part = temp_part
            else:
                # Проверяем, поместится ли параграф в текущую часть
                if len(current_part + '\n\n' + paragraph) > MAX_MESSAGE_LENGTH:
                    # Не помещается - сохраняем текущую часть
                    if current_part:
                        parts.append(current_part.strip())
                    current_part = paragraph
                else:
                    # Помещается - добавляем к текущей части
                    if current_part:
                        current_part += '\n\n' + paragraph
                    else:
                        current_part = paragraph
        
        # Добавляем последнюю часть
        if current_part:
            parts.append(current_part.strip())
        
        # Отправляем все части
        for i, part in enumerate(parts):
            # Клавиатуру добавляем только к последнему сообщению
            keyboard = reply_markup if i == len(parts) - 1 else None
            
            # Добавляем номер части если частей больше одной
            if len(parts) > 1:
                part_header = f"📄 Часть {i + 1} из {len(parts)}\n\n"
                part = part_header + part
            
            if update.message:
                await update.message.reply_text(
                    part,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
            
            # Небольшая пауза между сообщениями
            await asyncio.sleep(0.5)
    
    async def _start_business_forecast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запуск полного бизнес-прогноза"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        
        # Сначала проверяем, есть ли сохраненные компании
        try:
            from database.crud import CompanyCRUD
            from database.connection import get_session
            
            with get_session() as session:
                user_companies = CompanyCRUD.get_companies_by_user(session, user_id)
                
                if user_companies:
                    # Показываем список компаний для выбора
                    companies_text = "📈 ВЫБЕРИТЕ КОМПАНИЮ ДЛЯ БИЗНЕС-ПРОГНОЗА\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    
                    for i, comp in enumerate(user_companies, 1):
                        reg_date_str = 'Не указана'
                        if hasattr(comp, 'registration_date') and comp.registration_date is not None:
                            try:
                                reg_date_str = comp.registration_date.strftime('%d.%m.%Y')
                            except:
                                reg_date_str = 'Не указана'
                        
                        reg_place = 'Не указано'
                        if hasattr(comp, 'registration_place') and comp.registration_place is not None:
                            reg_place = str(comp.registration_place)
                        
                        companies_text += f"""📊 {i}. {comp.name}
📅 Дата регистрации: {reg_date_str}
🏙️ Место: {reg_place}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"""
                    
                    companies_text += "\n💡 Выберите компанию из списка выше или создайте новый профиль."
                    
                    await update.message.reply_text(
                        companies_text,
                        parse_mode=None,
                        reply_markup=self.keyboards.get_companies_management_menu(user_companies)
                    )
                    
                    # Устанавливаем состояние выбора компании
                    self.state_manager.set_state(user_id, BotState.SELECTING_COMPANY_FOR_FORECAST)
                    return
                    
        except Exception as e:
            logger.warning(f"⚠️ Ошибка загрузки компаний: {e}")
        
        # Если компаний нет или произошла ошибка, предлагаем создать новый профиль
        forecast_text = """📈 ПОЛНЫЙ БИЗНЕС-ПРОГНОЗ

Для составления детального прогноза мне потребуется информация о:
• Компании (название, дата и место регистрации)
• Сфере деятельности
• Собственнике и руководителе

📝 Начнем с названия компании:"""
        
        await update.message.reply_text(
            forecast_text,
            parse_mode=None,
            reply_markup=ReplyKeyboardRemove()
        )
        
        self.state_manager.set_state(user_id, BotState.BUSINESS_COMPANY_NAME)
        self.state_manager.get_user_data(user_id).reset()
    
    async def _handle_business_company_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка названия компании для бизнес-прогноза"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        user_data = self.state_manager.get_user_data(user_id)
        
        cleaned_name = clean_company_name(text.strip())
        user_data.company_name = cleaned_name
        
        await update.message.reply_text(
            f"✅ Компания: {cleaned_name}\
\
"
            "📅 Введите дату регистрации в формате ДД.ММ.ГГГГ:",
            parse_mode=None
        )
        
        self.state_manager.set_state(user_id, BotState.BUSINESS_REG_DATE)
    
    async def _handle_business_reg_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка даты регистрации для бизнес-прогноза"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        user_data = self.state_manager.get_user_data(user_id)
        
        reg_date = validate_date(text.strip())
        if not reg_date:
            await update.message.reply_text(
                "❌ Неверный формат даты. Введите в формате ДД.ММ.ГГГГ"
            )
            return
        
        if user_data:
            user_data.registration_date = reg_date
        
        await update.message.reply_text(
            f"✅ Дата: {reg_date.strftime('%d.%m.%Y')}\
\
"
            "🏙️ Введите город регистрации:",
            parse_mode=None
        )
        
        self.state_manager.set_state(user_id, BotState.BUSINESS_REG_PLACE)
    
    async def _handle_business_reg_place(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка места регистрации для бизнес-прогноза"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        user_data = self.state_manager.get_user_data(user_id)
        
        user_data.registration_place = text.strip()
        
        await update.message.reply_text(
            f"✅ Место: {text.strip()}\
\
"
            "🏭 Выберите сферу деятельности компании:",
            parse_mode=None,
            reply_markup=self.keyboards.get_business_spheres()
        )
        
        self.state_manager.set_state(user_id, BotState.BUSINESS_SPHERE)
    
    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик inline-кнопок"""
        if not update.callback_query or not update.effective_user:
            return
            
        query = update.callback_query
        user_id = update.effective_user.id
        callback_data = query.data
        
        await query.answer()  # Убираем "часики" с кнопки
        
        logger.info(f"🔘 Пользователь {user_id}: callback '{callback_data or 'Unknown'}'")
        
        if not callback_data:
            return
        
        # Обработка выбора сферы деятельности
        if callback_data.startswith("sphere_"):
            current_state = self.state_manager.get_state(user_id)
            if current_state == BotState.PROFILE_SPHERE:
                await self._handle_profile_sphere_selection(update, context, callback_data)
            else:
                await self._handle_sphere_selection(update, context, callback_data)
        
        # Обработка типов совместимости
        elif callback_data.startswith("compat_"):
            # await self._handle_compatibility_type(update, context, callback_data)
            pass
        
        # Обработка детального анализа
        elif callback_data.startswith("analysis_"):
            # await self._handle_analysis_type(update, context, callback_data)
            pass
        
        # Обработка управления компаниями
        elif callback_data == "add_company":
            await self._start_add_company(update, context)
        
        elif callback_data.startswith("select_company_"):
            company_id = callback_data.replace("select_company_", "")
            await self._select_company(update, context, company_id)
        
        elif callback_data.startswith("edit_company_"):
            company_id = callback_data.replace("edit_company_", "")
            await self._edit_company(update, context, company_id)
        
        elif callback_data.startswith("delete_company_"):
            company_id = callback_data.replace("delete_company_", "")
            await self._delete_company(update, context, company_id)
        
        elif callback_data == "back_to_companies":
            await self._show_companies_menu(update, context)
        
        # Обработка сохранения профилей компаний
        elif callback_data == "save_company_profile":
            await self._save_company_profile(update, context)
        
        elif callback_data == "skip_save_company":
            await self._skip_save_company(update, context)
        
        # Обработка общих действий
        elif callback_data == "back_to_main":
            await self._back_to_main_menu(update, context)
        
        elif callback_data == "skip_field":
            await self._skip_current_field(update, context)
        
        # Обработка астропрогнозов компаний
        elif callback_data == "company_zodiac":
            await self._handle_company_zodiac_analysis(update, context)
        
        elif callback_data == "company_forecast":
            await self._handle_company_business_forecast(update, context)
        
        elif callback_data == "company_compatibility":
            await self._handle_company_compatibility_analysis(update, context)
        
        # Обработка возврата к действиям с компанией
        elif callback_data == "back_to_company_actions":
            await self._back_to_company_actions(update, context)
        
        # Обработка навигации по частям длинного анализа
        elif callback_data.startswith("next_part_"):
            part_index = int(callback_data.replace("next_part_", ""))
            await self._show_next_analysis_part(update, context)
        
        else:
            await query.edit_message_text(
                "🤔 Неизвестная команда. Возвращаюсь в главное меню.",
                reply_markup=self.keyboards.get_back_inline_button()
            )
    
    async def _handle_sphere_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Обработка выбора сферы деятельности"""
        if not update.effective_user or not update.callback_query:
            return
        user_id = update.effective_user.id
        user_data = self.state_manager.get_user_data(user_id)
        
        sphere_map = {
            "sphere_construction": "Строительство и промышленность",
            "sphere_finance": "Финансы и инвестиции",
            "sphere_trade": "Торговля и сфера услуг", 
            "sphere_tech": "Технологии и телекоммуникации",
            "sphere_government": "Государственный сектор и социальная сфера",
            "sphere_energy": "Энергетика"
        }
        
        selected_sphere = sphere_map.get(callback_data, "Неизвестно")
        if user_data:
            user_data.business_sphere = selected_sphere
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
            f"✅ Сфера деятельности: {selected_sphere}\
\
"
            "👤 Теперь информация о руководстве.\
\
"
            "Введите имя собственника (или нажмите '⏭️ Пропустить'):",
            parse_mode=None,
            reply_markup=self.keyboards.get_skip_optional()
        )
        
        self.state_manager.set_state(user_id, BotState.BUSINESS_OWNER_NAME)
    
    async def _skip_current_field(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Пропуск текущего поля"""
        if not update.effective_user:
            return
        user_id = update.effective_user.id
        current_state = self.state_manager.get_state(user_id)
        
        if current_state == BotState.BUSINESS_OWNER_NAME:
            await self._ask_director_name(update, context)
        elif current_state == BotState.BUSINESS_OWNER_BIRTH:
            await self._ask_director_name(update, context)
        elif current_state == BotState.BUSINESS_DIRECTOR_NAME:
            await self._ask_director_birth(update, context, required=True)
        else:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    "❌ Это поле нельзя пропустить."
                )
    
    async def _ask_director_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запрос имени директора"""
        if not update.effective_user:
            return
        user_id = update.effective_user.id
        
        # Проверяем тип обновления и используем соответствующий метод
        if update.callback_query:
            await update.callback_query.edit_message_text(
                "👔 Введите имя директора компании (или нажмите '⏭️ Пропустить'):",
                parse_mode=None,
                reply_markup=self.keyboards.get_skip_optional()
            )
        else:
            if update.message:
                await update.message.reply_text(
                    "👔 Введите имя директора компании (или нажмите '⏭️ Пропустить'):",
                    parse_mode=None,
                    reply_markup=self.keyboards.get_skip_optional()
                )
        
        self.state_manager.set_state(user_id, BotState.BUSINESS_DIRECTOR_NAME)
    
    async def _ask_director_birth(self, update: Update, context: ContextTypes.DEFAULT_TYPE, required: bool = False):
        """Запрос даты рождения директора"""
        if not update.effective_user:
            return
        user_id = update.effective_user.id
        
        if required:
            text = ("📅 Введите дату рождения руководителя в формате ДД.ММ.ГГГГ\
"
                   "⚠️ Это поле обязательно для составления прогноза.")
            markup = None
        else:
            text = ("📅 Введите дату рождения руководителя в формате ДД.ММ.ГГГГ\
"
                   "(или нажмите '⏭️ Пропустить'):")
            markup = self.keyboards.get_skip_optional()
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                parse_mode=None,
                reply_markup=markup
            )
        else:
            if update.message:
                await update.message.reply_text(
                    text,
                    parse_mode=None,
                    reply_markup=markup
                )
        
        self.state_manager.set_state(user_id, BotState.BUSINESS_DIRECTOR_BIRTH)
    
    async def _handle_business_owner_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка имени владельца компании"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        user_data = self.state_manager.get_user_data(user_id)
        
        if user_data:
            user_data.owner_name = text.strip()
            logger.info(f"👤 Владелец компании {user_data.company_name}: {text}")
        
        # Переходим к дате рождения владельца
        await update.message.reply_text(
            f"📅 Введите дату рождения владельца {text} в формате ДД.ММ.ГГГГ\nНапример: 15.03.1985",
            parse_mode=None,
            reply_markup=self.keyboards.get_skip_optional()
        )
        
        self.state_manager.set_state(user_id, BotState.BUSINESS_OWNER_BIRTH)
    
    async def _handle_business_owner_birth(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка даты рождения владельца компании"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        user_data = self.state_manager.get_user_data(user_id)
        
        # Валидация даты
        birth_date = validate_date(text.strip())
        if not birth_date:
            await update.message.reply_text(
                "❌ Неверный формат даты. Введите в формате ДД.ММ.ГГГГ (например: 15.03.1985):",
                parse_mode=None
            )
            return
        
        if user_data:
            user_data.owner_birth_date = birth_date
            logger.info(f"📅 Дата рождения владельца: {birth_date}")
        
        # Переходим к запросу данных директора
        await self._ask_director_name(update, context)
    
    async def _handle_business_director_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка имени директора компании"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        user_data = self.state_manager.get_user_data(user_id)
        
        if user_data:
            user_data.director_name = text.strip()
            logger.info(f"👔 Директор компании {user_data.company_name}: {text}")
        
        # Переходим к дате рождения директора
        await update.message.reply_text(
            f"📅 Введите дату рождения директора {text} в формате ДД.ММ.ГГГГ\nНапример: 20.07.1980",
            parse_mode=None,
            reply_markup=self.keyboards.get_skip_optional()
            )
        
        self.state_manager.set_state(user_id, BotState.BUSINESS_DIRECTOR_BIRTH)
    
    async def _handle_business_director_birth(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка даты рождения директора и завершение бизнес-прогноза"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        user_data = self.state_manager.get_user_data(user_id)
        
        birth_date = validate_date(text.strip())
        if not birth_date:
            await update.message.reply_text(
                "❌ Неверный формат даты. Введите в формате ДД.ММ.ГГГГ"
            )
            return
        
        user_data.director_birth_date = birth_date
        
        # Показываем прогресс
        await update.message.reply_text(
            "🔮 Генерирую полный бизнес-прогноз...\
\
"
            "⏳ Анализирую астрологические и нумерологические данные...\
"
            "📰 Учитываю текущие экономические тренды...",
            parse_mode=None
        )
        
        # Генерируем полный прогноз
        try:
            company_data = user_data.get_company_data()
            
            # Получаем новости и астрологические данные
            news_summary = ""
            astrology_data = ""
            
            if self.news_analyzer and user_data.business_sphere:
                news_analysis = await self.news_analyzer.analyze_news_for_company(
                    user_data.business_sphere
                )
                news_summary = news_analysis.get('summary', '')
            
            # Генерируем прогноз
            if self.astro_agent:
                forecast = await self.astro_agent.generate_business_forecast(
                    company_data,
                    astrology_data,
                    news_summary
                )
            else:
                # Заглушка при отсутствии AI
                forecast = self._generate_basic_forecast(user_data)
            
            # Отправляем прогноз с разбивкой на части
            await self._send_long_message(update, forecast, self.keyboards.get_detailed_analysis())
            
            # Сохраняем в векторную БД
            if self.embedding_manager:
                await self.embedding_manager.save_astro_prediction(
                    company_data,
                    forecast,
                    "business_forecast"
                )
            
            # Автоматически сохраняем компанию в профиль пользователя
            await self._auto_save_company_profile(update, user_data)
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации бизнес-прогноза: {e}")
            await update.message.reply_text(
                "😔 Произошла ошибка при генерации прогноза. Попробуйте позже.",
                reply_markup=self.keyboards.get_main_menu()
            )
        
        # Возвращаемся в главное меню
        self.state_manager.reset_user(user_id)
    
    def _generate_basic_forecast(self, user_data) -> str:
        """Генерация базового прогноза без AI"""
        from utils.helpers import get_zodiac_sign
        
        company_zodiac = get_zodiac_sign(user_data.registration_date)
        director_zodiac = "Не указано"
        
        if user_data.director_birth_date:
            director_zodiac = get_zodiac_sign(user_data.director_birth_date)
        
        # Нумерологический анализ
        company_number = self.numerology.calculate_name_number(user_data.company_name) if user_data.company_name else 1
        company_meaning = self.numerology.get_number_meaning(company_number)
        
        forecast = f"""🌟 ПОЛНЫЙ БИЗНЕС-ПРОГНОЗ
🏢 Компания: "{user_data.company_name}"
📅 Анализ на: {datetime.now().strftime('%d.%m.%Y')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔮 АСТРОЛОГИЧЕСКИЙ ПРОФИЛЬ

⭐ Знак компании: {company_zodiac}
👔 Знак руководителя: {director_zodiac}  
📋 Дата регистрации: {user_data.registration_date.strftime('%d.%m.%Y')}
🌍 Место: {user_data.registration_place or 'Не указано'}
🏭 Сфера деятельности: {user_data.business_sphere or 'Не указана'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔢 НУМЕРОЛОГИЧЕСКИЙ ПРОФИЛЬ

🎯 Число имени: {company_number}
✨ Характеристики: {company_meaning.get('traits', 'Уникальные качества лидерства и инноваций')}
💼 Бизнес-потенциал: {company_meaning.get('business', 'Высокий потенциал для масштабного развития')}
⚠️ Потенциальные риски: {company_meaning.get('risks', 'Минимальные')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 СТРАТЕГИЧЕСКИЕ РЕКОМЕНДАЦИИ

🚀 Развитие бизнеса:
• Используйте энергетику числа {company_number}
• Планируйте проекты в соответствии с циклами {company_zodiac}
• Развивайте направления, поддерживаемые вашим знаком

👥 Управление командой:
• Учитывайте совместимость {company_zodiac} и {director_zodiac}
• Оптимизируйте процессы под энергетику компании
• Развивайте корпоративную культуру

💡 Инновации и рост:
• Внедряйте новшества в благоприятные периоды
• Используйте интуицию руководителя
• Развивайте уникальные конкурентные преимущества

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ ЭКСПРЕСС-ПРОГНОЗ НА 3 МЕСЯЦА

🌱 Финансы: Стабильный рост с потенциалом увеличения
🤝 Партнерства: Благоприятный период для новых альянсов
⚠️ Риски: Минимальные, связанные с внешними факторами

💡 Для получения AI-анализа с учетом актуальных экономических трендов и детального астрологического прогноза используйте расширенную версию с подключенными сервисами."""
        
        return forecast
    
    async def _start_compatibility_check(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запуск проверки совместимости"""
        if not update.message or not update.effective_user:
            return
        user_id = update.effective_user.id
        
        # Сначала проверяем, есть ли сохраненные компании
        try:
            from database.crud import CompanyCRUD
            from database.connection import get_session
            
            with get_session() as session:
                user_companies = CompanyCRUD.get_companies_by_user(session, user_id)
                
                if user_companies:
                    # Показываем список компаний для выбора
                    companies_text = "🤝 ВЫБЕРИТЕ КОМПАНИЮ ДЛЯ АНАЛИЗА СОВМЕСТИМОСТИ\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    
                    for i, comp in enumerate(user_companies, 1):
                        reg_date_str = 'Не указана'
                        if hasattr(comp, 'registration_date') and comp.registration_date is not None:
                            try:
                                reg_date_str = comp.registration_date.strftime('%d.%m.%Y')
                            except:
                                reg_date_str = 'Не указана'
                        
                        companies_text += f"""📊 {i}. {comp.name}
📅 Дата регистрации: {reg_date_str}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"""
                    
                    companies_text += "\n💡 Выберите компанию из списка выше или создайте новый профиль."
                    
                    await update.message.reply_text(
                        companies_text,
                        parse_mode=None,
                        reply_markup=self.keyboards.get_companies_management_menu(user_companies)
                    )
                    
                    # Устанавливаем состояние выбора компании
                    self.state_manager.set_state(user_id, BotState.SELECTING_COMPANY_FOR_COMPATIBILITY)
                    return
                    
        except Exception as e:
            logger.warning(f"⚠️ Ошибка загрузки компаний: {e}")
        
        # Если компаний нет или произошла ошибка, предлагаем создать новый профиль
        await update.message.reply_text(
            """🤝 АНАЛИЗ СОВМЕСТИМОСТИ

Для анализа совместимости мне потребуется информация о компании и объекте совместимости.

💡 Рекомендуется сначала создать профиль компании через анализ знака зодиака или бизнес-прогноз.

Выберите тип объекта для проверки совместимости:""",
            parse_mode=None,
            reply_markup=self.keyboards.get_compatibility_types()
        )
    
    async def _show_daily_forecast_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ меню ежедневных прогнозов"""
        if not update.message:
            return
        await update.message.reply_text(
            """📅 ЕЖЕДНЕВНЫЕ ПРОГНОЗЫ

Настройте автоматические утренние прогнозы для вашей компании:""",
            parse_mode=None,
            reply_markup=self.keyboards.get_daily_forecast_settings()
        )
    
    async def _show_companies_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ меню управления компаниями"""
        if not update.message or not update.effective_user:
            return
            
        user_id = update.effective_user.id
        
        # Загружаем сохраненные компании из БД
        companies = []
        try:
            from database.connection import db_manager
            from database.crud import CompanyCRUD
            
            with db_manager.get_session() as session:
                user_companies = CompanyCRUD.get_companies_by_user(session, user_id)
                companies = []
                for comp in user_companies:
                    reg_date = getattr(comp, 'registration_date', None)
                    companies.append({
                        'id': getattr(comp, 'id', 0),
                        'name': str(getattr(comp, 'name', 'Неизвестная компания')),
                        'registration_date': reg_date.strftime('%d.%m.%Y') if reg_date else 'Не указана',
                        'sphere': str(getattr(comp, 'business_sphere', None) or 'Не указана')
                    })
        except Exception as e:
            logger.warning(f"⚠️ Ошибка загрузки компаний: {e}")
        
        if companies:
            # Формируем список компаний с подробной информацией
            companies_text = "🏢 ВАШИ КОМПАНИИ\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            for i, comp in enumerate(companies, 1):
                companies_text += f"""📊 {i}. {comp['name']}
📅 Регистрация: {comp['registration_date']}
🏭 Сфера: {comp['sphere']}

"""
            
            companies_text += """📋 ДОСТУПНЫЕ ДЕЙСТВИЯ:
• Выбрать компанию для анализа
• Добавить новую компанию
• Редактировать существующую
• Удалить компанию

Выберите действие:"""
            
            await update.message.reply_text(
                companies_text,
                parse_mode=None,
                reply_markup=self.keyboards.get_companies_management_menu(companies)
            )
        else:
            await update.message.reply_text(
                """🏢 УПРАВЛЕНИЕ КОМПАНИЯМИ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 У вас пока нет сохраненных компаний.

💡 ВОЗМОЖНОСТИ:
✅ Сохранение полных профилей компаний
✅ Быстрый выбор для любых анализов
✅ Редактирование данных компаний
✅ Управление несколькими компаниями

🚀 СОЗДАТЬ ПЕРВУЮ КОМПАНИЮ:
Используйте любой анализ (знак зодиака или бизнес-прогноз), и система автоматически предложит сохранить профиль компании.

➕ Или создайте профиль компании прямо сейчас:""",
                parse_mode=None,
                reply_markup=self.keyboards.get_add_company_menu()
            )
    
    async def _show_settings_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ меню настроек"""
        settings_text = """
⚙️ НАСТРОЙКИ АСТРОБОТА

🔔 Уведомления: Включены
⏰ Время прогнозов: 08:00
🏢 Активная компания: Не выбрана
📊 Сохранено прогнозов: 0

Для изменения настроек используйте соответствующие разделы меню.
        """
        
        if update.message:
            await update.message.reply_text(
                settings_text,
                parse_mode=None,
                reply_markup=self.keyboards.get_back_button()
            )
    
    async def _back_to_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Возврат в главное меню"""
        if not update.effective_user or not update.callback_query:
            return
        user_id = update.effective_user.id
        
        await update.callback_query.edit_message_text(
            "🔮 Главное меню Астробота\
\
"
            "Выберите нужное действие:",
            parse_mode=None,
            reply_markup=self.keyboards.get_back_inline_button()
        )
        
        self.state_manager.reset_user(user_id)
    
    async def _show_personal_cabinet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ личного кабинета пользователя"""
        if not update.effective_user:
            return
            
        user = update.effective_user
        user_id = user.id
        
        # Получаем статистику пользователя из базы данных
        try:
            from database.connection import db_manager
            from database.crud import UserCRUD
            
            with db_manager.get_session() as session:
                db_user = UserCRUD.get_user_by_telegram_id(session, user_id)
                
                if db_user:
                    analyses_count = len(db_user.analyses) if hasattr(db_user, 'analyses') else 0
                    registration_date = db_user.created_at.strftime('%d.%m.%Y') if hasattr(db_user, 'created_at') else "Неизвестно"
                else:
                    analyses_count = 0
                    registration_date = "Сегодня"
        except Exception as e:
            logger.warning(f"⚠️ Ошибка загрузки данных пользователя: {e}")
            analyses_count = 0
            registration_date = "Неизвестно"
        
        cabinet_text = f"""👤 ЛИЧНЫЙ КАБИНЕТ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👋 Добро пожаловать, {user.first_name or 'Пользователь'}!

📊 СТАТИСТИКА ИСПОЛЬЗОВАНИЯ:
🔮 Проведено анализов: {analyses_count}
📅 Дата регистрации: {registration_date}
🆔 ID пользователя: {user_id}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 ДОСТУПНЫЕ ФУНКЦИИ:

🔮 Анализ знака зодиака компаний
📊 Бизнес-прогнозы и рекомендации  
🤝 Проверка совместимости
📅 Ежедневные астрологические прогнозы
🏢 Управление компаниями
🔢 Нумерологические расчеты

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💎 ПРЕМИУМ ВОЗМОЖНОСТИ:
✨ Детальные астрологические карты
📰 Интеграция с новостными трендами
🧠 Сохранение в векторной базе данных
🎯 Персонализированные рекомендации

🔙 Назад к главному меню"""

        if update.message:
            await update.message.reply_text(
                cabinet_text,
                parse_mode=None,
                reply_markup=self.keyboards.get_back_button()
            )
    
    async def _show_tariffs_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ тарифных планов"""
        tariffs_text = """💳 ТАРИФНЫЕ ПЛАНЫ АСТРОБОТА
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🆓 БАЗОВЫЙ (ТЕКУЩИЙ)
✅ Определение знака зодиака компании
✅ Базовые астрологические характеристики  
✅ Простые нумерологические расчеты
✅ Общие рекомендации по развитию
⭐ Цена: Бесплатно

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💎 ПРЕМИУМ
✅ Все функции Базового тарифа
✅ Детальные натальные карты через AI
✅ Анализ совместимости руководителей
✅ Интеграция с экономическими новостями
✅ Персональные бизнес-прогнозы
✅ Сохранение истории анализов
✅ Приоритетная поддержка
⭐ Цена: 990₽/месяц

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 КОРПОРАТИВНЫЙ  
✅ Все функции Премиум тарифа
✅ Безлимитные анализы компаний
✅ API доступ для интеграций
✅ Индивидуальные астрологические консультации
✅ Корпоративные отчеты и аналитика
✅ Персональный менеджер
⭐ Цена: 4990₽/месяц

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 СПЕЦИАЛЬНОЕ ПРЕДЛОЖЕНИЕ:
🎯 Первый месяц Премиум - 99₽
🎁 Корпоративный тариф - скидка 20% при оплате за год

📞 Для подключения платных тарифов свяжитесь с поддержкой: @astrobot_support

🔙 Назад к главному меню"""

        if update.message:
            await update.message.reply_text(
                tariffs_text,
                parse_mode=None,
                reply_markup=self.keyboards.get_back_button()
            )
    
    async def _start_add_company(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запуск создания профиля компании"""
        if not update.callback_query or not update.effective_user:
            return
            
        user_id = update.effective_user.id
        
        await update.callback_query.edit_message_text(
            """✨ СОЗДАНИЕ ПРОФИЛЯ КОМПАНИИ ✨
⭐️ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ ⭐️

📝 Введите полное название компании:

💡 Этот профиль будет сохранен и доступен для быстрого выбора в любых анализах.""",
            parse_mode=None,
            reply_markup=self.keyboards.get_back_inline_button()
        )
        
        self.state_manager.set_state(user_id, BotState.PROFILE_COMPANY_NAME)
        self.state_manager.get_user_data(user_id).reset()
    
    async def _select_company(self, update: Update, context: ContextTypes.DEFAULT_TYPE, company_id: str):
        """Выбор компании для работы"""
        if not update.callback_query or not update.effective_user:
            return
            
        user_id = update.effective_user.id
        
        # Загружаем данные компании
        try:
            from database.connection import db_manager
            from database.crud import CompanyCRUD
            
            with db_manager.get_session() as session:
                company = CompanyCRUD.get_company_by_id(session, int(company_id))
                
                if company and getattr(company, 'owner_id', 0) == user_id:
                    # Загружаем данные компании в текущую сессию
                    user_data = self.state_manager.get_user_data(user_id)
                    user_data.company_name = str(getattr(company, 'name', ''))
                    user_data.registration_date = getattr(company, 'registration_date', None)
                    user_data.registration_place = str(getattr(company, 'registration_place', '') or '')
                    user_data.business_sphere = str(getattr(company, 'business_sphere', '') or '')
                    user_data.owner_name = str(getattr(company, 'owner_name', '') or '')
                    user_data.owner_birth_date = getattr(company, 'owner_birth_date', None)
                    user_data.director_name = str(getattr(company, 'director_name', '') or '')
                    user_data.director_birth_date = getattr(company, 'director_birth_date', None)
                    
                    # Сохраняем данные компании в context.user_data для астропрогнозов
                    # Используем update() вместо прямого присваивания
                    company_data_dict = {
                        'id': getattr(company, 'id', 0),
                        'name': str(getattr(company, 'name', '')),
                        'registration_date': getattr(company, 'registration_date', None),
                        'registration_place': str(getattr(company, 'registration_place', '') or ''),
                        'business_sphere': str(getattr(company, 'business_sphere', '') or ''),
                        'owner_name': str(getattr(company, 'owner_name', '') or ''),
                        'owner_birth_date': getattr(company, 'owner_birth_date', None),
                        'director_name': str(getattr(company, 'director_name', '') or ''),
                        'director_birth_date': getattr(company, 'director_birth_date', None)
                    }
                    
                    # Проверяем, что context.user_data существует
                    if context.user_data is not None:
                        context.user_data.update({'selected_company': company_data_dict})
                    else:
                        # Логируем проблему, но продолжаем работу
                        logger.warning("⚠️ context.user_data is None, данные компании не сохранены")
                    
                    reg_date = getattr(company, 'registration_date', None)
                    company_info = f"""🏢 ВЫБРАНА КОМПАНИЯ: {str(getattr(company, 'name', 'Неизвестная'))}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 ПРОФИЛЬ КОМПАНИИ:
📅 Дата регистрации: {reg_date.strftime('%d.%m.%Y') if reg_date else 'Не указана'}
🌍 Место: {str(getattr(company, 'registration_place', '') or 'Не указано')}
🏭 Сфера: {str(getattr(company, 'business_sphere', '') or 'Не указана')}

👥 РУКОВОДСТВО:
👤 Владелец: {str(getattr(company, 'owner_name', '') or 'Не указан')}
👔 Директор: {str(getattr(company, 'director_name', '') or 'Не указан')}

Выберите действие:"""
                    
                    await update.callback_query.edit_message_text(
                        company_info,
                        parse_mode=None,
                        reply_markup=self.keyboards.get_company_actions_menu()
                    )
                    
                    logger.info(f"📊 Пользователь {user_id} выбрал компанию: {company.name}")
                else:
                    await update.callback_query.edit_message_text(
                        "❌ Компания не найдена или нет доступа.",
                        reply_markup=self.keyboards.get_back_inline_button()
                    )
        except Exception as e:
            logger.error(f"❌ Ошибка выбора компании: {e}")
            await update.callback_query.edit_message_text(
                "😔 Ошибка загрузки данных компании.",
                reply_markup=self.keyboards.get_back_inline_button()
            )
    
    async def _edit_company(self, update: Update, context: ContextTypes.DEFAULT_TYPE, company_id: str):
        """Редактирование компании"""
        if not update.callback_query:
            return
            
        await update.callback_query.edit_message_text(
            """✏️ РЕДАКТИРОВАНИЕ КОМПАНИИ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚧 Функция в разработке.

В следующих версиях вы сможете:
• Изменять данные компании
• Обновлять информацию о руководстве
• Корректировать сферу деятельности

🔙 Пока используйте создание нового профиля.""",
            parse_mode=None,
            reply_markup=self.keyboards.get_back_inline_button()
        )
    
    async def _delete_company(self, update: Update, context: ContextTypes.DEFAULT_TYPE, company_id: str):
        """Удаление компании"""
        if not update.callback_query:
            return
            
        await update.callback_query.edit_message_text(
            """🗑️ УДАЛЕНИЕ КОМПАНИИ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ Функция в разработке.

В следующих версиях вы сможете:
• Безопасно удалять профили компаний
• Подтверждать удаление
• Восстанавливать случайно удаленные

🔙 Пока профили сохраняются автоматически.""",
            parse_mode=None,
            reply_markup=self.keyboards.get_back_inline_button()
        )
    
    async def _offer_save_company_profile(self, update: Update, user_data, analysis_result: str):
        """Предложение сохранить профиль компании"""
        if not update.message or not user_data.company_name:
            return
            
        # Сохраняем данные компании в контексте для последующего использования
        if not update.effective_user:
            return
        user_id = update.effective_user.id
        context_data = {
            'company_name': user_data.company_name,
            'registration_date': user_data.registration_date.isoformat() if user_data.registration_date else None,
            'registration_place': user_data.registration_place,
            'business_sphere': getattr(user_data, 'business_sphere', None),
            'owner_name': getattr(user_data, 'owner_name', None),
            'owner_birth_date': user_data.owner_birth_date.isoformat() if getattr(user_data, 'owner_birth_date', None) else None,
            'director_name': getattr(user_data, 'director_name', None),
            'director_birth_date': user_data.director_birth_date.isoformat() if getattr(user_data, 'director_birth_date', None) else None
        }
        
        # Сохраняем в состоянии пользователя
        temp_user_data = self.state_manager.get_user_data(user_id)
        temp_user_data.temp_company_data = context_data
            
        # Проверяем, не сохранена ли уже эта компания
        try:
            from database.connection import db_manager
            from database.crud import CompanyCRUD
            
            with db_manager.get_session() as session:
                # Проверяем существование компании через список пользовательских компаний
                if not update.effective_user:
                    return
                user_companies = CompanyCRUD.get_companies_by_user(session, update.effective_user.id)
                existing_company = None
                for comp in user_companies:
                    comp_name = str(getattr(comp, 'name', ''))
                    if comp_name.lower() == user_data.company_name.lower():
                        existing_company = comp
                        break
                
                if existing_company:
                    # Компания уже сохранена, не предлагаем повторное сохранение
                    return
        except Exception as e:
            logger.warning(f"⚠️ Ошибка проверки существования компании: {e}")
        
        # Предлагаем сохранить новую компанию
        save_offer_text = f"""💾 СОХРАНИТЬ В "МОИ КОМПАНИИ"?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏢 Компания: {user_data.company_name}
📅 Дата: {user_data.registration_date.strftime('%d.%m.%Y') if user_data.registration_date else 'Не указана'}
🌍 Место: {user_data.registration_place or 'Не указано'}

💡 ПРЕИМУЩЕСТВА СОХРАНЕНИЯ:
✅ Быстрый доступ к данным компании
✅ Автоматическое заполнение при анализах
✅ История всех проведенных анализов
✅ Кэширование астрологических расчетов

Сохранить профиль компании?"""

        # Создаем inline клавиатуру для выбора
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💾 Сохранить профиль", callback_data=f"save_company_profile")],
            [InlineKeyboardButton("❌ Не сохранять", callback_data="skip_save_company")],
            [InlineKeyboardButton("🔙 К главному меню", callback_data="back_to_main")]
        ])
        
        await update.message.reply_text(
            save_offer_text,
            parse_mode=None,
            reply_markup=keyboard
        )
    
    async def _save_company_profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сохранение профиля компании"""
        if not update.callback_query or not update.effective_user:
            return
            
        user_id = update.effective_user.id
        user_data = self.state_manager.get_user_data(user_id)
        
        # Получаем сохраненные данные компании
        temp_data = getattr(user_data, 'temp_company_data', None)
        
        # Логируем данные для диагностики
        logger.info(f"🔍 Попытка сохранения: temp_data={temp_data is not None}")
        
        if not temp_data:
            await update.callback_query.edit_message_text(
                "❌ Данные компании не найдены. Попробуйте провести анализ заново.",
                reply_markup=self.keyboards.get_back_inline_button()
            )
            return
        
        try:
            from database.connection import db_manager
            from database.crud import CompanyCRUD
            from datetime import datetime
            
            with db_manager.get_session() as session:
                # Восстанавливаем данные из контекста
                company_name = temp_data.get('company_name')
                reg_date_str = temp_data.get('registration_date')
                
                if not company_name or not reg_date_str:
                    raise ValueError("Недостаточно данных для сохранения компании")
                
                # Конвертируем дату обратно
                registration_date = datetime.fromisoformat(reg_date_str)
                owner_birth_date = None
                director_birth_date = None
                
                if temp_data.get('owner_birth_date'):
                    owner_birth_date = datetime.fromisoformat(temp_data['owner_birth_date'])
                if temp_data.get('director_birth_date'):
                    director_birth_date = datetime.fromisoformat(temp_data['director_birth_date'])
                
                saved_company = CompanyCRUD.create_company(
                    session=session,
                    owner_id=user_id,
                    name=company_name,
                    registration_date=registration_date,
                    registration_place=temp_data.get('registration_place') or "Не указано",
                    industry=temp_data.get('business_sphere'),
                    owner_name=temp_data.get('owner_name'),
                    owner_birth_date=owner_birth_date,
                    director_name=temp_data.get('director_name'),
                    director_birth_date=director_birth_date
                )
                
                await update.callback_query.edit_message_text(
                    f"""✅ ПРОФИЛЬ СОХРАНЕН
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏢 Компания "{company_name}" успешно добавлена в "Мои компании"!

💡 Теперь вы можете:
• Быстро выбирать эту компанию для анализов
• Использовать сохраненные данные
• Просматривать историю анализов

🔮 Для нового анализа используйте главное меню или выберите компанию в разделе "🏢 Мои компании".""",
                    parse_mode=None,
                    reply_markup=self.keyboards.get_back_inline_button()
                )
                
                logger.info(f"💾 Профиль компании {company_name} сохранен для пользователя {user_id}")
                
                # Очищаем временные данные
                user_data.temp_company_data = None
                
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения профиля компании: {e}")
            await update.callback_query.edit_message_text(
                "😔 Ошибка сохранения профиля компании. Попробуйте позже.",
                reply_markup=self.keyboards.get_back_inline_button()
            )
    
    async def _skip_save_company(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Пропуск сохранения профиля компании"""
        if not update.callback_query:
            return
            
        await update.callback_query.edit_message_text(
            """✅ АНАЛИЗ ЗАВЕРШЕН
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Анализ компании выполнен успешно!

💡 Профиль компании не сохранен. Вы можете создать его позже через раздел "🏢 Мои компании".

🔮 Для нового анализа используйте главное меню.""",
            parse_mode=None,
            reply_markup=self.keyboards.get_back_inline_button()
        )
    
    # Обработчики для создания профиля компании
    async def _handle_profile_company_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка названия компании для профиля"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        user_data = self.state_manager.get_user_data(user_id)
        
        cleaned_name = clean_company_name(text.strip())
        user_data.company_name = cleaned_name
        
        await update.message.reply_text(
            f"✅ Название: {cleaned_name}\n\n📅 Введите дату регистрации в формате ДД.ММ.ГГГГ:",
            parse_mode=None
        )
        
        self.state_manager.set_state(user_id, BotState.PROFILE_REG_DATE)
    
    async def _handle_profile_reg_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка даты регистрации для профиля"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        user_data = self.state_manager.get_user_data(user_id)
        
        reg_date = validate_date(text.strip())
        if not reg_date:
            await update.message.reply_text(
                "❌ Неверный формат даты. Введите в формате ДД.ММ.ГГГГ"
            )
            return
        
        user_data.registration_date = reg_date
        
        await update.message.reply_text(
            f"✅ Дата: {reg_date.strftime('%d.%m.%Y')}\n\n🏙️ Введите город регистрации:",
            parse_mode=None
        )
        
        self.state_manager.set_state(user_id, BotState.PROFILE_REG_PLACE)
    
    async def _handle_profile_reg_place(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка места регистрации для профиля"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        user_data = self.state_manager.get_user_data(user_id)
        
        user_data.registration_place = text.strip()
        
        await update.message.reply_text(
            f"✅ Место: {text.strip()}\n\n🏭 Выберите сферу деятельности:",
            parse_mode=None,
            reply_markup=self.keyboards.get_business_spheres()
        )
        
        self.state_manager.set_state(user_id, BotState.PROFILE_SPHERE)
    
    async def _save_company_profile_direct(self, update: Update, user_data):
        """Прямое сохранение профиля компании"""
        if not update.effective_user or not update.message:
            return
            
        user_id = update.effective_user.id
        
        try:
            from database.connection import db_manager
            from database.crud import CompanyCRUD
            
            # Проверяем обязательные поля
            if not user_data.company_name or not user_data.registration_date:
                await update.message.reply_text(
                    "❌ Недостаточно данных. Необходимы название и дата регистрации.",
                    reply_markup=self.keyboards.get_main_menu()
                )
                return
            
            with db_manager.get_session() as session:
                saved_company = CompanyCRUD.create_company(
                    session=session,
                    owner_id=user_id,
                    name=user_data.company_name,
                    registration_date=user_data.registration_date,
                    registration_place=user_data.registration_place or "Не указано",
                    industry=user_data.business_sphere,
                    owner_name=user_data.owner_name,
                    owner_birth_date=user_data.owner_birth_date,
                    director_name=user_data.director_name,
                    director_birth_date=user_data.director_birth_date
                )
                
                await update.message.reply_text(
                    f"""✅ ПРОФИЛЬ КОМПАНИИ СОЗДАН
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏢 Компания "{user_data.company_name}" успешно сохранена!

💡 Теперь вы можете:
🔮 Быстро выбирать для анализов
📊 Использовать сохраненные данные  
📈 Получать персонализированные прогнозы

🔙 Используйте главное меню для анализов.""",
                    parse_mode=None,
                    reply_markup=self.keyboards.get_main_menu()
                )
                
                logger.info(f"💾 Профиль компании {user_data.company_name} создан пользователем {user_id}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка создания профиля: {e}")
            await update.message.reply_text(
                "😔 Ошибка создания профиля компании. Попробуйте позже.",
                reply_markup=self.keyboards.get_main_menu()
            )
        
        # Сбрасываем состояние
        self.state_manager.reset_user(user_id)
    
    async def _handle_profile_sphere_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Обработка выбора сферы для профиля компании"""
        if not update.effective_user or not update.callback_query:
            return
        user_id = update.effective_user.id
        user_data = self.state_manager.get_user_data(user_id)
        
        sphere_map = {
            "sphere_construction": "Строительство и промышленность",
            "sphere_finance": "Финансы и инвестиции",
            "sphere_trade": "Торговля и сфера услуг", 
            "sphere_tech": "Технологии и телекоммуникации",
            "sphere_government": "Государственный сектор и социальная сфера",
            "sphere_energy": "Энергетика"
        }
        
        selected_sphere = sphere_map.get(callback_data, "Неизвестно")
        user_data.business_sphere = selected_sphere
        
        await update.callback_query.edit_message_text(
            f"""✅ Сфера: {selected_sphere}

👤 Введите имя собственника компании:

💡 Эти данные помогут создать более точные прогнозы.""",
            parse_mode=None,
            reply_markup=self.keyboards.get_skip_optional()
        )
        
        self.state_manager.set_state(user_id, BotState.PROFILE_OWNER_NAME)
    
    async def _handle_profile_owner_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка имени владельца для профиля"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        user_data = self.state_manager.get_user_data(user_id)
        
        user_data.owner_name = text.strip()
        
        await update.message.reply_text(
            f"✅ Владелец: {text}\n\n📅 Введите дату рождения владельца в формате ДД.ММ.ГГГГ:",
            parse_mode=None,
            reply_markup=self.keyboards.get_skip_optional()
        )
        
        self.state_manager.set_state(user_id, BotState.PROFILE_OWNER_BIRTH)
    
    async def _handle_profile_owner_birth(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка даты рождения владельца для профиля"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        user_data = self.state_manager.get_user_data(user_id)
        
        birth_date = validate_date(text.strip())
        if not birth_date:
            await update.message.reply_text(
                "❌ Неверный формат даты. Введите в формате ДД.ММ.ГГГГ"
            )
            return
        
        user_data.owner_birth_date = birth_date
        
        await update.message.reply_text(
            "✅ Дата рождения владельца сохранена\n\n👔 Введите имя директора компании:",
            parse_mode=None,
            reply_markup=self.keyboards.get_skip_optional()
        )
        
        self.state_manager.set_state(user_id, BotState.PROFILE_DIRECTOR_NAME)
    
    async def _handle_profile_director_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка имени директора для профиля"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        user_data = self.state_manager.get_user_data(user_id)
        
        user_data.director_name = text.strip()
        
        await update.message.reply_text(
            f"✅ Директор: {text}\n\n📅 Введите дату рождения директора в формате ДД.ММ.ГГГГ:",
            parse_mode=None,
            reply_markup=self.keyboards.get_skip_optional()
        )
        
        self.state_manager.set_state(user_id, BotState.PROFILE_DIRECTOR_BIRTH)
    
    async def _handle_profile_director_birth(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка даты рождения директора и завершение создания профиля"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        user_data = self.state_manager.get_user_data(user_id)
        
        birth_date = validate_date(text.strip())
        if not birth_date:
            await update.message.reply_text(
                "❌ Неверный формат даты. Введите в формате ДД.ММ.ГГГГ"
            )
            return
        
        user_data.director_birth_date = birth_date
        
        # Сохраняем профиль компании
        await self._save_company_profile_direct(update, user_data)

    async def _auto_save_company_profile(self, update: Update, user_data):
        """Автоматическое сохранение компании в профиль пользователя"""
        if not update.effective_user or not update.message:
            return
            
        user_id = update.effective_user.id
        
        try:
            from database.connection import db_manager
            from database.crud import CompanyCRUD
            
            # Проверяем, есть ли уже такая компания у пользователя
            with db_manager.get_session() as session:
                existing_companies = CompanyCRUD.get_companies_by_user(session, user_id)
                
                # Проверяем по названию и дате регистрации
                company_exists = False
                for company in existing_companies:
                    if (company.name == user_data.company_name and 
                        company.registration_date == user_data.registration_date):
                        company_exists = True
                        break
                
                if not company_exists and user_data.company_name and user_data.registration_date:
                    # Создаем новую компанию
                    saved_company = CompanyCRUD.create_company(
                        session=session,
                        owner_id=user_id,
                        name=user_data.company_name,
                        registration_date=user_data.registration_date,
                        registration_place=user_data.registration_place or "Не указано",
                        industry=user_data.business_sphere,
                        owner_name=user_data.owner_name,
                        owner_birth_date=user_data.owner_birth_date,
                        director_name=user_data.director_name,
                        director_birth_date=user_data.director_birth_date
                    )
                    
                    logger.info(f"💾 Компания {user_data.company_name} автоматически сохранена для пользователя {user_id}")
                    
                    # Уведомляем пользователя
                    await update.message.reply_text(
                        f"💾 Компания <b>{user_data.company_name}</b> автоматически сохранена в ваш профиль!",
                        parse_mode='HTML',
                        reply_markup=self.keyboards.get_main_menu()
                    )
                else:
                    logger.info(f"💾 Компания {user_data.company_name} уже существует в профиле пользователя {user_id}")
                    
        except Exception as e:
            logger.warning(f"⚠️ Ошибка автоматического сохранения компании: {e}")
            # Не показываем ошибку пользователю, чтобы не прерывать основной функционал

    def _clean_html_tags(self, text: str) -> str:
        """Очистка HTML-тегов и замена на правильное форматирование для Telegram"""
        import re
        
        # Заменяем ненужные HTML-теги, но сохраняем нужные для Telegram
        text = re.sub(r'<p>(.*?)</p>', r'\1', text, flags=re.DOTALL)    # Убираем параграфы
        text = re.sub(r'<h[1-6]>(.*?)</h[1-6]>', r'<b>\1</b>', text, flags=re.DOTALL)  # h1-h6 → жирный
        text = re.sub(r'<strong>(.*?)</strong>', r'<b>\1</b>', text, flags=re.DOTALL)  # strong → жирный
        text = re.sub(r'<em>(.*?)</em>', r'<i>\1</i>', text, flags=re.DOTALL)  # em → курсив
        # Оставляем <b> и <i> для Telegram
        text = re.sub(r'<ul>', '', text)               # Убираем списки
        text = re.sub(r'</ul>', '', text)
        text = re.sub(r'<ol>', '', text)               # Убираем нумерованные списки
        text = re.sub(r'</ol>', '', text)
        text = re.sub(r'<li>', '• ', text)             # Заменяем li на эмодзи
        text = re.sub(r'</li>', '', text)
        text = re.sub(r'<hr>', '\n', text)             # Заменяем hr на перенос
        text = re.sub(r'<hr/>', '\n', text)
        text = re.sub(r'<br>', '\n', text)             # Заменяем br на перенос
        text = re.sub(r'<br/>', '\n', text)
        text = re.sub(r'<div>(.*?)</div>', r'\1', text, flags=re.DOTALL)  # Убираем div
        
        # Очищаем только ненужные теги (сохраняем <b> и <i> для Telegram)
        text = re.sub(r'<(?!/?[bi]>)[^>]+>', '', text)
        
        # Убираем символы # и заменяем на эмодзи
        text = re.sub(r'^#{1,6}\s*(.+)$', r'🌟 \1', text, flags=re.MULTILINE)
        text = re.sub(r'###\s*(.+)', r'💎 \1', text)
        text = re.sub(r'##\s*(.+)', r'🚀 \1', text)
        text = re.sub(r'#\s*(.+)', r'⭐ \1', text)
        
        # Убираем разделители
        text = re.sub(r'^---+$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^===+$', '', text, flags=re.MULTILINE)
        
        # Заменяем буллеты на графические иконки
        text = re.sub(r'^\s*\*\s+', '⭐ ', text, flags=re.MULTILINE)     # * в начале строки на ⭐
        text = re.sub(r'^\s*-\s+', '💫 ', text, flags=re.MULTILINE)      # - в начале строки на 💫
        text = re.sub(r'^\s*•\s+', '🎯 ', text, flags=re.MULTILINE)      # • в начале строки на 🎯
        
        # Делаем заголовки жирными (строки с эмодзи в начале)
        text = re.sub(r'^(🌟.*?)$', r'<b>\1</b>', text, flags=re.MULTILINE)  # 🌟 заголовки жирным
        text = re.sub(r'^(💎.*?)$', r'<b>\1</b>', text, flags=re.MULTILINE)  # 💎 заголовки жирным
        text = re.sub(r'^(🚀.*?)$', r'<b>\1</b>', text, flags=re.MULTILINE)  # 🚀 заголовки жирным
        text = re.sub(r'^(⚠️.*?)$', r'<b>\1</b>', text, flags=re.MULTILINE)  # ⚠️ заголовки жирным
        text = re.sub(r'^(💰.*?)$', r'<b>\1</b>', text, flags=re.MULTILINE)  # 💰 заголовки жирным
        text = re.sub(r'^(🤝.*?)$', r'<b>\1</b>', text, flags=re.MULTILINE)  # 🤝 заголовки жирным
        text = re.sub(r'^(💼.*?)$', r'<b>\1</b>', text, flags=re.MULTILINE)  # 💼 заголовки жирным
        text = re.sub(r'^(✨.*?)$', r'<b>\1</b>', text, flags=re.MULTILINE)  # ✨ заголовки жирным
        
        # Добавляем пустые строки после каждого смыслового блока для лучшей читаемости
        text = re.sub(r'(🌟.*?)(\n(?=[🌟💎🚀⚠️📈🔮💼🎯💡✨]))', r'\1\n\n\2', text)  # После заголовков с эмодзи
        text = re.sub(r'(\.\s*)(\n🌟)', r'\1\n\2', text)  # После предложений перед заголовками
        text = re.sub(r'(\.\s*)(\n💎)', r'\1\n\2', text)  # После предложений перед блоками
        text = re.sub(r'(\.\s*)(\n🚀)', r'\1\n\2', text)  # После предложений перед блоками
        text = re.sub(r'(\.\s*)(\n⚠️)', r'\1\n\2', text)  # После предложений перед блоками
        text = re.sub(r'(\.\s*)(\n📈)', r'\1\n\2', text)  # После предложений перед блоками
        text = re.sub(r'(\.\s*)(\n🔮)', r'\1\n\2', text)  # После предложений перед блоками
        text = re.sub(r'(\.\s*)(\n💼)', r'\1\n\2', text)  # После предложений перед блоками
        
        # Очищаем лишние пробелы и переносы
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Убираем множественные переносы
        text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)  # Убираем отступы в начале строк
        text = re.sub(r'\s+$', '', text, flags=re.MULTILINE)  # Убираем пробелы в конце строк
        
        return text.strip()

    async def _auto_save_analysis(self, user_id: int, company_data: dict, analysis_type: str, analysis_result: str):
        """Автоматическое сохранение анализа в Qdrant и БД"""
        saved_to_qdrant = False
        saved_to_db = False
        
        # Проверяем, что analysis_type не None
        if not analysis_type:
            analysis_type = "unknown"
        
        # Сохранение в Qdrant
        if self.qdrant_client and company_data:
            try:
                await self.qdrant_client.save_astro_result(
                    user_id=user_id,
                    company_name=company_data.get('name', ''),
                    analysis_type=analysis_type,
                    result=analysis_result
                )
                saved_to_qdrant = True
                logger.info(f"💾 Анализ {analysis_type} автоматически сохранен в Qdrant для пользователя {user_id}")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка автосохранения в Qdrant: {e}")
        
        # Сохранение в базу данных
        try:
            from database.connection import db_manager
            from database.crud import AnalysisCRUD, UserCRUD
            
            with db_manager.get_session() as session:
                user_db = UserCRUD.get_user_by_telegram_id(session, user_id)
                if user_db and company_data:
                    # Создаем запись анализа
                    db_user_id = getattr(user_db, 'id', 0)
                    AnalysisCRUD.create_analysis(
                        session=session,
                        user_id=int(db_user_id),
                        analysis_type=f"{analysis_type}_company",
                        result_text=analysis_result,
                        input_data={
                            'company_id': company_data.get('id', 0),
                            'company_name': company_data.get('name', ''),
                            'analysis_timestamp': datetime.now().isoformat()
                        },
                        zodiac_signs=[],
                        news_used=True,
                        numerology_used=True,
                        astrology_api_used=True
                    )
                    saved_to_db = True
                    logger.info(f"💾 Анализ {analysis_type} автоматически сохранен в БД для пользователя {user_id}")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка автосохранения в БД: {e}")
        
        return saved_to_qdrant, saved_to_db

    def _split_long_text(self, text: str, max_length: int = 3500) -> list:
        """Разбивает длинный текст на части для Telegram"""
        import re
        
        if len(text) <= max_length:
            return [text]
        
        parts = []
        current_part = ""
        
        # Сначала разбиваем по разделам (строки с эмодзи)
        sections = re.split(r'(\n(?=🌟|💎|🚀|⚠️|📈|🔮|🏛️|💼))', text)
        
        for section in sections:
            if not section.strip():
                continue
                
            # Если секция помещается в текущую часть
            if len(current_part + section) <= max_length:
                current_part += section
            else:
                # Сохраняем текущую часть
                if current_part.strip():
                    parts.append(current_part.strip())
                
                # Если секция слишком длинная, разбиваем по предложениям
                if len(section) > max_length:
                    sentences = section.split('. ')
                    temp_part = ""
                    
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if not sentence.endswith('.') and sentence:
                            sentence += '. '
                        
                        if len(temp_part + sentence) <= max_length:
                            temp_part += sentence
                        else:
                            if temp_part.strip():
                                parts.append(temp_part.strip())
                            temp_part = sentence
                    
                    current_part = temp_part
                else:
                    current_part = section
        
        # Добавляем последнюю часть
        if current_part.strip():
            parts.append(current_part.strip())
        
        return parts if parts else [text]

    async def _show_next_analysis_part(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показ следующей части анализа"""
        if not update.callback_query or not update.effective_user:
            return
            
        user_id = update.effective_user.id
        user_data = context.user_data
        
        if not user_data or 'analysis_parts' not in user_data:
            await update.callback_query.edit_message_text(
                "❌ Данные анализа не найдены.",
                reply_markup=self.keyboards.get_back_inline_button()
            )
            return
        
        current_index = user_data.get('current_part_index', 1)
        total_parts = user_data.get('total_parts', 1)
        analysis_type = user_data.get('analysis_type', 'unknown')
        parts = user_data['analysis_parts']
        
        if current_index >= total_parts or not parts:
            await update.callback_query.edit_message_text(
                "❌ Больше частей анализа нет.",
                reply_markup=self.keyboards.get_back_inline_button()
            )
            return
        
        # Показываем все части до текущей включительно (накопленный текст)
        accumulated_text = "\n\n".join(parts[:current_index])
        
        # Определяем заголовок в зависимости от типа анализа
        if analysis_type == 'zodiac':
            header = "<b>🔮 АНАЛИЗ ЗНАКА ЗОДИАКА КОМПАНИИ</b>\n\n"
        elif analysis_type == 'forecast':
            header = "<b>📈 БИЗНЕС-ПРОГНОЗ КОМПАНИИ</b>\n\n"
        elif analysis_type == 'compatibility':
            header = "<b>🤝 АНАЛИЗ СОВМЕСТИМОСТИ КОМПАНИИ</b>\n\n"
        else:
            header = "<b>📊 АНАЛИЗ КОМПАНИИ</b>\n\n"
        
        # Формируем клавиатуру
        keyboard = []
        
        if current_index < total_parts - 1:
            # Есть еще части
            keyboard.append([InlineKeyboardButton("📄 Следующая часть", callback_data=f"next_part_{current_index + 1}")])
        # Последняя часть - просто кнопка назад
        
        keyboard.append([InlineKeyboardButton("🔙 К действиям с компанией", callback_data="back_to_company_actions")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Показываем накопленный текст
        await update.callback_query.edit_message_text(
            f"{header}{accumulated_text}\n\n📄 Показано {current_index} из {total_parts} частей",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        
        # Обновляем индекс
        user_data['current_part_index'] = current_index + 1

    async def _handle_company_zodiac_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка анализа знака зодиака компании"""
        if not update.callback_query or not update.effective_user:
            return
            
        user_id = update.effective_user.id
        query = update.callback_query
        
        try:
            # Получаем данные компании из context.user_data (сохраненные при выборе)
            company_data = None
            if context.user_data and 'selected_company' in context.user_data:
                company_data = context.user_data['selected_company']
            
            if not company_data:
                await query.edit_message_text(
                    "❌ Данные компании не найдены. Выберите компанию заново.",
                    reply_markup=self.keyboards.get_back_inline_button()
                )
                return
            
            # Показываем сообщение о начале анализа
            await query.edit_message_text(
                "🔮 Анализирую знак зодиака компании...\n⏳ Это может занять несколько секунд.",
                parse_mode=None
            )
            
            # Получаем новости по трем блокам согласно ТЗ
            news_data = ""
            if self.news_analyzer:
                try:
                    # Политические новости
                    political_news = await self.news_analyzer.news_client.get_politics_news(limit=3)
                    politics_summary = "🏛️ ПОЛИТИКА:\n"
                    if political_news:
                        for i, article in enumerate(political_news[:3], 1):
                            title = article.get('title', '')[:80]
                            politics_summary += f"{i}. {title}...\n"
                    
                    # Экономические новости
                    business_news = await self.news_analyzer.news_client.get_business_news(limit=3)
                    economy_summary = "\n💼 ЭКОНОМИКА:\n"
                    if business_news:
                        # Обрабатываем как список или как dict с results
                        news_list = business_news if isinstance(business_news, list) else business_news.get('results', [])
                        for i, article in enumerate(news_list[:3], 1):
                            title = article.get('title', '')[:80]
                            economy_summary += f"{i}. {title}...\n"
                    
                    # Новости фондовой биржи
                    stock_news = await self.news_analyzer.news_client.get_stock_market_news(limit=3)
                    stock_summary = "\n📈 ФОНДОВАЯ БИРЖА:\n"
                    if stock_news:
                        # Обрабатываем как список или как dict с results
                        news_list = stock_news if isinstance(stock_news, list) else stock_news.get('results', [])
                        for i, article in enumerate(news_list[:3], 1):
                            title = article.get('title', '')[:80]
                            if any(word in title.lower() for word in ['акци', 'биржа', 'инвест', 'рынок']):
                                stock_summary += f"{i}. {title}...\n"
                    
                    news_data = politics_summary + economy_summary + stock_summary
                    
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось получить новости: {e}")
            else:
                logger.warning("⚠️ NewsAnalyzer недоступен")
            
            # Выполняем анализ
            try:
                analysis_result = await self.astro_agent.analyze_company_zodiac(
                    company_info=company_data,
                    news_data=news_data
                )
            except Exception as e:
                logger.error(f"❌ Критическая ошибка анализа: {e}")
                await query.edit_message_text(
                    f"❌ Произошла ошибка при анализе знака зодиака:\n\n{str(e)}\n\nПожалуйста, попробуйте позже или обратитесь к администратору.",
                    reply_markup=self.keyboards.get_back_inline_button()
                )
                return
            
            # Валидируем и исправляем текст
            logger.info(f"📝 НАЧАЛО ВАЛИДАЦИИ: Анализ готов ({len(analysis_result)} символов)")
            logger.info(f"📋 Первые 200 символов: {analysis_result[:200]}...")
            
            if self.validator:
                try:
                    # Получаем оригинальный промпт для валидации
                    from ai_astrologist.prompts import COMPANY_ZODIAC_PROMPT
                    original_prompt = COMPANY_ZODIAC_PROMPT
                    logger.info("🔍 ЗАПУСКАЕМ ANTHROPIC ВАЛИДАЦИЮ...")
                    logger.info("🎯 Цель: минимум 7 баллов из 10")
                    
                    # Отправляем пользователю уведомление о начале валидации
                    await update.callback_query.edit_message_text(
                        "🔍 **ВАЛИДАЦИЯ КАЧЕСТВА ТЕКСТА**\n\n"
                        "🤖 Anthropic Claude анализирует сгенерированный текст...\n"
                        "🎯 Цель: достичь оценки 10/10\n"
                        "⏳ Пожалуйста, подождите...",
                        reply_markup=None,
                        parse_mode='HTML'
                    )
                    
                    # Создаем callback для обновления статуса валидации
                    async def validation_update_callback(message):
                        try:
                            if update.callback_query:
                                await update.callback_query.edit_message_text(
                                    message,
                                    parse_mode='HTML',
                                    reply_markup=None
                                )
                        except:
                            pass  # Игнорируем ошибки обновления
                    
                    # Запускаем валидацию с callback для отображения оценок
                    if hasattr(self.validator, 'claude_agent') and self.validator.claude_agent:
                        improved_text, final_score = await self.validator.claude_agent.claude_validator.iterative_refinement(
                            text=analysis_result,
                            original_prompt=original_prompt,
                            analysis_type="zodiac",
                            target_score=10.0,
                            max_iterations=7,
                            update_callback=validation_update_callback
                        )
                        validated_result = improved_text
                    else:
                        validated_result = await self.validator.validate_and_fix(analysis_result, "zodiac", original_prompt)
                    
                    logger.info("✅ ВАЛИДАЦИЯ ЗАВЕРШЕНА: (%d символов)", len(validated_result))
                    logger.info("📋 Результат валидации (первые 200): %s...", validated_result[:200])
                    
                    if validated_result and len(validated_result.strip()) > 100:
                        analysis_result = validated_result
                        logger.info("🔄 Результат валидации принят")
                    else:
                        logger.warning("⚠️ Результат валидации пустой, используем оригинал")
                        
                except Exception as e:
                    logger.error(f"❌ КРИТИЧЕСКАЯ ошибка валидации: {e}")
                    logger.info("🔧 Используем результат без валидации")
            else:
                logger.warning("⚠️ Валидатор недоступен")
            
            # Очищаем HTML-теги
            analysis_result = self._clean_html_tags(analysis_result)
            logger.info(f"🧹 HTML очистка завершена ({len(analysis_result)} символов)")
            
            # Проверяем что результат не пустой
            if not analysis_result or len(analysis_result.strip()) < 50:
                logger.error(f"❌ Результат анализа пустой или слишком короткий: {len(analysis_result) if analysis_result else 0}")
                await query.edit_message_text(
                    "❌ Произошла ошибка при обработке анализа. Результат получился пустым.\n\nПожалуйста, попробуйте еще раз.",
                    reply_markup=self.keyboards.get_back_inline_button()
                )
                return
            
            # Автоматически сохраняем анализ
            await self._auto_save_analysis(user_id, company_data, "zodiac", analysis_result)
            
            # Разбиваем длинный текст на части
            text_parts = self._split_long_text(analysis_result)
            
            if len(text_parts) == 1:
                # Короткий текст - отправляем как есть
                await query.edit_message_text(
                    f"<b>🔮 АНАЛИЗ ЗНАКА ЗОДИАКА КОМПАНИИ</b>\n\n{analysis_result}",
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 К действиям с компанией", callback_data="back_to_company_actions")]])
                )
            else:
                # Длинный текст - разбиваем на части
                # Проверяем, что context.user_data существует
                if context.user_data is not None:
                    context.user_data.update({
                        'analysis_parts': text_parts,
                        'total_parts': len(text_parts),
                        'current_part_index': 1,
                        'analysis_type': 'zodiac',
                        'last_analysis_result': analysis_result,
                        'last_analysis_type': 'zodiac'
                    })
                else:
                    logger.warning("⚠️ context.user_data is None, данные анализа не сохранены")
                
                # Показываем первую часть
                first_part = text_parts[0]
                keyboard = []
                
                if len(text_parts) > 1:
                    keyboard.append([InlineKeyboardButton("📄 Следующая часть", callback_data="next_part_2")])
                

                keyboard.append([InlineKeyboardButton("🔙 К действиям с компанией", callback_data="back_to_company_actions")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"<b>🔮 АНАЛИЗ ЗНАКА ЗОДИАКА КОМПАНИИ</b>\n\n{first_part}\n\n📄 Показано 1 из {len(text_parts)} частей",
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            logger.error(f"❌ Ошибка анализа знака зодиака компании: {e}")
            await query.edit_message_text(
                f"❌ Ошибка при анализе: {str(e)}",
                reply_markup=self.keyboards.get_back_inline_button()
            )

    async def _handle_company_business_forecast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка бизнес-прогноза компании"""
        if not update.callback_query or not update.effective_user:
            return
            
        user_id = update.effective_user.id
        query = update.callback_query
        
        try:
            # Получаем данные компании из context.user_data (сохраненные при выборе)
            company_data = None
            if context.user_data and 'selected_company' in context.user_data:
                company_data = context.user_data['selected_company']
            
            if not company_data:
                await query.edit_message_text(
                    "❌ Данные компании не найдены. Выберите компанию заново.",
                    reply_markup=self.keyboards.get_back_inline_button()
                )
                return
            
            # Показываем сообщение о начале анализа
            await query.edit_message_text(
                "📈 Составляю бизнес-прогноз компании...\n⏳ Это может занять несколько секунд.",
                parse_mode=None
            )
            
            # Получаем новости для компании
            news_data = ""
            try:
                if self.news_analyzer and company_data and company_data.get('business_sphere'):
                    news_analysis = await self.news_analyzer.analyze_news_for_company(
                        company_sphere=company_data.get('business_sphere', ''),
                        days_back=7
                    )
                    # Преобразуем результат анализа в строку
                    if isinstance(news_analysis, dict) and 'summary' in news_analysis:
                        news_data = str(news_analysis['summary'])
                    else:
                        news_data = str(news_analysis)
            except Exception as e:
                logger.warning(f"⚠️ Не удалось получить новости: {e}")
            
            # Выполняем прогноз
            try:
                forecast_result = await self.astro_agent.generate_business_forecast(
                    company_data=company_data,
                    astrology_data="",
                    news_data=news_data
                )
            except Exception as e:
                logger.error(f"❌ Критическая ошибка прогноза: {e}")
                await query.edit_message_text(
                    f"❌ Произошла ошибка при генерации бизнес-прогноза:\n\n{str(e)}\n\nПожалуйста, попробуйте позже или обратитесь к администратору.",
                    reply_markup=self.keyboards.get_back_inline_button()
                )
                return
            
            # Валидируем и исправляем текст
            if self.validator:
                try:
                    from ai_astrologist.prompts import BUSINESS_FORECAST_PROMPT
                    original_prompt = BUSINESS_FORECAST_PROMPT
                    forecast_result = await self.validator.validate_and_fix(forecast_result, "forecast", original_prompt)
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка валидации: {e}. Используем результат без валидации.")
            
            # Очищаем HTML-теги
            forecast_result = self._clean_html_tags(forecast_result)
            
            # Автоматически сохраняем анализ
            await self._auto_save_analysis(user_id, company_data, "forecast", forecast_result)
            
            # Разбиваем длинный текст на части
            text_parts = self._split_long_text(forecast_result)
            
            if len(text_parts) == 1:
                # Короткий текст - отправляем как есть
                await query.edit_message_text(
                    f"<b>📈 БИЗНЕС-ПРОГНОЗ КОМПАНИИ</b>\n\n{forecast_result}",
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 К действиям с компанией", callback_data="back_to_company_actions")]])
                )
            else:
                # Длинный текст - разбиваем на части
                # Проверяем, что context.user_data существует
                if context.user_data is not None:
                    context.user_data.update({
                        'analysis_parts': text_parts,
                        'total_parts': len(text_parts),
                        'current_part_index': 1,
                        'analysis_type': 'forecast',
                        'last_analysis_result': forecast_result,
                        'last_analysis_type': 'forecast'
                    })
                else:
                    logger.warning("⚠️ context.user_data is None, данные анализа не сохранены")
                
                # Показываем первую часть
                first_part = text_parts[0]
                keyboard = []
                
                if len(text_parts) > 1:
                    keyboard.append([InlineKeyboardButton("📄 Следующая часть", callback_data="next_part_2")])
                

                keyboard.append([InlineKeyboardButton("🔙 К действиям с компанией", callback_data="back_to_company_actions")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"<b>📈 БИЗНЕС-ПРОГНОЗ КОМПАНИИ</b>\n\n{first_part}\n\n📄 Показано 1 из {len(text_parts)} частей",
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            logger.error(f"❌ Ошибка бизнес-прогноза компании: {e}")
            await query.edit_message_text(
                f"❌ Ошибка при составлении прогноза: {str(e)}",
                reply_markup=self.keyboards.get_back_inline_button()
            )

    async def _handle_company_compatibility_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка анализа совместимости компании"""
        if not update.callback_query or not update.effective_user:
            return
            
        user_id = update.effective_user.id
        query = update.callback_query
        
        try:
            # Получаем данные компании из context.user_data (сохраненные при выборе)
            company_data = None
            if context.user_data and 'selected_company' in context.user_data:
                company_data = context.user_data['selected_company']
            
            if not company_data:
                await query.edit_message_text(
                    "❌ Данные компании не найдены. Выберите компанию заново.",
                    reply_markup=self.keyboards.get_back_inline_button()
                )
                return
            
            # Показываем сообщение о начале анализа
            await query.edit_message_text(
                "🤝 Анализирую совместимость компании...\n⏳ Это может занять несколько секунд.",
                parse_mode=None
            )
            
            # Для анализа совместимости нужен второй объект
            # Пока что используем базовый анализ
            compatibility_result = await self.astro_agent.analyze_compatibility(
                company_data=company_data,
                object_data={"type": "general"},
                object_type="general"
            )
            
            # Валидируем и исправляем текст
            if self.validator:
                # Используем базовый промпт для анализа совместимости
                original_prompt = "Проанализируй совместимость компании с учетом астрологических факторов и дай практические рекомендации"
                compatibility_result = await self.validator.validate_and_fix(compatibility_result, "compatibility", original_prompt)
            
            # Очищаем HTML-теги
            compatibility_result = self._clean_html_tags(compatibility_result)
            
            # Автоматически сохраняем анализ
            await self._auto_save_analysis(user_id, company_data, "compatibility", compatibility_result)
            
            # Разбиваем длинный текст на части
            text_parts = self._split_long_text(compatibility_result)
            
            if len(text_parts) == 1:
                # Короткий текст - отправляем как есть
                await query.edit_message_text(
                    f"<b>🤝 АНАЛИЗ СОВМЕСТИМОСТИ КОМПАНИИ</b>\n\n{compatibility_result}",
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 К действиям с компанией", callback_data="back_to_company_actions")]])
                )
            else:
                # Длинный текст - разбиваем на части
                # Проверяем, что context.user_data существует
                if context.user_data is not None:
                    context.user_data.update({
                        'analysis_parts': text_parts,
                        'total_parts': len(text_parts),
                        'current_part_index': 1,
                        'analysis_type': 'compatibility',
                        'last_analysis_result': compatibility_result,
                        'last_analysis_type': 'compatibility'
                    })
                else:
                    logger.warning("⚠️ context.user_data is None, данные анализа не сохранены")
                
                # Показываем первую часть
                first_part = text_parts[0]
                keyboard = []
                
                if len(text_parts) > 1:
                    keyboard.append([InlineKeyboardButton("📄 Следующая часть", callback_data="next_part_2")])
                

                keyboard.append([InlineKeyboardButton("🔙 К действиям с компанией", callback_data="back_to_company_actions")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"<b>🤝 АНАЛИЗ СОВМЕСТИМОСТИ КОМПАНИИ</b>\n\n{first_part}\n\n📄 Показано 1 из {len(text_parts)} частей",
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            logger.error(f"❌ Ошибка анализа совместимости компании: {e}")
            await query.edit_message_text(
                f"❌ Ошибка при анализе совместимости: {str(e)}",
                reply_markup=self.keyboards.get_back_inline_button()
            )



    async def _back_to_company_actions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Возврат к действиям с компанией"""
        if not update.callback_query or not update.effective_user:
            return
            
        user_id = update.effective_user.id
        query = update.callback_query
        
        try:
            # Получаем данные компании из context.user_data (сохраненные при выборе)
            company_data = None
            if context.user_data and 'selected_company' in context.user_data:
                company_data = context.user_data['selected_company']
            
            if not company_data:
                await query.edit_message_text(
                    "❌ Данные компании не найдены. Выберите компанию заново.",
                    reply_markup=self.keyboards.get_back_inline_button()
                )
                return
            
            # Показываем меню действий с компанией
            company_name = company_data.get('name', 'Неизвестно')
            
            await query.edit_message_text(
                f"🏢 <b>{company_name}</b>\n\nВыберите действие:",
                parse_mode='HTML',
                reply_markup=self.keyboards.get_company_actions_menu()
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка возврата к действиям с компанией: {e}")
            await query.edit_message_text(
                f"❌ Ошибка: {str(e)}",
                reply_markup=self.keyboards.get_back_inline_button()
            )
