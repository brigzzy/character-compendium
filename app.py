from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
import models

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

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
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

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
        elif len(password) < 6:
            flash('Password must be at least 6 characters')
        elif models.create_user(username, password, is_admin=True):
            flash('Admin account created! Please log in.')
            return redirect(url_for('login'))
        else:
            flash('Error creating account')
    
    return render_template('first_user.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
@admin_required
def admin():
    users = models.get_all_users()
    return render_template('admin.html', users=users)

@app.route('/admin/user/create', methods=['POST'])
@admin_required
def admin_create_user():
    username = request.form.get('username')
    password = request.form.get('password')
    is_admin = request.form.get('is_admin') == 'on'
    
    if len(password) < 6:
        flash('Password must be at least 6 characters')
    elif models.create_user(username, password, is_admin):
        flash(f'User {username} created successfully')
    else:
        flash('Username already exists')
    
    return redirect(url_for('admin'))

@app.route('/admin/user/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def admin_toggle_admin(user_id):
    # Prevent removing admin from self
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
    # Prevent deleting self
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
    character = models.get_character(character_id, session['user_id'])
    if not character:
        flash('Character not found')
        return redirect(url_for('dashboard'))
    return render_template('sheet.html', character=character)

@app.route('/character/<int:character_id>/update', methods=['POST'])
@login_required
def update_character(character_id):
    data = request.form.to_dict()
    
    # Convert numeric fields
    numeric_fields = [
        'level', 'hp_current', 'hp_max', 'ac', 'proficiency_bonus',
        'str_score', 'str_save_prof', 'int_score', 'int_save_prof',
        'athletics_prof', 'arcana_prof', 'history_prof', 'investigation_prof',
        'nature_prof', 'religion_prof', 'mana_current', 'mana_max'
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

@app.route('/character/<int:character_id>/delete', methods=['POST'])
@login_required
def delete_character(character_id):
    models.delete_character(character_id, session['user_id'])
    flash('Character deleted')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
