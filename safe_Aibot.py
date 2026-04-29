import os
import json
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ===== CONFIG =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEYS")
MISTRAL_KEY = os.getenv("MISTRAL_KEY")

ADMINS = [6157906511]

users = set()
banned = set()
memory = {}
user_ai = {}

# ===== AI =====
def ask_deepseek(uid, text):
    try:
        if uid not in memory:
            memory[uid] = []

        memory[uid].append({"role": "user", "content": text})

        res = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
            json={
                "model": "deepseek-chat",
                "messages": memory[uid][-10:]
            }
        )

        data = res.json()

        if "error" in data:
            return f"❌ {data['error']}"

        reply = data["choices"][0]["message"]["content"]
        memory[uid].append({"role": "assistant", "content": reply})
        return reply

    except:
        return "❌ حصل خطأ"

def ask_mistral(text):
    try:
        res = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {MISTRAL_KEY}"},
            json={
                "model": "mistral-tiny",
                "messages": [{"role": "user", "content": text}]
            }
        )

        data = res.json()

        if "error" in data:
            return f"❌ {data['error']}"

        return data["choices"][0]["message"]["content"]

    except:
        return "❌ حصل خطأ"

# ===== MENUS =====
def ai_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧠 DeepSeek", callback_data="deepseek")],
        [InlineKeyboardButton("🔥 Mistral", callback_data="mistral")]
    ])

def admin_panel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Users", callback_data="users")],
        [InlineKeyboardButton("🚫 Ban", callback_data="ban"),
         InlineKeyboardButton("✅ Unban", callback_data="unban")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")]
    ])

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id

    users.add(uid)

    if uid in ADMINS:
        await update.message.reply_text("👑 Admin Panel", reply_markup=admin_panel())
        return

    await update.message.reply_text(f"""
👋 أهلاً بيك يا {user.first_name}

👨‍💻 يوسف محمد عبدالماجد  
🎓 طالب في جامعة ZNU  
💻 كلية حاسبات و معلومات  
🤖 قسم الذكاء الاصطناعي  

━━━━━━━━━━━━━━━
👇 اضغط:
/start_bot
""")

# ===== START BOT =====
async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("اختار AI:", reply_markup=ai_menu())

# ===== BUTTONS =====
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data in ["deepseek", "mistral"]:
        user_ai[uid] = q.data
        await q.edit_message_text(f"✅ اخترت {q.data}\nابعت رسالتك")
        return

    if uid not in ADMINS:
        return

    if q.data == "users":
        await q.edit_message_text(f"👥 {len(users)}", reply_markup=admin_panel())

    elif q.data == "ban":
        context.user_data["mode"] = "ban"
        await q.edit_message_text("ابعت ID")

    elif q.data == "unban":
        context.user_data["mode"] = "unban"
        await q.edit_message_text("ابعت ID")

    elif q.data == "broadcast":
        context.user_data["mode"] = "broadcast"
        await q.edit_message_text("ابعت الرسالة")

# ===== HANDLE =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid in banned:
        return

    mode = context.user_data.get("mode")

    if mode == "ban":
        banned.add(int(update.message.text))
        await update.message.reply_text("🚫 تم")
        context.user_data["mode"] = None
        return

    if mode == "unban":
        banned.discard(int(update.message.text))
        await update.message.reply_text("✅ تم")
        context.user_data["mode"] = None
        return

    if mode == "broadcast":
        for u in users:
            try:
                await context.bot.send_message(u, update.message.text)
            except:
                pass
        await update.message.reply_text("📢 تم")
        context.user_data["mode"] = None
        return

    ai = user_ai.get(uid)

    if not ai:
        return await update.message.reply_text("⚠️ اختار AI الأول /start_bot")

    msg = await update.message.reply_text("⏳")

    text = update.message.text

    if ai == "deepseek":
        reply = ask_deepseek(uid, text)
    else:
        reply = ask_mistral(text)

    await msg.edit_text(reply)

# ===== PHOTO =====
async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("🤖 بحاول افهم الصورة...")

        # هنا مؤقت لحد ما نربط AI vision
        await update.message.reply_text("📸 دي صورة... بس فيه مشكلة في الصور دلوقتي 😅")

    except:
        await update.message.reply_text("❌ فيه مشكلة في الصور دلوقتي")

# ===== MAIN =====
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("start_bot", start_bot))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.add_handler(MessageHandler(filters.PHOTO, photo))

    print("🔥 BOT RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()
