import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from pymongo import MongoClient
import random
import os
import time
from datetime import datetime
from flask import Flask
import threading

# Yahan apna bot token dalein
TOKEN = '8609194789:AAFVX59ciRYVAsOKSegU9BNa5NuHSqJD3mw'
bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

ADMIN_ID = 1484173564
APPROVAL_CHANNEL = "@ValiModes_key"

# ================= DATABASE SETUP (MONGODB - NO RESET) =================
# ✅ Password update kar diya gaya hai!
MONGO_URL = "mongodb+srv://rihanshaikh9007_db_user:Rihanshaikh123@cluster0.zinixku.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URL)
db = client['webseries_bot']

# Collections (Tables)
channels_col = db['channels']
join_reqs_col = db['join_reqs']
users_col = db['users']
refs_col = db['completed_refs']
settings_col = db['settings']
promo_col = db['promo_codes']
promo_users_col = db['promo_users']
tasks_col = db['tasks']
task_users_col = db['task_users']

# Default Settings Setup
if not settings_col.find_one({"name": "key_link"}):
    settings_col.insert_one({"name": "key_link", "value": "https://www.mediafire.com/file/if3uvvwjbj87lo2/DRIPCLIENT_v6.2_GLOBAL_AP.apks/file"})
if not settings_col.find_one({"name": "base_price"}):
    settings_col.insert_one({"name": "base_price", "value": "15"})

# ================= SECURITY / ANTI-SPAM =================
user_last_msg = {}
verify_spam = {} 
temp_channel_data = {}

def flood_check(user_id):
    now = time.time()
    if user_id in user_last_msg and now - user_last_msg[user_id] < 1.0: return True
    user_last_msg[user_id] = now
    return False

def is_user_banned(user_id):
    user = users_col.find_one({"user_id": user_id})
    return user and user.get("is_banned", 0) == 1

# ================= FLASK WEB SERVER =================
app = Flask(__name__)
@app.route('/')
def home(): return "V3 Ultimate Bot is Running with Advanced Features!"
def run_web(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

# ================= 👨‍💻 VIP ADMIN COMMANDS =================
@bot.message_handler(commands=['addcoins', 'setprice', 'promo', 'check', 'change', 'admin', 'addtask'])
def admin_super_commands(message):
    if message.chat.id != ADMIN_ID: return
    cmd = message.text.split()[0]
    
    if cmd == '/addcoins':
        try:
            _, uid, amt = message.text.split()
            uid, amt = int(uid), int(amt)
            users_col.update_one({"user_id": uid}, {"$inc": {"coins": amt}}, upsert=True)
            bot.reply_to(message, f"✅ {amt} Coins added to {uid}.")
            bot.send_message(uid, f"🎁 Admin ne aapko <b>{amt} Coins</b> bheje hain!")
        except: bot.reply_to(message, "❌ Format: `/addcoins USER_ID COINS`")

    elif cmd == '/setprice':
        try:
            _, price = message.text.split()
            settings_col.update_one({"name": "base_price"}, {"$set": {"value": price}}, upsert=True)
            bot.reply_to(message, f"✅ Base Key Price set to {price} Coins.")
        except: bot.reply_to(message, "❌ Format: `/setprice 15`")

    elif cmd == '/promo':
        try:
            args = message.text.split()
            code, reward, max_u = args[1], int(args[2]), int(args[3])
            hours = int(args[4]) if len(args) > 4 else 87600 
            expiry = time.time() + (hours * 3600)
            promo_col.insert_one({"code": code, "reward": reward, "max_uses": max_u, "used_count": 0, "expiry": expiry})
            bot.reply_to(message, f"✅ <b>Promo Created!</b>\nCode: <code>{code}</code>\nReward: {reward}\nLimit: {max_u}\nValid for: {hours} Hours")
        except: bot.reply_to(message, "❌ Format: `/promo CODE REWARD LIMIT HOURS`\nExample: `/promo VIP 10 50 24`")

    elif cmd == '/addtask':
        try:
            args = message.text.split()
            task_id, reward, secret, link = args[1], int(args[2]), args[3], args[4]
            tasks_col.update_one({"task_id": task_id}, {"$set": {"reward": reward, "secret": secret, "link": link}}, upsert=True)
            bot.reply_to(message, f"✅ <b>Task Added!</b>\nID: {task_id}\nReward: {reward}\nSecret: {secret}\nLink: {link}")
        except: bot.reply_to(message, "❌ Format: `/addtask TASK_ID REWARD SECRET_CODE LINK`")

    elif cmd == '/check':
        try:
            uid = int(message.text.split()[1])
            user = users_col.find_one({"user_id": uid})
            if not user: return bot.reply_to(message, "❌ User not found.")
            refs = refs_col.count_documents({"referrer_id": uid})
            status = "🔴 BANNED" if user.get("is_banned", 0) == 1 else "🟢 ACTIVE"
            bot.reply_to(message, f"🕵️ <b>User Info:</b>\n\n🆔 ID: {uid}\n💰 Coins: {user.get('coins', 0)}\n👥 Referrals: {refs}\n📅 Joined: {user.get('join_date', 'N/A')}\n📊 Status: {status}")
        except: bot.reply_to(message, "❌ Format: `/check USER_ID`")
        
    elif cmd == '/change':
        new_link = message.text.replace('/change', '').strip()
        if new_link:
            settings_col.update_one({"name": "key_link"}, {"$set": {"value": new_link}}, upsert=True)
            bot.reply_to(message, f"✅ <b>Link Updated!</b>\nNew link for keys:\n{new_link}")

    elif cmd == '/admin':
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(InlineKeyboardButton("➕ Add Channel", callback_data="add_channel"), InlineKeyboardButton("➖ Remove Channel", callback_data="remove_channel"))
        markup.add(InlineKeyboardButton("📋 View Added Channels", callback_data="view_channels"), InlineKeyboardButton("📊 Stats & Users", callback_data="adm_stats"))
        markup.add(InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast"), InlineKeyboardButton("🚫 Ban User", callback_data="adm_ban"))
        bot.send_message(message.chat.id, "👨‍💻 <b>Admin Panel V3 (Features Edition)</b>", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["add_channel", "remove_channel", "view_channels"] or call.data.startswith("adm_") or call.data.startswith("style_"))
def admin_callbacks(call):
    if call.message.chat.id != ADMIN_ID: return
    if call.data.startswith("style_"):
        style = call.data.split("_")[1]
        data = temp_channel_data.get(call.message.chat.id)
        if data:
            channels_col.insert_one({"channel_id": data['ch_id'], "link": data['link'], "style": style})
            bot.edit_message_text(f"✅ Channel <code>{data['ch_id']}</code> added!", chat_id=call.message.chat.id, message_id=call.message.message_id)
            del temp_channel_data[call.message.chat.id]
        return
    if call.data == "add_channel":
        msg = bot.send_message(call.message.chat.id, "🤖 Channel ID bhejo:")
        bot.register_next_step_handler(msg, process_add_channel)
    elif call.data == "view_channels":
        channels = list(channels_col.find())
        text = "📋 <b>Added Channels:</b>\n\n" if channels else "❌ No channels."
        for ch in channels: text += f"ID: <code>{ch.get('channel_id')}</code>\nLink: {ch.get('link')}\n\n"
        bot.send_message(call.message.chat.id, text, disable_web_page_preview=True)
    elif call.data == "remove_channel":
        msg = bot.send_message(call.message.chat.id, "🗑️ Channel ID bhejo:")
        bot.register_next_step_handler(msg, lambda m: [channels_col.delete_one({"channel_id": m.text.strip()}), bot.send_message(m.chat.id, "✅ Removed!")])
    elif call.data == "adm_stats":
        tot = users_col.count_documents({})
        bot.send_message(call.message.chat.id, f"📊 <b>BOT STATS</b>\n👥 Total Users: {tot}")
    elif call.data == "adm_broadcast":
        msg = bot.send_message(call.message.chat.id, "📢 Broadcast message bhejo:")
        bot.register_next_step_handler(msg, process_broadcast)
    elif call.data == "adm_ban":
        msg = bot.send_message(call.message.chat.id, "🚫 User ID to BAN:")
        bot.register_next_step_handler(msg, lambda m: toggle_ban(m, 1))

def process_add_channel(message):
    ch_id = message.text.strip()
    try:
        invite_link = bot.create_chat_invite_link(ch_id, creates_join_request=True).invite_link
        temp_channel_data[message.chat.id] = {'ch_id': ch_id, 'link': invite_link}
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔵 Blue", callback_data="style_primary"), InlineKeyboardButton("🟢 Green", callback_data="style_success"))
        bot.send_message(message.chat.id, "🎨 <b>Color choose karein:</b>", reply_markup=markup)
    except Exception as e: bot.send_message(message.chat.id, f"❌ Error: {e}")

def process_broadcast(message):
    bot.send_message(message.chat.id, "⏳ Broadcasting...")
    for u in users_col.find({"is_banned": 0}):
        try: bot.copy_message(u['user_id'], message.chat.id, message.message_id)
        except: pass
    bot.send_message(message.chat.id, "✅ <b>Broadcast Done!</b>")

def toggle_ban(message, status):
    users_col.update_one({"user_id": int(message.text.strip())}, {"$set": {"is_banned": status}})
    bot.reply_to(message, "✅ Done!")

# ================= JOIN REQUEST & FORCE SUB =================
def get_unjoined_channels(user_id):
    unjoined = []
    for ch in list(channels_col.find()):
        joined = False
        try:
            if bot.get_chat_member(ch['channel_id'], user_id).status in ['member', 'administrator', 'creator']: joined = True
        except: pass
        if not joined and join_reqs_col.find_one({"user_id": user_id, "channel_id": ch['channel_id']}): joined = True
        if not joined: unjoined.append(ch)
    return unjoined

@bot.chat_join_request_handler()
def handle_join_request(message: telebot.types.ChatJoinRequest):
    join_reqs_col.insert_one({"user_id": message.from_user.id, "channel_id": str(message.chat.id)})

@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    if flood_check(uid) or is_user_banned(uid): return

    if not users_col.find_one({"user_id": uid}):
        users_col.insert_one({"user_id": uid, "username": message.from_user.username or "Unknown", "join_date": datetime.now().strftime("%Y-%m-%d"), "coins": 0, "is_banned": 0, "last_bonus": 0, "streak": 0})
        args = message.text.split()
        if len(args) > 1 and args[1].isdigit():
            ref_id = int(args[1])
            if ref_id != uid and not refs_col.find_one({"user_id": uid}):
                users_col.update_one({"user_id": ref_id}, {"$inc": {"coins": 2}})
                refs_col.insert_one({"user_id": uid, "referrer_id": ref_id})
                try: bot.send_message(ref_id, "🎉 <b>Congrats!</b>\nKisi ne aapke link se bot start kiya hai. <b>+2 Coins</b> Added!")
                except: pass
    send_force_sub(message.chat.id, uid)

def send_force_sub(chat_id, user_id):
    unjoined = get_unjoined_channels(user_id)
    if not unjoined: return send_main_menu(chat_id)
        
    markup = InlineKeyboardMarkup()
    for ch in unjoined: markup.add(InlineKeyboardButton("Join Channel", url=ch['link'], style=ch.get('style', 'primary')))
    markup.add(InlineKeyboardButton("✅ Done !!", callback_data="verify_channels", style="success"))
    bot.send_message(chat_id, "💎 𝗪𝗘𝗟𝗖𝗢𝗠𝗘 𝗧𝗢 𝗩𝗔𝗟𝗜 𝗠𝗢𝗗𝗦\n📢 𝗡𝗶𝗰𝗵𝗲 𝗱𝗶𝘆𝗲 𝗴𝗮𝘆𝗲 𝘀𝗮𝗿𝗲 𝗰𝗵𝗮𝗻𝗻𝗲𝗹𝘀 𝗝𝗢𝗜𝗡 𝗸𝗮𝗿𝗻𝗮 𝗭𝗔𝗥𝗨𝗥𝗜 𝗵𝗮𝗶", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "verify_channels")
def verify_callback(call):
    uid = call.from_user.id
    if get_unjoined_channels(uid): return bot.answer_callback_query(call.id, "❌ Aapne sabhi channels join nahi kiye!", show_alert=True)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    send_main_menu(call.message.chat.id)
    bot.answer_callback_query(call.id, "✅ Verified!", show_alert=False)

# ================= MAIN MENU & ADVANCED FEATURES =================
def send_main_menu(chat_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("🛒 VIP Key Shop"), KeyboardButton("🎁 Daily Streak Bonus"))
    markup.add(KeyboardButton("📝 Earn Tasks"), KeyboardButton("🎲 Mini Games"))
    markup.add(KeyboardButton("🔗 Refer & Earn"), KeyboardButton("👤 My Account"))
    markup.add(KeyboardButton("🏆 Leaderboard"), KeyboardButton("🎟️ Redeem Promo"))
    bot.send_message(chat_id, "✅ Main Menu:", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def text_commands(message):
    uid = message.from_user.id
    if flood_check(uid) or is_user_banned(uid): return
    if get_unjoined_channels(uid): return send_force_sub(message.chat.id, uid)
    
    user = users_col.find_one({"user_id": uid})
    if not user: return
    coins = user.get('coins', 0)
    text = message.text

    if text == "👤 My Account":
        bot.send_message(uid, f"👤 <b>Account Stats</b>\n\n🆔 ID: <code>{uid}</code>\n💰 Coins: <b>{coins}</b>\n🔥 Streak: <b>{user.get('streak', 0)} Days</b>")
        
    elif text == "🔗 Refer & Earn":
        bot.send_message(uid, f"📢 <b>REFER & EARN</b>\nInvite friends & get <b>2 Coins</b> per join!\n\n🔗 Your Link:\nhttps://t.me/{bot.get_me().username}?start={uid}")

    elif text == "🎁 Daily Streak Bonus":
        last_bonus = user.get('last_bonus', 0)
        streak = user.get('streak', 0)
        now = time.time()
        
        if now - last_bonus < 86400: # 24 hours
            left = int((86400 - (now - last_bonus)) / 3600)
            bot.send_message(uid, f"⏳ <b>Wait!</b>\nAapko agla bonus <b>{left} ghante</b> baad milega.")
        else:
            if now - last_bonus > 172800: streak = 1 
            else: streak = min(streak + 1, 7) 
            
            reward = streak * 2 
            users_col.update_one({"user_id": uid}, {"$inc": {"coins": reward}, "$set": {"last_bonus": now, "streak": streak}})
            bot.send_message(uid, f"🔥 <b>Day {streak} Streak Bonus!</b>\nAapko <b>{reward} Coins</b> mil gaye hain.\n\n<i>Kal aana mat bhoolna, streak tut jayegi!</i>")

    elif text == "📝 Earn Tasks":
        all_tasks = list(tasks_col.find())
        pending_tasks = [t for t in all_tasks if not task_users_col.find_one({"user_id": uid, "task_id": t['task_id']})]
        if not pending_tasks: return bot.send_message(uid, "🎉 Aapne saare tasks complete kar liye hain! Naye tasks ka wait karein.")
        
        markup = InlineKeyboardMarkup()
        for t in pending_tasks:
            markup.add(InlineKeyboardButton(f"Task: {t['task_id']} (+{t['reward']} Coins)", callback_data=f"task_{t['task_id']}"))
        bot.send_message(uid, "📝 <b>Available Tasks:</b>\nTask complete karein aur secret code lakar coins jeetein!", reply_markup=markup)

    elif text == "🎲 Mini Games":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🪙 Play 5 Coins", callback_data="game_5"), InlineKeyboardButton("🪙 Play 10 Coins", callback_data="game_10"))
        markup.add(InlineKeyboardButton("🪙 Play 20 Coins", callback_data="game_20"))
        bot.send_message(uid, f"🎲 <b>Coin Toss Game (Double or Nothing)</b>\nAapke Coins: <b>{coins}</b>\nKitne coins lagana chahte ho?", reply_markup=markup)

    elif text == "🏆 Leaderboard":
        top = list(refs_col.aggregate([{"$group": {"_id": "$referrer_id", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}, {"$limit": 5}]))
        msg = "🏆 <b>TOP REFERRERS</b> 🏆\n\n"
        for i, t in enumerate(top): msg += f"{i+1}. User <code>{t['_id']}</code> - {t['count']} Invites\n"
        bot.send_message(uid, msg)

    elif text == "🎟️ Redeem Promo":
        msg = bot.send_message(uid, "🎫 Apna Promo Code enter karein:")
        bot.register_next_step_handler(msg, process_promo)

    elif text == "🛒 VIP Key Shop":
        setting = settings_col.find_one({"name": "base_price"})
        bp = int(setting['value']) if setting else 15
        markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton(f"🔑 1-Day VIP ({bp} Coins)", callback_data=f"buy_1_{bp}"),
            InlineKeyboardButton(f"🔑 3-Day VIP ({bp*2} Coins)", callback_data=f"buy_3_{bp*2}")
        )
        bot.send_message(uid, f"🛒 <b>VIP KEY SHOP</b>\nAapke Coins: <b>{coins}</b>", reply_markup=markup)

# ================= TASKS & GAMES SYSTEM =================
@bot.callback_query_handler(func=lambda call: call.data.startswith("task_"))
def handle_task(call):
    task_id = call.data.split("_")[1]
    task = tasks_col.find_one({"task_id": task_id})
    if not task: return bot.answer_callback_query(call.id, "❌ Task removed!")
    
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🌐 Open Task Link", url=task['link']))
    msg = bot.send_message(call.message.chat.id, f"📝 <b>Task ID:</b> {task_id}\n💰 <b>Reward:</b> {task['reward']} Coins\n\n1️⃣ Link open karein.\n2️⃣ Wahan diye gaye 'Secret Code' ko copy karein.\n3️⃣ Abhi yahan bot ko wo code message karein👇", reply_markup=markup)
    bot.register_next_step_handler(msg, lambda m: verify_task_code(m, task))

def verify_task_code(message, task):
    uid, code = message.from_user.id, message.text.strip()
    if task_users_col.find_one({"user_id": uid, "task_id": task['task_id']}): return bot.send_message(uid, "❌ Aap already ye task kar chuke hain.")
    
    if code == task['secret']:
        users_col.update_one({"user_id": uid}, {"$inc": {"coins": task['reward']}})
        task_users_col.insert_one({"user_id": uid, "task_id": task['task_id']})
        bot.send_message(uid, f"🎉 <b>Task Verified!</b>\nAapko <b>{task['reward']} Coins</b> mil gaye hain!")
    else: bot.send_message(uid, "❌ <b>Wrong Secret Code!</b> Try again.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("game_"))
def handle_game_setup(call):
    amt = int(call.data.split("_")[1])
    uid = call.from_user.id
    user = users_col.find_one({"user_id": uid})
    if user.get('coins', 0) < amt: return bot.answer_callback_query(call.id, f"❌ Aapke paas {amt} coins nahi hain!", show_alert=True)
    
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🗣️ Heads", callback_data=f"play_{amt}_Heads"), InlineKeyboardButton("🪙 Tails", callback_data=f"play_{amt}_Tails"))
    bot.edit_message_text(f"🎲 <b>Bet:</b> {amt} Coins\nChuno Heads ya Tails?", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("play_"))
def handle_game_play(call):
    parts = call.data.split("_")
    amt, choice = int(parts[1]), parts[2]
    uid = call.from_user.id
    
    user = users_col.find_one({"user_id": uid})
    if user.get('coins', 0) < amt: return bot.answer_callback_query(call.id, "❌ Not enough coins!", show_alert=True)
    
    users_col.update_one({"user_id": uid}, {"$inc": {"coins": -amt}}) 
    result = random.choice(["Heads", "Tails"])
    
    if choice == result:
        users_col.update_one({"user_id": uid}, {"$inc": {"coins": amt * 2}}) 
        bot.edit_message_text(f"🎲 Coin Flipping...\n\nResult: <b>{result}</b>\n🎉 <b>YOU WIN!</b> You got {amt*2} Coins!", chat_id=call.message.chat.id, message_id=call.message.message_id)
    else:
        bot.edit_message_text(f"🎲 Coin Flipping...\n\nResult: <b>{result}</b>\n😢 <b>YOU LOSE!</b> Better luck next time.", chat_id=call.message.chat.id, message_id=call.message.message_id)

# ================= PROMO & SHOP SYSTEM =================
def process_promo(message):
    uid, code = message.from_user.id, message.text.strip().upper()
    promo = promo_col.find_one({"code": code})
    if not promo: return bot.send_message(uid, "❌ Invalid Promo Code!")
    if time.time() > promo.get('expiry', 0): return bot.send_message(uid, "❌ Ye Promo Code Expire ho chuka hai!")
    if promo.get('used_count', 0) >= promo['max_uses']: return bot.send_message(uid, "❌ Ye code ki limit khatam ho chuki hai!")
    if promo_users_col.find_one({"user_id": uid, "code": code}): return bot.send_message(uid, "❌ Aapne ye code pehle hi use kar liya hai!")
    
    users_col.update_one({"user_id": uid}, {"$inc": {"coins": promo['reward']}})
    promo_col.update_one({"code": code}, {"$inc": {"used_count": 1}})
    promo_users_col.insert_one({"user_id": uid, "code": code})
    bot.send_message(uid, f"🎉 <b>Success!</b>\nPromo Code se <b>{promo['reward']} Coins</b> mil gaye!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def handle_shop_buy(call):
    uid, parts = call.from_user.id, call.data.split("_")
    days, price = int(parts[1]), int(parts[2])
    if get_unjoined_channels(uid): return bot.answer_callback_query(call.id, "❌ Pehle channels join karo!", show_alert=True)
    
    user = users_col.find_one({"user_id": uid})
    if user.get('coins', 0) >= price:
        users_col.update_one({"user_id": uid}, {"$inc": {"coins": -price}})
        bot.delete_message(call.message.chat.id, call.message.message_id)
        
        req_text = f"🆕 <b>Key Request ({days}-Day)</b>\n👤 {call.from_user.first_name}\n🆔 <code>{uid}</code>"
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ APPROVE", callback_data=f"app_{uid}_{price}"), InlineKeyboardButton("❌ REJECT", callback_data=f"rej_{uid}_{price}"))
        try:
            bot.send_message(APPROVAL_CHANNEL, req_text, reply_markup=markup)
            bot.send_message(uid, "⏳ <b>Request Sent!</b>\nAdmin approval ka wait karein.")
        except:
            users_col.update_one({"user_id": uid}, {"$inc": {"coins": price}})
            bot.send_message(uid, "❌ Setup Error. Coins refunded.")
    else: bot.answer_callback_query(call.id, f"❌ Not enough coins!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("app_") or call.data.startswith("rej_"))
def handle_approval(call):
    if call.from_user.id != ADMIN_ID: return bot.answer_callback_query(call.id, "❌ Admin Only", show_alert=True)
    parts = call.data.split("_")
    action, uid, refund = parts[0], int(parts[1]), int(parts[2])

    if action == "app":
        try: bot.edit_message_text(f"{call.message.text}\n\n✅ <b>APPROVED</b>", chat_id=call.message.chat.id, message_id=call.message.message_id)
        except: pass
        key = f"{random.randint(1000000000, 9999999999)}"
        setting = settings_col.find_one({"name": "key_link"})
        link = setting['value'] if setting else "No link"
        try: bot.send_message(uid, f"🎉 <b>Approved!</b>\n\nKey - <code>{key}</code>\nAPK - {link}", disable_web_page_preview=True)
        except: pass
    elif action == "rej":
        try: bot.edit_message_text(f"{call.message.text}\n\n❌ <b>REJECTED</b>", chat_id=call.message.chat.id, message_id=call.message.message_id)
        except: pass
        users_col.update_one({"user_id": uid}, {"$inc": {"coins": refund}})
        try: bot.send_message(uid, "❌ <b>Request Rejected!</b> Coins refunded.")
        except: pass

if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    print("V3 Ultimate Features Bot is running...")
    bot.infinity_polling(allowed_updates=telebot.util.update_types)
