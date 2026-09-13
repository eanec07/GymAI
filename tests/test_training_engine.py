import unittest

from training.filtering import ranked_for_target
from training.models import Exercise, TrainingGoal, UserProfile
from training.programming import build_weekly_program


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


if __name__ == "__main__":
    unittest.main()
