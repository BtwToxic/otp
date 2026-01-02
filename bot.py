from pyrogram import Client, filters
from pyrogram.types import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from pymongo import MongoClient
from datetime import datetime, timedelta
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
promos = db.promos
orders = db.orders

# user_state example:
# { user_id: {"flow": "DEPOSIT", "step": "AMOUNT", "amount": 0} }
user_state = {}

# ================= KEYBOARDS =================

main_kb = ReplyKeyboardMarkup(
    [
        ["📦 Telegram Accounts", "💰 Deposit"],
        ["👤 My Profile", "🎁 Promocode"],
        ["📘 How to Use", "🏷 Discount"],
        ["🧑‍💻 Support"]
    ],
    resize_keyboard=True
)

def approve_kb(order_id):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ Approve", callback_data=f"approve_{order_id}")]]
    )

# ================= HELPERS =================

def reset_state(uid):
    user_state.pop(uid, None)

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
        {
            "$inc": {
                "balance": amt,
                "total_deposit": amt,
                "today_deposit": amt
            },
            "$set": {"last_update": datetime.now()}
        }
    )

def create_promo(amount):
    code = "PROMO-" + "".join(
        random.choices(string.ascii_uppercase + string.digits, k=6)
    )
    promos.insert_one({
        "code": code,
        "amount": amount,
        "expires": datetime.now() + timedelta(days=3),
        "used": []
    })
    return code

# ================= START =================

@app.on_message(filters.command("start"))
async def start(_, m):
    reset_state(m.from_user.id)
    try:
        await app.get_chat_member(FORCE_JOIN, m.from_user.id)
    except:
        return await m.reply(f"❌ Pehle channel join karo:\n{FORCE_JOIN}")

    get_user(m.from_user.id, m.from_user.first_name)
    await m.reply("🔥 Welcome!", reply_markup=main_kb)

# ================= PROFILE =================

@app.on_message(filters.regex("^👤 My Profile$"))
async def profile(_, m):
    reset_state(m.from_user.id)
    u = get_user(m.from_user.id, m.from_user.first_name)
    await m.reply(
        f"⭐ User Profile ⭐\n\n"
        f"👤 Name: {u['name']}\n"
        f"🆔 ID: `{u['_id']}`\n\n"
        f"💰 Balance: ₹{u['balance']}\n"
        f"📊 Total Deposit: ₹{u['total_deposit']}\n"
        f"📅 Today Deposit: ₹{u['today_deposit']}\n\n"
        f"⏰ Last Updated: {u['last_update']}"
    )

# ================= PROMOCODE =================

@app.on_message(filters.regex("^🎁 Promocode$"))
async def promo_start(_, m):
    reset_state(m.from_user.id)
    user_state[m.from_user.id] = {"flow": "PROMO"}
    await m.reply("🎁 Promocode bhejo:")

@app.on_message(filters.command("pro"))
async def admin_promo(_, m):
    if m.from_user.id not in ADMIN_IDS:
        return
    if len(m.command) < 2 or not m.command[1].isdigit():
        return await m.reply("Use: /pro 100")

    amount = int(m.command[1])
    code = create_promo(amount)
    await m.reply(
        f"✅ Promocode Created\n\nCode: `{code}`\nAmount: ₹{amount}\nValid: 3 Days"
    )

# ================= DEPOSIT (2-STEP) =================

@app.on_message(filters.regex("^💰 Deposit$"))
async def deposit(_, m):
    reset_state(m.from_user.id)
    user_state[m.from_user.id] = {"flow": "DEPOSIT", "step": "AMOUNT"}
    await m.reply("💰 Enter deposit amount (numbers only):")

# ================= BUY =================

@app.on_message(filters.regex("^📦 Telegram Accounts$"))
async def buy(_, m):
    reset_state(m.from_user.id)
    user_state[m.from_user.id] = {"flow": "BUY"}
    await m.reply("📦 Price: ₹50 per ID\nQuantity bhejo (number only)")

# ================= STATIC BUTTONS =================

@app.on_message(filters.regex("^📘 How to Use$"))
async def howto(_, m):
    reset_state(m.from_user.id)
    await m.reply(
        "📘 HOW TO USE\n\n"
        "1️⃣ Deposit funds\n"
        "2️⃣ Redeem promocode\n"
        "3️⃣ Buy IDs\n"
    )

@app.on_message(filters.regex("^🏷 Discount$"))
async def discount(_, m):
    reset_state(m.from_user.id)
    await m.reply(
        "🏷 DAILY DISCOUNT\n\n"
        "₹1000+ → 5%\n₹2000+ → 10%\n₹4000+ → 15%\n₹5000+ → 20%"
    )

@app.on_message(filters.regex("^🧑‍💻 Support$"))
async def support(_, m):
    reset_state(m.from_user.id)
    await m.reply(
        "🧑‍💻 SUPPORT\n\n"
        "📢 Channel: @techbotss\n"
        "👤 Admin: @NIXHANT_VERMA33"
    )

# ================= TEXT ROUTER =================
# commands excluded safely

@app.on_message(filters.text & ~filters.regex(r"^/"))
async def text_router(_, m):
    uid = m.from_user.id
    text = m.text.strip()
    state = user_state.get(uid)

    # ----- PROMO -----
    if state and state.get("flow") == "PROMO":
        promo = promos.find_one({"code": text})
        if not promo:
            return await m.reply("❌ Invalid promocode")
        if datetime.now() > promo["expires"]:
            return await m.reply("❌ Promocode expired")
        if uid in promo["used"]:
            return await m.reply("❌ Already used")

        add_balance(uid, promo["amount"])
        promos.update_one({"code": text}, {"$push": {"used": uid}})
        reset_state(uid)
        return await m.reply(f"✅ ₹{promo['amount']} added to balance")

    # ----- DEPOSIT STEP 1: AMOUNT -----
    if state and state.get("flow") == "DEPOSIT" and state.get("step") == "AMOUNT":
        if not text.isdigit():
            return await m.reply("❌ Amount sirf number me bhejo")
        user_state[uid] = {"flow": "DEPOSIT", "step": "UTR", "amount": int(text)}
        return await m.reply("🔢 Ab UTR / Transaction ID bhejo:")

    # ----- DEPOSIT STEP 2: UTR -----
    if state and state.get("flow") == "DEPOSIT" and state.get("step") == "UTR":
        amount = state["amount"]
        utr = text
        order_id = str(uuid.uuid4())[:8]

        orders.insert_one({
            "order_id": order_id,
            "user": uid,
            "amount": amount,
            "utr": utr
        })

        for admin in ADMIN_IDS:
            await app.send_message(
                admin,
                f"🧾 New Deposit Request\n\n"
                f"User ID: {uid}\nAmount: ₹{amount}\nUTR: {utr}\nOrder ID: {order_id}",
                reply_markup=approve_kb(order_id)
            )

        reset_state(uid)
        return await m.reply(f"⏳ Waiting for admin approval\nOrder ID: `{order_id}`")

    # ----- BUY -----
    if state and state.get("flow") == "BUY":
        if not text.isdigit():
            return await m.reply("❌ Sirf number bhejo")
        qty = int(text)
        cost = qty * 50
        u = users.find_one({"_id": uid})
        if u["balance"] < cost:
            return await m.reply(f"❌ Insufficient balance\nRequired: ₹{cost}")
        users.update_one({"_id": uid}, {"$inc": {"balance": -cost}})
        reset_state(uid)
        return await m.reply(f"✅ Purchase Successful\nQty: {qty}\nCost: ₹{cost}")

# ================= ADMIN APPROVE =================

@app.on_callback_query(filters.regex("^approve_"))
async def approve(_, q: CallbackQuery):
    if q.from_user.id not in ADMIN_IDS:
        return
    order_id = q.data.split("_", 1)[1]
    order = orders.find_one({"order_id": order_id})
    if not order:
        return await q.answer("Order not found", show_alert=True)

    add_balance(order["user"], order["amount"])
    await app.send_message(order["user"], f"✅ Payment approved\n₹{order['amount']} added")
    await q.message.edit("✅ Approved")

# ================= RUN =================

app.run()
