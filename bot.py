import telebot
import requests
import base64
import os
from youtube_transcript_api import YouTubeTranscriptApi
import re

def extract_youtube_text(youtube_url):
    try:
        # استخراج ID الفيديو
        if "v=" in youtube_url:
            video_id = youtube_url.split("v=")[1].split("&")[0]
        else:
            video_id = youtube_url.split("/")[-1]

        transcript = YouTubeTranscriptApi.get_transcript(
            video_id, languages=['ar', 'en']
        )

        full_text = " ".join([entry['text'] for entry in transcript])
        return full_text

    except Exception as e:
        return None
def summarize_text(text):
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "اشرح الفيديو بشكل مبسط وواضح."},
            {"role": "user", "content": f"رجاءً اشرح هذا الفيديو:\n\n{text}"}
        ]
    }

    response = requests.post(url, headers=headers, json=payload).json()

    try:
        return response["choices"][0]["message"]["content"]
    except:
        return "⚠️ حدث خطأ أثناء الشرح."


# -----------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# -----------------------------------------------------

bot = telebot.TeleBot(BOT_TOKEN)

# 🔥 نموذج يدعم الصور 100%
MODEL = "openai/gpt-4o-mini"

SYSTEM_PROMPT = """
أنت مساعد ذكي متخصص في تحليل الصور وشرح تمارين البكالوريا
بدقة وبطريقة تعليمية مفصلة وواضحة.
عند إرسال صورة، قم باستخراج التمرين وشرحه بالكامل.
"""
# -----------------------------------------------------
YOUTUBE_REGEX = r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/(watch\?v=[\w-]+|shorts/[\w-]+|[\w-]+)"

# -----------------------------------------------------
def to_base64(image_bytes):
    return base64.b64encode(image_bytes).decode("utf-8")

# -----------------------------------------------------
def ask_openrouter(message_text, image_bytes=None):
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if image_bytes:
        base64_img = to_base64(image_bytes)
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": message_text},
                {
                    "type": "image_url",
                    "image_url": f"data:image/jpeg;base64,{base64_img}"
                }
            ]
        })
    else:
        messages.append({"role": "user", "content": message_text})

    data = {
        "model": MODEL,
        "messages": messages
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code != 200:
        return f"⚠️ خطأ في الاتصال بالخادم:\n{response.text}"

    return response.json()["choices"][0]["message"]["content"]

# -----------------------------------------------------
@bot.message_handler(commands=["start"])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📘 وضع البكالوريا", "🧠 وضع عام", "📸 حل تمرين من صورة")
    bot.send_message(message.chat.id, "مرحباً! 👋 اختر وضعك:", reply_markup=markup)

# -----------------------------------------------------
# استقبال الصور
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.send_message(message.chat.id, "⏳ يتم تحليل الصورة...")

    file_id = message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    downloaded = bot.download_file(file_info.file_path)

    answer = ask_openrouter("حل التمرين بالتفصيل:", image_bytes=downloaded)

    bot.send_message(message.chat.id, answer)

# -----------------------------------------------------
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    txt = message.text.strip()

    if txt == "📘 وضع البكالوريا":
        bot.send_message(message.chat.id, "🎓 تم تفعيل وضع البكالوريا. أرسل سؤالك.")
        return

    if txt == "🧠 وضع عام":
        bot.send_message(message.chat.id, "🤖 تم تفعيل الوضع العام.")
        return

    if txt == "📸 حل تمرين من صورة":
        bot.send_message(message.chat.id, "📤 أرسل الآن صورة التمرين.")
        return

    answer = ask_openrouter(txt)
    bot.send_message(message.chat.id, answer)

# -----------------------------------------------------
@bot.message_handler(func=lambda msg: "youtube.com" in msg.text or "youtu.be" in msg.text)
def handle_youtube(message):
    bot.reply_to(message, "⏳ جاري استخراج محتوى الفيديو...")

    url = message.text.strip()

    text = extract_youtube_text(url)

    if not text:
        bot.reply_to(message, "⚠️ لا يمكن استخراج نص الفيديو.\nقد يكون لا يحتوي على ترجمة.")
        return

    bot.reply_to(message, "📄 تم استخراج النص! جاري شرحه...")

    summary = summarize_text(text)

    bot.reply_to(message, summary)
# -----------------------------------------------------

print("🤖 Bot is running...")
bot.infinity_polling()
