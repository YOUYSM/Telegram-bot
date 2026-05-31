


import telebot
import requests
import os
import base64
import time
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

load_dotenv() 

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
GROQ_KEY = os.environ['GROQ_KEY']

bot = telebot.TeleBot(TELEGRAM_TOKEN)
chat_history = {}

# Flask server for Railway
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run)
    t.start()

def transcribe_audio(audio_file):
    try:
        res = requests.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"}, # yaha x nahi headers hoga
            files={"file": ("voice.ogg", audio_file, "audio/ogg")},
            data={"model": "whisper-large-v3"}
        )
        return res.json().get("text", "")
    except:
        return ""

def ai_reply(user_id, q, image_base64=None):
    if user_id not in chat_history:
        chat_history[user_id] = []

    if image_base64:
        api_content = [
            {"type": "text", "text": q},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
        ]
    else:
        api_content = q

    chat_history[user_id].append({"role": "user", "content": q})
    messages = chat_history[user_id][-4:].copy()

    system_prompt = {
        "role": "system",
        "content": "You are Kamal, an artificial intelligence. If someone asks 'who are you' or 'tum kon ho', reply exactly: 'bas mein ek artificial intelligence hun kaise tum.ho'. For other questions, act like a friend. Reply in 1-2 short lines. Talk in English. Don't repeat user's message. Use emoji only sometimes."
    }
    messages.insert(0, system_prompt)
    messages[-1] = {"role": "user", "content": api_content}

    model = "meta-llama/llama-4-scout-17b-16e-instruct" if image_base64 else "llama-3.1-8b-instant"
    temp = 0.3
    max_tok = 50 if image_base64 else 80

    try:
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={
                "model": model,
                "messages": messages,
                "temperature": temp,
                "max_tokens": max_tok
            },
            timeout=15
        )
        data = res.json()
        if 'error' in data:
            return None
    except:
        return None

    reply = data['choices'][0]['message']['content']
    chat_history[user_id].append({"role": "assistant", "content": reply})
    return reply

@bot.message_handler(commands=['start', 'clear'])
def start(message):
    chat_history[message.chat.id] = []
    bot.send_message(message.chat.id, "Yo, Kamal is here. What's up?")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    try:
        reply = ai_reply(message.chat.id, message.text)
        if reply:
            bot.send_message(message.chat.id, reply)
    except:
        pass

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        image_base64 = base64.b64encode(downloaded_file).decode('utf-8')
        caption = message.caption if message.caption else "Check this image and tell me what it is? Keep it short"
        reply = ai_reply(message.chat.id, caption, image_base64)
        if reply:
            bot.send_message(message.chat.id, reply)
    except:
        pass

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        text = transcribe_audio(downloaded_file)
        if text:
            reply = ai_reply(message.chat.id, text)
            if reply:
                bot.send_message(message.chat.id, reply)
    except:
        pass


if __name__ == "__main__":
    keep_alive()
    print("Bot started...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
