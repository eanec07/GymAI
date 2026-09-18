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

    def test_public_version_marker_is_non_sensitive_and_matches_assets(self):
        response = self.client.get("/version")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"app": "SYLRIX.FIT", "build": sylrix.app.config["ASSET_VERSION"]})
        self.assertEqual(response.headers["Cache-Control"], "no-cache")
        page = self.client.get("/")
        self.assertIn(f"Build {sylrix.app.config['ASSET_VERSION']}".encode(), page.data)

    def test_shared_shell_versions_authoritative_stylesheets(self):
        page = self.client.get("/")
        self.assertIn(b"sylrix-fit.css?v=", page.data)
        asset = self.client.get("/static/sylrix-fit.css")
        self.assertEqual(asset.status_code, 200)
        asset.close()

    def test_pwa_public_shell_never_caches_member_pages(self):
        page = self.client.get("/")
        self.assertIn(b'rel="manifest"', page.data)
        self.assertIn(b"pwa.js?v=", page.data)
        self.assertIn(b"mobile-nav.js?v=", page.data)
        manifest = self.client.get("/manifest.webmanifest")
        self.assertEqual(manifest.status_code, 200)
        self.assertEqual(manifest.get_json()["display"], "standalone")
        manifest.close()
        worker = self.client.get("/service-worker.js")
        self.assertEqual(worker.status_code, 200)
        self.assertIn(b"sylrix-public-", worker.data)
        self.assertIn(b"/static/offline.html", worker.data)
        self.assertNotIn(b"'/app'", worker.data)
        self.assertIn(b"fetch(request).then(response", worker.data)
        self.assertNotIn(b"caches.match(request, {ignoreSearch", worker.data)
        offline = self.client.get("/static/offline.html")
        self.assertEqual(offline.status_code, 200)
        self.assertIn(b"Connection required", offline.data)
        offline.close()

    def test_mobile_shell_keeps_portrait_navigation_and_pwa_product_name(self):
        page = self.client.get("/")
        self.assertIn(b'<meta name="viewport" content="width=device-width, initial-scale=1">', page.data)
        self.assertIn(b'aria-controls="site-navigation"', page.data)
        self.assertIn(b'id="mobile-menu-toggle"', page.data)
        self.assertIn(b"try { localStorage.setItem('sylrix-language'", page.data)
        self.assertNotIn(b"closeNavigation", page.data)
        page.close()
        manifest_response = self.client.get("/manifest.webmanifest")
        manifest = manifest_response.get_json()
        manifest_response.close()
        self.assertEqual(manifest["name"], "SYLRIX.FIT")
        self.assertEqual(manifest["short_name"], "SYLRIX.FIT")
        self.assertEqual(manifest["orientation"], "any")

        product_response = self.client.get("/static/sylrix-fit.css")
        product_css = product_response.get_data(as_text=True)
        product_response.close()
        self.assertIn("Portrait-first shell", product_css)
        self.assertIn(".nav-links.open{display:flex!important}", product_css)
        self.assertIn("position:fixed!important", product_css)
        self.assertIn("body.nav-open{overflow:hidden}", product_css)
        self.assertIn(".active-workout-screen .set-row{grid-template-columns:repeat(3,minmax(0,1fr)) auto!important", product_css)
        training_response = self.client.get("/static/training-cards.css")
        training_css = training_response.get_data(as_text=True)
        training_response.close()
        self.assertIn(".training-card-overlay", training_css)
        self.assertIn(".training-card--powerlifting img", training_css)

        mobile_nav = self.client.get("/static/mobile-nav.js")
        self.assertEqual(mobile_nav.status_code, 200)
        self.assertIn(b"mobile-nav-ready", mobile_nav.data)
        self.assertIn(b"aria-expanded", mobile_nav.data)
        self.assertIn(b"event.key === 'Escape'", mobile_nav.data)
        self.assertNotIn(b"localStorage", mobile_nav.data)
        mobile_nav.close()

    def test_every_training_style_has_portrait_cover_and_focal_position(self):
        response = self.client.get("/static/training-cards.css")
        stylesheet = response.get_data(as_text=True)
        response.close()
        self.assertIn("object-fit:cover", stylesheet)
        self.assertIn("@media(max-width:600px)", stylesheet)
        for style in ("strength", "bodybuilding", "calisthenics", "endurance", "general-fitness", "powerbuilding", "powerlifting", "crossfit"):
            self.assertIn(f".training-card--{style} img{{object-position:", stylesheet)

    def test_landing_uses_distinct_approved_brand_adjacent_photography(self):
        stylesheet_response = self.client.get("/static/marketing.css")
        stylesheet = stylesheet_response.get_data(as_text=True)
        stylesheet_response.close()
        self.assertIn("sylrix-hero-redhead-v1.png", stylesheet)
        self.assertIn("sylrix-latina-row-v1.png", stylesheet)
        for path in ("/static/assets/sylrix-hero-redhead-v1.png", "/static/assets/sylrix-latina-row-v1.png"):
            asset = self.client.get(path)
            self.assertEqual(asset.status_code, 200, path)
            self.assertEqual(asset.mimetype, "image/png")
            asset.close()

    def test_coach_styles_use_the_sylrix_palette(self):
        stylesheet_response = self.client.get("/static/app-screens.css")
        stylesheet = stylesheet_response.get_data(as_text=True)
        stylesheet_response.close()
        self.assertIn("#0B0B0B", stylesheet)
        self.assertIn("#1A1E26", stylesheet)
        self.assertIn("#C0C0C0", stylesheet)
        self.assertIn("#E53935", stylesheet)
        self.assertNotIn("#d8ff75", stylesheet.lower())

    def test_approved_brand_assets_are_served_and_referenced(self):
        expected_assets = {
            "/favicon.ico": "",
            "/static/branding/sylrix-icon.png": "",
            "/static/branding/sylrix-wordmark.png": "",
            "/static/branding/favicon.png": "",
            "/static/branding/sylrix-icon-192.png": "192x192",
            "/static/branding/sylrix-icon-512.png": "512x512",
            "/static/branding/apple-touch-icon.png": "",
        }
        for path in expected_assets:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            response.close()
        page = self.client.get("/")
        self.assertIn(b"branding/sylrix-icon.png", page.data)
        self.assertIn(b"branding/sylrix-wordmark.png", page.data)
        self.assertIn(b"branding/apple-touch-icon.png", page.data)
        manifest_response = self.client.get("/manifest.webmanifest")
        manifest = manifest_response.get_json()
        manifest_response.close()
        manifest_icons = {icon["src"]: icon["sizes"] for icon in manifest["icons"]}
        self.assertEqual(manifest_icons["/static/branding/sylrix-icon-192.png"], "192x192")
        self.assertEqual(manifest_icons["/static/branding/sylrix-icon-512.png"], "512x512")

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
        self.assertEqual(dashboard.headers["Cache-Control"], "private, no-store")
        self.assertIn(b"Breakfast", self.client.get(f"/nutrition?date={today}").data)
        self.assertIn(b"Beta Lifter", dashboard.data)


if __name__ == "__main__":
    unittest.main()
