# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Spenditure** is a Flask-based personal expense tracker app built as a step-by-step learning project. The app is being built incrementally — many routes and database functions are stubs that students implement step-by-step. The database layer (`database/db.py`) is intentionally left empty for Step 1.

## Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Run the app (debug mode, port 5001)
python app.py

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run a single test file
pytest tests/test_db.py

# Run a single test
pytest tests/test_db.py::test_function_name
```

The app runs at `http://localhost:5001`.

## Architecture

**Single-file Flask app** — all routes are in `app.py`. No blueprints.

**Templates** — all extend `base.html`, which provides the navbar, footer, and asset includes (Google Fonts: DM Serif Display + DM Sans; single CSS file `static/css/style.css`; `static/js/main.js`).

**CSS** — single file `static/css/style.css` using CSS custom properties defined in `:root`. Design tokens: `--accent` (dark green `#1a472a`), `--paper` (warm off-white `#f7f6f3`), `--font-display` / `--font-body`.

## Incremental Build Steps

Routes in `app.py` are marked with the step they belong to (Steps 1–9). Placeholder routes return plain strings like `"Logout — coming in Step 3"`. When implementing a step, replace the stub return with real logic. Do not delete stub routes — replace them.

## Conventions

- Templates use `{% extends "base.html" %}` with `{% block title %}`, `{% block content %}`, and optional `{% block scripts %}` / `{% block head %}`.
- Page-specific JS goes in `{% block scripts %}` inside the template, not in `main.js`.
- Form actions use hardcoded paths (`action="/register"`) rather than `url_for` for simplicity.
- Currency is displayed in Indian Rupees (₹).
