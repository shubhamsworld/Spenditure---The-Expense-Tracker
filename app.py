import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from database.db import get_db, init_db, seed_db, create_user, get_user_by_email

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def require_login():
    if not session.get("user_id"):
        flash("Please sign in to continue.", "error")
        return redirect(url_for("login"))
    return None


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if not name or not email or not password or not confirm:
            flash("All fields are required.", "error")
            return render_template("register.html")

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            flash("Email already registered.", "error")
            return render_template("register.html")

        flash("Account created! Please sign in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            flash("All fields are required.", "error")
            return render_template("login.html")

        user = get_user_by_email(email)
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        session.clear()
        session["user_id"]    = user["id"]
        session["user_name"]  = user["name"]
        session["user_email"] = user["email"]
        flash(f"Welcome back, {user['name']}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/dashboard")
def dashboard():
    redir = require_login()
    if redir:
        return redir
    return render_template("dashboard.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    flash("You've been signed out.", "success")
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    redir = require_login()
    if redir:
        return redir

    name   = session.get("user_name", "")
    parts  = name.strip().split()
    initials = (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()

    user = {
        "name": name,
        "email": session.get("user_email", ""),
        "member_since": "January 2026",
        "initials": initials,
    }
    stats = {
        "total_spent": "₹5,669",
        "transaction_count": 8,
        "top_category": "Education",
    }
    expenses = [
        {"date": "May 22", "description": "Clothing",         "category": "Shopping",       "amount": "₹1,500"},
        {"date": "May 18", "description": "Movie + snacks",   "category": "Entertainment",  "amount": "₹800"},
        {"date": "May 15", "description": "Pharmacy",         "category": "Health",         "amount": "₹250"},
        {"date": "May 12", "description": "Online course",    "category": "Education",      "amount": "₹1,200"},
        {"date": "May 10", "description": "Restaurant",       "category": "Food",           "amount": "₹450"},
    ]
    categories = [
        {"name": "Shopping",      "amount": "₹1,500", "pct": 26},
        {"name": "Bills",         "amount": "₹999",   "pct": 18},
        {"name": "Education",     "amount": "₹1,200", "pct": 21},
        {"name": "Entertainment", "amount": "₹800",   "pct": 14},
        {"name": "Food",          "amount": "₹770",   "pct": 14},
        {"name": "Health",        "amount": "₹250",   "pct": 4},
        {"name": "Transport",     "amount": "₹150",   "pct": 3},
    ]
    return render_template("profile.html", user=user, stats=stats, expenses=expenses, categories=categories)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=True, port=5001)
