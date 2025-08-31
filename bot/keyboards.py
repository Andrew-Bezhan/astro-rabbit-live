"""
Клавиатуры и меню для Telegram бота
"""

from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton
from typing import List


class BotKeyboards:
    """Класс для создания клавиатур бота"""
    
    @staticmethod
    def get_main_menu() -> ReplyKeyboardMarkup:
        """
        Главное меню бота
        
        Returns:
            ReplyKeyboardMarkup: Основная клавиатура
        """
        keyboard = [
            ["🏢 Мои компании"],
            ["🔮 Узнать знак зодиака Компании"],
            ["📈 Бизнес-прогноз для Компании"],
            ["🤝 Проверить совместимость"],
            ["📅 Ежедневные прогнозы", "👤 Личный кабинет"],
            ["💳 Тарифы", "ℹ️ Справка", "⚙️ Настройки"]
        ]
        
        return ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=False,
            input_field_placeholder="Выберите действие..."
        )
    
    @staticmethod
    def get_companies_required_menu() -> ReplyKeyboardMarkup:
        """
        Меню с кнопкой для перехода к компаниям
        
        Returns:
            ReplyKeyboardMarkup: Клавиатура с кнопкой "Мои компании"
        """
        keyboard = [
            ["🏢 Мои компании"],
            ["🔙 Главное меню"]
        ]
        
        return ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=False,
            input_field_placeholder="Выберите действие..."
        )
    
    @staticmethod
    def get_business_spheres() -> InlineKeyboardMarkup:
        """
        Клавиатура выбора сферы деятельности
        
        Returns:
            InlineKeyboardMarkup: Клавиатура со сферами
        """
        spheres = [
            ("🏗️ Строительство и промышленность", "sphere_construction"),
            ("💰 Финансы и инвестиции", "sphere_finance"),
            ("🛒 Торговля и сфера услуг", "sphere_trade"),
            ("💻 Технологии и телекоммуникации", "sphere_tech"),
            ("🏛️ Государственный сектор", "sphere_government"),
            ("⚡ Энергетика", "sphere_energy")
        ]
        
        keyboard = []
        for text, callback_data in spheres:
            keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_compatibility_types() -> InlineKeyboardMarkup:
        """
        Клавиатура типов совместимости
        
        Returns:
            InlineKeyboardMarkup: Клавиатура типов
        """
        types = [
            ("👤 Проверить совместимость сотрудника", "compat_employee"),
            ("🤝 Проверить совместимость клиента", "compat_client"),
            ("🤝 Проверить совместимость партнера", "compat_partner")
        ]
        
        keyboard = []
        for text, callback_data in types:
            keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])
        
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_detailed_analysis() -> InlineKeyboardMarkup:
        """
        Клавиатура детального анализа
        
        Returns:
            InlineKeyboardMarkup: Клавиатура анализов
        """
        analyses = [
            ("⚡ Быстрый прогноз на 3 месяца", "analysis_three_months"),
            ("💰 Прогноз финансов", "analysis_financial"),
            ("🤝 Прогноз партнерства", "analysis_partnership"),
            ("⚠️ Прогноз рисков", "analysis_risks")
        ]
        
        keyboard = []
        for text, callback_data in analyses:
            keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])
        
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_company_selection(companies: List[dict]) -> InlineKeyboardMarkup:
        """
        Клавиатура выбора сохраненной компании
        
        Args:
            companies (List[dict]): Список компаний пользователя
            
        Returns:
            InlineKeyboardMarkup: Клавиатура с компаниями
        """
        keyboard = []
        
        for i, company in enumerate(companies[:10]):  # Максимум 10 компаний
            company_name = company.get('name', f'Компания {i+1}')
            # Ограничиваем длину названия
            if len(company_name) > 30:
                company_name = company_name[:27] + "..."
            
            keyboard.append([InlineKeyboardButton(
                f"🏢 {company_name}",
                callback_data=f"select_company_{i}"
            )])
        
        keyboard.append([InlineKeyboardButton("➕ Добавить новую компанию", callback_data="add_new_company")])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_confirmation() -> InlineKeyboardMarkup:
        """
        Клавиатура подтверждения
        
        Returns:
            InlineKeyboardMarkup: Клавиатура да/нет
        """
        keyboard = [
            [
                InlineKeyboardButton("✅ Да", callback_data="confirm_yes"),
                InlineKeyboardButton("❌ Нет", callback_data="confirm_no")
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_skip_optional() -> InlineKeyboardMarkup:
        """
        Клавиатура с кнопкой пропуска для необязательных полей
        
        Returns:
            InlineKeyboardMarkup: Клавиатура с пропуском
        """
        keyboard = [
            [InlineKeyboardButton("⏭️ Пропустить", callback_data="skip_field")]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_back_button() -> InlineKeyboardMarkup:
        """
        Клавиатура только с кнопкой "Назад"
        
        Returns:
            InlineKeyboardMarkup: Клавиатура назад
        """
        keyboard = [
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_daily_forecast_settings() -> InlineKeyboardMarkup:
        """
        Клавиатура настроек ежедневных прогнозов
        
        Returns:
            InlineKeyboardMarkup: Клавиатура настроек
        """
        keyboard = [
            [InlineKeyboardButton("🔔 Включить уведомления", callback_data="daily_enable")],
            [InlineKeyboardButton("🔕 Отключить уведомления", callback_data="daily_disable")],
            [InlineKeyboardButton("⏰ Изменить время", callback_data="daily_time")],
            [InlineKeyboardButton("🏢 Выбрать компанию", callback_data="daily_company")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_company_profile_actions() -> InlineKeyboardMarkup:
        """
        Клавиатура действий с профилем компании
        
        Returns:
            InlineKeyboardMarkup: Клавиатура действий
        """
        keyboard = [
            [InlineKeyboardButton("👁️ Просмотреть", callback_data="profile_view")],
            [InlineKeyboardButton("✏️ Редактировать", callback_data="profile_edit")],
            [InlineKeyboardButton("🗑️ Удалить", callback_data="profile_delete")],
            [InlineKeyboardButton("📊 Создать прогноз", callback_data="profile_forecast")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_companies")]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_contact_keyboard() -> ReplyKeyboardMarkup:
        """
        Клавиатура для отправки контакта
        
        Returns:
            ReplyKeyboardMarkup: Клавиатура с кнопкой контакта
        """
        keyboard = [
            [KeyboardButton("📞 Поделиться контактом", request_contact=True)],
            [KeyboardButton("⏭️ Пропустить")]
        ]
        
        return ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )
    
    @staticmethod
    def get_location_keyboard() -> ReplyKeyboardMarkup:
        """
        Клавиатура для отправки геолокации
        
        Returns:
            ReplyKeyboardMarkup: Клавиатура с кнопкой локации
        """
        keyboard = [
            [KeyboardButton("📍 Поделиться локацией", request_location=True)],
            [KeyboardButton("✍️ Ввести вручную")]
        ]
        
        return ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )
    
    @staticmethod
    def get_back_inline_button() -> InlineKeyboardMarkup:
        """Inline кнопка возврата в главное меню"""
        keyboard = [
            [InlineKeyboardButton("🔙 Назад к главному меню", callback_data="back_to_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_add_company_menu() -> InlineKeyboardMarkup:
        """Меню добавления новой компании"""
        keyboard = [
            [InlineKeyboardButton("➕ Создать профиль компании", callback_data="add_company")],
            [InlineKeyboardButton("🔙 Назад к главному меню", callback_data="back_to_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_companies_management_menu(companies: list) -> InlineKeyboardMarkup:
        """Меню управления компаниями"""
        keyboard = []
        
        # Добавляем кнопки для каждой компании (максимум 5)
        for i, comp in enumerate(companies[:5], 1):
            keyboard.append([
                InlineKeyboardButton(f"📊 {comp['name'][:20]}...", callback_data=f"select_company_{comp['id']}"),
                InlineKeyboardButton("✏️", callback_data=f"edit_company_{comp['id']}"),
                InlineKeyboardButton("🗑️", callback_data=f"delete_company_{comp['id']}")
            ])
        
        # Кнопки управления
        keyboard.extend([
            [InlineKeyboardButton("➕ Добавить компанию", callback_data="add_company")],
            [InlineKeyboardButton("🔙 Назад к главному меню", callback_data="back_to_main")]
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_company_actions_menu() -> InlineKeyboardMarkup:
        """Меню действий с выбранной компанией"""
        keyboard = [
            [InlineKeyboardButton("🔮 Анализ знака зодиака", callback_data="company_zodiac")],
            [InlineKeyboardButton("📈 Бизнес-прогноз", callback_data="company_forecast")],
            [InlineKeyboardButton("🤝 Проверка совместимости", callback_data="company_compatibility")],
            [InlineKeyboardButton("✏️ Редактировать профиль", callback_data="edit_company")],
            [InlineKeyboardButton("🔙 К списку компаний", callback_data="back_to_companies")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def get_save_analysis_menu() -> InlineKeyboardMarkup:
        """Меню сохранения результатов анализа"""
        keyboard = [
            [InlineKeyboardButton("💾 Сохранить анализ", callback_data="save_analysis")],
            [InlineKeyboardButton("🔙 К действиям с компанией", callback_data="back_to_company_actions")]
        ]
        return InlineKeyboardMarkup(keyboard)


