# 🚀 AstroBot - Руководство по запуску

## 📋 Предварительные требования

### 🔧 Системные требования:
- **Python 3.11+**
- **Windows 10/11, macOS, или Linux**
- **Минимум 2GB RAM**
- **100MB свободного места**

### 🔑 API ключи (обязательные):
- **Telegram Bot Token** - получите у @BotFather
- **OpenAI API Key** - для AI-астролога
- **NewsData API Key** - для новостей (опционально)

---

## 🚀 Быстрый запуск

### 1. 📥 Клонирование проекта:
```bash
git clone <repository-url>
cd astrobot
```

### 2. 📦 Установка зависимостей:
```bash
pip install -r requirements.txt
```

### 3. 🔧 Настройка конфигурации:
Создайте файл `.env` в корне проекта:
```env
# Обязательные настройки
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here

# Опциональные настройки
NEWSDATA_API_KEY=your_newsdata_api_key_here
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_ENVIRONMENT=gcp-starter
ASTROLOGY_API_KEY=your_prokerala_api_key_here

# Настройки базы данных
DATABASE_URL=sqlite:///astrobot.db

# Настройки логирования
LOG_LEVEL=INFO
```

### 4. 🗃️ Инициализация базы данных:
```bash
python -c "from database.connection import init_database; init_database()"
```

### 5. 🚀 Запуск бота:
```bash
python main.py
```

---

## 🔍 Проверка работоспособности

### ✅ Тест конфигурации:
```bash
python -c "from utils.config import load_config; print('✅ Конфигурация загружена')"
```

### ✅ Тест базы данных:
```bash
python -c "from database.connection import db_manager; print('✅ БД доступна' if db_manager.health_check() else '❌ БД недоступна')"
```

### ✅ Полное тестирование:
```bash
python test_full_system.py
```

---

## 📱 Использование в Telegram

### 🎯 Основные команды:
- `/start` - начало работы с ботом
- Используйте меню для навигации по функциям

### 🔮 Доступные функции:
1. **📊 Узнать знак зодиака компании**
   - Введите название и дату регистрации
   - Получите астрологический анализ

2. **📈 Бизнес-прогноз для компании**
   - Комплексный анализ с учетом новостей
   - Рекомендации для бизнеса

3. **🤝 Проверить совместимость**
   - Анализ совместимости знаков зодиака
   - Рекомендации по взаимодействию

4. **📅 Ежедневные прогнозы**
   - Актуальные астрологические рекомендации

---

## 🔧 Настройка для продакшена

### 🗄️ Переход на PostgreSQL:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/astrobot
```

### 📊 Мониторинг:
- Логи сохраняются в `logs/astrobot.log`
- Используйте `LOG_LEVEL=INFO` для подробного логирования

### 🔒 Безопасность:
- Никогда не коммитьте файл `.env`
- Используйте переменные окружения на сервере
- Регулярно обновляйте API ключи

---

## 🐛 Решение проблем

### ❌ Ошибка "Module not found":
```bash
pip install -r requirements.txt
```

### ❌ Ошибка базы данных:
```bash
python -c "from database.connection import init_database; init_database()"
```

### ❌ Бот не отвечает:
1. Проверьте токен в `.env`
2. Убедитесь, что бот запущен только в одном месте
3. Проверьте логи в `logs/astrobot.log`

### ❌ API недоступны:
- Система работает автономно при недоступности внешних API
- Проверьте лимиты на API ключах

---

## 📋 Структура файлов

```
astrobot/
├── main.py              # 🚀 Точка входа
├── requirements.txt     # 📦 Зависимости  
├── .env                 # 🔧 Конфигурация (создать)
├── astrobot.db         # 🗃️ База данных (создается автоматически)
├── logs/               # 📊 Логи
├── bot/                # 🤖 Telegram бот
├── ai_astrologist/     # 🔮 AI-астролог
├── astrology_api/      # ⭐ Астрологические расчеты
├── news_parser/        # 📰 Парсер новостей
├── embedding/          # 🧠 Векторная база
├── database/           # 🗃️ База данных
└── utils/              # 🔧 Утилиты
```

---

## 📞 Поддержка

### 🔧 Получение помощи:
1. Проверьте логи в `logs/astrobot.log`
2. Запустите `python test_full_system.py` для диагностики
3. Убедитесь, что все API ключи корректны

### 📊 Мониторинг:
- База данных: SQLite файл `astrobot.db`
- Логи: папка `logs/`
- Конфигурация: файл `.env`

---

## 🎉 Готово!

После выполнения всех шагов ваш AstroBot будет готов к работе!

**Найдите бота в Telegram и начните использовать астрологические прогнозы для бизнеса! 🌟**




