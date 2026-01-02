from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, CallbackQuery
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

def admin_kb(oid):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{oid}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{oid}")
        ]
    ])

# ================= HELPERS =================

def get_user(uid, name):
    if not users.find_one({"_id": uid}):
        users.insert_one({
            "_id": uid,
            "name": name,
            "balance": 0,
            "total_deposit": 0
        })
    return users.find_one({"_id": uid})

def add_balance(uid, amt):
    users.update_one(
        {"_id": uid},
        {"$inc": {"balance": amt, "total_deposit": amt}}
    )

# ================= START / FORCE JOIN =================

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

    reset_state(q.from_user.id)
    await q.message.delete()
    await app.send_message(q.from_user.id, "🔥 Welcome!", reply_markup=main_kb)

# ================= MENU BUTTONS =================

@app.on_message(filters.regex("^👤 My Profile$"))
async def profile(_, m):
    reset_state(m.from_user.id)
    u = get_user(m.from_user.id, m.from_user.first_name)
    await m.reply(
        f"👤 Profile\n\n"
        f"ID: `{u['_id']}`\n"
        f"Balance: ₹{u['balance']}\n"
        f"Total Deposit: ₹{u['total_deposit']}"
    )

@app.on_message(filters.regex("^📘 How to Use$"))
async def howto(_, m):
    reset_state(m.from_user.id)
    await m.reply("📘 Deposit → Buy → Done")

@app.on_message(filters.regex("^🏷 Discount$"))
async def discount(_, m):
    reset_state(m.from_user.id)
    await m.reply("🏷 ₹1000+ → 5%\n₹2000+ → 10%")

@app.on_message(filters.regex("^🧑‍💻 Support$"))
async def support(_, m):
    reset_state(m.from_user.id)
    await m.reply("Support:\n@techbotss\n@NIXHANT_VERMA33")

# ================= DEPOSIT =================

@app.on_message(filters.regex("^💰 Deposit$"))
async def deposit(_, m):
    reset_state(m.from_user.id)
    user_state[m.from_user.id] = {"step": "AMOUNT"}
    await m.reply(
        f"💰 Pay via UPI\n\nUPI ID: `{UPI_ID}`",
        reply_markup=paid_kb()
    )

@app.on_callback_query(filters.regex("^cancel_deposit$"))
async def cancel(_, q: CallbackQuery):
    reset_state(q.from_user.id)
    await q.message.edit("⛔ Deposit cancelled")
    await app.send_message(q.from_user.id, "Main menu 👇", reply_markup=main_kb)

@app.on_callback_query(filters.regex("^paid$"))
async def paid(_, q: CallbackQuery):
    user_state[q.from_user.id] = {"step": "AMOUNT"}
    await q.message.reply("💰 Enter paid amount:")

# ================= TEXT ROUTER (ONLY DEPOSIT FLOW) =================

@app.on_message(filters.text & ~filters.regex(r"^/"))
async def router(_, m):
    uid = m.from_user.id
    state = user_state.get(uid)
    if not state:
        return

    text = m.text.strip()

    if state["step"] == "AMOUNT":
        if not text.isdigit():
            return await m.reply("❌ Amount number me bhejo")
        user_state[uid] = {"step": "UTR", "amount": int(text)}
        return await m.reply("🔢 UTR / Transaction ID bhejo:")

    if state["step"] == "UTR":
        oid = str(uuid.uuid4())[:8]
        orders.insert_one({
            "order_id": oid,
            "user": uid,
            "amount": state["amount"],
            "utr": text,
            "status": "pending",
            "time": datetime.now()
        })

        for admin in ADMIN_IDS:
            await app.send_message(
                admin,
                f"🧾 Deposit Request\n\nUser: {uid}\nAmount: ₹{state['amount']}\nUTR: {text}\nOrder ID: {oid}",
                reply_markup=admin_kb(oid)
            )

        reset_state(uid)
        await m.reply(f"⏳ Waiting for admin approval\nOrder ID: `{oid}`")

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
    orders.update_one({"order_id": oid}, {"$set": {"status": "rejected"}})
    await app.send_message(orders.find_one({"order_id": oid})["user"], "❌ Payment rejected")
    await q.message.edit("❌ Rejected")

# ================= DEPOSIT HISTORY =================

@app.on_message(filters.regex("^📜 Deposit History$"))
async def history(_, m):
    reset_state(m.from_user.id)
    data = list(orders.find({"user": m.from_user.id}).sort("time", -1).limit(10))
    if not data:
        return await m.reply("📜 No deposit history")

    msg = "📜 Deposit History\n\n"
    for d in data:
        msg += f"{d['order_id']} | ₹{d['amount']} | {d['status'].upper()}\n"
    await m.reply(msg)

# ================= RUN =================

app.run()
