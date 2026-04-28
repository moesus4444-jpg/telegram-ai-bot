import json
import os
import aiohttp
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ===== CONFIG =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEEPSEEK_KEYS = os.getenv("DEEPSEEK_KEYS", "").split(",")
GROQ_KEY = os.getenv("GROQ_KEY")
MISTRAL_KEY = os.getenv("MISTRAL_KEY")

ADMINS = [6157906511]

bot_enabled = True
chat_enabled = True
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
banned = load_data("banned.json")

# ===== AI =====
async def ask_deepseek(user_id, text):
    try:
        key = DEEPSEEK_KEYS[0]

        if user_id not in memory:
            memory[user_id] = []

        memory[user_id].append({"role": "user", "content": text})

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.deepseek.com/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": memory[user_id][-10:]
                }
            ) as res:
                data = await res.json()

        if "choices" not in data:
            return None

        reply = data["choices"][0]["message"]["content"]
        memory[user_id].append({"role": "assistant", "content": reply})

        return reply

    except:
        return None


async def ask_groq(text):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama3-8b-8192",
                    "messages": [
                        {"role": "system", "content": "اتكلم مصري"},
                        {"role": "user", "content": text}
                    ]
                }
            ) as res:
                data = await res.json()

        return data["choices"][0]["message"]["content"]

    except:
        return None


async def ask_mistral(text):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {MISTRAL_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "mistral-small",
                    "messages": [
                        {"role": "user", "content": text}
                    ]
                }
            ) as res:
                data = await res.json()

        return data["choices"][0]["message"]["content"]

    except:
        return None


# ===== FORMAT =====
def format_code(text):
    if "def " in text or "import " in text or "class " in text:
        return f"```python\n{text}\n```"
    return text


async def send_long_message(update, msg, reply):
    reply = format_code(reply)
    parts = [reply[i:i+3500] for i in range(0, len(reply), 3500)]

    await msg.edit_text(parts[0], parse_mode="Markdown")

    for part in parts[1:]:
        await update.message.reply_text(part, parse_mode="Markdown")


# ===== ADMIN PANEL =====
def admin_panel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Users", callback_data="users"),
         InlineKeyboardButton("🚫 Ban", callback_data="ban")],

        [InlineKeyboardButton("✅ Unban", callback_data="unban"),
         InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],

        [InlineKeyboardButton("🔌 Bot ON/OFF", callback_data="toggle_bot"),
         InlineKeyboardButton("💬 Chat ON/OFF", callback_data="toggle_chat")]
    ])


# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id

    is_new = uid not in users
    users.add(uid)
    save_data("users.json", users)

    if is_new:
        msg = f"🚨 مستخدم جديد\n\n👤 {user.first_name}\n🆔 {uid}"
        for admin in ADMINS:
            try:
                await context.bot.send_message(admin, msg)
            except:
                pass

    if uid in ADMINS:
        await update.message.reply_text("👑 Admin Panel", reply_markup=admin_panel())
        return

    await update.message.reply_text("👋 أهلاً بيك\nاكتب /start_bot")


# ===== START BOT =====
async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🧠 DeepSeek", callback_data="deepseek")],
        [InlineKeyboardButton("⚡ Groq", callback_data="groq")],
        [InlineKeyboardButton("🔥 Mistral", callback_data="mistral")]
    ]
    await update.message.reply_text("اختار AI:", reply_markup=InlineKeyboardMarkup(keyboard))


# ===== BUTTONS =====
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_enabled, chat_enabled

    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data in ["deepseek", "groq", "mistral"]:
        context.user_data["ai"] = q.data
        await q.edit_message_text(f"✅ اخترت {q.data}")
        return

    if uid not in ADMINS:
        return

    if q.data == "users":
        await q.edit_message_text(f"👥 {len(users)}", reply_markup=admin_panel())

    elif q.data == "toggle_bot":
        bot_enabled = not bot_enabled
        await q.edit_message_text(f"Bot: {bot_enabled}", reply_markup=admin_panel())

    elif q.data == "toggle_chat":
        chat_enabled = not chat_enabled
        await q.edit_message_text(f"Chat: {chat_enabled}", reply_markup=admin_panel())

    elif q.data in ["ban", "unban", "broadcast"]:
        context.user_data["mode"] = q.data
        await q.edit_message_text("ابعت ID او رسالة")


# ===== MESSAGE =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid in banned or not bot_enabled:
        return

    mode = context.user_data.get("mode")

    if mode == "ban":
        banned.add(int(update.message.text))
        save_data("banned.json", banned)
        await update.message.reply_text("🚫 تم الحظر")
        context.user_data["mode"] = None
        return

    if mode == "unban":
        banned.discard(int(update.message.text))
        save_data("banned.json", banned)
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

    if not chat_enabled:
        return

    ai = context.user_data.get("ai")
    if not ai:
        return await update.message.reply_text("اختار AI الاول")

    msg = await update.message.reply_text("⏳ بفكر...")

    text = update.message.text

    if ai == "deepseek":
        reply = await ask_deepseek(uid, text)
    elif ai == "groq":
        reply = await ask_groq(text)
    elif ai == "mistral":
        reply = await ask_mistral(text)
    else:
        reply = "❌ خطأ"

    if not reply:
        reply = "❌ AI مش بيرد حالياً"

    await send_long_message(update, msg, reply)


# ===== PHOTO =====
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await photo.get_file()

    os.makedirs("photos", exist_ok=True)
    path = f"photos/{update.effective_user.id}.jpg"

    await file.download_to_drive(path)
    await update.message.reply_text("📸 الصورة اتحفظت")


# ===== MAIN =====
def main():
    app = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("start_bot", start_bot))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("🔥 BOT RUNNING...")
    app.run_polling()


if __name__ == "__main__":
    main()
