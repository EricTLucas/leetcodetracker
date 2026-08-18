from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3

app = FastAPI()

# Allow your HTML/JS site to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # you can restrict this later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "../leetcode.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/submissions/recent")
def recent_submissions(limit: int = 20):
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT id, title_slug, title, lang, runtime, memory,
               runtime_percentile, memory_percentile, timestamp
        FROM submissions
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [dict(row) for row in rows]

@app.get("/submissions/{submission_id}")
def submission_detail(submission_id: int):
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute("""
        SELECT *
        FROM submissions
        WHERE id = ?
    """, (submission_id,)).fetchone()
    return dict(row) if row else {"error": "not found"}

@app.get("/submissions/by-problem/{slug}")
def submissions_by_problem(slug: str):
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT *
        FROM submissions
        WHERE title_slug = ?
        ORDER BY timestamp DESC
    """, (slug,)).fetchall()
    return [dict(row) for row in rows]

@app.get("/meta/{key}")
def get_meta(key: str):
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return {"key": key, "value": row["value"] if row else None}

@app.get("/problems")
def list_problems():
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM problems").fetchall()
    return [dict(row) for row in rows]

@app.get("/submissions/by-problem/{slug}")
def submissions_by_problem(slug: str):
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT *
        FROM submissions
        WHERE title_slug = ?
        ORDER BY timestamp DESC
    """, (slug,)).fetchall()
    return [dict(row) for row in rows]