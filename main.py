import sqlite3
import threading
import telebot
import shortuuid
import requests
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import uvicorn

# ⚠️ APNI DETIALS YAHAN BHARO
BOT_TOKEN = "8679608771:AAGePlI-DGzrRSyYylPCuEy34G9fhGra1WQ"
CLOUDFLARE_SECRET_KEY = "0x4AAAAAADdkLAf0CGVgqqyG5vBvDQSMzWM"
SERVER_URL = "https://anti-bypass.onrender.com"  # <-- Tera Render URL yahan aayega

bot = telebot.TeleBot(BOT_TOKEN)
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Database setup (Links ko save karne ke liye)
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS secure_links 
                      (id TEXT PRIMARY KEY, original_url TEXT, owner_id INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# --- TELEGRAM BOT LOGIC ---
@bot.message_handler(commands=['start'])
def start_command(message):
    bot.reply_to(message, "👋 **Welcome!** Apne shortener link bhejo, main use bypass-proof bana dunga.", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text.startswith(('http://', 'https://')))
def process_link(message):
    original_url = message.text.strip()
    link_id = shortuuid.uuid()[:8] # Unique ID generate ki
    owner_id = message.from_user.id
    
    # DB mein link save kiya
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO secure_links (id, original_url, owner_id) VALUES (?, ?, ?)", (link_id, original_url, owner_id))
    conn.commit()
    conn.close()
    
    protected_url = f"{SERVER_URL}/verify/{link_id}"
    bot.reply_to(message, f"🔒 **Link Protected!**\n\nShare this link: {protected_url}", parse_mode="Markdown")


# --- WEB SERVER LOGIC (Bypass Bot Blocker) ---
@app.get("/verify/{link_id}", response_class=HTMLResponse)
async def serve_verify_page(request: Request, link_id: str):
    return templates.TemplateResponse("verify.html", {"request": request, "link_id": link_id})

@app.post("/redirect/{link_id}")
async def handle_verification(request: Request, link_id: str):
    form_data = await request.form()
    turnstile_response = form_data.get("cf-turnstile-response")
    
    # Cloudflare se verify karna ki user human hai ya bot
    verify_url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    payload = {"secret": CLOUDFLARE_SECRET_KEY, "response": turnstile_response}
    verify_result = requests.post(verify_url, data=payload).json()
    
    if not verify_result.get("success"):
        return HTMLResponse(content="<h3>Security Check Failed! Dubara try karein.</h3>", status_code=403)
        
    # Agar human verified hai, toh database se original link nikal kar redirect karo
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT original_url FROM secure_links WHERE id=?", (link_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return RedirectResponse(url=row[0], status_code=303)
    return HTMLResponse(content="<h3>Link Not Found!</h3>", status_code=404)

if __name__ == "__main__":
    # Bot ko background thread mein start karo
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    # Web server ko main thread mein start karo
    uvicorn.run(app, host="0.0.0.0", port=8000)
