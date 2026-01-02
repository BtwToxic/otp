from pyrogram import Client, filters
from pyrogram.types import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from pymongo import MongoClient
from datetime import datetime
import uuid, random, string

# ================= CONFIG =================

API_ID = 21705136
API_HASH = "78730e89d196e160b0f1992018c6cb19"
BOT_TOKEN = "8366650744:AAG5wP84RcqA8VmN4OcmR3ucTsmXfeCRmqc"

MONGO_URL = "mongodb+srv://Krishna:pss968048@cluster0.4rfuzro.mongodb.net/?retryWrites=true&w=majority"
DB_NAME = "tg_shop"

ADMIN_IDS = [6944519938]
FORCE_JOIN = "@techbotss"
UPI_ID = "dev@upi"

# ================= INIT =================

app = Client(
    "tg_shop_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

mongo = MongoClient(MONGO_URL)
db = mongo[DB_NAME]
users = db.users
orders = db.orders
promos = db.promos

user_state = {}

# ================= HELPERS =================

def hard_reset(uid):
    user_state.pop(uid, None)

def get_user(uid, name):
    u = users.find_one({"_id": uid})
    if not u:
        users.insert_one({
            "_id": uid,
            "name": name,
            "balance": 0,
            "total_deposit": 0,
            "today_deposit": 0,
            "last_update": datetime.now()
        })
        u = users.find_one({"_id": uid})
    return u

def add_balance(uid, amt):
    users.update_one(
        {"_id": uid},
        {
            "$inc": {
                "balance": amt,
                "total_deposit": amt,
                "today_deposit": amt
            },
            "$set": {"last_update": datetime.now()}
        }
    )

# ================= KEYBOARDS =================

main_kb = ReplyKeyboardMarkup(
    [
        ["📦 Telegram Accounts", "💰 Deposit"],
        ["👤 My Profile", "🎁 Promocode"],
        ["📜 Deposit History"],
        ["📘 How to Use", "🏷 Discount"],
        ["🧑‍💻 Support"]
    ],
    resize_keyboard=True
)

def force_join_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Join Channel", url=f"https://t.me/{FORCE_JOIN[1:]}")],
        [InlineKeyboardButton("✅ Joined", callback_data="joined")]
    ])

def deposit_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Paid", callback_data="paid")],
        [InlineKeyboardButton("⛔ Cancel Deposit", callback_data="cancel_deposit")]
    ])

def admin_kb(order_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{order_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{order_id}")
        ]
    ])

# ================= START =================

@app.on_message(filters.command("start"))
async def start(_, m):
    hard_reset(m.from_user.id)
    try:
        await app.get_chat_member(FORCE_JOIN, m.from_user.id)
    except:
        return await m.reply(
            "🚫 **Must join channel to use the bot**",
            reply_markup=force_join_kb()
        )

    get_user(m.from_user.id, m.from_user.first_name)
    await m.reply("🔥 **Welcome to the Bot!**\n\n **Use the menu below to explore features.**", reply_markup=main_kb)

@app.on_callback_query(filters.regex("^joined$"))
async def joined(_, q: CallbackQuery):
    try:
        await app.get_chat_member(FORCE_JOIN, q.from_user.id)
    except:
        return await q.answer("❌ **Join Channel First**", show_alert=True)

    await q.message.delete()
    await app.send_message(q.from_user.id, "🔥 **Welcome to the Bot!**\n\n **Use the menu below to explore features.**", reply_markup=main_kb)

# ================= MY PROFILE =================

@app.on_message(filters.regex(r"^👤 My Profile$"))
async def my_profile(_, m):
    hard_reset(m.from_user.id)
    u = get_user(m.from_user.id, m.from_user.first_name)
    await m.reply(
        "⭐ **User Profile** ⭐\n\n"
        f"👤 Name: {u['name']}\n"
        f"🆔 ID: `{u['_id']}`\n\n"
        f"💰 Balance: ₹{u['balance']}\n"
        f"📊 Total Deposit: ₹{u['total_deposit']}\n"
        f"📅 Today Deposit: ₹{u['today_deposit']}\n\n"
        f"⏰ Last Updated: {u['last_update']}"
    )

# ================= HOW TO USE =================

@app.on_message(filters.regex(r"^📘 How to Use$"))
async def how_to_use(_, m):
    hard_reset(m.from_user.id)
    await m.reply(
        "🚀 **Start Using the Bot Like a Pro!**\n\n"
        "🔥 **WATCH BOT TUTORIAL** 👇\n"
        "🎥 https://t.me/howtouse3\n\n"
        "✅ Step-by-step guide\n"
        "✅ Super easy to follow\n"
        "✅ Must watch before using the bot!"
    )

# ================= SUPPORT =================

@app.on_message(filters.regex(r"^🧑‍💻 Support$"))
async def support(_, m):
    hard_reset(m.from_user.id)
    await m.reply(
        "📚 **FAQ & Support 😊**\n\n"
        "🔗 Official Channel: 👉 @TechBotss\n\n"
        "💬 Support Admin: 👉 @ikBug\n\n"
        "🚦 Feel free to reach out if you need any help!"
    )

# ================= DISCOUNT =================

@app.on_message(filters.regex(r"^🏷 Discount$"))
async def discount(_, m):
    hard_reset(m.from_user.id)
    u = get_user(m.from_user.id, m.from_user.first_name)
    
    await m.reply(
        "🏷 **Daily Deposit Discount Offer**\n\n"
        "📌 Slabs (Telegram Accounts only):\n"
        "• ₹1000+ → 5% discount\n"
        "• ₹2000+ → 10% discount\n"
        "• ₹4000+ → 15% discount\n"
        "• ₹5000+ → 20% discount\n\n"
        f"💰 Your total deposit today: ₹{u['total_deposit']}\n"
        + (
            "🚫 No discount active for you today yet.\n"
            "➡️ Deposit at least ₹1000 today to unlock 5% discount.\n\n"
            if u < 1000 else
            "✅ Discount unlocked! It will apply on Telegram Accounts purchase.\n\n"
        )
        +
        "⏰ Discount resets daily (00:00–23:59)\n"
        "⚠️ Discount valid only on Telegram Accounts"
    )
# ================= PROMOCODE =================

@app.on_message(filters.regex(r"^🎁 Promocode$"))
async def promo(_, m):
    hard_reset(m.from_user.id)
    user_state[m.from_user.id] = {"flow": "PROMO"}
    await m.reply("🎁 **SEND YOUR PROMO CODE** :")

@app.on_message(filters.command("code"))
async def create_promo(_, m):
    if m.from_user.id not in ADMIN_IDS:
        return
    if len(m.command) < 2 or not m.command[1].isdigit():
        return await m.reply("Use: /code amount")

    code = "PROMO-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    promos.insert_one({
        "code": code,
        "amount": int(m.command[1]),
        "used": []
    })
    await m.reply(f"✅ **Promocode Created**\n\n**Code :** `{code}`")

# ================= TELEGRAM ACCOUNTS =================

@app.on_message(filters.regex(r"^📦 Telegram Accounts$"))
async def telegram_accounts(_, m):
    hard_reset(m.from_user.id)
    user_state[m.from_user.id] = {"flow": "BUY"}
    await m.reply(
        "📦 **Telegram Accounts**\n\n"
        "💵 Price: ₹50 per account\n"
        "✏️ Send quantity (numbers only):"
    )

# ================= DEPOSIT =================

@app.on_message(filters.regex(r"^💰 Deposit$"))
async def deposit(_, m):
    hard_reset(m.from_user.id)
    user_state[m.from_user.id] = {"flow": "DEPOSIT", "step": "AMOUNT"}
    await m.reply(
        f"💰 **Pay via UPI**\n\n **UPI ID :** `{UPI_ID}`",
        reply_markup=deposit_kb()
    )

@app.on_callback_query(filters.regex("^cancel_deposit$"))
async def cancel_deposit(_, q: CallbackQuery):
    hard_reset(q.from_user.id)
    await q.message.edit("⛔ **Deposit cancelled**")
    await app.send_message(q.from_user.id, "**Main Menu** 👇", reply_markup=main_kb)

@app.on_callback_query(filters.regex("^paid$"))
async def paid(_, q: CallbackQuery):
    await q.message.reply("💰 **Enter deposit amount (numbers only) :**")

# ================= DEPOSIT HISTORY =================

@app.on_message(filters.regex(r"^📜 Deposit History$"))
async def deposit_history(_, m):
    hard_reset(m.from_user.id)

    data = list(
        orders.find({"user": m.from_user.id}).sort("time", -1)
    )

    if not data:
        return await m.reply("📜 **No deposit history found.**")

    text = "📜 **Deposit History**\n\n"

    for d in data[-10:]:
        status = d.get("status", "pending")
        text += (
            f"🧾 **Order IDb:** `{d.get('order_id','N/A')}`\n\n"
            f"💰 **Amount :** ₹{d.get('amount',0)}\n\n"
            f"📌 **Status :** {status}\n\n"
            f"⏰ {d.get('time','')}\n\n"
        )

    await m.reply(text)

# ================= TEXT ROUTER =================

@app.on_message(filters.text & ~filters.command(""))
async def router(_, m):
    uid = m.from_user.id
    state = user_state.get(uid)
    if not state:
        return

    text = m.text.strip()

    # PROMO REDEEM
    if state.get("flow") == "PROMO":
        promo = promos.find_one({"code": text})
        if not promo or uid in promo["used"]:
            return await m.reply("❌ **Invalid Promocode**")
        add_balance(uid, promo["amount"])
        promos.update_one({"code": text}, {"$push": {"used": uid}})
        hard_reset(uid)
        return await m.reply(f"✅ ₹{promo['amount']} **added to balance**")

    # BUY ACCOUNTS
    if state.get("flow") == "BUY":
        if not text.isdigit():
            return
        qty = int(text)
        cost = qty * 50
        u = users.find_one({"_id": uid})
        if u["balance"] < cost:
            return await m.reply("❌ **Insufficient balance**")
        users.update_one({"_id": uid}, {"$inc": {"balance": -cost}})
        hard_reset(uid)
        return await m.reply(f"✅ **Purchased** {qty} **Telegram accounts**")

    # DEPOSIT FLOW
    if state.get("flow") == "DEPOSIT":
        if state["step"] == "AMOUNT":
            if not text.isdigit():
                return
            user_state[uid]["amount"] = int(text)
            user_state[uid]["step"] = "UTR"
            return await m.reply("🔢 **Enter UTR / Transaction ID:**")

        if state["step"] == "UTR":
            order_id = str(uuid.uuid4())[:8]
            orders.insert_one({
                "order_id": order_id,
                "user": uid,
                "amount": state["amount"],
                "utr": text,
                "status": "pending",
                "time": datetime.now()
            })
            for admin in ADMIN_IDS:
                await app.send_message(
                    admin,
                    f"🧾 **Deposit Request**\n\n"
                    f"👤 User: `{uid}`\n"
                    f"💰 Amount: ₹{state['amount']}\n"
                    f"🔢 UTR: {text}\n"
                    f"🆔 Order ID: `{order_id}`",
                    reply_markup=admin_kb(order_id)
                )
            hard_reset(uid)
            return await m.reply(
                f"⏳ **Waiting For Admin Approval**\n\n**Order ID:** `{order_id}`"
            )

# ================= ADMIN APPROVAL =================

@app.on_callback_query(filters.regex("^approve_"))
async def approve(_, q: CallbackQuery):
    oid = q.data.split("_")[1]
    order = orders.find_one({"order_id": oid})
    if not order:
        return
    add_balance(order["user"], order["amount"])
    orders.update_one({"order_id": oid}, {"$set": {"status": "approved"}})
    await app.send_message(order["user"], f"✅ Payment approved\n₹{order['amount']} added")
    await q.message.edit("✅ Approved")

@app.on_callback_query(filters.regex("^reject_"))
async def reject(_, q: CallbackQuery):
    oid = q.data.split("_")[1]
    orders.update_one({"order_id": oid}, {"$set": {"status": "rejected"}})
    await q.message.edit("Payment Rejected Please Contact Support Team")

# ================= RUN =================

app.run()
