import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('aquariums.db')
    cursor = conn.cursor()

    # Table des aquariums
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS aquariums (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            volume REAL NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Table des changements d'eau
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS water_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aquarium_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            volume_changed REAL NOT NULL,
            notes TEXT,
            FOREIGN KEY (aquarium_id) REFERENCES aquariums (id)
        )
    ''')

    # Table de la population
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS population (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aquarium_id INTEGER NOT NULL,
            species TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            notes TEXT,
            FOREIGN KEY (aquarium_id) REFERENCES aquariums (id)
        )
    ''')

    # Table des photos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aquarium_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            upload_date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (aquarium_id) REFERENCES aquariums (id)
        )
    ''')

    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect('aquariums.db')
    conn.row_factory = sqlite3.Row
    return conn
