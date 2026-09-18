import tempfile
import unittest
from pathlib import Path

import app as sylrix
from services.ai_coach import CoachService


class SplitPreferenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.original_database = sylrix.DATABASE
        self.original_csrf = sylrix.csrf_enabled
        sylrix.DATABASE = Path(self.directory.name) / "splits.db"
        sylrix.csrf_enabled = False
        sylrix.setup_database()
        self.client = sylrix.app.test_client()
        with sylrix.db_connection() as db:
            member = db.execute("INSERT INTO members (name, age, sex, weight, height, goal, days, equipment, experience, training_style) VALUES ('Split Member', 30, 'x', 180, 70, 'strength', 3, 'full gym', 'beginner', 'strength')")
            self.member_id = member.lastrowid
            account = db.execute("INSERT INTO accounts (username, email, password_hash, member_id) VALUES ('split_member', 'split@example.test', 'hash', ?)", (self.member_id,))
            self.account_id = account.lastrowid
        with self.client.session_transaction() as session:
            session["account_id"] = self.account_id

    def tearDown(self):
        sylrix.DATABASE = self.original_database
        sylrix.csrf_enabled = self.original_csrf
        self.directory.cleanup()

    def test_engine_supported_choices_are_day_and_style_compatible(self):
        self.assertEqual(sylrix.split_choices("strength", 1), [("auto", "SYLRIX Recommended"), ("full body", "Full Body")])
        self.assertEqual([item[0] for item in sylrix.split_choices("general-fitness", 3)], ["auto", "full body", "upper lower", "push pull legs"])
        self.assertEqual(sylrix.split_choices("bodybuilding", 5), [("auto", "SYLRIX Recommended")])
        self.assertEqual(sylrix.valid_split_preference("push pull legs", "strength", 2), "")
        self.assertEqual(sylrix.valid_split_preference("upper lower", "strength", 2), "upper lower")

    def test_profile_persists_supported_split_without_rewriting_active_session(self):
        with sylrix.db_connection() as db:
            session = db.execute("INSERT INTO workout_sessions (member_id, workout_name, workout_day, training_style) VALUES (?, 'Existing Session', 1, 'strength')", (self.member_id,))
            session_id = session.lastrowid
        response = self.client.post("/app/profile", data={
            "action": "save", "name": "Split Member", "username": "split_member", "weight": "180", "goal": "strength",
            "training_style": "strength", "split_preference": "push pull legs", "experience": "beginner", "days": "3",
            "session_minutes": "60", "equipment": "full gym", "favorite_exercises": "", "avoid_exercises": "",
        })
        self.assertEqual(response.status_code, 302)
        with sylrix.db_connection() as db:
            member = db.execute("SELECT split_preference FROM members WHERE id=?", (self.member_id,)).fetchone()
            active = db.execute("SELECT workout_name FROM workout_sessions WHERE id=?", (session_id,)).fetchone()
        self.assertEqual(member["split_preference"], "push pull legs")
        self.assertEqual(active["workout_name"], "Existing Session")

        with sylrix.db_connection() as db:
            refreshed_member = db.execute("SELECT * FROM members WHERE id=?", (self.member_id,)).fetchone()
        self.assertEqual([day["name"] for day in sylrix.member_plan(refreshed_member)], ["Push", "Pull", "Legs + Core"])

    def test_onboarding_exposes_and_persists_the_canonical_split_identifier(self):
        with sylrix.db_connection() as db:
            account_id = db.execute("INSERT INTO accounts (username, email, password_hash) VALUES ('onboard_split', 'onboard@example.test', 'hash')").lastrowid
        fresh_client = sylrix.app.test_client()
        with fresh_client.session_transaction() as session:
            session["account_id"] = account_id
        page = fresh_client.get("/onboarding")
        self.assertIn(b'name="split_preference"', page.data)
        response = fresh_client.post("/onboarding", data={
            "name": "Onboard Split", "age": "30", "sex": "male", "weight": "180", "height": "70",
            "goal": "strength", "days": "2", "equipment": "full gym", "experience": "beginner",
            "training_style": "strength", "split_preference": "upper lower", "session_minutes": "60",
        })
        self.assertEqual(response.status_code, 302)
        with sylrix.db_connection() as db:
            member = db.execute("SELECT split_preference FROM members JOIN accounts ON accounts.member_id=members.id WHERE accounts.id=?", (account_id,)).fetchone()
        self.assertEqual(member["split_preference"], "upper lower")

    def test_invalid_or_unsupported_split_is_rejected_and_coach_can_only_explain(self):
        invalid = self.client.post("/app/profile", data={
            "action": "save", "name": "Split Member", "username": "split_member", "weight": "180", "goal": "strength",
            "training_style": "strength", "split_preference": "push pull legs", "experience": "beginner", "days": "2",
            "session_minutes": "60", "equipment": "full gym", "favorite_exercises": "", "avoid_exercises": "",
        })
        self.assertEqual(invalid.status_code, 302)
        with sylrix.db_connection() as db:
            self.assertEqual(db.execute("SELECT split_preference FROM members WHERE id=?", (self.member_id,)).fetchone()["split_preference"], "auto")
        coach = CoachService(sylrix.DATABASE, self.member_id)
        answer = coach.reply("What is my workout split?")
        self.assertIn("saved workout split preference", answer)
        self.assertIn("Profile", answer)
