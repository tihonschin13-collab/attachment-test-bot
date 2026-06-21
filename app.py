import os
import json
import threading
import logging
from flask import Flask, request, jsonify, send_from_directory
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = os.environ.get("TELEGRAM_TOKEN")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://your-app.onrender.com")

if not TOKEN:
    raise ValueError("Переменная TELEGRAM_TOKEN не установлена!")

# Создание приложения
app = Flask(__name__, static_folder='public', static_url_path='')
bot = Bot(token=TOKEN)

# ===== МАРШРУТЫ ДЛЯ САЙТА =====
@app.route('/')
def serve_index():
    """Открывает тест при заходе на сайт"""
    return send_from_directory('public', 'index.html')

@app.route('/health')
def health():
    """Проверка, что бот работает"""
    return jsonify({"status": "ok"})

# ===== КОМАНДА /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton(
            "🧠 Пройти тест",
            web_app={"url": WEBAPP_URL}
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""
Привет, {user.first_name}! 👋

Это тест на определение типа привязанности.

📝 15 вопросов, 3 минуты.
Нажми на кнопку ниже, чтобы начать.
"""
    await update.message.reply_text(text, reply_markup=reply_markup)

# ===== ОБРАБОТКА РЕЗУЛЬТАТА =====
async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = json.loads(update.message.web_app_data.data)
        
        emoji_map = {
            'Надежный тип': '✅',
            'Тревожный тип': '😰',
            'Избегающий тип': '🚫',
            'Тревожно-избегающий (дезорганизованный) тип': '🌀'
        }
        emoji = emoji_map.get(data.get('type', ''), '📊')
        
        result_text = f"""
{emoji} *Ваш результат*

*Тип:* {data.get('type', 'Неизвестно')}

😰 Тревожность: {data.get('anxiety', 0)}%
🚫 Избегание: {data.get('avoidance', 0)}%

---
🔄 Чтобы пройти заново, нажми /start
"""
        await update.message.reply_text(result_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("❌ Ошибка обработки данных.")

# ===== ЗАПУСК БОТА =====
def run_bot():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    application.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
