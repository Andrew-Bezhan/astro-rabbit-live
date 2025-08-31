"""
Основной модуль Telegram бота Астробота
"""

import asyncio
from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    filters,
    ContextTypes
)

from .handlers import BotHandlers
from utils.config import load_config
from utils.logger import setup_logger
from database.connection import init_database

logger = setup_logger()


class AstroBot:
    """Основной класс Telegram бота"""
    
    def __init__(self):
        """Инициализация бота"""
        self.config = load_config()
        self.handlers = BotHandlers()
        # Проверяем наличие токена
        if not self.config.bot.token:
            logger.error("❌ Отсутствует токен Telegram бота в .env файле")
            raise ValueError("Telegram bot token is required")
        
        # Создаем приложение сразу в конструкторе
        self.application = Application.builder().token(self.config.bot.token).build()
        
        logger.info("🤖 AstroBot инициализирован")
    
    async def start(self):
        """Запуск бота"""
        try:
            # Регистрируем обработчики
            self._register_handlers()
            
            # Запускаем бота
            logger.info("🚀 Запуск Telegram бота...")
            
            # АГРЕССИВНАЯ ОЧИСТКА ПЕРЕД СТАРТОМ
            try:
                from telegram import Bot
                temp_bot = Bot(token=self.bot_token)
                
                # Принудительно очищаем webhook и updates
                await temp_bot.delete_webhook(drop_pending_updates=True)
                await asyncio.sleep(2)
                
                # Получаем и игнорируем все pending updates
                await temp_bot.get_updates(offset=-1, limit=100, timeout=1)
                await asyncio.sleep(1)
                
                logger.info("🧹 АГРЕССИВНАЯ очистка Telegram завершена")
            except Exception as e:
                logger.warning(f"⚠️ Агрессивная очистка не удалась: {e}")
            
            try:
                await asyncio.wait_for(self.application.initialize(), timeout=30.0)
                await asyncio.wait_for(self.application.start(), timeout=15.0)
                
                # Дополнительная очистка ПОСЛЕ старта
                try:
                    await self.application.bot.delete_webhook(drop_pending_updates=True)
                    logger.info("🔄 Webhook очищен для избежания конфликтов")
                    
                    # Дополнительная очистка pending updates
                    await asyncio.sleep(1)  # Небольшая задержка
                    await self.application.bot.get_updates(offset=-1, limit=1)
                    logger.info("🧹 Pending updates очищены")
                    
                    # Настраиваем команды меню бота
                    await self._setup_bot_commands()
                    logger.info("📋 Команды бота настроены")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось очистить webhook/updates: {type(e).__name__}")
                
            except asyncio.TimeoutError:
                logger.error("❌ Telegram инициализация прервана по таймауту (30 сек)")
                logger.info("🔄 Попробуйте перезапустить бота через несколько секунд")
                raise
            except asyncio.CancelledError:
                logger.warning("⚠️ Telegram инициализация отменена пользователем")
                return
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации Telegram: {type(e).__name__}: {e}")
                raise
            
            # Запускаем polling (получение обновлений) с retry механизмом
            retry_count = 0
            max_retries = 3
            
            while retry_count < max_retries:
                try:
                    if self.application.updater:
                        await self.application.updater.start_polling(
                            drop_pending_updates=True,
                            allowed_updates=Update.ALL_TYPES
                        )
                    break  # Если успешно, выходим из цикла
                except Exception as e:
                    if "Conflict" in str(e) and retry_count < max_retries - 1:
                        retry_count += 1
                        logger.warning(f"⚠️ Conflict detected, retry {retry_count}/{max_retries}")
                        await asyncio.sleep(5)  # Ждем перед повтором
                        # Пробуем еще раз очистить
                        try:
                            await self.application.bot.delete_webhook(drop_pending_updates=True)
                            await asyncio.sleep(2)
                        except:
                            pass
                        continue
                    else:
                        raise
            
            logger.info("✅ Астробот успешно запущен и готов к работе!")
            
            # Держим бота запущенным
            logger.info("🔄 Бот работает. Нажмите Ctrl+C для остановки.")
            
            # Создаем событие для ожидания остановки
            stop_event = asyncio.Event()
            
            # Для Windows используем простое ожидание
            try:
                await stop_event.wait()
            except KeyboardInterrupt:
                logger.info("📡 Получен сигнал остановки (Ctrl+C)")
                stop_event.set()
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска бота: {e}")
            raise
        finally:
            await self.stop()
    
    async def stop(self):
        """Остановка бота"""
        try:
            if self.application:
                logger.info("🛑 Остановка Telegram бота...")
                
                if self.application.updater:
                    await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                
                logger.info("✅ Telegram бот остановлен")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке бота: {e}")
    
    def _register_handlers(self):
        """Регистрация обработчиков команд и сообщений"""
        app = self.application
        
        # Обработчики команд
        app.add_handler(CommandHandler("start", self.handlers.start_command))
        app.add_handler(CommandHandler("help", self.handlers.help_command))
        
        # Дополнительные команды для бокового меню
        app.add_handler(CommandHandler("zodiac", self.handlers.zodiac_command))
        app.add_handler(CommandHandler("forecast", self.handlers.forecast_command))
        app.add_handler(CommandHandler("compatibility", self.handlers.compatibility_command))
        app.add_handler(CommandHandler("companies", self.handlers.companies_command))
        app.add_handler(CommandHandler("cabinet", self.handlers.cabinet_command))
        app.add_handler(CommandHandler("tariffs", self.handlers.tariffs_command))
        app.add_handler(CommandHandler("daily", self.handlers.daily_command))
        app.add_handler(CommandHandler("settings", self.handlers.settings_command))
        
        # Обработчик inline-кнопок (callback queries)
        app.add_handler(CallbackQueryHandler(self.handlers.callback_handler))
        
        # Обработчик текстовых сообщений (исключаем команды)
        app.add_handler(MessageHandler(
            filters.TEXT, 
            self.handlers.message_handler
        ))
        
        # Обработчик команд (дополнительная защита) - убираем, так как команды уже обрабатываются выше
        
        # Обработчик контактов
        app.add_handler(MessageHandler(
            filters.CONTACT, 
            self._handle_contact
        ))
        
        # Обработчик геолокации
        app.add_handler(MessageHandler(
            filters.LOCATION, 
            self._handle_location
        ))
        
        # Обработчик документов
        app.add_handler(MessageHandler(
            filters.Document.ALL, 
            self._handle_document
        ))
        
        # Обработчик ошибок - добавляем с правильной типизацией
        async def error_handler_wrapper(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
            if isinstance(update, Update):
                await self._error_handler(update, context)
        
        app.add_error_handler(error_handler_wrapper)
        
        logger.info("📝 Обработчики команд зарегистрированы")
    
    async def _setup_bot_commands(self):
        """Настройка команд меню бота"""
        try:
            from telegram import BotCommand
            
            commands = [
                BotCommand("start", "🏠 Главное меню"),
                BotCommand("zodiac", "🔮 Узнать знак зодиака компании"),
                BotCommand("forecast", "📈 Бизнес-прогноз для компании"),
                BotCommand("compatibility", "🤝 Проверить совместимость"),
                BotCommand("companies", "🏢 Мои компании"),
                BotCommand("cabinet", "👤 Личный кабинет"),
                BotCommand("tariffs", "💳 Тарифы"),
                BotCommand("daily", "📅 Ежедневные прогнозы"),
                BotCommand("settings", "⚙️ Настройки"),
                BotCommand("help", "ℹ️ Справка")
            ]
            
            await self.application.bot.set_my_commands(commands)
            logger.info(f"📋 Настроено {len(commands)} команд бокового меню")
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка настройки команд: {e}")

    
    async def _handle_contact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка полученного контакта"""
        if not update.message or not update.effective_user or not update.message.contact:
            return
            
        contact = update.message.contact
        user_id = update.effective_user.id
        
        logger.info(f"📞 Пользователь {user_id} поделился контактом: {contact.phone_number or 'Неизвестно'}")
        
        await update.message.reply_text(
            f"📞 Контакт получен: {contact.phone_number or 'Неизвестно'}\\n"
            "Спасибо за предоставленную информацию!",
            parse_mode='Markdown'
        )
    
    async def _handle_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка полученной геолокации"""
        if not update.message or not update.effective_user or not update.message.location:
            return
            
        location = update.message.location
        user_id = update.effective_user.id
        
        logger.info(f"📍 Пользователь {user_id} поделился локацией: {location.latitude or 0}, {location.longitude or 0}")
        
        await update.message.reply_text(
            f"📍 Локация получена:\\n"
            f"Широта: {location.latitude or 0}\\n"
            f"Долгота: {location.longitude or 0}\\n"
            "Спасибо за предоставленную информацию!",
            parse_mode='Markdown'
        )
    
    async def _handle_unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка неизвестных команд"""
        if not update.message or not update.effective_user:
            return
            
        user_id = update.effective_user.id
        command = update.message.text
        
        logger.warning(f"⚠️ Неизвестная команда от пользователя {user_id}: {command}")
        
        await update.message.reply_text(
            "🤔 Неизвестная команда. Возвращаюсь в главное меню.",
            reply_markup=self.handlers.keyboards.get_main_menu()
        )
    
    async def _handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка полученных документов"""
        if not update.message or not update.effective_user or not update.message.document:
            return
            
        document = update.message.document
        user_id = update.effective_user.id
        
        logger.info(f"📄 Пользователь {user_id} отправил документ: {document.file_name or 'Неизвестно'}")
        
        await update.message.reply_text(
            f"📄 Документ получен: {document.file_name or 'Неизвестно'}\\n"
            "В данный момент обработка документов не поддерживается.",
            parse_mode='Markdown'
        )
    
    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"❌ Ошибка в боте: {context.error}")
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "😔 Произошла ошибка. Попробуйте позже или обратитесь в поддержку.\\n"
                    "Используйте /start для возврата в главное меню.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"❌ Не удалось отправить сообщение об ошибке: {e}")
    
    async def send_daily_forecast(self, user_id: int, company_data: dict):
        """
        Отправка ежедневного прогноза пользователю
        
        Args:
            user_id (int): ID пользователя
            company_data (dict): Данные компании
        """
        try:
            # Генерируем прогноз
            if self.handlers.astro_agent:
                # Получаем актуальные новости
                news_summary = ""
                if self.handlers.news_analyzer:
                    news_summary = await self.handlers.news_analyzer.get_daily_news_digest()
                
                # Генерируем ежедневный прогноз
                forecast = await self.handlers.astro_agent.generate_daily_forecast(
                    company_data,
                    daily_astrology="Текущие астрологические влияния",
                    today_news=news_summary
                )
            else:
                # Заглушка
                from datetime import datetime
                forecast = f"""
🌅 **ЕЖЕДНЕВНЫЙ ПРОГНОЗ**
📅 {datetime.now().strftime('%d.%m.%Y')}

🏢 Компания: {company_data.get('name', 'Не указано')}

⭐ Сегодня благоприятный день для новых начинаний!
💼 Рекомендуется сосредоточиться на стратегическом планировании.
🤝 Хорошее время для деловых переговоров.

📈 Следите за новостями в вашей сфере деятельности.
                """
            
            # Отправляем прогноз
            await self.application.bot.send_message(
                chat_id=user_id,
                text=forecast,
                parse_mode='Markdown'
            )
            
            logger.info(f"📅 Ежедневный прогноз отправлен пользователю {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки ежедневного прогноза пользователю {user_id}: {e}")
    
    async def broadcast_message(self, user_ids: list, message: str):
        """
        Массовая рассылка сообщений
        
        Args:
            user_ids (list): Список ID пользователей
            message (str): Текст сообщения
        """
        successful = 0
        failed = 0
        
        for user_id in user_ids:
            try:
                await self.application.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='Markdown'
                )
                successful += 1
                
                # Небольшая задержка чтобы не превысить лимиты API
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"⚠️ Не удалось отправить сообщение пользователю {user_id}: {e}")
                failed += 1
        
        logger.info(f"📢 Рассылка завершена: {successful} успешно, {failed} ошибок")
    
    def get_bot_info(self) -> dict:
        """
        Получение информации о боте
        
        Returns:
            dict: Информация о боте
        """
        return {
            "bot_token_configured": bool(self.config.bot.token),
            "handlers_count": len(self.application.handlers) if self.application else 0,
            "is_running": self.application.running if self.application else False
        }
