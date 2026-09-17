import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as sylrix
from services.ai_coach import CoachService


class LocalizationAndSharingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.original_database = sylrix.DATABASE
        self.original_csrf = sylrix.csrf_enabled
        sylrix.DATABASE = Path(self.directory.name) / "sharing.db"
        sylrix.csrf_enabled = False
        sylrix.setup_database()
        self.client_a = sylrix.app.test_client()
        self.client_b = sylrix.app.test_client()
        with sylrix.db_connection() as db:
            first = db.execute("INSERT INTO members (name, age, sex, weight, height, goal, days, equipment, experience) VALUES ('Private Member', 30, 'x', 180, 70, 'strength', 3, 'full gym', 'beginner')")
            self.member_a = first.lastrowid
            account = db.execute("INSERT INTO accounts (username, email, password_hash, member_id) VALUES ('member_a', 'private@example.test', 'hash', ?)", (self.member_a,))
            self.account_a = account.lastrowid
            second = db.execute("INSERT INTO members (name, age, sex, weight, height, goal, days, equipment, experience) VALUES ('Other Member', 30, 'x', 180, 70, 'strength', 3, 'full gym', 'beginner')")
            self.member_b = second.lastrowid
            account = db.execute("INSERT INTO accounts (username, email, password_hash, member_id) VALUES ('member_b', 'other@example.test', 'hash', ?)", (self.member_b,))
            self.account_b = account.lastrowid
            session = db.execute("INSERT INTO workout_sessions (member_id, workout_name, workout_day, training_style) VALUES (?, 'Private Strength Session', 1, 'strength')", (self.member_a,))
            self.session_id = session.lastrowid
            set_row = db.execute("INSERT INTO workout_sets (session_id, exercise_name, exercise_order, set_number, target_reps, target_weight, target_rpe) VALUES (?, 'Bench Press', 1, 1, '8', 135, 7)", (self.session_id,))
            self.set_id = set_row.lastrowid
        with self.client_a.session_transaction() as session:
            session["account_id"] = self.account_a
        with self.client_b.session_transaction() as session:
            session["account_id"] = self.account_b

    def tearDown(self):
        sylrix.DATABASE = self.original_database
        sylrix.csrf_enabled = self.original_csrf
        self.directory.cleanup()

    def create_share(self):
        response = self.client_a.post(f"/workout/session/{self.session_id}/share", data={"action": "create"})
        self.assertEqual(response.status_code, 302)
        with sylrix.db_connection() as db:
            return db.execute("SELECT share_token FROM workout_shares WHERE workout_session_id=?", (self.session_id,)).fetchone()["share_token"]

    def test_language_selector_persists_for_member_and_guest(self):
        response = self.client_a.post("/language", data={"language": "es", "return_to": "/"})
        self.assertEqual(response.status_code, 302)
        with sylrix.db_connection() as db:
            self.assertEqual(db.execute("SELECT language FROM members WHERE id=?", (self.member_a,)).fetchone()["language"], "es")
        page = self.client_a.get("/")
        self.assertIn("Panel".encode(), page.data)
        guest = sylrix.app.test_client()
        self.assertEqual(guest.post("/language", data={"language": "es", "return_to": "/"}).status_code, 302)
        self.assertIn(b"Inicio", guest.get("/").data)

    def test_public_share_is_opaque_read_only_localized_and_revocable(self):
        token = self.create_share()
        self.assertGreaterEqual(len(token), 40)
        self.assertNotEqual(token, str(self.member_a))
        guest = sylrix.app.test_client()
        english = guest.get(f"/w/{token}")
        self.assertEqual(english.status_code, 200)
        self.assertEqual(english.headers["Cache-Control"], "no-store")
        self.assertIn(b"Bench Press", english.data)
        self.assertNotIn(b"Private Member", english.data)
        self.assertNotIn(b"private@example.test", english.data)
        self.assertEqual(guest.post(f"/workout/session/{self.session_id}/set/{self.set_id}", data={"weight": "200", "reps": "8"}).status_code, 404)
        self.assertEqual(guest.post("/language", data={"language": "es", "return_to": f"/w/{token}"}).status_code, 302)
        spanish = guest.get(f"/w/{token}")
        self.assertEqual(spanish.status_code, 200)
        self.assertIn("Press de banca".encode(), spanish.data)
        with sylrix.db_connection() as db:
            self.assertEqual(db.execute("SELECT exercise_name FROM workout_sets WHERE id=?", (self.set_id,)).fetchone()["exercise_name"], "Bench Press")
        self.assertEqual(guest.get(f"/w/{token}/qr.png").status_code, 200)
        self.assertEqual(self.client_b.post(f"/workout/session/{self.session_id}/share", data={"action": "revoke"}).status_code, 404)
        self.assertEqual(self.client_a.post(f"/workout/session/{self.session_id}/share", data={"action": "revoke"}).status_code, 302)
        self.assertEqual(guest.get(f"/w/{token}").status_code, 404)

    def test_share_mutations_require_csrf_and_qr_encodes_only_public_url(self):
        sylrix.csrf_enabled = True
        self.assertEqual(self.client_a.post(f"/workout/session/{self.session_id}/share", data={"action": "create"}).status_code, 403)
        self.client_a.get(f"/workout/session/{self.session_id}/share")
        with self.client_a.session_transaction() as session:
            token = session["csrf_token"]
        self.assertEqual(self.client_a.post(f"/workout/session/{self.session_id}/share", data={"action": "create", "csrf_token": token}).status_code, 302)
        with sylrix.db_connection() as db:
            share_token = db.execute("SELECT share_token FROM workout_shares WHERE workout_session_id=?", (self.session_id,)).fetchone()["share_token"]
        with patch("qrcode.make") as make:
            image = make.return_value
            image.save.side_effect = lambda output, format: output.write(b"png")
            response = self.client_a.get(f"/w/{share_token}/qr.png")
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertEqual(make.call_args.args, (f"http://localhost/w/{share_token}",))

    def test_invalid_share_is_unavailable(self):
        response = sylrix.app.test_client().get("/w/not-a-valid-share-token")
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Workout unavailable", response.data)

    def test_local_coach_honors_spanish_member_preference(self):
        reply = CoachService(sylrix.DATABASE, self.member_a, "es").reply("\u00bfQu\u00e9 debo entrenar hoy?")
        self.assertTrue(reply.startswith(("Tu plan actual", "Puedo ayudarte", "Completa el registro")))


if __name__ == "__main__":
    unittest.main()
