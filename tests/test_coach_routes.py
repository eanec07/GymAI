import sqlite3
import tempfile
import unittest
from pathlib import Path

from werkzeug.security import generate_password_hash

import app as sylrix
from services.ai_coach import CoachService
from training.prs import detect_prs


class CoachRouteTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.original_database = sylrix.DATABASE
        sylrix.DATABASE = Path(self.directory.name) / "sylrix-test.db"
        sylrix.setup_database()
        with sylrix.db_connection() as db:
            member_id = db.execute(
                """INSERT INTO members (name, age, sex, weight, height, goal, days, equipment, experience,
                   custom_goal, training_style, equipment_notes, limitations, split_preference, session_minutes,
                   favorite_exercises, avoid_exercises)
                   VALUES ('Route User', 25, 'male', 180, 70, 'strength', 3, 'full gym', 'beginner', '', 'strength', '', '', 'auto', 60, '', '')"""
            ).lastrowid
            self.account_id = db.execute(
                "INSERT INTO accounts (username, email, password_hash, member_id) VALUES (?, ?, ?, ?)",
                ("route_user", "route@example.com", generate_password_hash("safe-password-123"), member_id),
            ).lastrowid
            self.member_id = member_id
        self.client = sylrix.app.test_client()

    def tearDown(self):
        sylrix.DATABASE = self.original_database
        self.directory.cleanup()

    def _sign_in(self):
        with self.client.session_transaction() as session:
            session["account_id"] = self.account_id

    def test_coach_requires_authentication_and_persists_messages(self):
        self.assertEqual(self.client.get("/app/coach").status_code, 302)
        self._sign_in()
        response = self.client.post("/app/coach", data={"message": "Explain RPE"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"RPE is rate of perceived exertion", response.data)
        with sylrix.db_connection() as db:
            rows = db.execute("SELECT role FROM coach_messages WHERE member_id=? ORDER BY id", (self.member_id,)).fetchall()
        self.assertEqual([row["role"] for row in rows], ["user", "assistant"])

    def test_pr_events_persist_once_and_are_available_to_coach(self):
        current = [{"actual_weight": 235, "actual_reps": 5, "completed": True}]
        history = [{"actual_weight": 225, "actual_reps": 5, "completed": True}]
        events = detect_prs("Bench Press", current, history)
        with sylrix.db_connection() as db:
            session_id = db.execute(
                "INSERT INTO workout_sessions (member_id, workout_name, workout_day, training_style, status) VALUES (?, 'Bench', 1, 'strength', 'completed')",
                (self.member_id,),
            ).lastrowid
            sylrix.persist_pr_events(db, self.member_id, session_id, "Bench Press", events, current)
            sylrix.persist_pr_events(db, self.member_id, session_id, "Bench Press", events, current)
        with sylrix.db_connection() as db:
            count = db.execute("SELECT COUNT(*) FROM personal_records WHERE member_id=?", (self.member_id,)).fetchone()[0]
        records = CoachService(sylrix.DATABASE)._tool(self.member_id, "get_pr_history", {"exercise_name": "Bench Press"})
        self.assertEqual(count, len(events))
        self.assertTrue(records["records"])


if __name__ == "__main__":
    unittest.main()
