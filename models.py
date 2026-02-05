import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import json

DATABASE = 'compendium.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            level INTEGER DEFAULT 1,
            class TEXT,
            race TEXT,
            hp_current INTEGER DEFAULT 0,
            hp_max INTEGER DEFAULT 0,
            ac INTEGER DEFAULT 10,
            proficiency_bonus INTEGER DEFAULT 2,
            str_score INTEGER DEFAULT 10,
            str_save_prof INTEGER DEFAULT 0,
            int_score INTEGER DEFAULT 10,
            int_save_prof INTEGER DEFAULT 0,
            athletics_prof INTEGER DEFAULT 0,
            arcana_prof INTEGER DEFAULT 0,
            history_prof INTEGER DEFAULT 0,
            investigation_prof INTEGER DEFAULT 0,
            nature_prof INTEGER DEFAULT 0,
            religion_prof INTEGER DEFAULT 0,
            mana_current INTEGER DEFAULT 0,
            mana_max INTEGER DEFAULT 0,
            equipment TEXT,
            features TEXT,
            custom_abilities TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def create_user(username, password, is_admin=False):
    conn = get_db()
    password_hash = generate_password_hash(password)
    try:
        conn.execute('INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
                     (username, password_hash, 1 if is_admin else 0))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username, password):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    
    if user and check_password_hash(user['password_hash'], password):
        return dict(user)
    return None

def get_user_by_id(user_id):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None

def create_character(user_id):
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO characters (user_id, name) VALUES (?, ?)',
        (user_id, 'New Character')
    )
    character_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return character_id

def get_characters_by_user(user_id):
    conn = get_db()
    characters = conn.execute(
        'SELECT * FROM characters WHERE user_id = ? ORDER BY name',
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(char) for char in characters]

def get_character(character_id, user_id):
    conn = get_db()
    character = conn.execute(
        'SELECT * FROM characters WHERE id = ? AND user_id = ?',
        (character_id, user_id)
    ).fetchone()
    conn.close()
    return dict(character) if character else None

def update_character(character_id, user_id, data):
    conn = get_db()
    
    # Build update query dynamically based on provided data
    fields = []
    values = []
    
    allowed_fields = [
        'name', 'level', 'class', 'race', 'hp_current', 'hp_max', 'ac',
        'proficiency_bonus', 'str_score', 'str_save_prof', 'int_score',
        'int_save_prof', 'athletics_prof', 'arcana_prof', 'history_prof',
        'investigation_prof', 'nature_prof', 'religion_prof',
        'mana_current', 'mana_max', 'equipment', 'features', 'custom_abilities'
    ]
    
    for field in allowed_fields:
        if field in data:
            fields.append(f'{field} = ?')
            values.append(data[field])
    
    if not fields:
        return False
    
    values.extend([character_id, user_id])
    query = f"UPDATE characters SET {', '.join(fields)} WHERE id = ? AND user_id = ?"
    
    conn.execute(query, values)
    conn.commit()
    conn.close()
    return True

def delete_character(character_id, user_id):
    conn = get_db()
    conn.execute('DELETE FROM characters WHERE id = ? AND user_id = ?',
                 (character_id, user_id))
    conn.commit()
    conn.close()

def users_exist():
    conn = get_db()
    result = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()
    conn.close()
    return result['count'] > 0

def get_all_users():
    conn = get_db()
    users = conn.execute('SELECT id, username, is_admin FROM users ORDER BY username').fetchall()
    conn.close()
    return [dict(user) for user in users]

def update_user_admin_status(user_id, is_admin):
    conn = get_db()
    conn.execute('UPDATE users SET is_admin = ? WHERE id = ?', (1 if is_admin else 0, user_id))
    conn.commit()
    conn.close()

def delete_user(user_id):
    conn = get_db()
    # Delete user's characters first
    conn.execute('DELETE FROM characters WHERE user_id = ?', (user_id,))
    # Delete user
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
