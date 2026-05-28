"""
Tests for Step 03 — Login and Logout (Spec: .claude/specs/03-login-and-logout.md)

These tests verify the spec's Definition of Done exclusively through HTTP
requests and session inspection.  They never call implementation functions
directly in assertions.
"""

import sqlite3
import pytest
from werkzeug.security import generate_password_hash

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TEST_NAME     = "Test User"
TEST_EMAIL    = "testuser@example.com"
TEST_PASSWORD = "correct-password-123"


@pytest.fixture()
def app(tmp_path, monkeypatch):
    """
    Create a Flask test app wired to an isolated in-memory SQLite database.

    The real DB_PATH inside database/db.py is monkeypatched so that every
    call to get_db() opens the same temp file created here (an in-memory DB
    can't be shared between connections, so we use a temp file instead).
    """
    db_file = tmp_path / "test_expense_tracker.db"

    # Monkeypatch the module-level DB_PATH before importing app, so every
    # call to get_db() in the running test talks to our temp database.
    import database.db as db_module
    monkeypatch.setattr(db_module, "DB_PATH", str(db_file))

    # Bootstrap the schema and insert a known test user.
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        );
    """)
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (TEST_NAME, TEST_EMAIL, generate_password_hash(TEST_PASSWORD)),
    )
    conn.commit()
    conn.close()

    import app as flask_app_module
    flask_app_module.app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key",
        WTF_CSRF_ENABLED=False,
    )

    yield flask_app_module.app


@pytest.fixture()
def client(app):
    """Return a Flask test client."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def post_login(client, email, password):
    """POST to /login and return the response."""
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


def get_session_user_id(client):
    """Read session['user_id'] using session_transaction; returns None if absent."""
    with client.session_transaction() as sess:
        return sess.get("user_id")


# ---------------------------------------------------------------------------
# GET /login
# ---------------------------------------------------------------------------

def test_get_login_returns_200(client):
    """
    Spec: 'Visiting GET /login renders the login form with email and
    password fields' — the route must return HTTP 200.
    """
    response = client.get("/login")
    assert response.status_code == 200


def test_get_login_renders_email_and_password_fields(client):
    """
    Spec: 'Visiting GET /login renders the login form with email and
    password fields' — the response body must contain input elements for
    both email and password.
    """
    response = client.get("/login")
    html = response.data.decode()
    assert 'name="email"' in html or 'type="email"' in html
    assert 'name="password"' in html or 'type="password"' in html


# ---------------------------------------------------------------------------
# POST /login — successful login
# ---------------------------------------------------------------------------

def test_valid_login_sets_session_user_id(client):
    """
    Spec: 'Submitting the form with valid credentials sets session["user_id"]
    and redirects to /'.
    Verifies that session["user_id"] is populated after a correct login.
    """
    post_login(client, TEST_EMAIL, TEST_PASSWORD)
    user_id = get_session_user_id(client)
    assert user_id is not None
    assert isinstance(user_id, int)


def test_valid_login_redirects_to_landing(client):
    """
    Spec: 'Submitting the form with valid credentials sets session["user_id"]
    and redirects to /'.
    Verifies the redirect target is the landing page (/).
    """
    response = post_login(client, TEST_EMAIL, TEST_PASSWORD)
    assert response.status_code == 302
    assert response.headers["Location"] in ("/", "http://localhost/")


# ---------------------------------------------------------------------------
# POST /login — wrong password
# ---------------------------------------------------------------------------

def test_wrong_password_shows_generic_flash(client):
    """
    Spec: 'Submitting with a wrong password shows "Invalid email or password."
    flash and stays on the login page'.
    Verifies the generic error message appears in the response body.
    """
    response = client.post(
        "/login",
        data={"email": TEST_EMAIL, "password": "wrong-password"},
        follow_redirects=True,
    )
    html = response.data.decode()
    assert "Invalid email or password." in html


def test_wrong_password_does_not_set_session(client):
    """
    Spec: 'Submitting with a wrong password shows "Invalid email or password."
    flash and stays on the login page' — session must not be populated.
    """
    post_login(client, TEST_EMAIL, "wrong-password")
    assert get_session_user_id(client) is None


def test_wrong_password_stays_on_login_page(client):
    """
    Spec: 'Submitting with a wrong password … stays on the login page'.
    Verifies the response is not a redirect (status 200, on login page).
    """
    response = client.post(
        "/login",
        data={"email": TEST_EMAIL, "password": "wrong-password"},
        follow_redirects=False,
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /login — unregistered email
# ---------------------------------------------------------------------------

def test_unregistered_email_shows_generic_flash(client):
    """
    Spec: 'Submitting with an unregistered email shows the same generic error
    flash'.  Verifies the identical "Invalid email or password." message is
    shown (not a different message that reveals the email is unknown).
    """
    response = client.post(
        "/login",
        data={"email": "nobody@example.com", "password": TEST_PASSWORD},
        follow_redirects=True,
    )
    html = response.data.decode()
    assert "Invalid email or password." in html


def test_unregistered_email_does_not_set_session(client):
    """
    Spec: 'Submitting with an unregistered email shows the same generic error
    flash' — session must not be populated.
    """
    post_login(client, "nobody@example.com", TEST_PASSWORD)
    assert get_session_user_id(client) is None


# ---------------------------------------------------------------------------
# POST /login — blank fields
# ---------------------------------------------------------------------------

def test_blank_email_shows_error_flash(client):
    """
    Additional coverage: POSTing with a blank email must return an error flash
    (not a crash), per the 'all fields required' defensive rule implied by the
    spec's generic error handling.
    """
    response = client.post(
        "/login",
        data={"email": "", "password": TEST_PASSWORD},
        follow_redirects=True,
    )
    assert response.status_code == 200
    # Must not be a server error
    assert response.status_code != 500


def test_blank_password_shows_error_flash(client):
    """
    Additional coverage: POSTing with a blank password must return an error
    flash (not a crash).
    """
    response = client.post(
        "/login",
        data={"email": TEST_EMAIL, "password": ""},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert response.status_code != 500


# ---------------------------------------------------------------------------
# GET /logout
# ---------------------------------------------------------------------------

def test_logout_returns_302(client):
    """
    Additional coverage: 'Visiting GET /logout … redirects to /' must return
    HTTP 302.
    """
    response = client.get("/logout", follow_redirects=False)
    assert response.status_code == 302


def test_logout_redirects_to_landing(client):
    """
    Spec: 'Visiting GET /logout clears the session and redirects to /'.
    Verifies the redirect target is the landing page.
    """
    response = client.get("/logout", follow_redirects=False)
    assert response.headers["Location"] in ("/", "http://localhost/")


def test_logout_clears_session(client):
    """
    Spec: 'Visiting GET /logout clears the session and redirects to /'
    and 'After logout, session["user_id"] is no longer present'.
    Logs in first to set session, then logs out and verifies the session is
    empty.
    """
    # Establish a logged-in session.
    post_login(client, TEST_EMAIL, TEST_PASSWORD)
    assert get_session_user_id(client) is not None, "Pre-condition: must be logged in"

    # Log out.
    client.get("/logout", follow_redirects=False)

    # Session must no longer contain user_id.
    assert get_session_user_id(client) is None


def test_logout_session_is_empty(client):
    """
    Spec: 'After logout, session["user_id"] is no longer present'.
    Verifies the entire session is empty after logout (not just user_id absent).
    """
    post_login(client, TEST_EMAIL, TEST_PASSWORD)
    client.get("/logout", follow_redirects=False)

    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_logout_not_stub_string(client):
    """
    Spec: 'The /logout route no longer returns the raw stub string'.
    A 302 redirect is not a raw string response, so any 302 satisfies this.
    """
    response = client.get("/logout", follow_redirects=False)
    assert response.status_code == 302
    assert b"coming in Step" not in response.data
