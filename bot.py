import telebot
import requests
import base64
from flask import Flask
import threading
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

MODEL = "openai/gpt-4o-mini"

SYSTEM_PROMPT = """
أنت مساعد ذكي متخصص في تحليل الصور وشرح تمارين البكالوريا بدقة.
عند إرسال صورة، قم باستخراج التمرين وشرحه بالكامل بطريقة تعليمية مفصلة.
"""

bot = telebot.TeleBot(BOT_TOKEN)

def ask_openrouter(text=None, image=None):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if text:
        messages.append({"role": "user", "content": text})

    if image:
        with open(image, "rb") as img:
            b64 = base64.b64encode(img.read()).decode("utf-8")

        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": "حلل هذه الصورة:"},
                {"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"}
            ]
        })

    data = {"model": MODEL, "messages": messages}

    response = requests.post(url, headers=headers, json=data)
    return response.json()["choices"][0]["message"]["content"]


@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "مرحباً 👋\nأنا بوت تحليل الصور وتمارين البكالوريا.\nأرسل صورة أو نص وسأحلله فوراً!")


@bot.message_handler(content_types=["photo"])
def photo_handler(message):
    file_info = bot.get_file(message.photo[-1].file_id)
    file_path = file_info.file_path
    downloaded_file = bot.download_file(file_path)

    img_name = "image.jpg"
    with open(img_name, "wb") as new_file:
        new_file.write(downloaded_file)

    bot.reply_to(message, "يتم تحليل الصورة ⏳…")

    answer = ask_openrouter(image=img_name)
    bot.send_message(message.chat.id, answer)


@bot.message_handler(func=lambda m: True)
def text_handler(message):
    answer = ask_openrouter(text=message.text)
    bot.reply_to(message, answer)


def polling_thread():
    bot.infinity_polling()


threading.Thread(target=polling_thread).start()


app = Flask(name)

@app.route("/")
def home():
    return "Bot is running!"


if name == "main":
    app.run(host="0.0.0.0", port=8000)
