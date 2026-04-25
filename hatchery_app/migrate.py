import sqlite3
import os
from datetime import datetime

DATABASE = 'hatchery.db'

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def migrate():
    db = get_db()
    cursor = db.cursor()

    print("Starting database migration...")

    # Add new columns to existing tables
    try:
        cursor.execute("ALTER TABLE batches ADD COLUMN health_status TEXT DEFAULT 'Healthy'")
        cursor.execute("ALTER TABLE batches ADD COLUMN health_notes TEXT")
        print("Added health_status and health_notes to batches table.")
    except sqlite3.OperationalError as e:
        print(f"Columns already exist or error: {e}")

    try:
        cursor.execute("ALTER TABLE incubation_batches ADD COLUMN daily_temp_log TEXT")
        cursor.execute("ALTER TABLE incubation_batches ADD COLUMN daily_humidity_log TEXT")
        cursor.execute("ALTER TABLE incubation_batches ADD COLUMN lockdown_date TEXT")
        print("Added daily_temp_log, daily_humidity_log, lockdown_date to incubation_batches table.")
    except sqlite3.OperationalError as e:
        print(f"Columns already exist or error: {e}")

    # Create new tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL,
            task_date TEXT NOT NULL,
            completed INTEGER NOT NULL DEFAULT 0
        )
    """)
    print("Created daily_tasks table (if not exists).")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS environment_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT NOT NULL UNIQUE,
            temperature REAL,
            humidity REAL,
            notes TEXT
        )
    """)
    print("Created environment_logs table (if not exists).")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL UNIQUE,
            quantity INTEGER NOT NULL DEFAULT 0,
            unit TEXT,
            low_threshold INTEGER NOT NULL DEFAULT 0
        )
    """)
    print("Created inventory table (if not exists).")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_date TEXT NOT NULL,
            batch_id INTEGER,
            quantity_sold INTEGER NOT NULL,
            price_per_bird REAL NOT NULL,
            notes TEXT,
            FOREIGN KEY (batch_id) REFERENCES batches (id)
        )
    """)
    print("Created sales table (if not exists).")

    db.commit()
    db.close()
    print("Database migration complete.")

if __name__ == '__main__':
    migrate()
