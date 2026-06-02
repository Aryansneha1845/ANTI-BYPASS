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

# --- CONFIGURATION ---
BOT_TOKEN = "8679608771:AAGePlI-DGzrRSyYylPCuEy34G9fhGra1WQ"
CLOUDFLARE_SECRET_KEY = "Y0x4AAAAAADdkLAf0CGVgqqyG5vBvDQSMzWM"
SERVER_URL = "https://anti-bypass.onrender.com"  # Apna Render URL (Aakhri mein / mat lagana)

bot = telebot.TeleBot(BOT_TOKEN)
app = FastAPI()

# 🔥 PATH FIX: Yeh Render ko hamesha templates folder ka sahi rasta dikhayega
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Safe Base64 Encoding
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
    bot.reply_to(message, message.chat.id, text=response_text, parse_mode="HTML")

# --- WEB SERVER LOGIC ---

# Render health check ke liye status page
@app.get("/")
async def root_page():
    return {"status": "Server is running perfectly!"}

@app.get("/verify/{link_id}", response_class=HTMLResponse)
async def serve_verify_page(request: Request, link_id: str):
    original_url = decode_url(link_id)
    if not original_url:
        return HTMLResponse(content="<h3>Error: Invalid or Expired Link!</h3>", status_code=400)
    
    try:
        return templates.TemplateResponse("verify.html", {"request": request, "link_id": link_id})
    except Exception as e:
        return HTMLResponse(content=f"<h3>Template Error: templates/verify.html file nahi mili!</h3><p>{str(e)}</p>", status_code=500)

@app.post("/redirect/{link_id}")
async def handle_verification(request: Request, link_id: str):
    form_data = await request.form()
    turnstile_response = form_data.get("cf-turnstile-response")
    
    if not turnstile_response:
        return HTMLResponse(content="<h3>Security Verification Failed! Captcha missing.</h3>", status_code=400)
    
    # Cloudflare Turnstile Verification
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    threading.Thread(target=lambda: bot.infinity_polling(timeout=20, long_polling_timeout=10), daemon=True).start()
    uvicorn.run("main:app", host="0.0.0.0", port=port)
