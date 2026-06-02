import os
import base64
import telebot
import requests
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uvicorn
import threading

# --- CONFIGURATION (In teeno ko sahi se bhar do) ---
BOT_TOKEN = "8679608771:AAFOxJ-SB-fbrpzbf1oHEBo5AXImgS65OI0"
CLOUDFLARE_SECRET_KEY = "0x4AAAAAADdlsEueqshqwNC30WwX3e-l3h4"
SERVER_URL = "https://anti-bypass.onrender.com"  # Aakhri mein / mat lagana

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

# --- TELEGRAM BOT LOGIC ---
@bot.message_handler(commands=['start'])
def start_command(message):
    bot.reply_to(message, "👋 **Welcome!** Apne shortener link bhejo, main use bypass-proof bana dunga.", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text.startswith(('http://', 'https://')))
def process_link(message):
    original_url = message.text.strip()
    link_id = encode_url(original_url)
    protected_url = f"{SERVER_URL}/verify/{link_id}"
    
    response_text = (
        "🔒 <b>Link Protected Successfully!</b>\n\n"
        f"🔗 <b>Your Secure Link:</b> {protected_url}"
    )
    bot.reply_to(message, response_text, parse_mode="HTML")

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

# --- WEB SERVER & BOT STARTUP ---

# Webhook bypass karne ke liye aur bot ko background mein chalane ka sabse stable tarika
# --- WEB SERVER & BOT STARTUP ---

@app.on_event("startup")
def start_bot_thread():
    # Logging mita di jo crash kar rahi thi
    threading.Thread(target=lambda: bot.infinity_polling(timeout=20, long_polling_timeout=10), daemon=True).start()
    print("🤖 Telegram Bot Polling started in background thread successfully!")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
