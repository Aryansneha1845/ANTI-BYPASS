import os
import base64
import telebot
from telebot import types
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uvicorn
import threading

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8679608771:AAEzRleDch3cxKXuFLkzjE4McltBZG2rzXQ")
CLOUDFLARE_SECRET_KEY = os.environ.get("CLOUDFLARE_SECRET_KEY", "0x4AAAAAADdlsEueqshqwNC30WwX3e-l3h4")
SERVER_URL = os.environ.get("SERVER_URL", "anti-bypass-production.up.railway.app")

bot = telebot.TeleBot(BOT_TOKEN)
app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

def encode_url(url: str) -> str:
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")

def decode_url(encoded_str: str) -> str:
    try:
        padding = 4 - (len(encoded_str) % 4)
        if padding < 4:
            encoded_str += "=" * padding
        return base64.urlsafe_b64decode(encoded_str.encode()).decode()
    except Exception:
        return None

def shorten_url(url: str) -> str:
    try:
        response = requests.get(f"https://tinyurl.com/api-create.php?url={url}", timeout=5)
        if response.status_code == 200:
            return response.text.strip()
    except Exception:
        pass
    return url  # fallback — original URL return karega

# --- TELEGRAM BOT LOGIC ---

@bot.message_handler(commands=['start'])
def start_command(message):
    bot.reply_to(message,
        "👋 <b>Welcome to Link Protector Bot!</b>\n\n"
        "I make your shortener links <b>bypass-proof</b> using Cloudflare security.\n\n"
        "📋 <b>How to use:</b>\n"
        "Just <b>paste any link</b> directly in the chat!\n\n"
        "✅ <b>Supported links:</b>\n"
        "• VPLink\n"
        "• Aro Link\n"
        "• AdLink\n"
        "• Any other shortener or http/https link\n\n"
        "⬇️ <b>Go ahead, paste your link below!</b>",
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda message: message.text and message.text.startswith(('http://', 'https://')))
def process_link(message):
    original_url = message.text.strip()
    link_id = encode_url(original_url)
    protected_url = f"https://{SERVER_URL}/verify/{link_id}"

    # TinyURL se chota karo
    short_url = shorten_url(protected_url)

    # Inline keyboard with Watch Ad + Link not working buttons
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📺 Watch Ad & Get Link", url=short_url)
    )
    markup.add(
        types.InlineKeyboardButton("❌ Link not working?", callback_data=f"broken|{link_id}")
    )

    response_text = (
        "🔒 <b>Link Protected Successfully!</b>\n\n"
        f"🔗 <b>Your Secure Link:</b>\n<code>{short_url}</code>\n\n"
        "📌 Share this link — users will watch a short ad, then get redirected!\n\n"
        "➕ Paste another link anytime!"
    )
    bot.reply_to(message, response_text, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("broken|"))
def handle_broken(call):
    bot.answer_callback_query(call.id, "Thanks for reporting! We'll look into it. 🙏", show_alert=True)

@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    bot.reply_to(message,
        "❓ <b>Hmm, that doesn't look like a link!</b>\n\n"
        "Please paste a valid link starting with <b>http://</b> or <b>https://</b>\n\n"
        "📌 <b>Example:</b>\n"
        "<code>https://vplink.in/yourlink</code>\n"
        "<code>https://arolink.in/yourlink</code>\n\n"
        "Just paste your link and I'll protect it! 🔒",
        parse_mode="HTML"
    )

# --- WEB SERVER LOGIC ---

@app.get("/")
async def root_page():
    return {"status": "Server is running perfectly!"}

@app.get("/verify/{link_id}", response_class=HTMLResponse)
async def serve_verify_page(request: Request, link_id: str):
    original_url = decode_url(link_id)
    if not original_url:
        return HTMLResponse(content="<h3>Error: Invalid Link!</h3>", status_code=400)
    return templates.TemplateResponse("verify.html", {"request": request, "link_id": link_id})

@app.post("/redirect/{link_id}")
async def handle_verification(request: Request, link_id: str):
    form_data = await request.form()
    turnstile_response = form_data.get("cf-turnstile-response")

    if not turnstile_response:
        return HTMLResponse(content="<h3>Security Verification Failed! Captcha missing.</h3>", status_code=400)

    verify_url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    payload = {
        "secret": CLOUDFLARE_SECRET_KEY,
        "response": turnstile_response
    }

    verify_request = requests.post(verify_url, data=payload)
    verify_result = verify_request.json()

    if not verify_result.get("success"):
        return HTMLResponse(content="<h3>Security Check Failed! Please try again.</h3>", status_code=403)

    original_url = decode_url(link_id)
    if original_url:
        return RedirectResponse(url=original_url, status_code=303)

    return HTMLResponse(content="<h3>Link Expired!</h3>", status_code=404)

# --- STARTUP ---

@app.on_event("startup")
def start_bot_thread():
    threading.Thread(target=lambda: bot.infinity_polling(timeout=20, long_polling_timeout=10), daemon=True).start()
    print("🤖 Telegram Bot Polling started in background thread successfully!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
