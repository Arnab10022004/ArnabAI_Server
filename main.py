import sqlite3
import google.generativeai as genai
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime
import os

# --- CONFIGURATION ---
# Get Key from Hugging Face Secrets
API_KEY = os.getenv("GEMINI_API_KEY")

# Fallback for safety (prevents crash if key is missing)
if not API_KEY:
    print("WARNING: GEMINI_API_KEY not found. Please set it in Settings > Secrets.")
    # You can leave this empty or put a dummy value locally
    API_KEY = "dummy_key"

genai.configure(api_key=API_KEY)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# --- DATABASE SETUP ---
# CRITICAL CHANGE: Use /tmp/ for Hugging Face write permissions
DB_NAME = "/tmp/cloud_brain.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id TEXT PRIMARY KEY, name TEXT, joined_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, message TEXT, reply TEXT, timestamp TEXT)''')
    conn.commit()
    conn.close()

# Initialize DB on startup
init_db()

# --- DATA MODELS ---
class ChatRequest(BaseModel):
    user_id: str
    message: str

# --- API FOR ANDROID ---
@app.post("/api/ask")
async def ask_ai(request: ChatRequest):
    try:
        # 1. Ask Gemini
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(request.message)
        ai_reply = response.text

        # 2. Save to Database
        conn = get_db()
        c = conn.cursor()
        
        # Save User (Ignore if exists)
        c.execute("INSERT OR IGNORE INTO users (user_id, name, joined_at) VALUES (?, ?, ?)", 
                  (request.user_id, "Android User", str(datetime.now())))
        
        # Save Log
        c.execute("INSERT INTO logs (user_id, message, reply, timestamp) VALUES (?, ?, ?, ?)",
                  (request.user_id, request.message, ai_reply, str(datetime.now())))
        conn.commit()
        conn.close()

        return {"reply": ai_reply}
    except Exception as e:
        return {"reply": f"Server Error: {str(e)}"}

# --- DASHBOARD FOR ADMIN (You) ---
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    conn = get_db()
    # Get last 20 logs
    logs = conn.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 20").fetchall()
    conn.close()
    return templates.TemplateResponse("admin.html", {"request": request, "logs": logs})

# --- HEALTH CHECK (Optional) ---
@app.get("/")
def read_root():
    return {"status": "Online", "platform": "Hugging Face"}
