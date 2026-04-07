import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'database.sqlite')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recognition_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            confidence REAL,
            image_path TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enrolled_faces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            image_path TEXT NOT NULL,
            enrolled_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def log_event(name, confidence, image_path=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO recognition_events (name, confidence, image_path) VALUES (?, ?, ?)',
        (name, confidence, image_path)
    )
    conn.commit()
    conn.close()

def get_events(limit=50):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT name, timestamp, confidence, image_path FROM recognition_events ORDER BY id DESC LIMIT ?',
        (limit,)
    )
    events = [{'name': row[0], 'timestamp': row[1], 'confidence': row[2], 'image_path': row[3]} for row in cursor.fetchall()]
    conn.close()
    return events

def enroll_face(name, image_path):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            'INSERT INTO enrolled_faces (name, image_path) VALUES (?, ?)',
            (name, image_path)
        )
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False # Name probably already exists
    conn.close()
    return success

def get_enrolled_faces():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT name, image_path, enrolled_at FROM enrolled_faces ORDER BY id DESC')
    faces = [{'name': row[0], 'image_path': row[1], 'enrolled_at': row[2]} for row in cursor.fetchall()]
    conn.close()
    return faces

def delete_enrolled_face(name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM enrolled_faces WHERE name = ?', (name,))
    conn.commit()
    conn.close()
