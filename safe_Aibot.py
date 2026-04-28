import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
MISTRAL_KEY = os.getenv("MISTRAL_KEY")

# ===== AI =====
def ask_mistral(text):
    try:
        res = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {MISTRAL_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistral-tiny",
                "messages": [{"role": "user", "content": text}]
            },
            timeout=15
        )

        data = res.json()
        print("Mistral:", data)

        if "error" in data:
            return f"❌ Error:\n{data['error']}"

        return data["choices"][0]["message"]["content"]

    except Exception as e:
        return f"❌ Exception:\n{str(e)}"


# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بيك\nاكتب /start_bot")

# ===== START BOT =====
async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔥 Mistral", callback_data="mistral")]
    ]
    await update.message.reply_text("اختار AI:", reply_markup=InlineKeyboardMarkup(keyboard))

# ===== BUTTON =====
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["ai"] = q.data
    await q.edit_message_text("✅ تم اختيار Mistral")

# ===== HANDLE =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ai = context.user_data.get("ai")

    if not ai:
        return await update.message.reply_text("اختار AI الأول")

    msg = await update.message.reply_text("⏳ جاري التفكير...")

    text = update.message.text

    reply = ask_mistral(text)

    await msg.edit_text(reply)


# ===== MAIN =====
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("start_bot", start_bot))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("🔥 BOT RUNNING WITH MISTRAL...")
    app.run_polling()


if __name__ == "__main__":
    main()
