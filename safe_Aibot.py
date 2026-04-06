import os
import json
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEEPSEEK_KEYS = os.getenv("DEEPSEEK_KEYS", "")

if not BOT_TOKEN:
    raise Exception("❌ BOT_TOKEN مش موجود")

if not DEEPSEEK_KEYS:
    raise Exception("❌ DEEPSEEK_KEYS مش موجود")

DEEPSEEK_KEYS = DEEPSEEK_KEYS.split(",")

ADMINS = [6157906511]

# ================= STORAGE =================
def load_data(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

users = load_data("users.json")
banned = load_data("banned.json")

# ================= SESSION =================
session = aiohttp.ClientSession()

# ================= HELPERS =================
def is_admin(user_id):
    return user_id in ADMINS

async def notify_admins(text):
    for admin in ADMINS:
        try:
            await app.bot.send_message(admin, text)
        except:
            pass

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    users[str(user.id)] = user.username or "no_username"
    save_data("users.json", users)

    text = f"""
👋 اهلا بيك يا {user.first_name}

🎓 طالب في جامعة ZNU  
💻 كلية حاسبات و معلومات - قسم AI  

━━━━━━━━━━━━━━━
🤖 البوت جاهز يساعدك في:
• كتابة كود
• شرح
• حل مشاكل

👇 اضغط:
/start_bot
"""
    await update.message.reply_text(text)

# ================= SELECT AI =================
async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🤖 DeepSeek", callback_data="deepseek")]
    ]
    await update.message.reply_text(
        "اختار AI:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["ai"] = query.data
    await query.edit_message_text("✅ تم اختيار DeepSeek\nابعت سؤالك")

# ================= AI =================
async def ask_ai(text):
    url = "https://api.deepseek.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEYS[0].strip()}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": text}],
        "max_tokens": 600
    }

    try:
        async with session.post(url, headers=headers, json=data, timeout=60) as resp:
            res = await resp.json()

            if "choices" not in res:
                return "❌ حصل خطأ من AI"

            return res["choices"][0]["message"]["content"]

    except Exception as e:
        print("AI ERROR:", e)
        return "❌ AI واقع دلوقتي حاول تاني"

# ================= MESSAGE =================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if str(user_id) in banned:
        return await update.message.reply_text("❌ انت محظور")

    if "ai" not in context.user_data:
        return await update.message.reply_text("⚠️ اكتب /start_bot الاول")

    msg = update.message.text

    loading = await update.message.reply_text("⏳ بفكر...")

    reply = await ask_ai(msg)

    try:
        await loading.edit_text(reply[:4000])
    except:
        await update.message.reply_text(reply[:4000])

    await notify_admins(f"📩 User: {user_id}\n💬 {msg}")

# ================= ADMIN =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    text = f"""
👑 Admin Panel

👥 Users: {len(users)}
🚫 Banned: {len(banned)}

📌 أوامر:
• /ban ID
• /unban ID
"""
    await update.message.reply_text(text)

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        return await update.message.reply_text("❌ حط ID")

    uid = context.args[0]
    banned[uid] = True
    save_data("banned.json", banned)

    await update.message.reply_text("✅ تم الحظر")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        return await update.message.reply_text("❌ حط ID")

    uid = context.args[0]
    banned.pop(uid, None)
    save_data("banned.json", banned)

    await update.message.reply_text("✅ تم فك الحظر")

# ================= RUN =================
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("start_bot", start_bot))
app.add_handler(CommandHandler("admin", admin_panel))
app.add_handler(CommandHandler("ban", ban))
app.add_handler(CommandHandler("unban", unban))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🔥 BOT RUNNING...")
app.run_polling()
