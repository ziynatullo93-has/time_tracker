import telebot
from telebot import types
import requests

TOKEN = "8941576295:AAEQ9O6Im9UHBqJrnhALlsefT9qc0TfQI5w"
bot = telebot.TeleBot(TOKEN)

NGROK_URL = "https://time-tracker-hn9e.onrender.com/api/check-in"

user_actions = {}
user_locations = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📥 Приход"),
        types.KeyboardButton("📤 Уход"),
        types.KeyboardButton("☕ Перерыв"),
        types.KeyboardButton("🍽 Обед"),
        types.KeyboardButton("☕ Вернуться с перерыва"),
        types.KeyboardButton("🍽 Вернуться с обеда")
    )
    bot.send_message(
        message.chat.id, 
        "Привет! Выбери нужное действие:", 
        reply_markup=markup
    )

@bot.message_handler(content_types=['text', 'location', 'photo'])
def handle_messages(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or message.from_user.first_name
    
    # 1. Шаг выбора действия
    if message.text and any(act in message.text for act in ["Приход", "Уход", "Перерыв", "Обед", "Вернуться"]):
        user_actions[user_id] = message.text
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton("📍 Отправить геопозицию", request_location=True))
        
        bot.send_message(
            message.chat.id, 
            f"Ты выбрал: {message.text}. Теперь отправь свою геолокацию:", 
            reply_markup=markup
        )
        return

    # 2. Шаг получения геопозиции
    if message.location:
        action = user_actions.get(user_id, "")
        lat = message.location.latitude
        lon = message.location.longitude
        
        remove_markup = types.ReplyKeyboardRemove()

        # Если это Приход или Уход — просим фото
        if any(act in action for act in ["Приход", "Уход"]):
            user_locations[user_id] = {"lat": lat, "lon": lon}
            bot.send_message(
                message.chat.id, 
                "📍 Геопозиция получена! Теперь отправь фото:", 
                reply_markup=remove_markup
            )
            return

        # Для Перерыва, Обеда и Возвращения — сразу отправляем на сервер без фото!
        bot.send_message(message.chat.id, "⏳ Отправляю данные на сервер...", reply_markup=remove_markup)
        
        try:
            data = {
                "user_id": user_id,
                "username": username,
                "action": action,
                "latitude": lat,
                "longitude": lon
            }

            response = requests.post(NGROK_URL, data=data)
            res_json = response.json()

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(
                types.KeyboardButton("📥 Приход"),
                types.KeyboardButton("📤 Уход"),
                types.KeyboardButton("☕ Перерыв"),
                types.KeyboardButton("🍽 Обед"),
                types.KeyboardButton("☕ Вернуться с перерыва"),
                types.KeyboardButton("🍽 Вернуться с обеда")
            )

            if response.status_code == 200:
                bot.send_message(
                    message.chat.id, 
                    f"✅ Успешно сохранено! {res_json.get('duration_message', '')}", 
                    reply_markup=markup
                )
            else:
                bot.send_message(
                    message.chat.id, 
                    f"❌ Ошибка: {res_json.get('message', 'Неизвестная ошибка')}", 
                    reply_markup=markup
                )
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка связи с сервером: {e}")
        finally:
            user_actions.pop(user_id, None)
            user_locations.pop(user_id, None)
        return

    # 3. Шаг получения фото (только для Прихода и Ухода)
    if message.photo:
        if user_id not in user_actions or user_id not in user_locations:
            bot.send_message(message.chat.id, "⚠️ Сначала выбери действие и отправь геопозицию через /start")
            return

        action = user_actions[user_id]
        lat = user_locations[user_id]["lat"]
        lon = user_locations[user_id]["lon"]

        bot.send_message(message.chat.id, "⏳ Обрабатываю фото и отправляю на сервер...")

        try:
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)

            files = {'photo': ('photo.jpg', downloaded_file, 'image/jpeg')}
            data = {
                "user_id": user_id,
                "username": username,
                "action": action,
                "latitude": lat,
                "longitude": lon
            }

            response = requests.post(NGROK_URL, data=data, files=files)
            res_json = response.json()

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(
                types.KeyboardButton("📥 Приход"),
                types.KeyboardButton("📤 Уход"),
                types.KeyboardButton("☕ Перерыв"),
                types.KeyboardButton("🍽 Обед"),
                types.KeyboardButton("☕ Вернуться с перерыва"),
                types.KeyboardButton("🍽 Вернуться с обеда")
            )

            if response.status_code == 200:
                bot.send_message(
                    message.chat.id, 
                    f"✅ Успешно сохранено! {res_json.get('duration_message', '')}", 
                    reply_markup=markup
                )
            else:
                bot.send_message(
                    message.chat.id, 
                    f"❌ Ошибка: {res_json.get('message', 'Неизвестная ошибка')}", 
                    reply_markup=markup
                )
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка связи с сервером: {e}")
        finally:
            user_actions.pop(user_id, None)
            user_locations.pop(user_id, None)

if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()