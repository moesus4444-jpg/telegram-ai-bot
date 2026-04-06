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
        res = requests.post(url, headers=headers, json=data)
        reply = res.json()["choices"][0]["message"]["content"]
        memory[user_id].append({"role": "assistant", "content": reply})
        return reply
    except:
        return "❌ AI مش شغال"

# ===== ADMIN PANEL =====
def admin_panel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Users", callback_data="stats"),
         InlineKeyboardButton("🚫 Ban", callback_data="ban")],

        [InlineKeyboardButton("✅ Unban", callback_data="unban"),
         InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],

        [InlineKeyboardButton("🔌 Bot ON/OFF", callback_data="toggle_bot"),
         InlineKeyboardButton("💬 Chat ON/OFF", callback_data="toggle_chat")],

        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ])

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id

    is_new = uid not in users
    users.add(uid)
    save_data("users.json", users)

    # إشعار للأدمن
    if is_new:
        msg = (
            f"🚨 New User\n\n"
            f"👤 {user.first_name}\n"
            f"🆔 {uid}\n"
            f"🔗 @{user.username if user.username else 'None'}\n"
            f"🌍 {user.language_code}\n"
            f"🕒 {datetime.now()}"
        )
        for admin in ADMINS:
            try:
                await context.bot.send_message(admin, msg)
            except:
                pass

    # Admin
    if uid in ADMINS:
        await update.message.reply_text("👑 Admin Panel", reply_markup=admin_panel())
        return

    # User Welcome
    await update.message.reply_text(
        "👋 أهلاً بيك 🤖\n\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 البوت بيدعم الذكاء الاصطناعي\n"
        "━━━━━━━━━━━━━━━\n\n"
        "🎓 Designed by:\n"
        "يوسف محمد عبدالماجد\n"
        "طالب في جامعة ZNU\n"
        "كلية حاسبات و معلومات\n"
        "قسم الذكاء الاصطناعي\n\n"
        "▶️ اكتب /start_bot للبدء"
    )

# ===== START BOT =====
async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🧠 DeepSeek", callback_data="deepseek")]
    ]
    await update.message.reply_text("🤖 اختار AI:", reply_markup=InlineKeyboardMarkup(keyboard))

# ===== BUTTONS =====
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_enabled, chat_enabled

    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    # اختيار AI
    if q.data == "deepseek":
        context.user_data["ai"] = "deepseek"
        await q.edit_message_text("✅ تم اختيار DeepSeek\nابعت رسالتك")
        return

    # Admin فقط
    if uid not in ADMINS:
        return

    if q.data == "stats":
        await q.edit_message_text(f"👥 Users: {len(users)}", reply_markup=admin_panel())

    elif q.data == "toggle_bot":
        bot_enabled = not bot_enabled
        await q.edit_message_text(f"Bot: {'ON' if bot_enabled else 'OFF'}", reply_markup=admin_panel())

    elif q.data == "toggle_chat":
        chat_enabled = not chat_enabled
        await q.edit_message_text(f"Chat: {'ON' if chat_enabled else 'OFF'}", reply_markup=admin_panel())

    elif q.data in ["ban", "unban", "broadcast"]:
        context.user_data["mode"] = q.data
        await q.edit_message_text("Send ID or Message")

    elif q.data == "back":
        await q.edit_message_text("👑 Admin Panel", reply_markup=admin_panel())

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
        await update.message.reply_text("🚫 Banned")
        context.user_data["mode"] = None
        return

    if mode == "unban":
        banned.discard(int(update.message.text))
        save_data("banned.json", banned)
        await update.message.reply_text("✅ Unbanned")
        context.user_data["mode"] = None
        return

    if mode == "broadcast":
        for u in users:
            try:
                await context.bot.send_message(u, update.message.text)
            except:
                pass
        await update.message.reply_text("📢 Sent")
        context.user_data["mode"] = None
        return

    # AI Chat
    if not chat_enabled:
        return

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

    print("🔥 BOT RUNNING PRO MAX...")

    app.run_polling()

if __name__ == "__main__":
    main()
