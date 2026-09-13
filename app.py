import os
import sqlite3
import uuid
from datetime import date
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, send_from_directory, session, url_for
from PIL import Image, UnidentifiedImageError
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from nutrition import calculate_nutrition
from physique import build_physique_path
from data_sources import source_status
from gamification import player_status
from workouts import generate_daily_workout_for_level, generate_workout

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "sylrix.db"
LEGACY_DATABASES = (BASE_DIR / "sylrix_ai.db", BASE_DIR / "renata_ai.db", BASE_DIR / "gymai.db")
UPLOAD_DIR = BASE_DIR / "uploads"
ALLOWED_IMAGE_TYPES = {"png", "jpg", "jpeg", "webp"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SYLRIX_SECRET_KEY", os.environ.get("SYLRIX_AI_SECRET_KEY", os.environ.get("RENATA_AI_SECRET_KEY", os.environ.get("GYMAI_SECRET_KEY", "change-this-before-deploying"))))
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
is_production = os.environ.get("SYLRIX_ENV") == "production"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SYLRIX_COOKIE_SECURE", "1" if is_production else "0") == "1"

if is_production and app.config["SECRET_KEY"] == "change-this-before-deploying":
    raise RuntimeError("Set SYLRIX_SECRET_KEY before running SYLRIX in production.")


def db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def setup_database():
    if not DATABASE.exists():
        for legacy_database in LEGACY_DATABASES:
            if legacy_database.exists():
                legacy_database.rename(DATABASE)
                break
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with db_connection() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS members (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, age INTEGER NOT NULL, sex TEXT NOT NULL, weight REAL NOT NULL, height REAL NOT NULL, goal TEXT NOT NULL, days INTEGER NOT NULL, equipment TEXT NOT NULL, experience TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS workout_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER NOT NULL, exercise_name TEXT NOT NULL, weight REAL, reps INTEGER, sets INTEGER, notes TEXT, logged_on TEXT NOT NULL, FOREIGN KEY (member_id) REFERENCES members(id));
            CREATE TABLE IF NOT EXISTS progress_photos (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER NOT NULL, filename TEXT NOT NULL, caption TEXT, uploaded_on TEXT NOT NULL, FOREIGN KEY (member_id) REFERENCES members(id));
            CREATE TABLE IF NOT EXISTS step_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER NOT NULL, steps INTEGER NOT NULL, goal INTEGER NOT NULL DEFAULT 8000, logged_on TEXT NOT NULL, UNIQUE(member_id, logged_on), FOREIGN KEY (member_id) REFERENCES members(id));
            CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL COLLATE NOCASE UNIQUE, email TEXT NOT NULL COLLATE NOCASE UNIQUE, password_hash TEXT NOT NULL, member_id INTEGER UNIQUE, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (member_id) REFERENCES members(id));
        """)
        member_columns = {row[1] for row in connection.execute("PRAGMA table_info(members)")}
        for column, definition in {
            "custom_goal": "TEXT NOT NULL DEFAULT ''",
            "training_style": "TEXT NOT NULL DEFAULT ''",
            "equipment_notes": "TEXT NOT NULL DEFAULT ''",
            "limitations": "TEXT NOT NULL DEFAULT ''",
        }.items():
            if column not in member_columns:
                connection.execute(f"ALTER TABLE members ADD COLUMN {column} {definition}")


def current_member():
    account_id = session.get("account_id")
    with db_connection() as connection:
        if account_id:
            return connection.execute("SELECT members.* FROM members JOIN accounts ON accounts.member_id = members.id WHERE accounts.id = ?", (account_id,)).fetchone()
        if session.get("member_id"):
            return connection.execute("SELECT * FROM members WHERE id = ?", (session["member_id"],)).fetchone()
    return None


def current_account():
    if not session.get("account_id"):
        return None
    with db_connection() as connection:
        return connection.execute("SELECT * FROM accounts WHERE id = ?", (session["account_id"],)).fetchone()


def require_member():
    member = current_member()
    if not member:
        flash("Create your member profile first.")
    return member


def image_allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_TYPES


def image_is_valid(photo):
    try:
        with Image.open(photo.stream) as image:
            image.verify()
        photo.stream.seek(0)
        return True
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        return False


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; script-src 'self' 'unsafe-inline'; img-src 'self'; base-uri 'self'; frame-ancestors 'none'"
    if session.get("account_id"):
        response.headers["Cache-Control"] = "private, no-store"
    return response


@app.route("/")
def home():
    member = current_member()
    if not member:
        return render_template("home.html")
    nutrition = calculate_nutrition(member["age"], member["sex"], member["weight"], member["height"], member["goal"], member["days"])
    with db_connection() as connection:
        recent_logs = connection.execute("SELECT * FROM workout_logs WHERE member_id = ? ORDER BY logged_on DESC, id DESC LIMIT 5", (member["id"],)).fetchall()
        log_count = connection.execute("SELECT COUNT(*) FROM workout_logs WHERE member_id = ?", (member["id"],)).fetchone()[0]
        photo_count = connection.execute("SELECT COUNT(*) FROM progress_photos WHERE member_id = ?", (member["id"],)).fetchone()[0]
        step_goals = connection.execute("SELECT COUNT(*) FROM step_logs WHERE member_id = ? AND steps >= goal", (member["id"],)).fetchone()[0]
        today_steps = connection.execute("SELECT steps, goal FROM step_logs WHERE member_id = ? AND logged_on = ?", (member["id"], date.today().isoformat())).fetchone()
    return render_template("dashboard.html", member=member, nutrition=nutrition, recent_logs=recent_logs, status=player_status(log_count, photo_count, step_goals), today_steps=today_steps)


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("account_id"):
        return redirect(url_for("home"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if len(username) < 3 or not username.replace("_", "").replace("-", "").isalnum():
            flash("Choose a username with 3+ letters, numbers, hyphens, or underscores.")
        elif "@" not in email or len(email) > 254:
            flash("Enter a valid email address.")
        elif len(password) < 12:
            flash("Use a password with at least 12 characters.")
        else:
            try:
                with db_connection() as connection:
                    cursor = connection.execute("INSERT INTO accounts (username, email, password_hash) VALUES (?, ?, ?)", (username, email, generate_password_hash(password)))
                    session.clear()
                    session["account_id"] = cursor.lastrowid
                flash("Account created. Now build your player profile.")
                return redirect(url_for("onboarding"))
            except sqlite3.IntegrityError:
                flash("That username or email is already in use.")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("account_id"):
        return redirect(url_for("home"))
    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        password = request.form.get("password", "")
        with db_connection() as connection:
            account = connection.execute("SELECT * FROM accounts WHERE username = ? OR email = ?", (identity, identity.lower())).fetchone()
        if not account or not check_password_hash(account["password_hash"], password):
            flash("Incorrect username/email or password.")
        else:
            session.clear()
            session["account_id"] = account["id"]
            if account["member_id"]:
                return redirect(url_for("home"))
            flash("Finish your player profile to unlock your plan.")
            return redirect(url_for("onboarding"))
    return render_template("login.html")


@app.route("/onboarding", methods=["GET", "POST"])
def onboarding():
    account = current_account()
    if not account:
        flash("Create an account or sign in before building a profile.")
        return redirect(url_for("register"))
    if account["member_id"]:
        return redirect(url_for("home"))
    if request.method == "POST":
        try:
            values = {"name": request.form["name"].strip(), "age": int(request.form["age"]), "sex": request.form["sex"].lower(), "weight": float(request.form["weight"]), "height": float(request.form["height"]), "goal": request.form["goal"].lower(), "days": int(request.form["days"]), "equipment": request.form["equipment"].lower(), "experience": request.form["experience"].lower(), "custom_goal": request.form.get("custom_goal", "").strip()[:500], "training_style": request.form.get("training_style", "").strip()[:100], "equipment_notes": request.form.get("equipment_notes", "").strip()[:500], "limitations": request.form.get("limitations", "").strip()[:500]}
            if not values["name"] or not 1 <= values["days"] <= 7 or values["age"] < 13:
                raise ValueError
        except (KeyError, ValueError):
            flash("Please enter valid profile details. Training days must be from 1 to 7.")
            return render_template("onboarding.html")
        with db_connection() as connection:
            cursor = connection.execute("""INSERT INTO members (name, age, sex, weight, height, goal, days, equipment, experience, custom_goal, training_style, equipment_notes, limitations)
                VALUES (:name, :age, :sex, :weight, :height, :goal, :days, :equipment, :experience, :custom_goal, :training_style, :equipment_notes, :limitations)""", values)
            connection.execute("UPDATE accounts SET member_id = ? WHERE id = ?", (cursor.lastrowid, account["id"]))
        flash("Your SYLRIX profile is ready.")
        return redirect(url_for("plan"))
    return render_template("onboarding.html")


@app.route("/plan")
def plan():
    member = require_member()
    if not member:
        return redirect(url_for("onboarding"))
    plan_goal = f'{member["goal"]} {member["custom_goal"]}'
    plan_equipment = f'{member["equipment"]} {member["equipment_notes"]}'
    return render_template("plan.html", member=member, workout_plan=generate_workout(plan_equipment, member["experience"], member["days"], plan_goal))


@app.route("/log", methods=["GET", "POST"])
def log_workout():
    member = require_member()
    if not member:
        return redirect(url_for("onboarding"))
    if request.method == "POST":
        try:
            exercise = request.form["exercise"].strip()
            if not exercise:
                raise ValueError
            weight = float(request.form["weight"]) if request.form["weight"] else None
            reps = int(request.form["reps"]) if request.form["reps"] else None
            sets = int(request.form["sets"]) if request.form["sets"] else None
        except ValueError:
            flash("Please add an exercise and use valid numbers.")
            return redirect(url_for("log_workout"))
        with db_connection() as connection:
            connection.execute("INSERT INTO workout_logs (member_id, exercise_name, weight, reps, sets, notes, logged_on) VALUES (?, ?, ?, ?, ?, ?, ?)", (member["id"], exercise, weight, reps, sets, request.form.get("notes", "").strip(), date.today().isoformat()))
        flash("Workout entry saved.")
        return redirect(url_for("log_workout"))
    with db_connection() as connection:
        logs = connection.execute("SELECT * FROM workout_logs WHERE member_id = ? ORDER BY logged_on DESC, id DESC LIMIT 30", (member["id"],)).fetchall()
    return render_template("log.html", member=member, logs=logs)


@app.route("/nutrition")
def nutrition():
    member = require_member()
    if not member:
        return redirect(url_for("onboarding"))
    targets = calculate_nutrition(member["age"], member["sex"], member["weight"], member["height"], member["goal"], member["days"])
    return render_template("nutrition.html", member=member, targets=targets)


@app.route("/steps", methods=["GET", "POST"])
def steps():
    member = require_member()
    if not member:
        return redirect(url_for("onboarding"))
    today = date.today().isoformat()
    if request.method == "POST":
        try:
            step_count = int(request.form["steps"])
            goal = int(request.form["goal"])
            if step_count < 0 or goal < 1000 or goal > 100000:
                raise ValueError
        except (KeyError, ValueError):
            flash("Use a valid step count and a goal between 1,000 and 100,000.")
            return redirect(url_for("steps"))
        with db_connection() as connection:
            connection.execute("""INSERT INTO step_logs (member_id, steps, goal, logged_on) VALUES (?, ?, ?, ?)
                ON CONFLICT(member_id, logged_on) DO UPDATE SET steps = excluded.steps, goal = excluded.goal""", (member["id"], step_count, goal, today))
        flash("Today’s steps are saved.")
        return redirect(url_for("steps"))
    with db_connection() as connection:
        today_steps = connection.execute("SELECT * FROM step_logs WHERE member_id = ? AND logged_on = ?", (member["id"], today)).fetchone()
        history = connection.execute("SELECT * FROM step_logs WHERE member_id = ? ORDER BY logged_on DESC LIMIT 7", (member["id"],)).fetchall()
    return render_template("steps.html", member=member, today_steps=today_steps, history=history)


@app.route("/physique", methods=["GET", "POST"])
def physique():
    member = require_member()
    if not member:
        return redirect(url_for("onboarding"))
    path = None
    if request.method == "POST":
        path = build_physique_path(member, request.form.get("inspiration", ""), request.form.get("priority", "overall"))
    return render_template("physique.html", member=member, path=path)


@app.route("/sources")
def sources():
    return render_template("sources.html", sources=source_status())


@app.route("/progress", methods=["GET", "POST"])
def progress():
    member = require_member()
    if not member:
        return redirect(url_for("onboarding"))
    if request.method == "POST":
        photo = request.files.get("photo")
        if not photo or not photo.filename or not image_allowed(photo.filename) or not image_is_valid(photo):
            flash("Upload a valid PNG, JPG, JPEG, or WEBP image.")
            return redirect(url_for("progress"))
        filename = f"{uuid.uuid4().hex}_{secure_filename(photo.filename)}"
        photo.save(UPLOAD_DIR / filename)
        with db_connection() as connection:
            connection.execute("INSERT INTO progress_photos (member_id, filename, caption, uploaded_on) VALUES (?, ?, ?, ?)", (member["id"], filename, request.form.get("caption", "").strip(), date.today().isoformat()))
        flash("Progress photo saved.")
        return redirect(url_for("progress"))
    with db_connection() as connection:
        photos = connection.execute("SELECT * FROM progress_photos WHERE member_id = ? ORDER BY uploaded_on DESC, id DESC", (member["id"],)).fetchall()
    return render_template("progress.html", member=member, photos=photos)


@app.route("/progress/photo/<int:photo_id>")
def progress_photo(photo_id):
    member = require_member()
    if not member:
        return redirect(url_for("login"))
    with db_connection() as connection:
        photo = connection.execute("SELECT filename FROM progress_photos WHERE id = ? AND member_id = ?", (photo_id, member["id"])).fetchone()
    if not photo:
        abort(404)
    return send_from_directory(UPLOAD_DIR, photo["filename"])


@app.route("/daily")
def daily_workout():
    experience = request.args.get("experience", "beginner")
    return render_template("daily.html", workout=generate_daily_workout_for_level(experience))


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.")
    return redirect(url_for("home"))


@app.errorhandler(413)
def too_large(_error):
    flash("Images must be 8 MB or smaller.")
    return redirect(url_for("progress"))


setup_database()

if __name__ == "__main__":
    app.run(debug=os.environ.get("SYLRIX_DEBUG", "0") == "1", port=int(os.environ.get("PORT", 5001)))
