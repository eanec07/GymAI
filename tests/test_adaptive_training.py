import sqlite3
import tempfile
import unittest

from training.adaptive import apply_progression_states, progression_state, recommendation_for_session, save_progression_state


def completed_sets(weight, reps, rpe=None):
    return [{"actual_weight": weight, "actual_reps": rep, "actual_rpe": rpe, "completed": True} for rep in reps]


class AdaptiveTrainingTests(unittest.TestCase):
    def setUp(self):
        self.file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.file.close()
        self.db = sqlite3.connect(self.file.name)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE exercise_progression_state (
                id INTEGER PRIMARY KEY, member_id INTEGER NOT NULL, exercise_name TEXT NOT NULL,
                last_session_id INTEGER, recommended_weight REAL, recommended_reps TEXT,
                recommended_rpe REAL, progression_action TEXT NOT NULL, reason TEXT NOT NULL,
                consecutive_misses INTEGER NOT NULL DEFAULT 0, updated_at TEXT,
                UNIQUE(member_id, exercise_name));
        """)

    def tearDown(self):
        self.db.close()
        import os
        os.unlink(self.file.name)

    def _save(self, member_id, sets, style="powerlifting"):
        rec = recommendation_for_session(self.db, member_id, 10, "Barbell Bench Press", sets, "3 sets × 5 reps", style)
        return rec, save_progression_state(self.db, member_id, 10, "Barbell Bench Press", rec, sets)

    def test_success_persists_a_member_scoped_next_target(self):
        rec, state = self._save(1, completed_sets(225, [5, 5, 5], 8))
        self.assertEqual(rec.action, "increase")
        self.assertEqual(state["recommended_weight"], 227.5)
        self.assertIsNone(progression_state(self.db, 2, "Barbell Bench Press"))

    def test_miss_and_repeated_misses_are_conservative(self):
        first, state = self._save(1, completed_sets(225, [5, 5, 3]))
        self.assertEqual(first.action, "hold")
        self.assertEqual(state["consecutive_misses"], 1)
        self._save(1, completed_sets(225, [5, 4, 3]))
        final, state = self._save(1, completed_sets(225, [5, 4, 3]))
        self.assertEqual(final.action, "deload")
        self.assertLess(state["recommended_weight"], 225)

    def test_missing_rpe_does_not_prevent_progression(self):
        rec, state = self._save(1, completed_sets(225, [5, 5, 5]))
        self.assertEqual(rec.action, "increase")
        self.assertIsNone(state["recommended_rpe"])

    def test_next_plan_consumes_saved_target_after_new_request(self):
        self._save(1, completed_sets(225, [5, 5, 5]))
        # Read the saved record again to model a later request/new session.
        state = dict(progression_state(self.db, 1, "Barbell Bench Press"))
        plan = [{"day": 1, "exercises": [{"name": "Barbell Bench Press", "sets_reps": "3 sets × 5 reps", "muscles": "chest"}]}]
        adapted = apply_progression_states(plan, {"barbell bench press": state})
        self.assertIn("Target: 227.5 lb", adapted[0]["exercises"][0]["sets_reps"])


if __name__ == "__main__":
    unittest.main()
