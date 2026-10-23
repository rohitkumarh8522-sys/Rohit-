import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import os
import re
import json
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
    return "Group Guard Bot (Premium Version) is Running Alive!"

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

# ================= KEYBOARDS =================
def admin_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Managed Groups", callback_data="admin_groups"),
         InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("👑 Promote Admin", callback_data="admin_promote_list")]
    ])

def back_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Panel", callback_data="admin_main_menu")]
    ])

# ================= COMMANDS & HANDLERS =================

# Start Command (Clean & Professional)
@bot.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    bot_info = await client.get_me()
    text = (
        f"🛡️ **Welcome to Group Guard Bot**\n\n"
        f"Hello {message.from_user.mention}! Main aapke Telegram groups ko spam, links, forward messages aur bad words se secure rakhne ke liye taiyar hu.\n\n"
        f"✨ **Features:**\n"
        f"• Anti-Link & Anti-Forward\n"
        f"• Bio Link Protection\n"
        f"• Bad Word Auto-Ban\n"
        f"• 3 Warning System\n\n"
        f"👉 Mujhe apne group me add karein aur **Admin** banayein!"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Me To Your Group", url=f"https://t.me/{bot_info.username}?startgroup=true")]
    ])
    await message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

# Auto Track Group & Bot Admin Status
@bot.on_chat_member_updated()
async def group_status_check(client: Client, event):
    chat = event.chat
    if event.new_chat_member and event.new_chat_member.user.id == (await client.get_me()).id:
        if event.new_chat_member.status == ChatMemberStatus.ADMINISTRATOR:
            try:
                link = await client.export_chat_invite_link(chat.id)
            except Exception:
                link = "No Link Available"
            add_group(chat.id, chat.title, link)
        elif event.new_chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
            remove_group(chat.id)

# Admin Dashboard (Owner Only)
@bot.on_message(filters.command("admin") & filters.private)
async def admin_panel(client: Client, message: Message):
    if message.from_user.id != OWNER_ID:
        return
    
    await message.reply_text(
        "👑 **Bot Owner Control Panel**\n\nNeeche diye gaye buttons se apne bot ko manage karein:",
        reply_markup=admin_main_keyboard()
    )

# Callback Queries with Back Button Support
@bot.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery):
    if query.from_user.id != OWNER_ID:
        await query.answer("⚠️ Aap is bot ke owner nahi hain!", show_alert=True)
        return

    data_str = query.data
    data = load_data()

    if data_str == "admin_main_menu":
        await query.message.edit_text(
            "👑 **Bot Owner Control Panel**\n\nNeeche diye gaye buttons se apne bot ko manage karein:",
            reply_markup=admin_main_keyboard()
        )

    elif data_str == "admin_groups":
        groups = data.get("groups", {})
        if not groups:
            await query.message.edit_text("❌ Abhi tak koi group saved nahi hai.", reply_markup=back_keyboard())
            return
        
        msg = "📋 **Active Protected Groups:**\n\n"
        for i, (c_id, g_info) in enumerate(groups.items(), 1):
            msg += f"{i}. **{g_info['title']}**\n🔗 {g_info['link']}\n\n"
        
        await query.message.edit_text(msg, reply_markup=back_keyboard(), disable_web_page_preview=True)

    elif data_str == "admin_broadcast":
        msg = (
            "📢 **Broadcast Center**\n\n"
            "Sabhi groups me message bhejne ke liye is format me reply karein:\n"
            "`/bc Aapka message yaha`"
        )
        await query.message.edit_text(msg, reply_markup=back_keyboard(), parse_mode=ParseMode.MARKDOWN)

    elif data_str == "admin_promote_list":
        groups = data.get("groups", {})
        if not groups:
            await query.message.edit_text("❌ Kisi bhi group me bot admin nahi hai.", reply_markup=back_keyboard())
            return

        buttons = []
        for c_id, g_info in groups.items():
            buttons.append([InlineKeyboardButton(g_info['title'], callback_data=f"prom_{c_id}")])
        
        buttons.append([InlineKeyboardButton("⬅️ Back to Panel", callback_data="admin_main_menu")])
        keyboard = InlineKeyboardMarkup(buttons)
        await query.message.edit_text("👑 Select group jisme aap admin promote karna chahte hain:", reply_markup=keyboard)

    elif data_str.startswith("prom_"):
        chat_id = data_str.split("_")[1]
        msg = (
            f"🎯 **Group Selected**\n\n"
            f"Target Group ID: `{chat_id}`\n\n"
            f"User ko admin banane ke liye private me ye command bheje:\n"
            f"`/makeadmin {chat_id} @username`"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back to Groups", callback_data="admin_promote_list")]
        ])
        await query.message.edit_text(msg, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

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

    await message.reply_text(f"✅ **Broadcast Completed!**\n\nSuccess: {success}\nFailed: {failed}")

# Make Admin via Bot Command Handler
@bot.on_message(filters.command("makeadmin") & filters.private)
async def make_admin_cmd(client: Client, message: Message):
    if message.from_user.id != OWNER_ID:
        return
    if len(message.command) < 3:
        await message.reply_text("⚠️ Syntax: `/makeadmin <chat_id> <username>`")
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
        await message.reply_text(f"✅ User {user.mention} successfully **Admin** ban chuka hai!")
    except Exception as e:
        await message.reply_text(f"❌ Failed:\n`{e}`")

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

    # 1. CHECK BAD WORDS (Auto Ban on 3 Warnings)
    text = message.text or message.caption or ""
    if any(word in text.lower() for word in BAD_WORDS):
        await message.delete()
        warns = add_warn(chat_id, user_id)
        if warns >= 3:
            await client.ban_chat_member(chat_id, user_id)
            reset_warns(chat_id, user_id)
            await client.send_message(chat_id, f"🔨 **BANNED!**\n👤 {message.from_user.mention} ko 3 warnings ke baad **Abusive Language** ke karan ban kar diya gaya hai.")
        else:
            await client.send_message(chat_id, f"⚠️ **WARNING ({warns}/3)**\n👤 {message.from_user.mention}, gaali ya galat shabd use na karein!")
        return

    # 2. CHECK LINKS IN MESSAGE (Mute on 3 Warnings)
    if re.search(r'(https?://[^\s]+|t\.me/[^\s]+)', text):
        await message.delete()
        warns = add_warn(chat_id, user_id)
        if warns >= 3:
            await client.restrict_chat_member(chat_id, user_id, ChatPermissions())
            reset_warns(chat_id, user_id)
            await client.send_message(chat_id, f"🚫 **MUTED!**\n👤 {message.from_user.mention} ko 3 warnings ke baad **Link Spam** karne par mute kar diya gaya hai.")
        else:
            await client.send_message(chat_id, f"⚠️ **WARNING ({warns}/3)**\n👤 {message.from_user.mention}, group me link bhejna mana hai!")
        return

    # 3. CHECK FORWARD MESSAGES (Mute on 3 Warnings)
    if message.forward_date or message.forward_from or message.forward_from_chat:
        await message.delete()
        warns = add_warn(chat_id, user_id)
        if warns >= 3:
            await client.restrict_chat_member(chat_id, user_id, ChatPermissions())
            reset_warns(chat_id, user_id)
            await client.send_message(chat_id, f"🚫 **MUTED!**\n👤 {message.from_user.mention} ko 3 warnings ke baad **Message Forward** karne par mute kar diya gaya hai.")
        else:
            await client.send_message(chat_id, f"⚠️ **WARNING ({warns}/3)**\n👤 {message.from_user.mention}, message forward karna mana hai!")
        return

# Start Flask Web Server & Pyrogram Client
if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    bot.run()
