import sqlite3
import time

DB_PATH = "leetcode.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS submissions (
        id TEXT PRIMARY KEY,
        title_slug TEXT,
        title TEXT,
        lang TEXT,
        runtime TEXT,
        memory TEXT,
        timestamp INTEGER,
        code TEXT,
        runtime_percentile REAL,
        memory_percentile REAL
    );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS problems (
           title_slug TEXT PRIMARY KEY,
           completed TEXT
        )
    """)

    cur.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('full_sync_done', 'false')")
    cur.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('total_unique_solved', '0')")

    conn.commit()
    conn.close()



def save_submission_with_retry(sub, retries=5):
    for attempt in range(1, retries + 1):
        try:
            save_submission(sub)
            return
        except sqlite3.OperationalError as e:
            print(f"DB write attempt {attempt} failed: {e}")
            time.sleep(0.5)
    print("DB write failed permanently.")



def save_submission(sub):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO submissions (
            id, title_slug, title, lang, runtime, memory,
            timestamp, code, runtime_percentile, memory_percentile
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sub["id"],
        sub["title_slug"],
        toTitle(sub["title_slug"]),
        sub["lang"],
        sub["runtime"],
        sub["memory"],
        sub["timestamp"],
        sub["code"],
        sub["runtime_percentile"],
        sub["memory_percentile"]
    ))

    conn.commit()
    conn.close()

def save_problem(slug, completed):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO problems (title_slug, completed)
        VALUES (?, ?)
    """, (slug, completed))
    conn.commit()
    conn.close()

def get_meta(key):
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None

def set_meta(key, value):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("REPLACE INTO meta (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_known_slugs():
    conn = get_conn()
    cur = conn.cursor()
    rows = cur.execute("SELECT DISTINCT title_slug FROM problems WHERE completed = 'true'").fetchall()
    conn.close()
    return {r["title_slug"] for r in rows}

def toTitle(slug):
    words = slug.split("-")
    return " ".join(word.capitalize() for word in words)
