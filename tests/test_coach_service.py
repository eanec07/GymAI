import os
import sqlite3
import tempfile
import unittest

from services.ai_coach import CoachService


class CoachServiceTests(unittest.TestCase):
    def setUp(self):
        self.file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.file.close()
        with sqlite3.connect(self.file.name) as db:
            db.executescript("""
                CREATE TABLE members (id INTEGER PRIMARY KEY, age INTEGER, sex TEXT, weight REAL, height REAL, goal TEXT, training_style TEXT, experience TEXT, days INTEGER, session_minutes INTEGER, equipment TEXT, equipment_notes TEXT, limitations TEXT, favorite_exercises TEXT, avoid_exercises TEXT);
                CREATE TABLE training_preferences (member_id INTEGER, preference_key TEXT, preference_value TEXT);
                CREATE TABLE workout_sessions (id INTEGER PRIMARY KEY, member_id INTEGER, workout_name TEXT, workout_day INTEGER, training_style TEXT, status TEXT, started_at TEXT, completed_at TEXT);
                CREATE TABLE workout_sets (session_id INTEGER, exercise_name TEXT, actual_weight REAL, actual_reps INTEGER, target_reps TEXT, completed INTEGER);
                CREATE TABLE nutrition_logs (member_id INTEGER, calories REAL, protein REAL, carbs REAL, fat REAL, logged_on TEXT);
                CREATE TABLE step_logs (member_id INTEGER, steps INTEGER, goal INTEGER, logged_on TEXT);
            """)
            db.execute("INSERT INTO members VALUES (1, 25, 'male', 180, 70, 'strength', 'powerlifting', 'intermediate', 4, 60, 'full gym', '', '', 'bench press', '')")
            db.execute("INSERT INTO members VALUES (2, 30, 'female', 140, 65, 'muscle gain', 'bodybuilding', 'beginner', 3, 45, 'dumbbell', '', '', '', '')")
            db.execute("INSERT INTO training_preferences VALUES (1, 'bench_max', '315')")

    def tearDown(self):
        os.unlink(self.file.name)

    def test_profile_context_is_member_scoped(self):
        service = CoachService(self.file.name)
        first = service._tool(1, "get_member_profile", {})
        second = service._tool(2, "get_member_profile", {})
        self.assertEqual(first["training_preferences"]["bench_max"], "315")
        self.assertNotIn("bench_max", second["training_preferences"])

    def test_missing_key_uses_free_local_coach(self):
        previous = os.environ.pop("OPENAI_API_KEY", None)
        try:
            service = CoachService(self.file.name)
            self.assertFalse(service.configured)
            self.assertIn("stronger bench", service.reply(1, "How is my bench?"))
        finally:
            if previous:
                os.environ["OPENAI_API_KEY"] = previous


if __name__ == "__main__":
    unittest.main()
