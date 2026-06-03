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
# Yahan https add karna zaroori hai
SERVER_URL = "https://anti-bypass-production.up.railway.app" 

bot = telebot.TeleBot(BOT_TOKEN)
app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# TinyURL Function
def get_tiny_url(long_url):
    try:
        response = requests.get(f"https://tinyurl.com/api-create.php?url={long_url}")
        return response.text if response.status_code == 200 else long_url
    except:
        return long_url

def encode_url(url: str) -> str:
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")

def decode_url(encoded_str: str) -> str:
    try:
        padding = 4 - (len(encoded_str) % 4)
        if padding < 4: encoded_str += "=" * padding
        return base64.urlsafe_b64decode(encoded_str.encode()).decode()
    except Exception:
        return None

# --- TELEGRAM BOT LOGIC ---
@bot.message_handler(commands=['start'])
def start_command(message):
    bot.reply_to(message, "👋 **Welcome!** Apni link bhejo, main use secure aur bypass-proof bana dunga.", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text.startswith(('http://', 'https://')))
def process_link(message):
    original_url = message.text.strip()
    link_id = encode_url(original_url)
    long_protected_url = f"{SERVER_URL}/verify/{link_id}"
    
    # TinyURL se link chota karo
    short_link = get_tiny_url(long_protected_url)
    
    response_text = (
        "✅ <b>Link Secured!</b>\n\n"
        f"🔗 <b>Click here:</b> <a href='{short_link}'>{short_link}</a>"
    )
    bot.reply_to(message, response_text, parse_mode="HTML")

# --- WEB SERVER LOGIC ---
@app.get("/")
def root_page():
    return HTMLResponse(content="""
    <html>
    <head><meta name="monetag" content="d14fb179012a6ae543ad87410c833c6e"></head>
    <body><h1>Server is running perfectly!</h1></body>
    </html>
    """)

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
        return HTMLResponse(content="<h3>Security Check Failed!</h3>", status_code=400)
    
    payload = {"secret": CLOUDFLARE_SECRET_KEY, "response": turnstile_response}
    verify_request = requests.post("https://challenges.cloudflare.com/turnstile/v0/siteverify", data=payload)
    
    if not verify_request.json().get("success"):
        return HTMLResponse(content="<h3>Verification Failed!</h3>", status_code=403)
        
    original_url = decode_url(link_id)
    return RedirectResponse(url=original_url, status_code=303) if original_url else HTMLResponse(content="Link Expired", status_code=404)

# --- STARTUP ---
@app.on_event("startup")
def start_bot_thread():
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
