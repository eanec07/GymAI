import tempfile
import unittest
from datetime import date
from pathlib import Path

from werkzeug.security import generate_password_hash

import app as sylrix
from services.readiness import calculate_readiness, training_recommendation


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.original_database = sylrix.DATABASE
        sylrix.DATABASE = Path(self.directory.name) / "readiness.db"
        sylrix.setup_database()
        with sylrix.db_connection() as db:
            self.member_id = db.execute(
                "INSERT INTO members (name,age,sex,weight,height,goal,days,equipment,experience,training_style) VALUES ('Ready One',30,'male',180,70,'strength',3,'full gym','intermediate','strength')"
            ).lastrowid
            self.other_id = db.execute(
                "INSERT INTO members (name,age,sex,weight,height,goal,days,equipment,experience,training_style) VALUES ('Ready Two',30,'female',140,65,'strength',3,'full gym','intermediate','strength')"
            ).lastrowid
            self.account_id = db.execute(
                "INSERT INTO accounts (username,email,password_hash,member_id) VALUES ('ready_one','ready@example.test',?,?)",
                (generate_password_hash("safe-password-123"), self.member_id),
            ).lastrowid
        self.client = sylrix.app.test_client()
        with self.client.session_transaction() as session:
            session["account_id"] = self.account_id

    def tearDown(self):
        sylrix.DATABASE = self.original_database
        self.directory.cleanup()

    @staticmethod
    def check_in(**overrides):
        values = {"sleep_hours": "4", "sleep_quality": "1", "energy": "1", "soreness": "5", "stress": "5", "motivation": "1", "notes": "Low energy"}
        values.update(overrides)
        return values

    def test_score_is_deterministic_and_has_clear_classes(self):
        high = calculate_readiness(8, 5, 5, 1, 1, 5)
        recovery = calculate_readiness(4, 1, 1, 5, 5, 1)
        self.assertEqual((high.score, high.classification), (100, "High"))
        self.assertEqual(recovery.classification, "Recovery")
        self.assertEqual(training_recommendation({"score": recovery.score, "classification": recovery.classification})["action"], "rest")

    def test_check_in_is_owned_upserted_and_visible_on_dashboard(self):
        self.assertIn(b"How are you feeling today", self.client.get("/app").data)
        self.assertEqual(self.client.post("/app/readiness", data=self.check_in()).status_code, 302)
        self.assertEqual(self.client.post("/app/readiness", data=self.check_in(energy="2", notes="Updated")).status_code, 302)
        with sylrix.db_connection() as db:
            rows = db.execute("SELECT * FROM daily_readiness WHERE member_id=?", (self.member_id,)).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["notes"], "Updated")
        self.assertIn(b"Recovery readiness", self.client.get("/app/readiness").data)
        self.assertIn(b"READINESS", self.client.get("/app").data)

    def test_adjustment_is_session_scoped_and_other_member_is_blocked(self):
        self.client.post("/app/readiness", data=self.check_in())
        self.assertEqual(self.client.get("/workout/1").status_code, 200)
        with sylrix.db_connection() as db:
            session_id = db.execute("SELECT id FROM workout_sessions WHERE member_id=?", (self.member_id,)).fetchone()["id"]
            before = [row["target_weight"] for row in db.execute("SELECT target_weight FROM workout_sets WHERE session_id=? AND is_warmup=0", (session_id,))]
            other_session = db.execute("INSERT INTO workout_sessions (member_id,workout_name,workout_day,status) VALUES (?, 'Private',1,'active')", (self.other_id,)).lastrowid
        self.assertEqual(self.client.post(f"/workout/session/{other_session}/readiness-adjustment", data={"choice": "rest"}).status_code, 404)
        self.assertEqual(self.client.post(f"/workout/session/{session_id}/readiness-adjustment", data={"choice": "rest"}).status_code, 302)
        with sylrix.db_connection() as db:
            saved = db.execute("SELECT readiness_score, readiness_adjustment FROM workout_sessions WHERE id=?", (session_id,)).fetchone()
            after = [row["target_weight"] for row in db.execute("SELECT target_weight FROM workout_sets WHERE session_id=? AND is_warmup=0", (session_id,))]
        self.assertEqual(saved["readiness_adjustment"], "rest")
        self.assertIsNotNone(saved["readiness_score"])
        self.assertEqual(before, after)

    def test_readiness_history_is_limited_to_seven_entries(self):
        with sylrix.db_connection() as db:
            for day_number in range(10):
                db.execute(
                    "INSERT INTO daily_readiness (member_id,logged_on,sleep_hours,sleep_quality,energy,soreness,stress,motivation,score,classification) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (self.member_id, f"2026-09-{day_number + 1:02d}", 7, 3, 3, 3, 3, 3, 60, "Normal"),
                )
        page = self.client.get("/app/readiness")
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.data.count(b"Normal</span>"), 7)


if __name__ == "__main__":
    unittest.main()
