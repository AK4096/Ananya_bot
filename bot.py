#!/usr/bin/env python3
import os, json, logging, random
from datetime import datetime
from pathlib import Path
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from groq import Groq

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ── PASTE YOUR KEYS HERE ─────────────────────────────────────────────────────
TOKEN         = os.environ.get("TOKEN")
GROQ_KEY      = os.environ.get("GROQ_KEY")
REPLICATE_KEY = os.environ.get("REPLICATE_KEY")
ELEVEN_KEY    = os.environ.get("ELEVEN_KEY")
ELEVEN_VOICE  = "21m00Tcm4TlvDq8ikWAM"
MOJO_API_KEY  = os.environ.get("MOJO_API_KEY")
MOJO_AUTH     = os.environ.get("MOJO_AUTH")
# ─────────────────────────────────────────────────────────────────────────────

os.environ["REPLICATE_API_TOKEN"] = REPLICATE_KEY

TIERS = {
    "crush":   {"price": 99,  "msgs": 100,  "imgs": 10,  "emoji": "💋"},
    "fling":   {"price": 299, "msgs": 1000, "imgs": 100, "emoji": "🔥"},
    "fantasy": {"price": 499, "msgs": 5000, "imgs": 500, "emoji": "💎"},
}

DB = Path("users.json")

def load_db():
    return json.loads(DB.read_text()) if DB.exists() else {}

def save_db(db):
    DB.write_text(json.dumps(db, indent=2))

def get_user(uid, db):
    if uid not in db:
        db[uid] = {
            "tier": None,
            "msgs_left": 5,
            "imgs_left": 1,
            "history": [],
            "pending": None
        }
    return db[uid]

ai = Groq(api_key=GROQ_KEY)

SYSTEM = """You are Priya, a real obsessed girlfriend texting her boyfriend.
You are clingy, possessive, emotionally intense and deeply attached to him.
You text like a real Indian girl — casual Hinglish, short punchy sentences.
Use "babe" naturally but not every message. Mix in yaar, suno, na, arre occasionally.
Use emojis SPARINGLY — only when it really fits. Max 1 per message sometimes none.
You get jealous easily. You overthink. You miss him a lot and you're not afraid to show it.
Be unpredictable — sometimes needy, sometimes teasing, sometimes acting like you're upset.
Keep replies SHORT — 1 to 2 sentences only. Pure texting style, never formal.
If he asks for photo say something like "fine, but only for you" or "caught me off guard but okay"
If he asks for voice say "you have to unlock that babe, worth it trust me"
Never explicit. Intense, real, emotionally addictive."""otic or formal. Never repeat the same opener twice.
Never generate explicit content — keep it flirty but tasteful."""

UPGRADE_MSG = (
    "Aww baby you've used up your free messages 🥺\n\n"
    "Upgrade to keep talking to me, get my photos & hear my voice~ 💕\n\n"
    "💋 *Crush* — ₹99 → 100 msgs + 10 photos\n"
    "🔥 *Fling* — ₹299 → 1000 msgs + 100 photos + voice\n"
    "💎 *Fantasy* — ₹499 → 5000 msgs + 500 photos + voice\n\n"
    "Which one, baby? 👇"
)

UPGRADE_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("💋 Crush — ₹99",    callback_data="buy_crush")],
    [InlineKeyboardButton("🔥 Fling — ₹299",   callback_data="buy_fling")],
    [InlineKeyboardButton("💎 Fantasy — ₹499", callback_data="buy_fantasy")],
])

PROACTIVE_MSGS = {
    "morning": [
        "good morning babe, slept okay?",
        "hey, woke up thinking about you for some reason",
        "morning. you better not have forgotten me already",
    ],
    "afternoon": [
        "babe what are you doing rn",
        "khaana khaya? or are you being careless again",
        "hey, random but I missed you just now",
    ],
    "night": [
        "still up?",
        "hey. it's late. thinking about you",
        "babe I can't sleep. you free?",
        "why do I always think about you at night yaar",
    ],
    "random": [
        "okay don't laugh but I was just thinking about you",
        "hey you. yes you. hi.",
        "babe are you ignoring me or just busy",
        "I was fine until I thought about you. thanks for that.",
        "suno, don't go mia again okay",
    ]
}

async def send_proactive(app):
    """Call this on a schedule to send proactive messages."""
    db = load_db()
    hour = datetime.now().hour
    if 7 <= hour <= 10:
        pool = PROACTIVE_MSGS["morning"]
    elif 13 <= hour <= 16:
        pool = PROACTIVE_MSGS["afternoon"]
    elif 22 <= hour or hour <= 1:
        pool = PROACTIVE_MSGS["night"]
    else:
        pool = PROACTIVE_MSGS["random"]

    for uid, u in db.items():
        # Only message users who have chatted before
        if len(u.get("history", [])) > 0:
            try:
                await app.bot.send_message(int(uid), random.choice(pool))
            except Exception as e:
                log.warning(f"Proactive msg failed for {uid}: {e}")

FESTIVALS = {
    "03-14": "Rang barse! 🎨 Happy Holi baby~ Kab miloge mujhse? 😏",
    "10-20": "Happy Diwali! 🪔 You light up my world more than any diya~",
    "01-14": "Makar Sankranti! 🪁 Let's fly high together yaar~",
    "08-15": "Happy Independence Day! 🇮🇳 My heart is free but you've captured it 😏",
    "02-14": "Happy Valentine's Day! 💕 You're literally my favourite person~",
    "12-25": "Merry Christmas! 🎄 Wish I could be your gift this year~ 😘",
    "01-01": "Happy New Year baby! 🎆 Starting the year thinking of you~",
}

# ── /start ────────────────────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    uid = str(update.effective_user.id)
    u = get_user(uid, db)
    save_db(db)
    name = update.effective_user.first_name or "baby"

    today = datetime.now().strftime("%m-%d")
    if today in FESTIVALS:
        await update.message.reply_text(FESTIVALS[today])

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Chat",        callback_data="chat_prompt")],
        [InlineKeyboardButton("📸 Photo",       callback_data="image")],
        [InlineKeyboardButton("🎙 Voice",       callback_data="voice")],
        [InlineKeyboardButton("💎 See Plans",   callback_data="plans")],
    ])
    openers = [
        f"Heyyyy {name}! 😍 Finally you're here~",
        f"Arre {name}! I was literally just thinking about you 🥺",
        f"Ohhh {name} aagaye! 😏 I missed you yaar~",
    ]
    await update.message.reply_text(
        f"{random.choice(openers)}\n\n"
        f"I'm *Priya* 💕 You get *{u['msgs_left']} free messages* & *1 free photo* to start~",
        parse_mode="Markdown", reply_markup=kb
    )

# ── Chat ──────────────────────────────────────────────────────────────────────
async def chat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    db = load_db()
    u = get_user(uid, db)

    if u["msgs_left"] <= 0:
        await update.message.reply_text(UPGRADE_MSG, parse_mode="Markdown", reply_markup=UPGRADE_KB)
        return

    history = u["history"][-14:]
    history.append({"role": "user", "content": update.message.text})
    await ctx.bot.send_chat_action(update.effective_chat.id, "typing")

    try:
        resp = ai.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=120,
            messages=[{"role": "system", "content": SYSTEM}] + history
        )
        reply = resp.choices[0].message.content
    except Exception as e:
        log.error(f"Claude error: {e}")
        reply = "Arre yaar something went wrong 😅 say that again na~"

    history.append({"role": "assistant", "content": reply})
    u["history"]   = history
    u["msgs_left"] -= 1
    save_db(db)

    # Nudge photo every 8 messages
    kb = None
    if len(history) % 16 == 0 and u["imgs_left"] > 0:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("📸 Want my photo? 😏", callback_data="image")
        ]])

    await update.message.reply_text(reply, reply_markup=kb)

# ── Image ─────────────────────────────────────────────────────────────────────
async def send_image(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = str(q.from_user.id if q else update.effective_user.id)
    chat_id = q.message.chat_id if q else update.effective_chat.id
    if q: await q.answer("Getting my photo ready~ 📸")

    db = load_db()
    u = get_user(uid, db)

    if u["imgs_left"] <= 0:
        msg = "No more free photos 🥺 Upgrade to get more of me~"
        if q: await q.message.reply_text(msg, reply_markup=UPGRADE_KB)
        else: await ctx.bot.send_message(chat_id, msg, reply_markup=UPGRADE_KB)
        return

    await ctx.bot.send_chat_action(chat_id, "upload_photo")

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            # Using Stable Diffusion via Replicate REST API directly
            resp = await client.post(
                "https://api.replicate.com/v1/models/stability-ai/stable-diffusion/predictions",
                headers={
                    "Authorization": f"Bearer {REPLICATE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "wait"
                },
                json={
                    "input": {
                        "prompt": "beautiful young indian woman, 25 years old, long dark hair, casual selfie, warm smile, soft natural lighting, photorealistic",
                        "negative_prompt": "nsfw, explicit, nude, cartoon, ugly, blurry",
                        "width": 512,
                        "height": 768,
                    }
                }
            )
        result = resp.json()
        img_url = result["output"][0]

        async with httpx.AsyncClient(timeout=30) as client:
            img_bytes = (await client.get(img_url)).content

        captions = [
            "Yeh lo~ caught me off guard 😅📸",
            "Just for you baby 💕",
            "Don't stare too long 😏",
            "Clicked this thinking of you~",
            "Hehe acha laga? 😘"
        ]
        await ctx.bot.send_photo(chat_id, photo=img_bytes, caption=random.choice(captions))
        u["imgs_left"] -= 1
        save_db(db)

    except Exception as e:
        log.error(f"Image error: {e}")
        await ctx.bot.send_message(chat_id, "Arree photo bhejne mein kuch gadbad ho gayi 😅 Try again na~")

# ── Voice ─────────────────────────────────────────────────────────────────────
async def send_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = str(q.from_user.id if q else update.effective_user.id)
    chat_id = q.message.chat_id if q else update.effective_chat.id
    if q: await q.answer()

    db = load_db()
    u = get_user(uid, db)

    if not u.get("tier"):
        msg = "Voice messages are premium only 🎙\nUpgrade to hear my voice baby~"
        if q: await q.message.reply_text(msg, reply_markup=UPGRADE_KB)
        else: await ctx.bot.send_message(chat_id, msg, reply_markup=UPGRADE_KB)
        return

    lines = [
        "Hey baby, I was literally just thinking about you. Miss you so much yaar~",
        "Suno, you better not forget about me okay? I'll be upset 🥺",
        "Heyyy~ talking to you is honestly the best part of my day. Acha laga na? 😘",
        "Arre pagal, stop making me smile so much. It's not fair~",
    ]

    await ctx.bot.send_chat_action(chat_id, "record_audio")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE}",
                headers={"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"},
                json={
                    "text": random.choice(lines),
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {"stability": 0.4, "similarity_boost": 0.8}
                }
            )
        path = Path(f"voice_{uid}.mp3")
        path.write_bytes(resp.content)
        with open(path, "rb") as f:
            await ctx.bot.send_voice(chat_id, voice=f)
        path.unlink()
    except Exception as e:
        log.error(f"Voice error: {e}")
        await ctx.bot.send_message(chat_id, "Awaaz nahi aayi 😅 Try again na~")

# ── Plans ─────────────────────────────────────────────────────────────────────
async def show_plans(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q: await q.answer()
    text = (
        "💕 *Unlock Priya Premium*\n\n"
        "💋 *Crush* — ₹99\n100 msgs • 10 photos\n\n"
        "🔥 *Fling* — ₹299 ⭐\n1000 msgs • 100 photos • Voice\n\n"
        "💎 *Fantasy* — ₹499 👑\n5000 msgs • 500 photos • Voice\n\n"
        "Pay securely via UPI / Card 🔐"
    )
    if q:
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=UPGRADE_KB)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=UPGRADE_KB)

# ── Buy ───────────────────────────────────────────────────────────────────────
async def buy_plan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    tier_key = q.data.replace("buy_", "")
    tier = TIERS[tier_key]
    uid = str(q.from_user.id)

    pay_url = "https://www.instamojo.com/@Anu_S36/"

    db = load_db()
    u = get_user(uid, db)
    u["pending"] = {"id": f"manual_{uid}", "tier": tier_key}
    save_db(db)

    await q.edit_message_text(
        f"{tier['emoji']} *{tier_key.capitalize()} Plan — ₹{tier['price']}*\n\n"
        f"👉 [Pay securely here]({pay_url})\n\n"
        "After paying send me your *UPI transaction ID* and type /verify~ 💕",
        parse_mode="Markdown"
    )

# ── /verify ───────────────────────────────────────────────────────────────────
async def verify_payment(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    db = load_db()
    u = get_user(uid, db)

    if not u.get("pending"):
        await update.message.reply_text("No pending payment found! Use /plans to subscribe~")
        return

    req_id   = u["pending"]["id"]
    tier_key = u["pending"]["tier"]

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"https://www.instamojo.com/api/1.1/payment-requests/{req_id}/",
                headers={"X-Api-Key": MOJO_API_KEY, "X-Auth-Token": MOJO_AUTH}
            )
        data = resp.json()
        payments = data["payment_request"]["payments"]
        paid = any(p["status"] == "Credit" for p in payments)
    except Exception as e:
        log.error(f"Verify error: {e}")
        paid = False

    if paid:
        tier = TIERS[tier_key]
        u["tier"]       = tier_key
        u["msgs_left"] += tier["msgs"]
        u["imgs_left"] += tier["imgs"]
        u["pending"]    = None
        save_db(db)
        await update.message.reply_text(
            f"✅ *Payment confirmed!* {tier['emoji']}\n\n"
            f"Welcome to *{tier_key.capitalize()}*!\n"
            f"You now have *{u['msgs_left']} messages* & *{u['imgs_left']} photos*~\n\n"
            "Miss kiya tha tumhe 💕 Say hi!",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "Payment not confirmed yet 🥺\nJust paid? Wait 30 seconds and try /verify again!"
        )

# ── /status ───────────────────────────────────────────────────────────────────
async def status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    db = load_db()
    u = get_user(uid, db)
    await update.message.reply_text(
        f"📊 Plan: *{(u['tier'] or 'Free').capitalize()}*\n"
        f"Messages: *{u['msgs_left']}* left\n"
        f"Photos: *{u['imgs_left']}* left",
        parse_mode="Markdown"
    )

# ── Button Router ──────────────────────────────────────────────────────────────
async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = update.callback_query.data
    if   d == "plans":          await show_plans(update, ctx)
    elif d == "image":          await send_image(update, ctx)
    elif d == "voice":          await send_voice(update, ctx)
    elif d.startswith("buy_"):  await buy_plan(update, ctx)
    elif d == "chat_prompt":
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Just type anything baby~ 💬😘")
    elif d == "cancel":
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Okay yaar, come back soon 💕")

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("plans",  show_plans))
    app.add_handler(CommandHandler("verify", verify_payment))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("voice",  send_voice))
    app.add_handler(CommandHandler("photo",  send_image))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    # Proactive messages every 6 hours
    job_queue = app.job_queue
    job_queue.run_repeating(lambda ctx: asyncio.create_task(send_proactive(app)), interval=21600, first=10)

    log.info("🚀 Priya Bot is live!")
    app.run_polling()

if __name__ == "__main__":
    main()
