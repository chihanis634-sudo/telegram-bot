import telebot
import requests
import base64
import threading
from flask import Flask
import os
import time

# أخذ التوكنات من Koyeb (Environment variables)
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ============================
# إعدادات النموذج
# ============================
MODEL = "openai/gpt-4o-mini"

SYSTEM_PROMPT = """
أنت مساعد ذكي متخصص في تحليل الصور وشرحها بدقة.
"""

# ============================
# قاعدة بيانات بسيطة (VIP + آخر رد)
# ============================
user_last_answer = {}          # آخر نتيجة لكل مستخدم
VIP_USERS = {123456789, 987654321}  # ضع هنا IDs المستخدمين VIP

# ============================
# وضع الكتابة
# ============================
def typing(chat_id, seconds=2):
    bot.send_chat_action(chat_id, "typing")
    time.sleep(seconds)

# ============================
# أوامر البوت
# ============================

@bot.message_handler(commands=['start'])
def start_cmd(msg):
    bot.reply_to(msg, 
        "<b>مرحباً! 👋</b>\n"
        "أنا بوت تحليل الصور وشرحها بدقة.\n"
        "أرسل صورة أو نص وسيتم التحليل فوراً."
    )

@bot.message_handler(commands=['help'])
def help_cmd(msg):
    bot.reply_to(msg,
        "<b>الأوامر المتاحة:</b>\n"
        "/start - بدء الاستخدام\n"
        "/help - قائمة الأوامر\n"
        "/vip - معرفة وضع VIP\n"
        "/last - استرجاع آخر شرح"
    )

@bot.message_handler(commands=['vip'])
def vip_cmd(msg):
    uid = msg.from_user.id
    if uid in VIP_USERS:
        bot.reply_to(msg, "⭐ <b>أنت VIP</b>\nيمكنك استخدام البوت بلا قيود.")
    else:
        bot.reply_to(msg, "❌ لست VIP حالياً.\nيمكنك طلب الترقية من صاحب البوت.")

@bot.message_handler(commands=['last'])
def last_cmd(msg):
    uid = msg.from_user.id
    if uid in user_last_answer:
        bot.reply_to(msg, "<b>آخر نتيجة لك:</b>\n" + user_last_answer[uid])
    else:
        bot.reply_to(msg, "لا يوجد تاريخ سابق لك.")

# ============================
# تحليل النصوص
# ============================
def ask_openrouter(question):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ]
    }

    r = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
    data = r.json()
    return data["choices"][0]["message"]["content"]

# ============================
# استقبال النصوص
# ============================
@bot.message_handler(content_types=['text'])
def handle_text(msg):
    chat_id = msg.chat.id
    typing(chat_id)

    answer = ask_openrouter(msg.text)
    user_last_answer[msg.from_user.id] = answer

    bot.reply_to(msg, answer)

# ============================
# استقبال الصور
# ============================
@bot.message_handler(content_types=['photo'])
def handle_photo(msg):
    chat_id = msg.chat.id
    typing(chat_id)

    file_id = msg.photo[-1].file_id
    file_info = bot.get_file(file_id)
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
    image_data = requests.get(file_url).content
    encoded_image = base64.b64encode(image_data).decode()

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "حلل هذه الصورة بالتفصيل"},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{encoded_image}"
                    }
                ]
            }
        ]
    }

    r = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
    result = r.json()["choices"][0]["message"]["content"]

    user_last_answer[msg.from_user.id] = result
    bot.reply_to(msg, result)

# ============================
# تشغيل البوت Thread + Flask (ضروري لـ Koyeb)
# ============================

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_bot():
    bot.infinity_polling()

threading.Thread(target=run_bot).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
