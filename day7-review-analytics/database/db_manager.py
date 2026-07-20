import sqlite3
from datetime import datetime
import config

def init_db():
    conn = sqlite3.connect(config.DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS summaries
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  filename TEXT,
                  summary TEXT,
                  rating INTEGER,
                  category TEXT,
                  created_at DATETIME)''')
    conn.commit()
    conn.close()

def save_summary(filename, summary, rating, category):
    conn = sqlite3.connect(config.DB_NAME)
    c = conn.cursor()
    c.execute("""INSERT INTO summaries (filename, summary, rating, category, created_at)
                 VALUES (?, ?, ?, ?, ?)""",
              (filename, summary, rating, category, datetime.now()))
    conn.commit()
    conn.close()

def get_summaries_by_category(category):
    conn = sqlite3.connect(config.DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, filename, created_at FROM summaries WHERE category = ? ORDER BY created_at DESC", (category,))
    data = c.fetchall()
    conn.close()
    return data

def get_summary_by_id(summary_id):
    conn = sqlite3.connect(config.DB_NAME)
    c = conn.cursor()
    c.execute("SELECT filename, summary, rating, category, created_at FROM summaries WHERE id = ?", (summary_id,))
    data = c.fetchone()
    conn.close()
    return data
