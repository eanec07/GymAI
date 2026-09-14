import unittest

from app import app, exercise_slug
from training.exercise_repository import load_exercises


class ExerciseLibraryTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
