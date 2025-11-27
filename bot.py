import telebot
import requests
import base64
from flask import Flask
import threading

# -----------------------------
# المتغيرات (يتم أخذها من Render)
# -----------------------------
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

MODEL = "openai/gpt-4o-mini"

SYSTEM_PROMPT = """
أنت مساعد ذكي متخصص في تحليل الصور وشرح تمارين البكالوريا بدقة وبشكل تعليمي.
عند إرسال صورة تمرين، قم باستخراج السؤال وشرحه كاملاً.
"""

bot = telebot.TeleBot(BOT_TOKEN)

# -----------------------------
# Flask Keep Alive
# -----------------------------
app = Flask(__name__)
@app.route("/")
def home():
    return "Bot is alive!"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

# -----------------------------
# Image to base64
# -----------------------------
def to_base64(image_bytes):
    return base64.b64encode(image_bytes).decode("utf-8")

# -----------------------------
# OpenRouter Request
# -----------------------------
def ask_openrouter(message_text, image_bytes=None):
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if image_bytes:
        b64 = to_base64(image_bytes)
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": message_text},
                {"type": "image_url", "image_url": f"data:image/jpeg;base64,{b64}"}
            ]
        })
    else:
        messages.append({"role": "user", "content": message_text})

    data = {"model": MODEL, "messages": messages}

    response = requests.post(url, json=data, headers=headers)

    if response.status_code != 200:
        return f"⚠️ خطأ:\n{response.text}"

    return response.json()["choices"][0]["message"]["content"]

# -----------------------------
# Bot Handlers
# -----------------------------
@bot.message_handler(commands=["start"])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📘 وضع البكالوريا", "🧠 وضع عام", "📸 حل تمرين من صورة")
    bot.send_message(message.chat.id, "مرحباً! 👋 اختر وضعك:", reply_markup=markup)

@bot.message_handler(content_types=["photo"])
def photo(message):
    bot.send_message(message.chat.id, "⏳ يتم تحليل الصورة...")
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    downloaded = bot.download_file(file_info.file_path)

    answer = ask_openrouter("حل التمرين بالتفصيل:", image_bytes=downloaded)
    bot.send_message(message.chat.id, answer)

@bot.message_handler(func=lambda m: True)
def text_handler(message):
    txt = message.text

    if txt == "📘 وضع البكالوريا":
        bot.send_message(message.chat.id, "🎓 تم تفعيل وضع البكالوريا.")
        return

    if txt == "🧠 وضع عام":
        bot.send_message(message.chat.id, "🤖 تم تفعيل الوضع العام.")
        return

    if txt == "📸 حل تمرين من صورة":
        bot.send_message(message.chat.id, "📤 أرسل صورة التمرين الآن.")
        return

    answer = ask_openrouter(txt)
    bot.send_message(message.chat.id, answer)

# -----------------------------
# تشغيل Flask + Bot Polling
# -----------------------------
print("🤖 Bot is running...")

threading.Thread(target=run_flask).start()
bot.infinity_polling()
