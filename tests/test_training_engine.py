import unittest

from training.editing import change_rep_range, change_sets, replace_with_best_substitute
from training.filtering import find_substitutes, ranked_for_target
from training.models import Exercise, TrainingGoal, TrainingPreferences, UserProfile
from training.programming import build_weekly_program
from training.validation import validate_workout


def exercise(name, primary, secondary=(), mechanic="compound", equipment="dumbbell"):
    return Exercise(name, tuple(primary), tuple(secondary), equipment, "horizontal push", "beginner", mechanic, "strength")


class TrainingEngineTests(unittest.TestCase):
    def setUp(self):
        self.profile = UserProfile(TrainingGoal.STRENGTH, "beginner", 3, "dumbbell", "push pull legs")

    def test_primary_target_outranks_secondary_target(self):
        chest_primary = exercise("Dumbbell Bench Press", ("chest",), ("triceps",))
        triceps_secondary = exercise("Dumbbell Triceps Extension", ("triceps",), ("chest",))
        ranked = ranked_for_target([triceps_secondary, chest_primary], "chest", self.profile)
        self.assertEqual([item.name for item in ranked], ["Dumbbell Bench Press"])

    def test_limitations_remove_common_aggravating_movements(self):
        shoulder_press = exercise("Dumbbell Shoulder Press", ("shoulders",))
        row = exercise("Dumbbell Row", ("lats",))
        profile = UserProfile(TrainingGoal.HYPERTROPHY, "beginner", 1, "dumbbell", "full body", "shoulder irritation")
        program = build_weekly_program([shoulder_press, row], profile)
        names = [entry["name"] for entry in program[0]["exercises"]]
        self.assertNotIn("Dumbbell Shoulder Press", names)

    def test_compounds_come_before_isolation(self):
        bench = exercise("Dumbbell Bench Press", ("chest",), mechanic="compound")
        fly = exercise("Dumbbell Fly", ("chest",), mechanic="isolation")
        profile = UserProfile(TrainingGoal.HYPERTROPHY, "beginner", 1, "dumbbell", "full body")
        session = build_weekly_program([fly, bench], profile)[0]["exercises"]
        self.assertEqual(session[0]["name"], "Dumbbell Bench Press")

    def test_substitutes_prioritize_primary_muscle_and_pattern(self):
        barbell_bench = exercise("Barbell Bench Press", ("chest",), ("triceps",), equipment="barbell")
        dumbbell_bench = exercise("Dumbbell Bench Press", ("chest",), ("triceps",))
        machine_fly = exercise("Machine Fly", ("chest",), mechanic="isolation", equipment="machine")
        profile = UserProfile(TrainingGoal.STRENGTH, "beginner", 1, "dumbbell")
        options = find_substitutes(barbell_bench, [barbell_bench, machine_fly, dumbbell_bench], "dumbbell", profile)
        self.assertEqual(options[0].exercise.name, "Dumbbell Bench Press")
        self.assertIn("same primary muscles", options[0].reason)

    def test_unavailable_equipment_and_excluded_exercises_are_filtered(self):
        bench = exercise("Dumbbell Bench Press", ("chest",))
        profile = UserProfile(TrainingGoal.HYPERTROPHY, "beginner", 1, "dumbbell", "full body", avoid_exercises=("bench press",), preferences=TrainingPreferences(unavailable_equipment=("dumbbell",)))
        self.assertEqual(ranked_for_target([bench], "chest", profile), [])

    def test_custom_sets_and_rep_range(self):
        bench = exercise("Dumbbell Bench Press", ("chest",))
        profile = UserProfile(TrainingGoal.HYPERTROPHY, "beginner", 1, "dumbbell", "full body", preferences=TrainingPreferences(preferred_sets=5, preferred_rep_range=(6, 8)))
        entry = build_weekly_program([bench], profile)[0]["exercises"][0]
        self.assertEqual((entry["sets"], entry["rep_min"], entry["rep_max"]), (5, 6, 8))

    def test_preferred_exercise_and_automatic_defaults(self):
        bench = exercise("Dumbbell Bench Press", ("chest",))
        floor_press = exercise("Dumbbell Floor Press", ("chest",))
        preferred = UserProfile(TrainingGoal.HYPERTROPHY, "beginner", 1, "dumbbell", "full body", favorite_exercises=("Dumbbell Floor Press",))
        self.assertEqual(ranked_for_target([bench, floor_press], "chest", preferred)[0].name, "Dumbbell Floor Press")
        automatic = UserProfile(TrainingGoal.STRENGTH, "beginner", 1, "dumbbell", "full body")
        entry = build_weekly_program([bench], automatic)[0]["exercises"][0]
        self.assertEqual((entry["sets"], entry["rep_min"], entry["rep_max"]), (4, 4, 6))

    def test_editing_and_validation(self):
        bench = exercise("Dumbbell Bench Press", ("chest",))
        pushup = exercise("Push-Up", ("chest",), equipment="body only")
        profile = UserProfile(TrainingGoal.HYPERTROPHY, "beginner", 1, "dumbbell", "full body")
        workout = build_weekly_program([bench, pushup], profile)
        workout = change_sets(workout, "Dumbbell Bench Press", 4)
        workout = change_rep_range(workout, "Dumbbell Bench Press", 8, 10)
        updated, recommendation = replace_with_best_substitute(workout, "Dumbbell Bench Press", [bench, pushup], profile)
        self.assertEqual(updated[0]["exercises"][0]["name"], "Push-Up")
        self.assertGreater(recommendation["score"], 0)
        invalid = change_sets(updated, "Push-Up", 10)
        self.assertTrue(validate_workout(invalid, [bench, pushup], profile))


if __name__ == "__main__":
    unittest.main()
