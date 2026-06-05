import os
import base64
import telebot
import requests
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uvicorn
import threading

# --- CONFIGURATION ---
BOT_TOKEN = "8679608771:AAG7UVBy61pF8-JnN9-bwf9wNp631ptsuz4"
CLOUDFLARE_SECRET_KEY = "0x4AAAAAADdlsEueqshqwNC30WwX3e-l3h4"
SERVER_URL = "https://anti-bypass-production.up.railway.app"
CHANNEL_ID = "@Antibypassbots"

MAIN_CHANNEL = "https://t.me/c/3946440796/1"
BACKUP_CHANNEL = "https://t.me/c/3738247687/1"
BOT_LINK = "https://t.me/Antibypassbots"

bot = telebot.TeleBot(BOT_TOKEN)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# --- FUNCTIONS ---
def get_tiny_url(long_url):
    try:
        response = requests.get(f"https://tinyurl.com/api-create.php?url={long_url}")
        return response.text if response.status_code == 200 else long_url
    except:
        return long_url

def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def encode_url(url: str) -> str:
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")

def decode_url(encoded_str: str) -> str:
    try:
        padding = 4 - (len(encoded_str) % 4)
        if padding < 4:
            encoded_str += "=" * padding
        return base64.urlsafe_b64decode(encoded_str.encode()).decode()
    except:
        return None

# --- GUIDE MESSAGE ---
GUIDE_TEXT = """
╔══════════════════════════╗
      🤖 <b>ANTI-BYPASS BOT GUIDE</b>
╚══════════════════════════╝

📌 <b>Supported Shortener Links:</b>
• VPLink
• Aro Link
• Shorte.st
• GPLinks
• Linkvertise
• Adbull
• Kilo Links
• Aur bhi koi bhi shortener!

━━━━━━━━━━━━━━━━━━━━

📋 <b>How to Use:</b>

1️⃣ Apna shortener link copy karo
2️⃣ Is bot mein paste karo
3️⃣ Bot tumhe ek <b>secure protected link</b> dega
4️⃣ Woh link share karo apne users ke saath
5️⃣ User link open kare → Captcha solve kare → File mil jaayegi!

━━━━━━━━━━━━━━━━━━━━

✅ <b>Example:</b>
<code>https://vplink.in/xxxxxxx</code>
👆 Ye link bas yahan paste karo!

━━━━━━━━━━━━━━━━━━━━

⚡ <b>Commands:</b>
/start — Bot start karo
/guide — Ye guide dobara dekho
/about — Bot ke baare mein

━━━━━━━━━━━━━━━━━━━━
🔒 Powered by Anti-Bypass Bot
"""

ABOUT_TEXT = """
🤖 <b>Anti-Bypass Bot</b>

Ye bot shortener links ko bypass-proof bana deta hai.
Cloudflare Turnstile Captcha use karke direct bypass rokta hai.

👨‍💻 <b>Features:</b>
• ✅ All shortener links support
• ✅ Cloudflare Captcha Protection
• ✅ Instant short link generation
• ✅ 100% Free

📢 <b>Join our Channel:</b>
👉 @Antibypassbots
"""

# --- TELEGRAM BOT HANDLERS ---
@bot.message_handler(commands=['start'])
def start_command(message):
    name = message.from_user.first_name
    welcome = (
        f"👋 <b>Welcome, {name}!</b>\n\n"
        "Main tumhare shortener links ko <b>bypass-proof</b> bana deta hoon!\n\n"
        "📌 <b>Kaise use karein?</b>\n"
        "Bas apna shortener link yahan paste karo!\n\n"
        "🔍 Puri guide ke liye: /guide\n"
        "ℹ️ Bot ke baare mein: /about"
    )
    bot.reply_to(message, welcome, parse_mode="HTML", disable_web_page_preview=True)

@bot.message_handler(commands=['guide'])
def guide_command(message):
    bot.reply_to(message, GUIDE_TEXT, parse_mode="HTML", disable_web_page_preview=True)

@bot.message_handler(commands=['about'])
def about_command(message):
    bot.reply_to(message, ABOUT_TEXT, parse_mode="HTML", disable_web_page_preview=True)

@bot.message_handler(func=lambda message: message.text.startswith(('http://', 'https://')))
def process_link(message):
    user_id = message.from_user.id

    if not is_subscribed(user_id):
        layout = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🔒 <b>Pehle Channel Join Karo!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📢 <a href='{MAIN_CHANNEL}'>Main Channel Join Karo</a>\n\n"
            "Join karne ke baad apna link dobara bhejo. ✅"
        )
        bot.reply_to(message, layout, parse_mode="HTML", disable_web_page_preview=True)
        return

    original_url = message.text.strip()
    link_id = encode_url(original_url)
    long_protected_url = f"{SERVER_URL}/verify/{link_id}"
    short_link = get_tiny_url(long_protected_url)

    response_text = (
        "✅ <b>Link Successfully Protected!</b>\n\n"
        f"🔗 <b>Your Secure Link:</b>\n<code>{short_link}</code>\n\n"
        "📤 Isko apne users ke saath share karo!"
    )
    bot.reply_to(message, response_text, parse_mode="HTML", disable_web_page_preview=True)

@bot.message_handler(func=lambda message: True)
def unknown_message(message):
    bot.reply_to(
        message,
        "❓ Samajh nahi aaya!\n\n📌 Koi shortener link paste karo ya /guide dekho.",
        parse_mode="HTML"
    )

# --- WEB SERVER ---
def run_bot():
    try:
        print("✅ Bot polling started!")
        bot.infinity_polling(timeout=20, long_polling_timeout=10)
    except Exception as e:
        print(f"❌ Bot crashed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=run_bot, daemon=True).start()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
def root_page():
    return HTMLResponse("<h1>✅ Server Active</h1>")

@app.get("/verify/{link_id}", response_class=HTMLResponse)
async def serve_verify_page(request: Request, link_id: str):
    return templates.TemplateResponse("verify.html", {"request": request, "link_id": link_id})

@app.post("/redirect/{link_id}")
async def handle_verification(request: Request, link_id: str):
    form_data = await request.form()
    turnstile_response = form_data.get("cf-turnstile-response")
    payload = {"secret": CLOUDFLARE_SECRET_KEY, "response": turnstile_response}
    verify = requests.post("https://challenges.cloudflare.com/turnstile/v0/siteverify", data=payload)

    if verify.json().get("success"):
        url = decode_url(link_id)
        if url:
            return RedirectResponse(url=url, status_code=303)
    return HTMLResponse("<h3>❌ Verification Failed! Please try again.</h3>", status_code=403)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
