import os
import sqlite3
import logging
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)
from telegram.request import HTTPXRequest

# Set these in your hosting environment
BUILDER_TOKEN = os.getenv("BUILDER_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "bots.db")

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🎬 Kino bot"), KeyboardButton("📱 SMM bot")],
        [KeyboardButton("🛍 Do‘kon bot"), KeyboardButton("ℹ️ Yordam")],
    ],
    resize_keyboard=True
)

TEMPLATES = {
    "🎬 Kino bot": "kino",
    "📱 SMM bot": "smm",
    "🛍 Do‘kon bot": "shop",
}
TEMPLATE_NAMES = {"kino": "Kino", "smm": "SMM", "shop": "Do‘kon"}

db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.execute("""CREATE TABLE IF NOT EXISTS child_bots (
    owner_id INTEGER NOT NULL,
    token TEXT PRIMARY KEY,
    template TEXT NOT NULL,
    username TEXT,
    active INTEGER NOT NULL DEFAULT 1
)""")
db.commit()

# Active child bot applications are kept here while this process runs.
child_apps = {}
pending_template = {}


def save_bot(owner_id, token, template, username):
    db.execute(
        "INSERT OR REPLACE INTO child_bots(owner_id, token, template, username, active) VALUES(?,?,?,?,1)",
        (owner_id, token, template, username)
    )
    db.commit()


def get_bots():
    return db.execute(
        "SELECT owner_id, token, template, username FROM child_bots WHERE active=1"
    ).fetchall()


def child_keyboard(template):
    if template == "kino":
        return ReplyKeyboardMarkup(
            [["🔎 Kino qidirish"], ["📩 Admin bilan bog‘lanish"]],
            resize_keyboard=True
        )
    if template == "smm":
        return ReplyKeyboardMarkup(
            [["📋 Xizmatlar", "💰 Narxlar"], ["📝 Buyurtma berish"]],
            resize_keyboard=True
        )
    return ReplyKeyboardMarkup(
        [["🛍 Mahsulotlar", "📦 Buyurtma berish"], ["☎️ Aloqa"]],
        resize_keyboard=True
    )


async def child_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    template = context.application.bot_data["template"]
    names = {"kino": "Kino bot", "smm": "SMM xizmatlar bot", "shop": "Do‘kon bot"}
    await update.message.reply_text(
        f"Assalomu alaykum! {names.get(template, 'Bot')} xizmatiga xush kelibsiz.",
        reply_markup=child_keyboard(template)
    )


async def child_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    template = context.application.bot_data["template"]
    text = update.message.text

    if template == "kino":
        if text == "🔎 Kino qidirish":
            await update.message.reply_text(
                "Kino nomini yozing. Bu boshlang‘ich shablon: kino katalogini "
                "to‘ldirish uchun admin kino nomi va Telegram file_id larini qo‘shishi kerak."
            )
        elif text == "📩 Admin bilan bog‘lanish":
            await update.message.reply_text("Admin bilan bog‘lanish uchun username yoki telefon raqam qo‘shilmagan.")
        else:
            await update.message.reply_text(
                f"Qidiruv: {text}\nHozircha katalog namunaviy. O‘zingizga tegishli yoki tarqatishga ruxsatli videolarni qo‘shing."
            )
    elif template == "smm":
        if text == "📋 Xizmatlar":
            await update.message.reply_text("Xizmatlar:\n1. Telegram kanal yuritish\n2. Dizayn\n3. Reklama sozlash\n\nAdmin xizmatlarni o‘zgartirishi mumkin.")
        elif text == "💰 Narxlar":
            await update.message.reply_text("Narxlar buyurtma turiga qarab kelishiladi.")
        elif text == "📝 Buyurtma berish":
            context.user_data["awaiting_order"] = True
            await update.message.reply_text("Buyurtmangizni va aloqa ma’lumotini yozing.")
        elif context.user_data.get("awaiting_order"):
            context.user_data["awaiting_order"] = False
            owner_id = context.application.bot_data.get("owner_id")
            if owner_id:
                try:
                    await context.bot.send_message(owner_id, f"Yangi SMM buyurtma:\n{text}\nMijoz ID: {update.effective_user.id}")
                except Exception:
                    pass
            await update.message.reply_text("Buyurtmangiz qabul qilindi.")
        else:
            await update.message.reply_text("Menyudan xizmatni tanlang.")
    else:
        if text in ("🛍 Mahsulotlar", "📦 Buyurtma berish"):
            await update.message.reply_text("Mahsulotlar ro‘yxati hali kiritilmagan. Admin mahsulotlarni qo‘shishi kerak.")
        elif text == "☎️ Aloqa":
            await update.message.reply_text("Do‘kon aloqa ma’lumoti hali kiritilmagan.")
        else:
            await update.message.reply_text("Menyudan tanlang yoki savolingizni yozing.")


async def start_child(token, template, owner_id, username):
    if token in child_apps:
        return
    request = HTTPXRequest(connect_timeout=20, read_timeout=30, write_timeout=30, pool_timeout=20)
    app = Application.builder().token(token).request(request).build()
    app.bot_data["template"] = template
    app.bot_data["owner_id"] = owner_id
    app.add_handler(CommandHandler("start", child_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, child_text))
    try:
        await app.initialize()
        await app.start()
        if app.updater:
            await app.updater.start_polling(drop_pending_updates=True)
        child_apps[token] = app
        logging.info("Started child bot @%s (%s)", username, template)
    except Exception:
        logging.exception("Could not start child bot @%s", username)
        try:
            await app.shutdown()
        except Exception:
            pass


async def stop_child(token):
    app = child_apps.pop(token, None)
    if not app:
        return
    try:
        if app.updater and app.updater.running:
            await app.updater.stop()
        if app.running:
            await app.stop()
        await app.shutdown()
    except Exception:
        logging.exception("Error stopping child bot")


async def builder_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Men tayyor Telegram bot shablonlarini ishga tushiraman.\n\n"
        "1) Shablonni tanlang.\n2) @BotFather orqali olgan bot tokeningizni yuboring.\n"
        "3) Token tekshiriladi va bot shu serverda ishga tushadi.\n\n"
        "Eslatma: tokenni faqat o‘zingiz boshqaradigan bot uchun yuboring.",
        reply_markup=MENU
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Shablonlar: Kino, SMM, Do‘kon.\n"
        "Bot tokenini @BotFather dan oling. Hosting ishlashi uchun ushbu dastur serverda doim ishlashi kerak."
    )


async def builder_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if text in TEMPLATES:
        pending_template[user_id] = TEMPLATES[text]
        await update.message.reply_text(
            f"{TEMPLATE_NAMES[TEMPLATES[text]]} shabloni tanlandi.\n"
            "Endi @BotFather dan olingan bot tokenini yuboring.\n"
            "Bekor qilish uchun /cancel yozing."
        )
        return

    if text == "ℹ️ Yordam":
        await help_cmd(update, context)
        return

    if text == "/cancel":
        pending_template.pop(user_id, None)
        await update.message.reply_text("Bekor qilindi.", reply_markup=MENU)
        return

    template = pending_template.get(user_id)
    if not template:
        await update.message.reply_text("Avval menyudan bot turini tanlang.", reply_markup=MENU)
        return

    token = text
    if len(token) < 25 or ":" not in token:
        await update.message.reply_text("Token formati noto‘g‘ri ko‘rinadi. @BotFather tokenini qayta yuboring yoki /cancel.")
        return

    await update.message.reply_text("Token tekshirilmoqda...")
    try:
        request = HTTPXRequest(connect_timeout=15, read_timeout=20)
        temp_app = Application.builder().token(token).request(request).build()
        me = await temp_app.bot.get_me()
        await temp_app.shutdown()
    except Exception:
        await update.message.reply_text(
            "Token tekshirilmadi. Tokenni @BotFather dan tekshiring. Xavfsizlik uchun tokenni boshqa joyga yubormang."
        )
        return

    try:
        await start_child(token, template, user_id, me.username or "unknown")
        if token not in child_apps:
            await update.message.reply_text("Bot ishga tushmadi. Tokenni tekshiring yoki boshqa token kiriting.")
            return
        save_bot(user_id, token, template, me.username or "unknown")
        pending_template.pop(user_id, None)
        await update.message.reply_text(
            f"✅ @{me.username} ishga tushdi!\n"
            f"Shablon: {TEMPLATE_NAMES[template]}\n"
            "Bot shu dastur ishlayotgan paytda faol bo‘ladi.",
            reply_markup=MENU
        )
    except Exception:
        logging.exception("Create bot failed")
        await update.message.reply_text("Xatolik yuz berdi. Server loglarini tekshiring.")


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pending_template.pop(update.effective_user.id, None)
    await update.message.reply_text("Bekor qilindi.", reply_markup=MENU)


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID and update.effective_user.id != ADMIN_ID:
        return
    rows = db.execute("SELECT username, template, owner_id FROM child_bots WHERE active=1").fetchall()
    lines = [f"Faol ro‘yxatdagi botlar: {len(rows)}"]
    lines += [f"@{u} — {TEMPLATE_NAMES.get(t,t)} — egasi {o}" for u, t, o in rows]
    await update.message.reply_text("\n".join(lines))


async def post_init(app: Application):
    for owner_id, token, template, username in get_bots():
        await start_child(token, template, owner_id, username or "unknown")


async def post_shutdown(app: Application):
    for token in list(child_apps.keys()):
        await stop_child(token)
    db.close()


def main():
    if not BUILDER_TOKEN:
        raise SystemExit("BUILDER_TOKEN muhit o‘zgaruvchisiga asosiy bot tokenini kiriting.")
    app = (
        Application.builder()
        .token(BUILDER_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    app.add_handler(CommandHandler("start", builder_start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, builder_text))
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
