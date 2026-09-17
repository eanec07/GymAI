import os
import re
import sqlite3
import uuid
import json
import logging
import secrets
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, send_from_directory, session, url_for
from PIL import Image, UnidentifiedImageError
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from nutrition import calculate_nutrition
from services.nutrition_tracking import daily_nutrition, nutrition_values, recent_foods
from services.readiness import calculate_readiness, readiness_for_today, readiness_history, training_recommendation
from physique import build_physique_path
from data_sources import source_status
from workouts import generate_daily_workout_for_level, generate_workout, weekly_daily_schedule
from services.ai_coach import CoachService, MODEL
from training.exercise_repository import load_exercises
from training.filtering import find_substitutes
from training.models import TrainingGoal, UserProfile
from training.progression import get_progression_recommendation
from training.prs import detect_prs
from training.adaptive import apply_progression_states, progression_state, progression_states, recommendation_for_session, save_progression_state
from muscles import diagram_regions, display_muscle

TRAINING_CATEGORIES = {
    "bodybuilding": ("Bodybuilding", "Build muscle through balanced hypertrophy training, practical volume, and progressive overload.", "Bodybuilding"),
    "powerlifting": ("Powerlifting", "Build your squat, bench, and deadlift with focused strength progression.", "Powerlifting"),
    "powerbuilding": ("Powerbuilding", "Combine big-lift strength with enough volume to build a capable physique.", "Strength training"),
    "crossfit": ("CrossFit-style training", "Develop conditioning and full-body capacity with scalable functional sessions.", "CrossFit / functional fitness"),
    "calisthenics": ("Calisthenics", "Use bodyweight strength, pull-up progressions, and minimal equipment.", "Calisthenics"),
    "strength": ("Strength", "Train foundational movements with clear progression and useful rep ranges.", "Strength training"),
    "general-fitness": ("General fitness", "Build a sustainable routine for strength, movement, and everyday energy.", "Home workouts"),
    "endurance": ("Endurance", "Build steady capacity and athletic consistency for longer efforts.", "Sports performance"),
}

CATEGORY_SETUP = {
    "bodybuilding": {"goals": "Prioritize muscle groups · Build balanced size · Bring up weak points", "questions": "Priority muscle groups, preferred split, volume comfort, and rep-range preference.", "split": "Upper / Lower or Push / Pull / Legs"},
    "powerlifting": {"goals": "Build squat · Build bench press · Build deadlift", "questions": "Current or estimated maxes, competition interest, weak points, and preferred lift frequency.", "split": "3- or 4-day squat / bench / deadlift layout"},
    "powerbuilding": {"goals": "Build big lifts · Add productive hypertrophy volume", "questions": "Strength targets, muscle priorities, current squat / bench / deadlift numbers, and frequency.", "split": "Upper / Lower strength + hypertrophy"},
    "crossfit": {"goals": "Improve engine · Build functional strength · Train mixed-modal fitness", "questions": "Conditioning level, barbell access, rower or bike access, kettlebells, pull-up rig, and session duration.", "split": "Alternating engine and strength + conditioning days"},
    "calisthenics": {"goals": "Stronger basics · Better pull-ups and dips · Skill progress", "questions": "Current pull-up, push-up, and dip ability; pull-up bar, rings, dip bars, bands, and skill goals.", "split": "Push / Pull / Legs or Upper / Lower + skill work"},
    "strength": {"goals": "Build foundational lifts · Progress with confidence", "questions": "Primary lifts, available rack and barbell, strength target, and preferred frequency.", "split": "Upper / Lower or full-body strength"},
    "general-fitness": {"goals": "Move better · Feel stronger · Build a sustainable habit", "questions": "Main health goal, days available, session duration, and realistic equipment access.", "split": "Balanced full-body plan"},
    "endurance": {"goals": "Build weekly capacity · Prepare for a distance · Improve consistency", "questions": "Weekly mileage, current running frequency, preferred distance, pace if known, and limitations.", "split": "Running frequency plan + simple strength support"},
}

TRAINING_PREFERENCE_FIELDS = {
    "powerlifting": (("squat_max", "Squat max / estimated max (lb)", "315", "number"), ("bench_max", "Bench max / estimated max (lb)", "225", "number"), ("deadlift_max", "Deadlift max / estimated max (lb)", "405", "number"), ("weak_lift", "Weakest lift", "Example: bench press", "text"), ("competition_interest", "Competition interest", "None, maybe later, or competing", "text"), ("lift_frequency", "Preferred lift frequency", "Example: bench twice weekly", "text")),
    "powerbuilding": (("squat_max", "Squat max / estimated max (lb)", "315", "number"), ("bench_max", "Bench max / estimated max (lb)", "225", "number"), ("deadlift_max", "Deadlift max / estimated max (lb)", "405", "number"), ("strength_priority", "Strength priority", "Example: bench press", "text"), ("priority_muscles", "Muscles to emphasize", "Example: shoulders and back", "text"), ("training_emphasis", "Strength vs hypertrophy emphasis", "Example: 60% strength / 40% size", "text")),
    "bodybuilding": (("priority_muscles", "Priority muscle groups", "Example: chest and shoulders", "text"), ("weak_points", "Weak points", "Example: upper back", "text"), ("volume_preference", "Volume preference", "Low, moderate, or high", "text"), ("preferred_rep_range", "Preferred rep range", "Example: 8–12", "text")),
    "strength": (("main_lifts", "Main lifts", "Example: squat, bench, deadlift", "text"), ("current_strength", "Current strength", "Example: beginner with a 135 lb bench", "text"), ("strength_goals", "Strength goals", "Example: 225 lb bench", "text"), ("barbell_access", "Barbell access", "Yes or no", "text"), ("rack_access", "Rack access", "Yes or no", "text")),
    "calisthenics": (("pullup_reps", "Max/current pull-ups", "0", "number"), ("pushup_reps", "Max/current push-ups", "10", "number"), ("dip_reps", "Max/current dips", "0", "number"), ("bodyweight_equipment", "Available equipment", "Pull-up bar, rings, bands", "text"), ("skill_goal", "Skill goal", "Muscle-up, handstand, front lever, planche…", "text")),
    "crossfit": (("conditioning_level", "Conditioning level", "Beginner, intermediate, or advanced", "text"), ("functional_equipment", "Available functional equipment", "Kettlebells, rower, bike, box, sled, pull-up rig", "text"), ("functional_emphasis", "Training emphasis", "Strength, conditioning, or balanced", "text")),
    "endurance": (("weekly_mileage", "Current weekly mileage", "15", "number"), ("running_frequency", "Current training frequency", "Example: 3 runs/week", "text"), ("target_distance", "Target distance", "5K, 10K, half marathon…", "text"), ("current_pace", "Current pace", "Example: 10:00 / mile", "text"), ("race_goal", "Race goal", "Example: finish a 10K", "text"), ("longest_session", "Longest recent session", "Example: 5 miles", "text")),
    "general-fitness": (("primary_goal", "Primary goal", "Strength, energy, fat loss, mobility…", "text"), ("cardio_priority", "Cardio priority", "Low, moderate, or high", "text"), ("body_composition_priority", "Body-composition priority", "Example: lose 15 lb", "text"), ("preferred_cardio", "Preferred cardio", "Walk, run, bike, row…", "text")),
}

BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("SYLRIX_DATABASE_PATH", str(BASE_DIR / "sylrix.db")))
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
csrf_enabled = os.environ.get("SYLRIX_CSRF_ENABLED", "1" if is_production else "0") == "1"
app.config["BETA_MODE"] = os.environ.get("SYLRIX_BETA_MODE") == "1"
app.config["ASSET_VERSION"] = os.environ.get("SYLRIX_ASSET_VERSION", "20260918")
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SYLRIX_COOKIE_SECURE", "1" if is_production else "0") == "1"

if is_production and app.config["SECRET_KEY"] == "change-this-before-deploying":
    raise RuntimeError("Set SYLRIX_SECRET_KEY before running SYLRIX in production.")
if is_production:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
app.logger.info("SYLRIX starting in %s mode", "production" if is_production else "development")


@app.context_processor
def csrf_context():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return {"csrf_token": token}


@app.before_request
def enforce_csrf():
    if csrf_enabled and request.method == "POST":
        token = request.form.get("csrf_token", "")
        if not token or not secrets.compare_digest(token, session.get("csrf_token", "")):
            abort(403)


@contextmanager
def db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


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
            CREATE TABLE IF NOT EXISTS nutrition_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER NOT NULL, food_name TEXT NOT NULL, calories REAL NOT NULL DEFAULT 0, protein REAL NOT NULL DEFAULT 0, carbs REAL NOT NULL DEFAULT 0, fat REAL NOT NULL DEFAULT 0, fiber REAL NOT NULL DEFAULT 0, logged_on TEXT NOT NULL, FOREIGN KEY (member_id) REFERENCES members(id));
            CREATE TABLE IF NOT EXISTS coach_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER NOT NULL, role TEXT NOT NULL, message TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (member_id) REFERENCES members(id));
            CREATE TABLE IF NOT EXISTS training_preferences (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER NOT NULL, preference_key TEXT NOT NULL, preference_value TEXT NOT NULL DEFAULT '', UNIQUE(member_id, preference_key), FOREIGN KEY (member_id) REFERENCES members(id));
            CREATE TABLE IF NOT EXISTS workout_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER NOT NULL, workout_name TEXT NOT NULL, workout_day INTEGER NOT NULL, training_style TEXT NOT NULL DEFAULT '', started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, completed_at TEXT, status TEXT NOT NULL DEFAULT 'active', FOREIGN KEY(member_id) REFERENCES members(id));
            CREATE TABLE IF NOT EXISTS workout_sets (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL, exercise_name TEXT NOT NULL, exercise_order INTEGER NOT NULL, set_number INTEGER NOT NULL, target_reps TEXT, target_weight REAL, target_rpe REAL, actual_weight REAL, actual_reps INTEGER, actual_rpe REAL, completed INTEGER NOT NULL DEFAULT 0, notes TEXT NOT NULL DEFAULT '', is_warmup INTEGER NOT NULL DEFAULT 0, skipped INTEGER NOT NULL DEFAULT 0, FOREIGN KEY(session_id) REFERENCES workout_sessions(id));
            CREATE TABLE IF NOT EXISTS session_exercises (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL, exercise_order INTEGER NOT NULL, original_exercise_name TEXT NOT NULL, exercise_name TEXT NOT NULL, replaced INTEGER NOT NULL DEFAULT 0, notes TEXT NOT NULL DEFAULT '', UNIQUE(session_id, exercise_order), FOREIGN KEY(session_id) REFERENCES workout_sessions(id));
            CREATE TABLE IF NOT EXISTS personal_records (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER NOT NULL, workout_session_id INTEGER, exercise_name TEXT NOT NULL, pr_type TEXT NOT NULL, value REAL NOT NULL DEFAULT 0, weight REAL, reps INTEGER, estimated_1rm REAL, achieved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(member_id, workout_session_id, exercise_name, pr_type), FOREIGN KEY(member_id) REFERENCES members(id), FOREIGN KEY(workout_session_id) REFERENCES workout_sessions(id));
            CREATE TABLE IF NOT EXISTS body_weight_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER NOT NULL, weight REAL NOT NULL, logged_on TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(member_id, logged_on), FOREIGN KEY(member_id) REFERENCES members(id));
            CREATE TABLE IF NOT EXISTS exercise_progression_state (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER NOT NULL, exercise_name TEXT NOT NULL, last_session_id INTEGER, recommended_weight REAL, recommended_reps TEXT, recommended_rpe REAL, progression_action TEXT NOT NULL, reason TEXT NOT NULL DEFAULT '', consecutive_misses INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(member_id, exercise_name), FOREIGN KEY(member_id) REFERENCES members(id), FOREIGN KEY(last_session_id) REFERENCES workout_sessions(id));
            CREATE TABLE IF NOT EXISTS daily_readiness (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER NOT NULL, logged_on TEXT NOT NULL, sleep_hours REAL NOT NULL, sleep_quality INTEGER NOT NULL, energy INTEGER NOT NULL, soreness INTEGER NOT NULL, stress INTEGER NOT NULL, motivation INTEGER NOT NULL, notes TEXT NOT NULL DEFAULT '', score INTEGER NOT NULL, classification TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(member_id, logged_on), FOREIGN KEY(member_id) REFERENCES members(id));
            CREATE INDEX IF NOT EXISTS idx_workout_sessions_member_status ON workout_sessions(member_id, status);
            CREATE INDEX IF NOT EXISTS idx_workout_sets_session ON workout_sets(session_id);
            CREATE INDEX IF NOT EXISTS idx_nutrition_logs_member_date ON nutrition_logs(member_id, logged_on);
            CREATE INDEX IF NOT EXISTS idx_body_weight_logs_member_date ON body_weight_logs(member_id, logged_on);
            CREATE INDEX IF NOT EXISTS idx_personal_records_member_achieved ON personal_records(member_id, achieved_at);
            CREATE INDEX IF NOT EXISTS idx_progression_state_member_exercise ON exercise_progression_state(member_id, exercise_name);
            CREATE INDEX IF NOT EXISTS idx_coach_messages_member_id ON coach_messages(member_id, id);
            CREATE INDEX IF NOT EXISTS idx_daily_readiness_member_date ON daily_readiness(member_id, logged_on);
        """)
        member_columns = {row[1] for row in connection.execute("PRAGMA table_info(members)")}
        for column, definition in {
            "custom_goal": "TEXT NOT NULL DEFAULT ''",
            "training_style": "TEXT NOT NULL DEFAULT ''",
            "equipment_notes": "TEXT NOT NULL DEFAULT ''",
            "limitations": "TEXT NOT NULL DEFAULT ''",
            "split_preference": "TEXT NOT NULL DEFAULT 'auto'",
            "session_minutes": "INTEGER NOT NULL DEFAULT 60",
            "favorite_exercises": "TEXT NOT NULL DEFAULT ''",
            "avoid_exercises": "TEXT NOT NULL DEFAULT ''",
            "goal_weight": "REAL",
            "auto_rest_timer": "INTEGER NOT NULL DEFAULT 1",
        }.items():
            if column not in member_columns:
                connection.execute(f"ALTER TABLE members ADD COLUMN {column} {definition}")
        set_columns = {row[1] for row in connection.execute("PRAGMA table_info(workout_sets)")}
        if "is_warmup" not in set_columns:
            connection.execute("ALTER TABLE workout_sets ADD COLUMN is_warmup INTEGER NOT NULL DEFAULT 0")
        exercise_columns = {row[1] for row in connection.execute("PRAGMA table_info(session_exercises)")}
        if "notes" not in exercise_columns:
            connection.execute("ALTER TABLE session_exercises ADD COLUMN notes TEXT NOT NULL DEFAULT ''")
        nutrition_columns = {row[1] for row in connection.execute("PRAGMA table_info(nutrition_logs)")}
        if "serving" not in nutrition_columns:
            connection.execute("ALTER TABLE nutrition_logs ADD COLUMN serving TEXT NOT NULL DEFAULT ''")
        session_columns = {row[1] for row in connection.execute("PRAGMA table_info(workout_sessions)")}
        for column, definition in {
            "readiness_score": "INTEGER",
            "readiness_classification": "TEXT NOT NULL DEFAULT ''",
            "readiness_adjustment": "TEXT NOT NULL DEFAULT ''",
            "readiness_adjusted_at": "TEXT",
        }.items():
            if column not in session_columns:
                connection.execute(f"ALTER TABLE workout_sessions ADD COLUMN {column} {definition}")
        if "skipped" not in set_columns:
            connection.execute("ALTER TABLE workout_sets ADD COLUMN skipped INTEGER NOT NULL DEFAULT 0")


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


def valid_training_style(value):
    return value if value in TRAINING_CATEGORIES else ""


def training_preferences_for(member_id):
    with db_connection() as connection:
        rows = connection.execute("SELECT preference_key, preference_value FROM training_preferences WHERE member_id = ?", (member_id,)).fetchall()
    return {row["preference_key"]: row["preference_value"] for row in rows}


def save_training_preferences(member_id, style, form):
    allowed_keys = {key for key, *_field in TRAINING_PREFERENCE_FIELDS.get(style, ())}
    with db_connection() as connection:
        for key in allowed_keys:
            value = form.get(f"preference_{key}", "").strip()[:200]
            connection.execute("INSERT INTO training_preferences (member_id, preference_key, preference_value) VALUES (?, ?, ?) ON CONFLICT(member_id, preference_key) DO UPDATE SET preference_value = excluded.preference_value", (member_id, key, value))


def member_plan(member):
    plan = generate_workout(f'{member["equipment"]} {member["equipment_notes"]}', member["experience"], member["days"], f'{member["goal"]} {member["custom_goal"]}', member["training_style"], member["split_preference"], member["limitations"], member["session_minutes"], member["favorite_exercises"], member["avoid_exercises"], training_preferences_for(member["id"]))
    with db_connection() as connection:
        return apply_progression_states(plan, progression_states(connection, member["id"]))


def workout_set_targets(exercise):
    prescription = exercise["sets_reps"]
    count = int(re.search(r"(\d+)\s*(?:sets|rounds)", prescription, re.I).group(1)) if re.search(r"(\d+)\s*(?:sets|rounds)", prescription, re.I) else 3
    reps = re.search(r"(?:×\s*)([^·@]+)", prescription)
    weight = re.search(r"Target:\s*([\d.]+)\s*lb", prescription, re.I)
    rpe = re.search(r"RPE\s*([\d.]+)", prescription, re.I)
    rep_text = reps.group(1).strip() if reps else ""
    # A range such as 3–5 uses its top end as the deterministic progression target.
    rep_numbers = re.findall(r"\d+", rep_text)
    return count, (rep_numbers[-1] if rep_numbers else ""), (float(weight.group(1)) if weight else None), (float(rpe.group(1)) if rpe else None)


def warmup_targets(exercise_name, target_weight):
    """Conservative optional warm-ups for common loaded compound movements."""
    if not target_weight or not any(term in exercise_name.lower() for term in ("squat", "bench", "deadlift", "press", "row")):
        return []
    return [(round(target_weight * .5 / 5) * 5, "5"), (round(target_weight * .7 / 5) * 5, "3")]


def session_for_member(session_id, member_id):
    with db_connection() as connection:
        return connection.execute("SELECT * FROM workout_sessions WHERE id = ? AND member_id = ?", (session_id, member_id)).fetchone()


def persist_pr_events(connection, member_id, session_id, exercise_name, events, current_sets):
    """Store detector output once per session without reimplementing PR logic."""
    completed = [item for item in current_sets if item.get("actual_reps") is not None]
    weights = [item.get("actual_weight") for item in completed if item.get("actual_weight") is not None]
    best_weight = max(weights, default=None)
    reps_at_best_weight = max((item["actual_reps"] for item in completed if item.get("actual_weight") == best_weight), default=None)
    e1rm_values = [
        (item.get("actual_weight") or 0) * (1 + item["actual_reps"] / 30)
        for item in completed if item.get("actual_weight") is not None
    ]
    best_e1rm = round(max(e1rm_values), 1) if e1rm_values else None
    for event in events:
        value = event.current if event.current is not None else 0
        connection.execute(
            """INSERT OR IGNORE INTO personal_records
               (member_id, workout_session_id, exercise_name, pr_type, value, weight, reps, estimated_1rm)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (member_id, session_id, exercise_name, event.kind, value, best_weight, reps_at_best_weight, best_e1rm),
        )


def exercise_slug(name):
    """Produce stable, URL-safe exercise identifiers from library names."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def library_profile(member=None):
    """Use a signed-in athlete's constraints, with safe public defaults."""
    if not member:
        return UserProfile(
            goal=TrainingGoal.HYPERTROPHY,
            experience="intermediate",
            days_per_week=3,
            equipment="full gym",
        )
    unavailable = tuple(
        item.strip().lower() for item in member["equipment_notes"].split(",") if item.strip()
    )
    return UserProfile(
        goal=TrainingGoal.from_text(member["goal"]),
        experience=member["experience"],
        days_per_week=member["days"],
        equipment=f'{member["equipment"]} {member["equipment_notes"]}',
        limitations=member["limitations"],
        favorite_exercises=tuple(item.strip() for item in member["favorite_exercises"].split(",") if item.strip()),
        avoid_exercises=tuple(item.strip() for item in member["avoid_exercises"].split(",") if item.strip()),
    )


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


def readiness_values(form):
    """Validate the short, member-owned daily readiness check-in."""
    values = {
        "sleep_hours": float(form["sleep_hours"]),
        "sleep_quality": int(form["sleep_quality"]),
        "energy": int(form["energy"]),
        "soreness": int(form["soreness"]),
        "stress": int(form["stress"]),
        "motivation": int(form["motivation"]),
    }
    if not 0 <= values["sleep_hours"] <= 24 or any(not 1 <= values[key] <= 5 for key in values if key != "sleep_hours"):
        raise ValueError
    result = calculate_readiness(**values)
    return values, result, form.get("notes", "").strip()[:500]


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


@app.route("/health")
def health():
    try:
        with db_connection() as connection:
            connection.execute("SELECT 1").fetchone()
    except sqlite3.Error:
        app.logger.exception("Health check database failure")
        return {"status": "unavailable"}, 503
    return {"status": "ok"}


@app.route("/manifest.webmanifest")
def web_app_manifest():
    response = send_from_directory(app.static_folder, "manifest.webmanifest", mimetype="application/manifest+json")
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.route("/service-worker.js")
def service_worker():
    """Serve a versioned public-shell worker; it never caches member pages."""
    response = app.response_class(
        render_template("service-worker.js", asset_version=app.config["ASSET_VERSION"]),
        mimetype="application/javascript",
    )
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Service-Worker-Allowed"] = "/"
    return response


@app.route("/privacy")
def privacy():
    return render_template("legal.html", page="Privacy", content="SYLRIX stores the account, training, nutrition, progress, and photo information you choose to enter so it can provide member-specific features. Private beta data handling must be formally reviewed before any public or commercial launch.")


@app.route("/terms")
def terms():
    return render_template("legal.html", page="Terms", content="SYLRIX provides general fitness organization and educational guidance, not medical advice. This private-beta placeholder requires formal legal review before public or commercial use.")


@app.route("/")
def home():
    return render_template("home.html")

@app.route("/exercises")
def exercises():
    query = request.args.get("q", "").lower().strip()
    muscle = request.args.get("muscle", "").lower().strip()
    equipment = request.args.get("equipment", "").lower().strip()
    difficulty = request.args.get("difficulty", "").lower().strip()
    items = load_exercises()
    if query: items = [item for item in items if query in item.name.lower()]
    if muscle: items = [item for item in items if muscle in item.primary_muscles or muscle in item.secondary_muscles]
    if equipment: items = [item for item in items if item.equipment == equipment]
    if difficulty: items = [item for item in items if item.difficulty == difficulty]
    library = load_exercises()
    return render_template("exercises.html", exercises=items[:100], query=query, muscle=muscle, equipment=equipment, difficulty=difficulty, muscles=sorted({m for item in library for m in item.primary_muscles}), equipment_options=sorted({item.equipment for item in library}), difficulties=sorted({item.difficulty for item in library}), exercise_slug=exercise_slug, display_muscle=display_muscle)

@app.route("/exercises/<exercise_id>")
def exercise_detail(exercise_id):
    item = next((item for item in load_exercises() if exercise_slug(item.name) == exercise_id), None)
    if not item: abort(404)
    profile = library_profile(current_member())
    substitutes = find_substitutes(item, load_exercises(), profile.equipment, profile)
    return render_template("exercise_detail.html", exercise=item, substitutes=substitutes, display_muscle=display_muscle, diagram_regions=diagram_regions, exercise_slug=exercise_slug, signed_in=bool(current_member()))


@app.route("/training/<category>")
def training_category(category):
    details = TRAINING_CATEGORIES.get(category)
    if not details:
        abort(404)
    name, description, style = details
    return render_template("training_category.html", category=category, name=name, description=description, style=style, setup=CATEGORY_SETUP[category], member=current_member())


@app.route("/training/<category>/select", methods=["POST"])
def select_training_category(category):
    """Save only a known training path for an authenticated member."""
    if category not in TRAINING_CATEGORIES:
        abort(404)
    member = require_member()
    if not member:
        return redirect(url_for("register", style=category))
    with db_connection() as connection:
        connection.execute("UPDATE members SET training_style = ? WHERE id = ?", (category, member["id"]))
    flash(f"{TRAINING_CATEGORIES[category][0]} is now your active training path.")
    return redirect(url_for("plan"))


@app.route("/app")
def app_dashboard():
    member = current_member()
    if not member:
        return redirect(url_for("login"))
    with db_connection() as connection:
        nutrition = daily_nutrition(connection, member)
        recent_logs = connection.execute("SELECT * FROM workout_logs WHERE member_id = ? ORDER BY logged_on DESC, id DESC LIMIT 5", (member["id"],)).fetchall()
        today_steps = connection.execute("SELECT steps, goal FROM step_logs WHERE member_id = ? AND logged_on = ?", (member["id"], date.today().isoformat())).fetchone()
        active_session = connection.execute("SELECT * FROM workout_sessions WHERE member_id = ? AND status = 'active' ORDER BY started_at DESC, id DESC LIMIT 1", (member["id"],)).fetchone()
        recent_sessions = connection.execute("SELECT workout_name, workout_day, completed_at FROM workout_sessions WHERE member_id = ? AND status = 'completed' ORDER BY completed_at DESC, id DESC LIMIT 3", (member["id"],)).fetchall()
        latest_pr = connection.execute("SELECT exercise_name, pr_type, achieved_at FROM personal_records WHERE member_id = ? ORDER BY achieved_at DESC, id DESC LIMIT 1", (member["id"],)).fetchone()
        completed_this_week = connection.execute("SELECT COUNT(*) FROM workout_sessions WHERE member_id = ? AND status = 'completed' AND completed_at >= datetime('now', '-7 days')", (member["id"],)).fetchone()[0]
        latest_weight = connection.execute("SELECT weight, logged_on FROM body_weight_logs WHERE member_id=? ORDER BY logged_on DESC, id DESC LIMIT 1", (member["id"],)).fetchone()
        progression = connection.execute("SELECT exercise_name, recommended_weight, recommended_reps, progression_action FROM exercise_progression_state WHERE member_id=? ORDER BY updated_at DESC LIMIT 1", (member["id"],)).fetchone()
        readiness = readiness_for_today(connection, member["id"])
    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    readiness_recommendation = training_recommendation(readiness, completed_this_week, bool(progression))
    return render_template("dashboard.html", member=member, nutrition=nutrition, recent_logs=recent_logs, today_steps=today_steps, active_session=active_session, recent_sessions=recent_sessions, latest_pr=latest_pr, completed_this_week=completed_this_week, latest_weight=latest_weight, progression=progression, greeting=greeting, readiness=readiness, readiness_recommendation=readiness_recommendation)


@app.route("/app/readiness", methods=["GET", "POST"])
def readiness():
    member = require_member()
    if not member:
        return redirect(url_for("login"))
    if request.method == "POST":
        try:
            values, result, notes = readiness_values(request.form)
        except (KeyError, ValueError):
            flash("Use sleep from 0–24 hours and ratings from 1 to 5.")
        else:
            with db_connection() as connection:
                connection.execute(
                    """INSERT INTO daily_readiness (member_id, logged_on, sleep_hours, sleep_quality, energy, soreness, stress, motivation, notes, score, classification)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(member_id, logged_on) DO UPDATE SET sleep_hours=excluded.sleep_hours, sleep_quality=excluded.sleep_quality, energy=excluded.energy, soreness=excluded.soreness, stress=excluded.stress, motivation=excluded.motivation, notes=excluded.notes, score=excluded.score, classification=excluded.classification, updated_at=CURRENT_TIMESTAMP""",
                    (member["id"], date.today().isoformat(), values["sleep_hours"], values["sleep_quality"], values["energy"], values["soreness"], values["stress"], values["motivation"], notes, result.score, result.classification),
                )
            flash("Today’s readiness check-in is saved.")
        return redirect(url_for("readiness"))
    with db_connection() as connection:
        today_readiness = readiness_for_today(connection, member["id"])
        history = readiness_history(connection, member["id"])
        recent_completed = connection.execute("SELECT COUNT(*) FROM workout_sessions WHERE member_id=? AND status='completed' AND completed_at >= datetime('now', '-7 days')", (member["id"],)).fetchone()[0]
        progression = connection.execute("SELECT 1 FROM exercise_progression_state WHERE member_id=? LIMIT 1", (member["id"],)).fetchone()
    return render_template("readiness.html", member=member, readiness=today_readiness, history=history, recommendation=training_recommendation(today_readiness, recent_completed, bool(progression)))


@app.route("/register", methods=["GET", "POST"])
def register():
    requested_style = valid_training_style(request.args.get("style", "").strip())
    if requested_style:
        session["pending_training_style"] = requested_style
    if session.get("account_id"):
        return redirect(url_for("app_dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        invite_code = os.environ.get("SYLRIX_BETA_INVITE_CODE", "")
        submitted_code = request.form.get("invite_code", "")
        if app.config["BETA_MODE"] and (not invite_code or not submitted_code or not secrets.compare_digest(submitted_code, invite_code)):
            flash("A valid private-beta invite code is required to register.")
        elif len(username) < 3 or not username.replace("_", "").replace("-", "").isalnum():
            flash("Choose a username with 3+ letters, numbers, hyphens, or underscores.")
        elif "@" not in email or len(email) > 254:
            flash("Enter a valid email address.")
        elif len(password) < 12:
            flash("Use a password with at least 12 characters.")
        else:
            try:
                with db_connection() as connection:
                    cursor = connection.execute("INSERT INTO accounts (username, email, password_hash) VALUES (?, ?, ?)", (username, email, generate_password_hash(password)))
                    pending_style = valid_training_style(session.get("pending_training_style", ""))
                    session.clear()
                    session["account_id"] = cursor.lastrowid
                    if pending_style:
                        session["pending_training_style"] = pending_style
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
                return redirect(url_for("app_dashboard"))
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
        return redirect(url_for("app_dashboard"))
    if request.method == "POST":
        try:
            selected_style = valid_training_style(request.form.get("training_style", "") or session.get("pending_training_style", ""))
            values = {"name": request.form["name"].strip(), "age": int(request.form["age"]), "sex": request.form["sex"].lower(), "weight": float(request.form["weight"]), "height": float(request.form["height"]), "goal": request.form["goal"].lower(), "days": int(request.form["days"]), "equipment": request.form["equipment"].lower(), "experience": request.form["experience"].lower(), "custom_goal": request.form.get("custom_goal", "").strip()[:500], "training_style": selected_style, "split_preference": request.form.get("split_preference", "auto").strip()[:100], "equipment_notes": request.form.get("equipment_notes", "").strip()[:500], "limitations": request.form.get("limitations", "").strip()[:500], "session_minutes": int(request.form.get("session_minutes", 60)), "favorite_exercises": request.form.get("favorite_exercises", "").strip()[:300], "avoid_exercises": request.form.get("avoid_exercises", "").strip()[:300]}
            if not values["name"] or not 1 <= values["days"] <= 7 or values["age"] < 13 or not 20 <= values["session_minutes"] <= 120:
                raise ValueError
        except (KeyError, ValueError):
            flash("Please enter valid profile details. Training days must be from 1 to 7.")
            selected_style = valid_training_style(session.get("pending_training_style", ""))
            return render_template("onboarding.html", selected_training_style=selected_style, selected_setup=CATEGORY_SETUP.get(selected_style), training_fields=TRAINING_PREFERENCE_FIELDS.get(selected_style, ()))
        with db_connection() as connection:
            cursor = connection.execute("""INSERT INTO members (name, age, sex, weight, height, goal, days, equipment, experience, custom_goal, training_style, split_preference, equipment_notes, limitations, session_minutes, favorite_exercises, avoid_exercises)
                VALUES (:name, :age, :sex, :weight, :height, :goal, :days, :equipment, :experience, :custom_goal, :training_style, :split_preference, :equipment_notes, :limitations, :session_minutes, :favorite_exercises, :avoid_exercises)""", values)
            connection.execute("UPDATE accounts SET member_id = ? WHERE id = ?", (cursor.lastrowid, account["id"]))
        save_training_preferences(cursor.lastrowid, selected_style, request.form)
        flash("Your SYLRIX profile is ready.")
        session.pop("pending_training_style", None)
        return redirect(url_for("plan"))
    selected_style = valid_training_style(session.get("pending_training_style", ""))
    return render_template("onboarding.html", selected_training_style=selected_style, selected_setup=CATEGORY_SETUP.get(selected_style), training_fields=TRAINING_PREFERENCE_FIELDS.get(selected_style, ()))


@app.route("/plan")
def plan():
    member = require_member()
    if not member:
        return redirect(url_for("onboarding"))
    plan_goal = f'{member["goal"]} {member["custom_goal"]}'
    plan_equipment = f'{member["equipment"]} {member["equipment_notes"]}'
    preferences = training_preferences_for(member["id"])
    return render_template("plan.html", member=member, workout_plan=member_plan(member), training_preferences=preferences)


@app.route("/app/workouts")
def app_workouts():
    return redirect(url_for("plan"))


@app.route("/workout/<int:day_number>")
def active_workout(day_number):
    member = require_member()
    if not member:
        return redirect(url_for("onboarding"))
    plan = member_plan(member)
    workout = next((item for item in plan if item["day"] == day_number), None)
    if not workout:
        abort(404)
    with db_connection() as connection:
        active = connection.execute("SELECT * FROM workout_sessions WHERE member_id=? AND workout_day=? AND status='active' ORDER BY id DESC LIMIT 1", (member["id"], day_number)).fetchone()
        if not active:
            cursor = connection.execute("INSERT INTO workout_sessions (member_id, workout_name, workout_day, training_style) VALUES (?, ?, ?, ?)", (member["id"], workout["name"], day_number, member["training_style"]))
            session_id = cursor.lastrowid
            for order, exercise in enumerate(workout["exercises"], start=1):
                connection.execute("INSERT INTO session_exercises (session_id, exercise_order, original_exercise_name, exercise_name) VALUES (?, ?, ?, ?)", (session_id, order, exercise["name"], exercise["name"]))
                count, reps, weight, rpe = workout_set_targets(exercise)
                for warmup_number, (warmup_weight, warmup_reps) in enumerate(warmup_targets(exercise["name"], weight), start=1):
                    connection.execute("INSERT INTO workout_sets (session_id, exercise_name, exercise_order, set_number, target_reps, target_weight, is_warmup) VALUES (?, ?, ?, ?, ?, ?, 1)", (session_id, exercise["name"], order, -warmup_number, warmup_reps, warmup_weight))
                for set_number in range(1, count + 1):
                    connection.execute("INSERT INTO workout_sets (session_id, exercise_name, exercise_order, set_number, target_reps, target_weight, target_rpe) VALUES (?, ?, ?, ?, ?, ?, ?)", (session_id, exercise["name"], order, set_number, reps, weight, rpe))
            active = connection.execute("SELECT * FROM workout_sessions WHERE id=?", (session_id,)).fetchone()
        sets = connection.execute("SELECT * FROM workout_sets WHERE session_id=? AND skipped=0 ORDER BY exercise_order, is_warmup DESC, set_number", (active["id"],)).fetchall()
        overrides = connection.execute("SELECT * FROM session_exercises WHERE session_id=? ORDER BY exercise_order", (active["id"],)).fetchall()
        previous = connection.execute("SELECT exercise_name, actual_weight, actual_reps FROM workout_sets JOIN workout_sessions ON workout_sessions.id=workout_sets.session_id WHERE workout_sessions.member_id=? AND workout_sessions.status='completed' AND actual_reps IS NOT NULL ORDER BY workout_sets.id DESC", (member["id"],)).fetchall()
        readiness = readiness_for_today(connection, member["id"])
        recent_completed = connection.execute("SELECT COUNT(*) FROM workout_sessions WHERE member_id=? AND status='completed' AND completed_at >= datetime('now', '-7 days')", (member["id"],)).fetchone()[0]
        has_progression = connection.execute("SELECT 1 FROM exercise_progression_state WHERE member_id=? LIMIT 1", (member["id"],)).fetchone()
    by_exercise = {}
    for entry in sets: by_exercise.setdefault(entry["exercise_name"], []).append(entry)
    previous_by_exercise = {}
    for entry in previous:
        previous_by_exercise.setdefault(entry["exercise_name"], []).append(entry)
    for index, exercise in enumerate(workout["exercises"]):
        if index < len(overrides):
            exercise["original_name"] = overrides[index]["original_exercise_name"]
            exercise["name"] = overrides[index]["exercise_name"]
    completed_sets = sum(item["completed"] for item in sets if not item["is_warmup"])
    working_sets = sum(not item["is_warmup"] for item in sets)
    completed_exercises = len({item["exercise_order"] for item in sets if item["completed"] and not item["is_warmup"]})
    return render_template("active_workout.html", member=member, workout=workout, workout_session=active, sets_by_exercise=by_exercise, previous_by_exercise=previous_by_exercise, overrides=overrides, completed_sets=completed_sets, working_sets=working_sets, completed_exercises=completed_exercises, readiness=readiness, readiness_recommendation=training_recommendation(readiness, recent_completed, bool(has_progression)), exercise_slug=exercise_slug)


@app.route("/workout/session/<int:session_id>/readiness-adjustment", methods=["POST"])
def apply_readiness_adjustment(session_id):
    member = require_member()
    session_row = session_for_member(session_id, member["id"]) if member else None
    if not session_row or session_row["status"] != "active":
        abort(404)
    choice = request.form.get("choice", "")
    with db_connection() as connection:
        readiness = readiness_for_today(connection, member["id"])
        recent_completed = connection.execute("SELECT COUNT(*) FROM workout_sessions WHERE member_id=? AND status='completed' AND completed_at >= datetime('now', '-7 days')", (member["id"],)).fetchone()[0]
        has_progression = connection.execute("SELECT 1 FROM exercise_progression_state WHERE member_id=? LIMIT 1", (member["id"],)).fetchone()
        recommendation = training_recommendation(readiness, recent_completed, bool(has_progression))
        allowed = {"train_as_planned", recommendation["action"]}
        if choice not in allowed or not readiness:
            abort(400)
        if session_row["readiness_adjustment"]:
            flash("Today’s session adjustment was already selected.")
            return redirect(url_for("active_workout", day_number=session_row["workout_day"]))
        if choice == "reduce_load":
            rows = connection.execute("SELECT id, target_weight FROM workout_sets WHERE session_id=? AND is_warmup=0 AND skipped=0 AND completed=0 AND target_weight IS NOT NULL", (session_id,)).fetchall()
            for row in rows:
                connection.execute("UPDATE workout_sets SET target_weight=? WHERE id=?", (round(row["target_weight"] * .95 / 5) * 5, row["id"]))
        elif choice == "reduce_volume":
            rows = connection.execute("SELECT id, exercise_order FROM workout_sets WHERE session_id=? AND is_warmup=0 AND skipped=0 AND completed=0 ORDER BY exercise_order, set_number DESC", (session_id,)).fetchall()
            skipped_orders = set()
            for row in rows:
                if row["exercise_order"] not in skipped_orders:
                    connection.execute("UPDATE workout_sets SET skipped=1 WHERE id=?", (row["id"],))
                    skipped_orders.add(row["exercise_order"])
        connection.execute("UPDATE workout_sessions SET readiness_score=?, readiness_classification=?, readiness_adjustment=?, readiness_adjusted_at=CURRENT_TIMESTAMP WHERE id=?", (readiness["score"], readiness["classification"], choice, session_id))
    flash("Today’s session choice is saved. Your base plan is unchanged.")
    return redirect(url_for("active_workout", day_number=session_row["workout_day"]))


@app.route("/workout/session/<int:session_id>/exercise/<int:exercise_order>/replace", methods=["GET", "POST"])
def replace_session_exercise(session_id, exercise_order):
    member = require_member()
    session_row = session_for_member(session_id, member["id"]) if member else None
    if not session_row or session_row["status"] != "active": abort(404)
    with db_connection() as connection:
        current = connection.execute("SELECT * FROM session_exercises WHERE session_id=? AND exercise_order=?", (session_id, exercise_order)).fetchone()
    if not current: abort(404)
    library = load_exercises()
    source = next((item for item in library if item.name == current["exercise_name"]), None)
    if not source: abort(404)
    profile = library_profile(member)
    choices = find_substitutes(source, library, profile.equipment, profile)
    if request.method == "POST":
        selected = request.form.get("exercise", "")
        if selected not in {choice.exercise.name for choice in choices}: abort(400)
        with db_connection() as connection:
            connection.execute("UPDATE session_exercises SET exercise_name=?, replaced=1 WHERE session_id=? AND exercise_order=?", (selected, session_id, exercise_order))
            connection.execute("UPDATE workout_sets SET exercise_name=? WHERE session_id=? AND exercise_order=?", (selected, session_id, exercise_order))
        return redirect(url_for("active_workout", day_number=session_row["workout_day"]))
    return render_template("replace_exercise.html", workout_session=session_row, current=current, choices=choices)


@app.route("/workout/session/<int:session_id>/set/<int:set_id>", methods=["POST"])
def save_workout_set(session_id, set_id):
    member = require_member()
    session_row = session_for_member(session_id, member["id"]) if member else None
    if not session_row or session_row["status"] != "active":
        abort(404)
    try:
        weight = request.form.get("weight", "").strip()
        reps = int(request.form["reps"])
        rpe = request.form.get("rpe", "").strip()
        if reps < 0 or reps > 1000: raise ValueError
        weight = float(weight) if weight else None
        rpe = float(rpe) if rpe else None
    except (KeyError, ValueError):
        flash("Use valid weight, reps, and RPE values.")
        return redirect(request.referrer or url_for("app_dashboard"))
    with db_connection() as connection:
        changed = connection.execute("UPDATE workout_sets SET actual_weight=?, actual_reps=?, actual_rpe=?, completed=1 WHERE id=? AND session_id=? AND skipped=0", (weight, reps, rpe, set_id, session_id)).rowcount
    if not changed: abort(404)
    return redirect(request.referrer or url_for("app_dashboard"))


@app.route("/workout/session/<int:session_id>/exercise/<int:exercise_order>/note", methods=["POST"])
def save_exercise_note(session_id, exercise_order):
    member = require_member()
    session_row = session_for_member(session_id, member["id"]) if member else None
    if not session_row or session_row["status"] != "active": abort(404)
    with db_connection() as connection:
        changed = connection.execute("UPDATE session_exercises SET notes=? WHERE session_id=? AND exercise_order=?", (request.form.get("notes", "").strip()[:1000], session_id, exercise_order)).rowcount
    if not changed: abort(404)
    return redirect(url_for("active_workout", day_number=session_row["workout_day"]))


@app.route("/workout/session/<int:session_id>/finish", methods=["POST"])
def finish_workout(session_id):
    member = require_member()
    session_row = session_for_member(session_id, member["id"]) if member else None
    if not session_row: abort(404)
    with db_connection() as connection:
        incomplete = connection.execute("SELECT COUNT(*) FROM workout_sets WHERE session_id=? AND completed=0 AND is_warmup=0 AND skipped=0", (session_id,)).fetchone()[0]
        if incomplete and request.form.get("confirm") != "finish":
            flash(f"{incomplete} set(s) are unfinished. Confirm finishing to save anyway.")
            return redirect(url_for("active_workout", day_number=session_row["workout_day"]))
        current_sets = connection.execute("SELECT * FROM workout_sets WHERE session_id=? AND completed=1 AND is_warmup=0 AND skipped=0 ORDER BY exercise_order, set_number", (session_id,)).fetchall()
        historical_sets = connection.execute("SELECT workout_sets.* FROM workout_sets JOIN workout_sessions ON workout_sessions.id=workout_sets.session_id WHERE workout_sessions.member_id=? AND workout_sessions.status='completed' AND workout_sessions.id != ? AND workout_sets.is_warmup=0 AND workout_sets.skipped=0", (member["id"], session_id)).fetchall()
        recommendations, pr_events = [], []
        for name in sorted({item["exercise_name"] for item in current_sets}):
            current = [dict(item) for item in current_sets if item["exercise_name"] == name]
            historical = [dict(item) for item in historical_sets if item["exercise_name"] == name]
            target = next((item["target_reps"] for item in current_sets if item["exercise_name"] == name), "5")
            recommendation = recommendation_for_session(connection, member["id"], session_id, name, current, f"3 sets × {target} reps", session_row["training_style"])
            save_progression_state(connection, member["id"], session_id, name, recommendation, current)
            recommendations.append((name, recommendation))
            exercise_events = detect_prs(name, current, historical)
            persist_pr_events(connection, member["id"], session_id, name, exercise_events, current)
            pr_events.extend(exercise_events)
        connection.execute("UPDATE workout_sessions SET status='completed', completed_at=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
        summary = connection.execute("SELECT COUNT(*) sets_completed, COUNT(DISTINCT exercise_order) exercises_completed, COALESCE(SUM(actual_weight * actual_reps),0) volume FROM workout_sets WHERE session_id=? AND completed=1 AND is_warmup=0 AND skipped=0", (session_id,)).fetchone()
    try:
        duration_seconds = max(0, int((datetime.now() - datetime.fromisoformat(session_row["started_at"])).total_seconds()))
    except (TypeError, ValueError):
        duration_seconds = 0
    return render_template("workout_complete.html", workout_session=session_row, summary=summary, recommendations=recommendations, pr_events=pr_events, duration_seconds=duration_seconds)


@app.route("/history")
def workout_history():
    member = require_member()
    if not member: return redirect(url_for("login"))
    with db_connection() as connection:
        sessions = connection.execute("SELECT workout_sessions.*, COUNT(workout_sets.id) set_count, COALESCE(SUM(workout_sets.actual_weight * workout_sets.actual_reps),0) volume FROM workout_sessions LEFT JOIN workout_sets ON workout_sets.session_id=workout_sessions.id AND workout_sets.skipped=0 WHERE workout_sessions.member_id=? AND workout_sessions.status='completed' GROUP BY workout_sessions.id ORDER BY workout_sessions.completed_at DESC", (member["id"],)).fetchall()
    return render_template("history.html", sessions=sessions)


@app.route("/history/<int:session_id>")
def workout_history_detail(session_id):
    member = require_member()
    session_row = session_for_member(session_id, member["id"]) if member else None
    if not session_row or session_row["status"] != "completed": abort(404)
    with db_connection() as connection:
        entries = connection.execute("SELECT * FROM workout_sets WHERE session_id=? AND completed=1 AND skipped=0 ORDER BY exercise_order, set_number", (session_id,)).fetchall()
    return render_template("history_detail.html", workout_session=session_row, entries=entries)


@app.route("/progress/exercise/<path:exercise_name>")
def exercise_progress(exercise_name):
    """A member-owned view of the data behind one exercise recommendation."""
    member = require_member()
    if not member:
        return redirect(url_for("login"))
    with db_connection() as connection:
        state = progression_state(connection, member["id"], exercise_name)
        sessions = connection.execute(
            """SELECT workout_sessions.completed_at, workout_sets.actual_weight, workout_sets.actual_reps,
                      workout_sets.actual_rpe, workout_sets.set_number
               FROM workout_sets JOIN workout_sessions ON workout_sessions.id=workout_sets.session_id
               WHERE workout_sessions.member_id=? AND workout_sessions.status='completed'
                 AND lower(workout_sets.exercise_name)=lower(?) AND workout_sets.completed=1
               ORDER BY workout_sessions.completed_at DESC, workout_sets.id DESC LIMIT 30""",
            (member["id"], exercise_name),
        ).fetchall()
        records = connection.execute(
            "SELECT pr_type, value, weight, reps, estimated_1rm, achieved_at FROM personal_records WHERE member_id=? AND lower(exercise_name)=lower(?) ORDER BY achieved_at DESC, id DESC LIMIT 10",
            (member["id"], exercise_name),
        ).fetchall()
    return render_template("exercise_progress.html", exercise_name=exercise_name, state=state, sessions=sessions, records=records)


@app.route("/app/profile", methods=["GET", "POST"])
def app_profile():
    member = require_member()
    if not member:
        return redirect(url_for("onboarding"))
    if request.method == "POST":
        action = request.form.get("action")
        if action == "reset_setup" and request.form.get("confirm") == "RESET":
            with db_connection() as connection:
                connection.execute("UPDATE accounts SET member_id = NULL WHERE member_id = ?", (member["id"],))
                connection.execute("DELETE FROM members WHERE id = ?", (member["id"],))
            flash("Your fitness setup was cleared. Your account remains active.")
            return redirect(url_for("onboarding"))
        if action == "save":
            try:
                style = valid_training_style(request.form.get("training_style", ""))
                name = request.form["name"].strip()[:100]
                username = request.form["username"].strip()[:30]
                current_weight = float(request.form["weight"])
                goal_weight_text = request.form.get("goal_weight", "").strip()
                goal_weight = float(goal_weight_text) if goal_weight_text else None
                values = (name, current_weight, goal_weight, request.form["goal"].lower(), style, request.form["experience"].lower(), int(request.form["days"]), int(request.form["session_minutes"]), request.form["equipment"].lower(), request.form.get("favorite_exercises", "")[:300], request.form.get("avoid_exercises", "")[:300], member["id"])
                if not name or len(username) < 3 or not username.replace("_", "").replace("-", "").isalnum() or not 70 <= current_weight <= 700 or (goal_weight is not None and not 70 <= goal_weight <= 700) or not 1 <= values[6] <= 7 or not 20 <= values[7] <= 120:
                    raise ValueError
            except (KeyError, ValueError):
                flash("Use a valid name, username, weights, training days, and session duration.")
            else:
                try:
                    with db_connection() as connection:
                        connection.execute("UPDATE members SET name=?, weight=?, goal_weight=?, goal=?, training_style=?, experience=?, days=?, session_minutes=?, equipment=?, favorite_exercises=?, avoid_exercises=? WHERE id=?", values)
                        connection.execute("UPDATE accounts SET username=? WHERE id=?", (username, session["account_id"]))
                    flash("Profile saved. Your next plan uses these settings.")
                except sqlite3.IntegrityError:
                    flash("That username is already in use.")
            return redirect(url_for("app_profile"))
    return render_template("profile.html", member=member, account=current_account())


@app.route("/app/coach", methods=["GET", "POST"])
def coach():
    member = require_member()
    if not member:
        return redirect(url_for("login"))
    # Bind Coach to this authenticated member once; the model never supplies IDs.
    service = CoachService(DATABASE, member["id"])
    if request.method == "POST" and request.form.get("message", "").strip():
        message = request.form["message"].strip()[:2000]
        with db_connection() as connection:
            connection.execute("INSERT INTO coach_messages (member_id, role, message) VALUES (?, 'user', ?)", (member["id"], message))
        answer = service.reply(message)
        with db_connection() as connection:
            connection.execute("INSERT INTO coach_messages (member_id, role, message) VALUES (?, 'assistant', ?)", (member["id"], answer))
    with db_connection() as connection:
        messages = connection.execute("SELECT role, message, created_at FROM coach_messages WHERE member_id=? ORDER BY id DESC LIMIT 30", (member["id"],)).fetchall()
    return render_template("coach.html", messages=reversed(messages), configured=service.configured, local_mode=service.local_mode, model=MODEL)


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


@app.route("/nutrition", methods=["GET", "POST"])
def nutrition():
    member = require_member()
    if not member:
        return redirect(url_for("onboarding"))
    selected_date = request.values.get("date", date.today().isoformat())
    try:
        selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date().isoformat()
    except ValueError:
        selected_date = date.today().isoformat()
    if request.method == "POST":
        try:
            food_name, serving, values, logged_on = nutrition_values(request.form)
        except (TypeError, ValueError):
            flash("Enter a food and valid non-negative nutrition values.")
        else:
            with db_connection() as connection:
                connection.execute("INSERT INTO nutrition_logs (member_id, food_name, serving, calories, protein, carbs, fat, fiber, logged_on) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (member["id"], food_name, serving, values["calories"], values["protein"], values["carbs"], values["fat"], values["fiber"], logged_on))
            flash("Food entry saved.")
        return redirect(url_for("nutrition", date=selected_date))
    with db_connection() as connection:
        summary = daily_nutrition(connection, member, selected_date)
        entries = connection.execute("SELECT * FROM nutrition_logs WHERE member_id=? AND logged_on=? ORDER BY id DESC", (member["id"], selected_date)).fetchall()
        foods = recent_foods(connection, member["id"])
        days = connection.execute("SELECT logged_on, COUNT(*) entry_count FROM nutrition_logs WHERE member_id=? GROUP BY logged_on ORDER BY logged_on DESC LIMIT 7", (member["id"],)).fetchall()
    return render_template("nutrition.html", member=member, summary=summary, entries=entries, recent_foods=foods, recent_days=days, selected_date=selected_date)


@app.route("/nutrition/<int:entry_id>/edit", methods=["POST"])
def edit_nutrition(entry_id):
    member = require_member()
    if not member: return redirect(url_for("login"))
    try:
        food_name, serving, values, logged_on = nutrition_values(request.form)
    except (TypeError, ValueError):
        flash("Enter a food and valid non-negative nutrition values.")
    else:
        with db_connection() as connection:
            changed = connection.execute("UPDATE nutrition_logs SET food_name=?, serving=?, calories=?, protein=?, carbs=?, fat=?, fiber=?, logged_on=? WHERE id=? AND member_id=?", (food_name, serving, values["calories"], values["protein"], values["carbs"], values["fat"], values["fiber"], logged_on, entry_id, member["id"])).rowcount
        if not changed: abort(404)
        flash("Food entry updated.")
    return redirect(url_for("nutrition", date=request.form.get("logged_on", date.today().isoformat())))


@app.route("/nutrition/<int:entry_id>/delete", methods=["POST"])
def delete_nutrition(entry_id):
    member = require_member()
    if not member: return redirect(url_for("login"))
    with db_connection() as connection:
        changed = connection.execute("DELETE FROM nutrition_logs WHERE id=? AND member_id=?", (entry_id, member["id"])).rowcount
    if not changed: abort(404)
    flash("Food entry deleted.")
    return redirect(url_for("nutrition", date=request.form.get("logged_on", date.today().isoformat())))


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
@app.route("/app/progress", methods=["GET", "POST"])
def progress():
    member = require_member()
    if not member:
        return redirect(url_for("onboarding"))
    if request.method == "POST":
        photo = request.files.get("photo")
        if not photo or not photo.filename or not image_allowed(photo.filename) or not image_is_valid(photo):
            app.logger.warning("Rejected progress photo upload")
            flash("Upload a valid PNG, JPG, JPEG, or WEBP image.")
            return redirect(url_for("progress"))
        filename = f"{uuid.uuid4().hex}_{secure_filename(photo.filename)}"
        try:
            photo.save(UPLOAD_DIR / filename)
        except OSError:
            app.logger.exception("Progress photo storage failure")
            flash("Your photo could not be saved. Please try again.")
            return redirect(url_for("progress"))
        with db_connection() as connection:
            connection.execute("INSERT INTO progress_photos (member_id, filename, caption, uploaded_on) VALUES (?, ?, ?, ?)", (member["id"], filename, request.form.get("caption", "").strip(), date.today().isoformat()))
        flash("Progress photo saved.")
        return redirect(url_for("progress"))
    with db_connection() as connection:
        photos = connection.execute("SELECT * FROM progress_photos WHERE member_id = ? ORDER BY uploaded_on DESC, id DESC", (member["id"],)).fetchall()
        weight_logs = connection.execute("SELECT * FROM body_weight_logs WHERE member_id = ? ORDER BY logged_on DESC, id DESC", (member["id"],)).fetchall()
    chronological_weights = list(reversed(weight_logs))
    current_weight = weight_logs[0]["weight"] if weight_logs else member["weight"]
    starting_weight = chronological_weights[0]["weight"] if chronological_weights else member["weight"]
    return render_template("progress.html", member=member, photos=photos, weight_logs=weight_logs, current_weight=current_weight, starting_weight=starting_weight, weight_change=round(current_weight - starting_weight, 1), weight_chart=[{"date": item["logged_on"], "weight": item["weight"]} for item in chronological_weights], today=date.today().isoformat())


def weight_log_values(form):
    """Validate the small, member-owned body-weight log payload."""
    weight = float(form["weight"])
    logged_on = datetime.strptime(form.get("logged_on", date.today().isoformat()), "%Y-%m-%d").date().isoformat()
    if not 70 <= weight <= 700:
        raise ValueError
    return weight, logged_on


@app.route("/progress/weight", methods=["POST"])
def add_body_weight():
    member = require_member()
    if not member:
        return redirect(url_for("login"))
    try:
        weight, logged_on = weight_log_values(request.form)
    except (KeyError, ValueError):
        flash("Enter a body weight between 70 and 700 lb and a valid date.")
    else:
        with db_connection() as connection:
            connection.execute("INSERT INTO body_weight_logs (member_id, weight, logged_on) VALUES (?, ?, ?) ON CONFLICT(member_id, logged_on) DO UPDATE SET weight=excluded.weight", (member["id"], weight, logged_on))
            latest = connection.execute("SELECT weight FROM body_weight_logs WHERE member_id=? ORDER BY logged_on DESC, id DESC LIMIT 1", (member["id"],)).fetchone()
            connection.execute("UPDATE members SET weight=? WHERE id=?", (latest["weight"], member["id"]))
        flash("Body weight saved.")
    return redirect(url_for("progress"))


@app.route("/progress/weight/<int:log_id>/edit", methods=["POST"])
def edit_body_weight(log_id):
    member = require_member()
    if not member:
        return redirect(url_for("login"))
    try:
        weight, logged_on = weight_log_values(request.form)
    except (KeyError, ValueError):
        flash("Enter a body weight between 70 and 700 lb and a valid date.")
        return redirect(url_for("progress"))
    try:
        with db_connection() as connection:
            changed = connection.execute("UPDATE body_weight_logs SET weight=?, logged_on=? WHERE id=? AND member_id=?", (weight, logged_on, log_id, member["id"])).rowcount
            latest = connection.execute("SELECT weight FROM body_weight_logs WHERE member_id=? ORDER BY logged_on DESC, id DESC LIMIT 1", (member["id"],)).fetchone()
            if latest:
                connection.execute("UPDATE members SET weight=? WHERE id=?", (latest["weight"], member["id"]))
        if not changed:
            abort(404)
    except sqlite3.IntegrityError:
        flash("You already have a body-weight entry for that date.")
    else:
        flash("Body weight entry updated.")
    return redirect(url_for("progress"))


@app.route("/progress/weight/<int:log_id>/delete", methods=["POST"])
def delete_body_weight(log_id):
    member = require_member()
    if not member:
        return redirect(url_for("login"))
    with db_connection() as connection:
        changed = connection.execute("DELETE FROM body_weight_logs WHERE id=? AND member_id=?", (log_id, member["id"])).rowcount
        latest = connection.execute("SELECT weight FROM body_weight_logs WHERE member_id=? ORDER BY logged_on DESC, id DESC LIMIT 1", (member["id"],)).fetchone()
        if latest:
            connection.execute("UPDATE members SET weight=? WHERE id=?", (latest["weight"], member["id"]))
    if not changed:
        abort(404)
    flash("Body weight entry deleted.")
    return redirect(url_for("progress"))


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
    try:
        selected_date = datetime.strptime(request.args.get("date", date.today().isoformat()), "%Y-%m-%d").date()
    except ValueError:
        selected_date = date.today()
    return render_template("daily.html", workout=generate_daily_workout_for_level(experience, selected_date), selected_date=selected_date, week=weekly_daily_schedule(selected_date))


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.")
    return redirect(url_for("home"))


@app.errorhandler(413)
def too_large(_error):
    flash("Images must be 8 MB or smaller.")
    return redirect(url_for("progress"))


@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(429)
@app.errorhandler(500)
def branded_error(error):
    if getattr(error, "code", 500) == 500:
        app.logger.exception("Unhandled application error")
    return render_template("error.html", code=getattr(error, "code", 500)), getattr(error, "code", 500)


setup_database()

if __name__ == "__main__":
    if is_production:
        raise RuntimeError("Use Gunicorn in production: gunicorn wsgi:app")
    app.run(debug=os.environ.get("SYLRIX_DEBUG", "0") == "1", port=int(os.environ.get("PORT", 5001)))
