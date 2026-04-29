import os
import json
import time
import aiohttp
from datetime import datetime
from collections import defaultdict, deque

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ===== CONFIG =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEYS")
MISTRAL_KEY = os.getenv("MISTRAL_KEY")

ADMINS = [6157906511]
BOT_NAME = "🔥 Youssef AI Bot"

# ===== LIMITS =====
MAX_HISTORY = 10
memory = defaultdict(lambda: deque(maxlen=MAX_HISTORY))
user_ai = {}

# ===== STORAGE =====
def load(file):
    try:
        with open(file) as f:
            return set(json.load(f))
    except:
        return set()

def save(file, data):
    with open(file, "w") as f:
        json.dump(list(data), f)

users = load("users.json")
banned = load("banned.json")

# ===== AI =====
async def ask_deepseek(uid, text):
    memory[uid].append({"role": "user", "content": text})

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
            json={
                "model": "deepseek-chat",
                "messages": list(memory[uid])
            }
        ) as res:
            data = await res.json()

    if "error" in data:
        return f"❌ {data['error']}"

    reply = data["choices"][0]["message"]["content"]
    memory[uid].append({"role": "assistant", "content": reply})
    return reply


async def ask_mistral(text):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {MISTRAL_KEY}"},
            json={
                "model": "mistral-tiny",
                "messages": [{"role": "user", "content": text}]
            }
        ) as res:
            data = await res.json()

    if "error" in data:
        return f"❌ {data['error']}"

    return data["choices"][0]["message"]["content"]

# ===== AI MENU =====
def ai_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧠 DeepSeek", callback_data="deepseek")],
        [InlineKeyboardButton("🔥 Mistral", callback_data="mistral")]
    ])

# ===== ADMIN =====
def admin_panel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Users", callback_data="users"),
         InlineKeyboardButton("🚫 Ban", callback_data="ban")],

        [InlineKeyboardButton("✅ Unban", callback_data="unban"),
         InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")]
    ])

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id

    users.add(uid)
    save("users.json", users)

    if uid in ADMINS:
        await update.message.reply_text("👑 Admin Panel", reply_markup=admin_panel())
        return

    await update.message.reply_text(f"👋 أهلاً بيك يا {user.first_name}\n\n🤖 {BOT_NAME}\nاكتب /ai واختار AI")

# ===== CHOOSE AI =====
async def choose_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("اختار AI:", reply_markup=ai_menu())

# ===== BUTTONS =====
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    # اختيار AI
    if q.data in ["deepseek", "mistral"]:
        user_ai[uid] = q.data
        await q.edit_message_text(f"✅ اخترت {q.data}")
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
        save("banned.json", banned)
        await update.message.reply_text("🚫 تم")
        context.user_data["mode"] = None
        return

    if mode == "unban":
        banned.discard(int(update.message.text))
        save("banned.json", banned)
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
        return await update.message.reply_text("⚠️ اكتب /ai واختار الأول")

    msg = await update.message.reply_text("⏳")

    if ai == "deepseek":
        reply = await ask_deepseek(uid, update.message.text)
    else:
        reply = await ask_mistral(update.message.text)

    await msg.edit_text(reply)

# ===== PHOTO =====
async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.photo[-1].get_file()
    os.makedirs("photos", exist_ok=True)
    await file.download_to_drive(f"photos/{update.effective_user.id}.jpg")

    await update.message.reply_text("📸 اتحفظت")

# ===== MAIN =====
def main():
    app = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ai", choose_ai))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.add_handler(MessageHandler(filters.PHOTO, photo))

    print("🔥 BOT RUNNING PRO...")
    app.run_polling()

if __name__ == "__main__":
    main()
