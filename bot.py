from pyrogram import Client, filters
from pyrogram.types import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from pymongo import MongoClient
from datetime import datetime
import uuid

# ================= CONFIG =================

API_ID = 21705136
API_HASH = "78730e89d196e160b0f1992018c6cb19"
BOT_TOKEN = "8366650744:AAG5wP84RcqA8VmN4OcmR3ucTsmXfeCRmqc"

MONGO_URL = "mongodb+srv://Krishna:pss968048@cluster0.4rfuzro.mongodb.net/?retryWrites=true&w=majority"
DB_NAME = "tg_shop"

ADMIN_IDS = [6944519938]
FORCE_JOIN = "@techbotss"
UPI_ID = "dev@upi"

# ================= APP =================

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

user_state = {}

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

def reset_state(uid):
    user_state.pop(uid, None)

def force_join_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Join Channel", url=f"https://t.me/{FORCE_JOIN[1:]}")],
        [InlineKeyboardButton("✅ Joined", callback_data="joined")]
    ])

def paid_kb():
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

# ================= HELPERS =================

def get_user(uid, name):
    if not users.find_one({"_id": uid}):
        users.insert_one({
            "_id": uid,
            "name": name,
            "balance": 0,
            "total_deposit": 0,
            "today_deposit": 0
        })
    return users.find_one({"_id": uid})

def add_balance(uid, amt):
    users.update_one(
        {"_id": uid},
        {"$inc": {
            "balance": amt,
            "total_deposit": amt,
            "today_deposit": amt
        }}
    )

# ================= START =================

@app.on_message(filters.command("start"))
async def start(_, m):
    reset_state(m.from_user.id)
    try:
        await app.get_chat_member(FORCE_JOIN, m.from_user.id)
    except:
        return await m.reply(
            "🚫 Must join channel to use bot",
            reply_markup=force_join_kb()
        )

    get_user(m.from_user.id, m.from_user.first_name)
    await m.reply("🔥 Welcome!", reply_markup=main_kb)

@app.on_callback_query(filters.regex("^joined$"))
async def joined(_, q: CallbackQuery):
    try:
        await app.get_chat_member(FORCE_JOIN, q.from_user.id)
    except:
        return await q.answer("❌ Pehle join karo", show_alert=True)

    await q.message.delete()
    get_user(q.from_user.id, q.from_user.first_name)
    await q.message.chat.send_message("🔥 Welcome!", reply_markup=main_kb)

# ================= DEPOSIT =================

@app.on_message(filters.regex("^💰 Deposit$"))
async def deposit(_, m):
    reset_state(m.from_user.id)
    user_state[m.from_user.id] = {"flow": "DEPOSIT", "step": "PAID"}
    await m.reply(
        f"💰 Pay via UPI\n\nUPI ID: `{UPI_ID}`",
        reply_markup=paid_kb()
    )

@app.on_callback_query(filters.regex("^cancel_deposit$"))
async def cancel_deposit(_, q: CallbackQuery):
    reset_state(q.from_user.id)
    await q.message.edit("⛔ Deposit cancelled")
    await q.message.chat.send_message("Main menu 👇", reply_markup=main_kb)

@app.on_callback_query(filters.regex("^paid$"))
async def paid(_, q: CallbackQuery):
    user_state[q.from_user.id] = {"flow": "DEPOSIT", "step": "AMOUNT"}
    await q.message.reply("💰 Enter paid amount:")

# ================= TEXT ROUTER =================

@app.on_message(filters.text & ~filters.regex(r"^/"))
async def text_router(_, m):
    uid = m.from_user.id
    text = m.text.strip()
    state = user_state.get(uid)

    # Deposit amount
    if state and state.get("flow") == "DEPOSIT" and state.get("step") == "AMOUNT":
        if not text.isdigit():
            return await m.reply("❌ Amount number me bhejo")
        user_state[uid] = {
            "flow": "DEPOSIT",
            "step": "UTR",
            "amount": int(text)
        }
        return await m.reply("🔢 UTR / Transaction ID bhejo:")

    # Deposit UTR
    if state and state.get("flow") == "DEPOSIT" and state.get("step") == "UTR":
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
                f"🧾 Deposit Request\n\n"
                f"User: {uid}\n"
                f"Amount: ₹{state['amount']}\n"
                f"UTR: {text}\n"
                f"Order ID: {order_id}",
                reply_markup=admin_kb(order_id)
            )

        reset_state(uid)
        await m.reply(f"⏳ Waiting for admin approval\nOrder ID: `{order_id}`")

# ================= ADMIN ACTIONS =================

@app.on_callback_query(filters.regex("^approve_"))
async def approve(_, q: CallbackQuery):
    if q.from_user.id not in ADMIN_IDS:
        return
    oid = q.data.split("_")[1]
    order = orders.find_one({"order_id": oid})
    if not order or order["status"] != "pending":
        return

    add_balance(order["user"], order["amount"])
    orders.update_one({"order_id": oid}, {"$set": {"status": "approved"}})

    await app.send_message(order["user"], f"✅ Payment approved\n₹{order['amount']} added")
    await q.message.edit("✅ Approved")

@app.on_callback_query(filters.regex("^reject_"))
async def reject(_, q: CallbackQuery):
    if q.from_user.id not in ADMIN_IDS:
        return
    oid = q.data.split("_")[1]
    order = orders.find_one({"order_id": oid})
    if not order or order["status"] != "pending":
        return

    orders.update_one({"order_id": oid}, {"$set": {"status": "rejected"}})
    await app.send_message(order["user"], "❌ Payment rejected")
    await q.message.edit("❌ Rejected")

# ================= DEPOSIT HISTORY =================

@app.on_message(filters.regex("^📜 Deposit History$"))
async def history(_, m):
    reset_state(m.from_user.id)
    data = list(
        orders.find({"user": m.from_user.id})
        .sort("time", -1)
        .limit(10)
    )

    if not data:
        return await m.reply("📜 No deposit history")

    msg = "📜 **Deposit History**\n\n"
    for d in data:
        msg += (
            f"🆔 {d['order_id']}\n"
            f"₹{d['amount']} | {d['status'].upper()}\n"
            f"UTR: {d['utr']}\n\n"
        )
    await m.reply(msg)

# ================= STATIC =================

@app.on_message(filters.regex("^🧑‍💻 Support$"))
async def support(_, m):
    reset_state(m.from_user.id)
    await m.reply("Support:\n@techbotss\n@NIXHANT_VERMA33")

# ================= RUN =================

app.run()
