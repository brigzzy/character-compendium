# Character Compendium

A D&D 5e character sheet web application with custom modifications for mana-based spellcasting and custom abilities.

## Features

- User authentication (multi-user support)
- Create and manage multiple characters
- D&D 5e-style character sheets
- Custom skills and abilities support
- Mana system instead of spell slots
- Persistent data storage with SQLite

## Setup

1. Install Python 3.8 or higher

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Open your browser to `http://localhost:5000`

5. Register a new account and start creating characters!

## Usage

- **Register/Login**: Create an account or log in to access your characters
- **Dashboard**: View all your characters and create new ones
- **Character Sheet**: Click on a character to view/edit their sheet
- **Save Changes**: Click "Save Changes" at the bottom of the character sheet

## Database

The app uses SQLite and stores data in `compendium.db`. This file is created automatically on first run.

## Security Note

Change the `secret_key` in `app.py` before deploying to production!

## Future Features

- Auto-save (without clicking Save)
- Additional ability scores
- Spell management
- Combat tracking
- Character export/import
