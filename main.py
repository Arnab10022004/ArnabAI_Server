import sqlite3
import google.generativeai as genai
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime
import os

# CONFIGURATION
# We get the key from the Cloud Environment for security
API_KEY = os.getenv("GEMINI_API_KEY") 
if not API_KEY:
    # Fallback for local testing only
    API_KEY = "PASTE_YOUR_KEY_HERE_FOR_LOCAL_TESTING" 

genai.configure(api_key=API_KEY)

app = FastAPI()
templates = Jinja2Templates(directory="templates")
DB_NAME = "cloud_brain.db"

# DATABASE SETUP
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

init_db()

# DATA MODEL
class ChatRequest(BaseModel):
    user_id: str
    message: str

# API FOR ANDROID
@app.post("/api/ask")
async def ask_ai(request: ChatRequest):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(request.message)
        ai_reply = response.text

        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, name, joined_at) VALUES (?, ?, ?)", 
                  (request.user_id, "Android User", str(datetime.now())))
        c.execute("INSERT INTO logs (user_id, message, reply, timestamp) VALUES (?, ?, ?, ?)",
                  (request.user_id, request.message, ai_reply, str(datetime.now())))
        conn.commit()
        conn.close()

        return {"reply": ai_reply}
    except Exception as e:
        return {"reply": f"Error: {str(e)}"}

# DASHBOARD FOR LAPTOP
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    conn = get_db()
    logs = conn.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 20").fetchall()
    conn.close()
    return templates.TemplateResponse("admin.html", {"request": request, "logs": logs})