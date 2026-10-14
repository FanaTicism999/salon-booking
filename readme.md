# Salon Booking Bot 🤖💇‍♀️

Pet-проект: **система онлайн-записи для салона красоты** с лендингом, Telegram-ботом и ботом для мессенджера MAX.

Проект создавался как реальное решение для малого бизнеса: владелец салона управляет услугами, записями и контентом сайта **прямо через Telegram**, а клиенты записываются через удобный мессенджер.

---

## 📸 Скриншоты

### Лендинг
![Лендинг](./screenshots/landing.png)

### Telegram-бот (клиент)
![Telegram-бот](./screenshots/tg-bot.png)

### MAX-бот (клиент)
![MAX-бот](./screenshots/max-bot.png)

### Админ-панель в Telegram
![Админка](./screenshots/admin.png)

---

## ✨ Возможности

### Для клиента
- 📝 Онлайн-запись через **Telegram** или **MAX**
- 📅 Выбор услуги, даты (7 дней вперёд) и времени
- ⏰ Слоты обновляются в реальном времени — **защита от двойных броней**
- 📞 Ввод номера телефона при первой записи (с валидацией +7)
- 📋 Просмотр и отмена своих записей
- ℹ️ Информация о салоне из лендинга

### Для владельца салона (админ)
- 📊 **Просмотр записей**: на сегодня (`/bookings_today`), на неделю (`/bookings_week`)
- 👤 **Карточка клиента**: имя, телефон, история, количество записей (`/user`, `/history`)
- 📞 **Создание записи вручную** — по звонку (`/add_booking`)
- 🚫 **Блокировка спамеров** (`/block`, `/unblock`, `/blocked`)
- 💼 **Управление услугами** — добавление, удаление, список (`/add_service`, `/list_services`, `/del_service`)
- ✏️ **Редактирование лендинга** прямо через бота (`/edit_name`, `/edit_phone`, `/edit_address`, `/show_site`)
- 📸 **Загрузка фото** для услуг и hero-секции (`/upload_hero`, `/upload_service1`...`9`)
- 📈 **Статистика за 30 дней** (`/stats`)
- 🆔 **Пометки источника** записи: 🤖 (из бота) или 📞 (по звонку)

### Лендинг
- 🎨 Современный дизайн с фиолетовой темой
- 🖼️ SVG-иллюстрации (не теряют качество)
- 📱 Полностью адаптивный (mobile-first)
- 🔄 Данные загружаются из `site.json` — обновление без правки HTML
- 🌐 **Автодеплой** на Cloudflare Pages при `git push`
- ✏️ **Контент редактируется через бота** — без программиста

---

## 🛠 Стек технологий

### Backend
- **Python 3.13**
- **aiogram 3.x** — Telegram-бот
- **maxapi** — MAX-бот (синтаксис в стиле aiogram)
- **SQLAlchemy 2.0** (async) — ORM
- **PostgreSQL** (Neon) — база данных
- **FastAPI** — REST API (в планах)

### Frontend (лендинг)
- **HTML5** + **CSS3** (без фреймворков)
- **Vanilla JS** — динамический рендеринг
- **SVG** — векторные иллюстрации
- **JSON** — контент-файл (`site.json`)

### Инфраструктура
- **Cloudflare Pages** — хостинг лендинга (бесплатно)
- **Render** — хостинг ботов (бесплатно)
- **Neon** — PostgreSQL в облаке (бесплатно)
- **GitHub** — хранение кода и CI/CD

---

## 🏗 Архитектура

```
                  ┌──────────────────────┐
                  │  PostgreSQL (Neon)   │
                  │ users / services /   │
                  │ bookings / blocked   │
                  └──────────┬───────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
       ┌──────▼──────┐                ┌─────▼──────┐
       │ Telegram-бот│                │  MAX-бот   │
       │  (aiogram)  │                │ (maxapi)   │
       └──────┬──────┘                └─────┬──────┘
              │                             │
       [админ + клиент]                [клиент]
              │
       ┌──────▼──────┐
       │  FastAPI    │ ← общий код БД
       │ requests.py │
       └──────┬──────┘
              │
       ┌──────▼───────┐    ┌───────────────┐
       │ site.json    │◄───│ GitHub API    │
       └──────┬───────┘    └───────┬───────┘
              │                    │
       ┌──────▼─────────┐          │
       │  Лендинг       │          │
       │ (Cloudflare    │          │
       │   Pages)       │          │
       └────────────────┘          │
                                   │
                     ┌─────────────▼─────────────┐
                     │ Редактирование из Telegram │
                     └────────────────────────────┘
```

---

## 🚀 Установка и запуск (локально)

### Требования
- Python 3.13+
- Git

### 1. Клонирование

```bash
git clone https://github.com/FanaTicism999/salon-booking.git
cd salon-booking
```

### 2. Виртуальное окружение

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Переменные окружения

Создай файл `.env` в корне проекта:

```env
BOT_TOKEN=your_telegram_bot_token
MAX_BOT_TOKEN=your_max_bot_token
ADMIN_ID=your_telegram_id
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_REPO=username/repo
DATABASE_URL=postgresql://user:pass@host/db?sslmode=require
```

### 5. Запуск

```bash
# Оба бота (Telegram + MAX) параллельно
python -m app.main

# Только Telegram
python -m app.handlers

# Только MAX
python -m app.max_handlers.client_max
```

### 6. Лендинг локально

```bash
cd landing
python -m http.server 8000
# открыть http://localhost:8000
```

---

## 🌐 Деплой

### Лендинг → Cloudflare Pages (бесплатно)

1. Push в GitHub
2. Cloudflare Pages → Connect to Git → выбрать репозиторий
3. **Build output directory**: `landing`
4. Готово — автодеплой при push

### Боты → Render (бесплатно)

1. Render → New Web Service → подключить репозиторий
2. **Build Command**: `pip install -r requirements.txt`
3. **Start Command**: `python -m app.main`
4. Добавить переменные окружения
5. Готово

⚠️ **Free-план Render засыпает через 15 минут.** Для обхода — использовать **UptimeRobot** (пинг каждые 5 минут).

---

## 🤖 Команды бота

### Клиентские
- `/start` — главное меню
- `/my_bookings` — мои записи

### Админские (только для ADMIN_ID)

| Команда | Что делает |
|---------|-----------|
| `/add_service` | Добавить услугу |
| `/list_services` | Список услуг |
| `/del_service <id>` | Удалить услугу |
| `/add_booking` | Создать запись вручную (по звонку) |
| `/bookings_today` | Записи на сегодня |
| `/bookings_week` | Записи за 7 дней |
| `/stats` | Статистика за 30 дней |
| `/user <id>` | Карточка клиента |
| `/history <id>` | История записей |
| `/block <id>` | Заблокировать клиента |
| `/unblock <id>` | Разблокировать |
| `/blocked` | Список заблокированных |
| `/show_site` | Текущие данные сайта |
| `/edit_name` | Изменить название |
| `/edit_phone` | Изменить телефон |
| `/edit_address` | Изменить адрес |
| `/edit_hero_title` | Изменить заголовок |
| `/edit_hero_subtitle` | Изменить слоган |
| `/upload_hero` | Загрузить фон |
| `/upload_service<1-9>` | Загрузить фото услуги |
| `/help` | Справка |

---

## 📁 Структура проекта

```
salon-booking/
├── app/
│   ├── database/
│   │   ├── engine.py       # Подключение к БД
│   │   ├── models.py       # Модели (User, Service, Booking, BlockedUser)
│   │   └── requests.py     # Функции работы с БД
│   ├── handlers/           # Telegram-бот
│   │   ├── admin.py        # Админ-команды
│   │   ├── client.py       # Клиентские команды
│   │   ├── booking.py      # FSM-логика записи
│   │   ├── editor.py       # Редактирование лендинга
│   │   ├── uploads.py      # Загрузка фото
│   │   └── help_cmd.py     # /help
│   ├── max_handlers/       # MAX-бот
│   │   └── client_max.py
│   ├── github_api.py       # GitHub API (site.json + uploads)
│   └── main.py             # Запуск обоих ботов
├── landing/                # Лендинг (Cloudflare Pages)
│   ├── index.html
│   ├── style.css
│   ├── script.js
│   ├── site.json           # Контент
│   └── images/             # SVG-иллюстрации + фото
├── requirements.txt
├── render.yaml
├── .env.example
└── README.md
```

---

## 🔒 Безопасность

- Секреты хранятся в `.env` (**не коммитятся** в Git)
- Админ-команды защищены проверкой `ADMIN_ID`
- Защита от двойных броней (проверка занятости слота)
- Защита от отмены чужих записей
- Валидация телефона (`+7XXXXXXXXXX`)
- Защита от записи на прошедшие слоты (минимум за 2 часа)

---

## 🎯 Что можно добавить дальше

- [ ] **Google Calendar/Yandex Calendar** — синхронизация записей
- [ ] **SMS-уведомления** клиентам
- [ ] **Онлайн-оплата** (ЮKassa)
- [ ] **Отзывы** после визита
- [ ] **Рассылки** клиентам по базе
- [ ] **Несколько мастеров** с отдельными расписаниями
- [ ] **Свой домен** + SSL
- [ ] **Полноценный Backend** + дальнейшее его развитие

---

## 👤 Автор

**Даниил Хасанов**
- GitHub: [@FanaTicism999](https://github.com/FanaTicism999)
- Telegram: [@Fanatism999]

---

## 📄 Лицензия

MIT License
---

## 🙏 Благодарности

- **aiogram** — за отличную библиотеку
- **maxapi** — за поддержку MAX
- **Cloudflare Pages** и **Render** — за бесплатный хостинг
- **Neon** — за бесплатный PostgreSQL

---

⭐ Если проект оказался полезным — поставь звезду на GitHub!