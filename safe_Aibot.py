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
        res = requests.post(url, headers=headers, json=data, timeout=15)
        reply = res.json()["choices"][0]["message"]["content"]
        memory[user_id].append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        print(e)
        return "❌ AI مش شغال دلوقتي"

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

    # 🔥 إشعار كامل للأدمن
    if is_new:
        msg = (
            f"🚨 مستخدم جديد\n\n"
            f"👤 الاسم: {user.first_name}\n"
            f"🆔 ID: {uid}\n"
            f"🔗 يوزر: @{user.username if user.username else 'None'}\n"
            f"🌍 اللغة: {user.language_code}\n"
            f"🕒 الوقت: {datetime.now()}"
        )
        for admin in ADMINS:
            try:
                await context.bot.send_message(admin, msg)
            except:
                pass

    # 👑 Admin
    if uid in ADMINS:
        await update.message.reply_text("👑 Admin Panel", reply_markup=admin_panel())
        return

    # 👤 User Welcome
    await update.message.reply_text(
        f"""
👋 أهلاً بيك يا {user.first_name}

🎓 أنا يوسف محمد عبدالماجد  
💻 طالب في جامعة ZNU  
🤖 كلية حاسبات و معلومات - قسم الذكاء الاصطناعي  

━━━━━━━━━━━━━━━
🤖 البوت جاهز يساعدك في:
• كتابة كود
• شرح
• حل مشاكل

👇 اضغط:
/start_bot
"""
    )

# ===== START BOT =====
async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🧠 DeepSeek", callback_data="deepseek")]
    ]
    await update.message.reply_text("اختار AI:", reply_markup=InlineKeyboardMarkup(keyboard))

# ===== BUTTONS =====
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_enabled, chat_enabled

    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data == "deepseek":
        context.user_data["ai"] = "deepseek"
        await q.edit_message_text("✅ تم اختيار DeepSeek\nابعت رسالتك")
        return

    if uid not in ADMINS:
        return

    if q.data == "users":
        await q.edit_message_text(f"👥 عدد المستخدمين: {len(users)}", reply_markup=admin_panel())

    elif q.data == "toggle_bot":
        bot_enabled = not bot_enabled
        await q.edit_message_text(f"Bot: {'ON' if bot_enabled else 'OFF'}", reply_markup=admin_panel())

    elif q.data == "toggle_chat":
        chat_enabled = not chat_enabled
        await q.edit_message_text(f"Chat: {'ON' if chat_enabled else 'OFF'}", reply_markup=admin_panel())

    elif q.data in ["ban", "unban", "broadcast"]:
        context.user_data["mode"] = q.data
        await q.edit_message_text("ابعت ID او رسالة")

# ===== MESSAGE =====
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if uid in banned or not bot_enabled:
        return

    # Admin modes
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

    # AI Chat
    if not chat_enabled:
        return

    if context.user_data.get("ai") is None:
        return await update.message.reply_text("⚠️ اكتب /start_bot الاول")

    msg = await update.message.reply_text("⏳ جاري التفكير...")

    reply = ask_ai(uid, update.message.text)

    await msg.edit_text(reply[:4000])

# ===== MAIN =====
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("start_bot", start_bot))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("🔥 BOT RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()
