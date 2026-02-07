# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

- Character Compendium is a multi user D&D 5e character sheet web application built with Flask. 
- Letting the user customize things on the sheet is very important

## Running the Application

### Creating the venv (First run only)

```bash
python3 -m venv venv
```

### Starting the Application

```bash
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Runs on `http://localhost:5000` with debug mode enabled. On first launch, the app redirects to `/first-user` to create an admin account. The SQLite database (`compendium.db`) is auto-created on startup.

## Architecture

The app follows a two-file MVC pattern:

- **`app.py`** — Flask routes (controller). All routes use `@login_required` or `@admin_required` decorators for auth. Character routes verify user ownership before allowing access.
- **`models.py`** — SQLite database functions (model). Contains `init_db()` for schema creation, all CRUD operations, and the `STAT_OPTIONS` constant defining which stats items can modify.
- **`templates/`** — Jinja2 templates (view). `base.html` provides the layout; `sheet.html` (352 lines) is the most complex template containing the full character sheet with inventory.
- **`static/inventory.js`** — Vanilla JS handling the inventory modal (add/edit items with dynamic stat property rows).

## Database Schema

Four SQLite tables: `users`, `characters`, `inventory_items`, `item_properties`. Key relationships:
- Users own characters (user_id FK, cascade delete via app logic)
- Characters have inventory items (character_id FK, cascade delete)
- Items have properties defining stat bonuses (item_id FK, cascade delete)

The `item_properties` table links items to stat modifications (e.g., a sword adding +2 to Strength). Only equipped items' bonuses are applied when rendering the character sheet.

## Key Design Decisions

- **No test framework** — there are no tests or test infrastructure.
- **No build step** — plain CSS and vanilla JS, no bundling or transpilation.
- **Session-based auth** — Flask sessions store user_id, username, and is_admin. Passwords hashed with Werkzeug.
- **Hardcoded secret key** in `app.py` — known issue, noted in README.
- **Limited ability scores** — only Strength and Intelligence are implemented (not all six D&D stats).
- **Skills subset** — only Athletics, Arcana, History, Investigation, Nature, Religion are tracked.
- Fields should auto calculate wherever possible using D&D 5E rules, but the user should have a way to override all values
