import tempfile
import unittest
from pathlib import Path

from werkzeug.security import generate_password_hash

import app as sylrix
from muscles import diagram_regions, normalize_muscle


class MemberProgressTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.original_database = sylrix.DATABASE
        sylrix.DATABASE = Path(self.directory.name) / "progress-test.db"
        sylrix.setup_database()
        with sylrix.db_connection() as db:
            self.member_id = db.execute("INSERT INTO members (name, age, sex, weight, height, goal, days, equipment, experience) VALUES ('Member One', 30, 'male', 200, 72, 'strength', 3, 'full gym', 'beginner')").lastrowid
            self.account_id = db.execute("INSERT INTO accounts (username, email, password_hash, member_id) VALUES (?, ?, ?, ?)", ("member_one", "one@example.com", generate_password_hash("safe-password-123"), self.member_id)).lastrowid
            self.other_member_id = db.execute("INSERT INTO members (name, age, sex, weight, height, goal, days, equipment, experience) VALUES ('Member Two', 30, 'female', 140, 65, 'muscle gain', 3, 'dumbbell', 'beginner')").lastrowid
        self.client = sylrix.app.test_client()

    def tearDown(self):
        sylrix.DATABASE = self.original_database
        self.directory.cleanup()

    def sign_in(self):
        with self.client.session_transaction() as session:
            session["account_id"] = self.account_id

    def test_weight_entry_edit_delete_and_member_isolation(self):
        self.assertEqual(self.client.post("/progress/weight", data={"weight": "198.5", "logged_on": "2026-09-15"}).status_code, 302)
        self.sign_in()
        self.client.post("/progress/weight", data={"weight": "198.5", "logged_on": "2026-09-15"})
        with sylrix.db_connection() as db:
            own = db.execute("SELECT * FROM body_weight_logs WHERE member_id=?", (self.member_id,)).fetchone()
            other_id = db.execute("INSERT INTO body_weight_logs (member_id, weight, logged_on) VALUES (?, 140, '2026-09-15')", (self.other_member_id,)).lastrowid
        self.assertEqual(own["weight"], 198.5)
        self.assertEqual(self.client.post(f"/progress/weight/{other_id}/edit", data={"weight": "150", "logged_on": "2026-09-14"}).status_code, 404)
        self.assertEqual(self.client.post(f"/progress/weight/{other_id}/delete").status_code, 404)
        self.client.post(f"/progress/weight/{own['id']}/edit", data={"weight": "197.0", "logged_on": "2026-09-14"})
        self.client.post(f"/progress/weight/{own['id']}/delete")
        with sylrix.db_connection() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM body_weight_logs WHERE member_id=?", (self.member_id,)).fetchone()[0], 0)

    def test_profile_edit_updates_only_signed_in_member(self):
        self.sign_in()
        response = self.client.post("/app/profile", data={"action": "save", "name": "Updated One", "username": "updated_one", "weight": "195", "goal_weight": "185", "goal": "strength", "training_style": "strength", "experience": "intermediate", "days": "4", "session_minutes": "60", "equipment": "full gym", "favorite_exercises": "bench press", "avoid_exercises": ""})
        self.assertEqual(response.status_code, 302)
        with sylrix.db_connection() as db:
            member = db.execute("SELECT name, weight, goal_weight FROM members WHERE id=?", (self.member_id,)).fetchone()
            other = db.execute("SELECT name FROM members WHERE id=?", (self.other_member_id,)).fetchone()
        self.assertEqual((member["name"], member["weight"], member["goal_weight"]), ("Updated One", 195.0, 185.0))
        self.assertEqual(other["name"], "Member Two")

    def test_muscle_mapping_normalizes_common_library_terms(self):
        self.assertEqual(normalize_muscle("pectorals"), "chest")
        self.assertEqual(diagram_regions(("chest", "triceps")), ("chest", "triceps"))


if __name__ == "__main__":
    unittest.main()
