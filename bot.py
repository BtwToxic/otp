from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
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
promos = db.promos

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

def force_join_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Join Channel", url=f"https://t.me/{FORCE_JOIN[1:]}")],
        [InlineKeyboardButton("✅ Joined", callback_data="joined")]
    ])

def paid_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Paid", callback_data="paid")],
        [InlineKeyboardButton("⛔ Cancel Deposit", callback_data="cancel")]
    ])

def admin_kb(oid):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{oid}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{oid}")
        ]
    ])

def reset(uid):
    user_state.pop(uid, None)

# ================= HELPERS =================

def get_user(uid, name):
    if not users.find_one({"_id": uid}):
        users.insert_one({
            "_id": uid,
            "name": name,
            "balance": 0,
            "total_deposit": 0,
            "today_deposit": 0,
            "last_update": datetime.now()
        })
    return users.find_one({"_id": uid})

def add_balance(uid, amt):
    users.update_one(
        {"_id": uid},
        {"$inc": {
            "balance": amt,
            "total_deposit": amt,
            "today_deposit": amt
        },
         "$set": {"last_update": datetime.now()}
        }
    )

# ================= START =================

@app.on_message(filters.command("start"))
async def start(_, m):
    reset(m.from_user.id)
    try:
        await app.get_chat_member(FORCE_JOIN, m.from_user.id)
    except:
        return await m.reply("🚫 Must join channel", reply_markup=force_join_kb())

    get_user(m.from_user.id, m.from_user.first_name)
    await m.reply("🔥 Welcome", reply_markup=main_kb)

@app.on_callback_query(filters.regex("^joined$"))
async def joined(_, q: CallbackQuery):
    try:
        await app.get_chat_member(FORCE_JOIN, q.from_user.id)
    except:
        return await q.answer("❌ Join first", show_alert=True)

    await q.message.delete()
    await app.send_message(q.from_user.id, "🔥 Welcome", reply_markup=main_kb)

# ================= PROFILE =================

@app.on_message(filters.regex("^👤 My Profile$"))
async def profile(_, m):
    reset(m.from_user.id)
    u = get_user(m.from_user.id, m.from_user.first_name)
    await m.reply(
        f"👤 **My Profile**\n\n"
        f"Name: {u['name']}\n"
        f"User ID: `{u['_id']}`\n\n"
        f"Balance: ₹{u['balance']}\n"
        f"Total Deposit: ₹{u['total_deposit']}\n"
        f"Today Deposit: ₹{u['today_deposit']}\n"
        f"Last Update: {u['last_update']}"
    )

# ================= PROMOCODE =================

@app.on_message(filters.regex("^🎁 Promocode$"))
async def promo(_, m):
    reset(m.from_user.id)
    user_state[m.from_user.id] = {"flow": "PROMO"}
    await m.reply("🎁 Promocode bhejo:")

@app.on_message(filters.command("pro"))
async def create_promo(_, m):
    if m.from_user.id not in ADMIN_IDS:
        return
    if len(m.command) < 2 or not m.command[1].isdigit():
        return await m.reply("Use: /pro 100")

    code = "PROMO-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    promos.insert_one({
        "code": code,
        "amount": int(m.command[1]),
        "used": []
    })
    await m.reply(f"✅ Promocode created\n\nCode: `{code}`")

# ================= BUY =================

@app.on_message(filters.regex("^📦 Telegram Accounts$"))
async def buy(_, m):
    reset(m.from_user.id)
    user_state[m.from_user.id] = {"flow": "BUY"}
    await m.reply("📦 Price: ₹50 per ID\nQuantity bhejo:")

# ================= DEPOSIT =================

@app.on_message(filters.regex("^💰 Deposit$"))
async def deposit(_, m):
    reset(m.from_user.id)
    user_state[m.from_user.id] = {"flow": "DEPOSIT", "step": "AMOUNT"}
    await m.reply(f"💰 Pay via UPI\nUPI ID: `{UPI_ID}`", reply_markup=paid_kb())

@app.on_callback_query(filters.regex("^cancel$"))
async def cancel(_, q: CallbackQuery):
    reset(q.from_user.id)
    await q.message.edit("⛔ Deposit cancelled")
    await app.send_message(q.from_user.id, "Main menu 👇", reply_markup=main_kb)

@app.on_callback_query(filters.regex("^paid$"))
async def paid(_, q: CallbackQuery):
    await q.message.reply("💰 Amount bhejo:")

# ================= TEXT ROUTER =================

@app.on_message(filters.text & ~filters.command(""))
async def router(_, m):
    uid = m.from_user.id
    state = user_state.get(uid)
    if not state:
        return

    text = m.text.strip()

    # PROMO
    if state.get("flow") == "PROMO":
        promo = promos.find_one({"code": text})
        if not promo or uid in promo["used"]:
            return await m.reply("❌ Invalid promocode")
        add_balance(uid, promo["amount"])
        promos.update_one({"code": text}, {"$push": {"used": uid}})
        reset(uid)
        return await m.reply(f"✅ ₹{promo['amount']} added")

    # BUY
    if state.get("flow") == "BUY":
        if not text.isdigit():
            return
        qty = int(text)
        cost = qty * 50
        u = users.find_one({"_id": uid})
        if u["balance"] < cost:
            return await m.reply("❌ Insufficient balance")
        users.update_one({"_id": uid}, {"$inc": {"balance": -cost}})
        reset(uid)
        return await m.reply(f"✅ Purchased {qty} IDs")

    # DEPOSIT
    if state.get("flow") == "DEPOSIT":
        if state["step"] == "AMOUNT":
            if not text.isdigit():
                return
            user_state[uid]["step"] = "UTR"
            user_state[uid]["amount"] = int(text)
            return await m.reply("🔢 UTR bhejo:")

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
                    f"🧾 Deposit\nUser: {uid}\n₹{state['amount']}\nUTR: {text}\nID: {oid}",
                    reply_markup=admin_kb(oid)
                )
            reset(uid)
            return await m.reply(f"⏳ Waiting approval\nOrder ID: `{oid}`")

# ================= ADMIN =================

@app.on_callback_query(filters.regex("^approve_"))
async def approve(_, q: CallbackQuery):
    oid = q.data.split("_")[1]
    order = orders.find_one({"order_id": oid})
    if not order:
        return
    add_balance(order["user"], order["amount"])
    orders.update_one({"order_id": oid}, {"$set": {"status": "approved"}})
    await app.send_message(order["user"], f"✅ ₹{order['amount']} added")
    await q.message.edit("✅ Approved")

@app.on_callback_query(filters.regex("^reject_"))
async def reject(_, q: CallbackQuery):
    oid = q.data.split("_")[1]
    orders.update_one({"order_id": oid}, {"$set": {"status": "rejected"}})
    await q.message.edit("❌ Rejected")

# ================= HISTORY =================

@app.on_message(filters.regex("^📜 Deposit History$"))
async def history(_, m):
    reset(m.from_user.id)
    data = list(orders.find({"user": m.from_user.id}).sort("time", -1).limit(10))
    if not data:
        return await m.reply("📜 No history")
    msg = "📜 Deposit History\n\n"
    for d in data:
        msg += f"{d['order_id']} | ₹{d['amount']} | {d['status']}\n"
    await m.reply(msg)

# ================= STATIC =================

@app.on_message(filters.regex("^📘 How to Use$"))
async def howto(_, m):
    await m.reply("📘 Deposit → Buy → Done")

@app.on_message(filters.regex("^🧑‍💻 Support$"))
async def support(_, m):
    await m.reply("Support:\n@techbotss\n@NIXHANT_VERMA33")

@app.on_message(filters.regex("^🏷 Discount$"))
async def discount(_, m):
    await m.reply("🏷 ₹1000+ → 5%\n₹2000+ → 10%")

# ================= RUN =================

app.run()
