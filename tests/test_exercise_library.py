import unittest
from app import app, exercise_slug
from training.exercise_repository import _load_exercises, load_exercises


class ExerciseLibraryTests(unittest.TestCase):
    def test_repository_cache_preserves_exercise_results(self):
        _load_exercises.cache_clear()
        first = load_exercises()
        second = load_exercises()
        self.assertEqual(first, second)
        self.assertEqual(_load_exercises.cache_info().misses, 1)

    def setUp(self):
        self.client = app.test_client()

    def test_slug_is_url_safe_and_resolves_to_detail_page(self):
        exercise = next(item for item in load_exercises() if "Bench Press" in item.name)
        slug = exercise_slug(exercise.name)
        self.assertNotIn(" ", slug)
        response = self.client.get(f"/exercises/{slug}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Smart alternatives", response.data)

    def test_search_filters_exercise_library(self):
        response = self.client.get("/exercises?q=romanian")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Romanian", response.data)

    def test_library_uses_accessible_sylrix_exercise_cards(self):
        response = self.client.get("/exercises?q=bench")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<section class="exercise-grid" aria-label="Exercise results">', response.data)
        self.assertIn(b'exercise-result-card', response.data)
        self.assertIn(b"Primary muscle", response.data)
        self.assertIn(b"Equipment", response.data)
        self.assertIn(b"Difficulty", response.data)
        self.assertIn(b"View exercise", response.data)
        self.assertNotIn(b"View movement", response.data)

    def test_detail_renders_original_front_back_anatomy_with_muscle_states(self):
        exercise = next(item for item in load_exercises() if "Bench Press" in item.name)
        response = self.client.get(f"/exercises/{exercise_slug(exercise.name)}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Front muscular anatomy", response.data)
        self.assertIn(b"Back muscular anatomy", response.data)
        self.assertIn(b"body-base", response.data)
        self.assertIn(b'class="region primary"', response.data)
        self.assertIn(b'class="region secondary"', response.data)
        self.assertIn(b"Primary", response.data)
        self.assertIn(b"Secondary", response.data)


if __name__ == "__main__":
    unittest.main()
