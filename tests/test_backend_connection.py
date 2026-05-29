"""
Tests for Step 05 — Backend Connection (Spec: .claude/specs/05-backend-routes-for-profile-page.md)

Unit tests call query helpers directly against an isolated temp DB.
Route tests verify the /profile endpoint via the Flask test client.
"""

import sqlite3
import pytest
from werkzeug.security import generate_password_hash

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USER_NAME     = "Test User"
USER_EMAIL    = "test@example.com"
USER_PASSWORD = "testpass123"
USER_CREATED  = "2026-01-15 10:00:00"

EXPENSES = [
    ("Food",      100.00, "2026-01-01", "Groceries"),
    ("Transport", 200.00, "2026-01-02", "Bus pass"),
    ("Bills",     300.00, "2026-01-03", "Electricity"),
]

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_path(tmp_path, monkeypatch):
    """
    Isolated SQLite database wired to both database.db and database.queries
    via monkeypatching the module-level DB_PATH variable.
    """
    db_file = tmp_path / "test_expense_tracker.db"

    import database.db as db_module
    monkeypatch.setattr(db_module, "DB_PATH", str(db_file))

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

    # Insert primary test user with known created_at
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (USER_NAME, USER_EMAIL, generate_password_hash(USER_PASSWORD), USER_CREATED),
    )
    user_id = cursor.lastrowid

    # Insert known expenses for the primary user
    cursor.executemany(
        "INSERT INTO expenses (user_id, category, amount, date, description) VALUES (?, ?, ?, ?, ?)",
        [(user_id, cat, amt, date, desc) for cat, amt, date, desc in EXPENSES],
    )

    # Insert a second user with NO expenses for empty-state tests
    cursor.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Empty User", "empty@example.com", generate_password_hash("emptypass")),
    )
    empty_user_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return {"db_file": str(db_file), "user_id": user_id, "empty_user_id": empty_user_id}


@pytest.fixture()
def app(db_path, monkeypatch):
    """Flask test app wired to the isolated database."""
    import database.db as db_module
    monkeypatch.setattr(db_module, "DB_PATH", db_path["db_file"])

    import app as flask_app_module
    flask_app_module.app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key",
        WTF_CSRF_ENABLED=False,
    )
    yield flask_app_module.app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def logged_in_client(client, db_path):
    """Test client with an active session for the primary test user."""
    client.post(
        "/login",
        data={"email": USER_EMAIL, "password": USER_PASSWORD},
        follow_redirects=False,
    )
    return client


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def get_queries():
    """Import queries module fresh each test (monkeypatch applied before call)."""
    from database import queries
    return queries


# ---------------------------------------------------------------------------
# Unit: get_user_by_id
# ---------------------------------------------------------------------------

def test_get_user_by_id_returns_correct_fields(db_path):
    q = get_queries()
    result = q.get_user_by_id(db_path["user_id"])
    assert result is not None
    assert result["name"] == USER_NAME
    assert result["email"] == USER_EMAIL


def test_get_user_by_id_formats_member_since(db_path):
    q = get_queries()
    result = q.get_user_by_id(db_path["user_id"])
    # USER_CREATED = "2026-01-15 10:00:00" → "January 2026"
    assert result["member_since"] == "January 2026"


def test_get_user_by_id_nonexistent_returns_none(db_path):
    q = get_queries()
    assert q.get_user_by_id(99999) is None


# ---------------------------------------------------------------------------
# Unit: get_summary_stats
# ---------------------------------------------------------------------------

def test_get_summary_stats_correct_total(db_path):
    q = get_queries()
    result = q.get_summary_stats(db_path["user_id"])
    # 100 + 200 + 300 = 600
    assert result["total_spent"] == 600.0


def test_get_summary_stats_correct_count(db_path):
    q = get_queries()
    result = q.get_summary_stats(db_path["user_id"])
    assert result["transaction_count"] == 3


def test_get_summary_stats_correct_top_category(db_path):
    q = get_queries()
    result = q.get_summary_stats(db_path["user_id"])
    # Bills = 300 is highest
    assert result["top_category"] == "Bills"


def test_get_summary_stats_empty_user_returns_zeros(db_path):
    q = get_queries()
    result = q.get_summary_stats(db_path["empty_user_id"])
    assert result["total_spent"] == 0
    assert result["transaction_count"] == 0
    assert result["top_category"] == "—"


# ---------------------------------------------------------------------------
# Unit: get_recent_transactions
# ---------------------------------------------------------------------------

def test_get_recent_transactions_returns_all_for_user(db_path):
    q = get_queries()
    result = q.get_recent_transactions(db_path["user_id"])
    assert len(result) == 3


def test_get_recent_transactions_ordered_newest_first(db_path):
    q = get_queries()
    result = q.get_recent_transactions(db_path["user_id"])
    # EXPENSES sorted by date DESC: Bills(Jan 3), Transport(Jan 2), Food(Jan 1)
    assert result[0]["category"] == "Bills"
    assert result[1]["category"] == "Transport"
    assert result[2]["category"] == "Food"


def test_get_recent_transactions_has_required_fields(db_path):
    q = get_queries()
    result = q.get_recent_transactions(db_path["user_id"])
    for row in result:
        assert "date" in row
        assert "description" in row
        assert "category" in row
        assert "amount" in row


def test_get_recent_transactions_date_format(db_path):
    q = get_queries()
    result = q.get_recent_transactions(db_path["user_id"])
    # "2026-01-03" → "Jan 3"
    assert result[0]["date"] == "Jan 3"


def test_get_recent_transactions_respects_limit(db_path):
    q = get_queries()
    result = q.get_recent_transactions(db_path["user_id"], limit=2)
    assert len(result) == 2


def test_get_recent_transactions_empty_user_returns_empty_list(db_path):
    q = get_queries()
    result = q.get_recent_transactions(db_path["empty_user_id"])
    assert result == []


# ---------------------------------------------------------------------------
# Unit: get_category_breakdown
# ---------------------------------------------------------------------------

def test_get_category_breakdown_returns_correct_count(db_path):
    q = get_queries()
    result = q.get_category_breakdown(db_path["user_id"])
    assert len(result) == 3


def test_get_category_breakdown_ordered_by_total_desc(db_path):
    q = get_queries()
    result = q.get_category_breakdown(db_path["user_id"])
    # Bills=300, Transport=200, Food=100
    assert result[0]["name"] == "Bills"
    assert result[1]["name"] == "Transport"
    assert result[2]["name"] == "Food"


def test_get_category_breakdown_pcts_sum_to_100(db_path):
    q = get_queries()
    result = q.get_category_breakdown(db_path["user_id"])
    assert sum(item["pct"] for item in result) == 100


def test_get_category_breakdown_pcts_are_integers(db_path):
    q = get_queries()
    result = q.get_category_breakdown(db_path["user_id"])
    for item in result:
        assert isinstance(item["pct"], int)


def test_get_category_breakdown_empty_user_returns_empty_list(db_path):
    q = get_queries()
    result = q.get_category_breakdown(db_path["empty_user_id"])
    assert result == []


# ---------------------------------------------------------------------------
# Route: GET /profile
# ---------------------------------------------------------------------------

def test_profile_unauthenticated_redirects_to_login(client):
    response = client.get("/profile", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_profile_authenticated_returns_200(logged_in_client):
    response = logged_in_client.get("/profile")
    assert response.status_code == 200


def test_profile_shows_real_user_name(logged_in_client):
    response = logged_in_client.get("/profile")
    assert USER_NAME.encode() in response.data


def test_profile_shows_real_user_email(logged_in_client):
    response = logged_in_client.get("/profile")
    assert USER_EMAIL.encode() in response.data


def test_profile_shows_rupee_symbol(logged_in_client):
    response = logged_in_client.get("/profile")
    assert "₹" in response.data.decode("utf-8")


def test_profile_shows_correct_total_spent(logged_in_client):
    response = logged_in_client.get("/profile")
    # 100 + 200 + 300 = 600 → "₹600"
    assert "₹600" in response.data.decode("utf-8")


def test_profile_shows_correct_transaction_count(logged_in_client):
    response = logged_in_client.get("/profile")
    assert b"3" in response.data


def test_profile_shows_correct_top_category(logged_in_client):
    response = logged_in_client.get("/profile")
    assert b"Bills" in response.data
