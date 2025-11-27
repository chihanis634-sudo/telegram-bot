import telebot
import requests
import base64
import os

# قراءة التوكنات من المتغيرات البيئية في Koyeb
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)

MODEL = "meta-llama/llama-3.2-vision-instruct"

# -----------------------------
# دالة تحليل النصوص
# -----------------------------
def analyze_text(text):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": text}],
    }

    response = requests.post(url, headers=headers, json=data)
    result = response.json()

    return result["choices"][0]["message"]["content"]

# -----------------------------
# دالة تحليل الصور
# -----------------------------
def analyze_image(image_url):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "model": MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "input_text", "text": "حلل ما في هذه الصورة بالتفصيل."},
                {"type": "input_image", "image_url": image_url}
            ]
        }]
    }

    response = requests.post(url, headers=headers, json=data)
    result = response.json()

    return result["choices"][0]["message"]["content"]

# -----------------------------
# استقبال الصور
# -----------------------------
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    image_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"

    bot.reply_to(message, "📷 يتم تحليل الصورة...")

    try:
        result = analyze_image(image_url)
        bot.reply_to(message, result)
    except Exception as e:
        bot.reply_to(message, f"⚠️ حدث خطأ أثناء تحليل الصورة:\n{e}")

# -----------------------------
# استقبال النصوص
# -----------------------------
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    bot.reply_to(message, "⏳ يتم التحليل...")

    try:
        result = analyze_text(message.text)
        bot.reply_to(message, result)
    except Exception as e:
        bot.reply_to(message, f"⚠️ حدث خطأ أثناء تحليل النص:\n{e}")

# -----------------------------
# تشغيل البوت
# -----------------------------
bot.polling(none_stop=True)
