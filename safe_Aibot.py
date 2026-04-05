import json
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ================= CONFIG =================
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEEPSEEK_KEYS = os.getenv("DEEPSEEK_KEYS").split(",")
ADMINS = [6157906511]

bot_enabled = True
chat_enabled = True

# ================= STORAGE =================
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

# ================= AI =================
def ask_ai(user_id, text):
    url = "https://api.deepseek.com/chat/completions"

    if user_id not in memory:
        memory[user_id] = []

    memory[user_id].append({"role": "user", "content": text})

    for key in DEEPSEEK_KEYS:
        try:
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": "deepseek-chat",
                "messages": memory[user_id][-10:]
            }

            res = requests.post(url, headers=headers, json=data)
            reply = res.json()["choices"][0]["message"]["content"]

            memory[user_id].append({"role": "assistant", "content": reply})
            return reply

        except:
            continue

    return "⚠️ AI مش شغال حالياً"

# ================= KEYBOARDS =================
def ai_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧠 DeepSeek", callback_data="deepseek")]
    ])

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Users", callback_data="stats"),
         InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],

        [InlineKeyboardButton("🚫 Ban", callback_data="ban"),
         InlineKeyboardButton("✅ Unban", callback_data="unban")],

        [InlineKeyboardButton("🔌 Bot ON/OFF", callback_data="toggle_bot"),
         InlineKeyboardButton("💬 Chat ON/OFF", callback_data="toggle_chat")],

        [InlineKeyboardButton("🔍 User Info", callback_data="info")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ])

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id

    is_new = uid not in users
    users.add(uid)
    save_users()

    # Admin panel
    if uid in ADMINS:
        await update.message.reply_text("⚙️ Admin Panel", reply_markup=admin_keyboard())
        return

    # New user notification
    if is_new:
        username = f"@{user.username}" if user.username else "No Username"
        lang = user.language_code if user.language_code else "Unknown"
        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        msg = (
            "🚨 New User Joined\n\n"
            f"👤 Name: {user.first_name}\n"
            f"🔗 Username: {username}\n"
            f"🆔 ID: {uid}\n"
            f"🌍 Language: {lang}\n"
            f"🕒 Time: {time_now}\n"
            f"📩 Profile: tg://user?id={uid}"
        )

        for admin in ADMINS:
            try:
                await context.bot.send_message(admin, msg)
            except:
                pass

    # Welcome message
    await update.message.reply_text(
        "👋 أهلاً بيك في البوت 🤖\n\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 البوت بيدعم الذكاء الاصطناعي\n"
        "━━━━━━━━━━━━━━━\n\n"
        "🎓 Designed by:\n"
        "يوسف محمد عبدالماجد\n"
        "طالب في جامعة ZNU\n"
        "كلية حاسبات ومعلومات\n"
        "قسم الذكاء الاصطناعي\n\n"
        "▶️ اكتب /start_bot علشان تبدأ"
    )

# ================= START BOT =================
async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 اختار الـ AI:",
        reply_markup=ai_keyboard()
    )

# ================= BUTTONS =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_enabled, chat_enabled

    q = update.callback_query
    await q.answer()

    uid = q.from_user.id

    # AI selection
    if q.data == "deepseek":
        context.user_data["ai"] = "deepseek"
        await q.edit_message_text("✅ تم اختيار DeepSeek\nابعت رسالتك")

    # Admin only
    if uid not in ADMINS:
        return

    data = q.data

    if data == "stats":
        await q.edit_message_text(f"👥 Users: {len(users)}", reply_markup=admin_keyboard())

    elif data == "toggle_bot":
        bot_enabled = not bot_enabled
        await q.edit_message_text(
            f"Bot: {'ON ✅' if bot_enabled else 'OFF ❌'}",
            reply_markup=admin_keyboard()
        )

    elif data == "toggle_chat":
        chat_enabled = not chat_enabled
        await q.edit_message_text(
            f"Chat: {'ON ✅' if chat_enabled else 'OFF ❌'}",
            reply_markup=admin_keyboard()
        )

    elif data in ["broadcast", "ban", "unban", "info"]:
        context.user_data["mode"] = data
        await q.edit_message_text(f"Send {data} input:", reply_markup=admin_keyboard())

    elif data == "back":
        context.user_data["mode"] = None
        await q.edit_message_text("⚙️ Admin Panel", reply_markup=admin_keyboard())

# ================= MESSAGE =================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if not bot_enabled or uid in banned:
        return

    if not chat_enabled:
        await update.message.reply_text("🚫 الشات مقفول حالياً")
        return

    if context.user_data.get("ai") != "deepseek":
        await update.message.reply_text("⚠️ اختار AI الأول من /start_bot")
        return

    text = update.message.text

    msg = await update.message.reply_text("⏳ جاري التفكير...")

    reply = ask_ai(uid, text)

    await msg.edit_text(reply)

# ================= IMAGE =================
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 البوت حالياً لا يدعم الصور")

# ================= ADMIN INPUT =================
async def admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return

    mode = context.user_data.get("mode")
    text = update.message.text

    if not mode:
        return

    if mode == "broadcast":
        for u in users:
            try:
                await context.bot.send_message(u, text)
            except:
                pass
        await update.message.reply_text("✅ Done")

    elif mode == "ban":
        banned.add(int(text))
        await update.message.reply_text("🚫 Banned")

    elif mode == "unban":
        banned.discard(int(text))
        await update.message.reply_text("✅ Unbanned")

    elif mode == "info":
        uid = int(text)
        await update.message.reply_text(
            f"User: {uid}\nBanned: {uid in banned}\nIn DB: {uid in users}"
        )

    context.user_data["mode"] = None

# ================= RUN =================
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("start_bot", start_bot))

app.add_handler(CallbackQueryHandler(buttons))

app.add_handler(MessageHandler(filters.PHOTO, handle_image))
app.add_handler(MessageHandler(filters.TEXT & filters.User(ADMINS), admin_input))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("🔥 BOT RUNNING FINAL PRO...")
app.run_polling()