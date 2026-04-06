import json
import requests
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ===== CONFIG =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEEPSEEK_KEYS = os.getenv("DEEPSEEK_KEYS", "").split(",")

ADMINS = [6157906511]

memory = {}

# ===== STORAGE =====
def load_data(file):
    try:
        with open(file, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(list(data), f)

users = load_data("users.json")

# ===== AI =====
def ask_ai(user_id, text):
    key = DEEPSEEK_KEYS[0]

    if user_id not in memory:
        memory[user_id] = []

    memory[user_id].append({"role": "user", "content": text})

    url = "https://api.deepseek.com/chat/completions"

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",
        "messages": memory[user_id][-10:]
    }

    try:
        res = requests.post(url, headers=headers, json=data)
        reply = res.json()["choices"][0]["message"]["content"]

        memory[user_id].append({"role": "assistant", "content": reply})

        return reply
    except:
        return "❌ AI مش شغال"

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id

    users.add(uid)
    save_data("users.json", users)

    await update.message.reply_text(
        "👋 أهلاً بيك في البوت 🤖\n\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 تقدر تتكلم مع AI بسهولة\n"
        "━━━━━━━━━━━━━━━\n\n"
        "🎓 Designed by:\n"
        "يوسف محمد عبدالماجد\n"
        "طالب في جامعة ZNU\n"
        "كلية حاسبات و معلومات\n"
        "قسم الذكاء الاصطناعي\n\n"
        "▶️ اكتب /start_bot لبدء الاستخدام"
    )

# ===== AI MENU =====
async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🧠 DeepSeek", callback_data="deepseek")]
    ]

    await update.message.reply_text(
        "🤖 اختار الـ AI:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===== BUTTONS =====
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "deepseek":
        context.user_data["ai"] = "deepseek"
        await q.edit_message_text("✅ تم اختيار DeepSeek\nابعت رسالتك")

# ===== MESSAGE =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if context.user_data.get("ai") != "deepseek":
        await update.message.reply_text("⚠️ اكتب /start_bot واختار AI الأول")
        return

    msg = await update.message.reply_text("⏳ جاري التفكير...")

    reply = ask_ai(uid, update.message.text)

    await msg.edit_text(reply)

# ===== MAIN =====
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("start_bot", start_bot))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("🔥 BOT RUNNING PRO FLOW...")

    app.run_polling()

if __name__ == "__main__":
    main()
