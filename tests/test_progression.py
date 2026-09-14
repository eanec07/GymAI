import unittest
from training.progression import calisthenics_progression, hypertrophy_progression, strength_progression
from training.prs import detect_prs


def rows(weight, reps):
    return [{"actual_weight": weight, "actual_reps": rep, "completed": True} for rep in reps]


class ProgressionTests(unittest.TestCase):
    def test_strength_success_increases_upper_body(self):
        result = strength_progression(rows(235, [5, 5, 5]), 5, "Barbell Bench Press")
        self.assertEqual((result.action, result.next_weight), ("increase", 237.5))

    def test_single_strength_miss_holds_load(self):
        result = strength_progression(rows(235, [5, 5, 3]), 5, "Barbell Bench Press")
        self.assertEqual(result.action, "hold")

    def test_repeated_strength_misses_deload(self):
        result = strength_progression(rows(235, [5, 4, 3]), 5, "Barbell Bench Press", prior_failures=2)
        self.assertEqual(result.action, "deload")

    def test_hypertrophy_top_range_increases(self):
        result = hypertrophy_progression(rows(70, [12, 12, 12]), 8, 12)
        self.assertEqual((result.action, result.next_weight), ("increase", 75))

    def test_hypertrophy_below_top_adds_reps(self):
        self.assertEqual(hypertrophy_progression(rows(70, [10, 9, 8]), 8, 12).action, "add_reps")

    def test_calisthenics_requires_repeated_success(self):
        self.assertEqual(calisthenics_progression(rows(None, [8, 8, 8]), "Assisted Pull-Up", 0).action, "add_reps")
        self.assertEqual(calisthenics_progression(rows(None, [8, 8, 8]), "Assisted Pull-Up", 2).action, "variation")

    def test_prs_use_baseline_then_compare_history(self):
        self.assertEqual(detect_prs("Bench Press", rows(225, [5]), [])[0].kind, "baseline")
        events = detect_prs("Bench Press", rows(235, [5]), rows(225, [5]))
        self.assertIn("weight", [event.kind for event in events])
        self.assertIn("e1rm", [event.kind for event in events])


if __name__ == "__main__":
    unittest.main()
