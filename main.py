from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import datetime

app = FastAPI(title="Memory Agent API")

# Enable CORS so your frontend can talk to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize SQLite Database
DB_NAME = "memory.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            source_type TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

class QueryRequest(BaseModel):
    question: str

@app.post("/upload")
async def upload_memory(title: str = Form(...), content: str = Form(...), source_type: str = Form(...)):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().strftime("%B %d, %Y")
    cursor.execute(
        "INSERT INTO memories (title, content, source_type, created_at) VALUES (?, ?, ?, ?)",
        (title, content, source_type, timestamp)
    )
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Memory saved successfully!"}

@app.get("/memories")
def get_memories():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM memories ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/ask")
def ask_memory(payload: QueryRequest):
    question = payload.question.lower()
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM memories")
    memories = [dict(row) for row in cursor.fetchall()]
    conn.close()

    if not memories:
        return {
            "answer": "I couldn't find enough information in your connected memories to answer this.",
            "sources": [],
            "conflict": None
        }

    # Simple keyword/context lookup simulation for hackathon MVP
    matched_memories = []
    for m in memories:
        if any(word in m['content'].lower() or word in m['title'].lower() for word in question.split() if len(word) > 3):
            matched_memories.append(m)

    # Fallback if no specific keyword match
    if not matched_memories and memories:
        matched_memories = [memories[0]]

    # Check for conflicts (e.g. multiple dates found)
    conflict_msg = None
    if "deadline" in question or "date" in question or "meeting" in question:
        if len(memories) >= 2:
            conflict_msg = f"Note: Found multiple records. An older record mentioned '{memories[-1]['content']}'."

    primary_memory = matched_memories[0]
    
    return {
        "answer": f"Based on your records, {primary_memory['content']}",
        "sources": [f"{primary_memory['title']} ({primary_memory['source_type']} - {primary_memory['created_at']})"],
        "conflict": conflict_msg
    }