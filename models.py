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

    conn.execute('''
        CREATE TABLE IF NOT EXISTS inventory_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            location TEXT DEFAULT '',
            quantity INTEGER DEFAULT NULL,
            equipped INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (character_id) REFERENCES characters (id) ON DELETE CASCADE
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS item_properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            stat_modified TEXT NOT NULL,
            value INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (item_id) REFERENCES inventory_items (id) ON DELETE CASCADE
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS features (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            source TEXT DEFAULT '',
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (character_id) REFERENCES characters (id) ON DELETE CASCADE
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS feature_properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feature_id INTEGER NOT NULL,
            stat_modified TEXT NOT NULL,
            value INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (feature_id) REFERENCES features (id) ON DELETE CASCADE
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


# --- Inventory Functions ---

# The stat options available for item properties
STAT_OPTIONS = [
    ('ac', 'Armor Class'),
    ('hp_max', 'Max HP'),
    ('mana_max', 'Max Mana'),
    ('str_score', 'Strength Score'),
    ('int_score', 'Intelligence Score'),
    ('proficiency_bonus', 'Proficiency Bonus'),
    ('spell_attack', 'Spell Attack'),
    ('str_save', 'Strength Save'),
    ('int_save', 'Intelligence Save'),
    ('athletics', 'Athletics'),
    ('arcana', 'Arcana'),
    ('history', 'History'),
    ('investigation', 'Investigation'),
    ('nature', 'Nature'),
    ('religion', 'Religion'),
]

def get_inventory(character_id):
    """Get all inventory items with their properties for a character."""
    conn = get_db()
    items = conn.execute(
        'SELECT * FROM inventory_items WHERE character_id = ? ORDER BY equipped DESC, sort_order, name',
        (character_id,)
    ).fetchall()
    
    result = []
    for item in items:
        item_dict = dict(item)
        props = conn.execute(
            'SELECT * FROM item_properties WHERE item_id = ? ORDER BY id',
            (item_dict['id'],)
        ).fetchall()
        item_dict['properties'] = [dict(p) for p in props]
        result.append(item_dict)
    
    conn.close()
    return result

def get_inventory_item(item_id, character_id):
    """Get a single inventory item with properties."""
    conn = get_db()
    item = conn.execute(
        'SELECT * FROM inventory_items WHERE id = ? AND character_id = ?',
        (item_id, character_id)
    ).fetchone()
    
    if not item:
        conn.close()
        return None
    
    item_dict = dict(item)
    props = conn.execute(
        'SELECT * FROM item_properties WHERE item_id = ? ORDER BY id',
        (item_dict['id'],)
    ).fetchall()
    item_dict['properties'] = [dict(p) for p in props]
    
    conn.close()
    return item_dict

def add_inventory_item(character_id, name, description, location, quantity, properties):
    """Add a new inventory item with properties. Returns the new item id."""
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO inventory_items (character_id, name, description, location, quantity) VALUES (?, ?, ?, ?, ?)',
        (character_id, name, description, location, quantity)
    )
    item_id = cursor.lastrowid
    
    for prop in properties:
        if prop.get('stat_modified') and prop.get('value') is not None:
            conn.execute(
                'INSERT INTO item_properties (item_id, stat_modified, value) VALUES (?, ?, ?)',
                (item_id, prop['stat_modified'], prop['value'])
            )
    
    conn.commit()
    conn.close()
    return item_id

def update_inventory_item(item_id, character_id, name, description, location, quantity, properties):
    """Update an existing inventory item and its properties."""
    conn = get_db()
    
    # Verify item belongs to this character
    item = conn.execute(
        'SELECT id FROM inventory_items WHERE id = ? AND character_id = ?',
        (item_id, character_id)
    ).fetchone()
    
    if not item:
        conn.close()
        return False
    
    conn.execute(
        'UPDATE inventory_items SET name = ?, description = ?, location = ?, quantity = ? WHERE id = ?',
        (name, description, location, quantity, item_id)
    )
    
    # Replace all properties
    conn.execute('DELETE FROM item_properties WHERE item_id = ?', (item_id,))
    for prop in properties:
        if prop.get('stat_modified') and prop.get('value') is not None:
            conn.execute(
                'INSERT INTO item_properties (item_id, stat_modified, value) VALUES (?, ?, ?)',
                (item_id, prop['stat_modified'], prop['value'])
            )
    
    conn.commit()
    conn.close()
    return True

def delete_inventory_item(item_id, character_id):
    """Delete an inventory item and its properties."""
    conn = get_db()
    conn.execute(
        'DELETE FROM inventory_items WHERE id = ? AND character_id = ?',
        (item_id, character_id)
    )
    conn.commit()
    conn.close()

def toggle_equip_item(item_id, character_id):
    """Toggle the equipped status of an item. Returns new status."""
    conn = get_db()
    item = conn.execute(
        'SELECT equipped FROM inventory_items WHERE id = ? AND character_id = ?',
        (item_id, character_id)
    ).fetchone()
    
    if not item:
        conn.close()
        return None
    
    new_status = 0 if item['equipped'] else 1
    conn.execute(
        'UPDATE inventory_items SET equipped = ? WHERE id = ?',
        (new_status, item_id)
    )
    conn.commit()
    conn.close()
    return new_status

def get_equipped_bonuses(character_id):
    """Calculate total stat bonuses from all equipped items."""
    conn = get_db()
    rows = conn.execute('''
        SELECT ip.stat_modified, SUM(ip.value) as total
        FROM item_properties ip
        JOIN inventory_items ii ON ip.item_id = ii.id
        WHERE ii.character_id = ? AND ii.equipped = 1
        GROUP BY ip.stat_modified
    ''', (character_id,)).fetchall()
    conn.close()
    
    bonuses = {}
    for row in rows:
        bonuses[row['stat_modified']] = row['total']
    return bonuses


# --- Features Functions ---

def get_features(character_id):
    """Get all features with their properties for a character."""
    conn = get_db()
    features = conn.execute(
        'SELECT * FROM features WHERE character_id = ? ORDER BY sort_order, name',
        (character_id,)
    ).fetchall()

    result = []
    for feature in features:
        f_dict = dict(feature)
        props = conn.execute(
            'SELECT * FROM feature_properties WHERE feature_id = ? ORDER BY id',
            (f_dict['id'],)
        ).fetchall()
        f_dict['properties'] = [dict(p) for p in props]
        result.append(f_dict)

    conn.close()
    return result

def get_feature(feature_id, character_id):
    """Get a single feature with properties and ownership check."""
    conn = get_db()
    feature = conn.execute(
        'SELECT * FROM features WHERE id = ? AND character_id = ?',
        (feature_id, character_id)
    ).fetchone()

    if not feature:
        conn.close()
        return None

    f_dict = dict(feature)
    props = conn.execute(
        'SELECT * FROM feature_properties WHERE feature_id = ? ORDER BY id',
        (f_dict['id'],)
    ).fetchall()
    f_dict['properties'] = [dict(p) for p in props]

    conn.close()
    return f_dict

def add_feature(character_id, name, description, source, properties):
    """Add a new feature with properties. Returns the new feature id."""
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO features (character_id, name, description, source) VALUES (?, ?, ?, ?)',
        (character_id, name, description, source)
    )
    feature_id = cursor.lastrowid

    for prop in properties:
        if prop.get('stat_modified') and prop.get('value') is not None:
            conn.execute(
                'INSERT INTO feature_properties (feature_id, stat_modified, value) VALUES (?, ?, ?)',
                (feature_id, prop['stat_modified'], prop['value'])
            )

    conn.commit()
    conn.close()
    return feature_id

def update_feature(feature_id, character_id, name, description, source, properties):
    """Update an existing feature and its properties."""
    conn = get_db()
    item = conn.execute(
        'SELECT id FROM features WHERE id = ? AND character_id = ?',
        (feature_id, character_id)
    ).fetchone()
    if not item:
        conn.close()
        return False

    conn.execute(
        'UPDATE features SET name = ?, description = ?, source = ? WHERE id = ?',
        (name, description, source, feature_id)
    )

    # Replace all properties
    conn.execute('DELETE FROM feature_properties WHERE feature_id = ?', (feature_id,))
    for prop in properties:
        if prop.get('stat_modified') and prop.get('value') is not None:
            conn.execute(
                'INSERT INTO feature_properties (feature_id, stat_modified, value) VALUES (?, ?, ?)',
                (feature_id, prop['stat_modified'], prop['value'])
            )

    conn.commit()
    conn.close()
    return True

def delete_feature(feature_id, character_id):
    """Delete a feature and its properties."""
    conn = get_db()
    conn.execute(
        'DELETE FROM features WHERE id = ? AND character_id = ?',
        (feature_id, character_id)
    )
    conn.commit()
    conn.close()

def get_feature_bonuses(character_id):
    """Calculate total stat bonuses from all features."""
    conn = get_db()
    rows = conn.execute('''
        SELECT fp.stat_modified, SUM(fp.value) as total
        FROM feature_properties fp
        JOIN features f ON fp.feature_id = f.id
        WHERE f.character_id = ?
        GROUP BY fp.stat_modified
    ''', (character_id,)).fetchall()
    conn.close()

    bonuses = {}
    for row in rows:
        bonuses[row['stat_modified']] = row['total']
    return bonuses
