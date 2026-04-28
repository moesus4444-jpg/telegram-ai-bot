import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEYS")
MISTRAL_KEY = os.getenv("MISTRAL_KEY")

# ===== SAFE REQUEST =====
def safe_request(url, headers, payload):
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)

        try:
            data = res.json()
        except:
            return f"❌ Invalid JSON:\n{res.text}"

        print("API RESPONSE:", data)

        # لو فيه error
        if "error" in data:
            return f"❌ API Error:\n{data['error']}"

        # لو مفيش choices
        if "choices" not in data:
            return f"❌ Unexpected Response:\n{data}"

        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"❌ Exception:\n{str(e)}"


# ===== AI =====
def ask_deepseek(text):
    return safe_request(
        "https://api.deepseek.com/chat/completions",
        {
            "Authorization": f"Bearer {DEEPSEEK_KEY}",
            "Content-Type": "application/json"
        },
        {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": text}]
        }
    )


def ask_mistral(text):
    return safe_request(
        "https://api.mistral.ai/v1/chat/completions",
        {
            "Authorization": f"Bearer {MISTRAL_KEY}",
            "Content-Type": "application/json"
        },
        {
            "model": "mistral-tiny",
            "messages": [{"role": "user", "content": text}]
        }
    )


# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بيك\nاكتب /start_bot")

# ===== SELECT AI =====
async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("DeepSeek", callback_data="deepseek")],
        [InlineKeyboardButton("Mistral", callback_data="mistral")]
    ]
    await update.message.reply_text("اختار AI:", reply_markup=InlineKeyboardMarkup(keyboard))

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["ai"] = q.data
    await q.edit_message_text(f"✅ اخترت {q.data}")

# ===== HANDLE =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ai = context.user_data.get("ai")

    if not ai:
        return await update.message.reply_text("اختار AI الأول")

    msg = await update.message.reply_text("⏳ جاري التفكير...")

    text = update.message.text

    if ai == "deepseek":
        reply = ask_deepseek(text)
    else:
        reply = ask_mistral(text)

    await msg.edit_text(reply)


# ===== MAIN =====
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("start_bot", start_bot))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("🔥 BOT RUNNING FINAL...")
    app.run_polling()


if __name__ == "__main__":
    main()
