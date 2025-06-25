
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv
import threading
from flask import Flask, render_template
import requests
import time

# Load environment variables
load_dotenv()

# Disable ALL logging to reduce console noise
logging.getLogger('telegram').setLevel(logging.CRITICAL)
logging.getLogger('httpx').setLevel(logging.CRITICAL)
logging.getLogger('werkzeug').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
logging.disable(logging.WARNING)

# Get bot token
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Flask app for the web interface
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    return {"status": "OK", "message": "Bot is running"}

def keep_alive():
    """Функция для поддержания работы бота 24/7 (только для dev)"""
    time.sleep(30)  # Ждем запуска Flask
    while True:
        try:
            # В Replit используем внешний URL вместо localhost
            import os
            repl_url = f"https://{os.getenv('REPL_SLUG', 'localhost')}.{os.getenv('REPL_OWNER', 'replit')}.repl.co/health"
            requests.get(repl_url, timeout=5)
        except:
            pass
        time.sleep(300)  # Увеличили интервал для экономии ресурсов

# Telegram bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler with cool greeting and navigation button"""
    try:
        user = update.effective_user
        chat_id = update.effective_chat.id

        # Безопасное удаление предыдущих сообщений
        try:
            for i in range(1, 6):  # Уменьшили количество попыток
                try:
                    await context.bot.delete_message(
                        chat_id=chat_id, 
                        message_id=update.message.message_id - i
                    )
                except:
                    break  # Прерываем при первой ошибке
        except:
            pass

        greeting_text = f"Нажми кнопку \"ЗАПУСК\", чтобы получить всю нужную информацию😎"

        # Create web app button (inline)
        inline_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 ЗАПУСК", web_app=WebAppInfo(url="https://code891.github.io/TAMBI/"))]
        ])

        # Create persistent keyboard (reply keyboard)
        reply_keyboard = ReplyKeyboardMarkup([
            [KeyboardButton("🔄 СТАРТ")]
        ], resize_keyboard=True, one_time_keyboard=False)

        await update.message.reply_text(
            text=greeting_text,
            reply_markup=inline_keyboard,
            parse_mode='HTML'
        )

        # Send second message with persistent keyboard
        await context.bot.send_message(
            chat_id=chat_id,
            text="👇 Используй кнопку ниже для быстрого перезапуска:",
            reply_markup=reply_keyboard
        )
    except Exception as e:
        # Улучшенная обработка ошибок
        try:
            await update.message.reply_text("⚠️ Произошла ошибка, попробуйте ещё раз")
        except:
            pass

async def restart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle restart button callback"""
    try:
        query = update.callback_query
        await query.answer()

        chat_id = query.message.chat_id

        # Безопасное удаление предыдущих сообщений
        try:
            for i in range(1, 6):
                try:
                    await context.bot.delete_message(
                        chat_id=chat_id, 
                        message_id=query.message.message_id - i
                    )
                except:
                    break
        except:
            pass

        greeting_text = f"Нажми кнопку \"ЗАПУСК\", чтобы получить всю нужную информацию😎"

        # Create web app button (inline)
        inline_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 ЗАПУСК", web_app=WebAppInfo(url="https://code891.github.io/TAMBI/"))]
        ])

        # Create persistent keyboard (reply keyboard)
        reply_keyboard = ReplyKeyboardMarkup([
            [KeyboardButton("🔄 СТАРТ")]
        ], resize_keyboard=True, one_time_keyboard=False)

        await query.edit_message_text(
            text=greeting_text,
            reply_markup=inline_keyboard,
            parse_mode='HTML'
        )

        # Send message with persistent keyboard
        await context.bot.send_message(
            chat_id=chat_id,
            text="👇 Используй кнопку ниже для быстрого перезапуска:",
            reply_markup=reply_keyboard
        )
    except Exception as e:
        # Тихая обработка ошибок
        pass

def run_flask():
    """Run Flask app in a separate thread"""
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        pass

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages, specifically СТАРТ button"""
    try:
        if update.message.text == "🔄 СТАРТ":
            await start(update, context)
    except Exception as e:
        pass

def main():
    """Main function to run the bot with auto-restart"""
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не найден!")
        return

    if len(BOT_TOKEN) < 40:
        print("❌ Неверный токен!")
        return

    # Start Flask app in separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Проверяем тип окружения
    is_deployment = os.getenv('REPLIT_DEPLOYMENT') or os.getenv('REPL_DEPLOYMENT')
    
    if not is_deployment:
        # В разработке запускаем keep_alive
        keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
        keep_alive_thread.start()
        print("🛠️ Запущен в режиме разработки")
    else:
        print("🚀 Запущен в режиме Deployment - автоматическое поддержание работы")

    restart_count = 0
    max_restarts = 5

    while restart_count < max_restarts:
        try:
            # Create bot application
            application = Application.builder().token(BOT_TOKEN).build()

            # Add handlers
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CallbackQueryHandler(restart_callback, pattern="restart"))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

            print(f"🤖 Бот запущен! (попытка {restart_count + 1})")

            # Run the bot with proper error handling
            application.run_polling(
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query"],
                close_loop=False
            )
            
            # Если дошли сюда без ошибок - сбрасываем счетчик
            restart_count = 0
            
        except Exception as e:
            restart_count += 1
            
            if "Conflict" in str(e):
                print("⚠️ КОНФЛИКТ: Другой экземпляр бота уже работает!")
                print("💡 Остановите Development версию и используйте только Deployment")
                break
            else:
                print(f"❌ Ошибка #{restart_count}: {e}")
                
                if restart_count < max_restarts:
                    print(f"🔄 Перезапуск через 10 секунд... ({restart_count}/{max_restarts})")
                    time.sleep(10)
                else:
                    print("❌ Превышено максимальное количество перезапусков!")
                    break
    
    print("🛑 Бот остановлен")

if __name__ == '__main__':
    main()
