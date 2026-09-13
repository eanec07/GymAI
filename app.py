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
from workouts import generate_daily_workout, generate_workout

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "gymai.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
ALLOWED_IMAGE_TYPES = {"png", "jpg", "jpeg", "webp"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("GYMAI_SECRET_KEY", "change-this-before-deploying")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)


def db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def setup_database():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with db_connection() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS members (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, age INTEGER NOT NULL, sex TEXT NOT NULL, weight REAL NOT NULL, height REAL NOT NULL, goal TEXT NOT NULL, days INTEGER NOT NULL, equipment TEXT NOT NULL, experience TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS workout_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER NOT NULL, exercise_name TEXT NOT NULL, weight REAL, reps INTEGER, sets INTEGER, notes TEXT, logged_on TEXT NOT NULL, FOREIGN KEY (member_id) REFERENCES members(id));
            CREATE TABLE IF NOT EXISTS progress_photos (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER NOT NULL, filename TEXT NOT NULL, caption TEXT, uploaded_on TEXT NOT NULL, FOREIGN KEY (member_id) REFERENCES members(id));
        """)


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
    return render_template("dashboard.html", member=member, nutrition=nutrition, recent_logs=recent_logs)


@app.route("/onboarding", methods=["GET", "POST"])
def onboarding():
    if request.method == "POST":
        try:
            values = {"name": request.form["name"].strip(), "age": int(request.form["age"]), "sex": request.form["sex"].lower(), "weight": float(request.form["weight"]), "height": float(request.form["height"]), "goal": request.form["goal"].lower(), "days": int(request.form["days"]), "equipment": request.form["equipment"].lower(), "experience": request.form["experience"].lower()}
            if not values["name"] or not 1 <= values["days"] <= 7 or values["age"] < 13:
                raise ValueError
        except (KeyError, ValueError):
            flash("Please enter valid profile details. Training days must be from 1 to 7.")
            return render_template("onboarding.html")
        with db_connection() as connection:
            cursor = connection.execute("INSERT INTO members (name, age, sex, weight, height, goal, days, equipment, experience) VALUES (:name, :age, :sex, :weight, :height, :goal, :days, :equipment, :experience)", values)
            session["member_id"] = cursor.lastrowid
        flash("Your GymAI profile is ready.")
        return redirect(url_for("plan"))
    return render_template("onboarding.html")


@app.route("/plan")
def plan():
    member = require_member()
    if not member:
        return redirect(url_for("onboarding"))
    return render_template("plan.html", member=member, workout_plan=generate_workout(member["equipment"], member["experience"], member["days"], member["goal"]))


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
    return render_template("daily.html", workout=generate_daily_workout())


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
    app.run(debug=True)
