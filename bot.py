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
BOT_TOKEN = "8314490143:AAEuAz7kgvp-yP_knzR5EvFCGLbUxCBmN5M"

MONGO_URL = "mongodb+srv://Krishna:pss968048@cluster0.4rfuzro.mongodb.net/?retryWrites=true&w=majority"
DB_NAME = "tg_shop"

ADMIN_IDS = [5812817910]
FORCE_JOIN = "@tgsupplyupdates"
UPI_ID = "whoisnaseem@fam "

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
accounts = db.accounts         
inventory = db.inventory        

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

def inv(country):
    return inventory.find_one({"country": country}) or {
        "country": country, "price": 50, "available": 0
    }

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

# ================= START / FORCE JOIN =================
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
    await m.reply("🔥 **Welcome to the Bot!**", reply_markup=main_kb)

@app.on_callback_query(filters.regex("^joined$"))
async def joined(_, q: CallbackQuery):
    try:
        await app.get_chat_member(FORCE_JOIN, q.from_user.id)
    except:
        return await q.answer("Join channel first", show_alert=True)
    await q.message.delete()
    await app.send_message(q.from_user.id, "🔥 **Welcome to the Bot!**", reply_markup=main_kb)

# ================= PROFILE =================
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

# ================= HOW / SUPPORT =================
@app.on_message(filters.regex(r"^📘 How to Use$"))
async def how_to_use(_, m):
    hard_reset(m.from_user.id)
    await m.reply("🎥 https://t.me/howtouse3")

@app.on_message(filters.regex(r"^🧑‍💻 Support$"))
async def support(_, m):
    hard_reset(m.from_user.id)
    await m.reply("**📚 FAQ & Support 😊**\n\n🔗**Official Channel:** 👉 @tgsupplyupdates\n💬 **Support Admin:** 👉 @BlazeNXT\n\n**🚦 Feel free to reach out if you need any help!**")

# ================= DISCOUNT =================
@app.on_message(filters.regex(r"^🏷 Discount$"))
async def discount(_, m):
    hard_reset(m.from_user.id)
    u = get_user(m.from_user.id, m.from_user.first_name)
    await m.reply(
        "🏷 **Daily Deposit Discount**\n\n"
        "• ₹1000+ → 5%\n• ₹2000+ → 10%\n• ₹4000+ → 15%\n• ₹5000+ → 20%\n\n"
        f"💰 Your total deposit today: ₹{u['today_deposit']}\n"
        "⏰ Resets daily\n"
        "⚠️ Only on Telegram Accounts"
    )

# ================= PROMO =================
@app.on_message(filters.regex(r"^🎁 Promocode$"))
async def promo(_, m):
    hard_reset(m.from_user.id)
    user_state[m.from_user.id] = {"flow": "PROMO"}
    await m.reply("🎁 Send promocode:")

@app.on_message(filters.command("code"))
async def create_promo(_, m):
    if m.from_user.id not in ADMIN_IDS:
        return
    if len(m.command) < 2 or not m.command[1].isdigit():
        return await m.reply("Use: /code amount")
    code = "PROMO-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    promos.insert_one({"code": code, "amount": int(m.command[1]), "used": []})
    await m.reply(f"✅ Promocode created: `{code}`")

# ================= TELEGRAM ACCOUNTS =================
@app.on_message(filters.regex(r"^📦 Telegram Accounts$"))
async def telegram_accounts(_, m):
    hard_reset(m.from_user.id)
    await m.reply(
        "📦 **Telegram Accounts**\n\nSelect Country 👇",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🇮🇳 India", callback_data="acct_india")],
            [InlineKeyboardButton("🇱🇷 U.S.A", callback_data="acct_south_africa")],
            [InlineKeyboardButton("🇲🇲 Myanmar", callback_data="acct_myanmar")]
        ])
    )

async def show_country(q, country, label, flag):
    i = inv(country)
    await q.message.edit(
        f"⚡ **Telegram Account Info**\n\n"
        f"🌍 Country: {flag} {label}\n"
        f"💰 Price: ₹{i['price']}\n"
        f"📦 Available: {i['available']}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Buy Now", callback_data=f"buy_{country}")],
            [InlineKeyboardButton("⬅️ Back", callback_data="acct_back")]
        ])
    )

# Back fix FIRST
@app.on_callback_query(filters.regex("^acct_back$"))
async def acct_back(_, q: CallbackQuery):
    await telegram_accounts(_, q.message)

# Country (exclude back)
@app.on_callback_query(filters.regex("^acct_(?!back)"))
async def acct_country(_, q: CallbackQuery):
    c = q.data.replace("acct_", "")
    mapping = {
        "india": ("India", "🇮🇳"),
        "south_africa": ("U.S.A", "🇱🇷"),
        "myanmar": ("Myanmar", "🇲🇲")
    }
    label, flag = mapping[c]
    await show_country(q, c, label, flag)

@app.on_callback_query(filters.regex("^buy_"))
async def buy_start(_, q: CallbackQuery):
    user_state[q.from_user.id] = {"flow": "BUY_COUNTRY", "country": q.data.replace("buy_", "")}
    await q.message.reply("📦 Send quantity (numbers only):")

# ================= DEPOSIT =================
@app.on_message(filters.regex(r"^💰 Deposit$"))
async def deposit(_, m):
    hard_reset(m.from_user.id)
    user_state[m.from_user.id] = {"flow": "DEPOSIT", "step": "AMOUNT"}

    await m.reply_photo(
        photo="assets/qr.jpg",
        caption=(
            "🧾**Pay via UPI**\n\n"
            f"💳**UPI ID:** `{UPI_ID}`\n\n"
            "🪙**NAME – NASEEM AKHTER**\n\n"
            "🛍️**All Payment Method Accepted • ✔️**\n\n"
            "☎️**Regards -** @BlazeNXT"
        ),
        reply_markup=deposit_kb()
    )
@app.on_callback_query(filters.regex("^cancel_deposit$"))
async def cancel_deposit(_, q: CallbackQuery):
    hard_reset(q.from_user.id)
    await q.message.edit("⛔ Deposit cancelled")
    await app.send_message(q.from_user.id, "Main Menu 👇", reply_markup=main_kb)

@app.on_callback_query(filters.regex("^paid$"))
async def paid(_, q: CallbackQuery):
    await q.message.reply("💰 Enter deposit amount:")

# ================= DEPOSIT HISTORY (RESTORED) =================
@app.on_message(filters.regex(r"^📜 Deposit History$"))
async def deposit_history(_, m):
    hard_reset(m.from_user.id)
    data = list(orders.find({"user": m.from_user.id}).sort("time", -1))
    if not data:
        return await m.reply("📜 **No deposit history found.**")
    text = "📜 **Deposit History**\n\n"
    for d in data[:10]:
        text += (
            f"🧾 **Order ID:** `{d.get('order_id')}`\n"
            f"💰 **Amount:** ₹{d.get('amount')}\n"
            f"📌 **Status:** {d.get('status')}\n"
            f"⏰ **Time:** {d.get('time')}\n\n"
        )
    await m.reply(text)

# ================= TEXT ROUTER =================
@app.on_message(filters.text & ~filters.command(["start", "add", "code"]))
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
        hard_reset(uid)
        return await m.reply(f"✅ ₹{promo['amount']} added")

    # BUY + DELIVER STRING SESSIONS
    if state.get("flow") == "BUY_COUNTRY":
        if not text.isdigit():
            return
        qty = int(text)
        country = state["country"]
        i = inv(country)
        cost = qty * i["price"]
        u = users.find_one({"_id": uid})
        if i["available"] < qty:
            return await m.reply("❌ Not enough stock")
        if u["balance"] < cost:
            return await m.reply("❌ Insufficient balance\n➡️ Please Deposit Funds")

        sessions = list(accounts.find({"country": country}).limit(qty))
        if len(sessions) < qty:
            return await m.reply("❌ Stock mismatch, contact admin")

        users.update_one({"_id": uid}, {"$inc": {"balance": -cost}})
        inventory.update_one({"country": country}, {"$inc": {"available": -qty}})
        bot = await app.get_me()

        for s in sessions:
            await app.send_message(
                uid,
                f"🔐 **Here is your tg Account String Session**\n\n`{s['session']}`\n\n**Note ~ USE THIS STRING SESSION FOR LOG IN**\n\n**CLICK LOG IN BUTTON FOR ACCOUNT LOGIN**",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"Log in", url=f"https://t.me/TgSupplyLoginBOT")]
                ])
            )
            accounts.delete_one({"_id": s["_id"]})

        hard_reset(uid)
        return await m.reply("✅ Purchase completed")

    # DEPOSIT FLOW
    if state.get("flow") == "DEPOSIT":
        if state["step"] == "AMOUNT":
            if not text.isdigit():
                return
            user_state[uid]["amount"] = int(text)
            user_state[uid]["step"] = "UTR"
            return await m.reply("🔢 Enter UTR:")
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
                    f"🧾 Deposit Request\nUser: `{uid}`\nAmount: ₹{state['amount']}\nUTR: {text}\nOrder: `{oid}`",
                    reply_markup=admin_kb(oid)
                )
            hard_reset(uid)
            return await m.reply(f"⏳ Waiting for approval\nOrder ID: `{oid}`")

    # ADD STRING SESSION (ADMIN)
    if state.get("flow") == "ADD_COUNTRY" and uid in ADMIN_IDS:
        if text not in ("india", "usa", "myanmar"):
            return await m.reply("❌ Invalid country")
        user_state[uid] = {"flow": "ADD_SESSION", "country": text}
        return await m.reply("🔐 Send STRING SESSION:")

    if state.get("flow") == "ADD_SESSION" and uid in ADMIN_IDS:
        country = state["country"]
        accounts.insert_one({
            "country": country,
            "session": text,
            "added_at": datetime.now()
        })
        inventory.update_one(
            {"country": country},
            {"$inc": {"available": 1}, "$setOnInsert": {"price": 50}},
            upsert=True
        )
        hard_reset(uid)
        return await m.reply(f"✅ String session added to {country}")

# ================= ADMIN APPROVAL =================
@app.on_callback_query(filters.regex("^approve_"))
async def approve(_, q: CallbackQuery):
    oid = q.data.split("_", 1)[1]
    order = orders.find_one({"order_id": oid})
    if not order:
        return await q.answer("Order not found", show_alert=True)
    add_balance(order["user"], order["amount"])
    orders.update_one({"order_id": oid}, {"$set": {"status": "approved"}})
    await app.send_message(order["user"], f"✅ Payment approved\n₹{order['amount']} added")
    await q.message.edit("✅ Approved")

@app.on_callback_query(filters.regex("^reject_"))
async def reject(_, q: CallbackQuery):
    oid = q.data.split("_", 1)[1]
    order = orders.find_one({"order_id": oid})
    if not order:
        return await q.answer("Order not found", show_alert=True)
    orders.update_one({"order_id": oid}, {"$set": {"status": "rejected"}})
    await q.message.edit("❌ Rejected")
    await app.send_message(order["user"], "❌ Payment rejected\nContact support")

# ================= /add =================
@app.on_message(filters.regex(r"^/add(@\w+)?$"))
async def add_start(_, m):
    if m.from_user.id not in ADMIN_IDS:
        return await m.reply("❌ You are not admin")

    user_state[m.from_user.id] = {"flow": "ADD_COUNTRY"}
    await m.reply(
        "➕ Add Account\n\n"
        "Type country:\n"
        "india / usa / myanmar"
    )
# ================= RUN =================
print("Bot Started ✅")
app.run()
