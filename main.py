import os
import re
import json
import asyncio
from flask import Flask
from threading import Thread
from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatPermissions
)
from pyrogram.enums import ChatMemberStatus, ParseMode

# ================= CONFIGURATION =================
API_ID = int(os.environ.get("API_ID", "1234567"))          # Apni API ID dalein
API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH")     # Apni API HASH dalein
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")  # Bot Token
OWNER_ID = int(os.environ.get("OWNER_ID", "123456789"))   # Apni Telegram User ID

# Flask App for Render Web Service Port Binding
app = Flask(__name__)

@app.route('/')
def home():
    return "Group Guard Bot (No-MongoDB Version) is Running Alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ================= LOCAL JSON STORAGE =================
DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"groups": {}, "warns": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"groups": {}, "warns": {}}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def add_group(chat_id, title, invite_link):
    data = load_data()
    data["groups"][str(chat_id)] = {"title": title, "link": invite_link}
    save_data(data)

def remove_group(chat_id):
    data = load_data()
    if str(chat_id) in data["groups"]:
        del data["groups"][str(chat_id)]
        save_data(data)

def get_warns(chat_id, user_id):
    data = load_data()
    key = f"{chat_id}_{user_id}"
    return data["warns"].get(key, 0)

def add_warn(chat_id, user_id):
    data = load_data()
    key = f"{chat_id}_{user_id}"
    count = data["warns"].get(key, 0) + 1
    data["warns"][key] = count
    save_data(data)
    return count

def reset_warns(chat_id, user_id):
    data = load_data()
    key = f"{chat_id}_{user_id}"
    if key in data["warns"]:
        del data["warns"][key]
        save_data(data)

# Bad words list
BAD_WORDS = ["madarchod", "bhenchod", "bhosdike", "gaand", "chutiya", "harami", "fuck", "mc", "bc"]

bot = Client(
    "group_protection_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= COMMANDS & HANDLERS =================

# Start Command
@bot.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    text = (
        f"👋 **Namaste {message.from_user.mention}!**\n\n"
        "🛡️ Main ek **Group Guard & Protection Bot** hu.\n"
        "Aap mujhe apne group me add karke admin bana sakte hain, main aapke group ko secure rakhunga.\n\n"
        "⚙️ **Mere Safety Features:**\n"
        "1. 👤 **Bio Link Check:** Bio me link hone par 3 warning ke baad **MUTE**.\n"
        "2. 🔗 **Link Spam Protection:** Group me link bhejne par 3 warning ke baad **MUTE**.\n"
        "3. ⏩ **Forward Message Check:** Forwarded messages par 3 warning ke baad **MUTE**.\n"
        "4. 🤬 **Bad Words Filter:** Abusive language use karne par 3 warning ke baad **BAN**.\n\n"
        "📌 **Kaise use karein?**\n"
        "Bas mujhe apne group me add karein aur **Admin Permissions** de dein!"
    )
    await message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# Auto Track Group & Bot Admin Status
@bot.on_chat_member_updated()
async def group_status_check(client: Client, event):
    chat = event.chat
    if event.new_chat_member and event.new_chat_member.user.id == (await client.get_me()).id:
        if event.new_chat_member.status == ChatMemberStatus.ADMINISTRATOR:
            try:
                link = await client.export_chat_invite_link(chat.id)
            except Exception:
                link = "No Link Available (Permission Missing)"
            add_group(chat.id, chat.title, link)
        elif event.new_chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            remove_group(chat.id)

# Admin Dashboard (Owner Only)
@bot.on_message(filters.command("admin") & filters.private)
async def admin_panel(client: Client, message: Message):
    if message.from_user.id != OWNER_ID:
        return
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Groups List", callback_data="admin_groups")],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👑 Promote Admin in Group", callback_data="admin_promote_list")]
    ])
    await message.reply_text("👑 **Welcome Admin Panel**\nKripya neeche diye gaye option choose karein:", reply_markup=keyboard)

# Callback Queries for Admin Buttons
@bot.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery):
    if query.from_user.id != OWNER_ID:
        await query.answer("⚠️ Aap is bot ke owner nahi hain!", show_alert=True)
        return

    data_str = query.data
    data = load_data()

    # 1. Groups List Button
    if data_str == "admin_groups":
        groups = data.get("groups", {})
        if not groups:
            await query.message.edit_text("❌ Abhi tak koi group saved nahi hai.")
            return
        
        msg = "📋 **Bot Admin Groups List:**\n\n"
        for i, (c_id, g_info) in enumerate(groups.items(), 1):
            msg += f"{i}. **{g_info['title']}**\n🔗 {g_info['link']}\n\n"
        
        await query.message.edit_text(msg, disable_web_page_preview=True)

    # 2. Broadcast Option
    elif data_str == "admin_broadcast":
        await query.message.edit_text("📢 **Broadcast Message:**\n\nKripya kisi bhi message ke saath reply me `/bc <message>` likhein broadcast karne ke liye.")

    # 3. Promote Admin Group List
    elif data_str == "admin_promote_list":
        groups = data.get("groups", {})
        if not groups:
            await query.message.edit_text("❌ Kisi bhi group me bot admin nahi hai.")
            return

        buttons = []
        for c_id, g_info in groups.items():
            buttons.append([InlineKeyboardButton(g_info['title'], callback_data=f"prom_{c_id}")])
        
        keyboard = InlineKeyboardMarkup(buttons)
        await query.message.edit_text("👑 Select Group jisme aap kisi user ko Admin banana chahte hain:", reply_markup=keyboard)

    elif data_str.startswith("prom_"):
        chat_id = data_str.split("_")[1]
        await query.message.edit_text(
            f"🎯 Group ID: `{chat_id}` selected.\n\n"
            f"User ko admin banane ke liye command bheje:\n"
            f"`/makeadmin {chat_id} @username`"
        )

# Broadcast Command Handler
@bot.on_message(filters.command("bc") & filters.private)
async def broadcast_cmd(client: Client, message: Message):
    if message.from_user.id != OWNER_ID:
        return
    if len(message.command) < 2:
        await message.reply_text("⚠️ Use: `/bc Aapka message yaha`")
        return

    text = message.text.split(None, 1)[1]
    data = load_data()
    groups = data.get("groups", {})
    success = 0
    failed = 0

    for chat_id in groups.keys():
        try:
            await client.send_message(int(chat_id), text)
            success += 1
            await asyncio.sleep(0.5)
        except Exception:
            failed += 1

    await message.reply_text(f"✅ Broadcast Done!\n\nSuccess: {success}\nFailed: {failed}")

# Make Admin via Bot Command Handler
@bot.on_message(filters.command("makeadmin") & filters.private)
async def make_admin_cmd(client: Client, message: Message):
    if message.from_user.id != OWNER_ID:
        return
    if len(message.command) < 3:
        await message.reply_text("⚠️ Syntax: `/makeadmin <chat_id> <username_ya_id>`")
        return

    try:
        chat_id = int(message.command[1])
        user_input = message.command[2]
        
        user = await client.get_users(user_input)
        await client.promote_chat_member(
            chat_id=chat_id,
            user_id=user.id,
            privileges=ChatPermissions(
                can_change_info=True,
                can_delete_messages=True,
                can_invite_users=True,
                can_restrict_members=True,
                can_pin_messages=True,
                can_promote_members=False
            )
        )
        await message.reply_text(f"✅ User {user.mention} successfully **Group me Admin** ban chuka hai!")
    except Exception as e:
        await message.reply_text(f"❌ Failed to promote admin:\n`{e}`")

# ================= GROUP PROTECTION ENGINE =================

@bot.on_message(filters.group & ~filters.service)
async def protection_engine(client: Client, message: Message):
    if not message.from_user:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    # Admin check (Skip admins)
    try:
        member = await client.get_chat_member(chat_id, user_id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return
    except Exception:
        pass

    # 1. CHECK BIO LINK
    try:
        user_full = await client.get_users(user_id)
        if user_full.bio and ("http://" in user_full.bio or "https://" in user_full.bio or "t.me/" in user_full.bio):
            warns = add_warn(chat_id, user_id)
            if warns >= 3:
                await client.restrict_chat_member(chat_id, user_id, ChatPermissions())
                reset_warns(chat_id, user_id)
                await message.reply_text(f"🚫 {message.from_user.mention} ko **Bio me Link** hone ke kaaran 3 warnings ke baad **MUTE** kar diya gaya hai!")
                return
            else:
                await message.reply_text(f"⚠️ **Warning {warns}/3** - {message.from_user.mention}! Aapke Bio me link hai, kripya ise hatayein varna aap MUTE ho jayenge.")
                return
    except Exception:
        pass

    # 2. CHECK BAD WORDS
    text = message.text or message.caption or ""
    if any(word in text.lower() for word in BAD_WORDS):
        await message.delete()
        warns = add_warn(chat_id, user_id)
        if warns >= 3:
            await client.ban_chat_member(chat_id, user_id)
            reset_warns(chat_id, user_id)
            await client.send_message(chat_id, f"🔨 {message.from_user.mention} ko **Abusive Language** use karne par 3 warnings ke baad **BAN** kar diya gaya hai!")
        else:
            await client.send_message(chat_id, f"⚠️ **Warning {warns}/3** - {message.from_user.mention}! Group me gaali/galt shabdh allowed nahi hai.")
        return

    # 3. CHECK LINKS IN MESSAGE
    if re.search(r'(https?://[^\s]+|t\.me/[^\s]+)', text):
        await message.delete()
        warns = add_warn(chat_id, user_id)
        if warns >= 3:
            await client.restrict_chat_member(chat_id, user_id, ChatPermissions())
            reset_warns(chat_id, user_id)
            await client.send_message(chat_id, f"🚫 {message.from_user.mention} ko **Link bhejne** ke kaaran 3 warnings ke baad **MUTE** kar diya gaya hai!")
        else:
            await client.send_message(chat_id, f"⚠️ **Warning {warns}/3** - {message.from_user.mention}! Group me Link bhejna mana hai.")
        return

    # 4. CHECK FORWARD MESSAGES
    if message.forward_date or message.forward_from or message.forward_from_chat:
        await message.delete()
        warns = add_warn(chat_id, user_id)
        if warns >= 3:
            await client.restrict_chat_member(chat_id, user_id, ChatPermissions())
            reset_warns(chat_id, user_id)
            await client.send_message(chat_id, f"🚫 {message.from_user.mention} ko **Message Forward** karne ke kaaran 3 warnings ke baad **MUTE** kar diya gaya hai!")
        else:
            await client.send_message(chat_id, f"⚠️ **Warning {warns}/3** - {message.from_user.mention}! Group me Message forward karna mana hai.")
        return

# Start Flask Web Server & Pyrogram Client
if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    bot.run()
