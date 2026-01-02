from pyrogram import Client, filters
from pyrogram.types import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from pymongo import MongoClient
from datetime import datetime, timedelta
import uuid
import random
import string
import os

# ================= CONFIG =================

BOT_TOKEN = "YOUR_BOT_TOKEN"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "tg_shop"

ADMIN_IDS = [123456789]  # apni telegram ID
FORCE_JOIN = "@yourchannel"
UPI_ID = "dev@upi"

# ==========================================

app = Client("tg_shop_bot", bot_token=BOT_TOKEN)

mongo = MongoClient(MONGO_URL)
db = mongo[DB_NAME]

users = db.users
promos = db.promos
orders = db.orders
items = db.items

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

def get_user(uid, name):
    user = users.find_one({"_id": uid})
    if not user:
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

def new_promo(amount):
    code = "PROMO-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    promos.insert_one({
        "code": code,
        "amount": amount,
        "expires": datetime.now() + timedelta(days=3),
        "used": []
    })
    return code

# ================= START =================

@app.on_message(filters.command("start"))
async def start(client, message):
    try:
        await client.get_chat_member(FORCE_JOIN, message.from_user.id)
    except:
        return await message.reply(
            f"❌ Pehle channel join karo:\n{FORCE_JOIN}"
        )

    get_user(message.from_user.id, message.from_user.first_name)
    await message.reply(
        "🔥 **Welcome to the Bot!**\nUse menu below 👇",
        reply_markup=main_kb
    )

# ================= PROFILE =================

@app.on_message(filters.regex("My Profile"))
async def profile(client, message):
    u = get_user(message.from_user.id, message.from_user.first_name)
    await message.reply(
        f"⭐ **User Profile** ⭐\n\n"
        f"👤 Name: {u['name']}\n"
        f"🆔 ID: `{u['_id']}`\n\n"
        f"💰 Balance: ₹{u['balance']}\n"
        f"📊 Total Deposit: ₹{u['total_deposit']}\n"
        f"📅 Today Deposit: ₹{u['today_deposit']}\n\n"
        f"⏰ Last Updated: {u['last_update']}"
    )

# ================= PROMOCODE =================

@app.on_message(filters.regex("Promocode"))
async def promo_ask(client, message):
    await message.reply("🎁 Send promocode:")

@app.on_message(filters.text & ~filters.command)
async def promo_redeem(client, message):
    code = message.text.strip()
    p = promos.find_one({"code": code})
    if not p:
        return

    if datetime.now() > p["expires"]:
        return await message.reply("❌ Promocode expired")

    if message.from_user.id in p["used"]:
        return await message.reply("❌ Promocode already used")

    add_balance(message.from_user.id, p["amount"])
    promos.update_one({"code": code}, {"$push": {"used": message.from_user.id}})

    await message.reply(f"✅ ₹{p['amount']} added to your balance")

# ================= ADMIN PROMO =================

@app.on_message(filters.command("pro"))
async def admin_promo(client, message):
    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        amount = int(message.command[1])
    except:
        return await message.reply("❌ Use: /pro 100")

    code = new_promo(amount)
    await message.reply(
        f"🎁 **New Promocode Generated**\n\n"
        f"Code: `{code}`\n"
        f"Amount: ₹{amount}\n"
        f"Valid: 3 Days"
    )

# ================= DEPOSIT =================

@app.on_message(filters.regex("Deposit"))
async def deposit(client, message):
    await message.reply(
        f"💰 **Deposit Funds**\n\n"
        f"UPI ID: `{UPI_ID}`\n\n"
        f"Payment ke baad:\n"
        f"`Amount + UTR` bhejo\n\n"
        f"Example:\n`50 1234567890`"
    )

@app.on_message(filters.regex(r"^\d+\s+\w+"))
async def deposit_request(client, message):
    parts = message.text.split()
    if len(parts) < 2:
        return

    amount = int(parts[0])
    utr = parts[1]
    order_id = str(uuid.uuid4())[:8]

    orders.insert_one({
        "order_id": order_id,
        "user": message.from_user.id,
        "amount": amount,
        "utr": utr
    })

    for admin in ADMIN_IDS:
        await client.send_message(
            admin,
            f"🧾 **New Deposit Request**\n\n"
            f"👤 User: {message.from_user.id}\n"
            f"💰 Amount: ₹{amount}\n"
            f"🔢 UTR: {utr}\n"
            f"🆔 Order ID: {order_id}",
            reply_markup=approve_kb(order_id)
        )

    await message.reply(
        f"⏳ Waiting for admin approval\nOrder ID: `{order_id}`"
    )

# ================= APPROVAL =================

@app.on_callback_query(filters.regex("approve_"))
async def approve_payment(client, query: CallbackQuery):
    if query.from_user.id not in ADMIN_IDS:
        return

    order_id = query.data.split("_")[1]
    o = orders.find_one({"order_id": order_id})
    if not o:
        return

    add_balance(o["user"], o["amount"])
    await client.send_message(
        o["user"],
        f"✅ Payment Approved!\n₹{o['amount']} added to your balance"
    )
    await query.message.edit("✅ Payment Approved")

# ================= TELEGRAM ACCOUNTS (SAFE ITEMS) =================

@app.on_message(filters.regex("Telegram Accounts"))
async def accounts(client, message):
    await message.reply(
        "📦 **Available Digital Accounts**\n\n"
        "Each item price: ₹50\n\n"
        "Send quantity (numbers only)"
    )

@app.on_message(filters.regex(r"^\d+$"))
async def buy_items(client, message):
    qty = int(message.text)
    u = users.find_one({"_id": message.from_user.id})
    cost = qty * 50

    if u["balance"] < cost:
        return await message.reply(
            f"❌ Insufficient Balance\n"
            f"Your Balance: ₹{u['balance']}\n"
            f"Required: ₹{cost}"
        )

    users.update_one(
        {"_id": message.from_user.id},
        {"$inc": {"balance": -cost}}
    )

    await message.reply(
        f"✅ Purchase Successful!\n\n"
        f"Items Bought: {qty}\n"
        f"Cost: ₹{cost}\n\n"
        f"📦 Your digital items will be delivered shortly."
    )

# ================= HOW TO USE =================

@app.on_message(filters.regex("How to Use"))
async def howto(client, message):
    await message.reply(
        "🚀 **How to Use the Bot**\n\n"
        "1️⃣ Deposit funds\n"
        "2️⃣ Redeem promocode (optional)\n"
        "3️⃣ Buy items\n\n"
        "📺 Tutorial:\nhttps://t.me/howtouse3"
    )

# ================= DISCOUNT =================

@app.on_message(filters.regex("Discount"))
async def discount(client, message):
    await message.reply(
        "🏷 **Daily Deposit Discount**\n\n"
        "₹1000+ → 5%\n"
        "₹2000+ → 10%\n"
        "₹4000+ → 15%\n"
        "₹5000+ → 20%\n\n"
        "⏰ Discount resets daily"
    )

# ================= SUPPORT =================

@app.on_message(filters.regex("Support"))
async def support(client, message):
    await message.reply(
        "🧑‍💻 **Support**\n\n"
        "📢 Channel: @Honey_fereshtegan\n"
        "👤 Admin: @NIXHANT_VERMA33\n\n"
        "Feel free to contact 💬"
    )

# ================= RUN =================

app.run()
