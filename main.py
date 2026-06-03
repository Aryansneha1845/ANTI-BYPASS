import os
import base64
import telebot
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uvicorn
import threading

# --- CONFIGURATION ---
BOT_TOKEN = "8679608771:AAFOxJ-SB-fbrpzbf1oHEBo5AXImgS65OI0"
CLOUDFLARE_SECRET_KEY = "0x4AAAAAADdlsEueqshqwNC30WwX3e-l3h4"
SERVER_URL = "https://anti-bypass-production.up.railway.app"
CHANNEL_ID = "@Antibypassbots" 

# Links
MAIN_CHANNEL = "https://t.me/c/3946440796/1"
BACKUP_CHANNEL = "https://t.me/c/3738247687/1"
BOT_LINK = "https://t.me/Antibypassbots"

bot = telebot.TeleBot(BOT_TOKEN)
app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# --- FUNCTIONS ---
def get_tiny_url(long_url):
    try:
        response = requests.get(f"https://tinyurl.com/api-create.php?url={long_url}")
        return response.text if response.status_code == 200 else long_url
    except: return long_url

def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except: return False

def encode_url(url: str) -> str:
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")

def decode_url(encoded_str: str) -> str:
    try:
        padding = 4 - (len(encoded_str) % 4)
        if padding < 4: encoded_str += "=" * padding
        return base64.urlsafe_b64decode(encoded_str.encode()).decode()
    except: return None

# --- TELEGRAM BOT LOGIC ---
@bot.message_handler(commands=['start'])
def start_command(message):
    bot.reply_to(message, "👋 **Welcome to Anti-Bypass!**\n\nApni link bhejo, main use bypass-proof bana dunga.", 
                 parse_mode="Markdown", disable_web_page_preview=True)

@bot.message_handler(func=lambda message: message.text.startswith(('http://', 'https://')))
def process_link(message):
    user_id = message.from_user.id
    
    # Subscription Check with Custom Layout
    if not is_subscribed(user_id):
        layout = (
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✨ **EXCLUSIVE CONTENT HUB** ✨\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔓 **Access Your Premium Files Here:**\n"
            f"🔗 [Main Channel]({MAIN_CHANNEL}) — *Latest Exclusive Content*\n\n"
            "🤖 **Official Bypass Bot:**\n"
            f"🔗 [Anti-Bypass Bot]({BOT_LINK}) — *Unlock Downloads Instantly*\n\n"
            "📦 **Backup & Premium Vault:**\n"
            f"🔗 [Backup Channel]({BACKUP_CHANNEL}) — *Restricted Premium Files*\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💡 *Tip: Link access karne mein dikkat ho, toh hamare Bot ka use karein.*\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        bot.reply_to(message, layout, parse_mode="Markdown", disable_web_page_preview=True)
        return

    # Link Processing
    original_url = message.text.strip()
    link_id = encode_url(original_url)
    long_protected_url = f"{SERVER_URL}/verify/{link_id}"
    short_link = get_tiny_url(long_protected_url)
    
    bot.reply_to(message, f"✅ **Link Secured!**\n\n🔗 **Your Link:** {short_link}", 
                 parse_mode="HTML", disable_web_page_preview=True)

# --- WEB SERVER LOGIC ---
@app.get("/")
def root_page():
    return HTMLResponse("<h1>Server Active</h1>")

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
        return RedirectResponse(url=url, status_code=303)
    return HTMLResponse("<h3>Verification Failed!</h3>", status_code=403)

@app.on_event("startup")
def start_bot_thread():
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
