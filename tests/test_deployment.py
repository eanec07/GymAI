import tempfile
import unittest
import sqlite3
from datetime import date
from pathlib import Path
from unittest.mock import patch

import app as sylrix


class DeploymentReadinessTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.original_database = sylrix.DATABASE
        self.original_csrf = sylrix.csrf_enabled
        self.original_beta = sylrix.app.config["BETA_MODE"]
        sylrix.DATABASE = Path(self.directory.name) / "deployment.db"
        sylrix.setup_database()
        self.client = sylrix.app.test_client()

    def tearDown(self):
        sylrix.DATABASE = self.original_database
        sylrix.csrf_enabled = self.original_csrf
        sylrix.app.config["BETA_MODE"] = self.original_beta
        self.directory.cleanup()

    def test_health_and_branded_not_found_are_safe(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})
        missing = self.client.get("/not-a-route")
        self.assertEqual(missing.status_code, 404)
        self.assertIn(b"This page is not here", missing.data)
        self.assertNotIn(b"Traceback", missing.data)

    def test_shared_shell_versions_authoritative_stylesheets(self):
        page = self.client.get("/")
        self.assertIn(b"sylrix-fit.css?v=", page.data)
        asset = self.client.get("/static/sylrix-fit.css")
        self.assertEqual(asset.status_code, 200)
        asset.close()

    def test_csrf_rejects_missing_token_and_accepts_rendered_token(self):
        sylrix.csrf_enabled = True
        self.assertEqual(self.client.post("/register", data={}).status_code, 403)
        self.assertEqual(self.client.get("/register").status_code, 200)
        with self.client.session_transaction() as session:
            token = session["csrf_token"]
        response = self.client.post("/register", data={
            "csrf_token": token,
            "username": "beta_member",
            "email": "member@example.test",
            "password": "safe-password-123",
        })
        self.assertEqual(response.status_code, 302)

    def test_beta_mode_requires_configured_invite(self):
        sylrix.csrf_enabled = False
        sylrix.app.config["BETA_MODE"] = True
        with patch.dict("os.environ", {"SYLRIX_BETA_INVITE_CODE": "invite-only"}):
            denied = self.client.post("/register", data={"username": "beta_member", "email": "member@example.test", "password": "safe-password-123"})
            self.assertEqual(denied.status_code, 200)
            self.assertIn(b"invite code", denied.data)
            allowed = self.client.post("/register", data={"invite_code": "invite-only", "username": "beta_member", "email": "member@example.test", "password": "safe-password-123"})
        self.assertEqual(allowed.status_code, 302)

    def test_additive_migrations_upgrade_an_older_schema(self):
        legacy_database = Path(self.directory.name) / "legacy.db"
        legacy_connection = sqlite3.connect(legacy_database)
        try:
            db = legacy_connection
            db.executescript("""
                CREATE TABLE members (id INTEGER PRIMARY KEY, name TEXT NOT NULL, age INTEGER NOT NULL, sex TEXT NOT NULL, weight REAL NOT NULL, height REAL NOT NULL, goal TEXT NOT NULL, days INTEGER NOT NULL, equipment TEXT NOT NULL, experience TEXT NOT NULL);
                CREATE TABLE workout_sessions (id INTEGER PRIMARY KEY, member_id INTEGER NOT NULL, workout_name TEXT NOT NULL, workout_day INTEGER NOT NULL, training_style TEXT NOT NULL DEFAULT '', started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, completed_at TEXT, status TEXT NOT NULL DEFAULT 'active');
                CREATE TABLE workout_sets (id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL, exercise_name TEXT NOT NULL, exercise_order INTEGER NOT NULL, set_number INTEGER NOT NULL, target_reps TEXT, target_weight REAL, target_rpe REAL, actual_weight REAL, actual_reps INTEGER, actual_rpe REAL, completed INTEGER NOT NULL DEFAULT 0, notes TEXT NOT NULL DEFAULT '', is_warmup INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE session_exercises (id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL, exercise_order INTEGER NOT NULL, original_exercise_name TEXT NOT NULL, exercise_name TEXT NOT NULL, replaced INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE nutrition_logs (id INTEGER PRIMARY KEY, member_id INTEGER NOT NULL, food_name TEXT NOT NULL, calories REAL NOT NULL DEFAULT 0, protein REAL NOT NULL DEFAULT 0, carbs REAL NOT NULL DEFAULT 0, fat REAL NOT NULL DEFAULT 0, fiber REAL NOT NULL DEFAULT 0, logged_on TEXT NOT NULL);
            """)
            legacy_connection.commit()
        finally:
            legacy_connection.close()
        original = sylrix.DATABASE
        try:
            sylrix.DATABASE = legacy_database
            sylrix.setup_database()
            with sylrix.db_connection() as db:
                session_columns = {row[1] for row in db.execute("PRAGMA table_info(workout_sessions)")}
                set_columns = {row[1] for row in db.execute("PRAGMA table_info(workout_sets)")}
                nutrition_columns = {row[1] for row in db.execute("PRAGMA table_info(nutrition_logs)")}
                self.assertIn("daily_readiness", {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")})
            self.assertTrue({"readiness_score", "readiness_classification", "readiness_adjustment"} <= session_columns)
            self.assertIn("skipped", set_columns)
            self.assertIn("serving", nutrition_columns)
        finally:
            sylrix.DATABASE = original

    def test_new_member_core_journey_persists_after_relogin(self):
        today = date.today().isoformat()
        self.assertEqual(self.client.post("/register", data={
            "username": "beta_lifter", "email": "beta@example.test", "password": "safe-password-123",
        }).status_code, 302)
        self.assertEqual(self.client.post("/onboarding", data={
            "name": "Beta Lifter", "age": "30", "sex": "male", "weight": "180", "height": "70",
            "goal": "strength", "days": "3", "equipment": "full gym", "experience": "beginner",
            "training_style": "strength", "session_minutes": "60",
        }).status_code, 302)
        self.assertEqual(self.client.get("/app").status_code, 200)
        self.assertEqual(self.client.post("/app/readiness", data={
            "sleep_hours": "7", "sleep_quality": "3", "energy": "3", "soreness": "3", "stress": "3", "motivation": "3",
        }).status_code, 302)
        self.assertEqual(self.client.post("/nutrition", data={
            "food_name": "Breakfast", "serving": "1 meal", "calories": "500", "protein": "30", "carbs": "50", "fat": "12", "fiber": "8", "logged_on": today,
        }).status_code, 302)
        self.assertEqual(self.client.post("/progress/weight", data={"weight": "179.5", "logged_on": today}).status_code, 302)
        self.assertEqual(self.client.post("/steps", data={"steps": "8000", "goal": "8000"}).status_code, 302)
        self.assertEqual(self.client.get("/workout/1").status_code, 200)
        with sylrix.db_connection() as db:
            session = db.execute("SELECT * FROM workout_sessions WHERE status='active'").fetchone()
            working_set = db.execute("SELECT id FROM workout_sets WHERE session_id=? AND is_warmup=0 LIMIT 1", (session["id"],)).fetchone()["id"]
        self.assertEqual(self.client.post(f"/workout/session/{session['id']}/set/{working_set}", data={"weight": "45", "reps": "8", "rpe": "7"}).status_code, 302)
        self.assertEqual(self.client.post(f"/workout/session/{session['id']}/exercise/1/note", data={"notes": "Good setup"}).status_code, 302)
        self.assertEqual(self.client.post(f"/workout/session/{session['id']}/finish", data={"confirm": "finish"}).status_code, 200)
        self.assertEqual(self.client.post("/app/coach", data={"message": "What should I train today?"}).status_code, 200)
        self.assertEqual(self.client.get("/logout").status_code, 302)
        self.assertEqual(self.client.post("/login", data={"identity": "beta_lifter", "password": "safe-password-123"}).status_code, 302)
        dashboard = self.client.get("/app")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"Breakfast", self.client.get(f"/nutrition?date={today}").data)
        self.assertIn(b"Beta Lifter", dashboard.data)


if __name__ == "__main__":
    unittest.main()
