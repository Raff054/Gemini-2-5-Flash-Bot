import os
import requests
import json
from google import genai
from google.genai.errors import APIError
from flask import Flask, request as flask_request

app = Flask(__name__)

# --- 1. Настройка переменных окружения и Доступ ---
TELEGRAM_TOKEN = os.environ.get("8251316235:AAG9HBHkXkV-jXwaHvmzRmOp92wOoUL554s")
GEMINI_API_KEY = os.environ.get("AIzaSyBK-_KDly9LRB47fZ4sQ6j-pkyQFsvJVHg")

# Список разрешенных ID пользователей Telegram
ALLOWED_USER_IDS_RAW = os.environ.get("620773667", "1015218674")
ALLOWED_USER_IDS = [int(i.strip()) for i in ALLOWED_USER_IDS_RAW.split(',') if i.strip().isdigit()]

# !!! ЖЕСТКО ЗАДАЕМ НУЖНУЮ МОДЕЛЬ !!!
GEMINI_MODEL_NAME = "gemini-2.5-flash" 

# Инициализация клиента Gemini
client = None
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Gemini client initialization error: {e}")

# --- 2. Функция отправки сообщения в Telegram ---
def send_telegram_message(chat_id, text, reply_to_message_id=None):
    if not TELEGRAM_TOKEN:
        print("TELEGRAM_BOT_TOKEN не установлен.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown',
        'reply_to_message_id': reply_to_message_id
    }
    requests.post(url, json=payload)

# --- 3. Обработчик HTTP-запросов (Flask Route) ---
@app.route('/', methods=['POST'])
def webhook_handler():
    try:
        if not client:
            return "Gemini client not initialized", 500

        data = flask_request.get_json()
        if not data or 'message' not in data:
            return "ok"

        message = data['message']
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        text = message.get('text', '')
        message_id = message['message_id']
        
        # --- ПРОВЕРКА ДОСТУПА ---
        if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
            send_telegram_message(
                chat_id, 
                "Извините, этот бот является приватным. Ваш ID не найден в списке разрешенных пользователей.",
                reply_to_message_id=message_id
            )
            return "ok"
        # ------------------------

        if not text:
            send_telegram_message(chat_id, "Извините, я могу обрабатывать только текст.")
            return "ok"
        
        # Обработка команды /start
        if text.startswith('/start'):
            send_telegram_message(
                chat_id,
                f"Привет! Я приватный бот на базе **Gemini 2.5 Flash**. Ваш ID: `{user_id}`. Задайте мне любой вопрос!",
                reply_to_message_id=message_id
            )
            return "ok"

        # Отправляем "печатает" для обратной связи
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendChatAction", 
                      json={'chat_id': chat_id, 'action': 'typing'})

        # Генерация ответа через Gemini
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=text
        )
        
        send_telegram_message(chat_id, response.text, reply_to_message_id=message_id)
        
    except APIError as e:
        print(f"Gemini API Error: {e}")
        send_telegram_message(chat_id, "Ошибка Gemini API. Проверьте ключ или логи Vercel.")
    except Exception as e:
        print(f"General Error: {e}")
        send_telegram_message(chat_id, "Произошла внутренняя ошибка. Попробуйте снова.")

    return "ok"

# Vercel-функция: Теперь она просто запускает приложение Flask
def handler(event, context):
    return app(event, context)
