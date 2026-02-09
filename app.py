from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import models
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'
ALLOW_BLANK_PASSWORDS = True

# Initialize database on first run
models.init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash('Admin access required')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def _verify_character_ownership(character_id):
    """Helper to verify the logged-in user owns this character. Returns character or None."""
    return models.get_character(character_id, session['user_id'])

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Check if this is first user setup
    if not models.users_exist():
        return redirect(url_for('first_user'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = models.verify_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user['is_admin'])
            session['dark_mode'] = bool(user.get('dark_mode', 0))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html', dev_mode=ALLOW_BLANK_PASSWORDS)

@app.route('/first-user', methods=['GET', 'POST'])
def first_user():
    # Redirect if users already exist
    if models.users_exist():
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match')
        elif not ALLOW_BLANK_PASSWORDS and len(password) < 6:
            flash('Password must be at least 6 characters')
        elif models.create_user(username, password, is_admin=True):
            flash('Admin account created! Please log in.')
            return redirect(url_for('login'))
        else:
            flash('Error creating account')
    
    return render_template('first_user.html', dev_mode=ALLOW_BLANK_PASSWORDS)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/profile/toggle-dark-mode', methods=['POST'])
@login_required
def toggle_dark_mode():
    new_mode = not session.get('dark_mode', False)
    models.update_user_dark_mode(session['user_id'], new_mode)
    session['dark_mode'] = new_mode
    return jsonify({'ok': True, 'dark_mode': new_mode})

@app.route('/admin')
@admin_required
def admin():
    users = models.get_all_users()
    return render_template('admin.html', users=users, dev_mode=ALLOW_BLANK_PASSWORDS)

@app.route('/admin/user/create', methods=['POST'])
@admin_required
def admin_create_user():
    username = request.form.get('username')
    password = request.form.get('password')
    is_admin = request.form.get('is_admin') == 'on'
    
    if not ALLOW_BLANK_PASSWORDS and len(password) < 6:
        flash('Password must be at least 6 characters')
    elif models.create_user(username, password, is_admin):
        flash(f'User {username} created successfully')
    else:
        flash('Username already exists')
    
    return redirect(url_for('admin'))

@app.route('/admin/user/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def admin_toggle_admin(user_id):
    if user_id == session['user_id']:
        flash('Cannot change your own admin status')
        return redirect(url_for('admin'))
    
    user = models.get_user_by_id(user_id)
    if user:
        new_status = not bool(user['is_admin'])
        models.update_user_admin_status(user_id, new_status)
        flash(f"Admin status updated for {user['username']}")
    
    return redirect(url_for('admin'))

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    if user_id == session['user_id']:
        flash('Cannot delete your own account')
        return redirect(url_for('admin'))
    
    user = models.get_user_by_id(user_id)
    if user:
        models.delete_user(user_id)
        flash(f"User {user['username']} deleted")
    
    return redirect(url_for('admin'))

@app.route('/dashboard')
@login_required
def dashboard():
    characters = models.get_characters_by_user(session['user_id'])
    return render_template('dashboard.html', characters=characters)

@app.route('/character/new', methods=['POST'])
@login_required
def new_character():
    character_id = models.create_character(session['user_id'])
    return redirect(url_for('view_character', character_id=character_id))

@app.route('/character/<int:character_id>')
@login_required
def view_character(character_id):
    character = _verify_character_ownership(character_id)
    if not character:
        flash('Character not found')
        return redirect(url_for('dashboard'))
    
    inventory = models.get_inventory(character_id)
    bonuses = models.get_equipped_bonuses(character_id)
    feature_bonuses = models.get_feature_bonuses(character_id)
    for stat, val in feature_bonuses.items():
        bonuses[stat] = bonuses.get(stat, 0) + val
    spell_bonuses = models.get_spell_bonuses(character_id)
    for stat, val in spell_bonuses.items():
        bonuses[stat] = bonuses.get(stat, 0) + val
    stat_options = models.STAT_OPTIONS
    features = models.get_features(character_id)
    spells = models.get_spells(character_id)
    currencies = models.get_currencies(character_id)

    return render_template('sheet.html', character=character, inventory=inventory,
                           bonuses=bonuses, stat_options=stat_options, features=features,
                           spells=spells, currencies=currencies)

@app.route('/character/<int:character_id>/update', methods=['POST'])
@login_required
def update_character(character_id):
    data = request.form.to_dict()

    # Convert numeric fields
    numeric_fields = [
        'level', 'hp_current', 'hp_max', 'ac', 'proficiency_bonus',
        'str_score', 'str_save_prof', 'int_score', 'int_save_prof',
        'athletics_prof', 'arcana_prof', 'history_prof', 'investigation_prof',
        'nature_prof', 'religion_prof', 'mana_current', 'mana_max',
        'spellcasting', 'death_save_success', 'death_save_fail',
        'initiative', 'speed', 'temp_hp'
    ]

    for field in numeric_fields:
        if field in data:
            try:
                data[field] = int(data[field]) if data[field] else 0
            except ValueError:
                data[field] = 0

    models.update_character(character_id, session['user_id'], data)
    flash('Character updated!')
    return redirect(url_for('view_character', character_id=character_id))

@app.route('/character/<int:character_id>/update_field', methods=['POST'])
@login_required
def update_field(character_id):
    data = request.get_json()
    if not data or 'field' not in data or 'value' not in data:
        return jsonify({'ok': False, 'error': 'Missing field or value'}), 400

    numeric_fields = [
        'level', 'hp_current', 'hp_max', 'ac', 'proficiency_bonus',
        'str_score', 'str_save_prof', 'int_score', 'int_save_prof',
        'athletics_prof', 'arcana_prof', 'history_prof', 'investigation_prof',
        'nature_prof', 'religion_prof', 'mana_current', 'mana_max',
        'spellcasting', 'death_save_success', 'death_save_fail',
        'initiative', 'speed', 'temp_hp'
    ]

    field = data['field']
    value = data['value']

    if field in numeric_fields:
        try:
            value = int(value) if value != '' else 0
        except ValueError:
            value = 0

    result = models.update_character(character_id, session['user_id'], {field: value})
    if result:
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'Update failed'}), 400

@app.route('/character/<int:character_id>/delete', methods=['POST'])
@login_required
def delete_character(character_id):
    models.delete_character(character_id, session['user_id'])
    flash('Character deleted')
    return redirect(url_for('dashboard'))


# --- Inventory Routes ---

@app.route('/character/<int:character_id>/inventory/add', methods=['POST'])
@login_required
def add_inventory_item(character_id):
    character = _verify_character_ownership(character_id)
    if not character:
        flash('Character not found')
        return redirect(url_for('dashboard'))
    
    name = request.form.get('item_name', '').strip()
    if not name:
        flash('Item name is required')
        return redirect(url_for('view_character', character_id=character_id))
    
    description = request.form.get('item_description', '').strip()
    location = request.form.get('item_location', '').strip()
    quantity_str = request.form.get('item_quantity', '').strip()
    quantity = int(quantity_str) if quantity_str else None
    
    # Parse properties from form
    properties = _parse_properties_from_form(request.form)
    props_enabled = 0 if request.form.get('props_disabled') else 1

    models.add_inventory_item(character_id, name, description, location, quantity, properties, props_enabled)
    flash(f'{name} added to inventory')
    return redirect(url_for('view_character', character_id=character_id))

@app.route('/character/<int:character_id>/inventory/<int:item_id>/update', methods=['POST'])
@login_required
def update_inventory_item(character_id, item_id):
    character = _verify_character_ownership(character_id)
    if not character:
        flash('Character not found')
        return redirect(url_for('dashboard'))
    
    name = request.form.get('item_name', '').strip()
    if not name:
        flash('Item name is required')
        return redirect(url_for('view_character', character_id=character_id))
    
    description = request.form.get('item_description', '').strip()
    location = request.form.get('item_location', '').strip()
    quantity_str = request.form.get('item_quantity', '').strip()
    quantity = int(quantity_str) if quantity_str else None
    
    properties = _parse_properties_from_form(request.form)
    
    models.update_inventory_item(item_id, character_id, name, description, location, quantity, properties)
    flash(f'{name} updated')
    return redirect(url_for('view_character', character_id=character_id))

@app.route('/character/<int:character_id>/inventory/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_inventory_item(character_id, item_id):
    character = _verify_character_ownership(character_id)
    if not character:
        flash('Character not found')
        return redirect(url_for('dashboard'))
    
    models.delete_inventory_item(item_id, character_id)
    flash('Item removed from inventory')
    return redirect(url_for('view_character', character_id=character_id))

@app.route('/character/<int:character_id>/inventory/<int:item_id>/toggle-equip', methods=['POST'])
@login_required
def toggle_equip_item(character_id, item_id):
    character = _verify_character_ownership(character_id)
    if not character:
        flash('Character not found')
        return redirect(url_for('dashboard'))
    
    new_status = models.toggle_equip_item(item_id, character_id)
    if new_status is not None:
        item = models.get_inventory_item(item_id, character_id)
        status_text = 'equipped' if new_status else 'unequipped'
        flash(f"{item['name']} {status_text}")
    
    return redirect(url_for('view_character', character_id=character_id))

@app.route('/character/<int:character_id>/inventory/<int:item_id>/json')
@login_required
def get_inventory_item_json(character_id, item_id):
    """Return item data as JSON for the edit modal."""
    character = _verify_character_ownership(character_id)
    if not character:
        return jsonify({'error': 'Not found'}), 404
    
    item = models.get_inventory_item(item_id, character_id)
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    return jsonify(item)


# --- Feature Routes ---

@app.route('/character/<int:character_id>/feature/add', methods=['POST'])
@login_required
def add_feature(character_id):
    character = _verify_character_ownership(character_id)
    if not character:
        flash('Character not found')
        return redirect(url_for('dashboard'))

    name = request.form.get('feature_name', '').strip()
    if not name:
        flash('Feature name is required')
        return redirect(url_for('view_character', character_id=character_id))

    description = request.form.get('feature_description', '').strip()
    source = request.form.get('feature_source', '').strip()
    if source == 'Other':
        source = request.form.get('feature_source_custom', '').strip()
    properties = _parse_properties_from_form(request.form)
    props_enabled = 0 if request.form.get('props_disabled') else 1
    models.add_feature(character_id, name, description, source, properties, props_enabled)
    flash(f'{name} added')
    return redirect(url_for('view_character', character_id=character_id))

@app.route('/character/<int:character_id>/feature/<int:feature_id>/update', methods=['POST'])
@login_required
def update_feature(character_id, feature_id):
    character = _verify_character_ownership(character_id)
    if not character:
        flash('Character not found')
        return redirect(url_for('dashboard'))

    name = request.form.get('feature_name', '').strip()
    if not name:
        flash('Feature name is required')
        return redirect(url_for('view_character', character_id=character_id))

    description = request.form.get('feature_description', '').strip()
    source = request.form.get('feature_source', '').strip()
    if source == 'Other':
        source = request.form.get('feature_source_custom', '').strip()
    properties = _parse_properties_from_form(request.form)
    models.update_feature(feature_id, character_id, name, description, source, properties)
    flash(f'{name} updated')
    return redirect(url_for('view_character', character_id=character_id))

@app.route('/character/<int:character_id>/feature/<int:feature_id>/delete', methods=['POST'])
@login_required
def delete_feature(character_id, feature_id):
    character = _verify_character_ownership(character_id)
    if not character:
        flash('Character not found')
        return redirect(url_for('dashboard'))

    models.delete_feature(feature_id, character_id)
    flash('Feature removed')
    return redirect(url_for('view_character', character_id=character_id))

@app.route('/character/<int:character_id>/feature/<int:feature_id>/json')
@login_required
def get_feature_json(character_id, feature_id):
    character = _verify_character_ownership(character_id)
    if not character:
        return jsonify({'error': 'Not found'}), 404

    feature = models.get_feature(feature_id, character_id)
    if not feature:
        return jsonify({'error': 'Feature not found'}), 404

    return jsonify(feature)


# --- Spell Routes ---

@app.route('/character/<int:character_id>/spell/add', methods=['POST'])
@login_required
def add_spell(character_id):
    character = _verify_character_ownership(character_id)
    if not character:
        flash('Character not found')
        return redirect(url_for('dashboard'))

    name = request.form.get('spell_name', '').strip()
    if not name:
        flash('Spell name is required')
        return redirect(url_for('view_character', character_id=character_id))

    try:
        level = max(0, min(9, int(request.form.get('spell_level', '0'))))
    except ValueError:
        level = 0

    description = request.form.get('spell_description', '').strip()
    properties = _parse_properties_from_form(request.form)
    props_enabled = 0 if request.form.get('props_disabled') else 1
    models.add_spell(character_id, name, level, description, properties, props_enabled)
    flash(f'{name} added to spells')
    return redirect(url_for('view_character', character_id=character_id))

@app.route('/character/<int:character_id>/spell/<int:spell_id>/update', methods=['POST'])
@login_required
def update_spell(character_id, spell_id):
    character = _verify_character_ownership(character_id)
    if not character:
        flash('Character not found')
        return redirect(url_for('dashboard'))

    name = request.form.get('spell_name', '').strip()
    if not name:
        flash('Spell name is required')
        return redirect(url_for('view_character', character_id=character_id))

    try:
        level = max(0, min(9, int(request.form.get('spell_level', '0'))))
    except ValueError:
        level = 0

    description = request.form.get('spell_description', '').strip()
    properties = _parse_properties_from_form(request.form)
    models.update_spell(spell_id, character_id, name, level, description, properties)
    flash(f'{name} updated')
    return redirect(url_for('view_character', character_id=character_id))

@app.route('/character/<int:character_id>/spell/<int:spell_id>/delete', methods=['POST'])
@login_required
def delete_spell(character_id, spell_id):
    character = _verify_character_ownership(character_id)
    if not character:
        flash('Character not found')
        return redirect(url_for('dashboard'))

    models.delete_spell(spell_id, character_id)
    flash('Spell removed')
    return redirect(url_for('view_character', character_id=character_id))

@app.route('/character/<int:character_id>/spell/<int:spell_id>/json')
@login_required
def get_spell_json(character_id, spell_id):
    character = _verify_character_ownership(character_id)
    if not character:
        return jsonify({'error': 'Not found'}), 404

    spell = models.get_spell(spell_id, character_id)
    if not spell:
        return jsonify({'error': 'Spell not found'}), 404

    return jsonify(spell)


# --- Currency Routes ---

@app.route('/character/<int:character_id>/currency/add', methods=['POST'])
@login_required
def add_currency(character_id):
    character = _verify_character_ownership(character_id)
    if not character:
        flash('Character not found')
        return redirect(url_for('dashboard'))

    name = request.form.get('currency_name', '').strip()
    abbreviation = request.form.get('currency_abbreviation', '').strip()
    if not name:
        flash('Currency name is required')
        return redirect(url_for('view_character', character_id=character_id))

    models.add_currency(character_id, name, abbreviation)
    flash(f'{name} added')
    return redirect(url_for('view_character', character_id=character_id))

@app.route('/character/<int:character_id>/currency/<int:currency_id>/delete', methods=['POST'])
@login_required
def delete_currency(character_id, currency_id):
    character = _verify_character_ownership(character_id)
    if not character:
        flash('Character not found')
        return redirect(url_for('dashboard'))

    models.delete_currency(currency_id, character_id)
    flash('Currency removed')
    return redirect(url_for('view_character', character_id=character_id))

@app.route('/character/<int:character_id>/currency/<int:currency_id>/adjust', methods=['POST'])
@login_required
def adjust_currency(character_id, currency_id):
    character = _verify_character_ownership(character_id)
    if not character:
        return jsonify({'ok': False, 'error': 'Not found'}), 404

    data = request.get_json()
    if not data or 'delta' not in data:
        return jsonify({'ok': False, 'error': 'Missing delta'}), 400

    try:
        delta = int(data['delta'])
    except (ValueError, TypeError):
        return jsonify({'ok': False, 'error': 'Invalid delta'}), 400

    new_amount = models.adjust_currency(currency_id, character_id, delta)
    if new_amount is None:
        return jsonify({'ok': False, 'error': 'Currency not found'}), 404

    return jsonify({'ok': True, 'amount': new_amount})


@app.route('/character/<int:character_id>/property/toggle', methods=['POST'])
@login_required
def toggle_property(character_id):
    character = _verify_character_ownership(character_id)
    if not character:
        return jsonify({'ok': False, 'error': 'Not found'}), 404

    data = request.get_json()
    if not data or 'table' not in data or 'prop_id' not in data:
        return jsonify({'ok': False, 'error': 'Missing table or prop_id'}), 400

    table = data['table']
    allowed_tables = ['item_properties', 'feature_properties', 'spell_properties']
    if table not in allowed_tables:
        return jsonify({'ok': False, 'error': 'Invalid table'}), 400

    prop_id = int(data['prop_id'])
    new_state = models.toggle_property(table, prop_id, character_id)
    if new_state is None:
        return jsonify({'ok': False, 'error': 'Property not found'}), 404

    return jsonify({'ok': True, 'enabled': new_state})


def _parse_properties_from_form(form):
    """Parse dynamic property fields from the form submission."""
    properties = []
    i = 0
    while True:
        stat_key = f'prop_stat_{i}'
        value_key = f'prop_value_{i}'
        if stat_key not in form:
            break
        stat = form.get(stat_key, '').strip()
        value_str = form.get(value_key, '').strip()
        if stat and value_str:
            try:
                value = int(value_str)
                properties.append({'stat_modified': stat, 'value': value})
            except ValueError:
                pass
        i += 1
    return properties


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
