import os
import sqlite3
import uuid
from datetime import date
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from nutrition import calculate_nutrition
from physique import build_physique_path
from data_sources import source_status
from gamification import player_status
from workouts import generate_daily_workout_for_level, generate_workout

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "renata_ai.db"
LEGACY_DATABASE = BASE_DIR / "gymai.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
ALLOWED_IMAGE_TYPES = {"png", "jpg", "jpeg", "webp"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("RENATA_AI_SECRET_KEY", os.environ.get("GYMAI_SECRET_KEY", "change-this-before-deploying"))
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)


def db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def setup_database():
    if not DATABASE.exists() and LEGACY_DATABASE.exists():
        LEGACY_DATABASE.rename(DATABASE)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with db_connection() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS members (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, age INTEGER NOT NULL, sex TEXT NOT NULL, weight REAL NOT NULL, height REAL NOT NULL, goal TEXT NOT NULL, days INTEGER NOT NULL, equipment TEXT NOT NULL, experience TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS workout_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER NOT NULL, exercise_name TEXT NOT NULL, weight REAL, reps INTEGER, sets INTEGER, notes TEXT, logged_on TEXT NOT NULL, FOREIGN KEY (member_id) REFERENCES members(id));
            CREATE TABLE IF NOT EXISTS progress_photos (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER NOT NULL, filename TEXT NOT NULL, caption TEXT, uploaded_on TEXT NOT NULL, FOREIGN KEY (member_id) REFERENCES members(id));
            CREATE TABLE IF NOT EXISTS step_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER NOT NULL, steps INTEGER NOT NULL, goal INTEGER NOT NULL DEFAULT 8000, logged_on TEXT NOT NULL, UNIQUE(member_id, logged_on), FOREIGN KEY (member_id) REFERENCES members(id));
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
    if not session.get("member_id"):
        return None
    with db_connection() as connection:
        return connection.execute("SELECT * FROM members WHERE id = ?", (session["member_id"],)).fetchone()


def require_member():
    member = current_member()
    if not member:
        flash("Create your member profile first.")
    return member


def image_allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_TYPES


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


@app.route("/onboarding", methods=["GET", "POST"])
def onboarding():
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
            session["member_id"] = cursor.lastrowid
        flash("Your Renata AI profile is ready.")
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
        if not photo or not photo.filename or not image_allowed(photo.filename):
            flash("Upload a PNG, JPG, JPEG, or WEBP image.")
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
    app.run(debug=True, port=int(os.environ.get("PORT", 5001)))
