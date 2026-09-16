import os
import sqlite3
import tempfile
import unittest
import sys
import types
from datetime import date
from unittest.mock import patch
import services.ai_coach as coach_module
from services.ai_coach import CoachService


class CoachServiceTests(unittest.TestCase):
    def setUp(self):
        self.file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.file.close()
        connection = sqlite3.connect(self.file.name)
        try:
            today = date.today().isoformat()
            connection.executescript("""
                CREATE TABLE members (id INTEGER PRIMARY KEY, age INTEGER, sex TEXT, weight REAL, height REAL, goal TEXT, training_style TEXT, experience TEXT, days INTEGER, session_minutes INTEGER, equipment TEXT, equipment_notes TEXT, limitations TEXT, favorite_exercises TEXT, avoid_exercises TEXT, custom_goal TEXT DEFAULT '', split_preference TEXT DEFAULT 'auto', goal_weight REAL);
                CREATE TABLE training_preferences (member_id INTEGER, preference_key TEXT, preference_value TEXT);
                CREATE TABLE workout_sessions (id INTEGER PRIMARY KEY, member_id INTEGER, workout_name TEXT, workout_day INTEGER, training_style TEXT, status TEXT, started_at TEXT, completed_at TEXT);
                CREATE TABLE workout_sets (id INTEGER PRIMARY KEY, session_id INTEGER, exercise_name TEXT, exercise_order INTEGER, set_number INTEGER, actual_weight REAL, actual_reps INTEGER, target_reps TEXT, target_weight REAL, target_rpe REAL, completed INTEGER);
                CREATE TABLE nutrition_logs (member_id INTEGER, calories REAL, protein REAL, carbs REAL, fat REAL, fiber REAL, logged_on TEXT);
                CREATE TABLE step_logs (member_id INTEGER, steps INTEGER, goal INTEGER, logged_on TEXT);
                CREATE TABLE personal_records (id INTEGER PRIMARY KEY, member_id INTEGER, workout_session_id INTEGER, exercise_name TEXT, pr_type TEXT, value REAL, weight REAL, reps INTEGER, estimated_1rm REAL, achieved_at TEXT);
                CREATE TABLE body_weight_logs (id INTEGER PRIMARY KEY, member_id INTEGER, weight REAL, logged_on TEXT);
                CREATE TABLE coach_messages (id INTEGER PRIMARY KEY, member_id INTEGER, role TEXT, message TEXT);
                CREATE TABLE exercise_progression_state (id INTEGER PRIMARY KEY, member_id INTEGER, exercise_name TEXT, last_session_id INTEGER, recommended_weight REAL, recommended_reps TEXT, recommended_rpe REAL, progression_action TEXT, reason TEXT, consecutive_misses INTEGER, updated_at TEXT, UNIQUE(member_id, exercise_name));
            """)
            connection.execute("INSERT INTO members VALUES (1, 25, 'male', 180, 70, 'strength', 'powerlifting', 'intermediate', 4, 60, 'full gym', '', '', 'bench press', '', '', 'auto', 170)")
            connection.execute("INSERT INTO members VALUES (2, 30, 'female', 140, 65, 'muscle gain', 'bodybuilding', 'beginner', 3, 45, 'dumbbell', '', '', '', '', '', 'auto', 130)")
            connection.execute("INSERT INTO training_preferences VALUES (1, 'bench_max', '315')")
            connection.execute("INSERT INTO workout_sessions VALUES (1, 1, 'Powerlifting — Bench', 2, 'powerlifting', 'active', ?, NULL)", (today,))
            connection.execute("INSERT INTO workout_sessions VALUES (2, 1, 'Powerlifting — Bench', 2, 'powerlifting', 'completed', ?, ?)", (today, today))
            connection.execute("INSERT INTO workout_sessions VALUES (3, 2, 'Bodybuilding — Push', 1, 'bodybuilding', 'completed', ?, ?)", (today, today))
            connection.executemany("INSERT INTO workout_sets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [
                (1, 1, 'Bench Press - Powerlifting', 1, 1, None, None, '5', 235, 7, 0),
                (2, 2, 'Bench Press - Powerlifting', 1, 1, 235, 5, '5', 235, 7, 1),
                (3, 2, 'Bench Press - Powerlifting', 1, 2, 235, 5, '5', 235, 7, 1),
                (4, 2, 'Bench Press - Powerlifting', 1, 3, 235, 5, '5', 235, 7, 1),
                (5, 3, 'Dumbbell Bench Press', 1, 1, 35, 10, '10', 35, 7, 1),
            ])
            connection.executemany("INSERT INTO nutrition_logs VALUES (?, ?, ?, ?, ?, ?, ?)", [
                (1, 2500, 180, 280, 70, 30, today), (1, 2400, 170, 260, 65, 28, today),
                (2, 1600, 100, 180, 50, 20, today),
            ])
            connection.executemany("INSERT INTO step_logs VALUES (?, ?, ?, ?)", [(1, 9000, 8000, today), (2, 3000, 8000, today)])
            connection.execute("INSERT INTO personal_records VALUES (1, 1, 2, 'Bench Press - Powerlifting', 'weight', 235, 235, 5, 274.2, ?)", (today,))
            connection.execute("INSERT INTO exercise_progression_state VALUES (1, 1, 'Bench Press - Powerlifting', 2, 237.5, '5', 8, 'increase', 'Completed all target reps.', 0, ?)", (today,))
            connection.executemany("INSERT INTO body_weight_logs VALUES (?, ?, ?, ?)", [(1, 1, 184, '2026-09-01'), (2, 1, 180, '2026-09-15'), (3, 2, 140, '2026-09-15')])
            connection.commit()
        finally:
            connection.close()
        self.service = CoachService(self.file.name)

    def tearDown(self):
        os.unlink(self.file.name)

    def test_member_profile_is_member_scoped(self):
        first = self.service._tool(1, "get_member_profile")
        second = self.service._tool(2, "get_member_profile")
        self.assertEqual(first["training_preferences"]["bench_max"], "315")
        self.assertNotIn("bench_max", second["training_preferences"])

    def test_training_plan_and_active_workout_are_separate(self):
        plan = self.service._tool(1, "get_training_plan")
        active = self.service._tool(1, "get_today_workout")
        self.assertGreaterEqual(len(plan), 1)
        self.assertIn("target_weight", plan[0]["exercises"][0])
        self.assertEqual(active["session"]["status"], "active")
        self.assertEqual(active["sets"][0]["exercise_name"], "Bench Press - Powerlifting")

    def test_recent_workouts_history_and_progression(self):
        recent = self.service._tool(1, "get_recent_workouts")
        history = self.service._tool(1, "get_exercise_history", {"exercise_name": "Bench Press - Powerlifting"})
        progression = self.service._tool(1, "get_progression", {"exercise_name": "Bench Press - Powerlifting"})
        self.assertEqual(len(recent), 1)
        self.assertEqual(len(history), 3)
        self.assertEqual(progression["action"], "increase")

    def test_pr_history_is_member_scoped(self):
        first = self.service._tool(1, "get_pr_history", {"exercise_name": "Bench Press - Powerlifting"})
        second = self.service._tool(2, "get_pr_history", {"exercise_name": "Bench Press - Powerlifting"})
        self.assertEqual(first["best_by_type"]["weight"]["value"], 235)
        self.assertFalse(second["records"])

    def test_nutrition_targets_and_bounded_history(self):
        targets = self.service._tool(1, "get_nutrition_targets")
        history = self.service._tool(1, "get_nutrition_history")
        self.assertEqual(targets["today_logged"]["protein"], 350)
        self.assertEqual(history["days_logged"], 1)
        self.assertEqual(history["averages"]["calories"], 4900)
        today = self.service.tools if self.service.tools else None
        bound = CoachService(self.file.name, 1)
        self.assertEqual(bound.tools.execute("get_today_nutrition", {"member_id": 2})["consumed"]["protein"], 350)

    def test_steps_substitutes_and_progress_summary(self):
        steps = self.service._tool(1, "get_steps")
        substitutes = self.service._tool(1, "find_exercise_substitutes", {"exercise_name": "Bench Press - Powerlifting"})
        summary = self.service._tool(1, "get_progress_summary")
        self.assertEqual(steps[0]["steps"], 9000)
        self.assertIsInstance(substitutes, list)
        self.assertEqual(summary["completed_workouts"], 1)
        self.assertEqual(summary["recent_prs"][0]["exercise_name"], "Bench Press - Powerlifting")

    def test_local_mode_uses_member_data_without_credentials(self):
        previous_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            self.assertFalse(self.service.configured)
            self.assertIn("last 7 days", self.service.reply(1, "Give me my weekly recap."))
            self.assertIn("personal records", self.service.reply(2, "Did I hit a PR?"))
        finally:
            if previous_key:
                os.environ["OPENAI_API_KEY"] = previous_key

    def test_weight_and_workout_tools_ignore_model_member_id(self):
        weight = self.service._tool(1, "get_weight_progress", {"member_id": 2})
        workouts = self.service._tool(1, "get_workout_history", {"member_id": 2})
        self.assertEqual(weight["latest_weight"], 180)
        self.assertEqual(weight["change"], -4)
        self.assertEqual(workouts["sessions"][0]["workout_name"], "Powerlifting — Bench")

    def test_exercise_search_and_invalid_tool_are_safe(self):
        results = self.service._tool(1, "search_exercises", {"equipment": "dumbbell", "limit": 3})
        self.assertTrue(results["exercises"])
        self.assertTrue(all(item["equipment"] == "dumbbell" for item in results["exercises"]))
        self.assertEqual(self.service._tool(1, "drop_database", {})["message"], "That tool is unavailable.")

    def test_saved_progression_tool_is_bound_to_the_authenticated_member(self):
        bound = CoachService(self.file.name, 1)
        state = bound.tools.execute("get_exercise_progression", {"exercise_name": "Bench Press - Powerlifting", "member_id": 2})
        missing = bound.tools.execute("get_exercise_progression", {"exercise_name": "Dumbbell Bench Press"})
        self.assertEqual(state["recommended_weight"], 237.5)
        self.assertIn("No saved progression", missing["message"])
        with patch.dict(os.environ, {}, clear=True), patch.object(coach_module, "COACH_MODE", "local"):
            self.assertIn("237.5 lb", bound.reply("What weight should I bench next time?"))

    def test_provider_tool_loop_has_a_hard_limit_and_falls_back_safely(self):
        class Responses:
            def __init__(self): self.calls = 0
            def create(self, **_kwargs):
                self.calls += 1
                call = types.SimpleNamespace(type="function_call", call_id=f"call-{self.calls}", name="get_member_profile", arguments="{}")
                return types.SimpleNamespace(id=f"response-{self.calls}", output=[call], output_text="")
        responses = Responses()
        fake_openai = types.SimpleNamespace(OpenAI=lambda **_kwargs: types.SimpleNamespace(responses=responses))
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False), patch.object(coach_module, "COACH_MODE", "openai"), patch.object(self.service, "_tool", return_value={"ok": True}), patch.dict(sys.modules, {"openai": fake_openai}):
            answer = self.service.reply(1, "Show my profile")
        self.assertTrue(answer)
        self.assertLessEqual(responses.calls, coach_module.MAX_TOOL_ITERATIONS + 1)
        self.assertEqual(self.service.last_error, "tool_iteration_limit")


if __name__ == "__main__":
    unittest.main()
