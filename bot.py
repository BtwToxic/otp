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
        {"$inc": {
            "balance": amt,
            "total_deposit": amt,
            "today_deposit": amt
        }}
    )

def inv(country):
    return inventory.find_one({"country": country}) or {
        "country": country,
        "price": 50,
        "available": 0
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

# ================= START =================

@app.on_message(filters.command("start"))
async def start(_, m):
    hard_reset(m.from_user.id)
    try:
        await app.get_chat_member(FORCE_JOIN, m.from_user.id)
    except:
        return await m.reply(
            "🚫 Join channel first",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Join", url=f"https://t.me/{FORCE_JOIN[1:]}")]
            ])
        )
    get_user(m.from_user.id, m.from_user.first_name)
    await m.reply("🔥 Welcome", reply_markup=main_kb)

# ================= TELEGRAM ACCOUNTS =================

@app.on_message(filters.regex("^📦 Telegram Accounts$"))
async def telegram_accounts(_, m):
    await m.reply(
        "📦 Select Country",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🇮🇳 India", callback_data="acct_india")],
            [InlineKeyboardButton("🇿🇦 South Africa", callback_data="acct_south_africa")],
            [InlineKeyboardButton("🇲🇲 Myanmar", callback_data="acct_myanmar")]
        ])
    )

async def show_country(q, country, label, flag):
    i = inv(country)
    await q.message.edit(
        f"⚡ Telegram Account Info\n\n"
        f"🌍 Country: {flag} {label}\n"
        f"💰 Price: ₹{i['price']}\n"
        f"📦 Available: {i['available']}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Buy Now", callback_data=f"buy_{country}")],
            [InlineKeyboardButton("⬅ Back", callback_data="acct_back")]
        ])
    )

# 🔧 BACK FIX (FIRST)
@app.on_callback_query(filters.regex("^acct_back$"))
async def acct_back(_, q: CallbackQuery):
    await telegram_accounts(_, q.message)

# 🔧 COUNTRY HANDLER (EXCLUDE back)
@app.on_callback_query(filters.regex("^acct_(?!back)"))
async def acct_country(_, q: CallbackQuery):
    c = q.data.replace("acct_", "")
    mp = {
        "india": ("India", "🇮🇳"),
        "south_africa": ("South Africa", "🇿🇦"),
        "myanmar": ("Myanmar", "🇲🇲")
    }
    label, flag = mp[c]
    await show_country(q, c, label, flag)

@app.on_callback_query(filters.regex("^buy_"))
async def buy_start(_, q: CallbackQuery):
    user_state[q.from_user.id] = {
        "flow": "BUY",
        "country": q.data.replace("buy_", "")
    }
    await q.message.reply("📦 Enter quantity:")

# ================= ROUTER =================

@app.on_message(filters.text & ~filters.command(""))
async def router(_, m):
    uid = m.from_user.id
    state = user_state.get(uid)
    if not state:
        return

    text = m.text.strip()

    # ================= BUY FLOW =================
    if state["flow"] == "BUY":
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
            return await m.reply("❌ Insufficient balance")

        sessions = list(accounts.find({"country": country}).limit(qty))
        if len(sessions) < qty:
            return await m.reply("❌ Stock mismatch")

        users.update_one({"_id": uid}, {"$inc": {"balance": -cost}})
        inventory.update_one({"country": country}, {"$inc": {"available": -qty}})

        for s in sessions:
            await app.send_message(
                uid,
                f"🔐 **Here is your ID String Session**\n\n`{s['session']}`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🤖 @" + (await app.get_me()).username,
                                          url=f"https://t.me/{(await app.get_me()).username}")]
                ])
            )
            accounts.delete_one({"_id": s["_id"]})

        hard_reset(uid)
        return await m.reply("✅ Purchase completed")

    # ================= ADD SESSION (ADMIN) =================
    if state.get("flow") == "ADD_COUNTRY" and uid in ADMIN_IDS:
        if text not in ("india", "south_africa", "myanmar"):
            return await m.reply("Invalid country")
        user_state[uid] = {"flow": "ADD_SESSION", "country": text}
        return await m.reply("Send STRING SESSION")

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
        return await m.reply(f"✅ Session added to {country}")

# ================= /add =================

@app.on_message(filters.command("add") & filters.user(ADMIN_IDS))
async def add_start(_, m):
    user_state[m.from_user.id] = {"flow": "ADD_COUNTRY"}
    await m.reply("Type country:\nindia / south_africa / myanmar")

# ================= RUN =================

print("Bot Started ✅")
app.run()
