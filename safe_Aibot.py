import os
import json
import aiohttp
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEYS")

ADMINS = [6157906511]

users = set()
banned = set()
memory = {}
last_request = {}

# ===== AI =====
async def ask_ai(user_id, text):
    try:
        if user_id not in memory:
            memory[user_id] = []

        memory[user_id].append({"role": "user", "content": text})

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.deepseek.com/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": memory[user_id][-10:]
                }
            ) as res:
                data = await res.json()

        if "error" in data:
            return f"❌ {data['error']}"

        reply = data["choices"][0]["message"]["content"]
        memory[user_id].append({"role": "assistant", "content": reply})

        return reply

    except Exception as e:
        return f"❌ Error: {str(e)}"


# ===== ADMIN PANEL =====
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

    await update.message.reply_text(
        f"""
👋 أهلاً بيك يا {user.first_name}

🤖 أنا بوت يوسف AI
💻 بساعدك في:
- كود
- شرح
- أسئلة

اكتب /start_bot
"""
    )


# ===== START BOT =====
async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 البوت جاهز... ابعت سؤالك")


# ===== BUTTONS =====
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id

    if uid not in ADMINS:
        return

    if q.data == "users":
        await q.edit_message_text(f"👥 عدد المستخدمين: {len(users)}", reply_markup=admin_panel())

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

    # Anti spam
    now = datetime.now().timestamp()
    if uid in last_request and now - last_request[uid] < 1:
        return await update.message.reply_text("استنى ثانية 😅")
    last_request[uid] = now

    mode = context.user_data.get("mode")

    if mode == "ban":
        banned.add(int(update.message.text))
        await update.message.reply_text("🚫 تم الحظر")
        context.user_data["mode"] = None
        return

    if mode == "unban":
        banned.discard(int(update.message.text))
        await update.message.reply_text("✅ تم فك الحظر")
        context.user_data["mode"] = None
        return

    if mode == "broadcast":
        for u in users:
            try:
                await context.bot.send_message(u, update.message.text)
            except:
                pass
        await update.message.reply_text("📢 تم الإرسال")
        context.user_data["mode"] = None
        return

    msg = await update.message.reply_text("⏳ جاري التفكير...")

    reply = await ask_ai(uid, update.message.text)

    await msg.edit_text(reply)


# ===== PHOTO =====
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await photo.get_file()

    os.makedirs("photos", exist_ok=True)
    path = f"photos/{update.effective_user.id}.jpg"

    await file.download_to_drive(path)
    await update.message.reply_text("📸 تم حفظ الصورة")


# ===== MAIN =====
def main():
    app = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("start_bot", start_bot))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("🔥 Youssef AI BOT V1 RUNNING...")
    app.run_polling()


if __name__ == "__main__":
    main()
