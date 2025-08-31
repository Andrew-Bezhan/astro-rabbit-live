"""
Упрощенная версия бота для демонстрации
"""

import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from bot.keyboards import BotKeyboards
from bot.states import StateManager, BotState
from ai_astrologist.numerology import NumerologyCalculator
from utils.helpers import validate_date, clean_company_name, get_zodiac_sign
from utils.logger import setup_logger
from utils.config import load_config

logger = setup_logger()


class SimpleBotHandlers:
    """Упрощенные обработчики бота без внешних API"""
    
    def __init__(self):
        self.state_manager = StateManager()
        self.keyboards = BotKeyboards()
        self.numerology = NumerologyCalculator()
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        if not update.effective_user or not update.message:
            return
            
        user = update.effective_user
        
        welcome_text = f"""
🔮 **Добро пожаловать в Астробот**, {user.first_name or 'Пользователь'}!

Я — ваш персональный эксперт по корпоративной астрологии.

✨ **Доступные функции:**
• 🔮 Определение знака зодиака компании
• 🔢 Нумерологический анализ названий
• ♈ Астрологические характеристики

**Выберите действие в меню ниже!** 👇
        """
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=self.keyboards.get_main_menu(),
            parse_mode='Markdown'
        )
        
        self.state_manager.reset_user(user.id)
        logger.info(f"👋 Пользователь {user.id} запустил бота")
    
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик сообщений"""
        if not update.effective_user or not update.message or not update.message.text:
            return
            
        user_id = update.effective_user.id
        text = update.message.text
        current_state = self.state_manager.get_state(user_id)
        
        logger.info(f"💬 Пользователь {user_id}: '{text}' (состояние: {current_state.name})")
        
        if current_state == BotState.IDLE:
            if text == "🔮 Узнать знак зодиака Компании":
                await self._start_simple_analysis(update, context)
            else:
                await update.message.reply_text(
                    "🤔 Выберите действие из меню.",
                    reply_markup=self.keyboards.get_main_menu()
                )
        
        elif current_state == BotState.ZODIAC_COMPANY_NAME:
            await self._handle_company_name(update, context, text)
        elif current_state == BotState.ZODIAC_REG_DATE:
            await self._handle_company_date(update, context, text)
        elif current_state == BotState.ZODIAC_REG_PLACE:
            await self._handle_company_place(update, context, text)
    
    async def _start_simple_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запуск упрощенного анализа"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        
        await update.message.reply_text(
            "🔮 **АНАЛИЗ ЗНАКА ЗОДИАКА КОМПАНИИ**\\n\\n"
            "📝 Введите **название компании**:",
            parse_mode='Markdown'
        )
        
        self.state_manager.set_state(user_id, BotState.ZODIAC_COMPANY_NAME)
        self.state_manager.get_user_data(user_id).reset()
    
    async def _handle_company_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка названия компании"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        user_data = self.state_manager.get_user_data(user_id)
        
        cleaned_name = clean_company_name(text.strip())
        if user_data:
            user_data.company_name = cleaned_name
        
        await update.message.reply_text(
            f"✅ Компания: **{cleaned_name}**\\n\\n"
            "📅 Введите **дату регистрации** в формате ДД.ММ.ГГГГ:",
            parse_mode='Markdown'
        )
        
        self.state_manager.set_state(user_id, BotState.ZODIAC_REG_DATE)
    
    async def _handle_company_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка даты регистрации"""
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
            f"✅ Дата: **{reg_date.strftime('%d.%m.%Y') if reg_date else 'Неизвестно'}**\\n\\n"
            "🏙️ Введите **город регистрации**:",
            parse_mode='Markdown'
        )
        
        self.state_manager.set_state(user_id, BotState.ZODIAC_REG_PLACE)
    
    async def _handle_company_place(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка места регистрации и завершение анализа"""
        if not update.effective_user or not update.message:
            return
        user_id = update.effective_user.id
        user_data = self.state_manager.get_user_data(user_id)
        
        if user_data:
            user_data.registration_place = text.strip()
        
        if not user_data or not user_data.registration_date or not user_data.company_name:
            await update.message.reply_text(
                "❌ Ошибка: недостаточно данных для анализа.",
                reply_markup=self.keyboards.get_main_menu()
            )
            return
        
        # Генерируем анализ
        zodiac = get_zodiac_sign(user_data.registration_date)
        company_number = self.numerology.calculate_name_number(user_data.company_name)
        company_meaning = self.numerology.get_number_meaning(company_number)
        
        analysis = f"""
🏢 **АНАЛИЗ КОМПАНИИ "{user_data.company_name}"**

♈ **Астрологические данные:**
🌟 Знак зодиака: {zodiac}
📅 Дата регистрации: {user_data.registration_date.strftime('%d.%m.%Y')}
🌍 Место регистрации: {user_data.registration_place}

🔢 **Нумерологический анализ:**
🎯 Число компании: {company_number}
💎 Характеристики: {company_meaning['traits']}
💼 Бизнес-потенциал: {company_meaning['business']}
⚠️ Потенциальные риски: {company_meaning['risks']}

💡 **Рекомендации:**
🚀 Используйте сильные стороны числа {company_number}
⭐ Учитывайте особенности знака {zodiac}
📊 Планируйте важные решения с учетом астрологических циклов

✨ **Это базовый анализ.** Для полного прогноза с учетом экономических трендов используйте /start и выберите "Бизнес-прогноз".
        """
        
        await update.message.reply_text(
            analysis,
            parse_mode='Markdown',
            reply_markup=self.keyboards.get_main_menu()
        )
        
        # Возвращаемся в главное меню
        self.state_manager.reset_user(user_id)
        logger.info(f"✅ Анализ для {user_data.company_name} завершен")


class SimpleAstroBot:
    """Упрощенная версия Астробота"""
    
    def __init__(self):
        self.config = load_config()
        self.handlers = SimpleBotHandlers()
        
        if not self.config.bot.token:
            raise ValueError("Telegram bot token is required")
        
        logger.info("🤖 SimpleAstroBot инициализирован")
    
    async def start(self):
        """Запуск бота"""
        app = None
        try:
            # Создаем приложение
            app = Application.builder().token(self.config.bot.token).build()
            
            # Регистрируем обработчики
            app.add_handler(CommandHandler("start", self.handlers.start_command))
            app.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND, 
                self.handlers.message_handler
            ))
            
            logger.info("🚀 Запуск упрощенного Telegram бота...")
            
            # Инициализируем и запускаем
            await app.initialize()
            await app.start()
            
            # Запускаем polling
            if app.updater:
                await app.updater.start_polling(drop_pending_updates=True)
            
            logger.info("✅ Упрощенный Астробот запущен! Нажмите Ctrl+C для остановки.")
            
            # Ждем остановки
            try:
                await asyncio.Event().wait()
            except KeyboardInterrupt:
                logger.info("📡 Получен сигнал остановки")
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска: {e}")
            raise
        finally:
            logger.info("🛑 Остановка бота...")
            if app:
                if app.updater:
                    await app.updater.stop()
                await app.stop()
                await app.shutdown()
            logger.info("✅ Бот остановлен")


if __name__ == "__main__":
    bot = SimpleAstroBot()
    asyncio.run(bot.start())
