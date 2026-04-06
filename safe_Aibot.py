import json
import requests
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ===== CONFIG =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEEPSEEK_KEYS = os.getenv("DEEPSEEK_KEYS").split(",")

ADMINS = [6157906511]

bot_enabled = True
chat_enabled = True

# ===== STORAGE =====
def load_users():
    try:
        with open("users.json", "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_users():
    with open("users.json", "w") as f:
        json.dump(list(users), f)

users = load_users()
banned = set()
memory = {}

# ===== AI =====
def ask_ai(text):
    key = DEEPSEEK_KEYS[0]

    url = "https://api.deepseek.com/chat/completions"

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": text}
        ]
    }

    try:
        res = requests.post(url, headers=headers, json=data)
        return res.json()["choices"][0]["message"]["content"]
    except:
        return "حصل خطأ في الرد 😢"

# ===== COMMANDS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in banned:
        return

    users.add(user_id)
    save_users()

    await update.message.reply_text("🤖 أهلا بيك في البوت!")

# ===== MESSAGE =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not chat_enabled:
        return

    user_id = update.effective_user.id

    if user_id in banned:
        return

    text = update.message.text

    await update.message.reply_text("⏳ جاري التفكير...")

    reply = ask_ai(text)

    await update.message.reply_text(reply)

# ===== MAIN =====
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🔥 BOT RUNNING...")

    app.run_polling()

if __name__ == "__main__":
    main()
