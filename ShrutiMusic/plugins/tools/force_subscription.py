
from pyrogram import Client, filters
from pyrogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery, ChatMemberUpdated
from pyrogram.errors import UserNotParticipant, ChatAdminRequired
import asyncio
from pymongo import MongoClient
from config import MONGO_DB_URI
# ========================
# MongoDB Setup
# ========================
mongo = MongoClient(MONGO_DB_URI)
forcesub_collection = mongo["ForceSubDB"]["ForceSub"]

# ========================
# Set / Disable ForceSub
# ========================
@Client.on_message(filters.command("fsub") & filters.group)
async def set_forcesub(client: Client, message: Message):
    if not message.from_user:
        return

    if len(message.command) < 2:
        return await message.reply_text("⚠ Usage:\n`/fsub <channel username or ID>`\n`/fsub off` to disable.")

    if message.command[1].lower() == "off":
        forcesub_collection.delete_one({"chat_id": message.chat.id})
        return await message.reply_text("✅ Force Subscription disabled for this group.")

    channel = message.command[1]
    try:
        chat_info = await client.get_chat(channel)
    except Exception as e:
        return await message.reply_text(f"❌ Invalid channel: {e}")

    forcesub_collection.update_one(
        {"chat_id": message.chat.id},
        {"$set": {
            "chat_id": message.chat.id,
            "channel_id": chat_info.id,
            "channel_username": chat_info.username
        }},
        upsert=True
    )
    await message.reply_text(f"✅ Force Subscription enabled for channel: {chat_info.title}")

# ========================
# Unmute on join
# ========================
@Client.on_chat_member_updated()
async def unmute_on_join(client: Client, update: ChatMemberUpdated):
    chat_id = update.chat.id
    user_id = update.from_user.id

    forcesub_data = forcesub_collection.find_one({"chat_id": chat_id})
    if not forcesub_data:
        return

    channel_id = forcesub_data["channel_id"]
    channel_username = forcesub_data["channel_username"]

    try:
        user_member = await client.get_chat_member(channel_id, user_id)
        if user_member.status == "member":
            await client.restrict_chat_member(
                chat_id,
                user_id,
                permissions=ChatPermissions(can_send_messages=True)
            )
            await client.send_message(
                chat_id,
                f"🎉 {update.from_user.mention}, you have been unmuted because you joined the [channel](https://t.me/{channel_username}).",
                disable_web_page_preview=True
            )
    except UserNotParticipant:
        pass
    except Exception as e:
        print(f"Error checking membership: {e}")

# ========================
# Close Button
# ========================
@Client.on_callback_query(filters.regex("close_force_sub"))
async def close_force_sub(client: Client, callback_query: CallbackQuery):
    await callback_query.answer("ᴄʟᴏsᴇᴅ!")
    await callback_query.message.delete()

# ========================
# ForceSub Check
# ========================
async def check_forcesub(client: Client, message: Message):
    chat_id = message.chat.id
    if message.from_user is None:
        return True

    user_id = message.from_user.id
    forcesub_data = forcesub_collection.find_one({"chat_id": chat_id})
    if not forcesub_data:
        return True

    channel_id = forcesub_data["channel_id"]
    channel_username = forcesub_data["channel_username"]

    try:
        user_member = await client.get_chat_member(channel_id, user_id)
        if user_member.status in ["member", "administrator", "creator"]:
            return True
    except UserNotParticipant:
        if channel_username:
            channel_url = f"https://t.me/{channel_username}"
        else:
            channel_url = await client.export_chat_invite_link(channel_id)

        await message.reply_photo(
            photo="https://envs.sh/Tn_.jpg",
            caption=(f"👋 ʜᴇʟʟᴏ {message.from_user.mention},\n\nʏᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴊᴏɪɴ ᴛʜᴇ [ᴄʜᴀɴɴᴇʟ]({channel_url}) ᴛᴏ sᴇɴᴅ ᴍᴇssᴀɢᴇs ɪɴ ᴛʜɪs ɢʀᴏᴜᴘ."),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("๏ ᴊᴏɪɴ ᴄʜᴀɴɴᴇʟ ๏", url=channel_url)]])
        )
        try:
            await client.restrict_chat_member(
                message.chat.id,
                message.from_user.id,
                permissions=ChatPermissions(can_send_messages=False)
            )
        except Exception as e:
            print(f"Error muting: {e}")
        return False
    except ChatAdminRequired:
        forcesub_collection.delete_one({"chat_id": chat_id})
        await message.reply_text("🚫 Force Subscription disabled (Bot is not admin in channel).")
        return True

    return True

# ========================
# Enforce ForceSub
# ========================
@Client.on_message(filters.group, group=30)
async def enforce_forcesub(client: Client, message: Message):
    await check_forcesub(client, message)

# ========================
# Help
# ========================
MODULE = "ғsᴜʙ"
HELP = """
**Force Subscription Commands:**
/fsub <channel username or ID> - Enable Force Subscription for this group.
/fsub off - Disable Force Subscription.
"""
